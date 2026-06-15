"""
Management command: crear_usuarios_demo

Crea los perfiles y usuarios de prueba para el ambiente de validación
(panel web + APK) con sus respectivos roles. Idempotente.

NOTA: son credenciales de PRUEBA para el ambiente de datos ficticios.
No usar en producción real con datos de víctimas.

Uso:
    python manage.py crear_usuarios_demo
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.autenticacion.models import Perfil, Usuario

# Perfiles: codigo, nombre, (buscar_rni, caracterizar, ver_reportes, administrar)
PERFILES = {
    "ADMINISTRADOR": ("Administrador",          (True,  True,  True,  True)),
    "COORDINADOR":   ("Coordinador / Líder",    (True,  True,  True,  False)),
    "SUPERVISOR":    ("Supervisor",             (True,  False, True,  False)),
    "ENCUESTADOR":   ("Encuestador de Campo",   (True,  True,  False, False)),
}

# Usuarios: codigo, password, nombre, email, perfil, es_administrador
USUARIOS = [
    ("ALEXJUT",    "alexjut1030",   "Javier Alexander Aguilar Castro", "ingaguilarsistemas@gmail.com", "ADMINISTRADOR", True),
    ("BRANDO",     "Brando2026*",   "Brando — Líder Frontend",         "brando@srni.dev",              "COORDINADOR",   False),
    ("SUPERVISOR", "Supervisor2026*", "Oscar Andrés Manosalva García", "supervisor@srni.dev",          "SUPERVISOR",    False),
    ("ENC001",     "SrniTest2026!", "Encuestador de Prueba 1",         "enc001@srni.dev",              "ENCUESTADOR",   False),
    ("ENC002",     "SrniTest2026!", "Encuestador de Prueba 2",         "enc002@srni.dev",              "ENCUESTADOR",   False),
    ("ENC003",     "SrniTest2026!", "Encuestador de Prueba 3",         "enc003@srni.dev",              "ENCUESTADOR",   False),
    ("ENC004",     "SrniTest2026!", "Encuestador de Prueba 4",         "enc004@srni.dev",              "ENCUESTADOR",   False),
    ("ENC005",     "SrniTest2026!", "Encuestador de Prueba 5",         "enc005@srni.dev",              "ENCUESTADOR",   False),
]


class Command(BaseCommand):
    help = "Crea perfiles y usuarios de prueba (admin, líder, supervisor, encuestadores)."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Perfiles
        perfiles = {}
        for codigo, (nombre, (buscar, caract, reportes, admin)) in PERFILES.items():
            perfil, _ = Perfil.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "puede_buscar_rni": buscar,
                    "puede_caracterizar": caract,
                    "puede_ver_reportes": reportes,
                    "puede_administrar": admin,
                    "activo": True,
                },
            )
            perfiles[codigo] = perfil
            self.stdout.write(f"  perfil {codigo}: ok")

        # 2) Usuarios
        for codigo, password, nombre, email, perfil_cod, es_admin in USUARIOS:
            perfil = perfiles[perfil_cod]
            try:
                u = Usuario.objects.get(codigo_usuario=codigo)
                u.nombre_completo = nombre
                u.email = email
                u.perfil = perfil
                u.es_admin = es_admin
                u.is_superuser = es_admin
                u.activo = True
                u.set_password(password)
                u.save()
                estado = "actualizado"
            except Usuario.DoesNotExist:
                u = Usuario.objects.create_user(
                    codigo_usuario=codigo,
                    password=password,
                    nombre_completo=nombre,
                    email=email,
                    perfil=perfil,
                    activo=True,
                )
                u.es_admin = es_admin
                u.is_superuser = es_admin
                u.save()
                estado = "creado"
            self.stdout.write(self.style.SUCCESS(f"  usuario {codigo} ({perfil_cod}): {estado}"))

        self.stdout.write(self.style.SUCCESS("Usuarios demo listos."))
