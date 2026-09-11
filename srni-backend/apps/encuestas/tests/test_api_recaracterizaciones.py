"""
`/api/recaracterizaciones/` — el punto de control del retiro de la vigencia.

─── Qué se protege ──────────────────────────────────────────────────────────
Con el bloqueo retirado, este endpoint es lo único que puede responder cuántas
recaracterizaciones se hicieron sobre ficha vigente, quién las hizo y con cuánta
anticipación. **Un registro que nadie consulta equivale a no tenerlo**, así que sin
esta consulta el trabajo anterior no sirve.

Dos propiedades fáciles de romper sin que nada falle:

1. **Es de supervisión, no de campo.** Un instrumento para mirar cómo opera el
   equipo en manos del equipo que se mira no supervisa nada.
2. **`dias_restantes` mide lo que FALTABA por vencer, así que el número más ALTO
   es la recaracterización más temprana** — la más grave. Es contraintuitivo y
   quien ordene o agregue al revés va a dejar fuera exactamente el caso que se
   busca, sin que ninguna prueba de humo lo note.
"""
import datetime

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/recaracterizaciones/'


@pytest.fixture
def escenario(db):
    """
    Tres personas, cinco recaracterizaciones y dos encuestadores.

    ROSA tiene tres —una de ellas a tres días de la anterior, el caso grave—, ANA
    tiene una y LUZ una. Así el agrupado por persona tiene algo que mostrar y el
    filtro por autor también.
    """
    from apps.autenticacion.models import Perfil, Usuario
    from apps.encuestas.models import RecaracterizacionVigente, SesionEncuesta
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    antioquia = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    medellin = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                        departamento=antioquia)
    narino = Departamento.objects.create(codigo_dane='52', nombre='Nariño')
    tumaco = Municipio.objects.create(codigo_dane='52835', nombre='Tumaco',
                                      departamento=narino)

    def usuario(codigo, **flags):
        perfil = Perfil.objects.create(codigo=f'P_{codigo}', nombre=codigo,
                                       activo=True, **flags)
        return Usuario.objects.create_user(
            codigo_usuario=codigo, password='SrniTest2026!', nombre_completo=codigo,
            email=f'{codigo}@srni.dev', perfil=perfil, activo=True)

    enc_uno = usuario('ENCUNO', puede_caracterizar=True, puede_buscar_rni=True)
    enc_dos = usuario('ENCDOS', puede_caracterizar=True, puede_buscar_rni=True)
    supervisor = usuario('SUPER', puede_ver_reportes=True, puede_buscar_rni=True)

    def victima(doc, nombre):
        return Victima.objects.create(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=doc_hash('CC', doc),
            primer_nombre=nombre, primer_apellido='PEREZ', genero='F',
            estado_ruv='INCLUIDO', pertenencia_etnica='NINGUNA',
            discapacidad=False)

    rosa, ana, luz = victima('9990100001', 'ROSA'), victima('9990100002', 'ANA'), \
        victima('9990100003', 'LUZ')

    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))

    # UN hogar por persona, y N sesiones dentro. Es el modelo real —el hogar es la
    # familia, no la entrevista— y la restriccion de la base lo exige: intentar un
    # hogar por recaracterizacion revienta contra
    # `uniq_hogar_no_archivado_por_autorizado`, que es justo lo que el disenio
    # quiere. Reproducirlo aca es lo que hace que la prueba mida el sistema real.
    hogares = {}

    def hogar_de(victima, autor, municipio):
        if victima.id not in hogares:
            hogares[victima.id] = Hogar.objects.create(
                autorizado=victima, creado_por=autor, municipio=municipio,
                estado='ACTIVO')
        return hogares[victima.id]

    def fila(victima, autor, municipio, dias, dia_del_mes, ruta='GENERAL'):
        hogar = hogar_de(victima, autor, municipio)
        sesion = SesionEncuesta.objects.create(
            hogar=hogar, instrumento=instrumento, encuestador=autor,
            estado='COMPLETADA', ruta_entrevista=ruta)
        return RecaracterizacionVigente.objects.create(
            sesion=sesion, victima=victima, hogar=hogar, realizada_por=autor,
            realizada_at=datetime.datetime(2026, 9, dia_del_mes, 10, 0,
                                           tzinfo=datetime.timezone.utc),
            ruta=ruta,
            fecha_ult_caracterizacion=datetime.date(2026, 3, 14),
            vigente_hasta=datetime.date(2028, 3, 14),
            dias_restantes=dias,
        )

    # ROSA: tres veces. La de 720 días es la grave — la ficha tenía 3 días de
    # hecha, porque le faltaban 720 de los 730 del periodo de dos años.
    fila(rosa, enc_uno, medellin, 500, 1)
    fila(rosa, enc_dos, medellin, 720, 3)
    fila(rosa, enc_uno, medellin, 300, 5)
    fila(ana, enc_uno, medellin, 200, 7, ruta='ACCIONES_CONSTITUCIONALES')
    fila(luz, enc_dos, tumaco, 100, 9)

    def cliente_de(u):
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    return {
        'supervisor': cliente_de(supervisor), 'encuestador': cliente_de(enc_uno),
        'rosa': rosa, 'ana': ana, 'luz': luz,
        'enc_uno': enc_uno, 'enc_dos': enc_dos,
    }


