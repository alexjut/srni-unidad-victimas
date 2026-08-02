"""
La guarda que impide fundir dos caracterizaciones en un mismo hogar del legacy.

`GIC_INSERT_HOGAR1` **no siempre crea un hogar**. Solo inserta si el `ID_USUARIO`
no tiene ninguno en estado ACTIVA; si ya tiene uno, no crea nada y devuelve en
`MARCADOR` **el código del hogar viejo**. Cuando sí crea, devuelve `MARCADOR='1'`.
La semántica está invertida respecto de lo que uno esperaría.

La versión anterior tomaba ese código previo como si fuera el hogar recién
escrito, y a partir de ahí colgaba de él las personas, el territorio y las
respuestas del hogar nuevo.

No queda en un dato mezclado: escribir una sola respuesta en un hogar ajeno
dispara `SP_INS_ETNIA_ARES`, que arranca con dos `DELETE` sobre
`GIC_N_VALIDADORESXPERSONA` filtrando **solo por HOG_CODIGO** — borra el estado
en el RUV y los hechos victimizantes de ese hogar. Sobre datos reales de la
UARIV, y sin rollback: los procedures hacen COMMIT interno.
"""
import datetime

import pytest

from apps.sincronizacion.oracle import verificacion as V

pytestmark = pytest.mark.django_db


class CursorFalso:
    """Cursor mínimo que devuelve lo que se le programe, por consulta."""

    def __init__(self, hogares_nuevos=(), sysdate=None):
        self.hogares_nuevos = list(hogares_nuevos)
        self.sysdate = sysdate or datetime.datetime(2026, 8, 2, 18, 0)
        self._ultimo = None

    def execute(self, sql, binds=None):
        self._ultimo = ('sysdate' if 'SYSDATE' in sql.upper() else 'hogares')

    def fetchone(self):
        if self._ultimo == 'sysdate':
            return (self.sysdate,)
        return self.hogares_nuevos[0] if self.hogares_nuevos else None

    def fetchall(self):
        return self.hogares_nuevos


T0 = datetime.datetime(2026, 8, 2, 17, 59)


# ── el caso que fundía hogares ───────────────────────────────────────────────

def test_un_marcador_distinto_de_1_significa_que_NO_se_creo_el_hogar():
    """
    El defecto exacto: se aceptaba ese código como el hogar nuestro.
    """
    ok, detalle = V.verificar_hogar(
        CursorFalso(), id_usuario=999999, marcador='999999-2W832', creado_desde=T0)

    assert ok is False, 'aceptar ese código funde dos caracterizaciones'
    assert detalle['error'] == 'hogar_no_creado'
    assert detalle['codigo_preexistente'] == '999999-2W832'
    # El motivo tiene que explicar qué pasó, no solo que falló.
    assert 'ACTIVA' in detalle['motivo']


def test_con_marcador_1_y_un_hogar_nuevo_se_acepta():
    """El camino bueno: el procedure creó, y aparece un hogar nuevo en la ventana."""
    cursor = CursorFalso(hogares_nuevos=[('999999-ABCDE', datetime.datetime(2026, 8, 2, 18, 0))])
    ok, detalle = V.verificar_hogar(cursor, id_usuario=999999, marcador='1', creado_desde=T0)

    assert ok is True
    assert detalle['hog_codigo'] == '999999-ABCDE'
    assert detalle['resuelto_por'] == 'usuario+ventana'


# ── la ventana temporal ──────────────────────────────────────────────────────

def test_sin_ventana_no_se_puede_afirmar_que_el_hogar_es_nuestro():
    """
    Antes se resolvía con "el ACTIVA más reciente del usuario". Con un ID_USUARIO
    compartido, ese puede ser el hogar de otro encuestador.
    """
    ok, detalle = V.verificar_hogar(
        CursorFalso(), id_usuario=999999, marcador='1', creado_desde=None)
    assert ok is False
    assert detalle['error'] == 'sin_ventana_temporal'


def test_si_no_aparece_ningun_hogar_nuevo_falla():
    """El procedure dijo que creó, pero no hay nada. No se inventa un código."""
    ok, detalle = V.verificar_hogar(
        CursorFalso(hogares_nuevos=[]), id_usuario=999999, marcador='1', creado_desde=T0)
    assert ok is False
    assert detalle['error'] == 'hogar_no_encontrado'


def test_dos_hogares_nuevos_a_la_vez_es_ambiguo_y_se_rechaza():
    """
    Pasa si dos escrituras corren en paralelo con el mismo ID_USUARIO. Elegir uno
    "por si acaso" es exactamente cómo se cuelgan las personas del hogar equivocado.
    """
    cursor = CursorFalso(hogares_nuevos=[
        ('999999-AAAAA', datetime.datetime(2026, 8, 2, 18, 1)),
        ('999999-BBBBB', datetime.datetime(2026, 8, 2, 18, 0)),
    ])
    ok, detalle = V.verificar_hogar(cursor, id_usuario=999999, marcador='1', creado_desde=T0)

    assert ok is False
    assert detalle['error'] == 'hogar_ambiguo'
    assert len(detalle['candidatos']) == 2


def test_el_reloj_es_el_de_oracle_no_el_nuestro():
    """
    Entre el servidor de aplicaciones y la base hay horas de diferencia: una
    ventana calculada con el reloj equivocado deja pasar hogares ajenos o rechaza
    los propios.
    """
    esperado = datetime.datetime(2026, 8, 2, 12, 34)
    assert V.reloj_oracle(CursorFalso(sysdate=esperado)) == esperado


# ── el aborte, que es la parte que evita el daño ─────────────────────────────

def test_un_hogar_no_verificado_aborta_la_escritura_entera():
    """
    Lo que de verdad protege: sin HOG_CODIGO propio, NO se escribe una sola
    persona ni una sola respuesta. Seguir sería colgarlas de un hogar ajeno.
    """
    from apps.sincronizacion.models import EstadoPaso
    from apps.sincronizacion.oracle.escritor import EscritorOracle, ResultadoPaso
    from apps.sincronizacion.models import PasoEscritura

    class HogarFalso:
        pk = 1
        codigo_hogar = 'SICAV-1'
        creado_por = None

        class _sesiones:
            @staticmethod
            def select_related(*a, **k):
                class _q:
                    @staticmethod
                    def first():
                        return None
                return _q
        sesiones = _sesiones

    from apps.sincronizacion.oracle.mapeo import ResolverCatalogos

    escritor = EscritorOracle(
        confirmar=True, destino='produccion',
        catalogos=ResolverCatalogos(estricto=True, usuario_servicio_id=999999))
    escritor.paso_hogar = lambda hogar, **kw: ResultadoPaso(
        PasoEscritura.HOGAR, '1', EstadoPaso.FALLIDO, '',
        {'error': 'hogar_no_creado', 'codigo_preexistente': '999999-2W832'})

    resultado = escritor.procesar_hogar(HogarFalso(), user=None)

    assert resultado.abortado is True
    assert 'no quedó verificado' in resultado.motivo_aborte
    # Un solo paso registrado: el hogar. Ninguna persona, ningún miembro.
    assert len(resultado.pasos) == 1
    assert resultado.resumen()['abortado'] is True
