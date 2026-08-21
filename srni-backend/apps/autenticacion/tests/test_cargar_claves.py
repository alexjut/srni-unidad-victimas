"""Tests del comando cargar_claves — asignar contraseñas Argon2 desde un CSV."""
import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.autenticacion.models import Perfil, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def perfil():
    return Perfil.objects.create(codigo="P_CC", nombre="Perfil", activo=True)


@pytest.fixture
def usuario(perfil):
    return Usuario.objects.create_user(
        codigo_usuario="KLMUÑOZM", password="ClaveInicial123",
        nombre_completo="Karen Muñoz", email="k@srni.dev",
        perfil=perfil, activo=True,
    )


def _csv(tmp_path, contenido):
    p = tmp_path / "claves.csv"
    p.write_text(contenido, encoding="utf-8")
    return str(p)


def test_asigna_la_clave_con_argon2(tmp_path, usuario):
    ruta = _csv(tmp_path, "KLMUÑOZM,ClaveNueva2026\n")
    call_command("cargar_claves", ruta)

    usuario.refresh_from_db()
    assert usuario.password.startswith("argon2")
    assert usuario.check_password("ClaveNueva2026")
    assert not usuario.check_password("ClaveInicial123")


def test_dry_run_no_toca_nada(tmp_path, usuario):
    ruta = _csv(tmp_path, "KLMUÑOZM,ClaveNueva2026\n")
    call_command("cargar_claves", ruta, "--dry-run")

    usuario.refresh_from_db()
    assert usuario.check_password("ClaveInicial123")


def test_usuario_inexistente_no_frena_a_los_demas(tmp_path, usuario):
    ruta = _csv(tmp_path, "NOEXISTE,X\nKLMUÑOZM,ClaveNueva2026\n")
    out = io.StringIO()
    call_command("cargar_claves", ruta, stdout=out)

    usuario.refresh_from_db()
    assert usuario.check_password("ClaveNueva2026")     # el que sí existe, aplicado
    assert "NOEXISTE" in out.getvalue()                 # el otro, reportado


def test_una_clave_debil_no_se_aplica_y_avisa(tmp_path, usuario):
    # 'corta' no pasa el mínimo de 10 caracteres. No debe tocar al usuario.
    ruta = _csv(tmp_path, "KLMUÑOZM,corta\n")
    with pytest.raises(CommandError):
        call_command("cargar_claves", ruta)             # nada quedó para aplicar

    usuario.refresh_from_db()
    assert usuario.check_password("ClaveInicial123")


def test_sin_validar_permite_forzar(tmp_path, usuario):
    ruta = _csv(tmp_path, "KLMUÑOZM,corta\n")
    call_command("cargar_claves", ruta, "--sin-validar")

    usuario.refresh_from_db()
    assert usuario.check_password("corta")


def test_ignora_el_encabezado(tmp_path, usuario):
    ruta = _csv(tmp_path, "codigo_usuario,password\nKLMUÑOZM,ClaveNueva2026\n")
    call_command("cargar_claves", ruta)

    usuario.refresh_from_db()
    assert usuario.check_password("ClaveNueva2026")


def test_acepta_punto_y_coma(tmp_path, usuario):
    ruta = _csv(tmp_path, "KLMUÑOZM;ClaveNueva2026\n")
    call_command("cargar_claves", ruta)

    usuario.refresh_from_db()
    assert usuario.check_password("ClaveNueva2026")


def test_codigo_repetido_se_reporta(tmp_path, usuario):
    ruta = _csv(tmp_path, "KLMUÑOZM,Primera2026\nKLMUÑOZM,Segunda2026\n")
    out = io.StringIO()
    call_command("cargar_claves", ruta, stdout=out)

    # La primera se aplica; la segunda se reporta como repetida y NO pisa.
    usuario.refresh_from_db()
    assert usuario.check_password("Primera2026")
    assert "repetido" in out.getvalue()


def test_solo_activos_ignora_al_inactivo(tmp_path, perfil):
    inactivo = Usuario.objects.create_user(
        codigo_usuario="VIEJO", password="ClaveInicial123",
        nombre_completo="Ex Usuario", email="v@srni.dev",
        perfil=perfil, activo=False,
    )
    ruta = _csv(tmp_path, "VIEJO,ClaveNueva2026\n")
    with pytest.raises(CommandError):        # ninguno queda para aplicar
        call_command("cargar_claves", ruta, "--solo-activos")

    inactivo.refresh_from_db()
    assert inactivo.check_password("ClaveInicial123")
