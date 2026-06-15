import uuid
from django.db import models
from django.conf import settings


class LogAcceso(models.Model):
    """
    Registro de auditoría INMUTABLE.

    Reglas de inmutabilidad:
    - No se puede llamar .save() en un registro existente
    - No se puede llamar .delete()
    - Solo se crea vía el método de clase LogAcceso.registrar()
    - A nivel de BD, el usuario de la app no tiene permisos UPDATE/DELETE sobre esta tabla

    Cumple con el requisito de trazabilidad de la Ley 1581 de 2012.
    """
    ACCIONES = [
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('LOGIN_FALLIDO', 'Intento de login fallido'),
        ('BUSQUEDA_RNI', 'Búsqueda en el RNI'),
        ('VER_VICTIMA', 'Vista de datos de víctima'),
        ('CREAR_HOGAR', 'Creación de hogar'),
        ('AGREGAR_MIEMBRO', 'Miembro agregado al hogar'),
        ('RESPONDER_PREGUNTA', 'Respuesta a pregunta'),
        ('FINALIZAR_ENCUESTA', 'Encuesta finalizada'),
        ('EXPORTAR', 'Exportación de datos'),
        ('CAMBIO_PASSWORD', 'Cambio de contraseña'),
        ('CAMBIO_USUARIO', 'Modificación de usuario'),
        ('ACCESO_DENEGADO', 'Acceso denegado'),
        ('LLAMADA_GEMINI', 'Llamada al asistente IA Gemini'),
        ('CONSENTIMIENTO_IA', 'Consentimiento de uso de IA'),
        ('DESCARGA_APK', 'Descarga de APK móvil'),
    ]

    RESULTADOS = [
        ('EXITO', 'Éxito'),
        ('DENEGADO', 'Acceso denegado'),
        ('ERROR', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='logs_acceso',
        db_constraint=False,
    )
    # Preservar codigo aún si el usuario es eliminado
    codigo_usuario = models.CharField(max_length=50, blank=True, db_index=True)
    accion = models.CharField(max_length=30, choices=ACCIONES, db_index=True)
    recurso = models.CharField(max_length=200, blank=True)
    recurso_id = models.CharField(max_length=100, blank=True, db_index=True)
    ip_origen = models.GenericIPAddressField(default='0.0.0.0')
    user_agent = models.CharField(max_length=500, blank=True)
    resultado = models.CharField(max_length=10, choices=RESULTADOS, db_index=True)
    detalle = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'log de acceso'
        verbose_name_plural = 'logs de acceso'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['codigo_usuario', 'timestamp']),
            models.Index(fields=['accion', 'timestamp']),
        ]

    def __str__(self):
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {self.codigo_usuario} — {self.accion} — {self.resultado}'

    @classmethod
    def registrar(
        cls, *, accion, ip, resultado='EXITO',
        usuario=None, recurso='', recurso_id='',
        user_agent='', detalle=None,
    ):
        """
        Único punto de entrada para crear registros de auditoría.
        Uso: LogAcceso.registrar(accion='LOGIN', ip=request.META.get('REMOTE_ADDR'), usuario=user)
        """
        return cls.objects.create(
            usuario=usuario,
            codigo_usuario=usuario.codigo_usuario if usuario else '',
            accion=accion,
            recurso=recurso,
            recurso_id=str(recurso_id),
            ip_origen=ip or '0.0.0.0',
            user_agent=(user_agent or '')[:500],
            resultado=resultado,
            detalle=detalle or {},
        )

    def save(self, *args, **kwargs):
        # _state.adding=True solo en INSERT — la PK UUID se asigna antes de save()
        # así que no podemos usar `if self.pk` (siempre es True para UUIDField con default).
        if not self._state.adding:
            raise PermissionError(
                'Los registros de auditoría son inmutables. No se puede modificar un LogAcceso existente.'
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(
            'Los registros de auditoría no se pueden eliminar.'
        )
