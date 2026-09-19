"""
Las tres preguntas del capítulo de control del Telefónico no sobraban: tenían otro id.

Las respuestas que manda el teléfono viajan con el **id de la pregunta**. Si el
servidor tiene esa misma pregunta con otro id, la respuesta se rechaza y la
encuestadora no se entera: su captura se queda en la cola del dispositivo.

Medido en producción el 19-sep-2026: `T1_tel`, `T2_tel` y `T3_tel` existían en los dos
lados con identificadores distintos. El arreglo obvio —borrarlas, que era lo que decía
el pendiente heredado— habría dejado a la APK mandando respuestas de tres preguntas
inexistentes.
"""
import json
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.encuestas.models import RespuestaEncuesta, SesionEncuesta
from apps.formulario.models import (
    AccionSkipChoices, Capitulo, Instrumento, NivelPreguntaChoices, OpcionRespuesta,
    Pregunta, ReglaSkipLogic, TipoPreguntaChoices,
)
from apps.hogares.models import Hogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()

ID_APK = '60c92827-0000-4000-8000-000000000001'


class AlinearIdsTests(TestCase):
    def setUp(self):
        self.instrumento = Instrumento.objects.create(
            codigo='TELEFONICO', nombre='Telefónico', version='V8',
            vigente_desde=date(2021, 10, 7),
        )
        self.cap = Capitulo.objects.create(
            instrumento=self.instrumento, codigo='T', nombre='T. CONTROL', orden=99,
            nivel=NivelPreguntaChoices.HOGAR,
        )
        self.pregunta = Pregunta.objects.create(
            capitulo=self.cap, codigo_externo='T3_tel', texto='Observaciones',
            tipo=TipoPreguntaChoices.TEXTO, nivel=NivelPreguntaChoices.HOGAR, orden=3,
        )
        self.mapa = self._escribir_mapa({'TELEFONICO': {'T3_tel': ID_APK}})

    def _escribir_mapa(self, contenido) -> str:
        ruta = Path(self._get_temp()) / 'mapa.json'
        ruta.write_text(json.dumps(contenido), encoding='utf-8')
        return str(ruta)

    def _get_temp(self) -> str:
        import tempfile
        if not hasattr(self, '_tmp'):
            self._tmp = tempfile.mkdtemp()
        return self._tmp

    def _sesion(self):
        tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento='660001',
            primer_nombre='A', primer_apellido='B',
            fecha_nacimiento='1990-01-01', genero='F',
        )
        user = Usuario.objects.create(
            codigo_usuario='ALIN1', email='a@uariv.test', nombre_completo='Enc')
        hogar = Hogar.objects.create(autorizado=victima, estado='BORRADOR', creado_por=user)
        return SesionEncuesta.objects.create(
            hogar=hogar, instrumento=self.instrumento, encuestador=user)

    # ── Lo esencial ──────────────────────────────────────────────────────────

    def test_la_pregunta_queda_con_el_id_de_la_apk(self):
        call_command('alinear_ids_desde_bundle', '--mapa', self.mapa)

        self.assertTrue(Pregunta.objects.filter(id=ID_APK, codigo_externo='T3_tel').exists())
        self.assertEqual(Pregunta.objects.filter(codigo_externo='T3_tel').count(), 1)

    def test_dry_run_no_cambia_nada(self):
        call_command('alinear_ids_desde_bundle', '--mapa', self.mapa, '--dry-run')

        self.pregunta.refresh_from_db()
        self.assertNotEqual(str(self.pregunta.id), ID_APK)

    def test_las_respuestas_ya_capturadas_se_trasladan(self):
        """Nadie pierde lo que respondió porque cambiemos un identificador."""
        sesion = self._sesion()
        RespuestaEncuesta.objects.create(
            sesion=sesion, pregunta=self.pregunta, valor='lo que dijo la familia')

        call_command('alinear_ids_desde_bundle', '--mapa', self.mapa)

        respuesta = RespuestaEncuesta.objects.get()
        self.assertEqual(str(respuesta.pregunta_id), ID_APK)
        self.assertEqual(respuesta.valor, 'lo que dijo la familia')

    def test_las_opciones_viajan_con_la_pregunta(self):
        OpcionRespuesta.objects.create(
            pregunta=self.pregunta, valor='1', etiqueta='Sí', orden=1)

        call_command('alinear_ids_desde_bundle', '--mapa', self.mapa)

        nueva = Pregunta.objects.get(id=ID_APK)
        self.assertEqual([o.etiqueta for o in nueva.opciones.all()], ['Sí'])

    def test_las_reglas_siguen_apuntando_a_la_pregunta(self):
        otra = Pregunta.objects.create(
            capitulo=self.cap, codigo_externo='T2_tel', texto='Otra',
            tipo=TipoPreguntaChoices.TEXTO, nivel=NivelPreguntaChoices.HOGAR, orden=2,
        )
        ReglaSkipLogic.objects.create(
            instrumento=self.instrumento, pregunta_origen=otra, valor_trigger='1',
            pregunta_afectada=self.pregunta, accion=AccionSkipChoices.HABILITAR,
        )

        call_command('alinear_ids_desde_bundle', '--mapa', self.mapa)

        regla = ReglaSkipLogic.objects.get()
        self.assertEqual(str(regla.pregunta_afectada_id), ID_APK)

    def test_correrlo_dos_veces_no_hace_nada_la_segunda(self):
        call_command('alinear_ids_desde_bundle', '--mapa', self.mapa)
        call_command('alinear_ids_desde_bundle', '--mapa', self.mapa)

        self.assertEqual(Pregunta.objects.filter(codigo_externo='T3_tel').count(), 1)

    def test_una_pregunta_que_el_servidor_no_tiene_se_informa_y_no_rompe(self):
        mapa = self._escribir_mapa({'TELEFONICO': {'NO_EXISTE': ID_APK}})

        call_command('alinear_ids_desde_bundle', '--mapa', mapa)

        self.assertFalse(Pregunta.objects.filter(codigo_externo='NO_EXISTE').exists())
