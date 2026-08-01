"""
Tests del bloqueo distribuido que impide que dos corridas de la misma tarea
periódica se pisen.

Es la pieza de la que depende todo lo demás: si el bloqueo no excluye, dos cargas
del padrón pueden leer el Oracle de producción a la vez durante un día entero.
"""
import pytest
from django.core.cache import cache

from srni.bloqueos import PREFIJO, bloqueo_exclusivo


@pytest.fixture(autouse=True)
def cache_limpia():
    """Sin esto, un bloqueo dejado por un test anterior hace fallar al siguiente."""
    cache.clear()
    yield
    cache.clear()


def test_se_adquiere_cuando_esta_libre():
    with bloqueo_exclusivo("prueba", ttl_segundos=60) as bl:
        assert bl.adquirido is True
        assert bl.token


def test_el_segundo_no_entra_mientras_el_primero_lo_tiene():
    """El caso que motiva el módulo: beat dispara y la corrida anterior sigue viva."""
    with bloqueo_exclusivo("prueba", ttl_segundos=60) as primero:
        assert primero.adquirido is True
        with bloqueo_exclusivo("prueba", ttl_segundos=60) as segundo:
            assert segundo.adquirido is False
            # El log tiene que decir QUIÉN lo tiene, o el operador no sabe si el que
            # está corriendo lleva dos minutos o dos días.
            assert segundo.dueño_actual and segundo.dueño_actual != "(desconocido)"


def test_se_libera_al_salir_y_el_siguiente_entra():
    with bloqueo_exclusivo("prueba", ttl_segundos=60) as primero:
        assert primero.adquirido is True
    with bloqueo_exclusivo("prueba", ttl_segundos=60) as segundo:
        assert segundo.adquirido is True


def test_se_libera_aunque_la_tarea_reviente():
    """
    Si una excepción dejara el bloqueo tomado, la tarea no volvería a correr NUNCA
    hasta que venciera el TTL — 48 h en el caso del padrón. Peor que el solapamiento.
    """
    with pytest.raises(RuntimeError):
        with bloqueo_exclusivo("prueba", ttl_segundos=60):
            raise RuntimeError("el comando falló")
    with bloqueo_exclusivo("prueba", ttl_segundos=60) as bl:
        assert bl.adquirido is True


def test_bloqueos_con_nombres_distintos_no_se_estorban():
    with bloqueo_exclusivo("padron:recarga", ttl_segundos=60) as a:
        with bloqueo_exclusivo("sincronizacion:reintento", ttl_segundos=60) as b:
            assert (a.adquirido, b.adquirido) == (True, True)


def test_el_que_no_adquirio_no_borra_el_bloqueo_ajeno():
    """
    Al salir del `with`, quien NO adquirió no debe tocar la clave: si la borrara,
    dejaría al dueño real trabajando sin protección.
    """
    with bloqueo_exclusivo("prueba", ttl_segundos=60):
        with bloqueo_exclusivo("prueba", ttl_segundos=60) as segundo:
            assert segundo.adquirido is False
        # Al cerrar el `with` interno la clave del primero sigue viva.
        assert cache.get(f"{PREFIJO}prueba") is not None


def test_no_borra_el_bloqueo_si_ya_no_es_suyo(monkeypatch):
    """
    Escenario del TTL vencido a mitad de una corrida larga: otro proceso tomó el
    bloqueo legítimamente. Borrarlo ahí lo dejaría desprotegido justo al empezar.
    """
    clave = f"{PREFIJO}prueba"
    with bloqueo_exclusivo("prueba", ttl_segundos=60) as bl:
        assert bl.adquirido is True
        # Simula que el TTL venció y otra corrida se apropió de la clave.
        cache.set(clave, "otro-token|otra-corrida", timeout=60)
    assert cache.get(clave) == "otro-token|otra-corrida"


def test_si_la_cache_no_responde_no_se_adquiere(monkeypatch):
    """
    Fail-CLOSED. En producción la caché va con IGNORE_EXCEPTIONS, así que un Redis
    caído hace que `add` devuelva algo falsy en vez de lanzar. Eso NO puede
    interpretarse como "el bloqueo es mío": sin exclusión garantizada, la carga
    del padrón no corre.
    """
    monkeypatch.setattr("srni.bloqueos.cache.add", lambda *a, **k: None)
    monkeypatch.setattr("srni.bloqueos.cache.get", lambda *a, **k: None)
    with bloqueo_exclusivo("prueba", ttl_segundos=60) as bl:
        assert bl.adquirido is False
