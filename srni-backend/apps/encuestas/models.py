"""
Modelos de Encuestas SRNI.

SesionEncuesta: sesión de diligenciamiento del formulario PAARI para un hogar.
RespuestaEncuesta: respuesta individual a una pregunta del instrumento.

Diseño:
- Una sesión está vinculada a un Hogar + Instrumento (versión del formulario).
- Las respuestas se guardan de a una (upsert por sesión+pregunta).
- El porcentaje_completado se recalcula al guardar cada respuesta.
- Una sesión COMPLETADA no admite más cambios de respuesta.
"""
import uuid
from django.db import models
from django.conf import settings


class SesionEncuesta(models.Model):
    """Sesión de caracterización de un hogar con un instrumento específico."""

    ESTADO = [
        ('INICIADA',     'Iniciada'),
        ('EN_PROGRESO',  'En progreso'),
        ('COMPLETADA',   'Completada'),
        ('SUSPENDIDA',   'Suspendida — sin finalizar'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    hogar = models.ForeignKey(
        'hogares.Hogar',
        on_delete=models.PROTECT,
        related_name='sesiones',
    )
    instrumento = models.ForeignKey(
        'formulario.Instrumento',
        on_delete=models.PROTECT,
        related_name='sesiones',
    )
    encuestador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sesiones_encuesta',
    )

    estado = models.CharField(
        max_length=15, choices=ESTADO, default='INICIADA', db_index=True
    )
    porcentaje_completado = models.PositiveSmallIntegerField(
        default=0,
        help_text='0–100. Se recalcula al guardar respuestas.',
    )
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sesión de Encuesta'
        verbose_name_plural = 'Sesiones de Encuesta'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hogar', 'estado']),
            models.Index(fields=['encuestador', 'estado']),
        ]

    def __str__(self):
        return f'Sesión {self.id} — {self.hogar_id} [{self.estado}] {self.porcentaje_completado}%'

    def recalcular_porcentaje(self) -> int:
        """
        Calcula el porcentaje de preguntas requeridas respondidas.
        Solo cuenta preguntas activas y requeridas del instrumento.
        """
        from apps.formulario.models import Pregunta

        total = Pregunta.objects.filter(
            tema__instrumento=self.instrumento,
            requerida=True,
            activa=True,
        ).count()

        if total == 0:
            return 0

        respondidas = self.respuestas.filter(
            pregunta__requerida=True,
            pregunta__activa=True,
        ).exclude(valor='').count()

        return int((respondidas / total) * 100)


class RespuestaEncuesta(models.Model):
    """
    Respuesta a una pregunta específica dentro de una sesión.
    unique_together(sesion, pregunta) garantiza exactamente una respuesta por pregunta.
    Para preguntas de selección múltiple, `valor` es un JSON array como string.
    """
    sesion = models.ForeignKey(
        SesionEncuesta, on_delete=models.CASCADE, related_name='respuestas'
    )
    pregunta = models.ForeignKey(
        'formulario.Pregunta', on_delete=models.PROTECT, related_name='respuestas'
    )
    # Para OPCION_UNICA: "A" / Para OPCION_MULTIPLE: '["A","B"]' / Para SINO: "true"
    valor = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Respuesta'
        verbose_name_plural = 'Respuestas'
        unique_together = [('sesion', 'pregunta')]
        ordering = ['pregunta__orden']

    def __str__(self):
        return f'[{self.pregunta.codigo}] → "{self.valor[:40]}"'
