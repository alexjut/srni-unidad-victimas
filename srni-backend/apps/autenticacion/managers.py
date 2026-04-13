from django.contrib.auth.models import BaseUserManager


class UsuarioManager(BaseUserManager):
    """Manager para el modelo Usuario con codigo_usuario como campo de login."""

    def create_user(self, codigo_usuario, email, nombre_completo, password=None, **extra_fields):
        if not codigo_usuario:
            raise ValueError('El código de usuario es obligatorio.')
        if not email:
            raise ValueError('El email es obligatorio.')

        email = self.normalize_email(email)
        user = self.model(
            codigo_usuario=codigo_usuario.strip().upper(),
            email=email,
            nombre_completo=nombre_completo,
            **extra_fields,
        )
        user.set_password(password)  # Django aplica Argon2 automáticamente
        user.save(using=self._db)
        return user

    def create_superuser(self, codigo_usuario, email, nombre_completo, password=None, **extra_fields):
        extra_fields.setdefault('es_admin', True)
        extra_fields.setdefault('activo', True)

        if not extra_fields.get('es_admin'):
            raise ValueError('El superusuario debe tener es_admin=True.')

        return self.create_user(codigo_usuario, email, nombre_completo, password, **extra_fields)
