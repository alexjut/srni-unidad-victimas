"""
Retirar a un integrante del hogar: una novedad, no un borrado.

─── El callejón que esto cierra ─────────────────────────────────────────────
Entre una caracterización y la siguiente la familia cambia: alguien muere, alguien
se va. Hasta el 11-sep-2026 el sistema solo sabía **borrar** un integrante, y solo
antes de la primera caracterización completada — con razón, porque borrar a alguien
ya reportado altera un dato entregado.

El efecto era que al recaracterizar no había forma de decir que la persona ya no
pertenece al hogar. El único mensaje disponible mandaba a «solicitar el ajuste a su
coordinación», que no existe como proceso. Con el control de vigencia retirado la
recaracterización pasó a ser el caso corriente y eso se volvió una pared.

─── Las tres operaciones, que no son la misma ───────────────────────────────
· DELETE   «nunca debió existir»       → borra. Solo antes de reportar.
· PATCH    «el dato está mal»          → corrige. Siempre, y queda en auditoría.
· retirar  «ya no pertenece al hogar»  → novedad con fecha. Siempre. No borra.

Lo que estos tests protegen es que sigan siendo tres cosas distintas: fundirlas
otra vez es exactamente cómo se llegó al callejón.
"""
import datetime

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

MURIO_EL = '2026-03-15'


@pytest.fixture
def escenario(db):
    """Un hogar con autorizado y dos integrantes más, y una caracterización cerrada."""
    from apps.autenticacion.models import Perfil, Usuario
    from apps.encuestas.models import SesionEncuesta
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                   departamento=depto)

    def victima(doc, nombre):
        return Victima.objects.create(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=doc_hash('CC', doc),
            primer_nombre=nombre, primer_apellido='PEREZ',
            genero='F', estado_ruv='INCLUIDO',
            habilitado_para_caracterizacion=True,
            pertenencia_etnica='NINGUNA', discapacidad=False,
            municipio_residencia=muni,
        )

    perfil = Perfil.objects.create(codigo='ENC_RM', nombre='Encuestador',
                                   activo=True, puede_caracterizar=True,
                                   puede_buscar_rni=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario='RMTEST', password='SrniTest2026!', nombre_completo='RM Test',
        email='rm@srni.dev', perfil=perfil, activo=True)

    autorizada = victima('1030547250', 'MARIA')
    abuela = victima('9990100001', 'ROSA')
    hija = victima('9990100002', 'ANA')

    hogar = Hogar.objects.create(autorizado=autorizada, creado_por=usuario,
                                 municipio=muni, estado='ACTIVO')
    m_aut = MiembroHogar.objects.create(
        hogar=hogar, victima=autorizada, es_autorizado=True, rol='MIEMBRO',
        estado_inclusion='INCLUIDO', creado_por=usuario)
    m_abuela = MiembroHogar.objects.create(
        hogar=hogar, victima=abuela, parentesco='PADRE_MADRE', rol='MIEMBRO',
        estado_inclusion='INCLUIDO', creado_por=usuario)
    m_hija = MiembroHogar.objects.create(
        hogar=hogar, victima=hija, parentesco='HIJO_A', rol='MIEMBRO',
        estado_inclusion='INCLUIDO', creado_por=usuario)

    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))

    cliente = APIClient()
    cliente.force_authenticate(user=usuario)

    return {
        'cliente': cliente, 'hogar': hogar, 'usuario': usuario,
        'instrumento': instrumento,
        'm_aut': m_aut, 'm_abuela': m_abuela, 'm_hija': m_hija,
        'cerrar_caracterizacion': lambda: SesionEncuesta.objects.create(
            hogar=hogar, instrumento=instrumento, encuestador=usuario,
            estado='COMPLETADA'),
    }


def _url(escenario, miembro, accion='retirar'):
    return f"/api/hogares/{escenario['hogar'].id}/miembros/{miembro.id}/{accion}/"


