"""
El código del hogar se genera solo (pendiente desde junio).

Se vio el efecto el 18-sep-2026 contra producción: los 54 hogares tenían el código
VACÍO. No es cosmético: es la referencia con la que se sigue un hogar entre SICAV, el
panel y el libro de escrituras al sistema legado, donde viaja como `hog_codigo_sicav`.
Sin él, la única forma de nombrar un hogar era el pedazo inicial de su UUID.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.hogares.models import Hogar, generar_codigo_hogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()


class CodigoHogarTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create(
            codigo_usuario='KLMUNOZM', email='k@uariv.test', nombre_completo='Encuestadora',
        )
        self.tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')

    def _victima(self, doc):
        return Victima.objects.create(
            tipo_documento=self.tipo, numero_documento=doc,
            primer_nombre='A', primer_apellido='B',
            fecha_nacimiento='1990-01-01', genero='F',
        )

    def _hogar(self, doc, **extra):
        return Hogar.objects.create(
            autorizado=self._victima(doc), estado='BORRADOR',
            creado_por=self.user, **extra,
        )

    def test_se_genera_al_crear_con_el_codigo_del_encuestador(self):
        h = self._hogar('900100')

        self.assertTrue(h.codigo_hogar.startswith('KLMUNOZM-'))
        self.assertEqual(len(h.codigo_hogar.split('-')[1]), 5)

    def test_dos_hogares_no_comparten_codigo(self):
        a = self._hogar('900101')
        b = self._hogar('900102')

        self.assertNotEqual(a.codigo_hogar, b.codigo_hogar)

    def test_no_pisa_un_codigo_que_ya_venia(self):
        """Los hogares del piloto traen su código; regenerarlo rompería su rastro."""
        h = self._hogar('900103', codigo_hogar='999999-2W832')

        self.assertEqual(h.codigo_hogar, '999999-2W832')

    def test_guardar_de_nuevo_no_cambia_el_codigo(self):
        h = self._hogar('900104')
        original = h.codigo_hogar

        h.estado = 'COMPLETADO'
        h.save()
        h.refresh_from_db()

        self.assertEqual(h.codigo_hogar, original)

    def test_sin_encuestador_igual_queda_con_codigo(self):
        """Una carga automática no tiene usuario; el hogar no puede quedar sin nombre."""
        h = Hogar.objects.create(
            autorizado=self._victima('900105'), estado='BORRADOR', creado_por=None,
        )

        self.assertTrue(h.codigo_hogar.startswith('SICAV-'))


class GenerarCodigoHogarTests(TestCase):
    def test_no_usa_caracteres_que_se_confunden_al_dictarlo(self):
        """Estos códigos se dictan por teléfono y se copian a mano en actas."""
        sufijos = ''.join(generar_codigo_hogar('ABC').split('-')[1] for _ in range(200))

        for ambiguo in '01OI':
            self.assertNotIn(ambiguo, sufijos)

    def test_el_prefijo_va_en_mayuscula_y_sin_espacios(self):
        self.assertTrue(generar_codigo_hogar('  klmunozm ').startswith('KLMUNOZM-'))
