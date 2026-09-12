"""
Con el control retirado no se puede autorizar, porque no habilitaría nada.

─── Por qué no alcanzaba con dejar la pantalla inerte ───────────────────────
El plan decidió conservar `ExcepcionVigencia` y su módulo: si el proceso repone la
regla —y estas decisiones se reponen— reponerla cuesta mover una variable, y
borrarlo todo convertiría esa vuelta atrás en volver a construirlo.

Pero «conservar» no es «dejar abierto». Con el control retirado, otorgar una
autorización es **peor que no tener la pantalla**: quien coordina dedicaría su
tiempo a autorizar casos creyendo que desbloquea a alguien, y el encuestador no
notaría ninguna diferencia porque ya podía caracterizar. Nadie se enteraría del
malentendido, y quedarían filas VIGENTE que nadie otorgó por una razón real —
ensuciando justo la tabla que se conserva como evidencia del régimen anterior.

─── Lo que sí sigue funcionando ─────────────────────────────────────────────
Consultar. El histórico es evidencia y no se toca. Y anular sigue disponible: una
autorización otorgada por error antes del cambio tiene que poder retirarse.

Se responde **409 y no 403**: no es que a esta persona le falte un permiso, es que
la operación entera dejó de tener sentido. Un 403 mandaría a quien coordina a
pedirle permisos a su jefe.
"""
import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/habilitaciones/'


@pytest.fixture
def escenario(db):
    from apps.autenticacion.models import Perfil, Usuario
    from apps.encuestas.models import ExcepcionVigencia
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')

    perfil = Perfil.objects.create(
        codigo='COORD_SC', nombre='Coordinador', activo=True,
        puede_buscar_rni=True, puede_ver_reportes=True,
        puede_autorizar_excepciones=True)
    coordinador = Usuario.objects.create_user(
        codigo_usuario='COORDSC', password='SrniTest2026!',
        nombre_completo='Coord SC', email='coordsc@srni.dev', perfil=perfil,
        activo=True)

    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento='1030547250',
        numero_documento_hash=doc_hash('CC', '1030547250'),
        primer_nombre='MARIA', primer_apellido='PEREZ', genero='F',
        estado_ruv='INCLUIDO', habilitado_para_caracterizacion=False,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc))

    # Una del régimen anterior: es el histórico que hay que poder seguir viendo.
    previa = ExcepcionVigencia.objects.create(
        victima=victima, ruta='ACCIONES_CONSTITUCIONALES',
        radicado='T-2026-451', observacion='Fallo del régimen anterior',
        autorizada_por=coordinador,
        fecha_ult_caracterizacion=datetime.date(2026, 3, 14),
        vigente_hasta=datetime.date(2028, 3, 14))

    cliente = APIClient()
    cliente.force_authenticate(user=coordinador)
    return {'cliente': cliente, 'victima': victima, 'previa': previa}


def _autorizar_una(escenario):
    return escenario['cliente'].post(URL, {
        'victima_id': str(escenario['victima'].id),
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-999',
        'observacion': 'Prueba de autorización con el control retirado',
    }, format='json')


def _autorizar_lote(escenario):
    return escenario['cliente'].post(f'{URL}lote/', {
        'victima_ids': [str(escenario['victima'].id)],
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-999',
        'observacion': 'Prueba de autorización en lote con el control retirado',
    }, format='json')


# ── Con el control retirado: no se autoriza ──────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_no_se_puede_autorizar_una(escenario):
    r = _autorizar_una(escenario)

    assert r.status_code == 409
    assert 'retirado' in r.data['detail'].lower()


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_no_se_puede_autorizar_en_lote(escenario):
    """
    El camino que de verdad usa el panel: autoriza SIEMPRE por `lote/`, incluso
    una sola persona. Bloquear solo `create` habría dejado cerrada la puerta que
    nadie usa y abierta la que sí.
    """
    r = _autorizar_lote(escenario)

    assert r.status_code == 409
    assert 'retirado' in r.data['detail'].lower()


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_no_queda_ninguna_fila_nueva(escenario):
    """
    Lo que se protege no es el código de estado: es que la tabla no se ensucie.
    Se conserva como evidencia del régimen anterior, y filas VIGENTE que nadie
    otorgó por una razón real la vuelven inservible para eso.
    """
    from apps.encuestas.models import ExcepcionVigencia

    antes = ExcepcionVigencia.objects.count()
    _autorizar_una(escenario)
    _autorizar_lote(escenario)

    assert ExcepcionVigencia.objects.count() == antes


# ── Lo que sí sigue funcionando ──────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_el_historico_se_sigue_consultando(escenario):
    """Es evidencia. Retirar la regla no borra lo que se autorizó bajo ella."""
    r = escenario['cliente'].get(URL)

    assert r.status_code == 200
    filas = r.data.get('results', r.data)
    assert any(f['id'] == str(escenario['previa'].id) for f in filas)


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_se_puede_anular_una_del_regimen_anterior(escenario):
    """
    Una autorización otorgada por error antes del cambio tiene que poder
    retirarse. Bloquear también la anulación dejaría un permiso abierto para
    siempre el día que la regla se reponga.
    """
    r = escenario['cliente'].post(
        f"{URL}{escenario['previa'].id}/anular/",
        {'motivo': 'Se otorgó por error antes del cambio de régimen'},
        format='json')

    assert r.status_code == 200
    escenario['previa'].refresh_from_db()
    assert escenario['previa'].estado == 'ANULADA'


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_la_busqueda_avisa_que_el_control_esta_retirado(escenario):
    """
    Es lo que el panel usa para no ofrecer un botón que responde 409. Un botón
    que existe y falla le hace perder el tiempo a quien coordina y parece una
    falla del sistema.
    """
    r = escenario['cliente'].post(f'{URL}buscar/', {
        'tipo_documento': 'CC', 'documentos': ['1030547250'],
    }, format='json')

    assert r.status_code == 200
    assert r.data['control_vigencia_activo'] is False


# ── Con el control activo: nada cambia ───────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_se_autoriza_normalmente(escenario):
    """El default. Si esto falla, el módulo quedó inservible para el día que se reponga."""
    from apps.encuestas.models import ExcepcionVigencia

    # La previa estorba: `_autorizar_una` responde 409 si ya hay una vigente.
    escenario['previa'].anular(escenario['previa'].autorizada_por, 'limpieza')

    r = _autorizar_una(escenario)

    assert r.status_code == 201, r.data
    assert ExcepcionVigencia.objects.filter(
        victima=escenario['victima'], estado='VIGENTE').exists()


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_la_busqueda_lo_dice(escenario):
    r = escenario['cliente'].post(f'{URL}buscar/', {
        'tipo_documento': 'CC', 'documentos': ['1030547250'],
    }, format='json')

    assert r.data['control_vigencia_activo'] is True
