"""
Modelos de Encuestas SRNI.

SesionEncuesta: sesión de diligenciamiento del formulario para un hogar.
RespuestaEncuesta: respuesta individual a una pregunta del instrumento.

Diseño:
- Una sesión está vinculada a un Hogar + Instrumento (versión exacta del formulario).
- Las respuestas quedan ancladas al Instrumento vigente al momento de la captura
  (trazabilidad documental — Ley 1581, auditoría UARIV).
- instrumento y ruta_entrevista son dos ejes INDEPENDIENTES:
    · instrumento: TERRITORIAL, ASISTENCIA, BUENAVENTURA, etc. (el caracterizador lo elige)
    · ruta_entrevista: GENERAL, ACCIONES_CONSTITUCIONALES, etc. (condición de la entrevista)
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
        ('INICIADA',    'Iniciada'),
        ('EN_PROGRESO', 'En progreso'),
        ('COMPLETADA',  'Completada'),
        ('SUSPENDIDA',  'Suspendida — sin finalizar'),
    ]

    # Rutas de entrevista — eje independiente del instrumento (Manual UARIV §4)
    RUTA_ENTREVISTA = [
        ('GENERAL',                   'General — caracterización ordinaria'),
        ('ACCIONES_CONSTITUCIONALES', 'Acciones constitucionales'),
        ('MODIFICACION_NUCLEO',       'Modificación de núcleo familiar'),
        ('ESPECIAL',                  'Ruta especial — población diferencial'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    hogar = models.ForeignKey(
        'hogares.Hogar',
        on_delete=models.PROTECT,
        related_name='sesiones',
    )
    # FK a Instrumento (codigo + version): garantiza que las respuestas
    # queden ancladas al instrumento exacto vigente al momento de la captura.
    instrumento = models.ForeignKey(
        'formulario.Instrumento',
        on_delete=models.PROTECT,
        related_name='sesiones',
    )
    ruta_entrevista = models.CharField(
        max_length=30, choices=RUTA_ENTREVISTA, default='GENERAL', db_index=True,
        help_text='Ruta de entrevista — independiente del instrumento (Manual UARIV §4).',
    )
    encuestador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sesiones_encuesta',
    )

    # Sprint 19 — Ubicación de atención (metadata del encuestador, no de la
    # víctima). Reemplaza el viejo capítulo "INFORMACIÓN GENERAL" del APK
    # original. Las 4 FKs forman una cascada UARIV:
    #   direccion_territorial  → departamento_atencion  → municipio_atencion
    #   direccion_territorial  → punto_atencion
    direccion_territorial = models.ForeignKey(
        'parametricas.DireccionTerritorial',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='sesiones',
    )
    departamento_atencion = models.ForeignKey(
        'parametricas.Departamento',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='sesiones_atencion',
    )
    municipio_atencion = models.ForeignKey(
        'parametricas.Municipio',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='sesiones_atencion',
    )
    punto_atencion = models.ForeignKey(
        'parametricas.PuntoAtencion',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='sesiones',
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
            models.Index(fields=['instrumento', 'ruta_entrevista']),
        ]

    def __str__(self):
        return f'Sesión {self.id} — {self.hogar_id} [{self.estado}] {self.porcentaje_completado}%'

    def recalcular_porcentaje(self) -> int:
        """
        Calcula el porcentaje de preguntas obligatorias respondidas.
        Solo cuenta preguntas activas y obligatorias del instrumento vigente.
        """
        from apps.formulario.models import Pregunta

        total = Pregunta.objects.filter(
            capitulo__instrumento=self.instrumento,
            obligatoria=True,
            activa=True,
        ).count()

        if total == 0:
            return 0

        respondidas = self.respuestas.filter(
            pregunta__obligatoria=True,
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
        return f'[{self.pregunta.codigo_externo}] → "{self.valor[:40]}"'
