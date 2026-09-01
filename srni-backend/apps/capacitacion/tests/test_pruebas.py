"""
Pruebas de capacitación — comportamiento que el negocio pidió expresamente.

Lo que se protege aquí:

1. La prueba es **pública**: se responde sin iniciar sesión, porque ninguno de
   los convocados tiene credenciales todavía.
2. El cuestionario **no revela la respuesta correcta**. Si la revelara, bastaría
   abrir las herramientas del navegador para tener el examen resuelto.
3. **No se puede repetir**: un intento por correo y prueba, garantizado en base
   de datos y no solo en la interfaz.
4. El **tablero de resultados sí exige sesión** y permiso de reportes.
"""
import pytest
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.capacitacion.models import IntentoPrueba, PreguntaPrueba, Prueba

CODIGO = 'prueba-demo-pre'


@pytest.fixture
def prueba(db):
    p = Prueba.objects.create(
        codigo=CODIGO, titulo='Demo', momento=Prueba.Momento.PRE, pareja='demo')
    PreguntaPrueba.objects.create(
        prueba=p, orden=1, enunciado='¿Cuántos años dura la vigencia?',
        opciones=[{'clave': 'A', 'texto': 'Uno'}, {'clave': 'B', 'texto': 'Dos'}],
        correcta='B', explicacion='Son dos años.')
    PreguntaPrueba.objects.create(
        prueba=p, orden=2, enunciado='¿Quién autoriza la excepción?',
        opciones=[{'clave': 'A', 'texto': 'Coordinación'}, {'clave': 'B', 'texto': 'El encuestador'}],
        correcta='A', explicacion='La autoriza coordinación desde el panel.')
    return p


@pytest.fixture
def preguntas(prueba):
    return list(prueba.preguntas.order_by('orden'))


def _publico():
    return APIClient()


# ─── Superficie pública ───────────────────────────────────────────────────────

def test_el_cuestionario_se_obtiene_sin_iniciar_sesion(prueba):
    r = _publico().get(f'/api/capacitacion/prueba/{CODIGO}/')
    assert r.status_code == 200
    assert r.data['total_preguntas'] == 2


def test_el_cuestionario_no_revela_la_respuesta_correcta(prueba):
    r = _publico().get(f'/api/capacitacion/prueba/{CODIGO}/')
    crudo = str(r.data)
    assert 'correcta' not in crudo
    assert 'explicacion' not in crudo
    for p in r.data['preguntas']:
        assert set(p) == {'id', 'orden', 'enunciado', 'opciones'}


def test_responder_califica_en_el_servidor_y_devuelve_el_detalle(prueba, preguntas):
    p1, p2 = preguntas
    r = _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/', {
        'correo': 'Ana.Perez@unidadvictimas.gov.co',
        'nombre': 'Ana Pérez',
        'respuestas': {str(p1.id): 'B', str(p2.id): 'B'},
        'segundos': 90,
    }, format='json')
    assert r.status_code == 201
    assert r.data['puntaje'] == 1 and r.data['total'] == 2
    assert r.data['porcentaje'] == 50
    fallada = [d for d in r.data['detalle'] if not d['acerto']][0]
    assert fallada['explicacion']          # la explicación solo va donde falló
    acertada = [d for d in r.data['detalle'] if d['acerto']][0]
    assert acertada['explicacion'] == ''


def test_no_se_puede_presentar_dos_veces(prueba, preguntas):
    cuerpo = {'correo': 'ana@unidadvictimas.gov.co',
              'respuestas': {str(preguntas[0].id): 'B'}}
    primera = _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                              cuerpo, format='json')
    assert primera.status_code == 201
    segunda = _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                              cuerpo, format='json')
    assert segunda.status_code == 409
    assert segunda.data['ya_presentada'] is True
    assert IntentoPrueba.objects.filter(prueba=prueba).count() == 1


def test_el_correo_se_compara_normalizado(prueba, preguntas):
    """Mayúsculas y espacios no crean una persona distinta."""
    cli = _publico()
    cli.post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
             {'correo': 'ana@unidadvictimas.gov.co',
              'respuestas': {str(preguntas[0].id): 'B'}}, format='json')
    r = cli.post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                 {'correo': '  ANA@UnidadVictimas.gov.co ',
                  'respuestas': {str(preguntas[0].id): 'B'}}, format='json')
    assert r.status_code == 409


