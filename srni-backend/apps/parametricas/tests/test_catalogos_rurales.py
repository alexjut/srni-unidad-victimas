"""
QA · M5 — los catálogos rurales y étnicos estaban vacíos.

Medido contra producción el 18-sep-2026: 0 veredas, 0 resguardos, 0 consejos
comunitarios. Los instrumentos piden la vereda como TEXTO LIBRE, así que el mismo
lugar termina escrito de diez maneras y no se puede agrupar ni contar.

Acá se fijan las dos reglas de lectura del catálogo de Oracle, que se aprendieron
mirando el dato: el municipio va dentro del código de la vereda, y el nombre viene
compuesto con el departamento y el municipio por delante.
"""
from django.test import TestCase

from apps.parametricas.management.commands.cargar_catalogos_rurales_oracle import (
    RELLENOS, _nombre_de_vereda,
)
from apps.parametricas.models import ComunidadNegra, ResguardoIndigena


class NombreDeVeredaTests(TestCase):
    def test_se_queda_con_el_nombre_de_la_vereda(self):
        self.assertEqual(
            _nombre_de_vereda('ANTIOQUIA-SAN LUIS-SANTA ISABEL'), 'SANTA ISABEL')

    def test_un_nombre_con_guion_propio_no_se_parte_de_mas(self):
        # Se toma el ÚLTIMO tramo, que es el de la vereda.
        self.assertEqual(_nombre_de_vereda('CAUCA-POPAYAN-EL PLACER'), 'EL PLACER')

    def test_nombre_simple_se_devuelve_igual(self):
        self.assertEqual(_nombre_de_vereda('LA ESPERANZA'), 'LA ESPERANZA')

    def test_vacio_no_revienta(self):
        self.assertEqual(_nombre_de_vereda(''), '')
        self.assertEqual(_nombre_de_vereda(None), '')

    def test_el_codigo_lleva_el_municipio_en_los_cinco_primeros(self):
        """`0566080` = municipio DANE `05660` + consecutivo de la vereda."""
        self.assertEqual('0566080'[:5], '05660')


class RellenosTests(TestCase):
    def test_los_rellenos_del_catalogo_no_son_lugares(self):
        """«Sin Informacion» figura como resguardo en Oracle; ofrecerlo sería absurdo."""
        self.assertIn('sin informacion', RELLENOS)


class CatalogoNacionalTests(TestCase):
    def test_un_consejo_comunitario_existe_sin_municipio(self):
        """El catálogo de la entidad es nacional: exigir municipio obligaría a inventarlo."""
        cc = ComunidadNegra.objects.create(
            codigo='CCN-1093', nombre='Cc De La Cuenca Del Rio Acandi Seco')

        self.assertIsNone(cc.municipio)

    def test_un_resguardo_existe_sin_municipio(self):
        r = ResguardoIndigena.objects.create(codigo='RES-898', nombre='Achagua')

        self.assertIsNone(r.municipio)
