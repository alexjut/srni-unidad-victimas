"""
Los pasos 4-6: validadores, hechos victimizantes y marca de encuestado.

De `GIC_N_VALIDADORESXPERSONA` salen dos columnas que hoy están vacías en todo lo
que SICAV escribe: el `ESTADO_RUV` de cada persona (el `PRE_VALOR` del validador 1,
`src_GIC_N_CARACTERIZACION.sql:3905`) y los `HECHO_VICTIMIZANTE_1..14` (los
validadores 101..114, `:3906` y siguientes). El hogar llega al legacy sin ellos,
pero llega mudo.

Lo que estos tests protegen, en orden de qué tan caro sale equivocarse:

1. **El cruce de hechos NO es el número del código.** Los dos catálogos tienen 14
   entradas en orden distinto y siete coinciden de casualidad. El mapeo "obvio"
   escribe el hecho equivocado en las otras siete, sin error visible.
2. **Los procedures no validan su entrada ni son idempotentes.** Un valor fuera de
   dominio inserta una fila con `VAL_IDVALIDADOR` NULL; una llamada repetida
   duplica la fila y rompe el reporte con ORA-01427.
3. **El orden respecto de las respuestas.** Los validadores tienen que estar antes,
   o `SP_INS_ETNIA_ARES` no deriva las marcas del hogar.
"""
import datetime

import pytest

from apps.sincronizacion.oracle import catalogos, mapeo, procedimientos as P
from apps.sincronizacion.oracle import verificacion as V

pytestmark = pytest.mark.django_db


class UsuarioFalso:
    codigo_usuario = 'ENC001'
    pk = 1


class MiembroFalso:
    """Lo mínimo que `MiembroHogar` le da a estos pasos."""

    def __init__(self, *, es_autorizado=False, tipo_persona='5004',
                 estado_inclusion='INCLUIDO'):
        self.pk = 1
        self.es_autorizado = es_autorizado
        self.tipo_persona = tipo_persona
        self.estado_inclusion = estado_inclusion
        self.victima = None


def _resolver(estricto=True):
    return mapeo.ResolverCatalogos(estricto=estricto, usuario_servicio_id=999999,
                                   perfil_servicio_id=1190)


# ── 1. El cruce de hechos, que es donde se pierde el dato en silencio ────────

def test_el_hecho_no_se_cruza_por_el_numero_del_codigo():
    """
    HV01 es 'Desplazamiento forzado' y en Oracle el 1 es 'Acto terrorista'.

    Este es el test que importa de todo el archivo. Los dos catálogos tienen
    catorce entradas y los dos numeran de 1 a 14, así que quitarle el prefijo al
    código SICAV *parece* funcionar — y `GIC_INSERT_VALIDADOR_HECHO_AUX` acepta
    cualquier entero de 1 a 14 sin chistar. El resultado sería un reporte que
    dice 'ACTO TERRORISTA' en la fila de una persona desplazada.

    Los cinco primeros son justamente los que NO coinciden.
    """
    esperado = {'HV01': 5, 'HV02': 1, 'HV03': 2, 'HV04': 3, 'HV05': 4}
    for codigo, id_hecho in esperado.items():
        assert catalogos.HECHO_VICTIMIZANTE[codigo] == id_hecho
        # Y explícitamente: NO es el número del código.
        assert catalogos.HECHO_VICTIMIZANTE[codigo] != int(codigo[2:])


def test_el_desplazamiento_forzado_cruza_al_5_que_es_el_que_dispara_el_506():
    """
    El desplazamiento es el único hecho con consecuencia en cadena: deja el
    validador 105 y con él `GIC_INSERT_VALIDADOR_ARES` crea el 506 del hogar.
    Escribirlo con otro número no solo pierde el hecho de la persona: también
    pierde la marca del hogar entero.
    """
    assert catalogos.HECHO_VICTIMIZANTE['HV01'] == 5
    assert P.validador_de_hecho(5) == 105


