"""
El libro de las recaracterizaciones sobre ficha vigente.

Con el control de vigencia retirado (`VIGENCIA['BLOQUEO_ACTIVO'] = False`), quien
tiene ficha vigente se caracteriza sin autorización, sin radicado y sin soporte.
Lo que no se pierde es el dato: al cerrar la encuesta queda una fila con quién,
cuándo, sobre quién y con cuánta anticipación.

─── El error que estos tests existen para atrapar ───────────────────────────
`finalizar` hace dos cosas en el mismo bloque, y el orden importa:

    1. registrar la recaracterización  ← lee la fecha ANTERIOR
    2. marcar a las personas como caracterizadas  ← la SOBREESCRIBE

Si alguien las invierte —y es el cambio más natural del mundo, porque el registro
"parece" que va después— el libro se sigue llenando, nada falla, y todas las filas
dicen que a la persona le faltaban cero días por vencer. El registro existiría y
no serviría para nada. `test_el_registro_guarda_la_fecha_anterior...` es el que se
cae si eso pasa.
"""
import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

#: Caracterizada hace poco: al 11-sep-2026 le faltan dos años y medio por vencer.
CARACTERIZADA_EL = datetime.datetime(2026, 3, 14, 10, 0,
                                     tzinfo=datetime.timezone.utc)
VIGENTE_HASTA = datetime.date(2028, 3, 14)


@pytest.fixture
def escenario(db):
    """
    Un hogar con dos personas: el autorizado **con ficha vigente** y un miembro
    nunca caracterizado.

    Los dos en el mismo hogar a propósito: el registro tiene que anotar al primero
    y dejar al segundo fuera. Un libro que anote a todo el mundo tendría millones
    de filas y ninguna diría nada.
    """
    from apps.autenticacion.models import Perfil, Usuario
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)

    def victima(doc, nombre, *, fecha_ult=None):
        return Victima.objects.create(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=doc_hash('CC', doc),
            primer_nombre=nombre, primer_apellido='PEREZ',
            genero='F', estado_ruv='INCLUIDO',
            # Con ficha vigente, `habilitado` va en False: es lo que hace que
            # `describir_elegibilidad` llegue a evaluar la regla de los dos años.
            habilitado_para_caracterizacion=fecha_ult is None,
            pertenencia_etnica='NINGUNA', discapacidad=False,
            municipio_residencia=muni,
            fecha_ult_caracterizacion=fecha_ult,
        )

    con_ficha_vigente = victima('1030547250', 'MARIA', fecha_ult=CARACTERIZADA_EL)
    nunca_caracterizado = victima('9990100001', 'ANA')

    perfil = Perfil.objects.create(codigo='ENC_RV', nombre='Encuestador',
                                   puede_caracterizar=True, puede_buscar_rni=True,
                                   activo=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario='RVTEST', password='SrniTest2026!',
        nombre_completo='RV Test', email='rv@srni.dev', perfil=perfil, activo=True)

    hogar = Hogar.objects.create(autorizado=con_ficha_vigente, creado_por=usuario,
                                 municipio=muni)
    MiembroHogar.objects.create(hogar=hogar, victima=nunca_caracterizado)

    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))

    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return {'cliente': cliente, 'hogar': hogar, 'instrumento': instrumento,
            'con_ficha_vigente': con_ficha_vigente,
            'nunca_caracterizado': nunca_caracterizado, 'usuario': usuario}


def _sesion(escenario, ruta='GENERAL'):
    from apps.encuestas.models import SesionEncuesta

    return SesionEncuesta.objects.create(
        hogar=escenario['hogar'], instrumento=escenario['instrumento'],
        encuestador=escenario['usuario'], estado='INICIADA',
        ruta_entrevista=ruta)


def _finalizar(escenario, sesion):
    r = escenario['cliente'].post(f'/api/encuestas/{sesion.id}/finalizar/',
                                  {}, format='json')
    assert r.status_code in (200, 201), r.data
    return r


# ── Con el control activo: el libro no se usa ────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_no_se_registra_nada(escenario):
    """
    Mientras la regla esté en pie, una recaracterización pasa por una habilitación
    otorgada y esa queda en `ExcepcionVigencia`, que es otro libro. Este tiene que
    quedar vacío: dos registros del mismo hecho volverían incontable el informe.
    """
    from apps.encuestas.models import RecaracterizacionVigente

    _finalizar(escenario, _sesion(escenario))

    assert RecaracterizacionVigente.objects.count() == 0


