"""
Tests del motor de formularios dinámico y skip logic.

Actualizado al esquema vigente (Instrumento plano — un único modelo en lugar
de Perfil + InstrumentoVersion) y a los endpoints actuales de la app formulario:
  - GET  /api/formulario/instrumentos/
  - GET  /api/formulario/capitulos/?instrumento=<id>
  - GET  /api/formulario/instrumento/<codigo>/
  - POST /api/formulario/evaluar-skip-logic/
"""
import pytest
from datetime import date
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.formulario.models import (
    Instrumento,
    Capitulo,
    Pregunta,
    OpcionRespuesta,
    ReglaSkipLogic,
    AccionSkipChoices,
)
from apps.formulario.views import EvaluarSkipLogicView


# ─── Fixtures de usuario ───────────────────────────────────────────────────────

@pytest.fixture
def perfil_usuario():
    return Perfil.objects.create(
        codigo='FTEST', nombre='Test Formulario',
        puede_buscar_rni=True, puede_caracterizar=True,
    )


@pytest.fixture
def usuario(perfil_usuario):
    return Usuario.objects.create_user(
        codigo_usuario='FTEST001', password='TestPass123!',
        nombre_completo='Test Formulario', email='formulario@srni.gov.co',
        perfil=perfil_usuario,
    )


