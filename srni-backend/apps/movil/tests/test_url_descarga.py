"""
La dirección de descarga que se le entrega al celular.

El endpoint respondía `http://caracterizacion.unidadvictimas.gov.co/...` aunque
se entrara por HTTPS: detrás del WAF, Django ve una petición en claro porque
FortiWeb termina el TLS y reenvía al :80. Estas pruebas fijan las tres formas de
resolverlo, en el orden en que se aplican.
"""
from django.test import RequestFactory, TestCase, override_settings

from apps.movil.views import url_descarga

DOMINIO = 'caracterizacion.unidadvictimas.gov.co'


class UrlDescargaTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _peticion(self, **extra):
        return self.factory.get('/api/movil/version/', SERVER_NAME=DOMINIO, **extra)

    @override_settings(MOVIL_URL_BASE=f'https://{DOMINIO}')
    def test_manda_la_base_configurada(self):
        url = url_descarga(self._peticion())
        self.assertEqual(url, f'https://{DOMINIO}/api/movil/descargar/')

    @override_settings(MOVIL_URL_BASE=f'https://{DOMINIO}/')
    def test_la_base_no_duplica_la_barra(self):
        url = url_descarga(self._peticion())
        self.assertEqual(url, f'https://{DOMINIO}/api/movil/descargar/')

    @override_settings(MOVIL_URL_BASE='')
    def test_sin_base_respeta_el_esquema_que_anuncia_el_proxy(self):
        url = url_descarga(self._peticion(HTTP_X_FORWARDED_PROTO='https'))
        self.assertEqual(url, f'https://{DOMINIO}/api/movil/descargar/')

    @override_settings(MOVIL_URL_BASE='')
    def test_sin_base_toma_el_primer_valor_de_la_cadena_de_proxies(self):
        url = url_descarga(self._peticion(HTTP_X_FORWARDED_PROTO='https, http'))
        self.assertEqual(url, f'https://{DOMINIO}/api/movil/descargar/')

    @override_settings(MOVIL_URL_BASE='')
    def test_sin_base_ni_proxy_queda_como_llego_la_peticion(self):
        # Desarrollo local: no hay TLS y no hay que inventarlo.
        url = url_descarga(self.factory.get('/api/movil/version/', SERVER_NAME='localhost'))
        self.assertEqual(url, 'http://localhost/api/movil/descargar/')
