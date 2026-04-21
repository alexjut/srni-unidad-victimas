"""
Modelos para el módulo de IA — Asistente de voz Gemini.

ConsentimientoIA: registro del consentimiento del encuestador antes de activar la IA.
SesionIA:         metadatos de una sesión con IA activa (sin audio, sin transcripciones).

Principios:
- Jamás se almacena audio ni texto de transcripciones (solo su hash SHA-256).
- El consentimiento es obligatorio antes de cualquier llamada a Gemini.
- Toda llamada a Gemini queda en LogAcceso (acción LLAMADA_GEMINI).
"""
import hashlib
import uuid
from django.db import models
from django.conf import settings


class ConsentimientoIA(models.Model):
    """
    Registro de consentimiento del encuestador para usar el asistente de voz IA.
    Un consentimiento activo (acepto=True) habilita la SesionIA correspondiente.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sesion_encuesta = models.ForeignKey(
        'encuestas.SesionEncuesta',
        on_delete=models.CASCADE,
        related_name='consentimientos_ia',
    )
    encuestador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='consentimientos_ia',
    )

    acepto = models.BooleanField(default=False)

    # SHA-256(UUID_sesion + timestamp ISO) — prueba de que el consentimiento se
    # registró para esa sesión en ese momento exacto.
    firma_digital = models.CharField(max_length=64, blank=True, db_index=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Consentimiento IA'
        verbose_name_plural = 'Consentimientos IA'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['sesion_encuesta', 'acepto']),
            models.Index(fields=['encuestador', 'creado_en']),
        ]

    def save(self, *args, **kwargs):
        if not self.firma_digital:
            raw = f'{self.sesion_encuesta_id}{self.creado_en or ""}'
            self.firma_digital = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        estado = 'ACEPTÓ' if self.acepto else 'RECHAZÓ'
        return f'Consentimiento {estado} — sesión {self.sesion_encuesta_id}'


class SesionIA(models.Model):
    """
    Metadatos de una sesión con asistente IA activo.
    Una sesión_encuesta puede tener como máximo una SesionIA (OneToOne).

    NO almacena audio ni texto de transcripciones.
    transcripcion_hash: SHA-256 del texto procesado — solo para auditoría.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sesion_encuesta = models.OneToOneField(
        'encuestas.SesionEncuesta',
        on_delete=models.CASCADE,
        related_name='sesion_ia',
    )

    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)

    # Número de llamadas a Gemini realizadas en esta sesión
    total_llamadas = models.PositiveIntegerField(default=0)

    # SHA-256 de toda la transcripción acumulada — solo para trazabilidad
    transcripcion_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = 'Sesión IA'
        verbose_name_plural = 'Sesiones IA'
        ordering = ['-inicio']

    def __str__(self):
        return f'SesionIA {self.id} — {self.sesion_encuesta_id} ({self.total_llamadas} llamadas)'
