"""
Management command: cargar_fechas_caracterizacion

Segundo paso del padrón. `cargar_padron_oracle` trae **quién** es víctima incluida;
este trae **cuándo se le caracterizó por última vez**, que es lo que hace operativa
la norma de recaracterizar cada 2 años.

    GIC_MIEMBROS_HOGAR ─┬─▶ MAX(GIC_HOGAR.USU_FECHACREACION) ─▶ Victima.fecha_ult_caracterizacion
    GIC_HOGAR ──────────┘

Por qué va aparte de la carga del padrón
-----------------------------------------
Son dos consultas con costos muy distintos: el padrón cruza por dblink con Vivanto
(~25 min) y esto es **local a la .9** (~1 min, 37.078 filas/s medidos). Meterlas en
la misma consulta obligaría a un tercer JOIN sobre 7,7 M de filas para ahorrar un
minuto. Y separadas se pueden repetir por su cuenta: las fechas cambian cada vez que
alguien caracteriza, el padrón no.

Qué es "la fecha de caracterización"
-------------------------------------
La caracterización cuelga del **hogar**, no de la persona: una persona puede haber
estado en varios hogares a lo largo del tiempo. Se toma el **MAX** — la más reciente,
que es la que define si está al día.

Fechas imposibles
-----------------
Medido el 2026-07-31: **17 personas** tienen fecha de hace ~2.000 años (año 26 d.C. y
similares). Son datos corruptos del legacy, no personas caracterizadas en la
antigüedad. Se descartan: quedan con fecha nula, que por
`debe_recaracterizarse()` significa "hay que caracterizarla" — que es justo lo
correcto para un dato que no sabemos.

Cómo se escribe — medido, no supuesto
--------------------------------------
| Estrategia | Ritmo | Las 3,3 M |
|---|---:|---:|
| `bulk_update` por lotes | 36 filas/s | **~25 h** |
| `COPY` a temporal + un `UPDATE ... FROM` | ~5.000 filas/s | **~12 min** |

`bulk_update` emite un `UPDATE ... CASE WHEN` por lote y antes un `SELECT ... IN`
para traer los objetos: sobre un padrón de 5,9 M con índices, eso es un viaje a la
base por cada mil filas. La primera versión hacía eso y en 7 minutos llevaba 15.000
de 3,3 millones.

La versión de ahora vuelca los pares `(cons_persona, vencida, fecha)` con `COPY`
—que es la vía más rápida que tiene PostgreSQL para meter filas— a una tabla
temporal, y después hace **un solo** `UPDATE ... FROM` con join por `cons_persona`.

**La regla de los 2 años se sigue evaluando en Python**, con
`debe_recaracterizarse()`, y el resultado viaja como un booleano más en el `COPY`.
No se traduce a SQL: duplicar una regla de negocio en dos lenguajes es cómo se
consigue que un día digan cosas distintas y nadie sepa cuál manda.

Uso
---
    python manage.py cargar_fechas_caracterizacion             # DRY-RUN
    python manage.py cargar_fechas_caracterizacion --confirmar # ~12 min

DRY-RUN por defecto. Idempotente: se puede correr cuantas veces se quiera.
"""
import csv
import datetime
import io
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.victimas import homologacion as H

CONSULTA = """
    SELECT m.per_idpersona, MAX(h.usu_fechacreacion)
      FROM gic_miembros_hogar m
      JOIN gic_hogar h ON h.hog_codigo = m.hog_codigo
     WHERE h.usu_fechacreacion IS NOT NULL
     GROUP BY m.per_idpersona
"""

# Antes de esto la Unidad no existía (creada por la Ley 1448 de 2011), así que una
# caracterización anterior es un dato corrupto, no un hecho histórico.
ANIO_MINIMO_PLAUSIBLE = 2011


