"""
El porcentaje evalúa las reglas por expresión con el contexto REAL de cada
integrante — edad, sexo, etnia y RUV.

Este archivo existe por un defecto que se coló en el primer arreglo del APK-005:
`recalcular_porcentaje` llamaba al motor sin contexto, así que las reglas por
expresión —127 en los fixtures, la mayoría del territorial— nunca se evaluaban
bien. Y se equivocaba en las dos direcciones:

  · `sexo == '2' and edad >= 12` → HABILITAR nunca disparaba, la obligatoria
    salía del denominador y una entrevista SIN el bloque de gestación cerraba
    en 100 %.
  · `etnia != 'ninguno'` → con el contexto vacío la variable valía `''`, y
    `'' != 'ninguno'` es VERDADERO, así que preguntas del capítulo étnico
    quedaban exigidas a todo el mundo y la sesión no llegaba nunca al 100 %.
    O sea, el APK-005 otra vez.

El criterio tiene que ser el mismo que usa la pantalla de captura del móvil
(`construirContextoMiembro`): si el backend decidiera la visibilidad con otros
datos, exigiría preguntas que la app nunca mostró.
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
from apps.formulario.skiplogic import evaluar_expresion_segura
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta


@pytest.fixture
def encuestador():
    perfil = Perfil.objects.create(
        codigo='PCTX', nombre='Test Ctx', puede_caracterizar=True, activo=True,
    )
    u = Usuario.objects.create_user(
        codigo_usuario='ECTX01', password='Test123!!!!',
        nombre_completo='Encuestador Ctx', email='ectx@srni.dev',
        perfil=perfil, activo=True,
    )
    return Usuario.objects.select_related('perfil').get(pk=u.pk)


@pytest.fixture
def hogar(encuestador):
    td, _ = TipoDocumento.objects.get_or_create(
        codigo='CC',
        defaults={'nombre': 'Cédula', 'aplica_nacionales': True, 'aplica_extranjeros': False},
    )
    dep = Departamento.objects.create(codigo_dane='08', nombre='Atlántico', activo=True)
    mun = Municipio.objects.create(
        codigo_dane='08001', nombre='Barranquilla', departamento=dep, activo=True,
    )
    victima = Victima.objects.create(
        tipo_documento=td, numero_documento='777666555',
        primer_nombre='Luz', primer_apellido='Mora',
        fecha_nacimiento='1985-05-05', genero='F', estado_civil='SOLTERO',
        pertenencia_etnica='NINGUNA', estado_ruv='INCLUIDO',
        municipio_residencia=mun, creado_por=encuestador,
    )
    return Hogar.objects.create(
        autorizado=victima, municipio=mun, tipo_vivienda='CASA',
        condicion_ocupacion='PROPIA', estrato=1, numero_cuartos=2,
        numero_personas=2, estado='BORRADOR', creado_por=encuestador,
    )


def _instrumento():
    inst = Instrumento.objects.create(
        codigo='CTX-TEST', nombre='Instrumento ctx', version='V1',
        vigente_desde=date(2021, 1, 1), activo=True, fuente_documental='tests',
    )
    cap = Capitulo.objects.create(
        instrumento=inst, codigo='C01', nombre='Cap 1', orden=1, nivel='HOGAR',
    )
    return inst, cap


def _pregunta(cap, codigo, orden, **kw):
    kw.setdefault('nivel', 'PERSONA')
    kw.setdefault('obligatoria', True)
    return Pregunta.objects.create(
        capitulo=cap, codigo_externo=codigo, no_pregunta=codigo,
        variable_bd=codigo, texto=f'Pregunta {codigo}', tipo='TEXTO',
        orden=orden, **kw,
    )


def _miembro(hogar, encuestador, **kw):
    kw.setdefault('parentesco', 'HIJO_A')
    kw.setdefault('rol', 'MIEMBRO')
    kw.setdefault('estado_inclusion', 'INCLUIDO')
    return MiembroHogar.objects.create(hogar=hogar, creado_por=encuestador, **kw)


def _sesion(hogar, inst, encuestador):
    return SesionEncuesta.objects.create(
        hogar=hogar, instrumento=inst, encuestador=encuestador, estado='INICIADA',
    )


def _responder(sesion, pregunta, valor, miembro=None):
    return RespuestaEncuesta.objects.create(
        sesion=sesion, pregunta=pregunta, miembro=miembro, valor=valor,
    )


# ─── Reglas por expresión: sexo y edad ───────────────────────────────────────

@pytest.mark.django_db
class TestSexoYEdad:
    def test_el_bloque_de_gestacion_se_le_exige_a_ella_y_no_a_el(self, hogar, encuestador):
        """
        La regla real del territorial: `sexo == '2' and edad >= 12` habilita el
        bloque de gestación/maternidad.

        Sin contexto, esa regla no disparaba nunca y la pregunta salía del
        denominador: una entrevista a la que le falta ese bloque entero se
        cerraba y se reportaba como completa.
        """
        inst, cap = _instrumento()
        base = _pregunta(cap, 'A1', 1)
        gestacion = _pregunta(cap, 'B2', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, expresion_origen="sexo == '2' and edad >= 12",
            pregunta_afectada=gestacion, accion=AccionSkipChoices.HABILITAR,
        )

        ella = _miembro(hogar, encuestador, genero='F', fecha_nacimiento='1995-01-01')
        el = _miembro(hogar, encuestador, genero='M', fecha_nacimiento='1990-01-01')

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, base, 'x', miembro=ella)
        _responder(sesion, base, 'x', miembro=el)

        # Denominador: A1 de ella, A1 de él, B2 SOLO de ella = 3. Respondidas: 2.
        assert sesion.recalcular_porcentaje() == 66

        _responder(sesion, gestacion, 'sí', miembro=ella)
        assert sesion.recalcular_porcentaje() == 100

    def test_la_menor_de_12_no_arrastra_el_bloque(self, hogar, encuestador):
        inst, cap = _instrumento()
        base = _pregunta(cap, 'A1', 1)
        gestacion = _pregunta(cap, 'B2', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, expresion_origen="sexo == '2' and edad >= 12",
            pregunta_afectada=gestacion, accion=AccionSkipChoices.HABILITAR,
        )
        nina = _miembro(hogar, encuestador, genero='F', fecha_nacimiento='2020-01-01')

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, base, 'x', miembro=nina)

        assert sesion.recalcular_porcentaje() == 100

    def test_la_edad_respondida_manda_sobre_la_registrada(self, hogar, encuestador):
        """B9 es la edad que captura el encuestador. Si la registró, gana sobre
        la fecha de nacimiento del padrón — que puede estar mal."""
        inst, cap = _instrumento()
        b9 = _pregunta(cap, 'B9', 1)
        mayor = _pregunta(cap, 'X1', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, expresion_origen="edad >= 18",
            pregunta_afectada=mayor, accion=AccionSkipChoices.HABILITAR,
        )
        # Registrado como menor, pero el encuestador capturó 40.
        m = _miembro(hogar, encuestador, genero='F', fecha_nacimiento='2015-01-01')

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, b9, '40', miembro=m)

        # X1 quedó visible por la edad capturada y está sin responder → 1 de 2.
        assert sesion.recalcular_porcentaje() == 50

    def test_sin_sexo_conocido_la_regla_no_dispara(self, hogar, encuestador):
        """
        El género del padrón no se hereda: el join acierta la mitad de las veces
        (ver join_caracterizacion_roto.md). Sin dato, la variable queda
        desconocida y la regla NO se dispara — no afirma nada.
        """
        inst, cap = _instrumento()
        base = _pregunta(cap, 'A1', 1)
        condicional = _pregunta(cap, 'B2', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, expresion_origen="sexo == '2'",
            pregunta_afectada=condicional, accion=AccionSkipChoices.HABILITAR,
        )
        m = _miembro(hogar, encuestador, genero='', fecha_nacimiento='1990-01-01')

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, base, 'x', miembro=m)

        assert sesion.recalcular_porcentaje() == 100


# ─── El default silencioso que exigía preguntas imposibles ───────────────────

@pytest.mark.django_db
class TestEtniaYRuv:
    def test_etnia_distinta_de_ninguno_no_exige_el_capitulo_etnico(self, hogar, encuestador):
        """
        `etnia != 'ninguno'` con la variable en `''` daba VERDADERO, así que la
        pregunta quedaba en el denominador para siempre. Nadie podía responderla
        —la app nunca la muestra, fija `etnia = 'ninguno'`— y la sesión no
        llegaba jamás al 100 %. Es el APK-005 por otra puerta.
        """
        inst, cap = _instrumento()
        base = _pregunta(cap, 'A1', 1)
        etnica = _pregunta(cap, 'C7', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, expresion_origen="etnia != 'ninguno'",
            pregunta_afectada=etnica, accion=AccionSkipChoices.HABILITAR,
        )
        m = _miembro(hogar, encuestador, genero='F', fecha_nacimiento='1990-01-01')

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, base, 'x', miembro=m)

        assert sesion.recalcular_porcentaje() == 100

    def test_ruv_incluido_igual_false_se_evalua_contra_el_dato_del_miembro(
        self, hogar, encuestador,
    ):
        """`false` en minúscula viene del diccionario, no de Python: el AST lo ve
        como un nombre. Tiene que valer el booleano, no un desconocido."""
        inst, cap = _instrumento()
        base = _pregunta(cap, 'A1', 1)
        solo_no_ruv = _pregunta(cap, 'A21', 2)
        ReglaSkipLogic.objects.create(
            instrumento=inst, expresion_origen="ruv_incluido == false",
            pregunta_afectada=solo_no_ruv, accion=AccionSkipChoices.HABILITAR,
        )

        incluido = _miembro(
            hogar, encuestador, genero='F', fecha_nacimiento='1990-01-01',
            estado_inclusion='INCLUIDO',
        )
        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, base, 'x', miembro=incluido)
        # A21 no aplica a quien SÍ está en el RUV.
        assert sesion.recalcular_porcentaje() == 100

        fuera = _miembro(
            hogar, encuestador, genero='M', fecha_nacimiento='1990-01-01',
            estado_inclusion='NO_INCLUIDO',
        )
        _responder(sesion, base, 'x', miembro=fuera)
        # Ahora: A1 de cada uno (2) + A21 solo del segundo (1) = 3; respondidas 2.
        assert sesion.recalcular_porcentaje() == 66


# ─── Estabilidad ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEstabilidad:
    def test_el_porcentaje_no_depende_del_orden_de_los_integrantes(self, hogar, encuestador):
        """
        Las preguntas HOGAR se evalúan una sola vez, con el contexto del
        AUTORIZADO. Si se usara «el primero que devuelva la base», el mismo
        hogar podría dar dos porcentajes distintos.
        """
        inst, cap = _instrumento()
        base = _pregunta(cap, 'A1', 1, nivel='HOGAR')
        solo_mujer = _pregunta(cap, 'H1', 2, nivel='HOGAR')
        ReglaSkipLogic.objects.create(
            instrumento=inst, expresion_origen="sexo == '2'",
            pregunta_afectada=solo_mujer, accion=AccionSkipChoices.HABILITAR,
        )

        _miembro(hogar, encuestador, genero='M', fecha_nacimiento='1990-01-01')
        _miembro(
            hogar, encuestador, genero='F', fecha_nacimiento='1985-05-05',
            es_autorizado=True, victima=hogar.autorizado,
        )
        _miembro(hogar, encuestador, genero='M', fecha_nacimiento='1992-01-01')

        sesion = _sesion(hogar, inst, encuestador)
        _responder(sesion, base, 'x')

        # La autorizada es mujer → H1 aplica y falta → 1 de 2.
        assert sesion.recalcular_porcentaje() == 50

    def test_el_contexto_no_agrega_consultas(self, django_assert_max_num_queries, hogar, encuestador):
        """Los datos demográficos viajan en la misma consulta de integrantes."""
        inst, cap = _instrumento()
        _pregunta(cap, 'A1', 1)
        for i in range(5):
            _miembro(hogar, encuestador, genero='F', fecha_nacimiento='1990-01-01')

        sesion = _sesion(hogar, inst, encuestador)
        with django_assert_max_num_queries(6):
            sesion.recalcular_porcentaje()


# ─── El evaluador, directo ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestEvaluador:
    @pytest.mark.parametrize('expr, ctx, esperado', [
        # Variable desconocida → la regla no dispara, en cualquier operador.
        ("etnia != 'ninguno'", {}, False),
        ("etnia == 'ninguno'", {}, False),
        ("edad >= 18", {}, False),
        ("sexo == '2'", {'sexo': ''}, False),
        # Literales en minúscula del diccionario.
        ("ruv_incluido == false", {'ruv_incluido': False}, True),
        ("ruv_incluido == false", {'ruv_incluido': True}, False),
        ("ruv_incluido == true", {'ruv_incluido': True}, True),
        # Lo que sí se conoce se compara normal.
        ("edad >= 18", {'edad': 30}, True),
        ("edad >= 18", {'edad': 10}, False),
        ("sexo == '2' and edad >= 12", {'sexo': '2', 'edad': 30}, True),
        ("sexo == '2' and edad >= 12", {'sexo': '1', 'edad': 30}, False),
        # AND mixto: contexto + respuesta de otra pregunta.
        ("etnia == 'indigena' and D6 == '2'", {'etnia': 'indigena'}, False),
    ])
    def test_casos(self, expr, ctx, esperado):
        assert evaluar_expresion_segura(expr, ctx, {}) is esperado

    @pytest.mark.parametrize('expr, ctx, esperado', [
        # La regla REAL del telefonico V8. Con `False` en mayuscula y con `or`.
        ("ruv_incluido == False or edad < 3", {'ruv_incluido': False, 'edad': 30}, True),
        ("ruv_incluido == False or edad < 3", {'ruv_incluido': True, 'edad': 2}, True),
        ("ruv_incluido == False or edad < 3", {'ruv_incluido': True, 'edad': 30}, False),
        # Una rama que no se puede evaluar no mata a la otra: la edad decide.
        ("ruv_incluido == False or edad < 3", {'edad': 2}, True),
        ("ruv_incluido == False or edad < 3", {'ruv_incluido': False}, True),
        ("ruv_incluido == False or edad < 3", {}, False),
        # En un AND, la rama desconocida si hace fallar la condicion entera.
        ("sexo == '2' and edad >= 12", {'edad': 30}, False),
        ("sexo == '2' and edad >= 12", {'sexo': '2'}, False),
    ])
    def test_or_y_literales_en_mayuscula(self, expr, ctx, esperado):
        assert evaluar_expresion_segura(expr, ctx, {}) is esperado

    def test_una_respuesta_vacia_no_cuenta_como_distinta(self):
        """Espejo del móvil: respuesta sin capturar = desconocida, no ''."""
        assert evaluar_expresion_segura("D6 != '2'", {}, {'D6': ''}) is False
        assert evaluar_expresion_segura("D6 != '2'", {}, {'D6': '1'}) is True