def test_los_catorce_hechos_cruzan_y_ninguno_se_repite():
    """Catorce códigos SICAV → catorce ids Oracle distintos, sin huecos."""
    valores = list(catalogos.HECHO_VICTIMIZANTE.values())
    assert len(catalogos.HECHO_VICTIMIZANTE) == 14
    assert sorted(valores) == list(range(P.HECHO_MINIMO, P.HECHO_MAXIMO + 1))


def test_el_unico_cruce_aproximado_esta_declarado_como_tal():
    """
    'Confinamiento' no existe en el catálogo del legacy (congelado en 2015) y se
    escribe como 'Otros'. Es una pérdida de precisión consciente, y tiene que
    poder informarse en cada corrida — no vivir solo en un comentario.
    """
    assert set(catalogos.HECHO_VICTIMIZANTE_APROXIMADO) == {'HV13'}
    assert catalogos.HECHO_VICTIMIZANTE['HV13'] == 13

    class _Cat:
        codigo = 'HV13'

    assert 'Confinamiento' in _resolver().hecho_es_aproximado(_Cat())

    class _Otro:
        codigo = 'HV01'

    assert _resolver().hecho_es_aproximado(_Otro()) == ''


def test_un_hecho_sin_cruce_lanza_en_vez_de_aproximar():
    class _Cat:
        codigo = 'HV99'

    with pytest.raises(mapeo.MapeoDesconocido):
        _resolver().resolver_id_hecho(_Cat())


# ── 2. Los dominios que el procedure NO comprueba ────────────────────────────

def test_un_tipo_de_persona_fuera_de_dominio_no_llega_a_oracle():
    """
    El procedure no rechaza el valor: deja su variable local en NULL y hace el
    INSERT igual. La fila queda con `VAL_IDVALIDADOR` NULL y esa persona no tiene
    tipo en ningún reporte. Si no se comprueba de este lado, no lo comprueba nadie.
    """
    with pytest.raises(mapeo.MapeoDesconocido) as exc:
        _resolver().resolver_validador_tipo_persona(
            MiembroFalso(tipo_persona='9999'))
    assert 'VAL_IDVALIDADOR NULL' in str(exc.value)


def test_los_cuatro_tipos_de_persona_de_sicav_son_los_que_oracle_homologa():
    """
    `MiembroHogar.TIPO_PERSONA` y el `IF` del procedure tienen que decir lo mismo.
    Si alguien agrega un choice en SICAV sin agregarlo allá, este test lo caza.
    """
    from apps.hogares.models import MiembroHogar

    de_sicav = {c for c, _ in MiembroHogar.TIPO_PERSONA}
    assert de_sicav == set(P.VALIDADORES_TIPO_PERSONA)


def test_el_estado_ruv_usa_el_mismo_dominio_de_dos_literales_que_per_estado():
    incluido = mapeo.binds_validador_hogar(
        '999999-A', 5, miembro=MiembroFalso(estado_inclusion='INCLUIDO'),
        catalogos=_resolver())
    no_incluido = mapeo.binds_validador_hogar(
        '999999-A', 5, miembro=MiembroFalso(estado_inclusion='NO_VERIFICADO'),
        catalogos=_resolver())

    assert incluido['validador'] == 'INCLUIDO'
    assert no_incluido['validador'] == 'NO INCLUIDO'
    for valor in (incluido['validador'], no_incluido['validador']):
        assert valor in P.VALIDADORES_ESTADO_RUV


def test_el_jefe_es_el_autorizado_y_solo_el():
    jefe = mapeo.binds_validador_parent(
        '999999-A', 5, miembro=MiembroFalso(es_autorizado=True),
        catalogos=_resolver())
    otro = mapeo.binds_validador_parent(
        '999999-A', 6, miembro=MiembroFalso(es_autorizado=False),
        catalogos=_resolver())

    assert jefe['validador'] == P.VALIDADOR_JEFE == 'JEFE'
    assert otro['validador'] == P.VALIDADOR_NO_JEFE == 'NO JEFE'


