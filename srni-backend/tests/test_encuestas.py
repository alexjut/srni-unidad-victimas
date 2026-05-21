"""
Tests de Encuestas: crear sesión, responder preguntas, finalizar, porcentaje.
"""
import pytest
from datetime import date
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.hogares.models import Hogar
from apps.formulario.models import (
    Perfil as PerfilInstrumento,
    InstrumentoVersion,
    Capitulo,
    Pregunta,
    OpcionRespuesta,
)
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta


@pytest.fixture
def perfil_enc():
    return Perfil.objects.create(
        codigo='ETEST', nombre='Test Encuestas',
        puede_buscar_rni=True, puede_caracterizar=True, activo=True,
    )


@pytest.fixture
def encuestador(perfil_enc):
    u = Usuario.objects.create_user(
        codigo_usuario='EENC001', password='Test123!!!!',
        nombre_completo='Encuestador Encuestas', email='eenc@srni.dev',
        perfil=perfil_enc, activo=True,
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
    dep = Departamento.objects.create(codigo_dane='76', nombre='Valle del Cauca', activo=True)
    return Municipio.objects.create(
        codigo_dane='76001', nombre='Cali', departamento=dep, activo=True
    )


@pytest.fixture
def victima(tipo_doc, municipio, encuestador):
    return Victima.objects.create(
        tipo_documento=tipo_doc, numero_documento='999888777',
        primer_nombre='Carlos', segundo_nombre='',
        primer_apellido='López', segundo_apellido='',
        fecha_nacimiento='1975-06-20',
        genero='M', estado_civil='CASADO',
        pertenencia_etnica='NINGUNA', estado_ruv='INCLUIDO',
        municipio_residencia=municipio, creado_por=encuestador,
    )


@pytest.fixture
def hogar(victima, municipio, encuestador):
    return Hogar.objects.create(
        jefe_hogar=victima, municipio=municipio,
        tipo_vivienda='APARTAMENTO', condicion_ocupacion='PROPIA',
        numero_personas=3, creado_por=encuestador,
    )


@pytest.fixture
def instrumento():
    perfil_inst = PerfilInstrumento.objects.create(
        codigo='PAARI-TEST', nombre='PAARI Test', activo=True,
    )
    version = InstrumentoVersion.objects.create(
        perfil=perfil_inst, numero='V7',
        vigente_desde=date(2021, 1, 1),
        fuente_documental='Test Encuestas',
    )
    capitulo = Capitulo.objects.create(
        instrumento=version, codigo='T01', nombre='Identificación',
        orden=1, nivel='PERSONA',
    )
    # 3 preguntas obligatorias
    p1 = Pregunta.objects.create(
        capitulo=capitulo, codigo_externo='P01', no_pregunta='P01',
        variable_bd='P01', texto='¿Género?',
        tipo='RADIO', nivel='PERSONA', orden=1, obligatoria=True,
    )
    OpcionRespuesta.objects.bulk_create([
        OpcionRespuesta(pregunta=p1, valor='M', etiqueta='Masculino', orden=1),
        OpcionRespuesta(pregunta=p1, valor='F', etiqueta='Femenino', orden=2),
    ])
    Pregunta.objects.create(
        capitulo=capitulo, codigo_externo='P02', no_pregunta='P02',
        variable_bd='P02', texto='¿Edad?',
        tipo='NUMERICO', nivel='PERSONA', orden=2, obligatoria=True,
    )
    Pregunta.objects.create(
        capitulo=capitulo, codigo_externo='P03', no_pregunta='P03',
        variable_bd='P03', texto='¿Estrato?',
        tipo='NUMERICO', nivel='PERSONA', orden=3, obligatoria=True,
    )
    return version


@pytest.fixture
def sesion(hogar, instrumento, encuestador):
    return SesionEncuesta.objects.create(
        hogar=hogar, instrumento=instrumento, encuestador=encuestador,
        estado='INICIADA',
    )


@pytest.fixture
def client_enc(encuestador):
    c = APIClient()
    c.force_authenticate(user=encuestador)
    return c


# ---------------------------------------------------------------------------
# Tests de sesiones
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCrearSesion:
    def test_crear_sesion_exitosa(self, client_enc, hogar, instrumento):
        r = client_enc.post('/api/encuestas/', {
            'hogar': str(hogar.id),
            'instrumento': str(instrumento.id),
        }, format='json')
        assert r.status_code == 201, r.data
        assert r.data['estado'] == 'INICIADA'
        assert r.data['porcentaje_completado'] == 0

    def test_encuestador_solo_ve_sus_sesiones(self, client_enc, sesion, hogar, instrumento):
        # Otro encuestador con otra sesión
        perfil2 = Perfil.objects.create(
            codigo='ENC2B', nombre='Enc2', puede_caracterizar=True, activo=True,
        )
        enc2_user = Usuario.objects.create_user(
            codigo_usuario='ENC002B', password='Test123!!!!',
            nombre_completo='Otro', email='enc2b@srni.dev',
            perfil=perfil2, activo=True,
        )
        enc2 = Usuario.objects.select_related('perfil').get(pk=enc2_user.pk)
        SesionEncuesta.objects.create(
            hogar=hogar, instrumento=instrumento, encuestador=enc2, estado='INICIADA',
        )
        r = client_enc.get('/api/encuestas/')
        assert r.status_code == 200
        ids = [s['id'] for s in r.data['results']]
        assert str(sesion.id) in ids
        assert len(ids) == 1


@pytest.mark.django_db
class TestResponderPreguntas:
    def test_responder_pregunta(self, client_enc, sesion, instrumento):
        pregunta = Pregunta.objects.get(
            capitulo__instrumento=instrumento, codigo_externo='P01'
        )
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': str(pregunta.id),
            'valor': 'M',
        }, format='json')
        assert r.status_code == 201
        assert r.data['valor'] == 'M'

    def test_responder_actualiza_estado_a_en_progreso(self, client_enc, sesion, instrumento):
        pregunta = Pregunta.objects.get(
            capitulo__instrumento=instrumento, codigo_externo='P01'
        )
        client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': str(pregunta.id), 'valor': 'F',
        }, format='json')
        sesion.refresh_from_db()
        assert sesion.estado == 'EN_PROGRESO'

    def test_responder_actualiza_porcentaje(self, client_enc, sesion, instrumento):
        preguntas = list(
            Pregunta.objects.filter(capitulo__instrumento=instrumento).order_by('orden')
        )
        # Responder 1 de 3 preguntas obligatorias → ~33%
        client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': str(preguntas[0].id), 'valor': 'M',
        }, format='json')
        sesion.refresh_from_db()
        assert sesion.porcentaje_completado == 33

    def test_upsert_respuesta_existente(self, client_enc, sesion, instrumento):
        pregunta = Pregunta.objects.get(
            capitulo__instrumento=instrumento, codigo_externo='P01'
        )
        client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': str(pregunta.id), 'valor': 'M',
        }, format='json')
        # Actualizar la misma respuesta
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': str(pregunta.id), 'valor': 'F',
        }, format='json')
        assert r.status_code == 200  # Update, no create
        assert r.data['valor'] == 'F'
        assert RespuestaEncuesta.objects.filter(sesion=sesion, pregunta=pregunta).count() == 1

    def test_pregunta_de_otro_instrumento_retorna_400(self, client_enc, sesion):
        otro_perfil = PerfilInstrumento.objects.create(
            codigo='OTRO-PERF', nombre='Otro Perfil', activo=True,
        )
        otra_version = InstrumentoVersion.objects.create(
            perfil=otro_perfil, numero='V1',
            vigente_desde=date(2021, 1, 1),
        )
        otro_cap = Capitulo.objects.create(
            instrumento=otra_version, codigo='OT1', nombre='Otro',
            orden=1, nivel='HOGAR',
        )
        pregunta_ajena = Pregunta.objects.create(
            capitulo=otro_cap, codigo_externo='OX1', no_pregunta='OX1',
            variable_bd='OX1', texto='Ajena',
            tipo='TEXTO', nivel='HOGAR', orden=1, obligatoria=True,
        )
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': str(pregunta_ajena.id), 'valor': 'x',
        }, format='json')
        assert r.status_code == 400

    def test_sesion_completada_rechaza_respuestas(self, client_enc, sesion, instrumento):
        sesion.estado = 'COMPLETADA'
        sesion.save(update_fields=['estado'])
        pregunta = Pregunta.objects.get(
            capitulo__instrumento=instrumento, codigo_externo='P01'
        )
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': str(pregunta.id), 'valor': 'M',
        }, format='json')
        assert r.status_code == 400


