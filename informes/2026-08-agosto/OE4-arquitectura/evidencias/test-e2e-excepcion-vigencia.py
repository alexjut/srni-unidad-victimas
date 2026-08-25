"""
Prueba de punta a punta del flujo de EXCEPCIÓN DE VIGENCIA.

Recorre la cadena completa con los MISMOS endpoints de la API que consume la
APK, para demostrar que una recaracterización por excepción funciona de extremo
a extremo a nivel de contrato:

  1. La persona tiene ficha vigente -> consultar-fuente la devuelve BLOQUEADA.
  2. Coordinación autoriza la excepción desde el panel (POST /api/habilitaciones/).
  3. consultar-fuente ahora la devuelve HABILITADA (el campo que lee la APK).
  4. Se conforma el hogar y se crea la sesión sobre esa persona.
  5. Al finalizar, la habilitación se CONSUME (un solo uso).
  6. Una nueva consulta la vuelve a devolver BLOQUEADA.

Es la prueba que respalda el informe de agosto: el flujo de excepción cierra el
círculo en el backend. NO reemplaza la verificación en un dispositivo físico
(pendiente), pero fija por contrato lo que la APK recibe en cada paso.

Ejecutar:
    cd srni-backend
    .venv/Scripts/python.exe -m pytest tests/test_e2e_excepcion_vigencia.py -v
"""
import datetime

import pytest
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.formulario.models import Instrumento, Capitulo
from apps.hogares.models import Hogar
from apps.encuestas.models import SesionEncuesta, ExcepcionVigencia

pytestmark = pytest.mark.django_db

CONSULTAR = '/api/victimas/consultar-fuente/'
AUTORIZAR = '/api/habilitaciones/'


@pytest.fixture
def mundo(db, settings):
    # El repositorio real, no el mock: es lo que corre en producción.
    settings.VICTIMA_REPOSITORY = 'DJANGO'

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    dep = Departamento.objects.create(codigo_dane='11', nombre='Bogotá', activo=True)
    mun = Municipio.objects.create(codigo_dane='11001', nombre='Bogotá',
                                   departamento=dep, activo=True)

    from apps.victimas.repository.base import doc_hash, num_hash
    # Ficha VIGENTE: caracterizada hace un año, no habilitada por tiempo.
    hace_un_anio = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento='1006119999',
        numero_documento_hash=doc_hash('CC', '1006119999'),
        numero_documento_hash_sin_tipo=num_hash('1006119999'),
        primer_nombre='LUZ', primer_apellido='MORA',
        genero='F', estado_ruv='INCLUIDO',
        habilitado_para_caracterizacion=False,      # ficha vigente por tiempo
        fecha_ult_caracterizacion=hace_un_anio,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        municipio_residencia=mun,
    )

    inst = Instrumento.objects.create(
        codigo='TERRITORIAL-E2E', nombre='Territorial', version='V8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1), fuente_documental='e2e')
    Capitulo.objects.create(instrumento=inst, codigo='A', nombre='Identificación',
                            orden=1, nivel='HOGAR')

    def cliente(codigo, **flags):
        perfil = Perfil.objects.create(codigo='P_' + codigo, nombre=codigo,
                                       activo=True, **flags)
        u = Usuario.objects.create_user(
            codigo_usuario=codigo, password='SrniTest2026!',
            nombre_completo=codigo, email=codigo + '@srni.dev',
            perfil=perfil, activo=True)
        c = APIClient()
        c.force_authenticate(user=Usuario.objects.select_related('perfil').get(pk=u.pk))
        return c, u

    coord_c, coord_u = cliente('COORD_E2E', puede_autorizar_excepciones=True,
                               puede_buscar_rni=True, puede_caracterizar=True)
    enc_c, enc_u = cliente('ENC_E2E', puede_buscar_rni=True, puede_caracterizar=True)

    return {
        'victima': victima, 'municipio': mun, 'instrumento': inst,
        'coord': coord_c, 'enc': enc_c, 'enc_u': enc_u,
    }


def test_flujo_completo_excepcion_de_vigencia(mundo):
    v = mundo['victima']
    doc = {'tipo_documento': 'CC', 'numero_documento': v.numero_documento}

    # ── Paso 1: con ficha vigente, la persona está BLOQUEADA ────────────────
    r1 = mundo['enc'].post(CONSULTAR, doc, format='json')
    assert r1.status_code == 200, r1.data
    assert r1.data['victima']['habilitado_para_caracterizacion'] is False, (
        'una ficha vigente NO debe poder recaracterizarse sin excepción')
    assert r1.data['motivo'] == 'FICHA_VIGENTE'

    # ── Paso 2: coordinación autoriza la excepción desde el panel ───────────
    r2 = mundo['coord'].post(AUTORIZAR, {
        'victima_id': str(v.id),
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-E2E',
        'observacion': 'Fallo de tutela que ordena actualizar la caracterización.',
    }, format='json')
    assert r2.status_code == 201, r2.data

    # ── Paso 3: consultar-fuente ahora la devuelve HABILITADA ───────────────
    #    Este es el campo que la APK lee para decidir si deja recaracterizar.
    r3 = mundo['enc'].post(CONSULTAR, doc, format='json')
    assert r3.status_code == 200, r3.data
    assert r3.data['victima']['habilitado_para_caracterizacion'] is True, (
        'tras autorizar, la APK debe verla habilitada (era el defecto del flujo online)')
    assert r3.data['motivo'] == 'ELEGIBLE_POR_EXCEPCION'
    assert 'T-2026-E2E' in r3.data['mensaje']

    # ── Paso 4: se conforma el hogar y se crea la sesión ────────────────────
    #    (el CRUD de hogares/sesiones tiene su propia cobertura; aquí es el
    #     vehículo para poder finalizar y probar el consumo).
    hogar = Hogar.objects.create(
        autorizado=v, municipio=mundo['municipio'], estado='BORRADOR',
        creado_por=mundo['enc_u'])
    sesion = SesionEncuesta.objects.create(
        hogar=hogar, instrumento=mundo['instrumento'], estado='INICIADA',
        encuestador=mundo['enc_u'])

    # ── Paso 5: al finalizar, la habilitación se consume ────────────────────
    r5 = mundo['enc'].post('/api/encuestas/' + str(sesion.id) + '/finalizar/',
                           {}, format='json')
    assert r5.status_code in (200, 201), r5.data

    hab = ExcepcionVigencia.objects.get(victima=v)
    assert hab.estado == ExcepcionVigencia.USADA
    assert hab.usada_en_sesion_id == sesion.id

    # ── Paso 6: una nueva consulta la vuelve a bloquear ─────────────────────
    #    La excepción es de un solo uso: sin una nueva autorización, no se puede
    #    volver a recaracterizar.
    r6 = mundo['enc'].post(CONSULTAR, doc, format='json')
    assert r6.status_code == 200, r6.data
    assert r6.data['victima']['habilitado_para_caracterizacion'] is False
    assert r6.data['motivo'] == 'FICHA_VIGENTE'
