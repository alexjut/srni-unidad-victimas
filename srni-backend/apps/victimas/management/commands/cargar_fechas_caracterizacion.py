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

Uso
---
    python manage.py cargar_fechas_caracterizacion             # DRY-RUN
    python manage.py cargar_fechas_caracterizacion --confirmar # ~1 min

DRY-RUN por defecto. Idempotente: se puede correr cuantas veces se quiera.
"""
import datetime
import time

from django.core.management.base import BaseCommand, CommandError

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
        cont = {"leidas": 0, "aplicadas": 0, "sin_persona_en_padron": 0,
                "fecha_imposible": 0, "vencidas": 0, "al_dia": 0}
        inicio = time.monotonic()

        try:
            cursor = conexion["con"].cursor()
            cursor.arraysize = lote
            cursor.execute(CONSULTA)
            while True:
                filas = cursor.fetchmany(lote)
                if not filas:
                    break
                self._aplicar_lote(filas, cont, hoy, confirmar, Victima)
                self.stdout.write(
                    f"  {cont['leidas']:>9,} leídas · {cont['aplicadas']:>9,} aplicadas "
                    f"· {cont['vencidas']:>9,} vencidas · "
                    f"{cont['sin_persona_en_padron']:>8,} fuera del padrón")
        except Exception as exc:                                   # noqa: BLE001
            raise CommandError(
                f"Falló tras {cont['leidas']:,} filas: {exc}\n"
                f"Es idempotente: volver a correrla entera (~1 min) no duplica nada.")
        finally:
            conexion["con"].close()

        segundos = time.monotonic() - inicio
        self.stdout.write(self.style.SUCCESS(
            f"\n{'Aplicadas' if confirmar else 'Simuladas'} {cont['aplicadas']:,} "
            f"fechas sobre {cont['leidas']:,} leídas en {segundos:.0f}s"))
        self.stdout.write(
            f"  vencidas (>{H.ANIOS_VIGENCIA_CARACTERIZACION} años, hay que "
            f"recaracterizar): {cont['vencidas']:,}")
        self.stdout.write(f"  al día: {cont['al_dia']:,}")
        self.stdout.write(self.style.WARNING(
            f"  fuera del padrón (caracterizadas pero no son víctimas incluidas hoy): "
            f"{cont['sin_persona_en_padron']:,}"))
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

    def _aplicar_lote(self, filas, cont, hoy, confirmar, Victima):
        """Un lote de (per_idpersona, fecha) → `bulk_update` sobre las que existan.

        Se busca por `cons_persona`, que es el id de la persona en el legacy y la
        misma llave con la que `cargar_padron_oracle` insertó. Las que no estén son
        personas caracterizadas alguna vez que **hoy no son víctimas incluidas** — no
        es un error: es la diferencia entre "se caracterizó" y "hay que caracterizar".
        """
        fechas = {}
        for per_id, fecha in filas:
            cont["leidas"] += 1
            if fecha is None:
                continue
            if fecha.year < ANIO_MINIMO_PLAUSIBLE or fecha.date() > hoy:
                cont["fecha_imposible"] += 1
                continue
            fechas[per_id] = fecha

        if not fechas:
            return

        # `only` para no traer 20 columnas de cada persona: son millones de filas.
        encontradas = list(
            Victima.objects.filter(cons_persona__in=list(fechas))
            .only("id", "cons_persona", "fecha_ult_caracterizacion",
                  "habilitado_para_caracterizacion")
        )
        cont["sin_persona_en_padron"] += len(fechas) - len(encontradas)

        por_actualizar = []
        for victima in encontradas:
            fecha = fechas[victima.cons_persona]
            vencida = H.debe_recaracterizarse(fecha, hoy=hoy)
            cont["vencidas" if vencida else "al_dia"] += 1
            victima.fecha_ult_caracterizacion = self._con_zona(fecha)
            # Ya son todas víctimas incluidas (el padrón las filtró): lo único que
            # decide la habilitación es si la caracterización venció.
            victima.habilitado_para_caracterizacion = vencida
            por_actualizar.append(victima)

        cont["aplicadas"] += len(por_actualizar)
        if confirmar and por_actualizar:
            Victima.objects.bulk_update(
                por_actualizar,
                ["fecha_ult_caracterizacion", "habilitado_para_caracterizacion"],
                batch_size=1000,
            )

    @staticmethod
    def _con_zona(fecha):
        """Oracle devuelve `DATE` sin zona; el campo es `DateTimeField`. Sin esto
        Django emite un `RuntimeWarning` por naive datetime en cada fila."""
        from django.utils import timezone
        if timezone.is_naive(fecha):
            return timezone.make_aware(fecha, timezone.get_current_timezone())
        return fecha
