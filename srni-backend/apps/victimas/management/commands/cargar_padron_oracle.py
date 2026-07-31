"""
Management command: cargar_padron_oracle

Puebla el padrón de SICAV desde el Oracle legacy. Es la última pieza del circuito:

    .9 (Oracle UARIV) ──▶ ESTA CARGA ──▶ Victima (PostgreSQL) ──▶ padrón SQLite ──▶ APK

De dónde sale cada dato
-----------------------
| Aporta | Tabla | Cómo se alcanza |
|---|---|---|
| documento, tipo, nombres, fecha nac. | `GIC_PERSONA` | esquema propio en `.9` |
| etnia, discapacidad, género | `M_CARACT_TABLA_RA_PER` | `RNIPAQUETES` vía `DBL_VIVANTO` |

Se unen por `GIC_PERSONA.PER_IDPERSONA = corte.CONS_PERONA` — cruce medido al 99,8 %.

Qué NO carga, y por qué
-----------------------
**`ESTADO_RUV` se ignora deliberadamente.** El corte lo trae como número con cuatro
valores (1: 7.827.597 · 2: 1.703.048 · 3: 430.518 · 4: 340) y **no existe catálogo
que diga qué significan**: `MI_ESTADOPERSONAS` es acreditación de identidad y
`MI_ESTADOVICTIMA` solo tiene dos valores. Adivinar aquí no es una imprecisión
menor: `estado_ruv` y `habilitado_para_caracterizacion` deciden **si una persona
puede ser caracterizada**. Mapear mal el 2 bloquearía a 1,7 millones de personas, o
habilitaría a quien no debía.

Así que las personas se cargan con el `estado_ruv` por defecto del modelo y
habilitadas, y la elegibilidad la resuelve el encuestador con el manual —que es
quien la resuelve hoy—. Cuando se sepa qué significan esos códigos, se completa con
una segunda pasada; el resto de la carga no cambia.

Rendimiento — medido contra producción el 2026-07-31
----------------------------------------------------
| Modo | Ritmo real | Las ~7,75 M |
|---|---:|---:|
| `--solo-identidad` (sin dblink) | **6.667 filas/s** | **~20 min** |
| completo (con el JOIN por dblink) | 220 filas/s | ~10 h |

El JOIN por dblink cuesta **30 veces más**. Por eso la carga se hace en dos tiempos:

1. **`--solo-identidad` primero.** En 20 minutos el padrón queda utilizable: documento,
   tipo, nombres y fecha de nacimiento es todo lo que necesita el encuestador para
   identificar a la persona en campo.
2. **La pasada completa después**, sin prisa —de noche, por ejemplo—, para enriquecer
   con etnia, género y discapacidad. Es idempotente: actualiza lo ya cargado.

Al revés no tiene sentido: esperar diez horas para tener un padrón que en veinte
minutos ya servía.

Uso
---
    python manage.py cargar_padron_oracle --limite 500                    # prueba
    python manage.py cargar_padron_oracle --solo-identidad --confirmar    # ~20 min
    python manage.py cargar_padron_oracle --confirmar                     # ~10 h

DRY-RUN por defecto. Idempotente: reprocesa por `cons_persona` sin duplicar.
"""
import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.victimas import homologacion as H

# Una sola consulta con el JOIN por dblink. El corte está del otro lado, así que se
# trae solo lo que se usa: pedir `SELECT *` sobre 10 M filas por dblink es la
# diferencia entre minutos y horas.
_COLUMNAS_IDENTIDAD = """
           p.per_idpersona, p.per_tipodoc, p.per_numerodoc,
           p.per_primernombre, p.per_segundonombre,
           p.per_primerapellido, p.per_segundoapellido,
           p.per_fechanacimiento"""

_FILTRO = """
     WHERE p.per_numerodoc IS NOT NULL
       AND TRIM(p.per_numerodoc) IS NOT NULL
       AND p.per_idpersona > :desde"""

# Con el corte de Vivanto: trae además etnia, género y discapacidad.
CONSULTA_COMPLETA = f"""
    SELECT {_COLUMNAS_IDENTIDAD},
           c.pert_etnica, c.genero_hom, c.discap
      FROM gic_persona p
      LEFT JOIN RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO c
             ON c.cons_perona = p.per_idpersona
    {_FILTRO}
"""

