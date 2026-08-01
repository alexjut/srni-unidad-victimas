"""
Tests de la barrida periódica que recoge los hogares sin escribir en Oracle.

Lo que se protege:

1. **Que encuentre lo que el disparo automático dejó atrás** — sobre todo lo
   cerrado mientras `ORACLE_SYNC.AUTOMATICA` estaba apagado, que es el caso masivo.
2. **Que NO dé por escrito en producción lo que se ensayó en la réplica local.** Es
   el fallo silencioso que costó encontrar el 2026-07-28 y por el que el destino
   entró en la clave del ledger.
3. **Que no insista para siempre** sobre un hogar que necesita intervención humana.
4. **Que no arranque sola** ni escriba con el interruptor apagado.
"""
from datetime import timedelta
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.sincronizacion import tasks
from apps.sincronizacion.models import EstadoPaso, PasoEscritura, RegistroEscrituraOracle

pytestmark = pytest.mark.django_db

SYNC_ON = {"AUTOMATICA": True, "DESTINO": "produccion"}
REINTENTO_ON = {"HABILITADO": True, "CADA_MINUTOS": 15, "LIMITE": 50,
                "ENFRIAMIENTO_MINUTOS": 30, "MAX_INTENTOS": 5}

BARRIDO = dict(enfriamiento_minutos=30, limite=50, max_intentos=5)


@pytest.fixture(autouse=True)
def cache_limpia():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def crear_hogar(db):
    """Hogar con una sesión COMPLETADA cerrada hace `hace_horas` — o sea, listo
    para escribirse en Oracle y ya fuera del período de enfriamiento."""
    from apps.encuestas.models import SesionEncuesta
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    instrumento = Instrumento.objects.create(
        codigo="TEST", version="1", nombre="Instrumento de prueba",
        vigente_desde=timezone.now().date())
    contador = {"n": 0}

    def _crear(*, cerrada=True, hace_horas=3):
        contador["n"] += 1
        n = contador["n"]
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento=f"90000{n}",
            primer_nombre="A", primer_apellido="B",
            fecha_nacimiento="1990-01-01", genero="F")
        hogar = Hogar.objects.create(codigo_hogar=f"BARRIDA-{n}",
                                     autorizado=victima, estado="BORRADOR")
        SesionEncuesta.objects.create(
            hogar=hogar, instrumento=instrumento,
            estado="COMPLETADA" if cerrada else "EN_PROGRESO",
            fecha_fin=timezone.now() - timedelta(hours=hace_horas) if cerrada else None,
        )
        return hogar

    return _crear


def _registro(hogar, *, estado, destino="produccion", intento=1, hace_horas=3):
    reg = RegistroEscrituraOracle.objects.create(
        hogar=hogar, paso=PasoEscritura.HOGAR, origen_id=str(hogar.pk),
        estado=estado, destino_entorno=destino, intento=intento)
    # `actualizado_en` es auto_now: para simular un fallo viejo hay que forzarlo con
    # un UPDATE que no dispare el auto_now.
    RegistroEscrituraOracle.objects.filter(pk=reg.pk).update(
        actualizado_en=timezone.now() - timedelta(hours=hace_horas))
    return reg


# ── 1. qué entra al barrido ──────────────────────────────────────────────────
def test_encuentra_el_hogar_cerrado_que_nunca_se_intento(crear_hogar):
    """El caso masivo: todo lo capturado mientras la escritura automática estaba
    apagada quedó sin una sola fila en el ledger."""
    hogar = crear_hogar()
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == [hogar.pk]


def test_ignora_el_hogar_sin_encuesta_cerrada(crear_hogar):
    """Sin encuesta finalizada no hay nada que escribir: es la misma señal que
    dispara el camino automático."""
    crear_hogar(cerrada=False)
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == []


def test_ignora_el_hogar_ya_verificado(crear_hogar):
    hogar = crear_hogar()
    _registro(hogar, estado=EstadoPaso.VERIFICADO)
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == []


