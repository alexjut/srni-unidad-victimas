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

`ESTADO_RUV`: se carga como dato INFORMATIVO, no como filtro
-------------------------------------------------------------
El corte trae `ESTADO_RUV` como número con cuatro valores. Según Edwin (31-jul) son
*incluidos, no incluidos, en valoración y excluidos* — **pero él mismo aclaró que le
falta validarlo con el área de RUV**, y no hay catálogo en la base que lo confirme.

La medición lo respalda: mirando solo a las personas **ya caracterizadas**, el estado
**3 cae de 4,3 % a 0,5 %** (ocho veces menos), que es justo lo que se espera de "en
valoración" — a quien tiene el caso en trámite todavía no se le caracteriza.

Así que el valor **se carga** (sirve para estadísticas y para dar contexto al
encuestador) pero **`habilitado_para_caracterizacion` NO se deriva de él** hasta que
el RUV confirme. Si el 2 no fuera "no incluido", derivar la habilitación de una
hipótesis bloquearía a 1,7 millones de personas. Un dato informativo equivocado se
corrige; una caracterización negada en campo, no.

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
           c.pert_etnica, c.genero_hom, c.discap, c.estado_ruv
      FROM gic_persona p
      LEFT JOIN RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO c
             ON c.cons_perona = p.per_idpersona
    {_FILTRO}
"""

# Solo identidad: documento, nombres y fecha de nacimiento. Sin tocar el dblink.
CONSULTA_IDENTIDAD = f"""
    SELECT {_COLUMNAS_IDENTIDAD},
           NULL AS pert_etnica, NULL AS genero_hom, NULL AS discap,
           NULL AS estado_ruv
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
        parser.add_argument("--carga-inicial", action="store_true",
                            help="Inserta por lotes (bulk) en vez de upsert fila a "
                                 "fila: 51 filas/s -> minutos. Solo para la PRIMERA "
                                 "carga; exige que la tabla este vacia porque no "
                                 "deduplica.")
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
        carga_inicial = opts["carga_inicial"]
        consulta = CONSULTA_IDENTIDAD if solo_identidad else CONSULTA_COMPLETA
        if carga_inicial and confirmar:
            # El criterio NO es "la tabla está vacía" —siempre hay algún registro de
            # prueba o de alta manual— sino "¿ya hubo una carga masiva?". Insertar por
            # lotes no deduplica, así que repetirla duplicaría el padrón entero.
            previa = CargaPadron.objects.filter(estado="COMPLETADA",
                                                creadas__gt=1000).first()
            if previa:
                raise CommandError(
                    f"Ya hay una carga inicial del {previa.iniciada_en:%Y-%m-%d %H:%M} "
                    f"con {previa.creadas:,} personas. `--carga-inicial` inserta sin "
                    f"deduplicar, así que duplicaría el padrón.\n"
                    f"Para recargar o actualizar, corre SIN `--carga-inicial`: el "
                    f"upsert es más lento pero es idempotente.")
        acumulador = [] if (carga_inicial and confirmar) else None

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
                                   tipos_sicav, confirmar, acumulador)
                    ultimo_id = fila[0] or ultimo_id
                    if limite and contadores["leidas"] >= limite:
                        break
                if acumulador is not None and len(acumulador) >= 2000:
                    self._volcar(acumulador)
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
            if acumulador:
                self._volcar(acumulador)
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
            "  estado_ruv cargado como INFORMATIVO (mapeo aún por validar con RUV); "
            "la habilitación para caracterizar NO se deriva de él"))
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

    def _procesar(self, fila, contadores, motivos, catalogo_tipos, tipos_sicav,
                  confirmar, acumulador=None):
        from apps.victimas.models import Victima

        (cons, tipodoc_raw, numero, n1, n2, a1, a2, f_nac,
         etnia, genero, discap, estado) = fila
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

        # ── carga inicial: se acumula para insertar por lotes ────────────────
        # `update_or_create` hace un SELECT y un INSERT por persona: medido, 51
        # filas/s → **42 horas** para el padrón completo. Con `bulk_create` el mismo
        # trabajo se hace en lotes y baja a minutos.
        #
        # El precio es que `bulk_create` NO llama a `save()`, así que los dos hashes
        # —que normalmente calcula el modelo— hay que calcularlos aquí. Se usan las
        # MISMAS funciones (`doc_hash` / `num_hash`), nunca una fórmula reescrita:
        # duplicar esa lógica es exactamente el defecto que costó una tarde arreglar.
        if acumulador is not None:
            from apps.victimas.repository.base import doc_hash, num_hash
            acumulador.append(Victima(
                cons_persona=cons,
                tipo_documento=tipo,
                numero_documento=numero,
                numero_documento_hash=doc_hash(codigo_tipo or "", numero),
                numero_documento_hash_sin_tipo=num_hash(numero),
                primer_nombre=(n1 or "").strip(),
                segundo_nombre=(n2 or "").strip(),
                primer_apellido=(a1 or "").strip(),
                segundo_apellido=(a2 or "").strip(),
                fecha_nacimiento=f_nac.date().isoformat() if f_nac else "",
                genero=H.homologar_genero(genero),
                pertenencia_etnica=H.homologar_etnia(etnia),
                discapacidad=H.homologar_discapacidad(discap),
                # Informativo: NO se deriva de aquí la habilitación (ver homologacion).
                estado_ruv=H.homologar_estado_ruv(estado) or "EN_PROCESO",
                fuente_origen="RUV",
            ))
            contadores["creadas"] += 1
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
                "estado_ruv": H.homologar_estado_ruv(estado) or "EN_PROCESO",
                "fuente_origen": "RUV",
                # estado_ruv y habilitado_para_caracterizacion se dejan en el default
                # del modelo: ver el docstring del comando.
            },
        )
        contadores["creadas" if creada else "actualizadas"] += 1

    @staticmethod
    def _volcar(acumulador):
        """Inserta el lote acumulado y lo vacía. `ignore_conflicts` es una red por si
        la fuente trajera un `cons_persona` repetido: mejor perder ese duplicado que
        abortar una carga de millones."""
        from apps.victimas.models import Victima
        Victima.objects.bulk_create(acumulador, batch_size=500, ignore_conflicts=True)
        acumulador.clear()

    @staticmethod
    def _cerrar(carga, contadores, motivos):
        for campo, valor in contadores.items():
            setattr(carga, campo, valor)
        carga.motivos_descarte = motivos
        carga.terminada_en = timezone.now()
        carga.save()
