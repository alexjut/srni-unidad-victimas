"""
La excepción de vigencia se autoriza desde el front, no desde el celular.

Cambio del 14-ago-2026. Hasta entonces el encuestador elegía la ruta en campo y
adjuntaba una foto del fallo desde el teléfono. La operación indicó que **el
caracterizador no debe tener ese documento**: llega por canal institucional al
nivel central.

Lo que estos tests fijan es el reparto de poder que resultó del cambio — quien
autoriza el salto de un control dejó de ser quien lo ejecuta— y que la
habilitación no se convierta en un permiso permanente.
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/habilitaciones/'


@pytest.fixture
def escenario(db):
    import datetime

    from apps.autenticacion.models import Perfil, Usuario
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')

    def victima(doc, nombre, **extra):
        campos = dict(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=doc_hash('CC', doc),
            primer_nombre=nombre, primer_apellido='PEREZ',
            genero='F', estado_ruv='INCLUIDO',
            habilitado_para_caracterizacion=False,
            pertenencia_etnica='NINGUNA', discapacidad=False,
            fecha_ult_caracterizacion=datetime.datetime(
                2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
        )
        campos.update(extra)
        return Victima.objects.create(**campos)

    def usuario(codigo, **flags):
        perfil = Perfil.objects.create(
            codigo=f'P_{codigo}', nombre=codigo, activo=True, **flags)
        return Usuario.objects.create_user(
            codigo_usuario=codigo, password='SrniTest2026!',
            nombre_completo=codigo, email=f'{codigo}@srni.dev',
            perfil=perfil, activo=True)

    coordinador = usuario('COORDTEST', puede_caracterizar=True, puede_buscar_rni=True,
                          puede_ver_reportes=True, puede_autorizar_excepciones=True)
    encuestador = usuario('ENCTEST', puede_caracterizar=True, puede_buscar_rni=True)
    documentador = usuario('DOCTEST', puede_caracterizar=False, puede_buscar_rni=True,
                           puede_ver_reportes=True)

    def cliente_de(u):
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    return {
        'victima': victima('1115724047', 'ANA'),
        'coordinador': cliente_de(coordinador),
        'encuestador': cliente_de(encuestador),
        'documentador': cliente_de(documentador),
        'usuario_coordinador': coordinador,
        'usuario_encuestador': encuestador,
    }


@pytest.fixture
def otra_victima(db, escenario):
    """Segunda persona con ficha vigente — el caso del hogar amparado."""
    import datetime

    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    return Victima.objects.create(
        tipo_documento=TipoDocumento.objects.get(codigo='CC'),
        numero_documento='1030547250',
        numero_documento_hash=doc_hash('CC', '1030547250'),
        primer_nombre='MARIA', primer_apellido='GOMEZ',
        genero='F', estado_ruv='INCLUIDO',
        habilitado_para_caracterizacion=False,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
    )


def _payload(victima, **extra):
    datos = {
        'victima_id': str(victima.id),
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-451',
        'observacion': 'Fallo de tutela que ordena caracterizar de nuevo al hogar.',
    }
    datos.update(extra)
    return datos


# ── Quién puede y quién no ───────────────────────────────────────────────────

def test_la_coordinacion_autoriza_la_excepcion(escenario):
    r = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                      format='json')

    assert r.status_code == 201, r.data
    assert r.data['estado'] == 'VIGENTE'
    assert r.data['radicado'] == 'T-2026-451'
    assert r.data['autorizada_por_codigo'] == 'COORDTEST'
    # La situación que la justificó queda congelada: si después se
    # recaracteriza, la fecha de la víctima cambia y se perdería el motivo.
    assert r.data['vigente_hasta'] == '2028-03-14'


def test_el_encuestador_NO_puede_autorizarse_a_si_mismo(escenario):
    """
    El corazón del cambio. Si el que ejecuta puede autorizar, la regla de
    vigencia vuelve a ser opcional en la práctica — que es como estaba antes.
    """
    r = escenario['encuestador'].post(URL, _payload(escenario['victima']),
                                      format='json')

    assert r.status_code == 403


def test_el_documentador_tampoco_aunque_vea_reportes(escenario):
    """
    Se creó de solo lectura a propósito (11-ago). Habilitar una excepción altera
    la caracterización de una víctima: colgar este permiso de `ver_reportes` le
    daría por la puerta de atrás justo lo que se le negó de frente.
    """
    r = escenario['documentador'].post(URL, _payload(escenario['victima']),
                                       format='json')

    assert r.status_code == 403


# ── Lo que exige para autorizar ──────────────────────────────────────────────

def test_sin_radicado_no_se_autoriza(escenario):
    r = escenario['coordinador'].post(URL, _payload(escenario['victima'], radicado=''),
                                      format='json')
    assert r.status_code == 400
    assert 'radicado' in r.data


def test_un_motivo_de_dos_palabras_no_es_un_motivo(escenario):
    r = escenario['coordinador'].post(
        URL, _payload(escenario['victima'], observacion='ok'), format='json')
    assert r.status_code == 400


def test_la_ruta_general_no_tiene_excepcion_que_autorizar(escenario):
    """La General respeta la vigencia: no hay nada que levantar."""
    r = escenario['coordinador'].post(
        URL, _payload(escenario['victima'], ruta='GENERAL'), format='json')

    assert r.status_code == 400
    assert 'no omite' in str(r.data['ruta']).lower()


def test_el_archivo_es_opcional(escenario):
    """
    Decidido el 14-ago: exigirlo dejaría fuera los casos que llegan por correo o
    por teléfono, y el radicado ya permite ir a buscar el documento.
    """
    r = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                      format='json')
    assert r.status_code == 201
    assert r.data['soporte_nombre'] == ''


def test_no_se_habilita_a_una_excluida_del_RUV(escenario):
    """
    El manual da la excepción para fichas vigentes, no para revertir una
    decisión del RUV. Sin esta guarda el front otorgaría una habilitación que la
    app después ignora, y nadie entendería por qué.
    """
    victima = escenario['victima']
    victima.estado_ruv = 'EXCLUIDO'
    victima.save(update_fields=['estado_ruv'])

    r = escenario['coordinador'].post(URL, _payload(victima), format='json')

    assert r.status_code == 409
    assert 'excluida del RUV' in r.data['detail']


def test_no_se_apilan_dos_habilitaciones_sobre_la_misma_persona(escenario):
    primera = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                            format='json')
    assert primera.status_code == 201

    segunda = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                            format='json')

    assert segunda.status_code == 409
    # Devuelve la que ya existe: quien intentó autorizar de nuevo necesita ver
    # cuál es, no solo que no se pudo.
    assert segunda.data['habilitacion']['radicado'] == 'T-2026-451'


# ── Anular ───────────────────────────────────────────────────────────────────

def test_anular_deja_rastro_y_no_borra(escenario):
    from apps.encuestas.models import ExcepcionVigencia

    creada = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                           format='json')
    hid = creada.data['id']

    r = escenario['coordinador'].post(
        f'{URL}{hid}/anular/',
        {'motivo': 'Se autorizó sobre la persona equivocada.'}, format='json')

    assert r.status_code == 200
    assert r.data['estado'] == 'ANULADA'
    # Sigue existiendo: una autorización otorgada y retirada es justamente lo
    # que una auditoría necesita poder ver.
    assert ExcepcionVigencia.objects.filter(pk=hid).exists()


def test_no_se_anula_dos_veces(escenario):
    creada = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                           format='json')
    hid = creada.data['id']
    cuerpo = {'motivo': 'Se autorizó sobre la persona equivocada.'}

    escenario['coordinador'].post(f'{URL}{hid}/anular/', cuerpo, format='json')
    segunda = escenario['coordinador'].post(f'{URL}{hid}/anular/', cuerpo, format='json')

    assert segunda.status_code == 409


# ── La vía vieja quedó cerrada ───────────────────────────────────────────────

def test_el_endpoint_del_celular_responde_410_y_dice_a_donde_ir(escenario):
    """
    410 y no 404: una APK anterior a la v1.2.0 sigue instalada en campo, y un
    404 se lee como "falló la red" — manda al encuestador a buscar señal por un
    endpoint que no va a volver.
    """
    import datetime

    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar
    from apps.parametricas.models import Departamento, Municipio

    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)
    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL_H', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))
    hogar = Hogar.objects.create(autorizado=escenario['victima'], municipio=muni)

    from apps.encuestas.models import SesionEncuesta
    sesion = SesionEncuesta.objects.create(hogar=hogar, instrumento=instrumento,
                                           estado='INICIADA')

    r = escenario['encuestador'].post(
        f'/api/encuestas/{sesion.id}/excepcion-vigencia/',
        {'victima_id': str(escenario['victima'].id),
         'ruta': 'ACCIONES_CONSTITUCIONALES'})

    assert r.status_code == 410
    assert 'coordinación' in r.data['detail']


# ── El celular la ve sin señal ───────────────────────────────────────────────

def test_la_habilitacion_viaja_en_la_precarga_de_la_jornada(escenario, settings):
    """
    Si solo se pudiera consultar en línea, el caso quedaría igual de bloqueado
    que antes: la habilitación se otorga en la web y el encuestador está en
    territorio, donde muchas veces no hay señal.
    """
    # El default de tests es MOCK, que devuelve un padrón inventado. Acá hace
    # falta el repositorio real: lo que se verifica es justamente que el dato
    # salga de la base y llegue hasta la respuesta.
    settings.VICTIMA_REPOSITORY = 'DJANGO'
    escenario['coordinador'].post(URL, _payload(escenario['victima']), format='json')

    r = escenario['encuestador'].get('/api/victimas/precarga/')

    assert r.status_code == 200
    fila = next(p for p in r.data['padron'] if p['documento'] == '1115724047')
    assert fila['habilitada_por_excepcion'] is True
    assert fila['excepcion_radicado'] == 'T-2026-451'


# ── Buscar y autorizar en lote ───────────────────────────────────────────────
#
# Un fallo de tutela ampara a un hogar entero. Pedirle a coordinación que busque
# de a una y repita el formulario veinte veces es cómo se terminan autorizando
# cosas a las apuradas.

def test_buscar_devuelve_el_id_que_pide_el_post(escenario):
    """
    Quien autoriza tiene el documento en el oficio, no un UUID. Ningún endpoint
    se lo daba: /api/victimas/buscar/ no expone el id y /api/victimas/{id}/ pide
    `puede_caracterizar`, que el SUPERVISOR no tiene.
    """
    r = escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': '1115724047'})

    assert r.status_code == 200
    assert r.data['total'] == 1
    fila = r.data['resultados'][0]
    assert fila['id'] == str(escenario['victima'].id)
    assert fila['requiere_excepcion'] is True
    assert fila['habilitacion_vigente'] is None


def test_buscar_avisa_de_los_documentos_que_no_estan(escenario):
    """
    "No lo encontré" es justo lo que quien autoriza necesita saber para no dar
    por cubierta a una persona del oficio que no está en el padrón.
    """
    r = escenario['coordinador'].post(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'documentos': ['1115724047', '9999999999']},
        format='json')

    assert r.status_code == 200
    assert r.data['total'] == 1
    assert r.data['sin_coincidencia'] == ['9999999999']


def test_buscar_encuentra_a_quien_esta_cargado_SIN_tipo_de_documento(escenario):
    """
    1.126.615 víctimas (14,5 % del padrón) están cargadas sin tipo de documento,
    y su hash de identidad se calculó con el tipo vacío. Buscarlas por «CC +
    número» no las encuentra.

    Esta pantalla respondía «sin coincidencia» sobre personas que SÍ están en el
    padrón, y quien autoriza no tenía forma de saber que el sistema le estaba
    mintiendo: daba por no cubierta a alguien del oficio. La búsqueda de la APK
    ya tenía este respaldo desde el 2-ago; acá faltaba.
    """
    import datetime
    from apps.victimas.models import Victima

    sin_tipo = Victima.objects.create(
        tipo_documento=None, numero_documento='7694421',
        primer_nombre='SIN', primer_apellido='TIPO',
        genero='F', estado_ruv='INCLUIDO',
        habilitado_para_caracterizacion=False,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
    )

    r = escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': '7694421'})

    assert r.status_code == 200
    assert r.data['total'] == 1, 'la persona está en el padrón y no se encontró'
    assert r.data['sin_coincidencia'] == []
    fila = r.data['resultados'][0]
    assert fila['id'] == str(sin_tipo.id)
    # Y se avisa: coincide por número, pero el tipo registrado no es el buscado.
    assert fila['coincide_solo_por_numero'] is True


def test_buscar_no_marca_por_numero_a_quien_si_coincide_por_tipo(escenario):
    """El aviso tiene que distinguir. Si el tipo coincide, no hay nada que verificar."""
    r = escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': '1115724047'})

    assert r.status_code == 200
    assert r.data['resultados'][0]['coincide_solo_por_numero'] is False


def test_buscar_marca_a_quien_ya_tiene_habilitacion(escenario):
    """Sin esto, la pantalla ofreceria autorizar de nuevo y el POST daria 409."""
    escenario['coordinador'].post(URL, _payload(escenario['victima']), format='json')

    r = escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': '1115724047'})

    fila = r.data['resultados'][0]
    assert fila['habilitacion_vigente']['radicado'] == 'T-2026-451'


def test_el_encuestador_no_puede_ni_buscar_aca(escenario):
    r = escenario['encuestador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': '1115724047'})
    assert r.status_code == 403


def test_autorizar_en_lote_sobre_varias_personas(escenario, otra_victima):
    r = escenario['coordinador'].post(
        f'{URL}lote/',
        {'victima_ids': [str(escenario['victima'].id), str(otra_victima.id)],
         'ruta': 'ACCIONES_CONSTITUCIONALES',
         'radicado': 'T-2026-451',
         'observacion': 'Fallo de tutela que ampara al hogar completo.'},
        format='json')

    assert r.status_code == 201, r.data
    assert r.data['total_autorizadas'] == 2
    assert r.data['total_omitidas'] == 0


def test_el_lote_no_es_todo_o_nada(escenario, otra_victima):
    """
    Si una persona del oficio ya tenía habilitación, esa se salta y las demás se
    autorizan igual. Todo-o-nada obligaría a depurar la lista a mano hasta que
    pase entera, con la tutela vencida esperando.
    """
    escenario['coordinador'].post(URL, _payload(escenario['victima']), format='json')

    r = escenario['coordinador'].post(
        f'{URL}lote/',
        {'victima_ids': [str(escenario['victima'].id), str(otra_victima.id)],
         'ruta': 'ESPECIAL', 'radicado': 'T-2026-999',
         'observacion': 'Auto de seguimiento sobre el mismo hogar.'},
        format='json')

    assert r.status_code == 201
    assert r.data['total_autorizadas'] == 1
    assert r.data['total_omitidas'] == 1
    assert r.data['omitidas'][0]['motivo'] == 'YA_HABILITADA'


def test_si_no_se_autorizo_ninguna_no_responde_201(escenario):
    """
    Un 201 con cero creadas le diria a quien autoriza que quedo hecho cuando no
    se hizo nada.
    """
    escenario['coordinador'].post(URL, _payload(escenario['victima']), format='json')

    r = escenario['coordinador'].post(
        f'{URL}lote/',
        {'victima_ids': [str(escenario['victima'].id)],
         'ruta': 'ESPECIAL', 'radicado': 'T-2026-999',
         'observacion': 'Auto de seguimiento sobre el mismo hogar.'},
        format='json')

    assert r.status_code == 409
    assert r.data['total_autorizadas'] == 0


def test_el_lote_exige_lo_mismo_que_la_individual(escenario, otra_victima):
    """Hereda el serializer para que las reglas no se escriban dos veces."""
    r = escenario['coordinador'].post(
        f'{URL}lote/',
        {'victima_ids': [str(otra_victima.id)], 'ruta': 'ESPECIAL',
         'radicado': '', 'observacion': 'corto'},
        format='json')

    assert r.status_code == 400
    assert 'radicado' in r.data


def test_el_encuestador_no_puede_autorizar_en_lote(escenario, otra_victima):
    r = escenario['encuestador'].post(
        f'{URL}lote/',
        {'victima_ids': [str(otra_victima.id)], 'ruta': 'ESPECIAL',
         'radicado': 'T-1', 'observacion': 'Fallo de tutela del hogar.'},
        format='json')
    assert r.status_code == 403


@pytest.mark.parametrize('url', ['/autorizaciones/', '/api/autorizaciones/'])
def test_el_backend_ya_no_sirve_la_pantalla(escenario, url):
    """
    La pantalla se movió al panel web: fuera de él se veía como otra aplicación,
    sin header, menú ni footer.

    Que el backend NO responda en estas rutas es parte del arreglo, no un
    descuido. Si volviera a atenderlas, en producción se las quitaría al
    `location /` de nginx —el que entrega la SPA— y la página del panel dejaría
    de ser alcanzable.
    """
    r = escenario['coordinador'].get(url)
    assert r.status_code == 404


def test_al_finalizar_la_encuesta_la_habilitacion_se_consume(escenario):
    """
    De un solo uso. Si quedara vigente, esa persona tendría permiso permanente
    para saltarse la regla de los dos años.
    """
    import datetime

    from apps.encuestas.models import ExcepcionVigencia, SesionEncuesta
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar
    from apps.parametricas.models import Departamento, Municipio

    escenario['coordinador'].post(URL, _payload(escenario['victima']), format='json')

    depto = Departamento.objects.create(codigo_dane='08', nombre='Atlántico')
    muni = Municipio.objects.create(codigo_dane='08001', nombre='Barranquilla',
                                    departamento=depto)
    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL_C', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))
    hogar = Hogar.objects.create(autorizado=escenario['victima'], municipio=muni)
    # Con encuestador: el ViewSet le muestra al perfil de campo solo sus propias
    # sesiones, así que sin esto la finalización responde 404.
    sesion = SesionEncuesta.objects.create(
        hogar=hogar, instrumento=instrumento, estado='INICIADA',
        encuestador=escenario['usuario_encuestador'])

    r = escenario['encuestador'].post(f'/api/encuestas/{sesion.id}/finalizar/',
                                      {}, format='json')
    assert r.status_code in (200, 201), r.data

    habilitacion = ExcepcionVigencia.objects.get(victima=escenario['victima'])
    assert habilitacion.estado == ExcepcionVigencia.USADA
    assert habilitacion.usada_en_sesion_id == sesion.id

# ── Quien está en el corte del RUV pero no tiene ficha en el padrón ──────────
#
# El caso que destapó Javier el 21-ago: buscó un documento para autorizar una
# recaracterización y la pantalla respondió «sin coincidencia en el padrón». La
# persona SÍ se había caracterizado —el corte trae la fecha— pero no tenía fila
# en `Victima`, y `ExcepcionVigencia.victima` es una FK con PROTECT: no había
# dónde colgar la habilitación.
#
# Decisión de Javier: se muestra marcada, y la ficha se crea al AUTORIZAR, no al
# buscar. Con `estado_ruv='INCLUIDO'`, porque el universo ES el corte oficial
# del RUV: estar ahí es estar incluida.


@pytest.fixture
def en_el_universo(db):
    """Una víctima que está en el corte del RUV y no en el padrón operativo."""
    import datetime
    from apps.victimas.models import PersonaUniverso
    from apps.victimas.repository.base import doc_hash, num_hash

    return PersonaUniverso.objects.create(
        cons_persona_universo=23664117,
        tipo_documento='CC', numero_documento='1140164081',
        numero_documento_hash=doc_hash('CC', '1140164081'),
        numero_documento_hash_sin_tipo=num_hash('1140164081'),
        primer_nombre='MAILY', primer_apellido='LIZARAZO',
        segundo_apellido='GELVES',
        genero='Mujer', pertenencia_etnica='Negro(a) o Afrocolombiano(a)',
        discapacidad=False, ciclo_vital='entre 29 y 59', num_hechos=1,
        corte='TEMP_UNIV_TEST', fecha_corte=datetime.date(2026, 7, 1),
        es_preferida=True,
        fecha_nacimiento=datetime.date(1986, 12, 10),
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 7, 28, 19, 14, tzinfo=datetime.timezone.utc),
    )


def test_buscar_encuentra_a_quien_solo_esta_en_el_corte_del_RUV(escenario, en_el_universo):
    """Antes decía «sin coincidencia» y coordinación la daba por no cubierta."""
    r = escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': '1140164081'})

    assert r.status_code == 200
    assert r.data['sin_coincidencia'] == []
    assert r.data['total'] == 1
    fila = r.data['resultados'][0]
    assert fila['origen'] == 'UNIVERSO'
    assert fila['id'] is None                       # todavía no hay ficha
    assert fila['universo_id'] == str(en_el_universo.id)
    assert fila['requiere_excepcion'] is True
    assert 'no tiene ficha' in fila['mensaje']


def test_buscar_colapsa_el_documento_repetido_de_la_misma_persona(escenario):
    """
    H-025 — buscar un documento que en el padron tiene DOS filas de la MISMA
    persona devolvia dos filas casi identicas, y el panel mostraba una fila
    duplicada. En el padron real hay 768.096 documentos repetidos y el 92% es la
    misma persona cargada dos veces por el Oracle de origen. Se colapsan a una,
    con el mismo criterio de la busqueda de victimas (ColisionDocumento).
    """
    import datetime
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima, ColisionDocumento
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.get(codigo='CC')
    doc = '1006119380'
    h = doc_hash('CC', doc)
    comun = dict(
        tipo_documento=tipo, numero_documento=doc,
        numero_documento_hash=h, primer_nombre='CARLA', primer_apellido='DIAZ',
        genero='F', estado_ruv='INCLUIDO', habilitado_para_caracterizacion=False,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        fecha_nacimiento='1990-05-05',
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
    )
    v1 = Victima.objects.create(**comun)
    Victima.objects.create(**comun)   # misma persona, segunda fila del Oracle

    # El veredicto: una sola persona, y la preferida es la primera fila.
    ColisionDocumento.objects.create(
        doc_hash=h, clase='DUPLICADO_FUENTE', filas=2, personas=1,
        victima_preferida=v1)

    r = escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': doc})

    assert r.status_code == 200
    docs = [x for x in r.data['resultados'] if x['numero_documento'] == doc]
    assert len(docs) == 1, 'el documento repetido de la misma persona salio duplicado (H-025)'
    assert docs[0]['id'] == str(v1.id)   # la fila preferida


def test_buscar_mantiene_separadas_a_personas_distintas(escenario):
    """El reverso de H-025: si de verdad son personas distintas (el ~7%), se
    muestran las dos, porque ahi quien autoriza SI tiene que elegir."""
    import datetime
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima, ColisionDocumento
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.get(codigo='CC')
    doc = '1030283098'
    h = doc_hash('CC', doc)
    def fila(nombre, nac):
        return Victima.objects.create(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=h, primer_nombre=nombre, primer_apellido='X',
            genero='F', estado_ruv='INCLUIDO', habilitado_para_caracterizacion=False,
            pertenencia_etnica='NINGUNA', discapacidad=False, fecha_nacimiento=nac,
            fecha_ult_caracterizacion=datetime.datetime(
                2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc))
    fila('MARIA', '1980-01-01')
    fila('ROSA', '1995-09-09')
    # Ambiguo: personas distintas, sin preferida.
    ColisionDocumento.objects.create(
        doc_hash=h, clase='AMBIGUO', filas=2, personas=2, victima_preferida=None)

    r = escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': doc})

    assert r.status_code == 200
    docs = [x for x in r.data['resultados'] if x['numero_documento'] == doc]
    assert len(docs) == 2, 'personas distintas con el mismo documento deben verse ambas'


def test_buscar_universo_usa_el_indice_y_no_escanea_12M(escenario, en_el_universo):
    """
    H-024 — regresión de rendimiento. La búsqueda del universo filtraba por
    `numero_documento_hash`, que NO tiene índice en PersonaUniverso (12 M filas):
    un table scan de ~5,8 s medido en producción que, con el timeout de 15 s del
    cliente, hacía fallar la pantalla de forma intermitente («No se pudo buscar»).

    El resultado es el mismo con o sin índice, así que esto no se puede probar por
    comportamiento: se prueba sobre el SQL. La búsqueda del universo debe filtrar
    SOLO por `numero_documento_hash_sin_tipo` (indexado), nunca por el hash
    completo.
    """
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as ctx:
        escenario['coordinador'].get(
            '/api/habilitaciones/buscar/',
            {'tipo_documento': 'CC', 'numero_documento': '1140164081'})

    import re

    sql_universo = " ".join(
        q['sql'] for q in ctx.captured_queries
        if 'personauniverso' in q['sql'].lower())

    assert sql_universo, 'se esperaba al menos una consulta a PersonaUniverso'
    # Se mira el FILTRO (columna seguida de IN), no el SELECT: el nombre de la
    # columna aparece igual en la lista de columnas del SELECT. El campo sin
    # indice NO debe usarse como filtro; el indexado SI.
    filtra_sin_indice = re.search(r'numero_documento_hash"\s+IN', sql_universo)
    filtra_indexado = re.search(r'numero_documento_hash_sin_tipo"\s+IN', sql_universo)
    assert not filtra_sin_indice, 'la busqueda del universo escanea el campo SIN indice (H-024)'
    assert filtra_indexado, 'la busqueda del universo debe filtrar por el campo indexado'


def test_buscar_dos_del_universo_no_cuelga_ni_duplica(escenario, en_el_universo, otra_victima):
    """Dos documentos sin ficha pero en el universo: aparecen los que estén, sin
    duplicar y sin quedar en «sin coincidencia» los encontrados."""
    r = escenario['coordinador'].post(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'documentos': ['1140164081', '9999999999']},
        format='json')

    assert r.status_code == 200
    delu = [x for x in r.data['resultados'] if x['origen'] == 'UNIVERSO']
    ids = [x['universo_id'] for x in delu]
    assert len(ids) == len(set(ids)), 'una persona del universo salió duplicada'
    assert '9999999999' in r.data['sin_coincidencia']


def test_buscar_NO_crea_la_ficha(escenario, en_el_universo):
    """
    Coordinación pega 200 documentos de un oficio para ver la situación de cada
    uno. Eso no puede dejar 200 fichas nuevas en el padrón.
    """
    from apps.victimas.models import Victima

    antes = Victima.objects.count()
    escenario['coordinador'].get(
        '/api/habilitaciones/buscar/',
        {'tipo_documento': 'CC', 'numero_documento': '1140164081'})

    assert Victima.objects.count() == antes


def test_autorizar_a_quien_viene_del_universo_le_crea_la_ficha(escenario, en_el_universo):
    """El momento en que alguien decidió algo sobre ella es el que crea la ficha."""
    from apps.victimas.models import PersonaUniverso, Victima

    r = escenario['coordinador'].post('/api/habilitaciones/', {
        'universo_id': str(en_el_universo.id),
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-0001',
        'observacion': 'Fallo de tutela que ordena actualizar la caracterización.',
    }, format='json')

    assert r.status_code == 201, r.content

    victima = Victima.objects.get(numero_documento_hash=en_el_universo.numero_documento_hash)
    # El universo ES el corte del RUV: estar ahí es estar incluida.
    assert victima.estado_ruv == 'INCLUIDO'
    assert victima.fuente_origen == 'RUV'
    # Los datos salen del corte, no los teclea nadie.
    assert victima.primer_nombre == 'MAILY'
    assert victima.genero == 'F'                    # 'Mujer' del universo
    assert str(victima.fecha_nacimiento) == '1986-12-10'
    # Y queda enlazada, para no volver a crearla.
    assert PersonaUniverso.objects.get(pk=en_el_universo.pk).victima_id == victima.id


def test_autorizar_dos_veces_no_duplica_la_ficha(escenario, en_el_universo):
    """
    La segunda autorización debe chocar contra «ya tiene una habilitación
    vigente», no crear una segunda ficha de la misma persona.
    """
    from apps.victimas.models import Victima

    datos = {
        'universo_id': str(en_el_universo.id),
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-0001',
        'observacion': 'Fallo de tutela que ordena actualizar la caracterización.',
    }
    r1 = escenario['coordinador'].post('/api/habilitaciones/', datos, format='json')
    assert r1.status_code == 201

    n = Victima.objects.count()
    r2 = escenario['coordinador'].post('/api/habilitaciones/', datos, format='json')

    assert r2.status_code == 409
    assert r2.data['motivo'] == 'YA_HABILITADA'
    assert Victima.objects.count() == n


def test_el_lote_tambien_acepta_gente_del_universo(escenario, en_el_universo):
    """Una tutela ampara a un hogar, y el hogar puede tener gente de las dos."""
    r = escenario['coordinador'].post('/api/habilitaciones/lote/', {
        'victima_ids': [str(escenario['victima'].id)],
        'universo_ids': [str(en_el_universo.id)],
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-0002',
        'observacion': 'Fallo que ampara al hogar completo.',
    }, format='json')

    assert r.status_code == 201, r.content
    assert r.data['total_autorizadas'] == 2
    assert r.data['total_omitidas'] == 0


def test_no_se_autoriza_sin_decir_a_quien(escenario):
    r = escenario['coordinador'].post('/api/habilitaciones/', {
        'ruta': 'ACCIONES_CONSTITUCIONALES', 'radicado': 'T-1',
        'observacion': 'Un motivo suficientemente largo.',
    }, format='json')
    assert r.status_code == 400
