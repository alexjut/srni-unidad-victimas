"""
Los dos pasos que hacen que un hogar EXISTA para los reportes.

Escribir el hogar, las personas y las respuestas no alcanza: los reportes no leen
`GIC_N_RESPUESTASENCUESTA` (la tabla de trabajo) sino
`GIC_N_RESPUESTASENCUESTA_C` (la definitiva), y las respuestas solo pasan de una a
otra cuando la encuesta se CIERRA con
`SP_ACTUALIZAR_ESTADO_ENCUESTA(hogar, usuario, '4')`.

Y ese cierre tiene una trampa: **solo hace su trabajo si el hogar tiene más de 3
capítulos terminados**. Si no, cae en un `ELSE NULL` literal
(`src_GIC_N_CARACTERIZACION.sql:1630-1631`) y **termina sin error**. Por eso los
capítulos no son burocracia: son la precondición del cierre.
"""
import pytest

from apps.sincronizacion.oracle import mapeo, procedimientos as P
from apps.sincronizacion.oracle import verificacion as V

pytestmark = pytest.mark.django_db


class UsuarioFalso:
    codigo_usuario = 'ENC001'
    pk = 1


class PreguntaFalsa:
    def __init__(self, id_preg):
        self.id_preg = id_preg
        self.codigo_externo = f'P{id_preg}'


class RespuestaFalsa:
    def __init__(self, id_preg):
        self.pregunta = PreguntaFalsa(id_preg)
        self.valor = '1'


# ── los capítulos se derivan de lo que se escribió ───────────────────────────

def test_los_temas_salen_del_catalogo_de_oracle():
    """
    No hay que mantener otro crosswalk: el catálogo ya trae `tem_idtema` por
    pregunta, y el puente `id_preg` es el mismo que ya se usa para escribir.
    """
    from apps.sincronizacion.oracle import catalogos

    cat = catalogos.cargar_respuestas()
    # Dos preguntas reales del catálogo, con su tema.
    ids = [i for i in list(cat['preguntas'])[:2]]
    esperados = {int(cat['preguntas'][i]['tem_idtema']) for i in ids
                 if cat['preguntas'][i].get('tem_idtema') is not None}

    temas = mapeo.temas_de_respuestas(
        [RespuestaFalsa(i) for i in ids], mapeo.ResolverCatalogos(estricto=False))
    assert temas == esperados


def test_una_pregunta_sin_puente_no_declara_capitulo():
    """
    Si la respuesta no se pudo escribir, tampoco corresponde declarar terminado su
    capítulo. Sería afirmar un trabajo que no quedó en la base.
    """
    temas = mapeo.temas_de_respuestas(
        [RespuestaFalsa(None)], mapeo.ResolverCatalogos(estricto=False))
    assert temas == set()


def test_los_binds_del_capitulo_son_los_tres_del_procedure():
    binds = mapeo.binds_capitulo('999999-ABCDE', 7, user=UsuarioFalso())
    assert binds == {'pcodhogar': '999999-ABCDE', 'pidtema': 7, 'pusuario': 'ENC001'}


# ── el cierre ────────────────────────────────────────────────────────────────

def test_el_cierre_usa_el_codigo_4_que_es_el_unico_que_mueve_las_respuestas():
    binds = mapeo.binds_cierre('999999-ABCDE', user=UsuarioFalso())
    assert binds['tipo_aplazamiento'] == P.CIERRE_CERRADA == '4'


def test_se_declara_el_procedure_correcto_y_no_el_trampa():
    """
    `CERRAR_ENCUESTA` existe y es tentador por el nombre, pero solo hace
    `UPDATE ESTADO='CERRADA'`: deja el hogar marcado como cerrado con CERO
    respuestas en la definitiva. Para los reportes, un hogar que no existe.
    """
    assert P.SP_ACTUALIZAR_ESTADO_ENCUESTA.nombre == 'SP_ACTUALIZAR_ESTADO_ENCUESTA'
    assert 'CERRAR_ENCUESTA' not in P.SP_ACTUALIZAR_ESTADO_ENCUESTA.nombre