@pytest.fixture
def cliente_auth(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


# ─── Fixtures del instrumento ──────────────────────────────────────────────────

@pytest.fixture
def instrumento():
    return Instrumento.objects.create(
        codigo='TERRITORIAL', nombre='Perfil Territorial', version='V7',
        vigente_desde=date(2021, 1, 1), activo=True,
        fuente_documental='Manual UARIV 520.06.06-1',
    )


@pytest.fixture
def capitulo(instrumento):
    return Capitulo.objects.create(
        instrumento=instrumento, codigo='B',
        nombre='Datos Básicos e Identidad',
        orden=2, nivel='PERSONA',
    )


@pytest.fixture
def pregunta_genero(capitulo):
    p = Pregunta.objects.create(
        capitulo=capitulo, codigo_externo='B1', no_pregunta='B1',
        variable_bd='B1', texto='¿Cuál es su sexo?',
        tipo='RADIO', nivel='PERSONA', orden=1, obligatoria=True,
    )
    OpcionRespuesta.objects.create(pregunta=p, valor='M', etiqueta='Masculino', orden=1)
    OpcionRespuesta.objects.create(pregunta=p, valor='F', etiqueta='Femenino', orden=2)
    return p


@pytest.fixture
def pregunta_embarazo(capitulo, instrumento, pregunta_genero):
    """Solo visible si B1 == F (sexo femenino)."""
    p = Pregunta.objects.create(
        capitulo=capitulo, codigo_externo='B2', no_pregunta='B2',
        variable_bd='B2', texto='¿Está embarazada o en período de lactancia?',
        tipo='BOOLEAN', nivel='PERSONA', orden=2, obligatoria=False,
    )
    # Sin respuesta a B1 → deshabilitada por defecto
    ReglaSkipLogic.objects.create(
        instrumento=instrumento, pregunta_origen=pregunta_genero,
        valor_trigger='F', pregunta_afectada=p,
        accion=AccionSkipChoices.HABILITAR,
    )
    return p


@pytest.fixture
def pregunta_edad(capitulo):
    return Pregunta.objects.create(
        capitulo=capitulo, codigo_externo='B3', no_pregunta='B3',
        variable_bd='B3', texto='¿Cuántos años cumplidos tiene?',
        tipo='NUMERICO', nivel='PERSONA', orden=3, obligatoria=True,
    )


# ─── Tests: estructura del instrumento via API ─────────────────────────────────

@pytest.mark.django_db
class TestInstrumentosAPI:
    def test_listar_instrumentos(self, cliente_auth, instrumento):
        resp = cliente_auth.get('/api/formulario/instrumentos/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 1

    def test_solo_instrumentos_activos(self, cliente_auth, instrumento):
        Instrumento.objects.create(
            codigo='INACTIVO', nombre='Inactivo', version='V1',
            vigente_desde=date(2021, 1, 1), activo=False,
        )
        resp = cliente_auth.get('/api/formulario/instrumentos/')
        codigos = [i['codigo'] for i in resp.data['results']]
        assert 'TERRITORIAL' in codigos
        assert 'INACTIVO' not in codigos

    def test_detalle_incluye_capitulos(self, cliente_auth, instrumento, capitulo):
        resp = cliente_auth.get(f'/api/formulario/instrumentos/{instrumento.id}/')
        assert resp.status_code == 200
        assert resp.data['codigo'] == 'TERRITORIAL'
        assert resp.data['version'] == 'V7'
        codigos_cap = [c['codigo'] for c in resp.data['capitulos']]
        assert 'B' in codigos_cap


@pytest.mark.django_db
class TestCapituloAPI:
    def test_listar_capitulos_por_instrumento(self, cliente_auth, instrumento, capitulo):
        resp = cliente_auth.get(f'/api/formulario/capitulos/?instrumento={instrumento.id}')
        assert resp.status_code == 200
        codigos = [c['codigo'] for c in resp.data['results']]
        assert 'B' in codigos

    def test_detalle_capitulo_incluye_preguntas(
        self, cliente_auth, capitulo, pregunta_genero
    ):
        resp = cliente_auth.get(f'/api/formulario/capitulos/{capitulo.id}/')
        assert resp.status_code == 200
        assert len(resp.data['preguntas']) == 1
        assert resp.data['preguntas'][0]['codigo_externo'] == 'B1'

    def test_pregunta_incluye_opciones(self, cliente_auth, capitulo, pregunta_genero):
        resp = cliente_auth.get(f'/api/formulario/capitulos/{capitulo.id}/')
        opciones = resp.data['preguntas'][0]['opciones']
        valores = [o['valor'] for o in opciones]
        assert 'M' in valores
        assert 'F' in valores


@pytest.mark.django_db
class TestInstrumentoCompletoAPI:
    def test_descarga_completa(self, cliente_auth, instrumento, capitulo, pregunta_genero):
        resp = cliente_auth.get('/api/formulario/instrumento/TERRITORIAL/')
        assert resp.status_code == 200
        data = resp.data
        assert data['codigo'] == 'TERRITORIAL'
        assert data['version'] == 'V7'
        assert len(data['capitulos']) == 1
        cap = data['capitulos'][0]
        assert cap['codigo'] == 'B'
        assert len(cap['preguntas']) == 1
        assert cap['preguntas'][0]['codigo_externo'] == 'B1'

    def test_instrumento_no_existe_404(self, cliente_auth):
        resp = cliente_auth.get('/api/formulario/instrumento/INEXISTENTE/')
        assert resp.status_code == 404

    def test_no_autenticado_401(self, instrumento):
        resp = APIClient().get('/api/formulario/instrumento/TERRITORIAL/')
        assert resp.status_code == 401


# ─── Tests: motor de skip logic ───────────────────────────────────────────────

@pytest.mark.django_db
class TestSkipLogic:
    def test_pregunta_sin_regla_siempre_visible(
        self, cliente_auth, capitulo, pregunta_genero, pregunta_edad
    ):
        """B1 (sexo) y B3 (edad) sin reglas → siempre visibles."""
        resp = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'capitulo_id': str(capitulo.id),
            'respuestas': [],
        }, format='json')
        assert resp.status_code == 200
        visibles = resp.data['preguntas_visibles']
        assert 'B1' in visibles
        assert 'B3' in visibles

    def test_pregunta_con_regla_oculta_sin_respuesta(
        self, cliente_auth, capitulo, pregunta_genero, pregunta_embarazo, pregunta_edad
    ):
        """B2 tiene regla HABILITAR cuando B1==F. Sin respuesta → no aparece."""
        resp = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'capitulo_id': str(capitulo.id),
            'respuestas': [],
        }, format='json')
        assert resp.status_code == 200
        assert 'B2' not in resp.data['preguntas_visibles']

    def test_pregunta_habilitada_cuando_condicion_cumplida(
        self, cliente_auth, capitulo, pregunta_genero, pregunta_embarazo
    ):
        """B1==F → habilita B2."""
        resp = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'capitulo_id': str(capitulo.id),
            'respuestas': [{'codigo_externo': 'B1', 'valor': 'F'}],
        }, format='json')
        assert resp.status_code == 200
        assert 'B2' in resp.data['preguntas_visibles']

    def test_pregunta_no_habilitada_condicion_incumplida(
        self, cliente_auth, capitulo, pregunta_genero, pregunta_embarazo
    ):
        """B1==M no cumple la condición B1==F → B2 no visible."""
        resp = cliente_auth.post('/api/formulario/evaluar-skip-logic/', {
            'capitulo_id': str(capitulo.id),
            'respuestas': [{'codigo_externo': 'B1', 'valor': 'M'}],
        }, format='json')
        assert resp.status_code == 200
        assert 'B2' not in resp.data['preguntas_visibles']

    def test_regla_activa_valor_exacto(self, instrumento, pregunta_genero, pregunta_embarazo):
        """Test unitario de _regla_activa con valor exacto."""
        regla = ReglaSkipLogic.objects.get(
            pregunta_origen=pregunta_genero,
            pregunta_afectada=pregunta_embarazo,
        )
        assert EvaluarSkipLogicView._regla_activa(regla, {'B1': 'F'}, {}) is True
        assert EvaluarSkipLogicView._regla_activa(regla, {'B1': 'M'}, {}) is False

    def test_regla_activa_expresion_contexto(self, instrumento, capitulo):
        """Regla basada en expresión de contexto (edad, RUV)."""
        p_destino = Pregunta.objects.create(
            capitulo=capitulo, codigo_externo='L1', variable_bd='L1',
            texto='¿Fue víctima de reclutamiento?',
            tipo='BOOLEAN', nivel='PERSONA', orden=10,
        )
        regla = ReglaSkipLogic.objects.create(
            instrumento=instrumento,
            expresion_origen='edad >= 15',
            pregunta_afectada=p_destino,
            accion=AccionSkipChoices.HABILITAR,
        )
        assert EvaluarSkipLogicView._regla_activa(regla, {}, {'edad': 18}) is True
        assert EvaluarSkipLogicView._regla_activa(regla, {}, {'edad': 10}) is False
