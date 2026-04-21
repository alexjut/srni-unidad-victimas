"""
Modelos de Hogares SRNI.

Hogar representa la unidad familiar caracterizada por el encuestador.
MiembroHogar lista a cada integrante del hogar, con referencia opcional
a su registro en la tabla Victima (si ya está en el RNI).

Seguridad:
- Ningún campo PII se almacena aquí en texto plano.
- Los nombres de miembros que NO están en el RNI se cifran con EncryptedField.
- Los miembros que SÍ están en el RNI se referencian via FK a Victima.
"""
import uuid
from django.db import models
from django.conf import settings

from apps.victimas.fields import EncryptedField


class Hogar(models.Model):
    """Unidad familiar objeto de caracterización."""

    ESTADO = [
        ('BORRADOR',  'Borrador — en proceso de captura'),
        ('ACTIVO',    'Activo — caracterización completa'),
        ('ARCHIVADO', 'Archivado'),
    ]

    TIPO_VIVIENDA = [
        ('CASA',        'Casa'),
        ('APARTAMENTO', 'Apartamento'),
        ('CUARTO',      'Cuarto / habitación'),
        ('CAMBUCHE',    'Cambuche / improvisada'),
        ('CONTENEDOR',  'Contenedor / prefabricada'),
        ('OTRO',        'Otro'),
    ]

    CONDICION_OCUPACION = [
        ('PROPIA',    'Propia — pagada'),
        ('PROPIA_PAGANDO', 'Propia — en proceso de pago'),
        ('ARRIENDO',  'Arriendo'),
        ('FAMILIAR',  'Familiar / cedida'),
        ('INVASION',  'Invasión / sin título'),
        ('OTRO',      'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Jefe de hogar — debe ser una víctima registrada en el sistema
    jefe_hogar = models.ForeignKey(
        'victimas.Victima',
        on_delete=models.PROTECT,
        related_name='hogares_como_jefe',
        help_text='Víctima que encabeza el hogar.',
    )
    municipio = models.ForeignKey(
        'parametricas.Municipio',
        on_delete=models.PROTECT,
        related_name='hogares',
        null=True, blank=True,
    )

    # Condiciones de vivienda
    tipo_vivienda = models.CharField(
        max_length=15, choices=TIPO_VIVIENDA, blank=True
    )
    condicion_ocupacion = models.CharField(
        max_length=20, choices=CONDICION_OCUPACION, blank=True
    )
    estrato = models.PositiveSmallIntegerField(
        default=0,
        help_text='0 = no aplica / sin estrato.',
    )
    numero_cuartos = models.PositiveSmallIntegerField(default=0)
    numero_personas = models.PositiveSmallIntegerField(
        default=1,
        help_text='Total de personas que habitan la vivienda.',
    )

    estado = models.CharField(
        max_length=10, choices=ESTADO, default='BORRADOR', db_index=True
    )
    observaciones = models.TextField(blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='hogares_creados',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hogar'
        verbose_name_plural = 'Hogares'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado', 'creado_por']),
            models.Index(fields=['jefe_hogar', 'estado']),
        ]

    def __str__(self):
        return f'Hogar {self.id} — {self.get_estado_display()}'


class MiembroHogar(models.Model):
    """
    Integrante de un hogar.
    Si el miembro está registrado en el RNI, se enlaza via FK a Victima.
    Si NO está en el RNI, sus datos básicos se almacenan cifrados aquí.
    """

    PARENTESCO = [
        ('JEFE',        'Jefe/a de hogar'),
        ('CONYUGE',     'Cónyuge / compañero/a'),
        ('HIJO_A',      'Hijo/a'),
        ('YERNO_NUERA', 'Yerno / nuera'),
        ('NIETO_A',     'Nieto/a'),
        ('PADRE_MADRE', 'Padre / madre'),
        ('HERMANO_A',   'Hermano/a'),
        ('OTRO_PARIENTE', 'Otro pariente'),
        ('NO_PARIENTE', 'Sin parentesco'),
    ]

    GENERO = [
        ('M',  'Masculino'),
        ('F',  'Femenino'),
        ('NB', 'No binario'),
        ('ND', 'No declara'),
    ]

    # Tipo de persona según Manual §5.1.2 — determina qué capítulos aplican
    TIPO_PERSONA = [
        ('AUTORIZADO',  'Autorizado — víctima ≥18 años incluida en RUV'),
        ('TUTOR',       'Tutor — responsable de víctima menor de edad'),
        ('CUIDADOR',    'Cuidador permanente — responsable de adulto dependiente'),
        ('OTRO',        'Otro integrante del hogar'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    hogar = models.ForeignKey(
        Hogar, on_delete=models.CASCADE, related_name='miembros'
    )
    # Si el miembro ya está en el RNI, enlazar directamente:
    victima = models.ForeignKey(
        'victimas.Victima',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='membresías_hogar',
    )

    # Datos básicos cifrados para miembros NO en el RNI
    nombre_completo = EncryptedField(
        blank=True, default='',
        help_text='Nombre del miembro si no está registrado en el RNI (cifrado).',
    )
    tipo_documento = models.ForeignKey(
        'parametricas.TipoDocumento',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    numero_documento = EncryptedField(
        blank=True, default='',
        help_text='Documento del miembro si no está en el RNI (cifrado).',
    )

    parentesco = models.CharField(max_length=20, choices=PARENTESCO)
    genero = models.CharField(max_length=2, choices=GENERO, blank=True)
    # fecha_nacimiento reemplaza 'edad' int para permitir cálculo exacto en validators
    fecha_nacimiento = models.DateField(
        null=True, blank=True,
        help_text='Fecha de nacimiento del miembro (PII — no se indexa).',
    )
    tipo_persona = models.CharField(
        max_length=15, choices=TIPO_PERSONA, default='OTRO',
        help_text='Rol del miembro según §5.1.2 del manual UARIV.',
    )
    incluido_ruv = models.BooleanField(
        default=False,
        help_text='True si el miembro está incluido en el RUV (Registro Único de Víctimas).',
    )
    tiene_discapacidad = models.BooleanField(
        default=False,
        help_text='El miembro tiene algún tipo de discapacidad.',
    )
    tiene_enfermedad_ruinosa = models.BooleanField(
        default=False,
        help_text='El miembro tiene enfermedad ruinosa o catastrófica (Manual §5.1.2).',
    )
    tipo_discapacidad = models.CharField(max_length=100, blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='miembros_registrados',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Miembro del Hogar'
        verbose_name_plural = 'Miembros del Hogar'
        ordering = ['parentesco', 'created_at']

    def __str__(self):
        return f'{self.get_parentesco_display()} — Hogar {self.hogar_id}'
