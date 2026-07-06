"""
Modelos de Hogares SRNI.

Hogar representa la unidad familiar caracterizada por el encuestador.
MiembroHogar lista a cada integrante del hogar, con referencia opcional
a su registro en la tabla Victima (si ya está en el RNI).

Conceptos clave:
- El AUTORIZADO es la víctima titular que autoriza y realiza la entrevista.
  Es el primer miembro del hogar: rol='MIEMBRO' + es_autorizado=True.
- El "jefe de hogar" se captura DENTRO de la entrevista, no aquí.
- estado_inclusion refleja si la persona está registrada como víctima en el RUV.

Seguridad:
- Ningún campo PII se almacena aquí en texto plano.
- Los nombres de miembros que NO están en el RNI se cifran con EncryptedField.
- Los miembros que SÍ están en el RNI se referencian via FK a Victima.
"""
import os
import uuid
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.conf import settings

from apps.victimas.fields import EncryptedField


def ruta_constancia(instance, filename):
    """Ruta de almacenamiento de la constancia tutor/cuidador.

    Sin PII en el nombre: se organiza por hogar y se nombra con el id del
    miembro (UUID). Conserva solo la extensión original.
    """
    ext = os.path.splitext(filename)[1].lower()[:10]
    return f'constancias/{instance.hogar_id}/{instance.id}{ext}'


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
        ('PROPIA',         'Propia — pagada'),
        ('PROPIA_PAGANDO', 'Propia — en proceso de pago'),
        ('ARRIENDO',       'Arriendo'),
        ('FAMILIAR',       'Familiar / cedida'),
        ('INVASION',       'Invasión / sin título'),
        ('OTRO',           'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # TODO: implementar generación automática del código de hogar (prefijo municipio + año + consecutivo)
    codigo_hogar = models.CharField(
        max_length=30, blank=True, default='',
        help_text='Código único de identificación del hogar (generado al confirmar).',
    )

    # Autorizado — víctima titular que autoriza la entrevista de caracterización.
    # El "jefe de hogar" se captura dentro de la entrevista, no aquí.
    autorizado = models.ForeignKey(
        'victimas.Victima',
        on_delete=models.PROTECT,
        related_name='hogares_como_autorizado',
        help_text='Víctima titular que autoriza y realiza la entrevista de caracterización.',
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
            models.Index(fields=['autorizado', 'estado']),
        ]
        constraints = [
            # Regla universal (Sprint 21): una víctima solo puede ser autorizada
            # en UN hogar no archivado a la vez. El constraint en BD cierra la
            # ventana de carrera que la validación de la vista no puede cubrir
            # (p. ej. reintentos simultáneos del móvil al sincronizar).
            UniqueConstraint(
                fields=['autorizado'],
                condition=~Q(estado='ARCHIVADO'),
                name='uniq_hogar_no_archivado_por_autorizado',
            ),
        ]

    def __str__(self):
        return f'Hogar {self.id} — {self.get_estado_display()}'


class MiembroHogar(models.Model):
    """
    Integrante de un hogar.
    Si el miembro está registrado en el RNI, se enlaza via FK a Victima.
    Si NO está en el RNI, sus datos básicos se almacenan cifrados aquí.

    Modelo conceptual:
    - rol: función del integrante (Miembro / Tutor / Cuidador permanente)
    - es_autorizado: marca única — el titular que creó el hogar y hace la entrevista
    - estado_inclusion: si es víctima registrada (INCLUIDO) o no (NO_INCLUIDO)
    """

    # Parentesco familiar — SIN 'JEFE' (el jefe de hogar se captura en la entrevista)
    PARENTESCO = [
        ('CONYUGE',       'Cónyuge / compañero/a'),
        ('HIJO_A',        'Hijo/a'),
        ('YERNO_NUERA',   'Yerno / nuera'),
        ('NIETO_A',       'Nieto/a'),
        ('PADRE_MADRE',   'Padre / madre'),
        ('HERMANO_A',     'Hermano/a'),
        ('OTRO_PARIENTE', 'Otro pariente'),
        ('NO_PARIENTE',   'Sin parentesco'),
    ]

    # Rol funcional en el hogar
    ROL = [
        ('MIEMBRO',             'Miembro del hogar'),
        ('TUTOR',               'Tutor — responsable legal de menor'),
        ('CUIDADOR_PERMANENTE', 'Cuidador permanente — responsable de adulto dependiente'),
    ]

    GENERO = [
        ('M',  'Masculino'),
        ('F',  'Femenino'),
        ('NB', 'No binario'),
        ('ND', 'No declara'),
    ]

    # Tipo de persona según Manual §5.1.2 — códigos compatibles con sistema legado Oracle
    # 5001=Autorizado, 5002=Tutor, 5003=Cuidador permanente, 5004=Otro miembro
    TIPO_PERSONA = [
        ('5001', 'Autorizado — víctima ≥18 años incluida en RUV'),
        ('5002', 'Tutor — responsable legal de víctima menor de edad'),
        ('5003', 'Cuidador permanente — responsable de adulto dependiente'),
        ('5004', 'Otro miembro del hogar'),
    ]

    # Estado de inclusión según verificación contra el RUV
    ESTADO_INCLUSION = [
        ('INCLUIDO',    'Incluido — víctima registrada en el RUV'),
        ('NO_INCLUIDO', 'No incluido — no registrado en el RUV'),
    ]

    FUENTE_ORIGEN = [
        ('ENCUESTADOR', 'Registrado por encuestador en campo'),
        ('RUV',         'Cargado desde RUV'),
        ('LEGADO',      'Migrado del sistema legado (IgedEncuesta)'),
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
        related_name='membresias_hogar',
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

    parentesco = models.CharField(
        max_length=20, choices=PARENTESCO, blank=True, default='',
        help_text='Relación familiar con el autorizado. Vacío para el propio autorizado.',
    )
    genero = models.CharField(max_length=2, choices=GENERO, blank=True)
    # fecha_nacimiento reemplaza 'edad' int para permitir cálculo exacto en validators
    fecha_nacimiento = models.DateField(
        null=True, blank=True,
        help_text='Fecha de nacimiento del miembro (PII — no se indexa).',
    )

    # Rol funcional (nuevo campo principal)
    rol = models.CharField(
        max_length=20, choices=ROL, default='MIEMBRO',
        help_text='Función del integrante en el hogar.',
    )

    # Marca del titular que autoriza la entrevista — solo uno por hogar
    es_autorizado = models.BooleanField(
        default=False,
        help_text='True para el titular que autoriza y realiza la entrevista. Solo uno por hogar.',
    )

    # Estado de inclusión en el RUV
    estado_inclusion = models.CharField(
        max_length=15, choices=ESTADO_INCLUSION, default='NO_INCLUIDO',
        help_text='Indica si la persona está registrada como víctima en el RUV.',
    )

    # Código Oracle para compatibilidad con sistema legado (calculado / opcional)
    tipo_persona = models.CharField(
        max_length=4, choices=TIPO_PERSONA, default='5004',
        help_text='Código Oracle §5.1.2 (compatibilidad legado). Se sincroniza con rol/es_autorizado.',
    )

    fuente_origen = models.CharField(
        max_length=15, choices=FUENTE_ORIGEN, default='ENCUESTADOR',
        help_text='Origen del registro de este miembro.',
    )
    incluido_ruv = models.BooleanField(
        default=False,
        help_text='True si el miembro está incluido en el RUV. Sincronizado con estado_inclusion.',
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

    # Constancia que acredita el rol de TUTOR / CUIDADOR_PERMANENTE (Manual §5.1.2).
    # El móvil la adjunta (expo-document-picker) y bloquea continuar hasta subirla;
    # aquí se persiste el archivo y su metadata. Solo aplica a esos dos roles.
    constancia = models.FileField(
        upload_to=ruta_constancia, null=True, blank=True,
        help_text='Documento que acredita el rol de tutor/cuidador.',
    )
    constancia_nombre = models.CharField(
        max_length=255, blank=True,
        help_text='Nombre original del archivo subido (para mostrar al usuario).',
    )
    constancia_subida_en = models.DateTimeField(
        null=True, blank=True,
        help_text='Momento en que se subió la constancia.',
    )

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
        ordering = ['-es_autorizado', 'rol', 'created_at']
        indexes = [
            models.Index(fields=['hogar', 'es_autorizado']),
            models.Index(fields=['hogar', 'rol']),
            models.Index(fields=['estado_inclusion']),
        ]
        constraints = [
            UniqueConstraint(
                fields=['hogar'],
                condition=Q(es_autorizado=True),
                name='unique_autorizado_por_hogar',
            )
        ]

    def save(self, *args, **kwargs):
        """Sincroniza incluido_ruv y tipo_persona con los campos principales."""
        # incluido_ruv refleja estado_inclusion
        self.incluido_ruv = (self.estado_inclusion == 'INCLUIDO')
        # tipo_persona Oracle: Autorizado=5001, Tutor=5002, Cuidador=5003, Miembro=5004
        if self.es_autorizado:
            self.tipo_persona = '5001'
        elif self.rol == 'TUTOR':
            self.tipo_persona = '5002'
        elif self.rol == 'CUIDADOR_PERMANENTE':
            self.tipo_persona = '5003'
        else:
            self.tipo_persona = '5004'
        super().save(*args, **kwargs)

    def __str__(self):
        rol_display = '★ AUTORIZADO' if self.es_autorizado else self.get_rol_display()
        return f'{rol_display} — Hogar {self.hogar_id}'
