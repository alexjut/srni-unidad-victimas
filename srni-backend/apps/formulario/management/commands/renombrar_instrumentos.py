"""
Sprint 20 — Renombrar instrumentos con nombres descriptivos.

Los nombres oficiales en BD venían muy escuetos ("Perfil Asistencia",
"Perfil Territorial") y el encuestador no sabía cuál elegir. Hallazgo
de Javier (2026-05-26): "no saben cuál es ese".

Este comando aplica nombres descriptivos a los 8 instrumentos sin tocar
sus códigos (TERRITORIAL, ASISTENCIA, etc.) — el código sigue siendo el
identificador estable para el motor y para los bundles.

Uso:
    python manage.py renombrar_instrumentos

Idempotente: usa .update() por codigo.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.formulario.models import Instrumento


NOMBRES = {
    'ASISTENCIA':         'Asistencia humanitaria',
    'TERRITORIAL':        'Caracterización territorial',
    'BUENAVENTURA':       'Buenaventura — Sentencia T-045',
    'SAN_ANDRES':         'San Andrés, Providencia y Santa Catalina',
    'TELEFONICO':         'Entrevista telefónica',
    'URBANO_ETNICO':      'Urbano étnico',
    'RURAL_ETNICO':       'Rural étnico',
    'VICTIMAS_EXTERIOR':  'Víctimas en el exterior',
}


class Command(BaseCommand):
    help = 'Renombra los 8 instrumentos con nombres descriptivos para el encuestador.'

    @transaction.atomic
    def handle(self, *args, **options):
        actualizados = 0
        no_encontrados = []

        for codigo, nuevo_nombre in NOMBRES.items():
            n = Instrumento.objects.filter(codigo=codigo).update(nombre=nuevo_nombre)
            if n:
                self.stdout.write(f'  {codigo:20s} -> "{nuevo_nombre}"')
                actualizados += n
            else:
                no_encontrados.append(codigo)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'{actualizados} instrumentos renombrados.'))
        if no_encontrados:
            self.stdout.write(self.style.WARNING(
                f'No encontrados en BD: {no_encontrados}'
            ))
        self.stdout.write(self.style.WARNING(
            'Corre `python manage.py exportar_a_mobile` para regenerar los bundles.'
        ))
