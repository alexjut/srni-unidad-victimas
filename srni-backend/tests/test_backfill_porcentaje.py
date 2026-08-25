"""
Tests del comando `backfill_porcentaje` (APK-005).

El comando existe porque el arreglo de la skip-logic solo aplica hacia adelante:
una sesión ya COMPLETADA nunca vuelve a recalcularse, así que las que QA
fotografió en 0 % se quedan en 0 % hasta correr esto. Aquí se simula esa sesión
—contenido que da 100 %, pero con `porcentaje_completado` viejo en 0— y se
verifica que el comando la corrige, que --dry-run no escribe, y que es
idempotente.
"""
from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.hogares.models import Hogar
from apps.formulario.models import Instrumento, Capitulo, Pregunta
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta

pytestmark = pytest.mark.django_db


@pytest.fixture
def encuestador():
    perfil = Perfil.objects.create(
        codigo='PBF', nombre='Test BF', puede_caracterizar=True, activo=True)
    u = Usuario.objects.create_user(
        codigo_usuario='EBF01', password='Test123!!!!',
        nombre_completo='Encuestador BF', email='ebf@srni.dev',
        perfil=perfil, activo=True)
    return Usuario.objects.select_related('perfil').get(pk=u.pk)


@pytest.fixture
def sesion_vieja_en_cero(encuestador):
    """Una sesión COMPLETADA cuyo contenido da 100 % pero quedó guardada en 0 %."""
    td, _ = TipoDocumento.objects.get_or_create(
        codigo='CC', defaults={'nombre': 'Cédula', 'aplica_nacionales': True})
    dep = Departamento.objects.create(codigo_dane='08', nombre='Atlántico', activo=True)
    mun = Municipio.objects.create(
        codigo_dane='08001', nombre='Barranquilla', departamento=dep, activo=True)
    victima = Victima.objects.create(
        tipo_documento=td, numero_documento='777666555',
        primer_nombre='Luz', primer_apellido='Mora',
        fecha_nacimiento='1985-05-05', genero='F', estado_ruv='INCLUIDO',
        pertenencia_etnica='NINGUNA', municipio_residencia=mun, creado_por=encuestador)
    hogar = Hogar.objects.create(
        autorizado=victima, municipio=mun, estado='BORRADOR', creado_por=encuestador)

    inst = Instrumento.objects.create(
        codigo='BF-TEST', nombre='Instrumento bf', version='V1',
        vigente_desde=date(2021, 1, 1), activo=True, fuente_documental='tests')
    cap = Capitulo.objects.create(
        instrumento=inst, codigo='C01', nombre='Cap 1', orden=1, nivel='HOGAR')
    preg = Pregunta.objects.create(
        capitulo=cap, codigo_externo='A1', no_pregunta='A1', variable_bd='A1',
        texto='Pregunta A1', tipo='TEXTO', orden=1, nivel='HOGAR', obligatoria=True)

    sesion = SesionEncuesta.objects.create(
        hogar=hogar, instrumento=inst, encuestador=encuestador, estado='COMPLETADA')
    RespuestaEncuesta.objects.create(sesion=sesion, pregunta=preg, miembro=None, valor='sí')

    # La obligatoria única está respondida → recalcular da 100. Pero la fila
    # quedó en 0, como las que QA fotografió.
    SesionEncuesta.objects.filter(pk=sesion.pk).update(porcentaje_completado=0)
    sesion.refresh_from_db()
    assert sesion.porcentaje_completado == 0
    assert sesion.recalcular_porcentaje() == 100  # el contenido sí da 100
    return sesion


def test_backfill_corrige_la_sesion_en_cero(sesion_vieja_en_cero):
    call_command('backfill_porcentaje', stdout=StringIO())
    sesion_vieja_en_cero.refresh_from_db()
    assert sesion_vieja_en_cero.porcentaje_completado == 100


def test_dry_run_no_escribe(sesion_vieja_en_cero):
    out = StringIO()
    call_command('backfill_porcentaje', '--dry-run', stdout=out)
    sesion_vieja_en_cero.refresh_from_db()
    # No tocó la fila...
    assert sesion_vieja_en_cero.porcentaje_completado == 0
    # ...pero sí reportó que UNA cambiaría.
    assert 'cambiarían' in out.getvalue()


def test_es_idempotente(sesion_vieja_en_cero):
    call_command('backfill_porcentaje', stdout=StringIO())
    # Segunda corrida: nada por cambiar.
    out = StringIO()
    call_command('backfill_porcentaje', stdout=out)
    assert '0 de 1 sesiones actualizadas' in out.getvalue()
