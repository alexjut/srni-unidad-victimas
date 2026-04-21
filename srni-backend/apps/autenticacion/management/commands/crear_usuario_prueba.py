"""
Management command: crear_usuario_prueba
Crea un usuario de prueba con perfil completo para test del login móvil.
Idempotente: si el usuario ya existe, actualiza su contraseña.

Uso:
    python manage.py crear_usuario_prueba
    python manage.py crear_usuario_prueba --codigo ENC001 --password MiPassword123!
"""
from django.core.management.base import BaseCommand
from apps.autenticacion.models import Perfil, Usuario


class Command(BaseCommand):
    help = 'Crea usuario de prueba para desarrollo y test del login móvil.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--codigo', type=str, default='ENCUESTADOR001',
            help='Código de usuario (default: ENCUESTADOR001)',
        )
        parser.add_argument(
            '--password', type=str, default='SrniTest2026!',
            help='Contraseña (default: SrniTest2026!)',
        )
        parser.add_argument(
            '--nombre', type=str, default='Encuestador de Prueba',
        )
        parser.add_argument(
            '--email', type=str, default='encuestador@srni.dev',
        )

    def handle(self, *args, **options):
        codigo = options['codigo'].strip().upper()
        password = options['password']
        nombre = options['nombre']
        email = options['email']

        # Perfil completo para pruebas
        perfil, p_creado = Perfil.objects.get_or_create(
            codigo='ENCUESTADOR',
            defaults={
                'nombre': 'Encuestador de Campo',
                'puede_buscar_rni': True,
                'puede_caracterizar': True,
                'puede_ver_reportes': False,
                'puede_administrar': False,
                'activo': True,
            },
        )
        if p_creado:
            self.stdout.write(self.style.SUCCESS(f'  + Perfil creado: {perfil}'))
        else:
            self.stdout.write(f'  · Perfil existente: {perfil}')

        # Usuario
        try:
            usuario = Usuario.objects.get(codigo_usuario=codigo)
            usuario.set_password(password)
            usuario.nombre_completo = nombre
            usuario.email = email
            usuario.perfil = perfil
            usuario.activo = True
            usuario.save()
            self.stdout.write(f'  · Usuario actualizado: {codigo}')
        except Usuario.DoesNotExist:
            usuario = Usuario.objects.create_user(
                codigo_usuario=codigo,
                password=password,
                nombre_completo=nombre,
                email=email,
                perfil=perfil,
                activo=True,
            )
            self.stdout.write(self.style.SUCCESS(f'  + Usuario creado: {codigo}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Usuario listo para login móvil:\n'
            f'  Código:    {codigo}\n'
            f'  Contraseña: {password}\n'
            f'  Perfil:    {perfil.nombre}\n'
        ))
