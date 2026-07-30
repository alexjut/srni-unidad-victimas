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

Uso
---
    python manage.py cargar_padron_oracle --limite 500        # prueba, no escribe
    python manage.py cargar_padron_oracle --limite 500 --confirmar
    python manage.py cargar_padron_oracle --confirmar         # las ~7,7 M

DRY-RUN por defecto. Idempotente: reprocesa por `cons_persona` sin duplicar.
"""
import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.victimas import homologacion as H

# Una sola consulta con el JOIN por dblink. El corte está del otro lado, así que se
# trae solo lo que se usa: pedir `SELECT *` sobre 10 M filas por dblink es la
# diferencia entre minutos y horas.
CONSULTA = """
    SELECT p.per_idpersona, p.per_tipodoc, p.per_numerodoc,
           p.per_primernombre, p.per_segundonombre,
           p.per_primerapellido, p.per_segundoapellido,
           p.per_fechanacimiento,
           c.pert_etnica, c.genero_hom, c.discap
      FROM gic_persona p
      LEFT JOIN RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO c
             ON c.cons_perona = p.per_idpersona
     WHERE p.per_numerodoc IS NOT NULL
       AND TRIM(p.per_numerodoc) IS NOT NULL
       AND p.per_idpersona > :desde
     ORDER BY p.per_idpersona
"""
# El `ORDER BY` y el `> :desde` son los que hacen la carga REANUDABLE, y no son un
# lujo: la conexión a `.9` se cortó dos veces en dos días durante este trabajo. Sobre
# 7,7 millones de filas, una carga que no se puede reanudar es una carga que en la
# práctica no termina — cada corte obliga a releer todo desde el principio.
#
# Con orden por `per_idpersona`, el comando informa el último id procesado y la
# siguiente corrida arranca ahí con `--desde`.


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
        parser.add_argument("--desde", type=int, default=0,
                            help="Reanuda desde este per_idpersona (el que informa "
                                 "la corrida anterior al cortarse).")

    def handle(self, *args, **opts):
        from apps.victimas.models import CargaPadron

        confirmar, limite, lote = opts["confirmar"], opts["limite"], opts["lote"]
        desde = opts["desde"]
        conexion = self._abrir()
        catalogo_tipos = H.cargar_catalogo_tipodoc_oracle()
        tipos_sicav = self._tipos_sicav()

        carga = CargaPadron.objects.create(
            origen=f"{conexion['dsn']} · GIC_PERSONA + M_CARACT_TABLA_RA_PER",
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
            cursor.execute(CONSULTA, {"desde": desde})
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
                f"REANUDAR CON:  --desde {ultimo_id}"
                f"{' --confirmar' if confirmar else ''}")
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
        self.stdout.write(f"  último per_idpersona procesado: {ultimo_id:,}"
                          f"  → para continuar: --desde {ultimo_id}")

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
