"""
El hogar deja de ser propiedad de un encuestador cuando se retira la vigencia.

─── El bloqueo que este cambio evita ────────────────────────────────────────
Hay dos reglas independientes que frenan al encuestador, y hasta ahora la primera
tapaba a la segunda:

    1. ficha vigente        → «no se puede recaracterizar»
    2. un hogar activo       → «esta víctima ya tiene un hogar activo registrado
                                por otro encuestador. Solicita su reasignación»

Con la vigencia retirada y esto sin tocar, el encuestador avanzaría más lejos para
chocar igual, y esta vez contra un mensaje **sin salida**: no hay pantalla de
reasignación en ninguna parte. Habríamos sustituido un bloqueo que se entendía por
otro que no se entiende. La queja volvería en una semana, con razón.

─── Lo que se fija acá ──────────────────────────────────────────────────────
· El hogar existente se devuelve, sea de quien sea. Se acaba el 409.
· La propiedad NO se reasigna: `creado_por` sigue siendo del primero, porque
  quitárselo le borraría de «mis encuestas» un trabajo que sí hizo.
· El segundo encuestador puede abrirlo y agregarle integrantes.
· El listado NO se abre: son 2,5 millones de fichas con datos personales.
· Con el control activo (el default) nada de esto cambia.
"""
import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/hogares/'


@pytest.fixture
def escenario(db):
    """Una víctima con hogar ya conformado por OTRO encuestador."""
    from apps.autenticacion.models import Perfil, Usuario
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)

    def usuario(codigo):
        perfil = Perfil.objects.create(
            codigo=f'P_{codigo}', nombre=codigo, activo=True,
            puede_caracterizar=True, puede_buscar_rni=True)
        return Usuario.objects.create_user(
            codigo_usuario=codigo, password='SrniTest2026!', nombre_completo=codigo,
            email=f'{codigo}@srni.dev', perfil=perfil, activo=True)

    primero = usuario('ENCUNO')
    segundo = usuario('ENCDOS')

    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento='1030547250',
        numero_documento_hash=doc_hash('CC', '1030547250'),
        primer_nombre='MARIA', primer_apellido='PEREZ',
        genero='F', estado_ruv='INCLUIDO',
        habilitado_para_caracterizacion=False,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        municipio_residencia=muni,
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
    )
    otra = Victima.objects.create(
        tipo_documento=tipo, numero_documento='9990100001',
        numero_documento_hash=doc_hash('CC', '9990100001'),
        primer_nombre='ANA', primer_apellido='PEREZ',
        genero='F', estado_ruv='INCLUIDO',
        habilitado_para_caracterizacion=True,
        pertenencia_etnica='NINGUNA', discapacidad=False,
    )

    hogar = Hogar.objects.create(autorizado=victima, creado_por=primero,
                                 municipio=muni, estado='ACTIVO')
    MiembroHogar.objects.create(hogar=hogar, victima=victima, es_autorizado=True,
                                rol='MIEMBRO', estado_inclusion='INCLUIDO',
                                creado_por=primero)

    def cliente_de(u):
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    return {
        'hogar': hogar, 'victima': victima, 'otra': otra, 'municipio': muni,
        'primero': primero, 'segundo': segundo,
        'cli_primero': cliente_de(primero), 'cli_segundo': cliente_de(segundo),
    }


def _conformar(cliente, escenario):
    return cliente.post(URL, {
        'autorizado': str(escenario['victima'].id),
        'municipio': escenario['municipio'].pk,
        'numero_personas': 1,
    }, format='json')


# ── Con el control activo: el comportamiento histórico ───────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_el_hogar_ajeno_sigue_dando_409(escenario):
    """El default no cambia nada. Si esto falla, el cambio se filtró a producción."""
    r = _conformar(escenario['cli_segundo'], escenario)

    assert r.status_code == 409
    assert 'otro' in r.data['detail']


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_el_ajeno_no_puede_abrir_el_hogar(escenario):
    r = escenario['cli_segundo'].get(f"{URL}{escenario['hogar'].id}/")

    assert r.status_code == 404


