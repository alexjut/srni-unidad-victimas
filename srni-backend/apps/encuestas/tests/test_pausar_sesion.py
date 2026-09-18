"""
Pausar y reanudar una caracterización (pedido de campo, QA 16-sep-2026).

«A veces estamos en una caracterización y por motivos tenemos que pausarla, y
luego, días o meses después, continuarla.»

Lo que se fija acá:
- Pausar deja la sesión en SUSPENDIDA y conserva las respuestas.
- La sesión pausada SIGUE siendo la activa del hogar: pedir otra caracterización
  devuelve la misma y no crea una segunda (regla «un hogar → una abierta»).
- Se puede seguir respondiendo, y al hacerlo vuelve a EN_PROGRESO sola.
- Una completada no se pausa ni se reanuda.
- `estado` ya no se puede cambiar por PATCH.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.auditoria.models import LogAcceso
from apps.autenticacion.models import Perfil
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta
from apps.formulario.models import (
    Instrumento, Capitulo, Pregunta, TipoPreguntaChoices, NivelPreguntaChoices,
)
from apps.hogares.models import Hogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()


class PausarSesionTests(APITestCase):
    def setUp(self):
        perfil = Perfil.objects.create(
            codigo='P_PAUSA', nombre='Encuestadora', activo=True,
            puede_caracterizar=True, puede_buscar_rni=True,
        )
        self.user = Usuario.objects.create_user(
            codigo_usuario="PAUSA1", password="SrniTest2026!", email="pausa@uariv.test",
            nombre_completo="Encuestadora", perfil=perfil, activo=True,
        )
        self.client.force_authenticate(self.user)

        tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento="999123",
            primer_nombre="A", primer_apellido="B",
            fecha_nacimiento="1990-01-01", genero="F",
        )
        self.hogar = Hogar.objects.create(
            codigo_hogar="PAUSA1-AAAAA", autorizado=victima,
            estado="BORRADOR", creado_por=self.user,
        )
        self.instrumento = Instrumento.objects.create(
            codigo="TERRITORIAL", nombre="Territorial", version="V8",
            vigente_desde=date(2021, 10, 7),
        )
        cap = Capitulo.objects.create(
            instrumento=self.instrumento, codigo="A", nombre="Cap A", orden=1,
            nivel=NivelPreguntaChoices.HOGAR,
        )
        self.pregunta = Pregunta.objects.create(
            capitulo=cap, codigo_externo="A1", texto="¿Municipio?",
            tipo=TipoPreguntaChoices.TEXTO, nivel=NivelPreguntaChoices.HOGAR, orden=1,
        )
        self.sesion = SesionEncuesta.objects.create(
            hogar=self.hogar, instrumento=self.instrumento, encuestador=self.user,
            estado="EN_PROGRESO",
        )
        RespuestaEncuesta.objects.create(
            sesion=self.sesion, pregunta=self.pregunta, valor="Soacha",
        )

    def _url(self, accion):
        return reverse(f'sesion-{accion}', args=[self.sesion.id])

    def test_pausar_deja_suspendida_y_conserva_respuestas(self):
        r = self.client.post(self._url('pausar'))

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['estado'], 'SUSPENDIDA')
        self.sesion.refresh_from_db()
        self.assertEqual(self.sesion.estado, 'SUSPENDIDA')
        self.assertEqual(
            RespuestaEncuesta.objects.filter(sesion=self.sesion).count(), 1,
            'pausar no puede tocar lo ya capturado',
        )
        self.assertTrue(
            LogAcceso.objects.filter(accion='PAUSAR_ENCUESTA', recurso_id=str(self.sesion.id)).exists()
        )

    def test_pausada_sigue_siendo_la_activa_del_hogar(self):
        self.client.post(self._url('pausar'))

        r = self.client.post('/api/encuestas/', {
            'hogar': str(self.hogar.id),
            'instrumento': str(self.instrumento.id),
        }, format='json')

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['id'], str(self.sesion.id),
                         'pausar no puede hacer que el hogar acepte una segunda caracterización')
        self.assertEqual(SesionEncuesta.objects.filter(hogar=self.hogar).count(), 1)

    def test_reanudar_vuelve_a_en_progreso(self):
        self.client.post(self._url('pausar'))

        r = self.client.post(self._url('reanudar'))

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.sesion.refresh_from_db()
        self.assertEqual(self.sesion.estado, 'EN_PROGRESO')
        self.assertTrue(
            LogAcceso.objects.filter(accion='REANUDAR_ENCUESTA', recurso_id=str(self.sesion.id)).exists()
        )

    def test_reanudar_dos_veces_no_falla(self):
        """El teléfono puede reenviarlo al volver la señal."""
        self.client.post(self._url('pausar'))
        self.client.post(self._url('reanudar'))

        r = self.client.post(self._url('reanudar'))

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['estado'], 'EN_PROGRESO')

    def test_responder_sobre_pausada_la_reactiva(self):
        """La cola sube respuestas después de pausar: no se pierden ni la dejan pausada."""
        self.client.post(self._url('pausar'))

        r = self.client.post(
            reverse('sesion-responder', args=[self.sesion.id]),
            {'pregunta_id': str(self.pregunta.id), 'valor': 'Bogotá'}, format='json',
        )

        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.sesion.refresh_from_db()
        self.assertEqual(self.sesion.estado, 'EN_PROGRESO')

    def test_no_se_pausa_una_completada(self):
        self.sesion.estado = 'COMPLETADA'
        self.sesion.save(update_fields=['estado'])

        r = self.client.post(self._url('pausar'))

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.sesion.refresh_from_db()
        self.assertEqual(self.sesion.estado, 'COMPLETADA')

    def test_no_se_reanuda_una_completada(self):
        self.sesion.estado = 'COMPLETADA'
        self.sesion.save(update_fields=['estado'])

        r = self.client.post(self._url('reanudar'))

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_estado_no_se_puede_cambiar_por_patch(self):
        """Antes se podía marcar COMPLETADA sin pasar por finalizar."""
        r = self.client.patch(
            f'/api/encuestas/{self.sesion.id}/', {'estado': 'COMPLETADA'}, format='json',
        )

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.sesion.refresh_from_db()
        self.assertEqual(self.sesion.estado, 'EN_PROGRESO')
