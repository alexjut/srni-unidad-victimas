"""
Modelo Victima con cifrado de PII y búsqueda por hash SHA-256.
Cumple Ley 1581/2012 (Habeas Data) y CONPES 3995.
"""
import uuid
from django.db import models
from django.conf import settings

from .fields import EncryptedField, sha256_hash


class CatalogoHechoVictimizante(models.Model):
    """
    Catálogo oficial de hechos victimizantes según Ley 1448/2011.
    # TODO: confirmar códigos y nombres exactos con área funcional (tablas Oracle EMC_VARIABLES / GIC_TIPO_HECHO).
    """
    codigo = models.CharField(max_length=10, unique=True, db_index=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Catálogo Hecho Victimizante'
        verbose_name_plural = 'Catálogo Hechos Victimizantes'
        ordering = ['orden', 'codigo']

    def __str__(self):
        return f'[{self.codigo}] {self.nombre}'


class Victima(models.Model):
    """
    Registro de víctima del conflicto armado.
    Los campos PII se cifran con AES (Fernet) antes de escribir en DB.
    El campo numero_documento_hash permite buscar por documento
    sin descifrar el registro completo.
    """
    ESTADO_RUV = [
        ('INCLUIDO',    'Incluido en RUV'),
        ('NO_INCLUIDO', 'No incluido en RUV'),
        ('EN_PROCESO',  'En proceso de valoración'),
        ('EXCLUIDO',    'Excluido del RUV'),
    ]

    ESTADO_CIVIL = [
        ('SOLTERO',     'Soltero/a'),
        ('CASADO',      'Casado/a'),
        ('UNION_LIBRE', 'Unión libre'),
        ('SEPARADO',    'Separado/a'),
        ('DIVORCIADO',  'Divorciado/a'),
        ('VIUDO',       'Viudo/a'),
    ]

    GENERO = [
        ('M',  'Masculino'),
        ('F',  'Femenino'),
        ('NB', 'No binario'),
        ('ND', 'No declara'),
    ]

    PERTENENCIA_ETNICA = [
        ('NINGUNA',       'Ninguna'),
        ('INDIGENA',      'Indígena'),
        ('AFROCOLOMBIANO','Afrocolombiano / Afrodescendiente'),
        ('ROM',           'Pueblo Rom / Gitano'),
        ('RAIZAL',        'Raizal del Archipiélago'),
        ('PALENQUERO',    'Palenquero de San Basilio'),
    ]

    FUENTE_ORIGEN = [
        ('RUV',           'Registro Único de Víctimas'),
        ('SNARIV',        'SNARIV — sistema interinstitucional'),
        ('LEGADO',        'Migración del sistema legado (IgedEncuesta)'),
        ('MANUAL',        'Registro manual por funcionario'),
        ('REGISTRADURIA', 'Registraduría Nacional del Estado Civil'),
    ]

    ESTADO_VALORACION = [
        ('PENDIENTE',    'Pendiente de valoración'),
        ('EN_REVISION',  'En revisión'),
        ('VALORADO',     'Valorado — incluido'),
        ('RECHAZADO',    'Valoración rechazada'),
    ]

    # Identificador interno (no expuesto en respuestas de búsqueda)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Consecutivo del sistema legado Oracle — facilita trazabilidad en migración
    cons_persona = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text='CONSUSUARIOID del sistema Oracle legado (IgedEncuesta).',
    )

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

    # --- Control de caracterización ---
    habilitado_para_caracterizacion = models.BooleanField(
        default=True, db_index=True,
        help_text='False si la víctima está excluida, fallecida o con restricción administrativa.',
    )
    fecha_ult_caracterizacion = models.DateTimeField(
        null=True, blank=True,
        help_text='Fecha/hora de la última sesión de caracterización completada.',
    )
    fuente_origen = models.CharField(
        max_length=20, choices=FUENTE_ORIGEN, default='RUV', db_index=True,
    )
    estado_valoracion = models.CharField(
        max_length=15, choices=ESTADO_VALORACION, default='PENDIENTE', db_index=True,
    )

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
            models.Index(fields=['habilitado_para_caracterizacion', 'estado_ruv']),
        ]

    def save(self, *args, **kwargs):
        # Calcular hash del número de documento antes de cifrar.
        # El campo EncryptedField cifra en get_prep_value (al escribir en DB),
        # así que aquí tenemos el plaintext en self.numero_documento.
        #
        # ⚠️ El hash lo calcula `repository.base.doc_hash`, NO una fórmula propia.
        # Hasta el 2026-07-29 aquí se hacía `sha256_hash(numero.strip().upper())`
        # —solo el número, en mayúsculas— mientras el repositorio y el padrón
        # descargable buscaban por `doc_hash("<tipo>|<numero>")` en minúsculas y sin
        # puntos ni guiones. **Dos hashes distintos para la misma cosa: la búsqueda
        # por documento no podía encontrar nada.** No se notó porque el repositorio
        # activo era el mock, que busca por diccionario y nunca usa el hash.
        #
        # Regla: una sola definición del hash, y vive en `repository.base`, que es
        # donde la usan el buscador y el generador del padrón.
        if self.numero_documento:
            from .repository.base import doc_hash
            tipo = self.tipo_documento.codigo if self.tipo_documento_id else ''
            self.numero_documento_hash = doc_hash(tipo, str(self.numero_documento))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Víctima {self.numero_documento_hash[:8]}… ({self.tipo_documento_id})'


class HechoVictima(models.Model):
    """
    Relación entre una víctima y los hechos victimizantes que sufrió.
    Permite reportes agregados por tipo de hecho (Ley 1448 Art. 3).
    """
    FUENTE_REGISTRO = [
        ('RUV',         'Registro Único de Víctimas'),
        ('DECLARACION', 'Declaración ante Ministerio Público'),
        ('SNARIV',      'Reporte SNARIV'),
        ('MANUAL',      'Registro manual por funcionario'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    victima = models.ForeignKey(
        Victima,
        on_delete=models.CASCADE,
        related_name='hechos_victimizantes',
    )
    hecho = models.ForeignKey(
        CatalogoHechoVictimizante,
        on_delete=models.PROTECT,
        related_name='victimas_afectadas',
    )
    fecha_hecho = models.DateField(
        null=True, blank=True,
        help_text='Fecha en que ocurrió el hecho victimizante.',
    )
    lugar_hecho = models.ForeignKey(
        'parametricas.Municipio',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='hechos_ocurridos',
    )
    fuente = models.CharField(max_length=15, choices=FUENTE_REGISTRO, default='RUV')
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Hecho Victimizante'
        verbose_name_plural = 'Hechos Victimizantes'
        # Una víctima puede tener el mismo tipo de hecho más de una vez
        # (e.g., desplazado dos veces), así que no se pone unique_together.
        indexes = [
            models.Index(fields=['victima', 'hecho']),
        ]
        ordering = ['fecha_hecho', 'hecho']

    def __str__(self):
        return f'{self.victima} — {self.hecho}'
