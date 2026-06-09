"""
Tests del módulo IA — Asistente de voz Gemini.

Cubre:
- POST /api/ia/consentimiento/ (crear, sesión no propia → 404)
- GET  /api/ia/estado/         (con y sin consentimiento)
- POST /api/ia/mapear-audio/   (sin consentimiento → 403, con consentimiento → 200, Gemini mock)
- POST /api/ia/mapear-audio/   (Gemini falla → 503)
- Autenticación requerida (401)
"""
import pytest
from datetime import date
from unittest.mock import patch
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.hogares.models import Hogar
from apps.formulario.models import (
    Instrumento,
    Capitulo,
    Pregunta,
)
from apps.encuestas.models import SesionEncuesta
from apps.ia.models import ConsentimientoIA, SesionIA


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures compartidas
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def perfil():
    return Perfil.objects.create(
        codigo='IATEST', nombre='Test IA',
        puede_buscar_rni=True, puede_caracterizar=True, activo=True,
    )


@pytest.fixture
def encuestador(perfil):
    u = Usuario.objects.create_user(
        codigo_usuario='EIIA001', password='Test123!!!!',
        nombre_completo='Encuestador IA', email='eia@srni.dev',
        perfil=perfil, activo=True,
    )
    return Usuario.objects.select_related('perfil').get(pk=u.pk)


@pytest.fixture
def otro_encuestador(perfil):
    u = Usuario.objects.create_user(
        codigo_usuario='EIIA002', password='Test123!!!!',
        nombre_completo='Otro Encuestador', email='eia2@srni.dev',
        perfil=perfil, activo=True,
    )
    return Usuario.objects.select_related('perfil').get(pk=u.pk)


@pytest.fixture
def tipo_doc():
    td, _ = TipoDocumento.objects.get_or_create(
        codigo='CC',
        defaults={'nombre': 'Cédula', 'aplica_nacionales': True, 'aplica_extranjeros': False},
    )
    return td


@pytest.fixture
def municipio():
    dep, _ = Departamento.objects.get_or_create(
        codigo_dane='11', defaults={'nombre': 'Bogotá', 'activo': True}
    )
    mun, _ = Municipio.objects.get_or_create(
        codigo_dane='11001',
        defaults={'nombre': 'Bogotá DC', 'departamento': dep, 'activo': True},
    )
    return mun


@pytest.fixture
def victima(tipo_doc, municipio):
    return Victima.objects.create(
        numero_documento='111222333',
        primer_nombre='Victima',
        primer_apellido='IA',
        fecha_nacimiento='1990-01-01',
        tipo_documento=tipo_doc,
        municipio_residencia=municipio,
    )


@pytest.fixture
def hogar(victima, municipio, encuestador):
    return Hogar.objects.create(
        autorizado=victima,
        municipio=municipio,
        creado_por=encuestador,
    )


@pytest.fixture
def instrumento():
    return Instrumento.objects.create(
        codigo='PAARI-IA', nombre='Instrumento IA Test', version='V7',
        vigente_desde=date(2021, 1, 1), activo=True,
        fuente_documental='Test IA',
    )


@pytest.fixture
def pregunta_lista(instrumento):
    capitulo = Capitulo.objects.create(
        instrumento=instrumento, codigo='T01', nombre='Tema IA',
        orden=1, nivel='PERSONA',
    )
    return Pregunta.objects.create(
        capitulo=capitulo, codigo_externo='P01', no_pregunta='P01',
        variable_bd='P01', texto='¿Tipo de vivienda?',
        tipo='LISTA', nivel='PERSONA', orden=1, obligatoria=True,
    )


@pytest.fixture
def sesion(encuestador, hogar, instrumento):
    return SesionEncuesta.objects.create(
        hogar=hogar, instrumento=instrumento, encuestador=encuestador,
    )


@pytest.fixture
def client_enc(encuestador):
    c = APIClient()
    c.force_authenticate(user=encuestador)
    return c


@pytest.fixture
def client_otro(otro_encuestador):
    c = APIClient()
    c.force_authenticate(user=otro_encuestador)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Autenticación
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_consentimiento_requiere_auth(sesion):
    c = APIClient()
    resp = c.post('/api/ia/consentimiento/', {'sesion_encuesta_id': str(sesion.id), 'acepto': True})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_estado_requiere_auth(sesion):
    c = APIClient()
    resp = c.get(f'/api/ia/estado/?sesion_encuesta_id={sesion.id}')
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Consentimiento
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_crear_consentimiento_acepta(client_enc, sesion):
    resp = client_enc.post('/api/ia/consentimiento/', {
        'sesion_encuesta_id': str(sesion.id),
        'acepto': True,
    }, format='json')
    assert resp.status_code == 201
    data = resp.json()
    assert data['acepto'] is True
    assert data['firma_digital']  # SHA-256 generado


@pytest.mark.django_db
def test_crear_consentimiento_rechaza(client_enc, sesion):
    resp = client_enc.post('/api/ia/consentimiento/', {
        'sesion_encuesta_id': str(sesion.id),
        'acepto': False,
    }, format='json')
    assert resp.status_code == 201
    assert resp.json()['acepto'] is False


