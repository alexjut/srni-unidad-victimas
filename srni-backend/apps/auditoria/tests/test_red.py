"""
La IP del cliente, tal como llega detrás del WAF.

Esto tumbó la búsqueda en producción el 2-ago: el WAF (FortiWeb) reenvía
`X-Forwarded-For: 186.29.187.18:62432` —con puerto—, `LogAcceso.ip_origen` es un
`GenericIPAddressField`, y al escribir el registro de auditoría el INSERT
reventaba. La petición entera respondía **500**.

Lo peligroso del defecto es dónde NO se ve: por `localhost` la IP llega limpia,
así que las pruebas locales pasaban y el fallo aparecía solo entrando por el
dominio — o sea, solo para los usuarios reales.
"""
import pytest
from rest_framework.test import APIClient

from apps.auditoria.red import ip_de_request, sin_puerto


class RequestFalso:
    def __init__(self, **meta):
        self.META = meta


# ── sin_puerto ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize('entrada,esperado', [
    ('186.29.187.18:62432', '186.29.187.18'),   # el caso real del WAF
    ('186.29.187.18',       '186.29.187.18'),
    ('[::1]:62432',         '::1'),
    ('[2001:db8::1]:443',   '2001:db8::1'),
    ('2001:db8::1',         '2001:db8::1'),     # IPv6 sin puerto: NO se toca
    ('',                    ''),
])
def test_sin_puerto(entrada, esperado):
    assert sin_puerto(entrada) == esperado


# ── ip_de_request ────────────────────────────────────────────────────────────

def test_toma_el_primer_valor_del_forwarded_for():
    """El primero es el cliente; los siguientes son los proxies que atravesó."""
    r = RequestFalso(HTTP_X_FORWARDED_FOR='186.29.187.18:62432, 10.0.0.1, 172.17.0.5')
    assert ip_de_request(r) == '186.29.187.18'


def test_sin_cabecera_usa_remote_addr():
    assert ip_de_request(RequestFalso(REMOTE_ADDR='172.21.0.1')) == '172.21.0.1'


def test_un_valor_ilegible_no_puede_tumbar_la_peticion():
    """
    Ante basura se devuelve el default en vez de dejar que reviente el INSERT.
    Perder la precisión de una IP en el registro es malo; tumbar el trabajo del
    encuestador por no poder registrarla, peor.
    """
    for basura in ('no-es-una-ip', 'unknown', '999.999.999.999', ':::'):
        assert ip_de_request(RequestFalso(HTTP_X_FORWARDED_FOR=basura)) == '0.0.0.0'


# ── el caso completo, extremo a extremo ──────────────────────────────────────

@pytest.mark.django_db
def test_buscar_con_la_ip_del_WAF_no_responde_500():
    """
    La reproducción exacta del fallo: misma petición, misma cabecera que manda el
    WAF. Antes daba 500; el resultado correcto es 404 (no existe esa víctima),
    y sobre todo que el registro de auditoría se haya escrito.
    """
    from apps.auditoria.models import LogAcceso
    from apps.autenticacion.models import Perfil, Usuario

    perfil = Perfil.objects.create(
        codigo='ENC_IP', nombre='Encuestador IP', puede_buscar_rni=True,
        puede_caracterizar=True, activo=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario='IPTEST', password='SrniTest2026!', nombre_completo='IP Test',
        email='ip@srni.dev', perfil=perfil, activo=True)

    c = APIClient()
    c.force_authenticate(user=usuario)
    resp = c.post(
        '/api/victimas/buscar/',
        {'tipo_documento_codigo': 'CC', 'numero_documento': '99999999'},
        format='json',
        HTTP_X_FORWARDED_FOR='186.29.187.18:62432',
    )

    assert resp.status_code == 404, 'con la IP del WAF la búsqueda respondía 500'
    log = LogAcceso.objects.filter(accion='BUSQUEDA_RNI').latest('timestamp')
    assert log.ip_origen == '186.29.187.18'