def test_la_fecha_del_hecho_va_como_texto_y_sin_fecha_va_vacia():
    """La columna es NVARCHAR2(20), no DATE: lo que se manda es una cadena."""
    class _Hecho:
        def __init__(self, fecha):
            self.fecha_hecho = fecha
            self.hecho = type('C', (), {'codigo': 'HV01'})()

    con = mapeo.binds_validador_hecho(
        '999999-A', 5, hecho=_Hecho(datetime.date(2015, 3, 9)), catalogos=_resolver())
    sin = mapeo.binds_validador_hecho(
        '999999-A', 5, hecho=_Hecho(None), catalogos=_resolver())

    assert con['fecha_hecho'] == '09/03/2015'
    assert sin['fecha_hecho'] == ''
    assert con['id_hecho'] == 5  # HV01 = desplazamiento = 5, no 1


# ── 3. La verificación: lo que detecta que el procedure se tragó el error ────

class CursorValidadores:
    """Devuelve las filas de GIC_N_VALIDADORESXPERSONA que se le carguen."""

    def __init__(self, filas):
        self.filas = filas
        self._ultimo = None

    def execute(self, sql, binds=None):
        self._ultimo = sql.lower()

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return (len(self.filas),)


def _verificar(filas, *, estado='INCLUIDO', tipo='5001', jefe='JEFE'):
    return V.verificar_validadores(
        CursorValidadores(filas), hog_codigo='999999-A', per_idpersona=5,
        estado_esperado=estado, tipo_persona_esperado=tipo, jefe_esperado=jefe)


def test_los_cuatro_validadores_completos_verifican():
    ok, detalle = _verificar([(1, 'INCLUIDO'), (5001, 'AUTORIZADO'),
                              (5005, '1190'), (20, 'JEFE')])
    assert ok, detalle


def test_falta_uno_y_no_verifica():
    ok, detalle = _verificar([(1, 'INCLUIDO'), (5001, 'AUTORIZADO'), (5005, '1190')])
    assert not ok
    assert detalle['error'] == 'validador_faltante'
    assert detalle['val_idvalidador'] == 20


def test_un_estado_ruv_duplicado_se_detecta_porque_rompe_el_reporte():
    """
    El reporte lee el estado con una subconsulta escalar
    (`SELECT PRE_VALOR … WHERE VAL_IDVALIDADOR = 1`). Con dos filas eso no
    devuelve el dato: devuelve ORA-01427. Y los procedures no tienen nada que lo
    impida — la tabla no tiene PK ni UNIQUE.
    """
    ok, detalle = _verificar([(1, 'INCLUIDO'), (1, 'INCLUIDO'),
                              (5001, 'AUTORIZADO'), (5005, '1190'), (20, 'JEFE')])
    assert not ok
    assert detalle['error'] == 'validador_duplicado'
    assert 'ORA-01427' in detalle['motivo']


def test_el_texto_del_estado_se_compara_no_solo_su_existencia():
    """
    El procedure pone `VAL_IDVALIDADOR = 1` para INCLUIDO **y** para NO INCLUIDO
    —las dos ramas del `IF` asignan lo mismo—, así que mirar el id no distingue
    nada. Lo que el reporte imprime es el `PRE_VALOR`.
    """
    ok, detalle = _verificar([(1, 'NO INCLUIDO'), (5001, 'AUTORIZADO'),
                              (5005, '1190'), (20, 'JEFE')],
                             estado='INCLUIDO')
    assert not ok
    assert detalle['error'] == 'validador_con_texto_distinto'
    assert detalle['esperado'] == 'INCLUIDO'
    assert detalle['encontrado'] == 'NO INCLUIDO'


def test_una_fila_con_validador_nulo_se_reporta():
    """Es la huella de un bind fuera de dominio: el INSERT se hizo igual."""
    ok, detalle = _verificar([(None, 'ALGO'), (1, 'INCLUIDO'),
                              (5001, 'AUTORIZADO'), (5005, '1190'), (20, 'JEFE')])
    assert not ok
    assert detalle['error'] == 'validador_nulo'


