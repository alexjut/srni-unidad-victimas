"""
Comando idempotente para limpiar sesiones y respuestas de prueba.

Borra:
  - Todas las RespuestaEncuesta
  - Todas las SesionEncuesta
  - (opcional --hogares) Todos los MiembroHogar y Hogar

NO borra:
  - Usuarios, perfiles, instrumentos, opciones, paramétricas
  - Víctimas registradas en RNI

Uso:
    python manage.py limpiar_test_encuestas             # borra sesiones+respuestas
    python manage.py limpiar_test_encuestas --hogares   # + hogares y miembros
    python manage.py limpiar_test_encuestas --dry-run   # solo cuenta, no borra
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta
from apps.hogares.models import Hogar, MiembroHogar


class Command(BaseCommand):
    help = 'Limpia sesiones y respuestas de prueba (para reset de testing).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hogares', action='store_true',
            help='También borrar hogares y miembros (reset completo).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo contar — no borrar nada.',
        )

    def handle(self, *args, **opts):
        dry = opts.get('dry_run', False)
        incluir_hogares = opts.get('hogares', False)

        sesiones_n = SesionEncuesta.objects.count()
        respuestas_n = RespuestaEncuesta.objects.count()
        hogares_n = Hogar.objects.count()
        miembros_n = MiembroHogar.objects.count()

        self.stdout.write('═' * 60)
        self.stdout.write('LIMPIAR DATOS DE PRUEBA')
        self.stdout.write('═' * 60)
        self.stdout.write(f'  Sesiones:    {sesiones_n}')
        self.stdout.write(f'  Respuestas:  {respuestas_n}')
        if incluir_hogares:
            self.stdout.write(f'  Hogares:     {hogares_n}')
            self.stdout.write(f'  Miembros:    {miembros_n}')

        if dry:
            self.stdout.write(self.style.WARNING('\nDry-run — nada se borrara.'))
            return

        with transaction.atomic():
            RespuestaEncuesta.objects.all().delete()
            SesionEncuesta.objects.all().delete()
            if incluir_hogares:
                MiembroHogar.objects.all().delete()
                Hogar.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'\nOK. Borrados {respuestas_n} respuestas y {sesiones_n} sesiones.'
            + (f'\nTambien borrados {miembros_n} miembros y {hogares_n} hogares.' if incluir_hogares else '')
        ))