@pytest.mark.django_db
def test_consentimiento_sesion_ajena_404(client_otro, sesion):
    """El encuestador B no puede consentir sobre la sesión del encuestador A."""
    resp = client_otro.post('/api/ia/consentimiento/', {
        'sesion_encuesta_id': str(sesion.id),
        'acepto': True,
    }, format='json')
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Estado IA
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_estado_sin_consentimiento(client_enc, sesion):
    resp = client_enc.get(f'/api/ia/estado/?sesion_encuesta_id={sesion.id}')
    assert resp.status_code == 200
    data = resp.json()
    assert data['activo'] is False
    assert data['consentimiento_id'] is None
    assert data['total_llamadas'] == 0


@pytest.mark.django_db
def test_estado_con_consentimiento(client_enc, sesion, encuestador):
    ConsentimientoIA.objects.create(
        sesion_encuesta=sesion, encuestador=encuestador, acepto=True
    )
    resp = client_enc.get(f'/api/ia/estado/?sesion_encuesta_id={sesion.id}')
    assert resp.status_code == 200
    data = resp.json()
    assert data['activo'] is True
    assert data['consentimiento_id'] is not None


@pytest.mark.django_db
def test_estado_sin_param_400(client_enc):
    resp = client_enc.get('/api/ia/estado/')
    assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Mapear audio
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mapear_sin_consentimiento_403(client_enc, sesion, pregunta_lista):
    resp = client_enc.post('/api/ia/mapear-audio/', {
        'sesion_encuesta_id': str(sesion.id),
        'pregunta_id': pregunta_lista.id,
        'texto_transcrito': 'Vivimos en una casa propia',
    }, format='json')
    assert resp.status_code == 403


_SUGERENCIA_MOCK = {'sugerencia': 'CASA', 'confianza': 1.0, 'modelo': 'gemini-1.5-flash'}


@pytest.mark.django_db
def test_mapear_con_consentimiento_ok(client_enc, sesion, encuestador, pregunta_lista):
    """Servicio mockeado devuelve sugerencia; verificamos respuesta 200."""
    ConsentimientoIA.objects.create(
        sesion_encuesta=sesion, encuestador=encuestador, acepto=True
    )

    with patch('apps.ia.views.mapear_texto_a_campo', return_value=_SUGERENCIA_MOCK):
        resp = client_enc.post('/api/ia/mapear-audio/', {
            'sesion_encuesta_id': str(sesion.id),
            'pregunta_id': pregunta_lista.id,
            'texto_transcrito': 'Vivimos en una casa propia',
        }, format='json')

    assert resp.status_code == 200
    data = resp.json()
    assert data['sugerencia'] == 'CASA'
    assert data['confianza'] == 1.0
    assert data['modelo'] == 'gemini-1.5-flash'


@pytest.mark.django_db
def test_mapear_registra_log_acceso(client_enc, sesion, encuestador, pregunta_lista):
    """Verificar que LLAMADA_GEMINI queda en LogAcceso."""
    from apps.auditoria.models import LogAcceso

    ConsentimientoIA.objects.create(
        sesion_encuesta=sesion, encuestador=encuestador, acepto=True
    )

    with patch('apps.ia.views.mapear_texto_a_campo', return_value=_SUGERENCIA_MOCK):
        client_enc.post('/api/ia/mapear-audio/', {
            'sesion_encuesta_id': str(sesion.id),
            'pregunta_id': pregunta_lista.id,
            'texto_transcrito': 'Tenemos un apartamento',
        }, format='json')

    assert LogAcceso.objects.filter(
        accion='LLAMADA_GEMINI',
        recurso_id=str(pregunta_lista.id),
        resultado='EXITO',
    ).exists()


@pytest.mark.django_db
def test_mapear_gemini_falla_503(client_enc, sesion, encuestador, pregunta_lista):
    """Si el servicio lanza GeminiError, la API devuelve 503 (no bloquea el formulario)."""
    from apps.ia.services import GeminiError

    ConsentimientoIA.objects.create(
        sesion_encuesta=sesion, encuestador=encuestador, acepto=True
    )

    with patch('apps.ia.views.mapear_texto_a_campo', side_effect=GeminiError('timeout')):
        resp = client_enc.post('/api/ia/mapear-audio/', {
            'sesion_encuesta_id': str(sesion.id),
            'pregunta_id': pregunta_lista.id,
            'texto_transcrito': 'casa',
        }, format='json')

    assert resp.status_code == 503


@pytest.mark.django_db
def test_mapear_incrementa_total_llamadas(client_enc, sesion, encuestador, pregunta_lista):
    """SesionIA.total_llamadas se incrementa en cada llamada exitosa."""
    ConsentimientoIA.objects.create(
        sesion_encuesta=sesion, encuestador=encuestador, acepto=True
    )

    with patch('apps.ia.views.mapear_texto_a_campo', return_value=_SUGERENCIA_MOCK):
        for _ in range(2):
            client_enc.post('/api/ia/mapear-audio/', {
                'sesion_encuesta_id': str(sesion.id),
                'pregunta_id': pregunta_lista.id,
                'texto_transcrito': 'casa propia',
            }, format='json')

    sesion_ia = SesionIA.objects.get(sesion_encuesta=sesion)
    assert sesion_ia.total_llamadas == 2
