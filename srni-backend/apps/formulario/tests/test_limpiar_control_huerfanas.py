"""
Las tres «huérfanas» del capítulo de control.

`cargar_capitulo_control` arma el código de cada pregunta con un sufijo por
instrumento: `_te` para Territorial y `_tel` para los demás. Una corrida anterior usó
el equivocado, y en producción quedaron preguntas de control con el código de otro
perfil — anotadas como limpieza pendiente desde el 1-sep-2026.

No estorban en campo (ese capítulo no se diligencia), pero sí a la verificación de
paridad entre el servidor y la APK: las cuenta como diferencia, así que nunca da 8 de 8
y deja de servir como alarma.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.encuestas.models import RespuestaEncuesta, SesionEncuesta
from apps.formulario.management.commands.limpiar_control_huerfanas import (
    es_huerfana, sufijo_de,
)
from apps.formulario.models import (
    Capitulo, Instrumento, NivelPreguntaChoices, Pregunta, TipoPreguntaChoices,
)
from apps.hogares.models import Hogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()


class CriterioTests(TestCase):
    def test_el_sufijo_de_territorial_es_distinto(self):
        self.assertEqual(sufijo_de('TERRITORIAL'), '_te')
        self.assertEqual(sufijo_de('TELEFONICO'), '_tel')
        self.assertEqual(sufijo_de('ASISTENCIA'), '_tel')

    def test_reconoce_la_huerfana(self):
        self.assertTrue(es_huerfana('T1_te', 'TELEFONICO'))
        self.assertTrue(es_huerfana('T3_tel', 'TERRITORIAL'))

    def test_no_toca_la_que_está_bien(self):
        self.assertFalse(es_huerfana('T1_tel', 'TELEFONICO'))
        self.assertFalse(es_huerfana('T2_te', 'TERRITORIAL'))

    def test_no_se_mete_con_otras_preguntas_del_capitulo(self):
        """Lo que no tiene forma de pregunta de control lo puso alguien a propósito."""
        self.assertFalse(es_huerfana('OBSERVACIONES', 'TELEFONICO'))
        self.assertFalse(es_huerfana('T4_otro', 'TELEFONICO'))


class LimpiezaTests(TestCase):
    def setUp(self):
        self.instrumento = Instrumento.objects.create(
            codigo='TELEFONICO', nombre='Telefónico', version='V8',
            vigente_desde=date(2021, 10, 7),
        )
        self.cap = Capitulo.objects.create(
            instrumento=self.instrumento, codigo='T', nombre='T. CONTROL', orden=99,
            nivel=NivelPreguntaChoices.HOGAR,
        )

    def _pregunta(self, codigo, orden=1):
        return Pregunta.objects.create(
            capitulo=self.cap, codigo_externo=codigo, texto=codigo,
            tipo=TipoPreguntaChoices.TEXTO, nivel=NivelPreguntaChoices.HOGAR, orden=orden,
        )

    def test_borra_la_huerfana_y_deja_la_correcta(self):
        self._pregunta('T1_te', 1)
        self._pregunta('T1_tel', 2)

        call_command('limpiar_control_huerfanas')

        codigos = set(Pregunta.objects.values_list('codigo_externo', flat=True))
        self.assertEqual(codigos, {'T1_tel'})

    def test_dry_run_no_borra_nada(self):
        self._pregunta('T2_te')

        call_command('limpiar_control_huerfanas', '--dry-run')

        self.assertTrue(Pregunta.objects.filter(codigo_externo='T2_te').exists())

    def test_una_huerfana_con_respuestas_se_desactiva_en_vez_de_borrarse(self):
        """Si alguien la contestó, deja de ser un resto de instalación."""
        pregunta = self._pregunta('T3_te')
        tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento='770001',
            primer_nombre='A', primer_apellido='B',
            fecha_nacimiento='1990-01-01', genero='F',
        )
        user = Usuario.objects.create(
            codigo_usuario='HUERF1', email='h@uariv.test', nombre_completo='Enc')
        hogar = Hogar.objects.create(
            autorizado=victima, estado='BORRADOR', creado_por=user)
        sesion = SesionEncuesta.objects.create(
            hogar=hogar, instrumento=self.instrumento, encuestador=user)
        RespuestaEncuesta.objects.create(
            sesion=sesion, pregunta=pregunta, valor='algo que alguien escribió')

        call_command('limpiar_control_huerfanas')

        pregunta.refresh_from_db()
        self.assertFalse(pregunta.activa)
        self.assertEqual(RespuestaEncuesta.objects.count(), 1, 'no se toca lo capturado')

    def test_sin_huerfanas_no_hace_nada(self):
        self._pregunta('T1_tel')

        call_command('limpiar_control_huerfanas')

        self.assertEqual(Pregunta.objects.count(), 1)
