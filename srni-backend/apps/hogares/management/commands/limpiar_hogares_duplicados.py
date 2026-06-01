"""
Limpieza de hogares duplicados por autorizado.

Regla de negocio: una víctima solo puede ser autorizada en un hogar a la vez.
Durante pruebas se crearon múltiples hogares con el mismo autorizado.
Este comando deja solo el hogar con más sesiones por víctima y elimina el resto.

Uso (dry-run por defecto):
    python manage.py limpiar_hogares_duplicados            # solo muestra qué haría
    python manage.py limpiar_hogares_duplicados --aplicar  # ejecuta la eliminación
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from apps.hogares.models import Hogar, MiembroHogar
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta
from apps.victimas.models import Victima


class Command(BaseCommand):
    help = 'Limpia hogares duplicados — deja solo el de más sesiones por víctima.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--aplicar', action='store_true',
            help='Ejecuta la eliminación. Sin esta flag, solo muestra qué haría.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        aplicar = options['aplicar']
        modo = self.style.WARNING('APLICAR (DESTRUCTIVO)') if aplicar else self.style.NOTICE('DRY-RUN (solo muestra)')
        self.stdout.write(f'Modo: {modo}')
        self.stdout.write('')

        victimas_con_dup = (
            Victima.objects
            .annotate(n_hogares=Count('hogares_como_autorizado'))
            .filter(n_hogares__gt=1)
        )

        total_eliminados = 0
        for v in victimas_con_dup:
            hogares = list(
                Hogar.objects
                .filter(autorizado=v)
                .annotate(n_ses=Count('sesiones'))
                .order_by('-n_ses', '-created_at')
            )
            # Mantener el primero (más sesiones, más reciente como desempate)
            mantener = hogares[0]
            eliminar = hogares[1:]

            self.stdout.write(self.style.NOTICE(
                f'Víctima {v.primer_nombre} {v.primer_apellido} '
                f'({v.numero_documento[:4]}***) — {len(hogares)} hogares:'
            ))
            self.stdout.write(f'  MANTENER: {str(mantener.id)[:8]} (sesiones={mantener.n_ses})')
            for h in eliminar:
                n_miembros = MiembroHogar.objects.filter(hogar=h).count()
                n_sesiones = SesionEncuesta.objects.filter(hogar=h).count()
                n_resp = RespuestaEncuesta.objects.filter(sesion__hogar=h).count()
                self.stdout.write(
                    f'  ELIMINAR: {str(h.id)[:8]} '
                    f'(miembros={n_miembros}, sesiones={n_sesiones}, respuestas={n_resp})'
                )

                if aplicar:
                    # Orden de eliminación: respuestas → sesiones → miembros → hogar
                    RespuestaEncuesta.objects.filter(sesion__hogar=h).delete()
                    SesionEncuesta.objects.filter(hogar=h).delete()
                    MiembroHogar.objects.filter(hogar=h).delete()
                    h.delete()
                    total_eliminados += 1
            self.stdout.write('')

        if aplicar:
            self.stdout.write(self.style.SUCCESS(f'OK. {total_eliminados} hogares eliminados.'))
        else:
            self.stdout.write(self.style.WARNING(
                'Sin cambios (dry-run). Re-ejecutá con --aplicar para confirmar.'
            ))
