"""
El porcentaje de una sesión cuenta obligatorias VISIBLES — APK-005.

QA lo reportó como «sesión Completada con la barra de progreso en 0 %» y el
primer intento de arreglo fue en la app: forzar 100 % cuando el estado era
COMPLETADA. Eso tapaba el síntoma y además mentía sobre las entrevistas que sí
se cerraron a medias, mientras el panel web —que nunca aplicó ese maquillaje—
mostraba otro número sobre la misma sesión.

El defecto estaba acá: `recalcular_porcentaje` dividía por TODAS las
obligatorias del instrumento sin evaluar skip-logic. Una obligatoria que una
regla HABILITAR mantiene oculta no se le puede mostrar a nadie, así que nunca se
responde — pero engordaba el denominador igual, y el progreso no llegaba a 100
ni terminando la entrevista completa.

Estas pruebas fijan el comportamiento correcto. Todas fallan contra la
implementación vieja.
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


# ─── Andamiaje ───────────────────────────────────────────────────────────────

@pytest.fixture
def encuestador():
    perfil = Perfil.objects.create(
        codigo='PSKIP', nombre='Test Skip', puede_caracterizar=True, activo=True,
    )
    u = Usuario.objects.create_user(
        codigo_usuario='ESKIP01', password='Test123!!!!',
        nombre_completo='Encuestador Skip', email='eskip@srni.dev',
        perfil=perfil, activo=True,
    )
    return Usuario.objects.select_related('perfil').get(pk=u.pk)


@pytest.fixture
def hogar(encuestador):
    td, _ = TipoDocumento.objects.get_or_create(
        codigo='CC',
        defaults={'nombre': 'Cédula', 'aplica_nacionales': True, 'aplica_extranjeros': False},
    )
    dep = Departamento.objects.create(codigo_dane='05', nombre='Antioquia', activo=True)
    mun = Municipio.objects.create(
        codigo_dane='05001', nombre='Medellín', departamento=dep, activo=True,
    )
    victima = Victima.objects.create(
        tipo_documento=td, numero_documento='111222333',
        primer_nombre='Ana', primer_apellido='Ruiz',
        fecha_nacimiento='1980-01-01', genero='F', estado_civil='SOLTERO',
        pertenencia_etnica='NINGUNA', estado_ruv='INCLUIDO',
        municipio_residencia=mun, creado_por=encuestador,
    )
    return Hogar.objects.create(
        autorizado=victima, municipio=mun,
        tipo_vivienda='CASA', condicion_ocupacion='PROPIA',
        estrato=1, numero_cuartos=2, numero_personas=1,
        estado='BORRADOR', creado_por=encuestador,
    )


def _instrumento(codigo='SKIP-TEST'):
    inst = Instrumento.objects.create(
        codigo=codigo, nombre='Instrumento skip', version='V1',
        vigente_desde=date(2021, 1, 1), activo=True, fuente_documental='tests',
    )
    cap = Capitulo.objects.create(
        instrumento=inst, codigo='C01', nombre='Cap 1', orden=1, nivel='HOGAR',
    )
    return inst, cap


def _pregunta(cap, codigo, orden, **kw):
    kw.setdefault('nivel', 'HOGAR')
    kw.setdefault('obligatoria', True)
    return Pregunta.objects.create(
        capitulo=cap, codigo_externo=codigo, no_pregunta=codigo,
        variable_bd=codigo, texto=f'Pregunta {codigo}', tipo='TEXTO',
        orden=orden, **kw,
    )


def _sesion(hogar, inst, encuestador):
    return SesionEncuesta.objects.create(
        hogar=hogar, instrumento=inst, encuestador=encuestador, estado='INICIADA',
    )


def _responder(sesion, pregunta, valor, miembro=None):
    return RespuestaEncuesta.objects.create(
        sesion=sesion, pregunta=pregunta, miembro=miembro, valor=valor,
    )


# ─── El defecto de fondo del APK-005 ─────────────────────────────────────────

@pytest.mark.django_db
class TestObligatoriaOculta:
    def test_la_obligatoria_oculta_no_infla_el_denominador(self, hogar, encuestador):
        """
        Este es el APK-005. Tres obligatorias, una escondida detrás de una regla
        HABILITAR que no se dispara: responder las otras dos ES terminar la
        entrevista, y tiene que decir 100 %.

        Con la implementación vieja daba 66 % — una sesión que se cierra
        completa y se ve a dos tercios.
        """
        inst, cap = _instrumento()
        p1 = _pregunta(cap, 'A1', 1)
        p2 = _pregunta(cap, 'A2', 2)
        oculta = _pregunta(cap, 'A3', 3)
        ReglaSkipLogic.objects.create(
            instrumento=inst, pregunta_origen=p1, valor_trigger='SI',
            pregunta_afectada=oculta, accion=AccionSkipChoices.HABILITAR,
        )

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, p1, 'NO')
        _responder(sesion, p2, 'algo')

        assert sesion.recalcular_porcentaje() == 100

    def test_cuando_la_regla_se_dispara_la_pregunta_si_cuenta(self, hogar, encuestador):
        """El espejo del anterior: si la condición se cumple, la pregunta entra
        al denominador y el progreso baja. Sin esto, 'no contar las ocultas'
        podría degenerar en 'no contar nada'."""
        inst, cap = _instrumento()
        p1 = _pregunta(cap, 'A1', 1)
        p2 = _pregunta(cap, 'A2', 2)
        condicional = _pregunta(cap, 'A3', 3)
        ReglaSkipLogic.objects.create(
            instrumento=inst, pregunta_origen=p1, valor_trigger='SI',
            pregunta_afectada=condicional, accion=AccionSkipChoices.HABILITAR,
        )

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, p1, 'SI')       # dispara la regla
        _responder(sesion, p2, 'algo')

        # 2 de 3: A3 ahora es visible y está sin responder.
        assert sesion.recalcular_porcentaje() == 66

        _responder(sesion, condicional, 'ya')
        assert sesion.recalcular_porcentaje() == 100

    def test_responder_una_oculta_no_infla_el_numerador(self, hogar, encuestador):
        """
        Una respuesta que quedó fuera de flujo —se capturó y después la regla
        dejó de cumplirse— no puede sumar. Si no cuenta abajo, tampoco arriba;
        de lo contrario el porcentaje podría pasarse de 100.
        """
        inst, cap = _instrumento()
        p1 = _pregunta(cap, 'A1', 1)
        oculta = _pregunta(cap, 'A2', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, pregunta_origen=p1, valor_trigger='SI',
            pregunta_afectada=oculta, accion=AccionSkipChoices.HABILITAR,
        )

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, p1, 'NO')       # la regla NO se cumple → A2 oculta
        _responder(sesion, oculta, 'quedó de antes')

        # Solo A1 cuenta, y está respondida.
        assert sesion.recalcular_porcentaje() == 100

    def test_deshabilitar_activa_saca_la_pregunta_de_la_cuenta(self, hogar, encuestador):
        inst, cap = _instrumento()
        p1 = _pregunta(cap, 'A1', 1)
        p2 = _pregunta(cap, 'A2', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, pregunta_origen=p1, valor_trigger='X',
            pregunta_afectada=p2, accion=AccionSkipChoices.DESHABILITAR,
        )

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, p1, 'X')        # deshabilita A2

        assert sesion.recalcular_porcentaje() == 100


@pytest.mark.django_db
class TestPrecargadas:
    def test_la_precargada_no_entra_al_denominador(self, hogar, encuestador):
        """Las precargadas vienen del padrón; no las responde nadie en la
        entrevista, así que no pueden impedir llegar al 100 %."""
        inst, cap = _instrumento()
        p1 = _pregunta(cap, 'A1', 1)
        _pregunta(cap, 'A2', 2, es_precargada=True)

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, p1, 'algo')

        assert sesion.recalcular_porcentaje() == 100


@pytest.mark.django_db
class TestPersonaPorMiembro:
    def test_la_pregunta_persona_cuenta_una_vez_por_miembro(self, hogar, encuestador):
        inst, cap = _instrumento()
        pp = _pregunta(cap, 'B1', 1, nivel='PERSONA')

        m1 = MiembroHogar.objects.create(
            hogar=hogar, parentesco='HIJO_A', rol='MIEMBRO',
            estado_inclusion='INCLUIDO', genero='M', fecha_nacimiento='2010-01-01',
            creado_por=encuestador,
        )
        m2 = MiembroHogar.objects.create(
            hogar=hogar, parentesco='HIJO_A', rol='MIEMBRO',
            estado_inclusion='INCLUIDO', genero='F', fecha_nacimiento='2012-01-01',
            creado_por=encuestador,
        )

        sesion = _sesion(hogar, inst, encuestador)
        assert sesion.recalcular_porcentaje() == 0

        _responder(sesion, pp, 'sí', miembro=m1)
        assert sesion.recalcular_porcentaje() == 50

        _responder(sesion, pp, 'sí', miembro=m2)
        assert sesion.recalcular_porcentaje() == 100

    def test_la_visibilidad_persona_se_evalua_con_las_respuestas_de_cada_miembro(
        self, hogar, encuestador,
    ):
        """
        El punto entero de la skip-logic por persona: la misma pregunta puede
        estar visible para un integrante y oculta para otro. Si se evaluara una
        vez sola, a uno de los dos se le contaría mal.
        """
        inst, cap = _instrumento()
        origen = _pregunta(cap, 'B1', 1, nivel='PERSONA')
        derivada = _pregunta(cap, 'B2', 2, nivel='PERSONA')
        ReglaSkipLogic.objects.create(
            instrumento=inst, pregunta_origen=origen, valor_trigger='SI',
            pregunta_afectada=derivada, accion=AccionSkipChoices.HABILITAR,
        )

        m1 = MiembroHogar.objects.create(
            hogar=hogar, parentesco='HIJO_A', rol='MIEMBRO',
            estado_inclusion='INCLUIDO', genero='M', fecha_nacimiento='2010-01-01',
            creado_por=encuestador,
        )
        m2 = MiembroHogar.objects.create(
            hogar=hogar, parentesco='HIJO_A', rol='MIEMBRO',
            estado_inclusion='INCLUIDO', genero='F', fecha_nacimiento='2012-01-01',
            creado_por=encuestador,
        )

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, origen, 'SI', miembro=m1)   # a m1 se le abre B2
        _responder(sesion, origen, 'NO', miembro=m2)   # a m2 no

        # Denominador: B1 de m1, B2 de m1, B1 de m2 = 3. Respondidas: 2.
        assert sesion.recalcular_porcentaje() == 66

        _responder(sesion, derivada, 'listo', miembro=m1)
        assert sesion.recalcular_porcentaje() == 100


@pytest.mark.django_db
class TestBordes:
    def test_sin_obligatorias_visibles_devuelve_cero_sin_reventar(self, hogar, encuestador):
        """Todas las obligatorias detrás de reglas que no se cumplen: no hay
        nada que responder. Devuelve 0 y no divide por cero."""
        inst, cap = _instrumento()
        libre = _pregunta(cap, 'A1', 1, obligatoria=False)
        oculta = _pregunta(cap, 'A2', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, pregunta_origen=libre, valor_trigger='SI',
            pregunta_afectada=oculta, accion=AccionSkipChoices.HABILITAR,
        )

        sesion = _sesion(hogar, inst, encuestador)
        assert sesion.recalcular_porcentaje() == 0

    def test_instrumento_sin_preguntas_devuelve_cero(self, hogar, encuestador):
        inst, _cap = _instrumento()
        sesion = _sesion(hogar, inst, encuestador)
        assert sesion.recalcular_porcentaje() == 0

    def test_pregunta_inactiva_no_cuenta(self, hogar, encuestador):
        inst, cap = _instrumento()
        p1 = _pregunta(cap, 'A1', 1)
        _pregunta(cap, 'A2', 2, activa=False)

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, p1, 'algo')

        assert sesion.recalcular_porcentaje() == 100

    def test_el_resultado_siempre_queda_entre_0_y_100(self, hogar, encuestador):
        inst, cap = _instrumento()
        p1 = _pregunta(cap, 'A1', 1)
        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, p1, 'algo')

        pct = sesion.recalcular_porcentaje()
        assert 0 <= pct <= 100
