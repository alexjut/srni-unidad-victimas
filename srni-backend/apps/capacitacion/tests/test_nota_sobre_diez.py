"""
La nota va sobre 10, aunque el cuestionario tenga 13 preguntas.

─── El desfase que esto cierra ──────────────────────────────────────────────
La escala que aprobó la Dirección técnica es **sobre 10**: 9-10 apropiado, 7-8
suficiente, 5-6 básico, 0-4 insuficiente. Y el criterio para rediseñar el bloque
es «ganancia promedio inferior a 2 puntos». Las dos cosas viven en esa escala.

El tablero contaba el puntaje **absoluto** contra un umbral fijo de 7. Mientras el
cuestionario tuvo 10 preguntas, coincidía. El 11-sep-2026 pasó a 13 y el cálculo
quedó midiendo otra cosa sin que nada fallara:

  · **7 de 13 es 54 %**, y pasaba por «habilitado» cuando la escala pide 70 %;
  · el promedio mezclaba intentos de 10 preguntas con intentos de 13 como si
    fueran la misma medida.

Es el tipo de defecto que no se ve: el informe sale, tiene números, y dice que el
equipo quedó mejor de lo que quedó. Por eso hay prueba.
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/capacitacion/resultados/'


@pytest.fixture
def escenario(db):
    """
    Un cuestionario de 13 preguntas y tres intentos en los puntos que importan:
    justo debajo del umbral, justo encima, y perfecto.
    """
    from apps.autenticacion.models import Perfil, Usuario
    from apps.capacitacion.models import IntentoPrueba, Prueba

    perfil = Perfil.objects.create(
        codigo='SUP_NOTA', nombre='Supervisor', activo=True,
        puede_ver_reportes=True, puede_buscar_rni=True)
    supervisor = Usuario.objects.create_user(
        codigo_usuario='SUPNOTA', password='SrniTest2026!',
        nombre_completo='Sup Nota', email='supnota@srni.dev', perfil=perfil,
        activo=True)

    prueba = Prueba.objects.create(
        codigo='cap-nota-pre', titulo='Pre', momento=Prueba.Momento.PRE,
        pareja='cap-nota')

    def intento(correo, puntaje, total=13):
        return IntentoPrueba.objects.create(
            prueba=prueba, correo=correo, puntaje=puntaje, total=total)

    # 8/13 = 61,5 % → sobre 10 es 6,2 → NO alcanza Suficiente (7)
    intento('justo.debajo@srni.dev', 8)
    # 10/13 = 76,9 % → sobre 10 es 7,7 → Suficiente
    intento('justo.encima@srni.dev', 10)
    # 13/13 → 10 → Apropiado
    intento('perfecto@srni.dev', 13)

    cliente = APIClient()
    cliente.force_authenticate(user=supervisor)
    return {'cliente': cliente, 'prueba': prueba, 'intento': intento}


def _resumen(escenario, **params):
    r = escenario['cliente'].get(URL, params)
    assert r.status_code == 200, r.data
    return r.data['resumen'] if 'resumen' in r.data else r.data


def test_el_promedio_va_sobre_diez_y_no_sobre_el_total(escenario):
    """
    Los tres intentos son 8, 10 y 13 sobre 13 → 6,15 + 7,69 + 10 = 23,85 / 3.
    Antes devolvía el promedio de 8, 10 y 13, que es 10,33 «sobre 10».
    """
    d = _resumen(escenario, prueba='cap-nota-pre')

    assert d['presentaron'] == 3
    assert 7.9 <= d['promedio'] <= 8.0
    assert d['promedio'] <= 10, 'un promedio mayor que 10 no cabe en la escala'


def test_la_respuesta_dice_sobre_que_escala_esta(escenario):
    """
    Un número sin unidad es exactamente cómo se llegó a comparar 7 sobre 13 con
    7 sobre 10. Que la respuesta lo diga evita repetirlo.
    """
    d = _resumen(escenario, prueba='cap-nota-pre')

    assert d['escala'] == 10
    assert d['umbral_habilitado'] == 7


def test_el_umbral_de_habilitado_es_el_70_por_ciento(escenario):
    """
    8 de 13 es 61,5 %: no alcanza. 10 y 13 sí. Con el umbral fijo en 7 absoluto,
    los tres pasaban y el informe decía que nadie quedó por debajo.
    """
    d = _resumen(escenario, prueba='cap-nota-pre')

    assert d['insuficientes'] == 1


def test_un_intento_con_total_cero_no_revienta(escenario):
    """
    No debería existir, pero un intento sin preguntas dividiría por cero y tumbaría
    el tablero entero el día que alguien lo abra.
    """
    escenario['intento']('raro@srni.dev', 0, total=0)

    d = _resumen(escenario, prueba='cap-nota-pre')

    assert d['presentaron'] == 4
    # El de total 0 no cuenta como «no habilitado»: no se puede afirmar nada de él.
    assert d['insuficientes'] == 1


def test_sigue_funcionando_con_un_cuestionario_de_diez(escenario):
    """
    La corrección no puede romper el caso histórico: 6 de 10 son 6 sobre 10 y no
    alcanzan; 8 de 10 son 8 y sí.
    """
    from apps.capacitacion.models import IntentoPrueba, Prueba

    vieja = Prueba.objects.create(
        codigo='cap-vieja-pre', titulo='Pre 10', momento=Prueba.Momento.PRE,
        pareja='cap-vieja')
    IntentoPrueba.objects.create(prueba=vieja, correo='a@srni.dev',
                                 puntaje=6, total=10)
    IntentoPrueba.objects.create(prueba=vieja, correo='b@srni.dev',
                                 puntaje=8, total=10)

    d = _resumen(escenario, prueba='cap-vieja-pre')

    assert d['presentaron'] == 2
    assert 6.9 <= d['promedio'] <= 7.1
    assert d['insuficientes'] == 1


def test_el_tablero_es_solo_de_supervision(escenario):
    """Mismo criterio que el resto: quien se mide no mira el instrumento."""
    from apps.autenticacion.models import Perfil, Usuario

    perfil = Perfil.objects.create(
        codigo='ENC_NOTA', nombre='Encuestador', activo=True,
        puede_caracterizar=True, puede_buscar_rni=True)
    encuestador = Usuario.objects.create_user(
        codigo_usuario='ENCNOTA', password='SrniTest2026!',
        nombre_completo='Enc Nota', email='encnota@srni.dev', perfil=perfil,
        activo=True)
    cliente = APIClient()
    cliente.force_authenticate(user=encuestador)

    assert cliente.get(URL).status_code == 403
