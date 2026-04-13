#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'srni.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Verifica que el entorno virtual esté "
            "activado y que Django esté instalado."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
