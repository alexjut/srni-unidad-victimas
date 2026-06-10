"""
Tests de Hogares: creación, miembros, autorizado, estado_inclusion, permisos y auditoría.
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
def victima2(tipo_doc, municipio, encuestador):
    """Segunda víctima para tests de integrantes adicionales."""
    return Victima.objects.create(
        tipo_documento=tipo_doc,
        numero_documento='9876543210',
        primer_nombre='Carlos', segundo_nombre='',
        primer_apellido='Pérez', segundo_apellido='',
        fecha_nacimiento='1975-06-20',
        genero='M', estado_civil='CASADO',
        pertenencia_etnica='NINGUNA', estado_ruv='NO_INCLUIDO',
        municipio_residencia=municipio,
        creado_por=encuestador,
    )


@pytest.fixture
def hogar(victima, municipio, encuestador):
    """Hogar creado directamente (sin API) — NO auto-inserta el autorizado."""
    return Hogar.objects.create(
        autorizado=victima,
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
            'autorizado': str(victima.id),
            'municipio': municipio.id,
            'tipo_vivienda': 'CASA',
            'condicion_ocupacion': 'ARRIENDO',
            'estrato': 2,
            'numero_cuartos': 3,
            'numero_personas': 4,
        }, format='json')
        assert r.status_code == 201, r.data
        assert r.data['estado'] == 'BORRADOR'
        # La API devuelve el UUID como objeto; comparamos con str() en ambos lados
        assert str(r.data['autorizado']) == str(victima.id)

    def test_crear_hogar_auto_inserta_autorizado_como_miembro(self, client_enc, victima, municipio):
        """
        Al crear el hogar vía API, el autorizado debe quedar automáticamente
        como primer MiembroHogar: rol='MIEMBRO', es_autorizado=True, estado_inclusion='INCLUIDO'.
        """
        r = client_enc.post('/api/hogares/', {
            'autorizado': str(victima.id),
            'numero_personas': 1,
        }, format='json')
        assert r.status_code == 201, r.data
        hogar_id = r.data['id']

        miembros = MiembroHogar.objects.filter(hogar_id=hogar_id)
        assert miembros.count() == 1, 'El autorizado debe ser el primer miembro'

        autorizado = miembros.get()
        assert autorizado.es_autorizado is True
        assert autorizado.rol == 'MIEMBRO'
        assert autorizado.estado_inclusion == 'INCLUIDO'
        assert autorizado.incluido_ruv is True      # sincronizado en save()
        assert autorizado.tipo_persona == '5001'    # código Oracle sincronizado en save()
        assert autorizado.victima == victima

    def test_crear_hogar_asigna_encuestador(self, client_enc, victima, municipio, encuestador):
        r = client_enc.post('/api/hogares/', {
            'autorizado': str(victima.id),
            'municipio': municipio.id,
            'numero_personas': 2,
        }, format='json')
        assert r.status_code == 201
        hogar = Hogar.objects.get(pk=r.data['id'])
        assert hogar.creado_por == encuestador

    def test_encuestador_solo_ve_sus_hogares(self, client_enc, hogar, victima2, municipio):
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
            autorizado=victima2, municipio=municipio,
            numero_personas=1, creado_por=enc2,
        )
        r = client_enc.get('/api/hogares/')
        assert r.status_code == 200
        ids = [h['id'] for h in r.data['results']]
        assert str(hogar.id) in ids
        assert len(ids) == 1


# ---------------------------------------------------------------------------
# Tests de integrantes del hogar
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMiembrosHogar:
    def test_agregar_miembro_sin_rni(self, client_enc, hogar):
        r = client_enc.post(f'/api/hogares/{hogar.id}/agregar-miembro/', {
            'nombre_completo': 'Miembro Sin RNI',
            'parentesco': 'HIJO_A',
            'rol': 'MIEMBRO',
            'estado_inclusion': 'NO_INCLUIDO',
            'genero': 'M',
        }, format='json')
        assert r.status_code == 201
        assert MiembroHogar.objects.filter(hogar=hogar).count() == 1

    def test_agregar_miembro_con_rni(self, client_enc, hogar, victima2):
        r = client_enc.post(f'/api/hogares/{hogar.id}/agregar-miembro/', {
            'victima': str(victima2.id),
            'parentesco': 'CONYUGE',
            'rol': 'MIEMBRO',
            'estado_inclusion': 'NO_INCLUIDO',
            'genero': 'M',
        }, format='json')
        assert r.status_code == 201
        miembro = MiembroHogar.objects.get(pk=r.data['id'])
        assert miembro.victima == victima2
        assert miembro.es_autorizado is False

    def test_nuevo_miembro_nunca_es_autorizado(self, client_enc, hogar, victima2):
        """
        La action agregar_miembro siempre fuerza es_autorizado=False.
        El autorizado solo se asigna al crear el hogar.
        """
        r = client_enc.post(f'/api/hogares/{hogar.id}/agregar-miembro/', {
            'victima': str(victima2.id),
            'parentesco': 'HIJO_A',
            'rol': 'TUTOR',
            'estado_inclusion': 'INCLUIDO',
        }, format='json')
        assert r.status_code == 201
        miembro = MiembroHogar.objects.get(pk=r.data['id'])
        assert miembro.es_autorizado is False

    def test_estado_inclusion_chip_incluido(self, client_enc, hogar, victima):
        """El campo estado_inclusion se sincroniza con incluido_ruv via save()."""
        m = MiembroHogar.objects.create(
            hogar=hogar, victima=victima,
            rol='MIEMBRO', es_autorizado=False,
            estado_inclusion='INCLUIDO',
            creado_por=hogar.creado_por,
        )
        assert m.incluido_ruv is True
        assert m.tipo_persona == '5004'  # Miembro ordinario aunque esté incluido

    def test_tipo_persona_oracle_sincronizado(self):
        """save() calcula tipo_persona y incluido_ruv a partir de rol/es_autorizado."""
        from unittest.mock import patch
        from django.db import models as django_models

        casos = [
            ({'rol': 'MIEMBRO', 'es_autorizado': True,  'estado_inclusion': 'INCLUIDO'},    '5001', True),
            ({'rol': 'TUTOR',   'es_autorizado': False, 'estado_inclusion': 'NO_INCLUIDO'}, '5002', False),
            ({'rol': 'CUIDADOR_PERMANENTE', 'es_autorizado': False, 'estado_inclusion': 'NO_INCLUIDO'}, '5003', False),
            ({'rol': 'MIEMBRO', 'es_autorizado': False, 'estado_inclusion': 'NO_INCLUIDO'}, '5004', False),
        ]
        for attrs, tipo_esperado, incluido_esperado in casos:
            m = MiembroHogar(**attrs)
            # Patch super().save() para no tocar la BD
            with patch.object(django_models.Model, 'save'):
                m.save()
            assert m.tipo_persona == tipo_esperado, f'Para {attrs}: tipo_persona {m.tipo_persona!r} ≠ {tipo_esperado!r}'
            assert m.incluido_ruv == incluido_esperado, f'Para {attrs}: incluido_ruv {m.incluido_ruv!r} ≠ {incluido_esperado!r}'

    def test_listar_miembros(self, client_enc, hogar, victima):
        MiembroHogar.objects.create(
            hogar=hogar, parentesco='HIJO_A', rol='MIEMBRO',
            estado_inclusion='NO_INCLUIDO',
            genero='M', fecha_nacimiento='2014-03-15',
            creado_por=client_enc.handler._force_user,
        )
        r = client_enc.get(f'/api/hogares/{hogar.id}/miembros/')
        assert r.status_code == 200
        assert len(r.data) == 1

    def test_detalle_incluye_miembros_con_nuevos_campos(self, client_enc, hogar, victima):
        MiembroHogar.objects.create(
            hogar=hogar, victima=victima,
            parentesco='CONYUGE', rol='MIEMBRO',
            estado_inclusion='INCLUIDO',
            genero='F', fecha_nacimiento='1982-07-20',
            creado_por=client_enc.handler._force_user,
        )
        r = client_enc.get(f'/api/hogares/{hogar.id}/')
        assert r.status_code == 200
        assert len(r.data['miembros']) == 1
        assert r.data['total_miembros'] == 1
        miembro = r.data['miembros'][0]
        assert 'rol' in miembro
        assert 'es_autorizado' in miembro
        assert 'estado_inclusion' in miembro

    def test_constraint_unico_autorizado_por_hogar(self, hogar, victima, victima2, encuestador):
        """Solo puede haber un es_autorizado=True por hogar."""
        import django.db
        MiembroHogar.objects.create(
            hogar=hogar, victima=victima,
            rol='MIEMBRO', es_autorizado=True,
            estado_inclusion='INCLUIDO',
            creado_por=encuestador,
        )
        with pytest.raises(django.db.IntegrityError):
            MiembroHogar.objects.create(
                hogar=hogar, victima=victima2,
                rol='MIEMBRO', es_autorizado=True,
                estado_inclusion='INCLUIDO',
                creado_por=encuestador,
            )

    def test_respuesta_incluye_campo_rol_display(self, client_enc, hogar):
        MiembroHogar.objects.create(
            hogar=hogar, rol='TUTOR',
            estado_inclusion='NO_INCLUIDO',
            creado_por=client_enc.handler._force_user,
        )
        r = client_enc.get(f'/api/hogares/{hogar.id}/miembros/')
        assert r.status_code == 200
        assert r.data[0]['rol_display'] == 'Tutor — responsable legal de menor'


# ---------------------------------------------------------------------------
# Tests de permisos
# ---------------------------------------------------------------------------

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
            'autorizado': str(victima.id), 'numero_personas': 1,
        }, format='json')
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tests del FilterSet (Sprint 13 — backend habilitador para panel web)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestHogarFilterSet:
    """
    Validan que el listado /api/hogares/ acepta los filtros server-side
    que consume el panel web: estado, municipio, tipo_vivienda,
    creado_por, rango de fechas y búsqueda de texto.
    """

    def test_filtra_por_estado(self, client_enc, victima, victima2, municipio, encuestador):
        Hogar.objects.create(
            autorizado=victima, municipio=municipio,
            estado='ACTIVO', creado_por=encuestador,
        )
        # victima2: una víctima solo puede ser autorizada en UN hogar no archivado
        Hogar.objects.create(
            autorizado=victima2, municipio=municipio,
            estado='BORRADOR', creado_por=encuestador,
        )
        r = client_enc.get('/api/hogares/?estado=ACTIVO')
        assert r.status_code == 200
        # results puede venir paginado o no según config
        resultados = r.data['results'] if 'results' in r.data else r.data
        assert all(h['estado'] == 'ACTIVO' for h in resultados)
        assert len(resultados) == 1

    def test_filtra_por_tipo_vivienda(self, client_enc, victima, victima2, municipio, encuestador):
        Hogar.objects.create(
            autorizado=victima, municipio=municipio,
            tipo_vivienda='CASA', creado_por=encuestador,
        )
        Hogar.objects.create(
            autorizado=victima2, municipio=municipio,
            tipo_vivienda='APARTAMENTO', creado_por=encuestador,
        )
        r = client_enc.get('/api/hogares/?tipo_vivienda=CASA')
        assert r.status_code == 200
        resultados = r.data['results'] if 'results' in r.data else r.data
        assert len(resultados) == 1
        assert resultados[0]['tipo_vivienda'] == 'CASA' if 'tipo_vivienda' in resultados[0] else True

    def test_filtra_por_municipio(self, client_enc, victima, victima2, municipio, encuestador):
        Hogar.objects.create(
            autorizado=victima, municipio=municipio, creado_por=encuestador,
        )
        Hogar.objects.create(
            autorizado=victima2, municipio=None, creado_por=encuestador,
        )
        r = client_enc.get(f'/api/hogares/?municipio={municipio.id}')
        assert r.status_code == 200
        resultados = r.data['results'] if 'results' in r.data else r.data
        assert len(resultados) == 1

    def test_filtra_por_rango_fecha(self, client_enc, victima, victima2, municipio, encuestador):
        from django.utils import timezone
        from datetime import timedelta

        antiguo = Hogar.objects.create(
            autorizado=victima, municipio=municipio, creado_por=encuestador,
        )
        # Forzar fecha vieja
        Hogar.objects.filter(pk=antiguo.pk).update(
            created_at=timezone.now() - timedelta(days=60)
        )
        Hogar.objects.create(
            autorizado=victima2, municipio=municipio, creado_por=encuestador,
        )

        hoy = timezone.now().date()
        hace_30 = (timezone.now() - timedelta(days=30)).date()

        r = client_enc.get(
            f'/api/hogares/?created_at_after={hace_30}&created_at_before={hoy}'
        )
        assert r.status_code == 200
        resultados = r.data['results'] if 'results' in r.data else r.data
        # solo el hogar reciente
        assert len(resultados) == 1

    def test_busqueda_libre_en_codigo_y_observaciones(self, client_enc, victima, victima2, municipio, encuestador):
        Hogar.objects.create(
            autorizado=victima, municipio=municipio, creado_por=encuestador,
            codigo_hogar='H-2026-MEDE-001',
            observaciones='Familia desplazada — caso prioritario',
        )
        Hogar.objects.create(
            autorizado=victima2, municipio=municipio, creado_por=encuestador,
            codigo_hogar='H-2026-MEDE-002',
            observaciones='Caracterización ordinaria',
        )
        r = client_enc.get('/api/hogares/?busqueda=prioritario')
        assert r.status_code == 200
        resultados = r.data['results'] if 'results' in r.data else r.data
        assert len(resultados) == 1

    def test_combinacion_de_filtros(self, client_enc, victima, victima2, municipio, encuestador):
        Hogar.objects.create(
            autorizado=victima, municipio=municipio, creado_por=encuestador,
            estado='ACTIVO', tipo_vivienda='CASA',
        )
        Hogar.objects.create(
            autorizado=victima2, municipio=municipio, creado_por=encuestador,
            estado='ACTIVO', tipo_vivienda='APARTAMENTO',
        )
        r = client_enc.get('/api/hogares/?estado=ACTIVO&tipo_vivienda=CASA')
        assert r.status_code == 200
        resultados = r.data['results'] if 'results' in r.data else r.data
        assert len(resultados) == 1
