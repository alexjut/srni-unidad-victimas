"""
Management command: crear_instrumentos_base

Crea los registros base de `Instrumento` (con PKs fijos) que esperan los
cargadores de perfiles (cargar_territorial_v7, cargar_buenaventura_v7, etc.).

Reemplaza al antiguo fixture `perfiles_iniciales` que creaba el modelo
`InstrumentoVersion` (eliminado en la migración 0004).

Uso:
    python manage.py crear_instrumentos_base
"""
from datetime import date

from django.core.management.base import BaseCommand

from apps.formulario.models import Instrumento

# (pk, codigo, nombre, version) — los PK coinciden con INSTRUMENTO_PK de cada cargador
INSTRUMENTOS = [
    ("22222222-0001-0001-0001-000000000001", "TERRITORIAL",   "Perfil Territorial",        "V7"),
    ("22222222-0002-0002-0002-000000000002", "BUENAVENTURA",  "Perfil Buenaventura",       "V7"),
    ("22222222-0003-0003-0003-000000000003", "SAN_ANDRES",    "Perfil San Andrés / SAI",   "V7"),
    ("22222222-0004-0004-0004-000000000004", "TELEFONICO",    "Perfil Telefónico SAAH",    "V8"),
    ("22222222-0005-0005-0005-000000000005", "URBANO_ETNICO", "Perfil Urbano Étnico",      "V1"),
    ("22222222-0006-0006-0006-000000000006", "RURAL_ETNICO",  "Perfil Rural Étnico",       "V1"),
]


class Command(BaseCommand):
    help = "Crea los registros base de Instrumento (PKs fijos) para los cargadores de perfiles."

    def handle(self, *args, **options):
        for pk, codigo, nombre, version in INSTRUMENTOS:
            # Idempotente: si ya existe el instrumento con el PK fijo, no se toca.
            if Instrumento.objects.filter(pk=pk).exists():
                self.stdout.write(f"  {codigo}-{version}: existente")
                continue

            # DB inconsistente: mismo (codigo, version) con OTRO pk (p. ej. cargas
            # previas o el fixture antiguo). Evita el IntegrityError de la
            # constraint UNIQUE(codigo, version) al reintentar el despliegue.
            conflicto = (
                Instrumento.objects
                .filter(codigo=codigo, version=version)
                .exclude(pk=pk)
                .first()
            )
            if conflicto is not None:
                if conflicto.capitulos.exists():
                    self.stdout.write(self.style.WARNING(
                        f"  {codigo}-{version}: ya existe con pk distinto ({conflicto.pk}) "
                        f"y tiene capítulos; se conserva. Revisar si los cargadores no "
                        f"lo encuentran por PK."
                    ))
                    continue
                # Aún sin capítulos → realinear al PK fijo que esperan los cargadores.
                conflicto.delete()

            Instrumento.objects.create(
                pk=pk,
                codigo=codigo,
                nombre=nombre,
                version=version,
                vigente_desde=date(2021, 10, 7),
                activo=True,
            )
            self.stdout.write(f"  {codigo}-{version}: creado")
        self.stdout.write(self.style.SUCCESS("Instrumentos base listos."))
