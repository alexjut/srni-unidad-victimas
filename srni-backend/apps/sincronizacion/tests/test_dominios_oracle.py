"""
Los valores que SICAV manda al legacy tienen que estar en el dominio que el legacy
entiende. Ninguno de estos campos tiene CHECK en Oracle: un valor inventado NO
falla, simplemente hace que la fila desaparezca de los reportes.

Por eso van con test: son errores que no avisan.

Los cinco casos vienen del análisis del volcado del 2-ago
(`docs/oracle-legacy/escritura_legacy_analisis.md`).
"""
import datetime

import pytest

from apps.sincronizacion.oracle import mapeo

pytestmark = pytest.mark.django_db


class UsuarioFalso:
    def __init__(self, codigo='ENC001'):
        self.codigo_usuario = codigo
        self.pk = 7


class CatalogosFalsos:
    """Solo lo que `binds_persona` y `binds_miembro` le piden."""
    def resolver_tdoc(self, tipo):
        return 1

    def resolver_relac_de_miembro(self, miembro):
        return 1

    def resolver_t_victima(self, miembro):
        return None

    def resolver_extra_persona(self, nombre, miembro=None):
        return mapeo.ResolverCatalogos.resolver_extra_persona(self, nombre, miembro)

    def id_usuario_servicio(self):
        return 999999


class MiembroFalso:
    def __init__(self, **kw):
        self.victima = kw.get('victima')
        self.nombre_completo = kw.get('nombre_completo', 'ANA MARIA DIAZ SOTO')
        self.numero_documento = kw.get('numero_documento', '123456')
        self.tipo_documento = kw.get('tipo_documento')
        self.fecha_nacimiento = kw.get('fecha_nacimiento', datetime.date(1990, 1, 1))
        self.es_autorizado = kw.get('es_autorizado', False)
        self.estado_inclusion = kw.get('estado_inclusion', '')
        self.parentesco = ''
        self.pk = kw.get('pk', 1)


class VictimaFalsa:
    def __init__(self, cons_persona=None, estado_ruv='INCLUIDO'):
        self.cons_persona = cons_persona
        self.estado_ruv = estado_ruv
        self.primer_nombre = 'ANA'
        self.segundo_nombre = 'MARIA'
        self.primer_apellido = 'DIAZ'
        self.segundo_apellido = 'SOTO'
        self.numero_documento = '123456'
        self.fecha_nacimiento = '1990-01-01'
        self.tipo_documento = None


def _binds(miembro):
    return mapeo.binds_persona(miembro, user=UsuarioFalso(),
                               estado_oracle='ACTIVA', catalogos=CatalogosFalsos())


# ── PER_ESTADO ───────────────────────────────────────────────────────────────

def test_el_estado_de_la_persona_no_es_el_del_hogar():
    """
    Se mandaba 'ACTIVA', que es el estado del HOGAR. El dominio de `PER_ESTADO` es
    INCLUIDO / NO INCLUIDO: con 'ACTIVA' la persona quedaba en la tabla pero
    `GIC_OBTENER_PERSONAS` no la devolvía nunca.
    """
    binds = _binds(MiembroFalso(estado_inclusion='INCLUIDO'))
    assert binds['estado'] == 'INCLUIDO'
    assert binds['estado'] != 'ACTIVA'


def test_el_estado_sale_del_dato_que_sicav_ya_tiene():
    assert mapeo.estado_persona_oracle(
        MiembroFalso(estado_inclusion='INCLUIDO')) == 'INCLUIDO'
    assert mapeo.estado_persona_oracle(
        MiembroFalso(estado_inclusion='NO_INCLUIDO')) == 'NO INCLUIDO'
    # Alta manual: no se verificó contra el RUV. El legacy solo sabe representar
    # dos valores, así que va como NO INCLUIDO y el matiz queda en SICAV.
    assert mapeo.estado_persona_oracle(
        MiembroFalso(estado_inclusion='NO_VERIFICADO')) == 'NO INCLUIDO'


def test_una_victima_incluida_del_padron_tambien_cuenta():
    m = MiembroFalso(estado_inclusion='', victima=VictimaFalsa(estado_ruv='INCLUIDO'))
    assert mapeo.estado_persona_oracle(m) == 'INCLUIDO'


# ── PER_IDMODELOINT (idpermi) ────────────────────────────────────────────────