class Command(BaseCommand):
    help = ("Carga la fecha de última caracterización desde GIC_HOGAR y aplica la "
            "regla de recaracterización a 2 años. DRY-RUN por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true",
                            help="Escribe de verdad. Sin él, solo informa.")
        parser.add_argument("--lote", type=int, default=5000,
                            help="Filas por fetch y por bulk_update (default 5000).")

    def handle(self, *args, **opts):
        from apps.victimas.models import Victima

        confirmar, lote = opts["confirmar"], opts["lote"]
        conexion = self._abrir()
        self.stdout.write(self.style.WARNING(
            f"\n{'ESCRITURA REAL' if confirmar else 'DRY-RUN (no escribe)'} — "
            f"origen {conexion['dsn']} · GIC_HOGAR\n"))

        hoy = datetime.date.today()
        cont = {"leidas": 0, "aplicadas": 0, "fecha_imposible": 0,
                "vencidas": 0, "al_dia": 0}
        inicio = time.monotonic()

        if confirmar:
            self._crear_temporal()

        try:
            cursor = conexion["con"].cursor()
            cursor.arraysize = lote
            cursor.execute(CONSULTA)
            while True:
                filas = cursor.fetchmany(lote)
                if not filas:
                    break
                self._procesar_lote(filas, cont, hoy, confirmar)
                self.stdout.write(
                    f"  {cont['leidas']:>9,} leídas · {cont['vencidas']:>9,} vencidas "
                    f"· {cont['al_dia']:>9,} al día")
        except Exception as exc:                                   # noqa: BLE001
            raise CommandError(
                f"Falló tras {cont['leidas']:,} filas: {exc}\n"
                f"Es idempotente: volver a correrla entera no duplica nada.")
        finally:
            conexion["con"].close()

        if confirmar:
            self.stdout.write("  volcando a la tabla del padrón…")
            cont["aplicadas"] = self._aplicar()

        segundos = time.monotonic() - inicio
        self.stdout.write(self.style.SUCCESS(
            f"\n{'Aplicadas' if confirmar else 'Simuladas'} {cont['aplicadas']:,} "
            f"fechas sobre {cont['leidas']:,} leídas en {segundos:.0f}s"))
        self.stdout.write(
            f"  vencidas (>{H.ANIOS_VIGENCIA_CARACTERIZACION} años, hay que "
            f"recaracterizar): {cont['vencidas']:,}")
        self.stdout.write(f"  al día: {cont['al_dia']:,}")
        fuera = cont["leidas"] - cont["fecha_imposible"] - cont["aplicadas"]
        if confirmar and fuera > 0:
            self.stdout.write(self.style.WARNING(
                f"  fuera del padrón (caracterizadas pero no son víctimas incluidas "
                f"hoy): {fuera:,}"))
        if cont["fecha_imposible"]:
            self.stdout.write(self.style.WARNING(
                f"  fechas imposibles descartadas (anteriores a "
                f"{ANIO_MINIMO_PLAUSIBLE}): {cont['fecha_imposible']:,}"))

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

    TEMPORAL = "tmp_fechas_caracterizacion"

    @property
    def _hay_copy(self):
        """`COPY` es de PostgreSQL. En SQLite —desarrollo y tests— se escribe con
        `bulk_update`, que es lento pero ahí son cuatro filas.

        Los dos caminos comparten lo que importa: la decisión de vigencia se toma
        una sola vez, en `_procesar_lote`, con `debe_recaracterizarse()`. Lo que
        cambia es cómo se vuelcan las filas, no qué dicen."""
        return connection.vendor == "postgresql"

    def _crear_temporal(self):
        """Tabla temporal donde aterriza el `COPY`. Vive lo que dure la conexión."""
        if not self._hay_copy:
            self._pendientes = {}
            return
        with connection.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {self.TEMPORAL}")
            cur.execute(f"""
                CREATE TEMP TABLE {self.TEMPORAL} (
                    cons_persona bigint PRIMARY KEY,
                    vencida      boolean NOT NULL,
                    fecha        timestamptz NOT NULL
                )""")

    def _procesar_lote(self, filas, cont, hoy, confirmar):
        """
        Un lote de `(per_idpersona, fecha)` → decide vigencia y lo vuelca por `COPY`.

        La regla de los 2 años se evalúa **aquí, en Python**, con
        `debe_recaracterizarse()`. Al SQL solo viaja el booleano ya resuelto: la
        regla vive en un único lugar y es la que está cubierta por tests.
        """
        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter="\t", lineterminator="\n")
        n = 0

        for per_id, fecha in filas:
            cont["leidas"] += 1
            if fecha is None:
                continue
            if fecha.year < ANIO_MINIMO_PLAUSIBLE or fecha.date() > hoy:
                cont["fecha_imposible"] += 1
                continue
            vencida = H.debe_recaracterizarse(fecha, hoy=hoy)
            cont["vencidas" if vencida else "al_dia"] += 1
            if not confirmar:
                continue
            if self._hay_copy:
                escritor.writerow([per_id, "t" if vencida else "f",
                                   fecha.isoformat(sep=" ")])
                n += 1
            else:
                self._pendientes[per_id] = (vencida, fecha)

        if confirmar and self._hay_copy and n:
            buffer.seek(0)
            with connection.cursor() as cur:
                cur.copy_expert(
                    f"COPY {self.TEMPORAL} (cons_persona, vencida, fecha) FROM STDIN",
                    buffer)

    def _aplicar(self):
        """
        Un solo `UPDATE ... FROM` con join por `cons_persona`.

        Las filas de la temporal que no encuentren pareja son personas caracterizadas
        alguna vez que **hoy no son víctimas incluidas**, así que no están en el
        padrón. No es un error: es la diferencia entre "se caracterizó" y "hay que
        caracterizar".

        Ya son todas víctimas incluidas (el padrón las filtró al cargarse), así que
        lo único que decide la habilitación es si la caracterización venció.
        """
        if not self._hay_copy:
            return self._aplicar_sin_copy()
        with connection.cursor() as cur:
            cur.execute(f"""
                UPDATE victimas_victima v
                   SET fecha_ult_caracterizacion = t.fecha,
                       habilitado_para_caracterizacion = t.vencida,
                       updated_at = NOW()
                  FROM {self.TEMPORAL} t
                 WHERE v.cons_persona = t.cons_persona""")
            return cur.rowcount

    def _aplicar_sin_copy(self):
        """Camino de SQLite (desarrollo y tests): `bulk_update`. Mismo resultado."""
        from django.utils import timezone
        from apps.victimas.models import Victima

        encontradas = list(
            Victima.objects.filter(cons_persona__in=list(self._pendientes))
            .only("id", "cons_persona", "fecha_ult_caracterizacion",
                  "habilitado_para_caracterizacion"))
        for victima in encontradas:
            vencida, fecha = self._pendientes[victima.cons_persona]
            if timezone.is_naive(fecha):
                fecha = timezone.make_aware(fecha, timezone.get_current_timezone())
            victima.fecha_ult_caracterizacion = fecha
            victima.habilitado_para_caracterizacion = vencida
        Victima.objects.bulk_update(
            encontradas,
            ["fecha_ult_caracterizacion", "habilitado_para_caracterizacion"],
            batch_size=1000)
        return len(encontradas)
