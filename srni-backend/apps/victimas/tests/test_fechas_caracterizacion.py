"""
Tests de `cargar_fechas_caracterizacion`.

Es el comando que decide **a quién le toca recaracterización**, así que lo que se
protege no es que corra: es que no deshabilite a quien sí hay que caracterizar. Un
falso "al día" es una persona que se queda sin actualizar sus datos y no se entera
nadie.

Lo que se protege:
1. Que el DRY-RUN no escriba nada.
2. Que la regla de 2 años se aplique en el sentido correcto (vencida → habilitada).
3. Que las fechas imposibles del legacy no se tomen por buenas.
4. Que se use la fecha MÁS RECIENTE cuando la persona estuvo en varios hogares.
"""
from unittest import mock

import datetime
import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db

HOY = datetime.date.today()


def _hace_anios(n):
    """
    Una fecha que hace **n años cumplidos**, con 15 días de margen.

    El margen no es adorno. La primera versión fijaba el día 28 del mes y los tests
    pasaron el 31-jul y fallaron el 1-ago: `_hace_anios(2)` daba el 28 de agosto de
    hace dos años, que el día 1 todavía no ha cumplido los dos años. El código
    estaba bien; el test se caía solo por correr un día distinto.
    """
    base = datetime.datetime(HOY.year - n, HOY.month, min(HOY.day, 28))
    return base - datetime.timedelta(days=15)


# (per_idpersona, fecha) tal como los devuelve el GROUP BY de Oracle
FILAS = [
    (2001, _hace_anios(0)),        # caracterizada este año  → al día
    (2002, _hace_anios(1)),        # hace 1 año              → al día
    (2003, _hace_anios(2)),        # hace 2 años             → VENCIDA
    (2004, _hace_anios(4)),        # campaña de 2022         → VENCIDA
    (2005, datetime.datetime(26, 5, 1)),   # año 26 d.C.: corrupta (17 casos reales)
    (2006, _hace_anios(3)),        # no está en el padrón
]


class _CursorFalso:
    def __init__(self, filas):
        self._pendientes = list(filas)
        self.arraysize = 1000

    def execute(self, sql, params=None):
        self.sql = sql

    def fetchmany(self, n):
        lote, self._pendientes = self._pendientes[:n], self._pendientes[n:]
        return lote


class _ConexionFalsa:
    def __init__(self, filas):
        self._filas = filas
        self.cerrada = False

    def cursor(self):
        return _CursorFalso(self._filas)

    def close(self):
        self.cerrada = True


@pytest.fixture
def fuente(db):
    """Simula Oracle y siembra en el padrón a 2001-2005 (2006 queda fuera a propósito)."""
    from apps.victimas.models import Victima
    for cons in (2001, 2002, 2003, 2004, 2005):
        Victima.objects.create(
            cons_persona=cons, numero_documento=f"{cons}0000",
            primer_nombre="X", primer_apellido="Y", genero="M",
            estado_ruv="INCLUIDO",
        )
    conexion = _ConexionFalsa(FILAS)
    with mock.patch("apps.sincronizacion.oracle.conexion.abrir_conexion",
                    return_value=conexion), \
         mock.patch("apps.sincronizacion.oracle.conexion.resolver_config",
                    return_value={"user": "U", "host": "30.0.1.9", "port": 1521,
                                  "service": "ENTREVISTARN", "password": "x"}):
        yield conexion


# ── 1. el dry-run no escribe ─────────────────────────────────────────────────
def test_el_dry_run_no_escribe_nada(fuente):
    from apps.victimas.models import Victima
    call_command("cargar_fechas_caracterizacion", verbosity=0)
    assert not Victima.objects.exclude(fecha_ult_caracterizacion=None).exists()


# ── 2. la regla de los 2 años, en el sentido correcto ────────────────────────
def test_la_caracterizacion_reciente_queda_al_dia(fuente):
    from apps.victimas.models import Victima
    call_command("cargar_fechas_caracterizacion", "--confirmar", verbosity=0)

    for cons in (2001, 2002):
        v = Victima.objects.get(cons_persona=cons)
        assert v.fecha_ult_caracterizacion is not None
        assert v.habilitado_para_caracterizacion is False, (
            f"{cons} se caracterizó hace menos de 2 años: no debería estar pendiente")


def test_la_caracterizacion_vencida_habilita_de_nuevo(fuente):
    """Lo más importante del comando: a los 2 años la persona vuelve a estar
    pendiente. Si esto se invirtiera, 1,9 millones de personas vencidas quedarían
    marcadas como al día y nadie las volvería a visitar."""
    from apps.victimas.models import Victima
    call_command("cargar_fechas_caracterizacion", "--confirmar", verbosity=0)

    for cons in (2003, 2004):
        v = Victima.objects.get(cons_persona=cons)
        assert v.habilitado_para_caracterizacion is True, (
            f"{cons} está vencida: tiene que aparecer como pendiente")