@pytest.mark.parametrize("estado", [
    EstadoPaso.FALLIDO,
    EstadoPaso.PENDIENTE,
    # El más peligroso: el procedure se llamó pero la verificación por consulta no
    # confirmó nada. "Llamé al procedure" no es "quedó escrito".
    EstadoPaso.EJECUTADO_SIN_VERIFICAR,
])
def test_recoge_la_maquina_de_estados_a_medias(crear_hogar, estado):
    hogar = crear_hogar()
    _registro(hogar, estado=estado)
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == [hogar.pk]


# ── 2. el destino no se confunde ─────────────────────────────────────────────
def test_lo_escrito_en_local_no_cuenta_como_escrito_en_produccion(crear_hogar):
    """
    El fallo silencioso del 2026-07-28: un hogar migrado a la réplica local se daba
    por hecho en producción. Si la barrida lo omitiera, ese hogar no llegaría nunca
    a la base de la UARIV y el tablero diría que está todo al día.
    """
    hogar = crear_hogar()
    _registro(hogar, estado=EstadoPaso.VERIFICADO, destino="local")
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == [hogar.pk]


def test_los_dry_run_no_cuentan_como_escritura(crear_hogar):
    """Un DRY-RUN se registra con `destino_entorno=''`: simular no es escribir."""
    hogar = crear_hogar()
    _registro(hogar, estado=EstadoPaso.DRY_RUN, destino="")
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == [hogar.pk]


# ── 3. enfriamiento y tope de intentos ───────────────────────────────────────
def test_no_reintenta_lo_que_fallo_recien(crear_hogar):
    """Volvería a fallar igual y ensuciaría el log cada cuarto de hora."""
    hogar = crear_hogar()
    _registro(hogar, estado=EstadoPaso.FALLIDO, hace_horas=0)
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == []


def test_no_toca_la_encuesta_recien_cerrada(crear_hogar):
    """Su tarea normal probablemente esté en vuelo en este mismo instante."""
    crear_hogar(hace_horas=0)
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == []


def test_abandona_el_hogar_que_agoto_los_intentos(crear_hogar):
    """Un mapeo que no cruza no se arregla insistiendo: alguien tiene que mirarlo."""
    hogar = crear_hogar()
    _registro(hogar, estado=EstadoPaso.FALLIDO, intento=5)
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == []


def test_un_paso_agotado_frena_el_hogar_entero(crear_hogar):
    """Los pasos dependen unos de otros: reintentar solo los reintentables dejaría
    una máquina de estados que nunca puede completarse."""
    hogar = crear_hogar()
    _registro(hogar, estado=EstadoPaso.FALLIDO, intento=5)
    RegistroEscrituraOracle.objects.create(
        hogar=hogar, paso=PasoEscritura.PERSONA, origen_id="otro",
        estado=EstadoPaso.PENDIENTE, destino_entorno="produccion", intento=1)
    assert tasks.hogares_pendientes_de_oracle("produccion", **BARRIDO) == []


# ── 4. límite y orden ────────────────────────────────────────────────────────
def test_respeta_el_tope_por_corrida_y_atiende_primero_al_mas_viejo(crear_hogar):
    """Sin un orden estable, con más pendientes que el tope los mismos hogares se
    reencolarían siempre y la cola de atrás no avanzaría nunca."""
    from apps.hogares.models import Hogar

    hogares = [crear_hogar() for _ in range(3)]
    # `created_at` es auto_now_add y los tres se crean en el mismo milisegundo: sin
    # separarlos a mano el orden sería indistinguible y el test, inestable.
    # hogares[0] queda como el más antiguo y hogares[2] como el más reciente.
    for posicion, hogar in enumerate(hogares):
        Hogar.objects.filter(pk=hogar.pk).update(
            created_at=timezone.now() - timedelta(days=10 - posicion))

    pendientes = tasks.hogares_pendientes_de_oracle(
        "produccion", enfriamiento_minutos=30, limite=2, max_intentos=5)
    assert pendientes == [h.pk for h in hogares[:2]]


