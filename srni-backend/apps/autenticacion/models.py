import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import UsuarioManager


class Perfil(models.Model):
    """
    Perfil de encuestador con flags de permisos.
    Un perfil agrupa las capacidades de un rol (encuestador de campo,
    coordinador DT, supervisor, administrador).
    """
    codigo = models.CharField(max_length=20, unique=True, verbose_name='código')
    nombre = models.CharField(max_length=100)
    puede_buscar_rni = models.BooleanField(
        default=True,
        verbose_name='puede buscar en el RNI',
        help_text='Buscar víctimas en el Registro Nacional de Información',
    )
    puede_caracterizar = models.BooleanField(
        default=True,
        verbose_name='puede caracterizar',
        help_text='Diligenciar encuestas de caracterización',
    )
    puede_ver_reportes = models.BooleanField(
        default=False,
        verbose_name='puede ver reportes',
        help_text='Acceder al módulo de reportes de producción',
    )
    puede_administrar = models.BooleanField(
        default=False,
        verbose_name='puede administrar',
        help_text='CRUD de usuarios, instrumentos y paramétricas',
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'perfil'
        verbose_name_plural = 'perfiles'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Usuario del sistema (encuestador).
    Reemplaza EMCUSUARIOS del APK original.

    Diferencias críticas respecto al APK:
    - Contraseña gestionada con Argon2 (nunca texto plano)
    - UUID como PK (no secuencial, no predecible)
    - Sin token custom — usa JWT con expiración
    - Vinculado a perfil con permisos granulares
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_usuario = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='código de usuario',
        help_text='Identificador único de login (equivale a IDUSUARIO del APK)',
    )
    nombre_completo = models.CharField(max_length=200, verbose_name='nombre completo')
    email = models.EmailField(unique=True)
    perfil = models.ForeignKey(
        Perfil,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='usuarios',
    )
    activo = models.BooleanField(default=True)
    es_admin = models.BooleanField(
        default=False,
        verbose_name='es administrador',
        help_text='Acceso al panel /admin/ de Django',
    )
    fecha_ultimo_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'codigo_usuario'
    REQUIRED_FIELDS = ['email', 'nombre_completo']

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        db_table = 'auth_usuario'

    def __str__(self):
        return f'{self.codigo_usuario} — {self.nombre_completo}'

    @property
    def is_active(self):
        return self.activo

    @property
    def is_staff(self):
        return self.es_admin

    def puede(self, accion: str) -> bool:
        """Verifica si el usuario tiene un permiso de perfil específico."""
        if not self.perfil or not self.perfil.activo:
            return False
        return getattr(self.perfil, f'puede_{accion}', False)
