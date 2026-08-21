"""
Asigna contraseñas a usuarios existentes desde un CSV, hasheándolas con Argon2.

POR QUÉ EXISTE — el sistema legacy (.NET/IIS + Oracle) guarda las claves como
SHA-512 con una sal que vive en el binario de la app; el propio Oracle solo
compara texto contra texto (`GIC_SP_AUTENTICA_USUARIO`). Ese formato no se puede
recalcular sin la sal, y aunque se pudiera no conviene: SHA-512 es rapidísimo de
crackear. El sistema nuevo usa **Argon2id**, que es el estándar actual.

Como ninguna encuestadora ha entrado nunca (todas con `last_login=None`), no hay
nada que preservar: se asignan claves nuevas y punto.

QUÉ HACE — lee un CSV `codigo_usuario,contraseña`, y por cada fila llama a
`set_password()` (Argon2) sobre el usuario que ya existe. NO crea usuarios: si el
código no está, lo reporta y sigue. Es idempotente: correrlo dos veces con el
mismo archivo deja lo mismo.

CÓMO SE USA (en el servidor):

    # ensayo: dice qué haría, sin tocar nada
    python manage.py cargar_claves claves.csv --dry-run

    # de verdad
    python manage.py cargar_claves claves.csv

FORMATO DEL CSV — dos columnas, sin encabezado obligatorio (si la primera fila
dice `codigo_usuario,password` se ignora). Separador coma o punto y coma:

    KLMUÑOZM,ClaveTemporal2026
    KDCARRIONT;OtraClave2026

SEGURIDAD DE OPERACIÓN — el archivo tiene claves en texto plano: guardalo fuera
del repo, borralo después de correr esto (`shred -u claves.csv`), y no lo subas a
git. El comando avisa al terminar.
"""
import csv

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.autenticacion.models import Usuario


class Command(BaseCommand):
    help = "Asigna contraseñas (Argon2) a usuarios existentes desde un CSV."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="CSV con codigo_usuario,contraseña por línea.")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="No escribe nada: solo dice qué haría y qué filas tienen problemas.",
        )
        parser.add_argument(
            "--sin-validar", action="store_true",
            help="Salta los validadores de Django (mínimo 10 caracteres, claves "
                 "comunes, etc.). Úsalo solo si sabés lo que hacés.",
        )
        parser.add_argument(
            "--solo-activos", action="store_true",
            help="Ignora usuarios inactivos aunque estén en el archivo.",
        )

    def handle(self, *args, **opts):
        ruta = opts["archivo"]
        dry = opts["dry_run"]
        validar = not opts["sin_validar"]
        solo_activos = opts["solo_activos"]

        try:
            filas = self._leer(ruta)
        except OSError as e:
            raise CommandError(f"No se pudo leer el archivo: {e}")

        if not filas:
            raise CommandError("El archivo no tiene ninguna fila utilizable.")

        # Índice de los usuarios que se nombran, en una sola consulta.
        codigos = [c for c, _ in filas]
        usuarios = {u.codigo_usuario: u for u in
                    Usuario.objects.filter(codigo_usuario__in=codigos)}

        aplicadas, saltadas, errores = [], [], []
        # Se resuelve TODO antes de escribir: si una clave no pasa la validación,
        # es mejor enterarse antes de haber cambiado la mitad.
        preparadas = []
        vistos = set()
        for i, (codigo, clave) in enumerate(filas, start=1):
            if codigo in vistos:
                errores.append((i, codigo, "repetido en el archivo"))
                continue
            vistos.add(codigo)

            usuario = usuarios.get(codigo)
            if usuario is None:
                errores.append((i, codigo, "no existe en el sistema"))
                continue
            if solo_activos and not usuario.activo:
                saltadas.append((codigo, "inactivo"))
                continue
            if validar:
                try:
                    validate_password(clave, user=usuario)
                except ValidationError as e:
                    errores.append((i, codigo, "; ".join(e.messages)))
                    continue
            preparadas.append((usuario, clave))

        # Reporte
        self.stdout.write(f"Filas leídas:        {len(filas)}")
        self.stdout.write(f"Listas para aplicar: {len(preparadas)}")
        if saltadas:
            self.stdout.write(self.style.WARNING(f"Saltadas:            {len(saltadas)}"))
        if errores:
            self.stdout.write(self.style.ERROR(f"Con problema:        {len(errores)}"))
            for i, codigo, motivo in errores[:50]:
                self.stdout.write(self.style.ERROR(f"  línea {i} · {codigo or '(vacío)'} → {motivo}"))
            if len(errores) > 50:
                self.stdout.write(self.style.ERROR(f"  … y {len(errores) - 50} más"))

        if dry:
            self.stdout.write(self.style.NOTICE(
                "\n[DRY-RUN] No se escribió nada. Quitá --dry-run para aplicar."))
            return

        if not preparadas:
            raise CommandError("Ninguna fila quedó lista para aplicar. No se escribió nada.")

        # set_password() por usuario. save() actualiza solo el campo password.
        with transaction.atomic():
            for usuario, clave in preparadas:
                usuario.set_password(clave)
                usuario.save(update_fields=["password"])
                aplicadas.append(usuario.codigo_usuario)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ {len(aplicadas)} contraseñas asignadas con Argon2."))
        self.stdout.write(self.style.WARNING(
            f"⚠️  El archivo {ruta} tiene claves en texto plano. Borralo ahora:\n"
            f"    shred -u {ruta}   (o rm {ruta})"))

    @staticmethod
    def _leer(ruta):
        """Devuelve [(codigo, clave), …]. Tolera coma o punto y coma, y un
        encabezado opcional. Ignora líneas vacías y espacios."""
        filas = []
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            muestra = f.read(2048)
            f.seek(0)
            sep = ";" if muestra.count(";") > muestra.count(",") else ","
            for cols in csv.reader(f, delimiter=sep):
                if not cols:
                    continue
                if len(cols) < 2:
                    # una sola columna: fila mal formada, se registra como error
                    filas.append(((cols[0] or "").strip(), ""))
                    continue
                codigo = (cols[0] or "").strip()
                clave = cols[1]  # la clave NO se recorta: un espacio puede ser parte
                if not codigo:
                    continue
                # Saltar un encabezado obvio.
                if codigo.lower() in ("codigo_usuario", "usuario", "codigo") and \
                        clave.strip().lower() in ("password", "contraseña", "clave", "contrasena"):
                    continue
                filas.append((codigo, clave))
        return filas
