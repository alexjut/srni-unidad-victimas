"""
Sprint 19 — Desactiva las 4 preguntas obsoletas de Ubicación de Atención
(DT_ATENCION, DEPTO_ATENCION, PUNTO_ATENCION, MUN_ATENCION) en todos los
instrumentos.

Por qué: estos 4 datos ya no son respuestas del formulario. Pasaron a ser
metadata de la sesión (SesionEncuesta.direccion_territorial, etc.) y se
piden en una pantalla aparte (caracterizar/ubicacion-atencion.tsx).

Mantener las preguntas en BD pero con `activa=False` significa:
  - El exportador `exportar_a_mobile.py` las filtra (línea 76: filter(activa=True)).
  - Las respuestas históricas (si las hay) siguen accesibles para auditoría.
  - Reversible: si se necesita reactivar, basta con activa=True.

Uso:
    python manage.py desactivar_preguntas_atencion
    python manage.py desactivar_preguntas_atencion --revertir  # las reactiva

Idempotente.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.formulario.models import Pregunta


CODIGOS_OBSOLETOS = ['DT_ATENCION', 'DEPTO_ATENCION', 'PUNTO_ATENCION', 'MUN_ATENCION']


class Command(BaseCommand):
    help = 'Desactiva (o reactiva) las preguntas de Ubicación de Atención.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--revertir',
            action='store_true',
            help='Reactiva las preguntas (activa=True) en lugar de desactivarlas.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        revertir = options['revertir']
        nuevo_estado = True if revertir else False
        accion = 'reactivadas' if revertir else 'desactivadas'

        qs = Pregunta.objects.filter(codigo_externo__in=CODIGOS_OBSOLETOS)

        # Reporte previo
        self.stdout.write(f'Preguntas con código en {CODIGOS_OBSOLETOS}:')
        for p in qs.select_related('capitulo__instrumento').order_by(
            'capitulo__instrumento__codigo', 'codigo_externo'
        ):
            self.stdout.write(
                f'  {p.capitulo.instrumento.codigo:<18} '
                f'cap={p.capitulo.codigo:<3} {p.codigo_externo:<16} '
                f'activa={p.activa}'
            )

        actualizadas = qs.update(activa=nuevo_estado)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'{actualizadas} preguntas {accion}.'))
        if not revertir:
            self.stdout.write(self.style.WARNING(
                'Ahora corre `python manage.py exportar_a_mobile` para regenerar los bundles.'
            ))