def _filas(respuesta):
    return respuesta.data.get('results', respuesta.data)


# ── Quién puede mirar el libro ───────────────────────────────────────────────

def test_el_encuestador_de_campo_no_puede_consultarlo(escenario):
    """
    Es un instrumento de supervisión. En manos del supervisado no supervisa nada,
    y además le diría al encuestador exactamente qué queda registrado de su
    trabajo, que no es el propósito.
    """
    r = escenario['encuestador'].get(URL)

    assert r.status_code == 403


def test_sin_autenticar_no_se_puede(escenario):
    assert APIClient().get(URL).status_code in (401, 403)


def test_el_supervisor_ve_el_libro_completo(escenario):
    r = escenario['supervisor'].get(URL)

    assert r.status_code == 200
    assert len(_filas(r)) == 5


# ── El listado ───────────────────────────────────────────────────────────────

def test_por_defecto_la_mas_reciente_primero(escenario):
    """Lo que un supervisor quiere ver al entrar: qué pasó ayer."""
    filas = _filas(escenario['supervisor'].get(URL))

    fechas = [f['realizada_at'] for f in filas]
    assert fechas == sorted(fechas, reverse=True)


def test_cada_fila_dice_quien_cuando_y_por_que_ruta(escenario):
    fila = _filas(escenario['supervisor'].get(URL))[0]

    assert fila['realizada_por_codigo'] in ('ENCUNO', 'ENCDOS')
    assert fila['ruta']
    assert fila['fecha_ult_caracterizacion'] == '2026-03-14'
    assert fila['vigente_hasta'] == '2028-03-14'
    assert fila['dias_restantes'] is not None


def test_cada_fila_trae_cuantas_veces_van_de_esa_persona(escenario):
    """
    El dato que permite ver, leyendo el listado corriente, que la fila que se está
    mirando es la tercera sobre la misma persona. Sin él hay que ir a otra pantalla
    a sospecharlo, y nadie va.
    """
    filas = _filas(escenario['supervisor'].get(URL))
    # `str()` sobre la clave: el campo de relación del serializer entrega un UUID,
    # no su texto, y comparar los dos tipos falla en silencio.
    por_persona = {str(f['victima']): f['veces_esta_persona'] for f in filas}

    assert por_persona[str(escenario['rosa'].id)] == 3
    assert por_persona[str(escenario['ana'].id)] == 1


def test_el_documento_viaja_hasheado_y_no_en_claro(escenario):
    """
    Para contar y agrupar el hash alcanza. Esta consulta la usa supervisión sobre
    volúmenes grandes, y exponer el documento de miles de víctimas en una pantalla
    de tablero es PII que nadie necesita para supervisar.
    """
    fila = _filas(escenario['supervisor'].get(URL))[0]

    assert fila['documento_hash']
    assert 'numero_documento' not in fila
    assert '999010' not in str(fila)


def test_es_solo_lectura(escenario):
    """
    Estas filas las escribe el sistema al cerrar una encuesta. Una que se pudiera
    editar desde el panel no serviría como constancia de nada.
    """
    r = escenario['supervisor'].post(URL, {}, format='json')

    assert r.status_code in (403, 405)


# ── Los filtros ──────────────────────────────────────────────────────────────

def test_filtra_por_encuestador(escenario):
    filas = _filas(escenario['supervisor'].get(URL, {'codigo_usuario': 'ENCDOS'}))

    assert len(filas) == 2
    assert all(f['realizada_por_codigo'] == 'ENCDOS' for f in filas)


def test_filtra_por_rango_de_fechas(escenario):
    filas = _filas(escenario['supervisor'].get(
        URL, {'fecha_desde': '2026-09-05', 'fecha_hasta': '2026-09-09'}))

    assert len(filas) == 3


def test_filtra_por_departamento(escenario):
    filas = _filas(escenario['supervisor'].get(URL, {'departamento': '52'}))

    assert len(filas) == 1
    assert filas[0]['departamento_nombre'] == 'Nariño'


def test_filtra_por_ruta(escenario):
    filas = _filas(escenario['supervisor'].get(
        URL, {'ruta': 'ACCIONES_CONSTITUCIONALES'}))

    assert len(filas) == 1


def test_filtra_las_hechas_con_mas_anticipacion(escenario):
    """
    `dias_restantes_min` alto = la ficha estaba más fresca = el caso más grave.
    Es el filtro que se va a usar de verdad: «muéstrame las peores».
    """
    filas = _filas(escenario['supervisor'].get(URL, {'dias_restantes_min': 600}))

    assert len(filas) == 1
    assert filas[0]['dias_restantes'] == 720


def test_ordena_por_gravedad(escenario):
    filas = _filas(escenario['supervisor'].get(URL, {'ordering': '-dias_restantes'}))

    assert filas[0]['dias_restantes'] == 720


# ── El resumen ───────────────────────────────────────────────────────────────

