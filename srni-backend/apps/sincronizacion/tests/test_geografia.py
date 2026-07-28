"""
Tests del cruce geográfico SICAV (DANE) → Oracle (ID_MUNI_DEPTO).

Lo que se protege: SICAV guarda el código DANE de 5 dígitos CON cero a la izquierda
('05001', como lo deja el selector de municipio del móvil) y Oracle guarda el mismo
código SIN el cero ('5001'). Escribir el valor crudo mete en GIC_N_RESPUESTASENCUESTA
un texto que ningún reporte territorial resuelve, y el `EXCEPTION WHEN OTHERS` del
procedure NO avisa — la forma exacta del bug histórico que este trabajo evita.

La convención está medida en producción (2026-07-28): 28.151/28.151 respuestas
reales cruzan contra GIC_MUNICIPIO.ID_MUNI_DEPTO.
"""
import pytest

from apps.sincronizacion.oracle import catalogos, mapeo


class _Preg:
    def __init__(self, id_preg, codigo="X"):
        self.id_preg = id_preg
        self.codigo_externo = codigo


class _Resp:
    def __init__(self, valor, id_preg):
        self.valor = valor
        self.pregunta = _Preg(id_preg)


# id_preg 3 = "Lugar de Residencia" (DP). 30 = tipo de documento (no geográfica).
PREG_GEO, PREG_NO_GEO = 3, 30


def _resolver(estricto):
    return mapeo.ResolverCatalogos(usuario_servicio_id="999999",
                                   perfil_servicio_id="1", estricto=estricto)


# ── el catálogo volcado de producción ────────────────────────────────────────
def test_el_catalogo_trae_las_preguntas_dp_y_los_municipios():
    geo = catalogos.cargar_geografia()
    assert PREG_GEO in geo["preguntas_dp"]
    assert 1161 in geo["preguntas_dt"]          # Dirección Territorial, no es DP
    assert len(geo["municipios"]) > 1000        # 1.126 en el volcado real


@pytest.mark.parametrize("dane, esperado", [
    ("05001", "5001"),      # Medellín — el caso del cero a la izquierda
    ("5001", "5001"),       # ya normalizado: idempotente
    ("73026", "73026"),     # Alvarado (el municipio del Escalón 1)
    ("76109", "76109"),     # Buenaventura
    ("11001", "11001"),     # Bogotá
    ("08758", "8758"),      # Atlántico: otro cero a la izquierda
])
def test_normaliza_el_dane_al_id_de_oracle(dane, esperado):
    assert catalogos.normalizar_codigo_municipio(dane) == esperado


@pytest.mark.parametrize("basura", [None, "", "  ", "abc", "05001x", "99999"])
def test_no_inventa_cuando_no_cruza(basura):
    """Incluye '99999': dígitos válidos que NO existen en el catálogo de Oracle."""
    assert catalogos.normalizar_codigo_municipio(basura) is None


# ── el bind que termina en RXP_TEXTORESPUESTA ────────────────────────────────
def test_la_respuesta_geografica_se_traduce():
    assert mapeo._texto_respuesta(_Resp("05001", PREG_GEO), _resolver(True)) == "5001"


def test_la_respuesta_no_geografica_pasa_intacta():
    """Un '05001' en una pregunta normal es texto, no un municipio: no se toca."""
    resolver = _resolver(True)
    assert mapeo._texto_respuesta(_Resp("05001", PREG_NO_GEO), resolver) == "05001"
    assert mapeo._texto_respuesta(_Resp("Bogotá", PREG_NO_GEO), resolver) == "Bogotá"


def test_municipio_desconocido_revienta_en_estricto():
    with pytest.raises(mapeo.MapeoDesconocido) as exc:
        mapeo._texto_respuesta(_Resp("99999", PREG_GEO), _resolver(True))
    assert "99999" in str(exc.value)


def test_municipio_desconocido_deja_marcador_en_dry_run():
    salida = mapeo._texto_respuesta(_Resp("99999", PREG_GEO), _resolver(False))
    assert salida == "‹PEND:GEOGRAFIA(99999)›"


def test_pregunta_sin_id_preg_no_estalla():
    """Sin puente a Oracle el valor va tal cual; el error lo da el resolver de res_id."""
    resp = _Resp("05001", PREG_GEO)
    resp.pregunta.id_preg = None
    assert mapeo._texto_respuesta(resp, _resolver(True)) == "05001"