# ── 3. las fechas imposibles no se toman por buenas ──────────────────────────
def test_la_fecha_del_anio_26_se_descarta(fuente):
    """17 personas reales tienen fecha de hace ~2.000 años. Guardarla haría creer
    que la persona sí fue caracterizada alguna vez."""
    from apps.victimas.models import Victima
    call_command("cargar_fechas_caracterizacion", "--confirmar", verbosity=0)

    v = Victima.objects.get(cons_persona=2005)
    assert v.fecha_ult_caracterizacion is None
    # sin fecha = nunca caracterizada = hay que caracterizarla
    assert v.habilitado_para_caracterizacion is True


def test_una_fecha_futura_tampoco_pasa(db):
    from apps.victimas.models import Victima
    Victima.objects.create(cons_persona=3001, numero_documento="30010000",
                           primer_nombre="X", primer_apellido="Y", genero="M")
    futura = datetime.datetime(HOY.year + 1, 1, 15)
    conexion = _ConexionFalsa([(3001, futura)])
    with mock.patch("apps.sincronizacion.oracle.conexion.abrir_conexion",
                    return_value=conexion), \
         mock.patch("apps.sincronizacion.oracle.conexion.resolver_config",
                    return_value={"user": "U", "host": "h", "port": 1521,
                                  "service": "S", "password": "x"}):
        call_command("cargar_fechas_caracterizacion", "--confirmar", verbosity=0)

    assert Victima.objects.get(cons_persona=3001).fecha_ult_caracterizacion is None


# ── 4. quien no está en el padrón no rompe nada ──────────────────────────────
def test_la_persona_fuera_del_padron_se_ignora_sin_fallar(fuente):
    """2006 se caracterizó alguna vez pero hoy no es víctima incluida, así que no
    está en el padrón. No es un error: es la diferencia entre 'se caracterizó' y
    'hay que caracterizar'."""
    from apps.victimas.models import Victima
    call_command("cargar_fechas_caracterizacion", "--confirmar", verbosity=0)
    assert not Victima.objects.filter(cons_persona=2006).exists()
    assert Victima.objects.count() == 5


# ── 5. idempotencia ──────────────────────────────────────────────────────────
def test_correrlo_dos_veces_da_lo_mismo(fuente):
    from apps.victimas.models import Victima
    call_command("cargar_fechas_caracterizacion", "--confirmar", verbosity=0)
    primera = {v.cons_persona: (v.fecha_ult_caracterizacion,
                                v.habilitado_para_caracterizacion)
               for v in Victima.objects.all()}

    fuente._filas = FILAS   # el cursor se rearma en cada corrida
    with mock.patch("apps.sincronizacion.oracle.conexion.abrir_conexion",
                    return_value=_ConexionFalsa(FILAS)), \
         mock.patch("apps.sincronizacion.oracle.conexion.resolver_config",
                    return_value={"user": "U", "host": "h", "port": 1521,
                                  "service": "S", "password": "x"}):
        call_command("cargar_fechas_caracterizacion", "--confirmar", verbosity=0)

    segunda = {v.cons_persona: (v.fecha_ult_caracterizacion,
                                v.habilitado_para_caracterizacion)
               for v in Victima.objects.all()}
    assert primera == segunda
    assert Victima.objects.count() == 5


# ── 6. que en producción se use el camino rápido ─────────────────────────────
def test_en_postgres_vuelca_con_copy_no_fila_a_fila(fuente):
    """
    La primera versión escribía con `bulk_update`: en producción hizo 15.000 filas
    en 7 minutos —36 filas/s, ~25 h para las 3,3 M— y hubo que matarla. El COPY a
    una temporal más un solo UPDATE hace lo mismo en minutos.

    Este test no mide velocidad (eso no se puede en SQLite): comprueba que en
    PostgreSQL se tome el camino del COPY y no el de fila a fila.
    """
    from apps.victimas.management.commands import cargar_fechas_caracterizacion as mod

    ruta = f"{mod.__name__}.connection"
    with mock.patch(ruta) as conexion:
        conexion.vendor = "postgresql"
        assert mod.Command()._hay_copy is True

    with mock.patch(ruta) as conexion:
        conexion.vendor = "sqlite"
        assert mod.Command()._hay_copy is False


def test_la_regla_de_2_anios_se_evalua_una_sola_vez_y_en_python(fuente):
    """
    La vigencia se decide con `debe_recaracterizarse()` y al SQL solo viaja el
    booleano ya resuelto. Traducir la regla a SQL daría dos versiones de la misma
    norma en dos lenguajes, y el día que difieran nadie sabría cuál manda.
    """
    import inspect
    from apps.victimas.management.commands import cargar_fechas_caracterizacion as mod

    fuente_sql = "".join(
        linea for linea in inspect.getsource(mod).splitlines(keepends=True)
        if "UPDATE" in linea or "COPY" in linea or "SELECT" in linea)
    for pista in ("INTERVAL", "AGE(", "NOW() -", "CURRENT_DATE -", "EXTRACT"):
        assert pista not in fuente_sql.upper(), (
            f"El SQL calcula fechas ({pista}): la regla de los 2 años quedaría "
            f"duplicada. Debe llegar resuelta desde debe_recaracterizarse().")