# ── Con el control retirado: el libro se llena solo ──────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_se_registra_solo_a_quien_tenia_ficha_vigente(escenario):
    from apps.encuestas.models import RecaracterizacionVigente

    _finalizar(escenario, _sesion(escenario))

    filas = list(RecaracterizacionVigente.objects.all())
    assert len(filas) == 1
    assert filas[0].victima_id == escenario['con_ficha_vigente'].id


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_el_registro_guarda_la_fecha_anterior_no_la_de_hoy(escenario):
    """
    El test que protege el orden dentro de `finalizar`.

    Si el registro corriera después de marcar las fechas, leería la
    caracterización que se acaba de hacer: `fecha_ult_caracterizacion` saldría
    igual a hoy y `dias_restantes` en cero o negativo, en todas las filas.
    """
    from apps.encuestas.models import RecaracterizacionVigente

    _finalizar(escenario, _sesion(escenario))

    fila = RecaracterizacionVigente.objects.get()
    assert fila.fecha_ult_caracterizacion == CARACTERIZADA_EL.date()
    assert fila.vigente_hasta == VIGENTE_HASTA
    # Le faltaba más de un año: es lo que distingue «la recaracterizaron a los 22
    # meses» de «a los tres días», y es el orden de gravedad del informe.
    assert fila.dias_restantes > 365


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_el_registro_dice_quien_cuando_y_por_donde(escenario):
    """Las tres preguntas que el libro existe para poder responder."""
    from apps.encuestas.models import RecaracterizacionVigente

    sesion = _sesion(escenario, ruta='MODIFICACION_NUCLEO_FAMILIAR')
    _finalizar(escenario, sesion)

    fila = RecaracterizacionVigente.objects.get()
    assert fila.realizada_por_id == escenario['usuario'].id
    assert fila.ruta == 'MODIFICACION_NUCLEO_FAMILIAR'
    assert fila.sesion_id == sesion.id
    assert fila.hogar_id == escenario['hogar'].id
    # La fecha del registro es la del cierre de la encuesta, no la del `INSERT`.
    sesion.refresh_from_db()
    assert fila.realizada_at == sesion.fecha_fin


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_la_persona_igual_queda_marcada_como_caracterizada(escenario):
    """
    Registrar no reemplaza a marcar. Las dos cosas pasan, y en ese orden: si
    marcar se hubiera perdido al meter el registro, la persona volvería a salir
    habilitada mañana con fecha vieja.
    """
    from apps.victimas.models import Victima

    _finalizar(escenario, _sesion(escenario))

    v = Victima.objects.get(id=escenario['con_ficha_vigente'].id)
    assert v.fecha_ult_caracterizacion.date() > CARACTERIZADA_EL.date()
    assert v.habilitado_para_caracterizacion is False


# ── Idempotencia ─────────────────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_cerrar_dos_veces_no_duplica_el_registro(escenario):
    """
    La app reintenta `finalizar` cuando la red se corta a mitad, así que el
    segundo cierre llega. El endpoint lo rechaza con 400 —ya está completada— y el
    libro tiene que seguir con una sola fila.

    La restricción `(sesion, victima)` es lo que lo garantiza sin condiciones en
    el código: si mañana alguien agrega otro camino que cierre encuestas, la base
    lo protege igual.
    """
    from apps.encuestas.models import RecaracterizacionVigente

    sesion = _sesion(escenario)
    _finalizar(escenario, sesion)

    r = escenario['cliente'].post(f'/api/encuestas/{sesion.id}/finalizar/',
                                  {}, format='json')
    assert r.status_code == 400

    assert RecaracterizacionVigente.objects.filter(sesion=sesion).count() == 1


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_registrar_es_idempotente_por_si_sola(escenario):
    """
    Llamada directa dos veces, sin pasar por el endpoint. Es el contrato del
    método: escribe o no escribe, pero nunca duplica ni revienta.
    """
    from apps.encuestas.models import RecaracterizacionVigente
    from apps.victimas.repository.base import describir_elegibilidad

    sesion = _sesion(escenario)
    victima = escenario['con_ficha_vigente']
    veredicto = describir_elegibilidad(victima, habilitacion=None)
    momento = datetime.datetime(2026, 9, 11, 15, 0, tzinfo=datetime.timezone.utc)

    primera = RecaracterizacionVigente.registrar(
        sesion=sesion, victima=victima, veredicto=veredicto,
        usuario=escenario['usuario'], momento=momento)
    segunda = RecaracterizacionVigente.registrar(
        sesion=sesion, victima=victima, veredicto=veredicto,
        usuario=escenario['usuario'], momento=momento)

    assert primera.id == segunda.id
    assert RecaracterizacionVigente.objects.count() == 1


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_no_registra_a_quien_no_tenia_ficha_vigente(escenario):
    """El caso corriente: el método decide, no quien lo llama."""
    from apps.encuestas.models import RecaracterizacionVigente
    from apps.victimas.repository.base import describir_elegibilidad

    victima = escenario['nunca_caracterizado']
    veredicto = describir_elegibilidad(victima, habilitacion=None)

    fila = RecaracterizacionVigente.registrar(
        sesion=_sesion(escenario), victima=victima, veredicto=veredicto,
        usuario=escenario['usuario'],
        momento=datetime.datetime(2026, 9, 11, tzinfo=datetime.timezone.utc))

    assert fila is None
    assert RecaracterizacionVigente.objects.count() == 0


# ── Lo que no puede romper ───────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_un_fallo_al_registrar_no_impide_cerrar_la_encuesta(escenario, monkeypatch):
    """
    La encuesta ya está capturada y cerrar es lo que el encuestador necesita. Un
    libro que no se pudo escribir se reconstruye desde la sesión; una entrevista
    que no se pudo cerrar se pierde en campo.
    """
    from apps.encuestas.models import RecaracterizacionVigente, SesionEncuesta

    def explota(**_):
        raise RuntimeError('la base dijo no')

    monkeypatch.setattr(RecaracterizacionVigente, 'registrar', staticmethod(explota))

    sesion = _sesion(escenario)
    _finalizar(escenario, sesion)

    assert SesionEncuesta.objects.get(id=sesion.id).estado == 'COMPLETADA'