def _retirar(escenario, miembro, **extra):
    cuerpo = {'motivo': 'FALLECIMIENTO', 'fecha': MURIO_EL}
    cuerpo.update(extra)
    return escenario['cliente'].post(_url(escenario, miembro), cuerpo, format='json')


# ── Lo esencial: funciona DESPUÉS de reportar ────────────────────────────────

def test_se_puede_retirar_aunque_haya_caracterizacion_completada(escenario):
    """
    El caso para el que existe. Si esto falla, seguimos en el callejón: la familia
    cambió, el encuestador está enfrente y no tiene nada que hacer.
    """
    escenario['cerrar_caracterizacion']()

    r = _retirar(escenario, escenario['m_abuela'])

    assert r.status_code == 200, r.data
    assert r.data['retirado_en'] == MURIO_EL


def test_el_retiro_no_borra_la_fila(escenario):
    """
    La fila tiene que quedarse: las respuestas de la caracterización anterior
    apuntan a ella. Borrarla dejaría esa entrevista hablando de un integrante que
    el sistema ya no conoce.
    """
    from apps.hogares.models import MiembroHogar

    escenario['cerrar_caracterizacion']()
    _retirar(escenario, escenario['m_abuela'])

    assert MiembroHogar.objects.filter(id=escenario['m_abuela'].id).exists()
    assert MiembroHogar.objects.filter(hogar=escenario['hogar']).count() == 3


def test_el_retiro_guarda_quien_cuando_y_por_que(escenario):
    from apps.hogares.models import MiembroHogar

    _retirar(escenario, escenario['m_abuela'], motivo='NO_CONVIVE',
             observacion='Se fue a vivir con su hermana')

    m = MiembroHogar.objects.get(id=escenario['m_abuela'].id)
    assert m.motivo_retiro == 'NO_CONVIVE'
    assert m.observacion_retiro == 'Se fue a vivir con su hermana'
    assert m.retirado_por_id == escenario['usuario'].id
    # Las dos fechas son distintas cosas: el hecho es de marzo, el registro de hoy.
    assert str(m.retirado_en) == MURIO_EL
    assert m.retirado_at is not None
    assert m.retirado_at.date() != m.retirado_en


def test_los_demas_integrantes_no_se_tocan(escenario):
    from apps.hogares.models import MiembroHogar

    _retirar(escenario, escenario['m_abuela'])

    assert MiembroHogar.objects.get(id=escenario['m_hija'].id).retirado_en is None
    assert MiembroHogar.objects.get(id=escenario['m_aut'].id).retirado_en is None


# ── La fecha del hecho, no la de hoy ─────────────────────────────────────────

def test_la_fecha_es_obligatoria(escenario):
    """
    Sin fecha no se puede saber si la persona pertenecía al hogar en la
    caracterización anterior, que es lo que mantiene válida esa entrevista.
    """
    r = escenario['cliente'].post(_url(escenario, escenario['m_abuela']),
                                  {'motivo': 'FALLECIMIENTO'}, format='json')

    assert r.status_code == 400
    assert 'fecha' in r.data


def test_el_motivo_es_obligatorio(escenario):
    r = escenario['cliente'].post(_url(escenario, escenario['m_abuela']),
                                  {'fecha': MURIO_EL}, format='json')

    assert r.status_code == 400
    assert 'motivo' in r.data


def test_no_se_acepta_una_fecha_futura(escenario):
    """Se registra un hecho que ya ocurrió, no uno que se espera."""
    from django.utils import timezone

    manana = timezone.localdate() + datetime.timedelta(days=1)

    r = _retirar(escenario, escenario['m_abuela'], fecha=str(manana))

    assert r.status_code == 400
    assert 'fecha' in r.data


def test_el_motivo_otro_exige_explicacion(escenario):
    """Es el motivo que más se va a usar, y solo dice algo con el detalle."""
    r = _retirar(escenario, escenario['m_abuela'], motivo='OTRO', observacion='  ')

    assert r.status_code == 400
    assert 'observacion' in r.data


