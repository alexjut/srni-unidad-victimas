"""
Tests de Víctimas: seguridad de PII, búsqueda por hash, permisos.
"""
import pytest
from rest_framework.test import APIClient
from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.victimas.repository.base import doc_hash
from apps.victimas.serializers import VictimaListSerializer, VictimaDetalleSerializer


@pytest.fixture
def perfil_completo():
    return Perfil.objects.create(
        codigo='VTEST',
        nombre='Test Víctimas',
        puede_buscar_rni=True,
        puede_caracterizar=True,
        activo=True,
    )


@pytest.fixture
def perfil_solo_busqueda():
    return Perfil.objects.create(
        codigo='BUSQ',
        nombre='Solo Búsqueda',
        puede_buscar_rni=True,
        puede_caracterizar=False,
        activo=True,
    )


@pytest.fixture
def usuario_completo(perfil_completo):
    u = Usuario.objects.create_user(
        codigo_usuario='VTEST001',
        password='TestPass123!',
        nombre_completo='Test Víctimas',
        email='victimas@srni.gov.co',
        perfil=perfil_completo,
        activo=True,
    )
    return Usuario.objects.select_related('perfil').get(pk=u.pk)


@pytest.fixture
def usuario_busqueda(perfil_solo_busqueda):
    u = Usuario.objects.create_user(
        codigo_usuario='BUSQ001',
        password='TestPass123!',
        nombre_completo='Test Búsqueda',
        email='busqueda@srni.gov.co',
        perfil=perfil_solo_busqueda,
        activo=True,
    )
    return Usuario.objects.select_related('perfil').get(pk=u.pk)


@pytest.fixture
def tipo_doc():
    return TipoDocumento.objects.create(
        codigo='CC', nombre='Cédula de Ciudadanía',
        aplica_nacionales=True, aplica_extranjeros=False,
    )


@pytest.fixture
def municipio():
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia', activo=True)
    return Municipio.objects.create(
        codigo_dane='05001', nombre='Medellín', departamento=depto, activo=True
    )


@pytest.fixture
def victima(tipo_doc, municipio, usuario_completo):
    return Victima.objects.create(
        tipo_documento=tipo_doc,
        numero_documento='1030547250',
        primer_nombre='María',
        segundo_nombre='Alejandra',
        primer_apellido='González',
        segundo_apellido='López',
        fecha_nacimiento='1985-03-15',
        genero='F',
        estado_civil='SOLTERO',
        pertenencia_etnica='NINGUNA',
        estado_ruv='INCLUIDO',
        municipio_residencia=municipio,
        creado_por=usuario_completo,
    )


# ---------------------------------------------------------------------------
# Tests de seguridad: PII no expuesta en VictimaListSerializer
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSeguridadPII:
    CAMPOS_PII = {
        'numero_documento', 'primer_nombre', 'segundo_nombre',
        'primer_apellido', 'segundo_apellido', 'fecha_nacimiento',
    }

    def test_list_serializer_no_expone_pii(self, victima):
        data = VictimaListSerializer(victima).data
        for campo in self.CAMPOS_PII:
            assert campo not in data, f'Campo PII "{campo}" no debe aparecer en VictimaListSerializer'

    def test_list_serializer_tiene_hash(self, victima):
        data = VictimaListSerializer(victima).data
        assert 'numero_documento_hash' in data
        # El hash es el de `repository.base.doc_hash`: UNA sola definición para
        # el modelo, la búsqueda, el upsert y el padrón descargable. Antes había
        # varias fórmulas distintas y la búsqueda por documento no encontraba nada.
        esperado = doc_hash('CC', '1030547250')
        assert data['numero_documento_hash'] == esperado

    def test_detalle_serializer_expone_pii(self, victima):
        data = VictimaDetalleSerializer(victima).data
        # El EncryptedField descifra automáticamente
        assert data['numero_documento'] == '1030547250'
        assert data['primer_nombre'] == 'María'
        assert data['primer_apellido'] == 'González'

    def test_documento_cifrado_en_db(self, victima):
        """Verifica que en la DB el campo está cifrado (empieza con 'gAAAAA')."""
        from django.db import connection
        # SQLite almacena UUIDField sin guiones (value.hex, 32 chars).
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT numero_documento FROM victimas_victima WHERE id = ?',
                [victima.id.hex],
            )
            row = cursor.fetchone()
        assert row is not None, 'La víctima no se encontró en la tabla victimas_victima'
        valor_db = row[0]
        assert valor_db.startswith('gAAAAA'), (
            f'El campo numero_documento debe estar cifrado en DB. Valor: {valor_db[:20]}'
        )


# ---------------------------------------------------------------------------
# Tests de búsqueda por hash
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBusquedaVictima:
    def test_busqueda_requiere_auth(self):
        client = APIClient()
        response = client.post('/api/victimas/buscar/', {
            'tipo_documento_codigo': 'CC',
            'numero_documento': '1030547250',
        }, format='json')
        assert response.status_code == 401

    def test_busqueda_exitosa(self, victima, usuario_busqueda):
        client = APIClient()
        client.force_authenticate(user=usuario_busqueda)
        response = client.post('/api/victimas/buscar/', {
            'tipo_documento_codigo': 'CC',
            'numero_documento': '1030547250',
        }, format='json')
        assert response.status_code == 200
        data = response.data
        # No debe haber PII en la respuesta
        assert 'primer_nombre' not in data
        assert 'numero_documento' not in data
        assert data['numero_documento_hash'] == doc_hash('CC', '1030547250')

    def test_busqueda_no_encontrada(self, tipo_doc, usuario_busqueda):
        client = APIClient()
        client.force_authenticate(user=usuario_busqueda)
        response = client.post('/api/victimas/buscar/', {
            'tipo_documento_codigo': 'CC',
            'numero_documento': '0000000000',
        }, format='json')
        assert response.status_code == 404

    def test_busqueda_normaliza_documento(self, victima, usuario_busqueda):
        """Documento en minúsculas o con espacios debe encontrar el mismo registro."""
        client = APIClient()
        client.force_authenticate(user=usuario_busqueda)
        response = client.post('/api/victimas/buscar/', {
            'tipo_documento_codigo': 'CC',
            'numero_documento': '  1030547250  ',  # con espacios
        }, format='json')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests de permisos en endpoint de detalle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPermisosVictima:
    def test_detalle_requiere_puede_caracterizar(self, victima, usuario_busqueda):
        """usuario_busqueda solo tiene puede_buscar_rni, no puede_caracterizar."""
        client = APIClient()
        client.force_authenticate(user=usuario_busqueda)
        response = client.get(f'/api/victimas/{victima.id}/')
        assert response.status_code == 403

    def test_detalle_con_permiso_correcto(self, victima, usuario_completo):
        client = APIClient()
        client.force_authenticate(user=usuario_completo)
        response = client.get(f'/api/victimas/{victima.id}/')
        assert response.status_code == 200
        assert response.data['numero_documento'] == '1030547250'
