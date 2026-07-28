"""
Tests de la cascada territorial y del paso RESPUESTA — SIN Oracle (DRY-RUN).

Lo que se protege aquí es el bug histórico: GIC_N_RELACION_DT_PUNTO mal poblado
rompe los reportes territoriales de Vivanto/SRNI. Los procedures no avisan (COMMIT
interno + WHEN OTHERS), así que el orden y el valor de cada bind tienen que estar
blindados por test.
"""
import pytest

from apps.sincronizacion.oracle import mapeo, procedimientos as P
from apps.sincronizacion.oracle.mapeo import ResolverCatalogos


# Fila real del volcado: DT CENTRAL(7) / TOLIMA(30) / JORNADAS(13) / ALVARADO(32).
TERRITORIO = {"id_dt": 7, "id_depto": 30, "id_pt": 13, "id_ma": 32}


def test_cascada_tiene_los_cuatro_pasos_en_orden():
    llamadas = mapeo.binds_territorio("HOG-1", TERRITORIO)
    assert [proc.nombre for proc, _ in llamadas] == [
        "GIC_SP_OBDEPTOPORDT",      # el único que INSERTA la fila → debe ir primero
        "GIC_SP_OBTPUNTOATECION",
        "GIC_SP_OBMUNICIPIOATECION",
        "GIC_SP_GUARDAMUNATEN",
    ]


def test_el_primero_es_el_que_inserta():
    # Los otros tres son UPDATE ... WHERE hogarcodigo=X: sin la fila creada por
    # GIC_SP_OBDEPTOPORDT actualizarían 0 filas SIN error y el hogar quedaría sin
    # territorio. Este test fija esa precondición del orden.
    proc, _ = mapeo.binds_territorio("HOG-1", TERRITORIO)[0]
    assert proc.nombre == "GIC_SP_OBDEPTOPORDT"


def test_obtpuntoatencion_recibe_el_id_de_DEPARTAMENTO_no_el_de_dt():
    """
    Regresión de la trampa: el formal se llama Id_DT pero el cuerpo hace
    `SET iddeptoaten = Id_dt` y filtra `T.IDDEPARTAMENTO = pId_DT`. Pasarle el id
    de la DT metería 7 en IDDEPTOATEN en vez de 30 y rompería el join de reportes
    (RL.IDDEPTOATEN = PA.IDDEPARTAMENTO). El bind se llama id_dt (nombre formal),
    pero su VALOR debe ser el departamento.
    """
    llamadas = dict((proc.nombre, binds) for proc, binds in
                    mapeo.binds_territorio("HOG-1", TERRITORIO))
    assert llamadas["GIC_SP_OBTPUNTOATECION"]["id_dt"] == TERRITORIO["id_depto"] == 30
    assert llamadas["GIC_SP_OBTPUNTOATECION"]["id_dt"] != TERRITORIO["id_dt"]
    # …y el primero sí recibe la DT de verdad.
    assert llamadas["GIC_SP_OBDEPTOPORDT"]["id_dt"] == TERRITORIO["id_dt"] == 7


def test_cada_paso_recibe_su_id_y_el_hogar():
    llamadas = dict((proc.nombre, binds) for proc, binds in
                    mapeo.binds_territorio("HOG-1", TERRITORIO))
    assert llamadas["GIC_SP_OBMUNICIPIOATECION"]["id_pt"] == 13
    assert llamadas["GIC_SP_GUARDAMUNATEN"]["id_ma"] == 32
    assert all(b["phogar_codigo"] == "HOG-1" for b in llamadas.values())


def test_bloques_plsql_invocan_por_nombre_formal():
    # El bind conserva el nombre formal (ID_DT) aunque el valor sea el depto.
    proc, binds = mapeo.binds_territorio("HOG-1", TERRITORIO)[1]
    res = P.invocar(proc, binds, confirmar=False)
    assert "GIC_N_CARACTERIZACION.GIC_SP_OBTPUNTOATECION" in res.bloque
    assert "ID_DT => :id_dt" in res.bloque
    assert res.ejecutado is False  # DRY-RUN no ejecuta


# ── RESPUESTA — ids reales donde los hay, pendientes donde no ────────────────
class _Opciones:
    """Stub del related manager: solo se usa .filter(valor=...).first()."""
    def __init__(self, *o): self._o = list(o)
    def filter(self, valor): return _Opciones(*[x for x in self._o if x.valor == valor])
    def first(self): return self._o[0] if self._o else None


class _Opcion:
    def __init__(self, valor, etiqueta):
        self.valor, self.etiqueta = valor, etiqueta