# Solo identidad: documento, nombres y fecha de nacimiento. Sin tocar el dblink.
CONSULTA_IDENTIDAD = f"""
    SELECT {_COLUMNAS_IDENTIDAD},
           NULL AS pert_etnica, NULL AS genero_hom, NULL AS discap
      FROM gic_persona p
    {_FILTRO}
"""
# ⚠️ SIN `ORDER BY`, y es deliberado — medido el 2026-07-31:
#
#     sin ORDER BY   5.424 filas/s  →  7,75 M en  0,4 h  (24 minutos)
#     con ORDER BY     170 filas/s  →  7,75 M en 12,7 h
#
# **32 veces más lento.** La causa: `GIC_PERSONA` tiene 15 índices —sobre documento,
# nombres y apellidos— pero **ninguno sobre `PER_IDPERSONA`**, así que ordenar por él
# obliga a un full scan más un sort de 7,7 millones de filas.
#
# La primera versión llevaba `ORDER BY` para poder reanudar con `--desde` tras un
# corte de red. No compensa: reanudar ahorraba minutos y el orden costaba doce horas.
# Como la carga es **idempotente por `cons_persona`**, si se corta basta con volver a
# correrla entera — 24 minutos— y las ya cargadas se actualizan sin duplicar.
#
# `--desde` se mantiene como filtro opcional (útil para acotar un rango a mano), pero
# ya no es el mecanismo de recuperación: el mecanismo es la idempotencia.


