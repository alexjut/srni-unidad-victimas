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
        ('INCLUIDO',      'Incluido en RUV'),
        ('NO_INCLUIDO',   'No incluido en RUV'),
        ('EN_PROCESO',    'En proceso de valoración'),
        ('EXCLUIDO',      'Excluido del RUV'),
        # Alta manual en campo: la persona NO está en el padrón descargado, y eso
        # NO significa que no esté en el RUV. 1,88 M de víctimas incluidas quedaron
        # fuera del padrón por falta de identidad en la .9 (ver
        # docs/oracle-legacy-padron/hallazgos_identidad_padron.md). Marcarlas
        # 'NO_INCLUIDO' les grabaría un estado falso que viaja al hogar y a los
        # reportes; este valor dice lo que sí se sabe y deja la condición abierta.
        ('NO_VERIFICADO', 'No verificado — no está en el padrón descargado'),
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
    # Opcional a propósito (2026-07-29): en la fuente hay **1.126.615 personas
    # (14,5 %) sin tipo de documento registrado**. Con el campo obligatorio, cargarlas
    # exigía inventarles un tipo —asumir CC, que serían el ~90 %— o dejarlas fuera del
    # padrón. Ninguna de las dos es aceptable: la primera afirma un documento que
    # nadie verificó, la segunda vuelve invisible a un millón de víctimas.
    #
    # NULL aquí significa exactamente "la fuente no lo trae", que es la verdad. Esas
    # personas se encuentran por `numero_documento_hash_sin_tipo`, con aviso al
    # encuestador para que verifique.
    tipo_documento = models.ForeignKey(
        'parametricas.TipoDocumento',
        on_delete=models.PROTECT,
        related_name='victimas',
        null=True, blank=True,
    )
    numero_documento = EncryptedField()
    # Hash de IDENTIDAD: '<tipo>|<numero>'. Es la llave de búsqueda normal.
    numero_documento_hash = models.CharField(max_length=64, db_index=True)
    # Hash de RESPALDO: solo el número, sin el tipo.
    #
    # Existe por un problema medido en la fuente (2026-07-29): **1.126.615 personas
    # del padrón (14,5 %) no tienen tipo de documento registrado**. Con solo el hash
    # de identidad, esas personas serían INENCONTRABLES — el encuestador escribe
    # "CC + número" y la llave nunca coincide.
    #
    # La alternativa era inventarles el tipo (asumir CC, que serían el ~90 %). No se
    # hace: sería afirmar un documento que nadie verificó. En cambio se indexa también
    # por número solo, y la búsqueda cae a este índice cuando la identidad no da
    # resultado, avisando al encuestador de que verifique.
    numero_documento_hash_sin_tipo = models.CharField(
        max_length=64, db_index=True, blank=True, default='',
        help_text='SHA-256 solo del número, para encontrar personas cuyo tipo de '
                  'documento no está registrado en la fuente.',
    )

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
            from .repository.base import doc_hash, num_hash
            tipo = self.tipo_documento.codigo if self.tipo_documento_id else ''
            self.numero_documento_hash = doc_hash(tipo, str(self.numero_documento))
            # Índice de respaldo para quien no tiene tipo registrado (ver el campo).
            self.numero_documento_hash_sin_tipo = num_hash(str(self.numero_documento))
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


