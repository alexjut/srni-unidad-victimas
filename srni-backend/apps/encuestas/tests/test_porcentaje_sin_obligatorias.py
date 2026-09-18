"""
APK-005 — una entrevista respondida no puede figurar en 0 %.

El porcentaje se mide sobre las obligatorias VISIBLES. Cuatro de los instrumentos
en producción al 18-sep-2026 (Asistencia, Buenaventura, San Andrés y Urbano-Étnico)
no tienen ni una pregunta marcada como obligatoria: su curaduría contra el manual
está pendiente. Con denominador cero, la entrevista entera respondida daba 0 %, y en
el panel eso se lee como trabajo no hecho.

Se midió el 18-sep contra producción: el recálculo dejaba **37 de 51 sesiones**
COMPLETADA en 0 %, varias de ellas viniendo de 100 %.

Ahora, cuando el instrumento no declara obligatorias, se mide sobre todo lo que hay
para responder. Dice menos de lo que debería —no distingue lo exigible de lo
opcional— pero dice la verdad.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.encuestas.models import RespuestaEncuesta, SesionEncuesta
from apps.formulario.models import (
    Capitulo, Instrumento, NivelPreguntaChoices, Pregunta, TipoPreguntaChoices,
)
from apps.hogares.models import Hogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()


class PorcentajeSinObligatoriasTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create(
            codigo_usuario='PCT1', email='pct@uariv.test', nombre_completo='Enc',
        )
        tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento='990001',
            primer_nombre='A', primer_apellido='B',
            fecha_nacimiento='1990-01-01', genero='F',
        )
        self.hogar = Hogar.objects.create(
            codigo_hogar='PCT1-AAAAA', autorizado=victima,
            estado='BORRADOR', creado_por=self.user,
        )
        self.instrumento = Instrumento.objects.create(
            codigo='ASISTENCIA', nombre='Asistencia humanitaria', version='V8',
            vigente_desde=date(2021, 10, 7),
        )
        self.cap = Capitulo.objects.create(
            instrumento=self.instrumento, codigo='A', nombre='Cap A', orden=1,
            nivel=NivelPreguntaChoices.HOGAR,
        )
        self.sesion = SesionEncuesta.objects.create(
            hogar=self.hogar, instrumento=self.instrumento, encuestador=self.user,
        )

    def _pregunta(self, codigo, orden, obligatoria=False, precargada=False):
        return Pregunta.objects.create(
            capitulo=self.cap, codigo_externo=codigo, texto=codigo,
            tipo=TipoPreguntaChoices.TEXTO, nivel=NivelPreguntaChoices.HOGAR,
            orden=orden, obligatoria=obligatoria, es_precargada=precargada,
        )

    def _responder(self, pregunta, valor='algo'):
        RespuestaEncuesta.objects.create(
            sesion=self.sesion, pregunta=pregunta, valor=valor,
        )

    def test_instrumento_sin_obligatorias_mide_sobre_lo_respondible(self):
        a, b, c, d = [self._pregunta(f'P{i}', i) for i in range(1, 5)]
        self._responder(a)
        self._responder(b)

        self.assertEqual(self.sesion.recalcular_porcentaje(), 50)

    def test_todo_respondido_sin_obligatorias_es_cien(self):
        for i, p in enumerate([self._pregunta(f'Q{i}', i) for i in range(1, 4)]):
            self._responder(p)

        self.assertEqual(self.sesion.recalcular_porcentaje(), 100)

    def test_nada_respondido_sigue_en_cero(self):
        self._pregunta('R1', 1)
        self._pregunta('R2', 2)

        self.assertEqual(self.sesion.recalcular_porcentaje(), 0)

    def test_con_obligatorias_manda_el_criterio_normal(self):
        """El respaldo NO puede cambiar lo que ya hacía un instrumento curado."""
        oblig = self._pregunta('O1', 1, obligatoria=True)
        self._pregunta('O2', 2, obligatoria=True)
        # Opcionales respondidas: no deben inflar el porcentaje.
        opcional = self._pregunta('X1', 3)
        self._responder(oblig)
        self._responder(opcional)

        self.assertEqual(self.sesion.recalcular_porcentaje(), 50)

    def test_las_precargadas_no_entran_ni_en_el_respaldo(self):
        """Vienen del padrón: nadie las responde en la entrevista."""
        self._pregunta('PRE', 1, precargada=True)
        libre = self._pregunta('LIB', 2)
        self._responder(libre)

        self.assertEqual(self.sesion.recalcular_porcentaje(), 100)

    def test_instrumento_sin_preguntas_es_cero(self):
        self.assertEqual(self.sesion.recalcular_porcentaje(), 0)
