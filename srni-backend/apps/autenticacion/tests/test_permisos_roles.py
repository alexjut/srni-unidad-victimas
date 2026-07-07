"""
Permisos por rol — regresión de los bugs reportados por el panel web.

Cubre:
  Bug 1 — GET /api/formulario/instrumentos/ debe dar 200 a cualquier rol
          autenticado (incluido SUPERVISOR, que no puede caracterizar).
  Bug 2 — GET /api/reportes/supervisor/ y /api/reportes/dashboard/series/
          deben dar 200 con datos agregados al ADMINISTRADOR y al SUPERVISOR.
  Bug 3 — GET /api/hogares/, /api/encuestas/ y /api/reportes/encuestador/
          deben dar 200 (solo lectura) al SUPERVISOR; la escritura de hogares
          sigue exigiendo puede_caracterizar (403 al SUPERVISOR).
"""
import pytest
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario

# codigo -> (buscar_rni, caracterizar, ver_reportes, administrar)
PERFILES = {
    "ADMINISTRADOR": (True, True, True, True),
    "SUPERVISOR": (True, False, True, False),
    "ENCUESTADOR": (True, True, False, False),
}


@pytest.fixture
def usuarios(db):
    creados = {}
    for codigo, (buscar, caract, reportes, admin) in PERFILES.items():
        perfil = Perfil.objects.create(
            codigo=codigo, nombre=codigo.title(),
            puede_buscar_rni=buscar, puede_caracterizar=caract,
            puede_ver_reportes=reportes, puede_administrar=admin, activo=True,
        )
        u = Usuario.objects.create_user(
            codigo_usuario=f"U_{codigo}", password="Test2026!",
            nombre_completo=f"Usuario {codigo}", email=f"{codigo.lower()}@test.dev",
            perfil=perfil, activo=True,
        )
        creados[codigo] = u
    return creados


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ─── Bug 1 ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("rol", ["ADMINISTRADOR", "SUPERVISOR", "ENCUESTADOR"])
def test_bug1_instrumentos_lectura_para_todos(usuarios, rol):
    resp = _client(usuarios[rol]).get("/api/formulario/instrumentos/")
    assert resp.status_code == 200, f"{rol} recibió {resp.status_code} en instrumentos"


def test_instrumentos_rechaza_anonimo():
    resp = APIClient().get("/api/formulario/instrumentos/")
    assert resp.status_code in (401, 403)


# ─── Bug 2 ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("rol", ["ADMINISTRADOR", "SUPERVISOR"])
def test_bug2_supervisor_reporte_ok(usuarios, rol):
    resp = _client(usuarios[rol]).get("/api/reportes/supervisor/")
    assert resp.status_code == 200, f"{rol} recibió {resp.status_code} en /supervisor/"
    assert "encuestadores" in resp.data


@pytest.mark.parametrize("rol", ["ADMINISTRADOR", "SUPERVISOR"])
def test_bug2_dashboard_series_ok(usuarios, rol):
    resp = _client(usuarios[rol]).get("/api/reportes/dashboard/series/")
    assert resp.status_code == 200, f"{rol} recibió {resp.status_code} en /dashboard/series/"
    assert "serie_diaria" in resp.data


def test_bug2_encuestador_no_ve_supervisor(usuarios):
    # El encuestador de campo no tiene ver_reportes ni administrar.
    resp = _client(usuarios["ENCUESTADOR"]).get("/api/reportes/supervisor/")
    assert resp.status_code == 403


# ─── Bug 3 ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "/api/hogares/",
    "/api/encuestas/",
    "/api/reportes/encuestador/",
])
def test_bug3_supervisor_lectura_operativa(usuarios, url):
    resp = _client(usuarios["SUPERVISOR"]).get(url)
    assert resp.status_code == 200, f"SUPERVISOR recibió {resp.status_code} en {url}"


def test_bug3_supervisor_no_puede_crear_hogar(usuarios):
    # Escritura sigue exigiendo puede_caracterizar → 403 para el supervisor.
    resp = _client(usuarios["SUPERVISOR"]).post("/api/hogares/", {}, format="json")
    assert resp.status_code == 403
