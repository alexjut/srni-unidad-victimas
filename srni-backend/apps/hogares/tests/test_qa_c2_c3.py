"""
Dos hallazgos del informe de QA del sitio administrativo.

· C2 — se podía abrir una caracterización con un instrumento retirado. Las
  respuestas quedaban ancladas a una versión que la entidad ya no usa.
· C3 — el hogar declaraba «1 persona» con cinco integrantes registrados:
  `numero_personas` se fija al crear y nadie lo volvía a tocar.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.autenticacion.models import Perfil
from apps.encuestas.serializers import SesionEncuestaDetalleSerializer
from apps.formulario.models import Instrumento
from apps.hogares.models import Hogar, MiembroHogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()
HOY = date.today()


def _base(codigo_usuario, doc):
    user = Usuario.objects.create(
        codigo_usuario=codigo_usuario, email=f'{codigo_usuario}@uariv.test',
        nombre_completo='Enc',
    )
    tipo = TipoDocumento.objects.create(codigo=f'C{doc[-2:]}', nombre='Cédula')
    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento=doc,
        primer_nombre='A', primer_apellido='B',
        fecha_nacimiento='1990-01-01', genero='F',
    )
    hogar = Hogar.objects.create(
        autorizado=victima, estado='BORRADOR', creado_por=user,
    )
    return user, hogar


class InstrumentoRetiradoTests(TestCase):
    """C2 — no se abre una caracterización con un instrumento que ya no se usa."""

    def setUp(self):
        self.user, self.hogar = _base('C2USER', '880001')

    def _validar(self, instrumento):
        s = SesionEncuestaDetalleSerializer(data={
            'hogar': str(self.hogar.id), 'instrumento': str(instrumento.id),
        })
        return s.is_valid(), s.errors

    def test_instrumento_vigente_se_acepta(self):
        vigente = Instrumento.objects.create(
            codigo='TERRITORIAL', nombre='Territorial', version='V8',
            vigente_desde=HOY - timedelta(days=30),
        )

        ok, _ = self._validar(vigente)

        self.assertTrue(ok)

    def test_instrumento_inactivo_se_rechaza(self):
        inactivo = Instrumento.objects.create(
            codigo='VIEJO', nombre='Viejo', version='V1',
            vigente_desde=HOY - timedelta(days=30), activo=False,
        )

        ok, errores = self._validar(inactivo)

        self.assertFalse(ok)
        self.assertIn('instrumento', errores)

    def test_instrumento_con_vigencia_terminada_se_rechaza(self):
        vencido = Instrumento.objects.create(
            codigo='VENCIDO', nombre='Vencido', version='V2',
            vigente_desde=HOY - timedelta(days=60),
            vigente_hasta=HOY - timedelta(days=1),
        )

        ok, errores = self._validar(vencido)

        self.assertFalse(ok)
        self.assertIn('instrumento', errores)

    def test_una_sesion_ya_abierta_se_puede_seguir_terminando(self):
        """Si el instrumento se retira después, no se pierde el trabajo hecho."""
        retirado = Instrumento.objects.create(
            codigo='RETIRADO', nombre='Retirado', version='V1',
            vigente_desde=HOY - timedelta(days=60), activo=False,
        )
        from apps.encuestas.models import SesionEncuesta
        sesion = SesionEncuesta.objects.create(
            hogar=self.hogar, instrumento=retirado, encuestador=self.user,
        )

        s = SesionEncuestaDetalleSerializer(
            sesion, data={'observaciones': 'sigue'}, partial=True,
        )

        self.assertTrue(s.is_valid(), s.errors)


class NumeroPersonasTests(APITestCase):
    """C3 — el número de personas no puede ser menor que los integrantes."""

    def setUp(self):
        perfil = Perfil.objects.create(
            codigo='P_C3', nombre='Encuestador', activo=True,
            puede_caracterizar=True, puede_buscar_rni=True,
        )
        self.user = Usuario.objects.create_user(
            codigo_usuario='C3USER', password='SrniTest2026!', email='c3@uariv.test',
            nombre_completo='Enc', perfil=perfil, activo=True,
        )
        self.client.force_authenticate(self.user)
        tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento='880002',
            primer_nombre='A', primer_apellido='B',
            fecha_nacimiento='1990-01-01', genero='F',
        )
        self.hogar = Hogar.objects.create(
            autorizado=victima, estado='BORRADOR', creado_por=self.user,
            numero_personas=1,
        )

    def _agregar(self, nombre):
        return self.client.post(
            f'/api/hogares/{self.hogar.id}/agregar-miembro/',
            {'nombre_completo': nombre, 'rol': 'MIEMBRO'}, format='json',
        )

    def test_agregar_integrantes_sube_el_numero_de_personas(self):
        self._agregar('HIJA UNO')
        self._agregar('HIJO DOS')

        self.hogar.refresh_from_db()
        self.assertGreaterEqual(
            self.hogar.numero_personas,
            self.hogar.miembros.filter(retirado_en__isnull=True).count(),
        )

    def test_no_baja_lo_que_declaro_la_familia(self):
        """Puede haber más habitantes que integrantes registrados: eso se respeta."""
        self.hogar.numero_personas = 8
        self.hogar.save(update_fields=['numero_personas'])

        self._agregar('HIJA UNO')

        self.hogar.refresh_from_db()
        self.assertEqual(self.hogar.numero_personas, 8)

    def test_los_retirados_no_cuentan(self):
        MiembroHogar.objects.create(
            hogar=self.hogar, nombre_completo='SE FUE', rol='MIEMBRO',
            retirado_en=HOY, motivo_retiro='FALLECIMIENTO',
        )

        self.assertEqual(self.hogar.sincronizar_numero_personas(), 1)