def test_un_motivo_que_no_existe_se_rechaza(escenario):
    r = _retirar(escenario, escenario['m_abuela'], motivo='SE_ABURRIO')

    assert r.status_code == 400


# ── Quién no se puede retirar ────────────────────────────────────────────────

def test_no_se_puede_retirar_al_autorizado(escenario):
    """
    Es el titular del hogar. Retirarlo dejaría un hogar sin dueño; para ese caso
    existe cambiar-autorizado, y el mensaje tiene que decirlo.
    """
    r = _retirar(escenario, escenario['m_aut'])

    assert r.status_code == 409
    assert 'autorizado' in r.data['detail'].lower()


# ── Idempotencia ─────────────────────────────────────────────────────────────

def test_retirar_dos_veces_no_pisa_la_fecha_original(escenario):
    """
    La app reintenta cuando la red se corta, así que el segundo intento llega. La
    fecha que vale es la del primer registro; la segunda podría venir de un
    encuestador que tecleó distinto.
    """
    from apps.hogares.models import MiembroHogar

    _retirar(escenario, escenario['m_abuela'])
    r = _retirar(escenario, escenario['m_abuela'], fecha='2026-01-01',
                 motivo='NO_CONVIVE')

    assert r.status_code == 200
    m = MiembroHogar.objects.get(id=escenario['m_abuela'].id)
    assert str(m.retirado_en) == MURIO_EL
    assert m.motivo_retiro == 'FALLECIMIENTO'


# ── Deshacer ─────────────────────────────────────────────────────────────────

def test_se_puede_deshacer_un_retiro_registrado_por_error(escenario):
    """
    El encuestador se equivoca de fila. Sin esto, la única salida sería pedir un
    ajuste a soporte, que es el callejón que este trabajo vino a cerrar.
    """
    from apps.hogares.models import MiembroHogar

    _retirar(escenario, escenario['m_abuela'])

    r = escenario['cliente'].post(
        _url(escenario, escenario['m_abuela'], 'reincorporar'), {}, format='json')

    assert r.status_code == 200
    m = MiembroHogar.objects.get(id=escenario['m_abuela'].id)
    assert m.retirado_en is None
    # Se limpian los cinco: dejar el motivo haría creer, meses después, que la
    # persona se fue y volvió.
    assert m.motivo_retiro == ''
    assert m.observacion_retiro == ''
    assert m.retirado_por_id is None
    assert m.retirado_at is None


def test_deshacer_sobre_alguien_que_no_estaba_retirado_no_falla(escenario):
    r = escenario['cliente'].post(
        _url(escenario, escenario['m_hija'], 'reincorporar'), {}, format='json')

    assert r.status_code == 200


# ── Las tres operaciones siguen siendo distintas ─────────────────────────────

def test_borrar_sigue_bloqueado_tras_una_caracterizacion_completada(escenario):
    """
    Borrar a alguien ya reportado alteraría un dato entregado, y eso sigue
    prohibido. El mensaje ahora tiene que ofrecer la salida correcta.
    """
    escenario['cerrar_caracterizacion']()

    r = escenario['cliente'].delete(
        f"/api/hogares/{escenario['hogar'].id}/miembros/{escenario['m_abuela'].id}/")

    assert r.status_code == 409
    assert 'retirar' in r.data['detail'].lower()


def test_borrar_sigue_funcionando_antes_de_reportar(escenario):
    """El caso «nunca debió existir» no se toca: es un error de captura."""
    from apps.hogares.models import MiembroHogar

    r = escenario['cliente'].delete(
        f"/api/hogares/{escenario['hogar'].id}/miembros/{escenario['m_hija'].id}/")

    assert r.status_code == 204
    assert not MiembroHogar.objects.filter(id=escenario['m_hija'].id).exists()


