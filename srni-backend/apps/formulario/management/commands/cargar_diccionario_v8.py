"""
Shim de compatibilidad para cargar_diccionario_v8.

Este comando delega en cargar_perfil, el loader genérico que reemplazó a esta
implementación. Se conserva para no romper scripts ni documentación existente.

Historial:
  - Implementación original: cargaba el perfil ASISTENCIA V8 directamente en Python.
    Usado hasta Sprint 6. Reemplazado en Sprint 7 por cargar_perfil (loader genérico
    con resolución de $ref y corrección del campo no_pregunta).

Uso equivalente (nuevo):
    python manage.py cargar_perfil --perfil ASISTENCIA
    python manage.py cargar_perfil --fixture apps/formulario/fixtures/perfil_asistencia_v8.json
    python manage.py cargar_perfil --fixture apps/formulario/fixtures/perfil_asistencia_v8.json --dry-run
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Shim: delega en cargar_perfil con el fixture ASISTENCIA V8 (idempotente)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="apps/formulario/fixtures/perfil_asistencia_v8.json",
            help="Ruta al fixture JSON (por defecto: perfil_asistencia_v8.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la carga sin persistir.",
        )

    def handle(self, *args, **opts):
        kwargs = {"fixture": opts["fixture"]}
        if opts.get("dry_run"):
            kwargs["dry_run"] = True
        call_command("cargar_perfil", **kwargs)