class Command(BaseCommand):
    help = ("Carga el padrón de víctimas desde el Oracle legacy hacia la base de "
            "SICAV. DRY-RUN por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true",
                            help="Escribe de verdad. Sin él, solo informa.")
        parser.add_argument("--limite", type=int, default=0,
                            help="Procesa solo N personas (para probar).")
        parser.add_argument("--lote", type=int, default=1000,
                            help="Filas por fetch (default 1000).")
        parser.add_argument("--solo-identidad", action="store_true",
                            help="Omite el JOIN por dblink: carga documento, nombres "
                                 "y fecha de nacimiento, sin etnia/género/discapacidad. "
                                 "Es ~25x mas rapido (ver la nota de rendimiento).")
        parser.add_argument("--desde", type=int, default=0,
                            help="Procesa solo per_idpersona mayores a este (para "
                                 "acotar un rango a mano; NO es el mecanismo de "
                                 "recuperación: para eso basta con volver a correr, "
                                 "que es idempotente).")

    def handle(self, *args, **opts):
        from apps.victimas.models import CargaPadron

        confirmar, limite, lote = opts["confirmar"], opts["limite"], opts["lote"]
        desde = opts["desde"]
        solo_identidad = opts["solo_identidad"]
        consulta = CONSULTA_IDENTIDAD if solo_identidad else CONSULTA_COMPLETA
        conexion = self._abrir()
        catalogo_tipos = H.cargar_catalogo_tipodoc_oracle()
        tipos_sicav = self._tipos_sicav()

        carga = CargaPadron.objects.create(
            origen=(f"{conexion['dsn']} · GIC_PERSONA" +
                    ("" if solo_identidad else " + M_CARACT_TABLA_RA_PER")),
            estado="EN_CURSO" if confirmar else "SIMULADA",
        )
        self.stdout.write(self.style.WARNING(
            f"\n{'ESCRITURA REAL' if confirmar else 'DRY-RUN (no escribe)'} — "
            f"origen {conexion['dsn']}\n"
            f"  catálogo de tipos de documento de Oracle: {len(catalogo_tipos)} entradas\n"
        ))

        contadores = {"leidas": 0, "creadas": 0, "actualizadas": 0,
                      "descartadas": 0, "sin_tipo_documento": 0}
        motivos, inicio = {}, time.monotonic()
        ultimo_id = desde
        if desde:
            self.stdout.write(f"  reanudando desde per_idpersona > {desde:,}\n")

        try:
            cursor = conexion["con"].cursor()
            cursor.arraysize = lote
            cursor.execute(consulta, {"desde": desde})
            while True:
                filas = cursor.fetchmany(lote)
                if not filas:
                    break
                for fila in filas:
                    self._procesar(fila, contadores, motivos, catalogo_tipos,
                                   tipos_sicav, confirmar)
                    ultimo_id = fila[0] or ultimo_id
                    if limite and contadores["leidas"] >= limite:
                        break
                self.stdout.write(
                    f"  {contadores['leidas']:>9,} leídas · "
                    f"{contadores['creadas']:>8,} nuevas · "
                    f"{contadores['actualizadas']:>8,} actualizadas · "
                    f"{contadores['descartadas']:>7,} descartadas")
                if limite and contadores["leidas"] >= limite:
                    break
        except Exception as exc:                                   # noqa: BLE001
            carga.estado = "FALLIDA"
            carga.detalle = (f"{type(exc).__name__}: {exc}"[:1900] +
                             f" | reanudar con --desde {ultimo_id}")
            self._cerrar(carga, contadores, motivos)
            raise CommandError(
                f"La carga falló tras {contadores['leidas']:,} filas: {exc}\n"
                f"La carga es idempotente: volver a correrla entera (~25 min) "
                f"actualiza lo ya cargado sin duplicar.\n"
                f"Último per_idpersona visto: {ultimo_id} (el orden no está "
                f"garantizado, así que NO sirve como punto de corte exacto).")
        finally:
            conexion["con"].close()

        if carga.estado == "EN_CURSO":
            carga.estado = "COMPLETADA"
        self._cerrar(carga, contadores, motivos)

        segundos = time.monotonic() - inicio
        self.stdout.write(self.style.SUCCESS(
            f"\n{'Cargadas' if confirmar else 'Simuladas'} {contadores['leidas']:,} "
            f"personas en {segundos:.0f}s"))
        self.stdout.write(
            f"  nuevas {contadores['creadas']:,} · actualizadas "
            f"{contadores['actualizadas']:,} · descartadas {contadores['descartadas']:,}")
        self.stdout.write(self.style.WARNING(
            f"  sin tipo de documento: {contadores['sin_tipo_documento']:,} "
            f"— se encuentran por el índice de respaldo, con aviso al encuestador"))
        for motivo, n in sorted(motivos.items(), key=lambda kv: -kv[1]):
            self.stdout.write(f"    descarte · {motivo}: {n:,}")
        self.stdout.write(self.style.NOTICE(
            "  estado_ruv NO se cargó: falta saber qué significan sus 4 códigos "
            "(ver el docstring del comando)"))
        self.stdout.write(f"  último per_idpersona visto: {ultimo_id:,}")

    # ── piezas ───────────────────────────────────────────────────────────────
    def _abrir(self):
        """Conexión de LECTURA al Oracle legacy, reusando la capa que ya existe."""
        from apps.sincronizacion.oracle import conexion as cx
        try:
            cfg = cx.resolver_config(cx.DESTINO_PRODUCCION)
        except cx.DestinoNoConfigurado as exc:
            raise CommandError(
                f"{exc}\nExporta ORACLE_PROD_HOST/SERVICE/USER/PASSWORD antes de correr.")
        return {"con": cx.abrir_conexion(cx.DESTINO_PRODUCCION),
                "dsn": f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['service']}"}

    @staticmethod
    def _tipos_sicav():
        from apps.parametricas.models import TipoDocumento
        return {t.codigo: t for t in TipoDocumento.objects.all()}

    def _procesar(self, fila, contadores, motivos, catalogo_tipos, tipos_sicav, confirmar):
        from apps.victimas.models import Victima

        (cons, tipodoc_raw, numero, n1, n2, a1, a2, f_nac,
         etnia, genero, discap) = fila
        contadores["leidas"] += 1

        numero = (numero or "").strip()
        if not numero:
            contadores["descartadas"] += 1
            motivos["sin número de documento"] = motivos.get("sin número de documento", 0) + 1
            return

        codigo_tipo = H.homologar_tipo_documento(tipodoc_raw, catalogo_tipos)
        tipo = tipos_sicav.get(codigo_tipo) if codigo_tipo else None
        if tipo is None:
            contadores["sin_tipo_documento"] += 1

        if not confirmar:
            return

        # Idempotencia por `cons_persona`: es el id de la persona en el legacy, así que
        # reprocesar actualiza en vez de duplicar. Los duplicados de documento SÍ se
        # cargan como registros separados —decisión del 29-jul— porque pueden ser
        # personas distintas y fusionarlos borraría a una del padrón.
        _, creada = Victima.objects.update_or_create(
            cons_persona=cons,
            defaults={
                "tipo_documento": tipo,
                "numero_documento": numero,
                "primer_nombre": (n1 or "").strip(),
                "segundo_nombre": (n2 or "").strip(),
                "primer_apellido": (a1 or "").strip(),
                "segundo_apellido": (a2 or "").strip(),
                "fecha_nacimiento": f_nac.date().isoformat() if f_nac else "",
                "genero": H.homologar_genero(genero),
                "pertenencia_etnica": H.homologar_etnia(etnia),
                "discapacidad": H.homologar_discapacidad(discap),
                "fuente_origen": "RUV",
                # estado_ruv y habilitado_para_caracterizacion se dejan en el default
                # del modelo: ver el docstring del comando.
            },
        )
        contadores["creadas" if creada else "actualizadas"] += 1

    @staticmethod
    def _cerrar(carga, contadores, motivos):
        for campo, valor in contadores.items():
            setattr(carga, campo, valor)
        carga.motivos_descarte = motivos
        carga.terminada_en = timezone.now()
        carga.save()