def test_corregir_ahora_si_se_permite_tras_una_caracterizacion_completada(escenario):
    """
    Antes también estaba bloqueado, y el efecto era que un apellido mal escrito
    quedaba adentro para siempre: el único camino ofrecido no existía como proceso.
    Corregir un dato no es lo mismo que borrar a una persona.
    """
    from apps.hogares.models import MiembroHogar

    escenario['cerrar_caracterizacion']()

    r = escenario['cliente'].patch(
        f"/api/hogares/{escenario['hogar'].id}/miembros/{escenario['m_abuela'].id}/",
        {'parentesco': 'OTRO_PARIENTE'}, format='json')

    assert r.status_code == 200, r.data
    assert MiembroHogar.objects.get(
        id=escenario['m_abuela'].id).parentesco == 'OTRO_PARIENTE'


# ── El modelo: quién pertenecía al hogar en qué momento ─────────────────────

def test_pertenencia_al_momento_de_cada_caracterizacion(escenario):
    """
    Es lo que permite que la entrevista anterior siga siendo válida y la nueva no
    pregunte por quien ya se fue. Sin esta distinción habría que elegir entre
    falsear la anterior o interrogar al encuestador sobre alguien que no está.
    """
    from apps.hogares.models import MiembroHogar

    _retirar(escenario, escenario['m_abuela'])  # se fue el 15-mar-2026
    m = MiembroHogar.objects.get(id=escenario['m_abuela'].id)

    assert m.pertenecia_al(datetime.date(2026, 1, 10)) is True    # antes: sí
    assert m.pertenecia_al(datetime.date(2026, 3, 15)) is False   # ese día: ya no
    assert m.pertenecia_al(datetime.date(2026, 9, 11)) is False   # después: no
    assert m.esta_retirado is True


def test_quien_no_esta_retirado_pertenece_siempre(escenario):
    assert escenario['m_hija'].pertenecia_al(datetime.date(1990, 1, 1)) is True
    assert escenario['m_hija'].esta_retirado is False


# ── Lo que ve el cliente ─────────────────────────────────────────────────────

def test_el_listado_de_miembros_entrega_el_retiro(escenario):
    """
    La APK decide con esto a quién le pregunta en la entrevista. Sin el campo, un
    integrante retirado seguiría sumando obligatorias y el avance **nunca llegaría
    al 100 %**, sin ninguna pregunta pendiente visible para desatascarlo.
    """
    _retirar(escenario, escenario['m_abuela'], motivo='FALLECIMIENTO')

    r = escenario['cliente'].get(f"/api/hogares/{escenario['hogar'].id}/miembros/")
    assert r.status_code == 200

    por_id = {m['id']: m for m in r.data}
    retirada = por_id[str(escenario['m_abuela'].id)]
    assert retirada['retirado_en'] == MURIO_EL
    assert retirada['motivo_retiro'] == 'FALLECIMIENTO'
    assert retirada['motivo_retiro_display'] == 'Falleció'
    assert por_id[str(escenario['m_hija'].id)]['retirado_en'] is None


def test_el_detalle_del_hogar_entrega_el_retiro(escenario):
    """Es la vía por la que el móvil arma el formulario de la entrevista."""
    _retirar(escenario, escenario['m_abuela'])

    r = escenario['cliente'].get(f"/api/hogares/{escenario['hogar'].id}/")

    por_id = {m['id']: m for m in r.data['miembros']}
    assert por_id[str(escenario['m_abuela'].id)]['retirado_en'] == MURIO_EL


def test_el_retiro_no_se_puede_escribir_por_la_puerta_de_atras(escenario):
    """
    Solo por su acción, que exige motivo y fecha y deja quién lo registró. Un PATCH
    que pudiera poner `retirado_en` a mano dejaría retiros sin justificación, que
    es justo lo que el registro existe para evitar.
    """
    from apps.hogares.models import MiembroHogar

    r = escenario['cliente'].patch(
        f"/api/hogares/{escenario['hogar'].id}/miembros/{escenario['m_hija'].id}/",
        {'retirado_en': MURIO_EL}, format='json')

    assert r.status_code == 200            # el campo se ignora, no rompe la petición
    assert MiembroHogar.objects.get(id=escenario['m_hija'].id).retirado_en is None
