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
    # Flag propio y no reutilizar `puede_ver_reportes`: DOCUMENTADOR también lo
    # tiene, y ese perfil se creó explícitamente sin poder alterar la
    # caracterización de una víctima. Habilitar una excepción de vigencia es
    # alterarla —levanta el bloqueo de los dos años—, así que colgarlo de
    # reportes le daría por la puerta de atrás justo lo que se le negó de frente.
    puede_autorizar_excepciones = models.BooleanField(
        default=False,
        verbose_name='puede autorizar excepciones de vigencia',
        help_text=(
            'Habilitar desde el front la actualización de una caracterización '
            'vigente por una ruta que omite la regla de los dos años '
            '(Manual §5.1.1). No lo tiene el encuestador: quien autoriza no es '
            'quien ejecuta.'
        ),
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


class Equipo(models.Model):
    """
    Un supervisor y los encuestadores que le responden, en un área.

    Hasta el 18-sep-2026 «supervisor» era solo un nombre de perfil: no existía
    ninguna relación que dijera a QUIÉN supervisa. Por eso la visibilidad del
    sistema era binaria —o ves lo tuyo, o ves todo el país— y un supervisor no
    podía mirar a los suyos sin ver a los 1.157 encuestadores.

    Se modela como entidad y no como un campo `jefe` en el usuario porque hace
    falta historia: quién supervisaba a quién en agosto es una pregunta que se va
    a hacer, y un campo sobrescrito no la puede responder. Por eso la pertenencia
    vive en `MiembroEquipo`, con fecha de entrada y de salida.

    El área del equipo NO es la Dirección Territorial de cada atención: esa se
    captura en la sesión y dice dónde se atendió a la familia. Son cosas distintas
    y mezclarlas daña los reportes de producción.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=120)
    supervisor = models.ForeignKey(
        'autenticacion.Usuario',
        on_delete=models.PROTECT,
        related_name='equipos_a_cargo',
        help_text='Quien responde por el equipo.',
    )
    direccion_territorial = models.ForeignKey(
        'parametricas.DireccionTerritorial',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='equipos',
        help_text='Área del equipo. Vacío = sin área asignada todavía.',
    )
    activo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'equipo'
        verbose_name_plural = 'equipos'
        ordering = ['nombre']
        db_table = 'auth_equipo'

    def __str__(self):
        return f'{self.nombre} — {self.supervisor.codigo_usuario}'

    def encuestadores(self):
        """Los que pertenecen hoy: los que salieron ya no cuentan."""
        return Usuario.objects.filter(
            pertenencias_equipo__equipo=self,
            pertenencias_equipo__hasta__isnull=True,
        ).distinct()


class MiembroEquipo(models.Model):
    """
    Que una persona pertenezca a un equipo, y desde cuándo.

    `hasta` vacío = pertenece hoy. Al sacarla no se borra la fila: se le pone
    fecha de salida, y así el reporte de agosto sigue sabiendo de quién era.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipo = models.ForeignKey(
        Equipo, on_delete=models.CASCADE, related_name='pertenencias',
    )
    usuario = models.ForeignKey(
        'autenticacion.Usuario', on_delete=models.CASCADE,
        related_name='pertenencias_equipo',
    )
    desde = models.DateField(auto_now_add=True)
    hasta = models.DateField(null=True, blank=True)
    asignado_por = models.ForeignKey(
        'autenticacion.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='asignaciones_equipo_hechas',
    )

    class Meta:
        verbose_name = 'miembro de equipo'
        verbose_name_plural = 'miembros de equipo'
        ordering = ['-desde']
        db_table = 'auth_equipo_miembro'
        constraints = [
            # Una persona en UN solo equipo a la vez. Sin esto los reportes la
            # cuentan dos veces y nadie sabe quién responde por ella.
            models.UniqueConstraint(
                fields=['usuario'],
                condition=models.Q(hasta__isnull=True),
                name='un_equipo_activo_por_usuario',
            ),
        ]

    def __str__(self):
        return f'{self.usuario.codigo_usuario} → {self.equipo.nombre}'