class _Pregunta:
    """Pregunta 5 'Zona de residencia' del volcado real (opción 8 = Cabecera)."""
    tipo = "RADIO"
    id_preg = 5
    codigo_externo = "Z6"
    opciones = _Opciones(_Opcion("1", "Cabecera municipal (donde está la alcaldía)"))


class _Respuesta:
    pk = 1
    miembro_id = None
    valor = "1"
    pregunta = _Pregunta()


def test_respuesta_nivel_hogar_sin_jefe_lanza():
    # Respuesta de hogar (miembro NULL) SIN jefe al que anclarla: debe lanzar, no
    # adivinar un IDPERSONA. (El hogar debe tener un autorizado/es_autorizado.)
    with pytest.raises(mapeo.MapeoPendienteNegocio) as exc:
        mapeo.per_idpersona_de_respuesta(_Respuesta(), {}, ResolverCatalogos(estricto=True))
    assert "PPER_IDPERSONA" in str(exc.value)


def test_respuesta_nivel_hogar_se_ancla_al_jefe():
    # La respuesta de nivel HOGAR (miembro NULL) se ancla al per_idpersona del
    # autorizado/jefe: es quien responde por el hogar. PER_IDPERSONA es nullable en
    # Oracle, así que el jefe es la elección fiel (no un literal inventado).
    assert mapeo.per_idpersona_de_respuesta(
        _Respuesta(), {}, ResolverCatalogos(estricto=True), jefe_per_idpersona=9177005) == 9177005


def test_respuesta_nivel_persona_usa_el_mapa_del_paso_persona():
    class _R(_Respuesta):
        miembro_id = "abc"
    assert mapeo.per_idpersona_de_respuesta(
        _R(), {"abc": 555}, ResolverCatalogos(estricto=True)) == 555


def test_binds_respuesta_mezcla_ids_reales_y_pendientes_en_dry_run():
    binds = mapeo.binds_respuesta(
        _Respuesta(), user=None, catalogos=ResolverCatalogos(estricto=False),
        hog_codigo="HOG-1", per_idpersona=555, instrumento=type("I", (), {"codigo": "TERRITORIAL"})(),
    )
    # Ya resueltos con dato real de Oracle:
    assert binds["pins_idinstrumento"] == 1        # único instrumento (Query B)
    assert binds["pcod_hogar"] == "HOG-1"
    assert binds["pper_idpersona"] == 555
    # El cruce de la respuesta resuelve limpio y su escribibilidad está confirmada
    # por la columna ESCRIBIBLE del export (antes esto era ‹PEND:ESCRIBIBLE(res=8)›).
    assert binds["pres_idrespuesta"] == 8
    # RXP_TIPOPREGUNTA se copia del catálogo de Oracle: la pregunta 5 es de hogar ⇒ GE.
    # (Antes era ‹PEND:RXP_TIPOPREGUNTA(RADIO)›, mandando el widget de SICAV.)
    assert binds["prxp_tipopreguntarespuesta"] == "GE"
    # Extras decididos CON DATO (2026-07-24), ya no son marcadores:
    #  - PPER_IDPREGUNTAPADRE → NULL: SICAV no modela 'pregunta padre' (derivadas de
    #    Oracle) y no es columna almacenada de GIC_N_RESPUESTASENCUESTA.
    #  - PBANDERA → 1: upsert idempotente; en un hogar nuevo el borrado es no-op.
    assert binds["pper_idpreguntapadre"] is None
    assert binds["pbandera"] == 1


def test_pbandera_es_1_upsert_idempotente_decidido():
    # PBANDERA=1 dispara SP_BORRADORESPUESTAS (borra+inserta la respuesta del par
    # hogar/pregunta). Se decidió 1 CON DATO (2026-07-24): en un hogar NUEVO el borrado
    # es no-op y 1 hace la escritura idempotente (re-correr no duplica). Es una decisión
    # deliberada y documentada — no un 1 por descuido, que era el riesgo original.
    binds = mapeo.binds_respuesta(
        _Respuesta(), user=None, catalogos=ResolverCatalogos(estricto=False),
        hog_codigo="HOG-1", per_idpersona=555, instrumento=type("I", (), {"codigo": "X"})(),
    )
    assert binds["pbandera"] == 1


def test_texto_respuesta_se_redacta_por_ser_pii_potencial():
    binds = mapeo.binds_respuesta(
        _Respuesta(), user=None, catalogos=ResolverCatalogos(estricto=False),
        hog_codigo="HOG-1", per_idpersona=555, instrumento=type("I", (), {"codigo": "X"})(),
    )
    res = P.invocar(P.SP_SET_RESPUESTAS_DE_ENCUESTA, binds, confirmar=False)
    # El texto libre puede traer PII según la pregunta → nunca en claro en auditoría.
    assert res.binds_redactados["prxp_textorespuesta"] == P.REDACTADO
