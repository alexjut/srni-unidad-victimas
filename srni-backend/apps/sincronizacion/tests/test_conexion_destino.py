"""
Tests de la guarda del destino de escritura.

Bug que se protege (detectado 2026-07-28, antes de que ocurriera): el destino
'local' se resolvía desde settings.ORACLE_LEGACY, alimentado por la variable de
entorno ORACLE_LEGACY_HOST. Una sesión que hubiera exportado esa variable hacia
otro servidor —cosa normal para una lectura de referencia contra prod— convertía

    escribir_a_oracle --confirmar --destino local

en una escritura contra PRODUCCIÓN, con el banner del comando diciendo "local".
Los procedures hacen COMMIT interno: no habría vuelta atrás ni error visible.
"""
import pytest
from django.test import override_settings

from apps.sincronizacion.oracle import conexion


def _cfg(host):
    return {"HOST": host, "PORT": 1521, "SERVICE": "FREEPDB1",
            "USER": "RNIENTREVISTA", "PASSWORD": "x"}


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "LOCALHOST", " localhost "])
def test_destino_local_acepta_hosts_locales(host):
    with override_settings(ORACLE_LEGACY=_cfg(host)):
        cfg = conexion.resolver_config("local")
    assert cfg["host"].strip().lower() == host.strip().lower()


@pytest.mark.parametrize("host", ["30.0.1.9", "oracle-prod.uariv.local", "10.0.0.5"])
def test_destino_local_rechaza_host_remoto(host):
    """Con ORACLE_LEGACY_HOST apuntando a otro server, 'local' NO resuelve."""
    with override_settings(ORACLE_LEGACY=_cfg(host)):
        with pytest.raises(conexion.DestinoLocalNoLocal) as exc:
            conexion.resolver_config("local")
    assert host in str(exc.value)


def test_el_rechazo_es_un_destinonoconfigurado():
    """Quien ya capturaba DestinoNoConfigurado sigue capturando este caso."""
    assert issubclass(conexion.DestinoLocalNoLocal, conexion.DestinoNoConfigurado)


def test_describir_destino_no_filtra_la_contrasena():
    with override_settings(ORACLE_LEGACY=_cfg("localhost")):
        dsn = conexion.describir_destino("local")
    assert dsn == "RNIENTREVISTA@localhost:1521/FREEPDB1"
    assert "x" not in dsn.replace("RNIENTREVISTA", "").replace("FREEPDB1", "")


def test_destino_desconocido_aborta():
    with pytest.raises(conexion.DestinoNoConfigurado):
        conexion.resolver_config("preproduccion")
