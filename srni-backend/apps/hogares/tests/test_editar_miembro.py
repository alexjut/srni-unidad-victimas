"""
APK-004 — corregir o quitar un integrante capturado por error.

Hasta el 14-ago-2026 se podía agregar un integrante al hogar pero no corregirlo
ni quitarlo: no existía la operación ni en la API ni en la app. Quien se
equivocaba al capturar quedaba con el error adentro del hogar para siempre.

Quitar acá **borra la fila**, y es a propósito: atiende el caso de «esta persona
nunca debió estar». «Ya no vive en el hogar» es otra cosa —un hecho histórico
que pide una novedad hacia el legado— y por eso la operación está acotada a
hogares sin caracterización completada.
"""
import datetime

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def escenario(db):
    from apps.autenticacion.models import Perfil, Usuario
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)

    def victima(doc, nombre):
        return Victima.objects.create(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=doc_hash('CC', doc),
            primer_nombre=nombre, primer_apellido='PEREZ',
            genero='F', estado_ruv='INCLUIDO',
            habilitado_para_caracterizacion=True,
            pertenencia_etnica='NINGUNA', discapacidad=False,
            municipio_residencia=muni)

    autorizada = victima('1030547250', 'MARIA')
    hija = victima('9990100001', 'ANA')

    perfil = Perfil.objects.create(codigo='ENC_EM', nombre='Encuestador',
                                   puede_caracterizar=True, puede_buscar_rni=True,
                                   activo=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario='EMTEST', password='SrniTest2026!', nombre_completo='EM Test',
        email='em@srni.dev', perfil=perfil, activo=True)

    hogar = Hogar.objects.create(autorizado=autorizada, creado_por=usuario,
                                 municipio=muni)
    titular = MiembroHogar.objects.create(
        hogar=hogar, victima=autorizada, tipo_documento=tipo, es_autorizado=True)
    miembro = MiembroHogar.objects.create(
        hogar=hogar, victima=hija, tipo_documento=tipo, parentesco='HIJO_A',
        genero='F')

    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return {'cliente': cliente, 'hogar': hogar, 'miembro': miembro,
            'titular': titular, 'usuario': usuario, 'muni': muni}


def url(hogar, miembro):
    return f'/api/hogares/{hogar.id}/miembros/{miembro.id}/'


def test_se_puede_quitar_un_integrante_agregado_por_error(escenario):
    from apps.hogares.models import MiembroHogar

    r = escenario['cliente'].delete(url(escenario['hogar'], escenario['miembro']))

    assert r.status_code == 204
    assert not MiembroHogar.objects.filter(pk=escenario['miembro'].id).exists()


def test_se_puede_corregir_el_parentesco(escenario):
    """El caso típico: se marcó HIJO/A y era NIETO/A."""
    r = escenario['cliente'].patch(
        url(escenario['hogar'], escenario['miembro']),
        {'parentesco': 'NIETO_A'}, format='json')

    assert r.status_code == 200, r.data
    escenario['miembro'].refresh_from_db()
    assert escenario['miembro'].parentesco == 'NIETO_A'


def test_al_autorizado_no_se_le_toca(escenario):
    """
    Es el titular del hogar: quitarlo dejaría un hogar sin dueño, y hay una
    operación propia para cambiarlo.
    """
    r = escenario['cliente'].delete(url(escenario['hogar'], escenario['titular']))

    assert r.status_code == 409
    assert 'titular' in r.data['detail']


def test_no_se_quita_de_un_hogar_ya_caracterizado(escenario):
    """
    La guarda que acota la operación. Con una encuesta COMPLETADA, ese
    integrante forma parte de algo ya reportado y borrarlo cambiaría un dato
    entregado — eso es una novedad hacia el legado, no una corrección de captura.
    """
    from apps.encuestas.models import SesionEncuesta
    from apps.formulario.models import Instrumento

    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL_EM', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))
    SesionEncuesta.objects.create(
        hogar=escenario['hogar'], instrumento=instrumento, estado='COMPLETADA')

    r = escenario['cliente'].delete(url(escenario['hogar'], escenario['miembro']))

    assert r.status_code == 409
    assert 'coordinación' in r.data['detail']


def test_una_sesion_a_medias_no_bloquea_la_correccion(escenario):
    """
    Solo bloquea lo COMPLETADO. Si bloqueara con la encuesta abierta, el
    encuestador no podría corregir justo cuando se da cuenta del error: en plena
    entrevista.
    """
    from apps.encuestas.models import SesionEncuesta
    from apps.formulario.models import Instrumento

    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL_EM2', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))
    SesionEncuesta.objects.create(
        hogar=escenario['hogar'], instrumento=instrumento, estado='INICIADA')

    r = escenario['cliente'].delete(url(escenario['hogar'], escenario['miembro']))

    assert r.status_code == 204


def test_no_se_toca_un_miembro_de_otro_hogar(escenario):
    """El id del hogar en la URL no es decorativo."""
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash
    from apps.parametricas.models import TipoDocumento

    tipo = TipoDocumento.objects.get(codigo='CC')
    otra = Victima.objects.create(
        tipo_documento=tipo, numero_documento='9990100002',
        numero_documento_hash=doc_hash('CC', '9990100002'),
        primer_nombre='LUZ', primer_apellido='DIAZ', genero='F',
        estado_ruv='INCLUIDO', habilitado_para_caracterizacion=True,
        pertenencia_etnica='NINGUNA', discapacidad=False)
    otro_hogar = Hogar.objects.create(autorizado=otra, municipio=escenario['muni'],
                                      creado_por=escenario['usuario'])

    r = escenario['cliente'].delete(url(otro_hogar, escenario['miembro']))

    assert r.status_code == 404


def test_quitar_queda_en_la_auditoria(escenario):
    """
    Quitar a alguien de un hogar es lo que una auditoría va a querer buscar.
    Con la acción de AGREGAR_MIEMBRO quedaría escondido entre las altas.
    """
    from apps.auditoria.models import LogAcceso

    escenario['cliente'].delete(url(escenario['hogar'], escenario['miembro']))

    assert LogAcceso.objects.filter(accion='QUITAR_MIEMBRO').exists()
