"""
Tests de Hogares: creación, miembros, permisos y auditoría.
"""
import pytest
from rest_framework.test import APIClient
from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.hogares.models import Hogar, MiembroHogar


@pytest.fixture
def perfil_enc():
    return Perfil.objects.create(
        codigo='HTEST', nombre='Test Hogares',
        puede_buscar_rni=True, puede_caracterizar=True, activo=True,
    )


@pytest.fixture
def encuestador(perfil_enc):
    u = Usuario.objects.create_user(
        codigo_usuario='HENC001', password='Test123!!!!',
        nombre_completo='Encuestador Hogares', email='henc@srni.dev',
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
    dep = Departamento.objects.create(codigo_dane='05', nombre='Antioquia', activo=True)
    return Municipio.objects.create(
        codigo_dane='05001', nombre='Medellín', departamento=dep, activo=True
    )


@pytest.fixture
def victima(tipo_doc, municipio, encuestador):
    return Victima.objects.create(
        tipo_documento=tipo_doc,
        numero_documento='1030547250',
        primer_nombre='Ana', segundo_nombre='',
        primer_apellido='García', segundo_apellido='',
        fecha_nacimiento='1980-01-15',
        genero='F', estado_civil='SOLTERO',
        pertenencia_etnica='NINGUNA', estado_ruv='INCLUIDO',
        municipio_residencia=municipio,
        creado_por=encuestador,
    )


@pytest.fixture
def hogar(victima, municipio, encuestador):
    return Hogar.objects.create(
        jefe_hogar=victima,
        municipio=municipio,
        tipo_vivienda='CASA',
        condicion_ocupacion='ARRIENDO',
        estrato=2,
        numero_cuartos=3,
        numero_personas=4,
        estado='BORRADOR',
        creado_por=encuestador,
    )


@pytest.fixture
def client_enc(encuestador):
    c = APIClient()
    c.force_authenticate(user=encuestador)
    return c


# ---------------------------------------------------------------------------
# Tests de creación de hogar
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCrearHogar:
    def test_requiere_auth(self):
        r = APIClient().post('/api/hogares/', {})
        assert r.status_code == 401

    def test_crear_hogar_exitoso(self, client_enc, victima, municipio):
        r = client_enc.post('/api/hogares/', {
            'jefe_hogar': str(victima.id),
            'municipio': municipio.id,
            'tipo_vivienda': 'CASA',
            'condicion_ocupacion': 'ARRIENDO',
            'estrato': 2,
            'numero_cuartos': 3,
            'numero_personas': 4,
        }, format='json')
        assert r.status_code == 201, r.data
        assert r.data['estado'] == 'BORRADOR'

    def test_hogar_creado_asigna_encuestador(self, client_enc, victima, municipio, encuestador):
        r = client_enc.post('/api/hogares/', {
            'jefe_hogar': str(victima.id),
            'municipio': municipio.id,
            'numero_personas': 2,
        }, format='json')
        assert r.status_code == 201
        hogar = Hogar.objects.get(pk=r.data['id'])
        assert hogar.creado_por == encuestador

    def test_encuestador_solo_ve_sus_hogares(self, client_enc, hogar, victima, municipio):
        # Crear otro encuestador con otro hogar
        perfil2 = Perfil.objects.create(
            codigo='ENC2', nombre='Otro Enc', puede_caracterizar=True, activo=True,
        )
        enc2_user = Usuario.objects.create_user(
            codigo_usuario='ENC002', password='Test123!!!!',
            nombre_completo='Otro', email='enc2@srni.dev',
            perfil=perfil2, activo=True,
        )
        enc2 = Usuario.objects.select_related('perfil').get(pk=enc2_user.pk)
        Hogar.objects.create(
            jefe_hogar=victima, municipio=municipio,
            numero_personas=1, creado_por=enc2,
        )
        r = client_enc.get('/api/hogares/')
        assert r.status_code == 200
        # Solo debe ver el hogar de encuestador, no el de enc2
        ids = [h['id'] for h in r.data['results']]
        assert str(hogar.id) in ids
        assert len(ids) == 1


@pytest.mark.django_db
class TestMiembrosHogar:
    def test_agregar_miembro_sin_rni(self, client_enc, hogar):
        r = client_enc.post(f'/api/hogares/{hogar.id}/agregar-miembro/', {
            'nombre_completo': 'Miembro Sin RNI',
            'parentesco': 'HIJO_A',
            'genero': 'M',
            'edad': 12,
            'discapacidad': False,
        }, format='json')
        assert r.status_code == 201
        assert MiembroHogar.objects.filter(hogar=hogar).count() == 1

    def test_agregar_miembro_con_rni(self, client_enc, hogar, victima):
        r = client_enc.post(f'/api/hogares/{hogar.id}/agregar-miembro/', {
            'victima': str(victima.id),
            'parentesco': 'CONYUGE',
            'genero': 'F',
        }, format='json')
        assert r.status_code == 201
        miembro = MiembroHogar.objects.get(pk=r.data['id'])
        assert miembro.victima == victima

    def test_listar_miembros(self, client_enc, hogar, victima):
        MiembroHogar.objects.create(
            hogar=hogar, parentesco='HIJO_A',
            genero='M', edad=10, creado_por=client_enc.handler._force_user,
        )
        r = client_enc.get(f'/api/hogares/{hogar.id}/miembros/')
        assert r.status_code == 200
        assert len(r.data) == 1

    def test_detalle_incluye_miembros(self, client_enc, hogar):
        MiembroHogar.objects.create(
            hogar=hogar, parentesco='JEFE',
            genero='F', edad=42, creado_por=client_enc.handler._force_user,
        )
        r = client_enc.get(f'/api/hogares/{hogar.id}/')
        assert r.status_code == 200
        assert len(r.data['miembros']) == 1
        assert r.data['total_miembros'] == 1


@pytest.mark.django_db
class TestPermisosHogar:
    def test_sin_puede_caracterizar_retorna_403(self, victima, municipio):
        perfil_sin = Perfil.objects.create(
            codigo='SINCAR', nombre='Sin Caracterizar',
            puede_caracterizar=False, activo=True,
        )
        u = Usuario.objects.create_user(
            codigo_usuario='SINCAR001', password='Test123!!!!',
            nombre_completo='Sin Permiso', email='sincar@srni.dev',
            perfil=perfil_sin, activo=True,
        )
        user = Usuario.objects.select_related('perfil').get(pk=u.pk)
        c = APIClient()
        c.force_authenticate(user=user)
        r = c.post('/api/hogares/', {
            'jefe_hogar': str(victima.id), 'numero_personas': 1,
        }, format='json')
        assert r.status_code == 403