# ── 5. la tarea: interruptores y encolado ────────────────────────────────────
@override_settings(ORACLE_SYNC=SYNC_ON, SYNC_REINTENTO=REINTENTO_ON)
def test_la_tarea_encola_los_pendientes(crear_hogar):
    hogar = crear_hogar()
    with mock.patch.object(tasks, "encolar_hogar", return_value=True) as encolar:
        res = tasks.reintentar_sincronizaciones_pendientes()
    encolar.assert_called_once_with(hogar.pk)
    assert res["estado"] == "PROCESADA"
    assert (res["pendientes"], res["encolados"]) == (1, 1)


@override_settings(ORACLE_SYNC=SYNC_ON, SYNC_REINTENTO=REINTENTO_ON)
def test_el_broker_caido_no_revienta_la_barrida(crear_hogar):
    """`encolar_hogar` traga la excepción a propósito; la barrida cuenta cuántos
    entraron de verdad para que el resumen no mienta."""
    crear_hogar()
    with mock.patch.object(tasks, "encolar_hogar", return_value=False):
        res = tasks.reintentar_sincronizaciones_pendientes()
    assert (res["pendientes"], res["encolados"]) == (1, 0)


@override_settings(ORACLE_SYNC={"AUTOMATICA": False, "DESTINO": "produccion"},
                   SYNC_REINTENTO=REINTENTO_ON)
def test_no_encola_nada_con_la_escritura_apagada(crear_hogar):
    """Encolar sería inofensivo (la tarea individual se auto-omite) pero llenaría
    la cola de no-ops cada cuarto de hora y taparía el log real."""
    crear_hogar()
    with mock.patch.object(tasks, "encolar_hogar") as encolar:
        res = tasks.reintentar_sincronizaciones_pendientes()
    encolar.assert_not_called()
    assert res["estado"] == "OMITIDA"


@override_settings(ORACLE_SYNC=SYNC_ON, SYNC_REINTENTO={"HABILITADO": False})
def test_la_barrida_tiene_su_propio_interruptor(crear_hogar):
    """Se puede apagar la barrida sin apagar la escritura automática: sirve para
    frenar una tormenta de reintentos sin cortar el camino normal."""
    crear_hogar()
    with mock.patch.object(tasks, "encolar_hogar") as encolar:
        assert tasks.reintentar_sincronizaciones_pendientes()["estado"] == "OMITIDA"
    encolar.assert_not_called()


@override_settings(ORACLE_SYNC={"AUTOMATICA": True, "DESTINO": ""},
                   SYNC_REINTENTO=REINTENTO_ON)
def test_sin_destino_valido_no_barre(crear_hogar):
    crear_hogar()
    res = tasks.reintentar_sincronizaciones_pendientes()
    assert res["estado"] == "OMITIDA" and "DESTINO" in res["motivo"]


def test_el_default_del_proyecto_es_apagado():
    from django.conf import settings
    assert settings.SYNC_REINTENTO["HABILITADO"] is False


# ── 6. exclusión mutua ───────────────────────────────────────────────────────
@override_settings(ORACLE_SYNC=SYNC_ON, SYNC_REINTENTO=REINTENTO_ON)
def test_no_corren_dos_barridas_a_la_vez(crear_hogar):
    """Con muchos pendientes el barrido puede tardar más que el intervalo. Dos a la
    vez encolarían los mismos hogares dos veces: el ledger deduplica, pero se
    gastan conexiones a Oracle justo cuando ya va lento."""
    crear_hogar()
    adentro = {}

    def _mientras_encola(_hogar_id):
        adentro["resultado"] = tasks.reintentar_sincronizaciones_pendientes()
        return True

    with mock.patch.object(tasks, "encolar_hogar", side_effect=_mientras_encola):
        tasks.reintentar_sincronizaciones_pendientes()

    assert adentro["resultado"]["estado"] == "SALTADA"
