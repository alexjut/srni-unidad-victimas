"""Desactiva (activo=False) una versión de instrumento sin borrarla.

Se usa para retirar versiones antiguas de PROD cuando entra una nueva
(ej. TERRITORIAL V7 al publicar V8) sin perder su histórico ni las
caracterizaciones ancladas a ella.

Ejemplos:
    python manage.py desactivar_instrumento --codigo TERRITORIAL --version V7
    python manage.py desactivar_instrumento --codigo TERRITORIAL --version V7 --vigente-hasta 2026-07-05
    python manage.py desactivar_instrumento --codigo TERRITORIAL --version V7 --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.formulario.models import Instrumento


class Command(BaseCommand):
    help = "Desactiva (activo=False) una versión de instrumento, sin borrarla."

    def add_arguments(self, parser):
        parser.add_argument("--codigo", required=True, help="Código del instrumento (ej: TERRITORIAL)")
        # OJO: --version lo reserva Django (muestra la versión de Django) → usar --ver.
        parser.add_argument("--ver", dest="version", required=True, help="Versión a desactivar (ej: V7)")
        parser.add_argument(
            "--vigente-hasta",
            dest="vigente_hasta",
            help="Opcional YYYY-MM-DD: además fija vigente_hasta para cerrar la vigencia.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Muestra qué haría sin persistir.")

    def handle(self, *args, **opts):
        codigo, version = opts["codigo"], opts["version"]
        try:
            instr = Instrumento.objects.get(codigo=codigo, version=version)
        except Instrumento.DoesNotExist:
            raise CommandError(f"No existe instrumento {codigo}-{version}.")

        vh = None
        if opts.get("vigente_hasta"):
            try:
                vh = date.fromisoformat(opts["vigente_hasta"])
            except ValueError:
                raise CommandError("--vigente-hasta debe ser YYYY-MM-DD.")

        estado = f"activo={instr.activo}, vigente_hasta={instr.vigente_hasta}"
        if opts["dry_run"]:
            self.stdout.write(f"[dry-run] {codigo}-{version}: {estado} -> activo=False"
                              + (f", vigente_hasta={vh}" if vh else ""))
            return

        instr.activo = False
        if vh:
            instr.vigente_hasta = vh
        instr.save(update_fields=["activo"] + (["vigente_hasta"] if vh else []) + ["actualizado"])
        self.stdout.write(self.style.SUCCESS(
            f"OK {codigo}-{version} desactivado (antes: {estado})."
        ))
