"""
Tests del motor de formularios dinámico y skip logic.
"""
import pytest
from rest_framework.test import APIClient
from apps.autenticacion.models import Perfil, Usuario
from apps.formulario.models import Instrumento, Tema, Pregunta, OpcionRespuesta, PreguntaDerivada
from apps.formulario.views import EvaluarSkipLogicView


@pytest.fixture
def perfil():
    return Perfil.objects.create(
        codigo='ENC2',
        nombre='Encuestador Formulario',
        puede_buscar_rni=True,
        puede_caracterizar=True,
    )


@pytest.fixture
def usuario(perfil):
    return Usuario.objects.create_user(
        codigo_usuario='FTEST001',
        password='TestPass123!',
        nombre_completo='Test Formulario',
        email='formulario@srni.gov.co',
        perfil=perfil,
    )


@pytest.fixture
def cliente_auth(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


@pytest.fixture
def instrumento():
    return Instrumento.objects.create(
        codigo='PAARI-4.1',
        nombre='Protocolo de Atención',
        version='4.1',
        vigente=True,
    )


@pytest.fixture
def tema(instrumento):
    return Tema.objects.create(
        instrumento=instrumento,
        codigo='T01',
        nombre='Identificación',
        orden=1,
        activo=True,
    )


@pytest.fixture
def pregunta_genero(tema):
    p = Pregunta.objects.create(
        tema=tema, codigo='P01', texto='¿Cuál es su género?',
        tipo_respuesta='OPCION_UNICA', orden=1, requerida=True, activa=True,
    )
    OpcionRespuesta.objects.create(pregunta=p, codigo='M', texto='Masculino', orden=1)
    OpcionRespuesta.objects.create(pregunta=p, codigo='F', texto='Femenino', orden=2)
    return p


@pytest.fixture
def pregunta_embarazo(tema, pregunta_genero):
    """Solo visible si P01 == F (femenino)."""
    p = Pregunta.objects.create(
        tema=tema, codigo='P02', texto='¿Está embarazada?',
        tipo_respuesta='SINO', orden=2, requerida=False, activa=True,
    )
    PreguntaDerivada.objects.create(
        pregunta_padre=pregunta_genero,
        pregunta_hija=p,
        operador='EQ',
        valor_condicion='F',
    )
    return p


@pytest.fixture
def pregunta_edad(tema):
    return Pregunta.objects.create(
        tema=tema, codigo='P03', texto='¿Cuántos años tiene?',
        tipo_respuesta='NUMERICO', orden=3, requerida=True, activa=True,
    )


# ---------------------------------------------------------------------------
# Tests de estructura del instrumento
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstrumentoAPI:
    def test_listar_instrumentos(self, cliente_auth, instrumento):
        response = cliente_auth.get('/api/formulario/instrumentos/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_filtro_vigente(self, cliente_auth, instrumento):
        Instrumento.objects.create(
            codigo='OLD', nombre='Versión antigua', version='3.0', vigente=False
        )
        response = cliente_auth.get('/api/formulario/instrumentos/?vigente=true')
        assert response.status_code == 200
        codigos = [i['codigo'] for i in response.data['results']]
        assert 'PAARI-4.1' in codigos
        assert 'OLD' not in codigos

    def test_detalle_incluye_temas(self, cliente_auth, instrumento, tema):
        response = cliente_auth.get(f'/api/formulario/instrumentos/{instrumento.id}/')
        assert response.status_code == 200
        assert len(response.data['temas']) == 1
        assert response.data['temas'][0]['codigo'] == 'T01'


@pytest.mark.django_db
class TestTemaAPI:
    def test_detalle_incluye_preguntas(self, cliente_auth, tema, pregunta_genero):
        response = cliente_auth.get(f'/api/formulario/temas/{tema.id}/')
        assert response.status_code == 200
        assert len(response.data['preguntas']) == 1
        assert response.data['preguntas'][0]['codigo'] == 'P01'

    def test_pregunta_incluye_opciones(self, cliente_auth, tema, pregunta_genero):
        response = cliente_auth.get(f'/api/formulario/temas/{tema.id}/')
        pregunta = response.data['preguntas'][0]
        codigos_opciones = [o['codigo'] for o in pregunta['opciones']]
        assert 'M' in codigos_opciones
        assert 'F' in codigos_opciones


# ---------------------------------------------------------------------------
# Tests del motor de skip logic
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSkipLogic:
    def test_pregunta_sin_condicion_siempre_visible(
        self, cliente_auth, tema, pregunta_genero, pregunta_edad
    ):
        """P01 (género) y P03 (edad) no tienen condiciones → siempre visibles."""
        response = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'tema_id': tema.id,
            'respuestas': [],
        }, format='json')
        assert response.status_code == 200
        visibles = response.data['preguntas_visibles']
        assert pregunta_genero.id in visibles
        assert pregunta_edad.id in visibles

    def test_pregunta_con_condicion_oculta_sin_respuesta(
        self, cliente_auth, tema, pregunta_genero, pregunta_embarazo, pregunta_edad
    ):
        """P02 (embarazo) requiere P01==F. Sin respuesta, no debe aparecer."""
        response = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'tema_id': tema.id,
            'respuestas': [],
        }, format='json')
        assert response.status_code == 200
        assert pregunta_embarazo.id not in response.data['preguntas_visibles']

    def test_pregunta_habilitada_por_condicion_eq(
        self, cliente_auth, tema, pregunta_genero, pregunta_embarazo
    ):
        """P01==F habilita P02."""
        response = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'tema_id': tema.id,
            'respuestas': [{'pregunta_id': pregunta_genero.id, 'valor': 'F'}],
        }, format='json')
        assert response.status_code == 200
        assert pregunta_embarazo.id in response.data['preguntas_visibles']

    def test_pregunta_no_habilitada_condicion_no_cumplida(
        self, cliente_auth, tema, pregunta_genero, pregunta_embarazo
    ):
        """P01==M no cumple la condición P01==F → P02 oculta."""
        response = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'tema_id': tema.id,
            'respuestas': [{'pregunta_id': pregunta_genero.id, 'valor': 'M'}],
        }, format='json')
        assert response.status_code == 200
        assert pregunta_embarazo.id not in response.data['preguntas_visibles']

    def test_operador_in(self, tema, pregunta_genero):
        """Test del operador IN internamente."""
        pregunta_extra = Pregunta.objects.create(
            tema=tema, codigo='P04', texto='Extra', tipo_respuesta='TEXTO',
            orden=4, requerida=False, activa=True,
        )
        condicion = PreguntaDerivada.objects.create(
            pregunta_padre=pregunta_genero,
            pregunta_hija=pregunta_extra,
            operador='IN',
            valor_condicion='M, NB, ND',
        )
        # M está en la lista
        assert EvaluarSkipLogicView._evaluar(
            condicion, {pregunta_genero.id: 'M'}
        ) is True
        # F no está en la lista
        assert EvaluarSkipLogicView._evaluar(
            condicion, {pregunta_genero.id: 'F'}
        ) is False

    def test_operador_notnull(self, tema, pregunta_genero):
        pregunta_extra = Pregunta.objects.create(
            tema=tema, codigo='P05', texto='Extra NOTNULL', tipo_respuesta='TEXTO',
            orden=5, requerida=False, activa=True,
        )
        condicion = PreguntaDerivada.objects.create(
            pregunta_padre=pregunta_genero,
            pregunta_hija=pregunta_extra,
            operador='NOTNULL',
            valor_condicion='',
        )
        assert EvaluarSkipLogicView._evaluar(
            condicion, {pregunta_genero.id: 'cualquier_valor'}
        ) is True
        assert EvaluarSkipLogicView._evaluar(
            condicion, {pregunta_genero.id: ''}
        ) is False

    def test_operador_gt(self, tema, pregunta_edad):
        pregunta_extra = Pregunta.objects.create(
            tema=tema, codigo='P06', texto='Adulto mayor', tipo_respuesta='SINO',
            orden=6, requerida=False, activa=True,
        )
        condicion = PreguntaDerivada.objects.create(
            pregunta_padre=pregunta_edad,
            pregunta_hija=pregunta_extra,
            operador='GT',
            valor_condicion='60',
        )
        assert EvaluarSkipLogicView._evaluar(
            condicion, {pregunta_edad.id: '65'}
        ) is True
        assert EvaluarSkipLogicView._evaluar(
            condicion, {pregunta_edad.id: '30'}
        ) is False
