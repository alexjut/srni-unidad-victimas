"""
Management command: cargar_departamentos_municipios
Carga los 33 departamentos de Colombia y sus municipios capitales
usando los códigos DANE oficiales.

Para cargar los 1122 municipios completos, proporciona un CSV con formato:
    codigo_dane_mun,nombre_municipio,codigo_dane_dep
y ejecuta:
    python manage.py cargar_departamentos_municipios --csv=ruta/al/archivo.csv

Uso sin CSV (solo departamentos + capitales):
    python manage.py cargar_departamentos_municipios

Idempotente: usa update_or_create por codigo_dane.
"""
import csv
import os
from django.core.management.base import BaseCommand, CommandError
from apps.parametricas.models import Departamento, Municipio


# Fuente: DIVIPOLA DANE 2023
DEPARTAMENTOS = [
    ('05', 'Antioquia'),
    ('08', 'Atlántico'),
    ('11', 'Bogotá D.C.'),
    ('13', 'Bolívar'),
    ('15', 'Boyacá'),
    ('17', 'Caldas'),
    ('18', 'Caquetá'),
    ('19', 'Cauca'),
    ('20', 'Cesar'),
    ('23', 'Córdoba'),
    ('25', 'Cundinamarca'),
    ('27', 'Chocó'),
    ('41', 'Huila'),
    ('44', 'La Guajira'),
    ('47', 'Magdalena'),
    ('50', 'Meta'),
    ('52', 'Nariño'),
    ('54', 'Norte de Santander'),
    ('63', 'Quindío'),
    ('66', 'Risaralda'),
    ('68', 'Santander'),
    ('70', 'Sucre'),
    ('73', 'Tolima'),
    ('76', 'Valle del Cauca'),
    ('81', 'Arauca'),
    ('85', 'Casanare'),
    ('86', 'Putumayo'),
    ('88', 'Archipiélago de San Andrés, Providencia y Santa Catalina'),
    ('91', 'Amazonas'),
    ('94', 'Guainía'),
    ('95', 'Guaviare'),
    ('97', 'Vaupés'),
    ('99', 'Vichada'),
]

# Municipios capitales (código_municipio, nombre, código_departamento)
CAPITALES = [
    ('05001', 'Medellín',         '05'),
    ('08001', 'Barranquilla',     '08'),
    ('11001', 'Bogotá D.C.',      '11'),
    ('13001', 'Cartagena',        '13'),
    ('15001', 'Tunja',            '15'),
    ('17001', 'Manizales',        '17'),
    ('18001', 'Florencia',        '18'),
    ('19001', 'Popayán',          '19'),
    ('20001', 'Valledupar',       '20'),
    ('23001', 'Montería',         '23'),
    ('25001', 'Agua de Dios',     '25'),
    ('27001', 'Quibdó',           '27'),
    ('41001', 'Neiva',            '41'),
    ('44001', 'Riohacha',         '44'),
    ('47001', 'Santa Marta',      '47'),
    ('50001', 'Villavicencio',    '50'),
    ('52001', 'Pasto',            '52'),
    ('54001', 'Cúcuta',           '54'),
    ('63001', 'Armenia',          '63'),
    ('66001', 'Pereira',          '66'),
    ('68001', 'Bucaramanga',      '68'),
    ('70001', 'Sincelejo',        '70'),
    ('73001', 'Ibagué',           '73'),
    ('76001', 'Cali',             '76'),
    ('81001', 'Arauca',           '81'),
    ('85001', 'Yopal',            '85'),
    ('86001', 'Mocoa',            '86'),
    ('88001', 'San Andrés',       '88'),
    ('91001', 'Leticia',          '91'),
    ('94001', 'Inírida',          '94'),
    ('95001', 'San José del Guaviare', '95'),
    ('97001', 'Mitú',             '97'),
    ('99001', 'Puerto Carreño',   '99'),
]


class Command(BaseCommand):
    help = 'Carga departamentos y municipios DANE (idempotente). Acepta --csv para municipios completos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default=None,
            help='Ruta al CSV con municipios completos (codigo_dane_mun,nombre,codigo_dane_dep)',
        )

    def handle(self, *args, **options):
        self._cargar_departamentos()
        csv_path = options.get('csv')
        if csv_path:
            self._cargar_municipios_csv(csv_path)
        else:
            self._cargar_capitales()
            self.stdout.write(
                self.style.WARNING(
                    '\nSolo se cargaron capitales. Para municipios completos usa --csv=ruta.csv'
                )
            )

    def _cargar_departamentos(self):
        self.stdout.write('Cargando departamentos...')
        creados = actualizados = 0
        for codigo, nombre in DEPARTAMENTOS:
            _, created = Departamento.objects.update_or_create(
                codigo_dane=codigo,
                defaults={'nombre': nombre, 'activo': True},
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        self.stdout.write(
            self.style.SUCCESS(f'  Departamentos: {creados} creados, {actualizados} actualizados.')
        )

    def _cargar_capitales(self):
        self.stdout.write('Cargando municipios capitales...')
        creados = actualizados = 0
        for codigo_mun, nombre, codigo_dep in CAPITALES:
            try:
                depto = Departamento.objects.get(codigo_dane=codigo_dep)
            except Departamento.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  Departamento {codigo_dep} no encontrado'))
                continue
            _, created = Municipio.objects.update_or_create(
                codigo_dane=codigo_mun,
                defaults={'nombre': nombre, 'departamento': depto, 'activo': True},
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        self.stdout.write(
            self.style.SUCCESS(f'  Municipios capitales: {creados} creados, {actualizados} actualizados.')
        )

    def _cargar_municipios_csv(self, csv_path: str):
        if not os.path.exists(csv_path):
            raise CommandError(f'El archivo CSV no existe: {csv_path}')

        self.stdout.write(f'Cargando municipios desde {csv_path}...')
        creados = actualizados = errores = 0

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                codigo_mun = row.get('codigo_dane_mun', '').strip()
                nombre = row.get('nombre_municipio', '').strip()
                codigo_dep = row.get('codigo_dane_dep', '').strip()

                if not all([codigo_mun, nombre, codigo_dep]):
                    errores += 1
                    continue

                try:
                    depto = Departamento.objects.get(codigo_dane=codigo_dep)
                except Departamento.DoesNotExist:
                    errores += 1
                    continue

                _, created = Municipio.objects.update_or_create(
                    codigo_dane=codigo_mun,
                    defaults={'nombre': nombre, 'departamento': depto, 'activo': True},
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'  Municipios CSV: {creados} creados, {actualizados} actualizados, {errores} errores.'
            )
        )