class ColisionDocumento(models.Model):
    """
    Un número de documento que aparece en más de una fila del padrón, con el
    veredicto de **qué** es esa repetición. Una fila por documento en conflicto
    (~768 mil), no por víctima.

    ─── Por qué existe ───────────────────────────────────────────────────────
    En el padrón real, 768.096 documentos de 4.928.725 están repetidos. Antes de
    medirlo se asumía que eran colisiones de identidad —dos personas con el mismo
    número—. Medido el 2-ago sobre la base de producción, no lo son:

      * **92 %** de los grupos son **una sola persona** repetida en el Oracle de
        origen, con nombre y fecha de nacimiento idénticos. El caso extremo:
        el documento `1089290511` aparece **505 veces**, siempre ALBA TAPIA
        RODRIGUEZ, con 504 `cons_persona` distintos.
      * **5 %** son la misma persona con el nombre mal escrito o la fecha
        distinta (ERIKA/ERICA, LUS/LUZ, SUESCUN ECHEVERRY/ECHEVERY).
      * **3 %** sí son **personas distintas** compartiendo documento.
      * Aparte, hay documentos que no identifican a nadie: `99` sale 4.297 veces
        con 3.780 nombres distintos, `0` sale 1.194 veces. Son valores de relleno.

    Tratarlos a todos igual es lo que hacía daño en las dos puntas: colapsarlos a
    ciegas (lo que hacía `INSERT OR REPLACE` en el padrón offline) borra a las
    personas distintas del 3 %; y pedir confirmación en todos —el 409 de la
    búsqueda— le pone una pregunta al encuestador en el 92 % de los casos en que
    no hay nada que decidir.

    ─── Cómo se clasifica ────────────────────────────────────────────────────
    Emparejamiento **determinístico y explicable**, no un modelo: se normaliza el
    nombre (mayúsculas, sin tildes, sin puntuación) y se agrupa por
    (nombre, fecha de nacimiento); las variantes ortográficas se unen cuando los
    apellidos coinciden y la fecha también. Es auditable —se puede decir por qué
    dos filas quedaron juntas— y a esta escala no hace falta más. Si algún día
    hiciera falta, el paso siguiente del oficio es Fellegi-Sunter con umbral y
    revisión humana de la franja gris; el resultado seguiría cayendo en esta tabla.

    ─── Qué NO hace ──────────────────────────────────────────────────────────
    **No fusiona ni borra filas de `Victima`.** Es la regla de oro del oficio
    (*link, don't merge*): el registro original se conserva y esta tabla es un
    dato **derivado y recalculable**. Si la clasificación resulta equivocada, se
    corrige el criterio y se vuelve a correr; ninguna víctima se perdió por el
    camino.
    """
    CLASE = [
        ('DUPLICADO_FUENTE', 'Una sola persona, repetida en la fuente'),
        ('VARIANTE_NOMBRE',  'Una sola persona, con el nombre o la fecha mal escritos'),
        ('AMBIGUO',          'Personas distintas que comparten el documento'),
        ('NO_IDENTIFICANTE', 'Valor de relleno: no identifica a nadie'),
    ]

    doc_hash = models.CharField(
        max_length=64, primary_key=True,
        help_text='SHA-256 canónico de (tipo, número) — la misma llave que usa la búsqueda.')

    clase = models.CharField(max_length=20, choices=CLASE, db_index=True)

    filas = models.PositiveIntegerField(
        help_text='Cuántas filas de Victima comparten este documento.')
    personas = models.PositiveIntegerField(
        help_text='Cuántas personas distintas se reconocieron entre esas filas. '
                  '1 = duplicado; >1 = ambiguo; 0 = no identificante.')

    victima_preferida = models.ForeignKey(
        'Victima', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+',
        help_text='Cuando es una sola persona: la fila más completa, la que se '
                  'muestra y la que va al padrón offline (survivorship). Null si '
                  'es ambiguo — ahí no elegimos nosotros.')

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Colisión de documento'
        verbose_name_plural = 'Colisiones de documento'
        indexes = [
            models.Index(fields=['clase', 'personas']),
        ]

    def __str__(self):
        return f'{self.doc_hash[:8]}… {self.clase} ({self.filas} filas → {self.personas} personas)'

    @property
    def requiere_confirmacion(self) -> bool:
        """
        Si el encuestador tiene que decidir. Lo único que la UI necesita saber.

        `NO_IDENTIFICANTE` también lo requiere, pero por el motivo contrario: no hay
        a quién elegir: el documento no sirve para identificar y la persona hay que
        verificarla por otra vía.
        """
        return self.clase in ('AMBIGUO', 'NO_IDENTIFICANTE')


class CargaPadron(models.Model):
    """
    Bitácora de cada carga del padrón desde el Oracle legacy.

    Por qué existe: sin esto, "el padrón" es un estado sin historia — nadie sabe de
    qué corte salió, cuándo, ni qué se descartó por el camino. Con la bitácora se
    puede reprocesar sin volver a preguntar a `.9`, comparar dos cargas y responder
    "¿por qué esta persona no aparece?" mirando los descartes en vez de adivinando.

    No guarda PII: solo contadores y el motivo agregado de los descartes.
    """
    ESTADO = [
        ('EN_CURSO',   'En curso'),
        ('COMPLETADA', 'Completada'),
        ('FALLIDA',    'Fallida'),
        ('SIMULADA',   'Simulada (dry-run, no escribió)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    iniciada_en = models.DateTimeField(auto_now_add=True)
    terminada_en = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADO, default='EN_CURSO')

    origen = models.CharField(
        max_length=200, blank=True,
        help_text='DSN y tablas de las que se leyó (sin credenciales).')

    leidas = models.PositiveIntegerField(default=0)
    creadas = models.PositiveIntegerField(default=0)
    actualizadas = models.PositiveIntegerField(default=0)
    descartadas = models.PositiveIntegerField(default=0)
    sin_tipo_documento = models.PositiveIntegerField(
        default=0,
        help_text='Personas cargadas sin tipo de documento (la fuente no lo trae). '
                  'Se encuentran por el índice de respaldo.')

    motivos_descarte = models.JSONField(
        default=dict, blank=True,
        help_text='{motivo: cuántas}. Agregado, sin datos de personas.')
    detalle = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Carga de padrón'
        verbose_name_plural = 'Cargas de padrón'
        ordering = ['-iniciada_en']

    def __str__(self):
        return f'Carga {self.iniciada_en:%Y-%m-%d %H:%M} — {self.estado} ({self.leidas:,} leídas)'