def test_estado_dice_si_ya_presento_y_con_que_puntaje(prueba, preguntas):
    cli = _publico()
    antes = cli.get(f'/api/capacitacion/prueba/{CODIGO}/estado/?correo=ana@unidadvictimas.gov.co')
    assert antes.data['presentada'] is False

    cli.post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
             {'correo': 'ana@unidadvictimas.gov.co',
              'respuestas': {str(preguntas[0].id): 'B', str(preguntas[1].id): 'A'}},
             format='json')

    despues = cli.get(f'/api/capacitacion/prueba/{CODIGO}/estado/?correo=ana@unidadvictimas.gov.co')
    assert despues.data['presentada'] is True
    assert despues.data['puntaje'] == 2
    assert despues.data['nivel'] == 'APROPIADO'


def test_estado_exige_el_correo(prueba):
    r = _publico().get(f'/api/capacitacion/prueba/{CODIGO}/estado/')
    assert r.status_code == 400


def test_una_prueba_cerrada_no_admite_respuestas(prueba, preguntas):
    prueba.abierta = False
    prueba.save(update_fields=['abierta'])
    r = _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                        {'correo': 'ana@unidadvictimas.gov.co',
                         'respuestas': {str(preguntas[0].id): 'B'}}, format='json')
    assert r.status_code == 409


def test_correo_invalido_se_rechaza(prueba, preguntas):
    r = _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                        {'correo': 'no-es-un-correo',
                         'respuestas': {str(preguntas[0].id): 'B'}}, format='json')
    assert r.status_code == 400


def test_una_pregunta_sin_responder_cuenta_como_error(prueba, preguntas):
    r = _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                        {'correo': 'ana@unidadvictimas.gov.co',
                         'respuestas': {str(preguntas[0].id): 'B'}}, format='json')
    assert r.status_code == 201
    assert r.data['puntaje'] == 1 and r.data['total'] == 2


# ─── Superficie interna ───────────────────────────────────────────────────────

@pytest.fixture
def supervisor(db):
    perfil = Perfil.objects.create(
        codigo='SUP_CAP', nombre='Supervisor', puede_ver_reportes=True, activo=True)
    return Usuario.objects.create_user(
        codigo_usuario='SUPCAP', password='Test2026!', nombre_completo='Sup',
        email='sup@test.dev', perfil=perfil, activo=True)


def test_los_resultados_no_son_publicos(prueba):
    assert _publico().get('/api/capacitacion/resultados/').status_code in (401, 403)


def test_los_resultados_dan_resumen_y_corte_por_pregunta(prueba, preguntas, supervisor):
    _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                    {'correo': 'ana@unidadvictimas.gov.co', 'nombre': 'Ana',
                     'respuestas': {str(preguntas[0].id): 'B', str(preguntas[1].id): 'B'}},
                    format='json')
    cli = APIClient()
    cli.force_authenticate(user=supervisor)
    r = cli.get('/api/capacitacion/resultados/')
    assert r.status_code == 200
    assert r.data['resumen']['presentaron'] == 1
    assert len(r.data['intentos']) == 1
    # La segunda pregunta la falló: 0 % de acierto en el corte por pregunta.
    porcentajes = {f['orden']: f['porcentaje_acierto'] for f in r.data['por_pregunta']}
    assert porcentajes[1] == 100 and porcentajes[2] == 0


def test_la_ganancia_empareja_pre_y_post_por_correo(prueba, preguntas, supervisor):
    post = Prueba.objects.create(codigo='prueba-demo-post', titulo='Demo post',
                                 momento=Prueba.Momento.POST, pareja='demo')
    for p in preguntas:
        PreguntaPrueba.objects.create(
            prueba=post, orden=p.orden, enunciado=p.enunciado,
            opciones=p.opciones, correcta=p.correcta)

    correo = 'ana@unidadvictimas.gov.co'
    _publico().post(f'/api/capacitacion/prueba/{CODIGO}/responder/',
                    {'correo': correo, 'respuestas': {str(preguntas[0].id): 'A'}},
                    format='json')          # 0 de 2
    pp = list(post.preguntas.order_by('orden'))
    _publico().post('/api/capacitacion/prueba/prueba-demo-post/responder/',
                    {'correo': correo,
                     'respuestas': {str(pp[0].id): 'B', str(pp[1].id): 'A'}},
                    format='json')          # 2 de 2

    cli = APIClient()
    cli.force_authenticate(user=supervisor)
    fila = cli.get('/api/capacitacion/resultados/').data['ganancia'][0]
    assert fila['pre'] == 0 and fila['post'] == 2 and fila['ganancia'] == 2
