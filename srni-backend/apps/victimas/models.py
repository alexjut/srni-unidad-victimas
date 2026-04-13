"""
Modelo Victima con cifrado de PII y búsqueda por hash SHA-256.
Cumple Ley 1581/2012 (Habeas Data) y CONPES 3995.
"""
import uuid
from django.db import models
from django.conf import settings

from .fields import EncryptedField, sha256_hash


class Victima(models.Model):
    """
    Registro de víctima del conflicto armado.
    Los campos PII se cifran con AES (Fernet) antes de escribir en DB.
    El campo numero_documento_hash permite buscar por documento
    sin descifrar el registro completo.
    """
    ESTADO_RUV = [
        ('INCLUIDO', 'Incluido en RUV'),
        ('NO_INCLUIDO', 'No incluido en RUV'),
        ('EN_PROCESO', 'En proceso de valoración'),
        ('EXCLUIDO', 'Excluido del RUV'),
    ]

    ESTADO_CIVIL = [
        ('SOLTERO', 'Soltero/a'),
        ('CASADO', 'Casado/a'),
        ('UNION_LIBRE', 'Unión libre'),
        ('SEPARADO', 'Separado/a'),
        ('DIVORCIADO', 'Divorciado/a'),
        ('VIUDO', 'Viudo/a'),
    ]

    GENERO = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('NB', 'No binario'),
        ('ND', 'No declara'),
    ]

    PERTENENCIA_ETNICA = [
        ('NINGUNA', 'Ninguna'),
        ('INDIGENA', 'Indígena'),
        ('AFROCOLOMBIANO', 'Afrocolombiano / Afrodescendiente'),
        ('ROM', 'Pueblo Rom / Gitano'),
        ('RAIZAL', 'Raizal del Archipiélago'),
        ('PALENQUERO', 'Palenquero de San Basilio'),
    ]

    # Identificador interno (no expuesto en respuestas de búsqueda)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- Documento: cifrado para almacenamiento, hash para búsqueda ---
    tipo_documento = models.ForeignKey(
        'parametricas.TipoDocumento',
        on_delete=models.PROTECT,
        related_name='victimas',
    )
    numero_documento = EncryptedField()
    numero_documento_hash = models.CharField(max_length=64, db_index=True)

    # --- Nombres y apellidos cifrados ---
    primer_nombre = EncryptedField()
    segundo_nombre = EncryptedField(blank=True, default='')
    primer_apellido = EncryptedField()
    segundo_apellido = EncryptedField(blank=True, default='')

    # --- Fecha de nacimiento cifrada ---
    fecha_nacimiento = EncryptedField()

    # --- Datos demográficos (no PII directa, sin cifrar) ---
    genero = models.CharField(max_length=2, choices=GENERO, db_index=True)
    estado_civil = models.CharField(max_length=15, choices=ESTADO_CIVIL, blank=True)
    pertenencia_etnica = models.CharField(
        max_length=20, choices=PERTENENCIA_ETNICA, default='NINGUNA', db_index=True
    )
    pueblo_indigena = models.CharField(max_length=150, blank=True)
    discapacidad = models.BooleanField(default=False, db_index=True)
    tipo_discapacidad = models.CharField(max_length=100, blank=True)

    # --- Estado en el RUV ---
    estado_ruv = models.CharField(
        max_length=15, choices=ESTADO_RUV, default='EN_PROCESO', db_index=True
    )

    # --- Hechos victimizantes: JSON libre ---
    hechos_victimizantes = models.JSONField(default=list, blank=True)

    # --- Municipio de residencia actual ---
    municipio_residencia = models.ForeignKey(
        'parametricas.Municipio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='victimas_residentes',
    )

    # --- Auditoría ---
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='victimas_registradas',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Víctima'
        verbose_name_plural = 'Víctimas'
        indexes = [
            models.Index(fields=['numero_documento_hash', 'tipo_documento']),
            models.Index(fields=['estado_ruv', 'pertenencia_etnica']),
        ]

    def save(self, *args, **kwargs):
        # Calcular hash del número de documento antes de cifrar.
        # El campo EncryptedField cifra en get_prep_value (al escribir en DB),
        # así que aquí tenemos el plaintext en self.numero_documento.
        if self.numero_documento:
            raw = self.numero_documento
            # Si ya está cifrado (viene de DB), from_db_value ya lo descifró.
            self.numero_documento_hash = sha256_hash(str(raw).strip().upper())
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Víctima {self.numero_documento_hash[:8]}… ({self.tipo_documento_id})'
