"""
Tests de Encuestas: crear sesión, responder preguntas, finalizar, porcentaje.
"""
import pytest
from rest_framework.test import APIClient
from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.hogares.models import Hogar
from apps.formulario.models import Instrumento, Tema, Pregunta, OpcionRespuesta
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
    inst = Instrumento.objects.create(
        codigo='PAARI-TEST', nombre='PAARI Test', version='1.0', vigente=True,
    )
    tema = Tema.objects.create(
        instrumento=inst, codigo='T01', nombre='Identificación', orden=1, activo=True,
    )
    # 3 preguntas requeridas
    p1 = Pregunta.objects.create(
        tema=tema, codigo='P01', texto='¿Género?',
        tipo_respuesta='OPCION_UNICA', orden=1, requerida=True, activa=True,
    )
    OpcionRespuesta.objects.bulk_create([
        OpcionRespuesta(pregunta=p1, codigo='M', texto='Masculino', orden=1),
        OpcionRespuesta(pregunta=p1, codigo='F', texto='Femenino', orden=2),
    ])
    Pregunta.objects.create(
        tema=tema, codigo='P02', texto='¿Edad?',
        tipo_respuesta='NUMERICO', orden=2, requerida=True, activa=True,
    )
    Pregunta.objects.create(
        tema=tema, codigo='P03', texto='¿Estrato?',
        tipo_respuesta='NUMERICO', orden=3, requerida=True, activa=True,
    )
    return inst


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
            'instrumento': instrumento.id,
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
            tema__instrumento=instrumento, codigo='P01'
        )
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': pregunta.id,
            'valor': 'M',
        }, format='json')
        assert r.status_code == 201
        assert r.data['valor'] == 'M'

    def test_responder_actualiza_estado_a_en_progreso(self, client_enc, sesion, instrumento):
        pregunta = Pregunta.objects.get(tema__instrumento=instrumento, codigo='P01')
        client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': pregunta.id, 'valor': 'F',
        }, format='json')
        sesion.refresh_from_db()
        assert sesion.estado == 'EN_PROGRESO'

    def test_responder_actualiza_porcentaje(self, client_enc, sesion, instrumento):
        preguntas = list(Pregunta.objects.filter(tema__instrumento=instrumento).order_by('orden'))
        # Responder 1 de 3 preguntas requeridas → ~33%
        client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': preguntas[0].id, 'valor': 'M',
        }, format='json')
        sesion.refresh_from_db()
        assert sesion.porcentaje_completado == 33

    def test_upsert_respuesta_existente(self, client_enc, sesion, instrumento):
        pregunta = Pregunta.objects.get(tema__instrumento=instrumento, codigo='P01')
        client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': pregunta.id, 'valor': 'M',
        }, format='json')
        # Actualizar la misma respuesta
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': pregunta.id, 'valor': 'F',
        }, format='json')
        assert r.status_code == 200  # Update, no create
        assert r.data['valor'] == 'F'
        assert RespuestaEncuesta.objects.filter(sesion=sesion, pregunta=pregunta).count() == 1

    def test_pregunta_de_otro_instrumento_retorna_400(self, client_enc, sesion):
        otro_inst = Instrumento.objects.create(
            codigo='OTRO', nombre='Otro', version='1.0', vigente=True,
        )
        otro_tema = Tema.objects.create(
            instrumento=otro_inst, codigo='OT1', nombre='Otro', orden=1, activo=True,
        )
        pregunta_ajena = Pregunta.objects.create(
            tema=otro_tema, codigo='OX1', texto='Ajena', tipo_respuesta='TEXTO',
            orden=1, requerida=True, activa=True,
        )
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': pregunta_ajena.id, 'valor': 'x',
        }, format='json')
        assert r.status_code == 400

    def test_sesion_completada_rechaza_respuestas(self, client_enc, sesion, instrumento):
        sesion.estado = 'COMPLETADA'
        sesion.save(update_fields=['estado'])
        pregunta = Pregunta.objects.get(tema__instrumento=instrumento, codigo='P01')
        r = client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
            'pregunta_id': pregunta.id, 'valor': 'M',
        }, format='json')
        assert r.status_code == 400


@pytest.mark.django_db
class TestFinalizarSesion:
    def test_finalizar_sesion(self, client_enc, sesion, instrumento):
        # Responder todas las preguntas
        for p in Pregunta.objects.filter(tema__instrumento=instrumento):
            client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
                'pregunta_id': p.id, 'valor': 'X',
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
            tema__instrumento=instrumento, requerida=True
        ).order_by('orden'))
        for p in preguntas[:2]:
            client_enc.post(f'/api/encuestas/{sesion.id}/responder/', {
                'pregunta_id': p.id, 'valor': 'X',
            }, format='json')

        r = client_enc.post(f'/api/encuestas/{sesion.id}/finalizar/', {}, format='json')
        assert r.status_code == 200
        assert r.data['porcentaje_completado'] == 66
