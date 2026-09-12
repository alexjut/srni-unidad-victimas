"""
Los límites por IP no contaban nada, y nadie lo notó.

─── Lo que se midió en producción el 12-sep-2026 ────────────────────────────
Ocho ingresos seguidos y sesenta peticiones anónimas, sin un solo 429. Con los
límites configurados, la caché funcionando y Redis respondiendo.

Las claves que quedaban en Redis lo explicaban:

    throttle_anon_191.107.130.174:54030,30.0.1.5,172.21.0.7
    throttle_anon_191.107.130.174:53238,30.0.1.5,172.21.0.7
                               └── el puerto de origen, distinto en cada petición

El FortiWeb antepone al cliente como `IP:puerto`, y detrás vienen el NPM y la red
interna de Docker. DRF usaba esa cadena completa como identidad, así que cada
petición parecía un cliente nuevo y el contador nacía siempre en 1.

─── Lo que estos tests fijan ────────────────────────────────────────────────
1. Que la identidad sea **solo la IP del cliente**: sin puerto y sin la cadena de
   proxies. Es lo único que hace que el contador acumule.
2. Que los topes aguanten **una entidad detrás de una IP**, no una persona. Es la
   otra mitad: arreglar la identidad con los valores anteriores habría roto la
   operación en vez de protegerla —el 15 de septiembre hay quince personas en una
   sala compartiendo salida a internet—.

Sin el punto 1 el límite no existe. Sin el punto 2 el límite tumba la jornada.
"""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient, APIRequestFactory

from apps.autenticacion.throttles import (LoginRateThrottle, MovilPublicoThrottle,
                                          PruebaPublicaThrottle)

#: Lo que realmente llega en la cabecera detrás del FortiWeb: el cliente con su
#: puerto efímero, el NPM y la red interna de Docker.
XFF_DEL_WAF = '191.107.130.174:54030, 30.0.1.5, 172.21.0.7'
IP_DEL_CLIENTE = '191.107.130.174'


@pytest.fixture(autouse=True)
def cache_limpia():
    cache.clear()
    yield
    cache.clear()


def _peticion(xff=XFF_DEL_WAF, remoto='172.21.0.7'):
    from django.contrib.auth.models import AnonymousUser

    r = APIRequestFactory().post(
        '/api/auth/login/', HTTP_X_FORWARDED_FOR=xff, REMOTE_ADDR=remoto)
    # `allow_request` mira `request.user` para decidir si el cliente es anónimo, y
    # la petición cruda de la fábrica no lo trae: sin esto revienta con
    # AttributeError antes de llegar a contar nada.
    r.user = AnonymousUser()
    return r


# ── 1. La identidad ──────────────────────────────────────────────────────────

@pytest.mark.parametrize('throttle', [
    LoginRateThrottle, PruebaPublicaThrottle, MovilPublicoThrottle])
def test_la_identidad_es_solo_la_ip_del_cliente(throttle):
    """Sin puerto y sin proxies. Los tres límites por IP comparten el mismo criterio."""
    assert throttle().get_ident(_peticion()) == IP_DEL_CLIENTE


def test_el_puerto_cambiante_no_crea_una_identidad_nueva():
    """
    El corazón del defecto. Dos peticiones del MISMO cliente con puertos distintos
    —que es lo normal: el puerto de origen cambia en cada conexión— tienen que
    contar en el mismo cubo. Antes cada una abría el suyo y el tope nunca llegaba.
    """
    t = LoginRateThrottle()
    a = t.get_ident(_peticion('191.107.130.174:54030, 30.0.1.5'))
    b = t.get_ident(_peticion('191.107.130.174:61887, 30.0.1.5'))

    assert a == b == IP_DEL_CLIENTE


def test_dos_clientes_distintos_no_se_mezclan():
    """
    La contracara: limpiar la identidad no puede meter a toda la entidad en un
    solo cubo por accidente. Dos IP distintas cuentan aparte.
    """
    t = LoginRateThrottle()

    assert t.get_ident(_peticion('191.107.130.174:1, 30.0.1.5')) \
        != t.get_ident(_peticion('190.80.5.20:1, 30.0.1.5'))


def test_sin_cabecera_usa_la_direccion_remota():
    """Sin WAF de por medio —pruebas locales, red interna— se cae a REMOTE_ADDR."""
    assert LoginRateThrottle().get_ident(
        _peticion(xff='', remoto='10.0.0.9')) == '10.0.0.9'


def test_una_ip_indeterminable_no_niega_el_servicio():
    """
    Si no se puede identificar al cliente, DRF interpreta `None` como «no aplicar
    el límite». Es la decisión correcta: negar servicio a quien no se pudo
    identificar convertiría un problema de cabeceras en una caída general. La
    defensa del ingreso que no depende de esto es el bloqueo por cuenta.
    """
    assert LoginRateThrottle().get_ident(_peticion(xff='', remoto='')) is None


# ── 2. Que el límite ahora SÍ cuente ─────────────────────────────────────────