def test_el_resumen_cuenta_total_y_personas_distintas(escenario):
    r = escenario['supervisor'].get(f'{URL}resumen/')

    assert r.status_code == 200
    assert r.data['total'] == 5
    assert r.data['personas_distintas'] == 3
    # Mayor que 1 significa que hay personas recaracterizadas más de una vez.
    assert r.data['promedio_por_persona'] > 1


def test_el_resumen_dice_quien_hizo_cuantas(escenario):
    r = escenario['supervisor'].get(f'{URL}resumen/')

    por_autor = {f['codigo_usuario']: f['veces'] for f in r.data['por_autor']}
    assert por_autor['ENCUNO'] == 3
    assert por_autor['ENCDOS'] == 2


def test_el_resumen_agrupa_por_territorial(escenario):
    r = escenario['supervisor'].get(f'{URL}resumen/')

    por_depto = {f['departamento']: f['veces'] for f in r.data['por_territorial']}
    assert por_depto['Antioquia'] == 4
    assert por_depto['Nariño'] == 1


def test_el_resumen_separa_por_anticipacion(escenario):
    """
    Las franjas son el orden de gravedad. Un promedio mezclaría «a los tres días»
    con «a los 22 meses» hasta volver invisible el primero, que es justo el que hay
    que ver.
    """
    r = escenario['supervisor'].get(f'{URL}resumen/')

    ant = r.data['anticipacion']
    assert ant['hasta_7_dias'] == 1        # la de 720 días restantes
    assert ant['sin_dato'] == 0
    assert sum(ant.values()) == 5


def test_el_resumen_respeta_los_filtros(escenario):
    r = escenario['supervisor'].get(f'{URL}resumen/', {'codigo_usuario': 'ENCDOS'})

    assert r.data['total'] == 2


def test_el_resumen_no_revienta_sin_datos(escenario):
    """Un filtro que no cruza nada. La división por cero es el error obvio."""
    r = escenario['supervisor'].get(f'{URL}resumen/', {'fecha_desde': '2030-01-01'})

    assert r.status_code == 200
    assert r.data['total'] == 0
    assert r.data['promedio_por_persona'] == 0


def test_el_resumen_tambien_es_solo_de_supervision(escenario):
    assert escenario['encuestador'].get(f'{URL}resumen/').status_code == 403


# ── Cuántas veces por persona ────────────────────────────────────────────────

def test_personas_muestra_solo_las_recaracterizadas_mas_de_una_vez(escenario):
    """
    El umbral por defecto es 2 a propósito: con 1 la respuesta es el padrón entero
    de recaracterizados y no dice nada, porque toda persona del libro tiene al
    menos una. Lo que hay que mirar son las que tienen más.
    """
    r = escenario['supervisor'].get(f'{URL}personas/')

    assert r.status_code == 200
    filas = _filas(r)
    assert len(filas) == 1
    assert filas[0]['victima'] == str(escenario['rosa'].id)
    assert filas[0]['veces'] == 3


def test_personas_dice_cuantos_encuestadores_distintos(escenario):
    """
    Dos autores sobre la misma persona es la señal de que nadie se enteró de que
    el otro ya la había caracterizado — el efecto de rebote que el retiro del
    control deja sin vigilancia.
    """
    fila = _filas(escenario['supervisor'].get(f'{URL}personas/'))[0]

    assert fila['autores'] == 2


def test_personas_delata_la_recaracterizacion_mas_temprana(escenario):
    """
    ⚠️ El aserto que protege la dirección del número. `dias_restantes` cuenta lo
    que FALTABA por vencer, así que el MÁXIMO es la recaracterización más temprana
    y por tanto la más grave. Agregarlo con `Min` daría 300 acá —la más benigna de
    ROSA— y el caso que se busca quedaría escondido sin que nada falle.
    """
    fila = _filas(escenario['supervisor'].get(f'{URL}personas/'))[0]

    assert fila['menor_dias_restantes'] == 720


def test_personas_trae_la_primera_y_la_ultima(escenario):
    fila = _filas(escenario['supervisor'].get(f'{URL}personas/'))[0]

    assert fila['primera'] < fila['ultima']


def test_personas_con_umbral_en_uno_trae_a_todas(escenario):
    filas = _filas(escenario['supervisor'].get(f'{URL}personas/', {'veces_min': 1}))

    assert len(filas) == 3


def test_personas_ignora_un_umbral_absurdo_en_vez_de_reventar(escenario):
    """El panel manda lo que el usuario teclea; un texto no puede dar un 500."""
    r = escenario['supervisor'].get(f'{URL}personas/', {'veces_min': 'muchas'})

    assert r.status_code == 200


def test_personas_respeta_los_filtros(escenario):
    """Con un solo autor, ROSA ya no tiene tres sino dos, y sigue apareciendo."""
    filas = _filas(escenario['supervisor'].get(
        f'{URL}personas/', {'codigo_usuario': 'ENCUNO'}))

    assert len(filas) == 1
    assert filas[0]['veces'] == 2


def test_personas_tambien_es_solo_de_supervision(escenario):
    assert escenario['encuestador'].get(f'{URL}personas/').status_code == 403
