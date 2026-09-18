"""
La documentación de la API no puede quedar abierta al público.

drf-spectacular sirve `/api/schema/`, `/api/docs/` y `/api/redoc/` con AllowAny por
omisión. En el despliegue esas rutas salen por el dominio institucional, así que
cualquiera podía leer el mapa completo de la API. No expone datos, pero sí rutas,
parámetros y la forma de cada respuesta. Hallazgo de la revisión del 18-sep-2026.
"""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.autenticacion.models import Perfil

Usuario = get_user_model()

RUTAS = ['/api/schema/', '/api/docs/', '/api/redoc/']


class DocumentacionProtegidaTests(APITestCase):
    def test_anonimo_no_ve_la_documentacion(self):
        for ruta in RUTAS:
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_usuario_autenticado_si_la_ve(self):
        perfil = Perfil.objects.create(codigo='P_DOCS', nombre='Encuestador', activo=True)
        user = Usuario.objects.create_user(
            codigo_usuario='DOCS1', password='SrniTest2026!', email='docs@uariv.test',
            nombre_completo='Quien consulta', perfil=perfil, activo=True,
        )
        self.client.force_authenticate(user)

        for ruta in RUTAS:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, status.HTTP_200_OK)