def test_el_minimo_de_capitulos_es_el_del_procedure():
    """`IF totalCT > 3` ⇒ hacen falta 4. Un off-by-one aquí no daría error: el
    cierre simplemente no cerraría, en silencio."""
    assert P.CAPITULOS_MINIMOS_PARA_CERRAR == 4


# ── la verificación, que es lo que detecta el ELSE NULL ──────────────────────

class CursorFalso:
    def __init__(self, estado='CERRADA', definitivas=12, trabajo=0, capitulos=6):
        self.datos = {'estado': estado, 'definitivas': definitivas,
                      'trabajo': trabajo, 'capitulos': capitulos}
        self._q = None

    def execute(self, sql, binds=None):
        s = sql.lower()
        if 'estado from gic_hogar' in s:
            self._q = 'estado'
        elif 'respuestasencuesta_c' in s:
            self._q = 'definitivas'
        elif 'respuestasencuesta' in s:
            self._q = 'trabajo'
        elif 'capitulos_ter' in s:
            self._q = 'capitulos'

    def fetchone(self):
        return (self.datos[self._q],)


def test_un_cierre_bueno_se_reconoce():
    ok, detalle = V.verificar_cierre(CursorFalso(), hog_codigo='999999-ABCDE')
    assert ok is True
    assert detalle['respuestas_definitivas'] == 12


def test_si_el_procedure_no_cerro_la_verificacion_lo_detecta():
    """
    El caso del `ELSE NULL`: el hogar tiene 2 capítulos, el procedure termina sin
    error y el hogar sigue ACTIVA. Mirar solo el retorno lo daría por cerrado.
    """
    ok, detalle = V.verificar_cierre(
        CursorFalso(estado='ACTIVA', capitulos=2), hog_codigo='999999-ABCDE')
    assert ok is False
    assert detalle['error'] == 'no_cerro'
    assert '2 capítulos' in detalle['motivo']


def test_cerrado_pero_sin_respuestas_tampoco_pasa():
    """
    Lo que deja `CERRAR_ENCUESTA`: estado CERRADA y la tabla definitiva vacía.
    Para los reportes ese hogar no existe, así que no puede darse por bueno.
    """
    ok, detalle = V.verificar_cierre(
        CursorFalso(definitivas=0), hog_codigo='999999-ABCDE')
    assert ok is False
    assert detalle['error'] == 'cerrado_sin_respuestas'


# ── la guarda previa del escritor ────────────────────────────────────────────

def test_el_escritor_no_llama_al_cierre_sin_capitulos_suficientes():
    """
    Se comprueba ANTES de invocar. Llamarlo igual no daría error —el procedure
    termina limpio— y el paso quedaría registrado como ejecutado sobre una
    encuesta que sigue abierta.
    """
    from apps.sincronizacion.models import EstadoPaso
    from apps.sincronizacion.oracle.escritor import EscritorOracle

    class HogarFalso:
        pk = 1
        codigo_hogar = 'SICAV-1'
        creado_por = None

    escritor = EscritorOracle(
        confirmar=True, destino='produccion',
        catalogos=mapeo.ResolverCatalogos(estricto=True, usuario_servicio_id=999999))
    escritor._cursor = CursorFalso(capitulos=2)
    escritor._ya_verificado = lambda *a, **k: False
    registrado = {}
    escritor._registrar = lambda *a, **k: registrado.update(k) or None

    r = escritor.paso_cierre(HogarFalso(), user=UsuarioFalso(),
                             hog_codigo='999999-ABCDE')

    assert r.estado is EstadoPaso.FALLIDO
    assert r.detalle['error'] == 'capitulos_insuficientes'
    assert r.detalle['capitulos_terminados'] == 2
    # Y no se llegó a invocar el procedure: el bloque PL/SQL viene vacío.
    assert r.bloque == ''