def test_el_hecho_no_escrito_se_distingue_del_escrito():
    class _Cursor:
        def __init__(self, n):
            self.n = n

        def execute(self, sql, binds=None):
            pass

        def fetchone(self):
            return (self.n,)

    ok, _ = V.verificar_hecho(_Cursor(1), hog_codigo='999999-A',
                              per_idpersona=5, id_hecho=5)
    assert ok

    ok, detalle = V.verificar_hecho(_Cursor(0), hog_codigo='999999-A',
                                    per_idpersona=5, id_hecho=5)
    assert not ok
    assert detalle['error'] == 'hecho_no_escrito'
    assert detalle['val_idvalidador'] == 105


def test_el_encuestado_exige_el_literal_SI_completo():
    """
    El reporte hace `CASE WHEN MH.PER_ENCUESTADA = 'SI'`. Con 'S' —que es lo que
    se mandaba antes— nadie figura como la persona entrevistada.
    """
    class _Cursor:
        def __init__(self, valor):
            self.valor = valor

        def execute(self, sql, binds=None):
            pass

        def fetchone(self):
            return (self.valor,)

    ok, _ = V.verificar_encuestado(_Cursor('SI'), hog_codigo='999999-A',
                                   per_idpersona=5)
    assert ok

    ok, detalle = V.verificar_encuestado(_Cursor('S'), hog_codigo='999999-A',
                                         per_idpersona=5)
    assert not ok
    assert detalle['error'] == 'no_marcado_encuestado'


# ── 4. El cierre, que se verificaba con un parámetro que no existía ──────────

def test_verificar_cierre_acepta_el_tipo_que_el_escritor_le_pasa():
    """
    `escritor.paso_cierre` llamaba a `verificar_cierre(..., tipo=tipo)` y la
    función no tenía ese parámetro: `TypeError` en la ruta confirmada, la única
    donde se verifica. Los tests, todos en DRY-RUN, no llegaban nunca hasta ahí.
    """
    from apps.sincronizacion.tests.test_capitulos_y_cierre import CursorFalso

    ok, detalle = V.verificar_cierre(CursorFalso(), hog_codigo='999999-A',
                                     tipo=P.CIERRE_CERRADA)
    assert ok, detalle


def test_un_hogar_anulado_se_verifica_contra_ANULADA_no_contra_CERRADA():
    """
    Anular es el camino para deshacer una prueba, y también archiva las
    respuestas. Verificarlo contra el literal 'CERRADA' lo daba por fallido
    siempre — que es como quedó el piloto del 28-jul al anularse.
    """
    from apps.sincronizacion.tests.test_capitulos_y_cierre import CursorFalso

    ok, detalle = V.verificar_cierre(CursorFalso(estado='ANULADA'),
                                     hog_codigo='999999-A', tipo=P.CIERRE_ANULADA)
    assert ok, detalle
    assert detalle['estado_esperado'] == 'ANULADA'


def test_aplazar_no_exige_respuestas_en_la_tabla_definitiva():
    """`IF TIPO_APLAZAMIENTO NOT IN ('5','3')`: aplazar y reabrir NO archivan."""
    from apps.sincronizacion.tests.test_capitulos_y_cierre import CursorFalso

    ok, _ = V.verificar_cierre(CursorFalso(estado='APLAZADA', definitivas=0),
                               hog_codigo='999999-A', tipo=P.CIERRE_APLAZADA)
    assert ok


# ── 5. El escritor: idempotencia y orden ─────────────────────────────────────

def _escritor(cursor):
    from apps.sincronizacion.oracle.escritor import EscritorOracle

    e = EscritorOracle(confirmar=True, destino='produccion', catalogos=_resolver())
    e._cursor = cursor
    e._ya_verificado = lambda *a, **k: False
    e._registro_verificado = lambda *a, **k: None
    e._registrar = lambda *a, **k: None
    return e