class _TopeDeTres(LoginRateThrottle):
    """
    El mismo limitador con un tope pequeño, para poder alcanzarlo en una prueba.

    Se fija el tope acá y no con `override_settings`: DRF guarda sus ajustes en su
    propia caché y no siempre los recarga, así que la prueba pasaba con el tope
    REAL de producción —cuatro peticiones contra cuarenta— sin medir nada.
    """

    def get_rate(self):
        return '3/minute'


def test_el_contador_acumula_entre_peticiones_del_mismo_cliente():
    """
    Con el tope en 3, la cuarta petición del mismo cliente se rechaza **aunque el
    puerto cambie**. Es la prueba de que el defecto está cerrado: antes pasaban
    todas, porque cada puerto abría su propio contador.
    """
    permitidas = sum(
        1 for puerto in (1111, 2222, 3333, 4444)
        if _TopeDeTres().allow_request(
            _peticion(f'{IP_DEL_CLIENTE}:{puerto}, 30.0.1.5'), None)
    )

    assert permitidas == 3, 'el contador no está acumulando por IP'
    assert LoginRateThrottle().scope == 'login'


def test_dos_clientes_distintos_no_se_gastan_el_cupo_entre_si():
    """
    Con el tope en 3, dos IP distintas hacen 3 cada una: seis permitidas. Si la
    limpieza de la identidad hubiera metido a todos en un mismo cubo, la cuarta
    del conjunto se habría rechazado y una territorial entera se cortaría sola.
    """
    permitidas = sum(
        1 for ip in ('191.107.130.174', '190.80.5.20')
        for puerto in (1111, 2222, 3333)
        if _TopeDeTres().allow_request(_peticion(f'{ip}:{puerto}, 30.0.1.5'), None)
    )

    assert permitidas == 6


# ── 3. Que los topes aguanten una sala ───────────────────────────────────────

def test_el_tope_de_ingresos_cabe_una_sala_entera(settings):
    """
    El 15 de septiembre hay quince personas en una sala compartiendo IP, y alguna
    va a teclear mal la clave. Con 5 por minuto —el valor anterior— la sexta veía
    «demasiados intentos» con la credencial correcta, y eso se lee como que las
    credenciales no sirven.
    """
    rate = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login']
    num, _, periodo = rate.partition('/')

    assert periodo.startswith('min')
    assert int(num) >= 30, f'{rate} no alcanza para una sala de veinte personas'


def test_el_cuestionario_publico_cabe_los_37_participantes(settings):
    """
    Cada participante hace del orden de cuatro peticiones, y el pre-test y el
    post-test caen en la misma hora: 37 × 4 × 2 ≈ 300. Con el catch-all de 20 por
    hora, dos tercios del grupo se quedaban sin responder.
    """
    rate = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['prueba_publica']
    num, _, periodo = rate.partition('/')

    assert periodo.startswith('hour')
    assert int(num) >= 300, f'{rate} no alcanza para 37 participantes'


def test_la_consulta_de_version_cabe_una_territorial(settings):
    """
    La hace cada teléfono al abrir la aplicación. Quedarse sin saber la versión
    disponible es exactamente cómo alguien sale a campo con una APK vieja.
    """
    rate = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['movil_publico']
    num, _, periodo = rate.partition('/')

    assert periodo.startswith('hour')
    assert int(num) >= 200, f'{rate} no alcanza para una territorial'


def test_las_busquedas_del_padron_siguen_estrechas(settings):
    """
    Contracara deliberada: este límite va por USUARIO, nunca estuvo roto, y es
    antienumeración del padrón. Subirlo «por coherencia» con los de IP sería
    aflojar justo el que sí protege 5,9 millones de fichas.
    """
    assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['busqueda_rni'] == '30/hour'


# ── 4. Y que el ingreso siga funcionando de punta a punta ────────────────────

@pytest.mark.django_db
def test_una_sala_de_quince_puede_ingresar(db):
    """
    La prueba que importa para el lunes: quince ingresos correctos seguidos desde
    la MISMA IP, con el puerto cambiando como lo cambia el WAF. Ninguno se rechaza.
    """
    from apps.autenticacion.models import Perfil, Usuario

    perfil = Perfil.objects.create(codigo='ENC_SALA', nombre='Encuestador',
                                   activo=True, puede_caracterizar=True,
                                   puede_buscar_rni=True)
    for i in range(15):
        Usuario.objects.create_user(
            codigo_usuario=f'SALA{i:02d}', password='SrniTest2026!',
            nombre_completo=f'Sala {i}', email=f'sala{i}@srni.dev',
            perfil=perfil, activo=True)

    cliente = APIClient()
    codigos = []
    for i in range(15):
        r = cliente.post(
            '/api/auth/login/',
            {'codigo_usuario': f'SALA{i:02d}', 'password': 'SrniTest2026!'},
            format='json',
            HTTP_X_FORWARDED_FOR=f'{IP_DEL_CLIENTE}:{50000 + i}, 30.0.1.5')
        codigos.append(r.status_code)

    assert codigos.count(200) == 15, f'alguien quedó fuera: {codigos}'
    assert 429 not in codigos
