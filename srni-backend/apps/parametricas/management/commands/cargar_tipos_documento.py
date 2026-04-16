"""
Management command: cargar_tipos_documento
Carga los 8 tipos de documento usados en el sistema SRNI.
Idempotente: usa get_or_create, seguro de ejecutar múltiples veces.

Uso:
    python manage.py cargar_tipos_documento
"""
from django.core.management.base import BaseCommand
from apps.parametricas.models import TipoDocumento


TIPOS = [
    # (codigo, nombre, aplica_nacionales, aplica_extranjeros)
    ('CC',  'Cédula de Ciudadanía',                True,  False),
    ('TI',  'Tarjeta de Identidad',                True,  False),
    ('RC',  'Registro Civil de Nacimiento',         True,  False),
    ('CE',  'Cédula de Extranjería',                False, True),
    ('PA',  'Pasaporte',                            True,  True),
    ('PE',  'Permiso Especial de Permanencia (PEP)', False, True),
    ('NIT', 'Número de Identificación Tributaria',  True,  False),
    ('NES', 'Número de Entrada al Sistema (Sin documento)', True, True),
]


class Command(BaseCommand):
    help = 'Carga los tipos de documento del sistema SRNI (idempotente)'

    def handle(self, *args, **options):
        creados = 0
        existentes = 0

        for codigo, nombre, nacionales, extranjeros in TIPOS:
            _, created = TipoDocumento.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'aplica_nacionales': nacionales,
                    'aplica_extranjeros': extranjeros,
                    'activo': True,
                },
            )
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'  + {codigo}: {nombre}'))
            else:
                existentes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nTipos de documento: {creados} creados, {existentes} ya existían.'
            )
        )