def test_el_puente_al_modelo_integrado_nunca_va_en_null():
    """
    Iba NULL. El DEFAULT 0 de la columna no aplica —el INSERT es posicional— y el
    job que resuelve el enlace busca `WHERE PER_IDMODELOINT = 0`: una fila en NULL
    no la ve nunca y queda fuera del cruce con el RUV para siempre.
    """
    binds = _binds(MiembroFalso())
    assert binds['idpermi'] is not None
    assert binds['idpermi'] == 0


def test_si_la_persona_viene_del_padron_el_puente_va_resuelto():
    """
    Se escribe el `cons_persona` en vez de 0, para no depender del job.

    🔴 La justificación que había aquí era falsa: afirmaba que el job cruza contra
    `M_CARACT_TABLA_RA_PER.CONS_PERONA` «que es de donde lo sacamos». Esa columna
    resultó ser un contador de filas (medido el 11-ago-2026,
    `docs/oracle-legacy/join_caracterizacion_roto.md`) y no es el origen de
    `cons_persona`, que viene de `GIC_PERSONA.PER_IDPERSONA`.

    Este test fija el COMPORTAMIENTO —se escribe el valor, no 0—, que no cambia.
    Lo que queda por verificar es si `PER_IDMODELOINT` es el mismo espacio de
    identificadores; ver la nota en `mapeo.resolver_idpermi`.
    """
    binds = _binds(MiembroFalso(victima=VictimaFalsa(cons_persona=6882450)))
    assert binds['idpermi'] == 6882450


def test_los_otros_extras_si_van_en_null():
    binds = _binds(MiembroFalso())
    for extra in ('id_declar', 'id_pers_fuente', 'id_siniestro'):
        assert binds[extra] is None


# ── PER_ENCUESTADA ───────────────────────────────────────────────────────────

def test_la_marca_de_encuestado_usa_el_literal_que_el_legacy_compara():
    """
    Iba 'S' y el legacy compara contra 'SI'. Con 'S', el campo JEFE_HOGAR de los
    reportes salía 'NO' para todo el hogar.
    """
    binds = mapeo.binds_miembro('999999-ABCDE', 42, user=UsuarioFalso(),
                                catalogos=CatalogosFalsos(),
                                miembro=MiembroFalso(es_autorizado=True))
    assert binds['encuestada'] == 'SI'


def test_solo_el_autorizado_figura_como_entrevistado():
    """Marcar a los cinco miembros es una afirmación falsa sobre cómo se levantó."""
    binds = mapeo.binds_miembro('999999-ABCDE', 42, user=UsuarioFalso(),
                                catalogos=CatalogosFalsos(),
                                miembro=MiembroFalso(es_autorizado=False))
    assert binds['encuestada'] == 'NO'


# ── USU_USUARIOCREACION ──────────────────────────────────────────────────────

def test_sin_usuario_falla_fuerte_en_vez_de_mandar_vacio():
    """
    En Oracle la cadena vacía ES null, y la columna es NOT NULL: el INSERT moría
    con ORA-01400 dentro del procedure, cuyo WHEN OTHERS se lo tragaba. La persona
    no se escribía y el paso podía darse por bueno.
    """
    class SinCodigo:
        codigo_usuario = ''
        pk = ''

    with pytest.raises(mapeo.UsuarioSinResolver):
        _binds(MiembroFalso())._ = None if False else mapeo.binds_persona(
            MiembroFalso(), user=SinCodigo(), estado_oracle='ACTIVA',
            catalogos=CatalogosFalsos())


def test_con_usuario_normal_no_molesta():
    assert _binds(MiembroFalso())['usuario'] == 'ENC001'


# ── USU_FCREACION ────────────────────────────────────────────────────────────

def test_la_fecha_va_en_hora_local_y_sin_zona():
    """
    `USU_FCREACION` es un DATE de Oracle y no guarda zona. Mandar el datetime aware
    de Django escribía la hora UTC —cinco horas en el futuro— en una columna que
    todos los reportes leen como hora de Colombia.
    """
    from django.utils import timezone

    valor = _binds(MiembroFalso())['usu_fcreacion']
    assert valor.tzinfo is None, 'un datetime con zona escribe la hora corrida'
    esperado = timezone.localtime(timezone.now()).replace(tzinfo=None)
    assert abs((valor - esperado).total_seconds()) < 60
