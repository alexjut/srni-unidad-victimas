"""
Tests de ResolverCatalogos (Etapa A) — SIN Oracle.

Verifican la resolución contra los CROSSWALKS REALES de `catalogos.py` (valores
leídos de prod RNIENTREVISTA, 2026-07-15): dado un valor SICAV, devuelve el código
Oracle real; ante un valor sin mapeo, LANZA error claro en modo estricto y un
marcador ‹PEND:...› en dry-run. Nunca falla en silencio ni inventa un default.
"""
import pytest

from apps.sincronizacion.oracle import catalogos
from apps.sincronizacion.oracle.mapeo import (
    MapeoDesconocido, MapeoPendienteNegocio, ResolverCatalogos,
)


def _r(estricto=True, **over):
    """Resolver con los crosswalks REALES de catalogos.py (sin inyectar)."""
    return ResolverCatalogos(estricto=estricto, **over)


# ── catálogo 2 — tipo de caracterización (constante HOGAR) ───────────────────
def test_tipo_caracterizacion_es_hogar():
    assert _r().resolver_tipo_caracterizacion("TERRITORIAL") == 2
    assert _r().resolver_tipo_caracterizacion() == catalogos.TIPO_CARACTERIZACION_HOGAR


# ── catálogo 3 — tipo de documento (valores reales GIC_TIPODOC) ──────────────
@pytest.mark.parametrize("codigo,esperado", [
    ("CC", 1), ("TI", 2), ("CE", 3), ("RC", 4), ("PA", 7), ("NIT", 9),
])
def test_tdoc_real(codigo, esperado):
    assert _r().resolver_tdoc(codigo) == esperado


class _TD:
    def __init__(self, codigo): self.codigo = codigo


def test_tdoc_por_instancia():
    assert _r().resolver_tdoc(_TD("CC")) == 1


@pytest.mark.parametrize("codigo", ["PE", "NES"])
def test_tdoc_sin_equivalente_lanza(codigo):
    # PE (PEP) y NES no tienen equivalente en GIC_TIPODOC → nunca se inventan.
    with pytest.raises(MapeoDesconocido):
        _r().resolver_tdoc(codigo)


def test_tdoc_sin_documento_lanza():
    with pytest.raises(MapeoDesconocido):
        _r().resolver_tdoc(None)


def test_tdoc_dry_run_marcador():
    assert _r(estricto=False).resolver_tdoc("PE") == "‹PEND:TIPO_DOCUMENTO(PE)›"


# ── catálogo 4 — parentesco (valores reales GIC_PARENTESCOGENEALOGICO) ───────
@pytest.mark.parametrize("codigo,esperado", [
    ("CONYUGE", 4), ("HIJO_A", 3), ("YERNO_NUERA", 8), ("NIETO_A", 5),
    ("PADRE_MADRE", 2), ("HERMANO_A", 7), ("OTRO_PARIENTE", 9), ("NO_PARIENTE", 10),
])
def test_relac_real(codigo, esperado):
    assert _r().resolver_relac(codigo) == esperado


def test_relac_vacio_lanza():
    with pytest.raises(MapeoDesconocido):
        _r().resolver_relac("")


# ── catálogo 4b — tipo de víctima (sin fuente aún → pendiente) ───────────────
def test_t_victima_pendiente_lanza():
    with pytest.raises(MapeoDesconocido):
        _r().resolver_t_victima("DIRECTA")


# ── catálogo 1 — usuario/perfil de servicio (pendiente de negocio) ───────────
def test_usuario_servicio_pendiente_lanza():
    with pytest.raises(MapeoPendienteNegocio):
        _r().id_usuario_servicio()


def test_usuario_servicio_configurado_ok():
    assert _r(usuario_servicio_id=9001).id_usuario_servicio() == 9001


def test_usuario_servicio_dry_run_marcador():
    assert _r(estricto=False).id_usuario_servicio() == "‹PEND:USUARIO_SERVICIO_ID(negocio)›"


# ── catálogo 5 — territorio (aparte por volumen → pendiente) ─────────────────
class _Sesion:
    class direccion_territorial: codigo = "DT-X"
    class departamento_atencion: codigo_dane = "05"
    class municipio_atencion: codigo_dane = "05001"
    class punto_atencion: codigo = "PA-1"


def test_territorio_estricto_lanza():
    with pytest.raises(MapeoDesconocido):
        _r().resolver_territorio(_Sesion())


def test_territorio_dry_run_marcadores():
    t = _r(estricto=False).resolver_territorio(_Sesion())
    assert t["id_dt"].startswith("‹PEND:TERRITORIO")