class CursorConValidadores(CursorValidadores):
    """Cursor que además responde a los COUNT del chequeo previo."""

    def __init__(self, filas):
        super().__init__(filas)
        self.sql_ejecutados = []

    def execute(self, sql, binds=None):
        self.sql_ejecutados.append(sql)
        self._ultimo = sql.lower()

    def fetchone(self):
        # Los COUNT del pre-chequeo: cuántas filas hay del/los validador(es) pedidos.
        s = self._ultimo or ''
        if 'val_idvalidador in (' in s:
            n = len([f for f in self.filas
                     if f[0] in set(P.VALIDADORES_PARENTESCO.values())])
        elif 'val_idvalidador = :v' in s:
            n = len([f for f in self.filas if f[0] == P.VALIDADOR_ESTADO_RUV])
        else:
            n = len(self.filas)
        return (n,)


def test_si_el_validador_ya_esta_no_se_vuelve_a_invocar():
    """
    Ninguno de los dos procedures es idempotente y la tabla no tiene UNIQUE: un
    reintento sin este chequeo deja el validador duplicado, y un estado duplicado
    rompe el reporte. Por eso se pregunta ANTES.
    """
    completo = [(1, 'INCLUIDO'), (5001, 'AUTORIZADO'), (5005, '1190'), (20, 'JEFE')]
    cursor = CursorConValidadores(completo)
    r = _escritor(cursor).paso_validador(
        _HogarFalso(), MiembroFalso(es_autorizado=True, tipo_persona='5001'),
        hog_codigo='999999-A', per_idpersona=5)

    assert r.detalle['ya_estaban'] == {'estado_ruv': True, 'parentesco': True}
    assert r.bloque == ''  # no se armó ningún bloque PL/SQL: no se invocó nada
    assert not any('INSERT' in s.upper() for s in cursor.sql_ejecutados)


def test_si_el_validador_no_esta_si_se_invoca():
    cursor = CursorConValidadores([])
    r = _escritor(cursor).paso_validador(
        _HogarFalso(), MiembroFalso(es_autorizado=True, tipo_persona='5001'),
        hog_codigo='999999-A', per_idpersona=5)

    assert 'ya_estaban' not in r.detalle
    assert 'GIC_INSERT_VALIDADOR_HOGAR' in r.bloque
    assert 'GIC_INSERT_VALIDADOR_PARENT' in r.bloque


class _HogarFalso:
    pk = 1
    codigo_hogar = 'SICAV-1'
    creado_por = None


def test_el_origen_del_paso_hecho_cabe_en_la_columna_del_ledger():
    """
    `MiembroHogar.id` y `HechoVictima.id` son UUID: 'miembro:hecho' mide 73
    caracteres y `origen_id` admite 64. En PostgreSQL eso es un DataError en el
    PRIMER hecho — o sea después de que los validadores ya quedaron commiteados en
    Oracle, con el hogar a medias y sin rollback posible.
    """
    import uuid

    from apps.sincronizacion.models import RegistroEscrituraOracle

    class _Hecho:
        pk = uuid.uuid4()
        fecha_hecho = None
        hecho = type('C', (), {'codigo': 'HV01'})()

    limite = RegistroEscrituraOracle._meta.get_field('origen_id').max_length
    r = _escritor(CursorConValidadores([])).paso_hecho(
        _HogarFalso(), MiembroFalso(), _Hecho(),
        hog_codigo='999999-A', per_idpersona=5)

    assert len(r.origen_id) <= limite


def test_no_se_puede_escribir_de_verdad_con_un_resolver_no_estricto():
    """
    Un resolver no estricto devuelve marcadores '‹PEND:...›' en vez de lanzar.
    Con `confirmar=True` esos marcadores acabarían DENTRO de columnas de
    producción, y nada daría error: los procedures no validan nada y se tragan sus
    excepciones. Se cierra en el constructor.
    """
    from apps.sincronizacion.oracle.escritor import EscritorOracle

    with pytest.raises(ValueError) as exc:
        EscritorOracle(confirmar=True, destino='produccion',
                       catalogos=_resolver(estricto=False))
    assert 'ESTRICTO' in str(exc.value)


# (El orden de los pasos sobre un hogar real se prueba en
#  test_cargar_hogar_demo_oracle.py, que ya monta el escenario completo.)
