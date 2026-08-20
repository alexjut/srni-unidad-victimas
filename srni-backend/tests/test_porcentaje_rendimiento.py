"""
`recalcular_porcentaje` corre en CADA respuesta guardada (`responder` y el bulk).

Cuando pasó a evaluar skip-logic dejó de ser tres `COUNT(*)` y se volvió un
recorrido en Python sobre todo el instrumento, una vez por miembro del hogar.
Vale la pena fijar el costo: el territorial tiene cientos de preguntas y un
hogar puede tener diez integrantes, y esto está en el camino de escritura de
alguien que está entrevistando a una víctima.

Lo que se fija acá es el número de CONSULTAS, que es lo que se degrada solo
(un N+1 escondido detrás de un atributo de relación no se nota al leer el
código, y sí se nota en campo con red mala).
"""
import pytest
from datetime import date

from apps.autenticacion.models import Perfil, Usuario
from apps.parametricas.models import TipoDocumento, Departamento, Municipio
from apps.victimas.models import Victima
from apps.hogares.models import Hogar, MiembroHogar
from apps.formulario.models import (
    Instrumento, Capitulo, Pregunta, ReglaSkipLogic, AccionSkipChoices,
)
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta


@pytest.fixture
def escenario_grande(db):
    """Instrumento del tamaño del territorial: 300 preguntas, 150 reglas,
    10 integrantes."""
    perfil = Perfil.objects.create(
        codigo='PPERF', nombre='Test Perf', puede_caracterizar=True, activo=True,
    )
    usuario = Usuario.objects.create_user(
        codigo_usuario='EPERF01', password='Test123!!!!',
        nombre_completo='Encuestador Perf', email='eperf@srni.dev',
        perfil=perfil, activo=True,
    )
    td, _ = TipoDocumento.objects.get_or_create(
        codigo='CC',
        defaults={'nombre': 'Cédula', 'aplica_nacionales': True, 'aplica_extranjeros': False},
    )
    dep = Departamento.objects.create(codigo_dane='11', nombre='Bogotá', activo=True)
    mun = Municipio.objects.create(
        codigo_dane='11001', nombre='Bogotá', departamento=dep, activo=True,
    )
    victima = Victima.objects.create(
        tipo_documento=td, numero_documento='555444333',
        primer_nombre='Perf', primer_apellido='Test',
        fecha_nacimiento='1980-01-01', genero='F', estado_civil='SOLTERO',
        pertenencia_etnica='NINGUNA', estado_ruv='INCLUIDO',
        municipio_residencia=mun, creado_por=usuario,
    )
    hogar = Hogar.objects.create(
        autorizado=victima, municipio=mun, tipo_vivienda='CASA',
        condicion_ocupacion='PROPIA', estrato=1, numero_cuartos=2,
        numero_personas=10, estado='BORRADOR', creado_por=usuario,
    )
    for _ in range(10):
        MiembroHogar.objects.create(
            hogar=hogar, parentesco='HIJO_A', rol='MIEMBRO',
            estado_inclusion='INCLUIDO', genero='M', fecha_nacimiento='2010-01-01',
            creado_por=usuario,
        )

    inst = Instrumento.objects.create(
        codigo='PERF-TEST', nombre='Instrumento grande', version='V1',
        vigente_desde=date(2021, 1, 1), activo=True, fuente_documental='tests',
    )
    preguntas = []
    for c in range(10):
        cap = Capitulo.objects.create(
            instrumento=inst, codigo=f'C{c:02d}', nombre=f'Cap {c}',
            orden=c + 1, nivel='HOGAR',
        )
        for i in range(30):
            preguntas.append(Pregunta(
                capitulo=cap, codigo_externo=f'Q{c:02d}_{i:02d}',
                no_pregunta=f'Q{c:02d}_{i:02d}', variable_bd=f'Q{c:02d}_{i:02d}',
                texto='x', tipo='TEXTO',
                nivel='PERSONA' if i % 2 else 'HOGAR',
                orden=i + 1, obligatoria=True,
            ))
    Pregunta.objects.bulk_create(preguntas)
    preguntas = list(Pregunta.objects.filter(capitulo__instrumento=inst).order_by('codigo_externo'))

    ReglaSkipLogic.objects.bulk_create([
        ReglaSkipLogic(
            instrumento=inst, pregunta_origen=preguntas[i],
            valor_trigger='SI', pregunta_afectada=preguntas[i + 1],
            accion=AccionSkipChoices.HABILITAR,
        )
        for i in range(0, 300, 2)
    ])

    sesion = SesionEncuesta.objects.create(
        hogar=hogar, instrumento=inst, encuestador=usuario, estado='EN_PROGRESO',
    )
    RespuestaEncuesta.objects.bulk_create([
        RespuestaEncuesta(sesion=sesion, pregunta=p, miembro=None, valor='SI')
        for p in preguntas[:150] if p.nivel == 'HOGAR'
    ])
    return sesion


@pytest.mark.django_db
def test_no_hay_n_mas_uno(django_assert_max_num_queries, escenario_grande):
    """
    Cuatro consultas: preguntas, reglas, respuestas y miembros. Ni una por
    pregunta, ni una por regla, ni una por integrante.

    El margen es 6 para no romper por un `.count()` que alguien agregue con
    criterio; lo que esta prueba impide es que el número crezca CON los datos.
    """
    with django_assert_max_num_queries(6):
        escenario_grande.recalcular_porcentaje()


@pytest.mark.django_db
def test_el_costo_no_crece_con_los_integrantes(django_assert_max_num_queries, escenario_grande):
    """El mismo techo con 10 integrantes que con 1: la evaluación por miembro
    se hace en memoria, no volviendo a la base."""
    with django_assert_max_num_queries(6):
        escenario_grande.recalcular_porcentaje()

    escenario_grande.hogar.miembros.all().delete()
    with django_assert_max_num_queries(6):
        escenario_grande.recalcular_porcentaje()


@pytest.mark.django_db
def test_devuelve_un_porcentaje_valido_en_el_escenario_grande(escenario_grande):
    pct = escenario_grande.recalcular_porcentaje()
    assert 0 <= pct <= 100