@pytest.mark.django_db
class TestFinalizarSesion:
    def test_finalizar_sesion(self, client_enc, sesion, instrumento):
        # Responder todas las preguntas
        for p in Pregunta.objects.filter(capitulo__instrumento=instrumento):
            client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
                'pregunta_id': str(p.id), 'valor': 'X',
            }, format='json')

        r = client_enc.post(f'/api/encuestas/{sesion.id}/finalizar/', {
            'observaciones': 'Encuesta finalizada correctamente.',
        }, format='json')
        assert r.status_code == 200
        assert r.data['estado'] == 'COMPLETADA'
        assert r.data['porcentaje_completado'] == 100
        assert r.data['fecha_fin'] is not None

    def test_finalizar_dos_veces_retorna_400(self, client_enc, sesion):
        sesion.estado = 'COMPLETADA'
        sesion.save(update_fields=['estado'])
        r = client_enc.post(f'/api/encuestas/{sesion.id}/finalizar/', {}, format='json')
        assert r.status_code == 400

    def test_porcentaje_parcial(self, client_enc, sesion, instrumento):
        """Con 2 de 3 preguntas respondidas, el porcentaje debe ser 66."""
        preguntas = list(Pregunta.objects.filter(
            capitulo__instrumento=instrumento, obligatoria=True
        ).order_by('orden'))
        for p in preguntas[:2]:
            client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
                'pregunta_id': str(p.id), 'valor': 'X',
            }, format='json')

        r = client_enc.post(f'/api/encuestas/{sesion.id}/finalizar/', {}, format='json')
        assert r.status_code == 200
        assert r.data['porcentaje_completado'] == 66
