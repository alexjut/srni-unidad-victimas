"""
Tests de paridad — Bloque 5 (SP_SET_RESPUESTAS_DE_ENCUESTA / SP_BORRADORESPUESTAS).

Verifican:
- Upsert de respuesta (no duplica por sesion+pregunta+miembro).
- Al cambiar la respuesta de una pregunta ORIGEN, se BORRA la respuesta de la
  pregunta derivada que queda fuera de flujo (HABILITAR que deja de cumplirse,
  DESHABILITAR que pasa a cumplirse).
- Si la derivada sigue en flujo, su respuesta NO se toca.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta
from apps.encuestas.services import guardar_respuesta
from apps.formulario.models import (
    Instrumento, Capitulo, Pregunta, ReglaSkipLogic,
    AccionSkipChoices, TipoPreguntaChoices, NivelPreguntaChoices,
)
from apps.hogares.models import Hogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()


class GuardarRespuestaTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create(
            codigo_usuario="228206", email="e@uariv.test", nombre_completo="Enc"
        )
        tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento="900002",
            primer_nombre="A", primer_apellido="B",
            fecha_nacimiento="1990-01-01", genero="M",
        )
        self.hogar = Hogar.objects.create(
            codigo_hogar="228206-BBBBB", autorizado=victima,
            estado="BORRADOR", creado_por=self.user,
        )
        self.instrumento = Instrumento.objects.create(
            codigo="TERRITORIAL", nombre="Territorial", version="V8",
            vigente_desde=date(2021, 10, 7),
        )
        self.cap = Capitulo.objects.create(
            instrumento=self.instrumento, codigo="A", nombre="Cap A", orden=1,
            nivel=NivelPreguntaChoices.HOGAR,
        )
        self.origen = Pregunta.objects.create(
            capitulo=self.cap, codigo_externo="A1", texto="¿Tiene discapacidad?",
            tipo=TipoPreguntaChoices.RADIO, nivel=NivelPreguntaChoices.HOGAR, orden=1,
        )
        self.derivada = Pregunta.objects.create(
            capitulo=self.cap, codigo_externo="A2", texto="¿Cuál?",
            tipo=TipoPreguntaChoices.TEXTO, nivel=NivelPreguntaChoices.HOGAR, orden=2,
        )
        # A2 se HABILITA solo si A1 == "1".
        ReglaSkipLogic.objects.create(
            instrumento=self.instrumento, pregunta_origen=self.origen,
            valor_trigger="1", pregunta_afectada=self.derivada,
            accion=AccionSkipChoices.HABILITAR,
        )
        self.sesion = SesionEncuesta.objects.create(
            hogar=self.hogar, instrumento=self.instrumento, encuestador=self.user,
        )

    def _respuestas(self, pregunta):
        return RespuestaEncuesta.objects.filter(sesion=self.sesion, pregunta=pregunta)

    def test_upsert_crea_respuesta(self):
        res = guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="1")
        self.assertTrue(res.creada)
        self.assertTrue(res.cambio)
        self.assertEqual(self._respuestas(self.origen).count(), 1)

    def test_upsert_actualiza_sin_duplicar(self):
        guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="1")
        res = guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="2")
        self.assertFalse(res.creada)
        self.assertTrue(res.cambio)
        self.assertEqual(self._respuestas(self.origen).count(), 1)
        self.assertEqual(self._respuestas(self.origen).first().valor, "2")

    def test_mismo_valor_no_marca_cambio(self):
        guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="1")
        res = guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="1")
        self.assertFalse(res.cambio)

    def test_limpia_derivada_cuando_origen_deja_de_gatillar(self):
        # A1=1 habilita A2; se responde A2.
        guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="1")
        guardar_respuesta(sesion=self.sesion, pregunta=self.derivada, valor="Motriz")
        self.assertEqual(self._respuestas(self.derivada).count(), 1)

        # A1 cambia a 2 → A2 queda fuera de flujo → su respuesta se borra.
        res = guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="2")
        self.assertIn("A2", res.limpiadas)
        self.assertEqual(self._respuestas(self.derivada).count(), 0)

    def test_no_limpia_si_derivada_sigue_en_flujo(self):
        guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="1")
        guardar_respuesta(sesion=self.sesion, pregunta=self.derivada, valor="Motriz")
        # Cambiar A1 de "1" a "1" no aplica; probamos otro trigger válido.
        ReglaSkipLogic.objects.filter(pregunta_origen=self.origen).update(valor_trigger="1,3")
        res = guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="3")
        self.assertNotIn("A2", res.limpiadas)
        self.assertEqual(self._respuestas(self.derivada).count(), 1)

    def test_deshabilitar_borra_derivada_cuando_pasa_a_cumplirse(self):
        # Regla DESHABILITAR: A2 se oculta cuando A1 == "9".
        ReglaSkipLogic.objects.filter(pregunta_origen=self.origen).delete()
        ReglaSkipLogic.objects.create(
            instrumento=self.instrumento, pregunta_origen=self.origen,
            valor_trigger="9", pregunta_afectada=self.derivada,
            accion=AccionSkipChoices.DESHABILITAR,
        )
        guardar_respuesta(sesion=self.sesion, pregunta=self.derivada, valor="Motriz")
        res = guardar_respuesta(sesion=self.sesion, pregunta=self.origen, valor="9")
        self.assertIn("A2", res.limpiadas)
        self.assertEqual(self._respuestas(self.derivada).count(), 0)