# ── Con el control retirado ──────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_se_devuelve_el_hogar_existente_en_vez_de_409(escenario):
    r = _conformar(escenario['cli_segundo'], escenario)

    assert r.status_code == 200, r.data
    assert r.data['id'] == str(escenario['hogar'].id)


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_no_se_duplica_el_hogar(escenario):
    """
    Una familia, un hogar. Estrenar hogar en cada recaracterización volvería
    incontable cuántas familias hay, que es una de las cifras que la entidad tiene
    que poder dar.
    """
    from apps.hogares.models import Hogar

    _conformar(escenario['cli_segundo'], escenario)

    assert Hogar.objects.filter(autorizado=escenario['victima']).count() == 1


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_la_propiedad_del_hogar_no_se_reasigna(escenario):
    """
    `creado_por` sigue siendo del primero. Reasignarlo le borraría de «mis
    encuestas» un trabajo que sí hizo, y la autoría de cada caracterización vive
    en su sesión, no en el hogar.
    """
    from apps.hogares.models import Hogar

    _conformar(escenario['cli_segundo'], escenario)

    hogar = Hogar.objects.get(id=escenario['hogar'].id)
    assert hogar.creado_por_id == escenario['primero'].id


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_el_segundo_encuestador_puede_abrir_el_hogar(escenario):
    """
    Sin esto el flujo muere igual: `create` le entrega el id y el `GET` siguiente
    responde 404. Es el bloqueo sin explicación que el cambio vino a evitar.
    """
    r = escenario['cli_segundo'].get(f"{URL}{escenario['hogar'].id}/")

    assert r.status_code == 200, r.data


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_el_segundo_encuestador_puede_agregar_integrantes(escenario):
    """La conformación tiene que poder completarse, no solo empezar."""
    r = escenario['cli_segundo'].post(
        f"{URL}{escenario['hogar'].id}/agregar-miembro/",
        {'victima': str(escenario['otra'].id), 'parentesco': 'HIJO_A'},
        format='json')

    assert r.status_code in (200, 201), r.data


# ── Lo que sigue cerrado ─────────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_el_listado_no_se_abre(escenario):
    """
    Abrir el detalle por identificador conocido no es abrir el listado. El id se
    obtiene conformando el hogar de la persona que se tiene enfrente; el listado
    completo son 2,5 millones de fichas con datos personales de víctimas, y nadie
    necesita navegarlas para caracterizar a una.
    """
    r = escenario['cli_segundo'].get(URL)

    assert r.status_code == 200
    ids = [h['id'] for h in r.data.get('results', r.data)]
    assert str(escenario['hogar'].id) not in ids


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_el_hogar_trabajado_si_aparece_en_el_listado_del_autor(escenario):
    """
    Contracara del anterior: quien caracterizó sobre el hogar sí lo ve en su
    listado. Si no, no podría volver a su propia entrevista a corregir nada.
    """
    from apps.encuestas.models import SesionEncuesta
    from apps.formulario.models import Instrumento

    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))
    SesionEncuesta.objects.create(
        hogar=escenario['hogar'], instrumento=instrumento,
        encuestador=escenario['segundo'], estado='INICIADA')

    r = escenario['cli_segundo'].get(URL)

    ids = [h['id'] for h in r.data.get('results', r.data)]
    assert str(escenario['hogar'].id) in ids


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_un_hogar_archivado_no_se_reutiliza(escenario):
    """
    ARCHIVADO significa cambio definitivo de núcleo familiar: ahí sí se estrena
    hogar. Retirar la vigencia no toca esa regla, que es de otra cosa.
    """
    from apps.hogares.models import Hogar

    escenario['hogar'].estado = 'ARCHIVADO'
    escenario['hogar'].save(update_fields=['estado'])

    r = _conformar(escenario['cli_segundo'], escenario)

    assert r.status_code == 201, r.data
    assert Hogar.objects.filter(autorizado=escenario['victima']).count() == 2
