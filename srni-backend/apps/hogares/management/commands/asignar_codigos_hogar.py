"""
Le pone código a los hogares que quedaron sin él.

`codigo_hogar` se generaba... nunca: era un TODO desde junio. El 18-sep-2026 se midió
contra producción y los 54 hogares tenían el campo vacío. Desde ahora se asigna al
crear el hogar; este comando es para los que ya existen.

El código es la referencia con la que se sigue un hogar entre SICAV, el panel y el
libro de escrituras al sistema legado (`hog_codigo_sicav`). Sin él, nombrar un hogar
era recitar el pedazo inicial de su UUID.

Uso:
    python manage.py asignar_codigos_hogar --dry-run   # cuántos y ejemplos
    python manage.py asignar_codigos_hogar
"""
from django.core.management.base import BaseCommand

from apps.hogares.models import Hogar, generar_codigo_hogar


class Command(BaseCommand):
    help = 'Asigna codigo_hogar a los hogares que lo tienen vacío.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='No escribe: informa cuántos quedarían con código y muestra ejemplos.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']

        pendientes = list(
            Hogar.objects.filter(codigo_hogar='')
            .select_related('creado_por')
            .order_by('created_at')
        )
        if not pendientes:
            self.stdout.write(self.style.SUCCESS('Todos los hogares ya tienen código.'))
            return

        # Los códigos ya usados se cargan una vez: son pocos y evita una consulta
        # por hogar para comprobar unicidad.
        usados = set(
            Hogar.objects.exclude(codigo_hogar='')
            .values_list('codigo_hogar', flat=True)
        )

        asignados = 0
        for hogar in pendientes:
            codigo = ''
            for _ in range(5):
                candidato = generar_codigo_hogar(
                    getattr(hogar.creado_por, 'codigo_usuario', '') or '')
                if candidato not in usados:
                    codigo = candidato
                    break
            if not codigo:
                self.stderr.write(f'  · {hogar.id}: no se pudo generar un código libre')
                continue

            usados.add(codigo)
            asignados += 1
            if asignados <= 10:
                self.stdout.write(f'  · {str(hogar.id)[:8]} → {codigo}')

            if not dry:
                # update() y no save(): no hay que disparar de nuevo la lógica del
                # modelo ni tocar `updated_at` de hogares que nadie modificó.
                Hogar.objects.filter(pk=hogar.pk).update(codigo_hogar=codigo)

        if dry:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] {asignados} de {len(pendientes)} hogares quedarían con código. '
                'Corré el comando sin --dry-run para aplicarlo.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Listo. {asignados} hogares con código nuevo.'))
