"""
Tests de paramétricas: serializers, endpoints y management commands.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import Departamento, Municipio, TipoDocumento
from apps.parametricas.serializers import DepartamentoSerializer, MunicipioSerializer


@pytest.fixture
def perfil():
    return Perfil.objects.create(
        codigo='ENC',
        nombre='Encuestador',
        puede_buscar_rni=True,
        puede_caracterizar=True,
    )


@pytest.fixture
def usuario(perfil):
    return Usuario.objects.create_user(
        codigo_usuario='TEST001',
        password='TestPass123!',
        nombre_completo='Usuario Test',
        email='test@srni.gov.co',
        perfil=perfil,
    )


@pytest.fixture
def cliente_auth(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


@pytest.fixture
def departamento():
    return Departamento.objects.create(codigo_dane='05', nombre='Antioquia', activo=True)


@pytest.fixture
def municipio(departamento):
    return Municipio.objects.create(
        codigo_dane='05001', nombre='Medellín', departamento=departamento, activo=True
    )


# ---------------------------------------------------------------------------
# Tests de serializers
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDepartamentoSerializer:
    def test_campos_presentes(self, departamento):
        data = DepartamentoSerializer(departamento).data
        assert set(data.keys()) == {'id', 'codigo_dane', 'nombre', 'activo'}

    def test_valores_correctos(self, departamento):
        data = DepartamentoSerializer(departamento).data
        assert data['codigo_dane'] == '05'
        assert data['nombre'] == 'Antioquia'
        assert data['activo'] is True


@pytest.mark.django_db
class TestMunicipioSerializer:
    def test_campos_anidados(self, municipio):
        data = MunicipioSerializer(municipio).data
        assert data['departamento_nombre'] == 'Antioquia'
        assert data['departamento_codigo'] == '05'
        assert data['codigo_dane'] == '05001'


# ---------------------------------------------------------------------------
# Tests de endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDepartamentosAPI:
    def test_listado_requiere_auth(self):
        client = APIClient()
        response = client.get('/api/parametricas/departamentos/')
        assert response.status_code == 401

    def test_listado_con_auth(self, cliente_auth, departamento):
        response = cliente_auth.get('/api/parametricas/departamentos/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_filtro_activo(self, cliente_auth, departamento):
        Departamento.objects.create(codigo_dane='99', nombre='Inactivo', activo=False)
        response = cliente_auth.get('/api/parametricas/departamentos/?activo=true')
        assert response.status_code == 200
        codigos = [d['codigo_dane'] for d in response.data['results']]
        assert '99' not in codigos

    def test_busqueda_por_nombre(self, cliente_auth, departamento):
        response = cliente_auth.get('/api/parametricas/departamentos/?search=Antio')
        assert response.status_code == 200
        assert response.data['count'] >= 1


@pytest.mark.django_db
class TestMunicipiosAPI:
    def test_filtro_por_departamento(self, cliente_auth, municipio):
        depto_id = municipio.departamento.id
        response = cliente_auth.get(f'/api/parametricas/municipios/?departamento={depto_id}')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_detalle_incluye_departamento(self, cliente_auth, municipio):
        response = cliente_auth.get(f'/api/parametricas/municipios/{municipio.id}/')
        assert response.status_code == 200
        assert response.data['departamento_nombre'] == 'Antioquia'


@pytest.mark.django_db
class TestTiposDocumentoAPI:
    def test_listado(self, cliente_auth):
        TipoDocumento.objects.create(
            codigo='CC', nombre='Cédula de Ciudadanía',
            aplica_nacionales=True, aplica_extranjeros=False,
        )
        response = cliente_auth.get('/api/parametricas/tipos-documento/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_filtro_nacionales(self, cliente_auth):
        TipoDocumento.objects.create(
            codigo='CC', nombre='Cédula de Ciudadanía',
            aplica_nacionales=True, aplica_extranjeros=False,
        )
        TipoDocumento.objects.create(
            codigo='CE', nombre='Cédula de Extranjería',
            aplica_nacionales=False, aplica_extranjeros=True,
        )
        response = cliente_auth.get('/api/parametricas/tipos-documento/?aplica_nacionales=true')
        assert response.status_code == 200
        codigos = [t['codigo'] for t in response.data['results']]
        assert 'CC' in codigos
        assert 'CE' not in codigos
