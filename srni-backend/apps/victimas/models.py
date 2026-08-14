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

    #: **De dónde salió `estado_ruv`, y por eso cuánto vale.**
    #:
    #: Existe por lo que se midió el 11-ago-2026: el padrón se cargó uniendo
    #: `GIC_PERSONA` con `M_CARACT_TABLA_RA_PER` por `CONS_PERONA`, que resultó ser
    #: **un contador de filas** —1, 2, 3…—, no un identificador de persona. El
    #: estado no quedó "desalineado": la asignación fue aleatoria, y además el
    #: valor se gastó en el `WHERE` que eligió quién entra al padrón, así que las
    #: 5.926.004 filas salieron con `INCLUIDO` constante por construcción.
    #: Ver `docs/oracle-legacy/join_caracterizacion_roto.md`.
    #:
    #: La lección: un estado sin procedencia no se puede auditar. Con este campo,
    #: "no lo sabemos" deja de ser indistinguible de "lo sabemos y es INCLUIDO",
    #: que es exactamente el error que costó cinco millones de filas.
    ESTADO_RUV_FUENTE = [
        # El snapshot mensual del RUV (`PersonaUniverso`), cruzado por hash de
        # documento. Es la fuente fiable: el cruce va por documento, no por un id
        # de otro sistema.
        ('UNIVERSO_RUV',  'Universo del RUV (snapshot mensual)'),
        # `M_CARACT_TABLA_RA_PER` del legado. 🔴 NO USAR para cargas nuevas: es la
        # fuente del defecto. Se conserva como valor para poder marcar lo que
        # venga de ahí si alguna vez se recupera con una llave válida.
        ('LEGACY_CARACT', 'Caracterización del legado — no confiable'),
        # Lo declaró un funcionario en el alta manual, con la persona enfrente.
        ('MANUAL',        'Declarado en campo por el funcionario'),
        # Nadie lo verificó. Es el valor honesto por defecto, y el que llevan las
        # 5,9 M cargadas con el join roto hasta que se recarguen.
        ('SIN_VERIFICAR', 'Sin verificar — nadie lo ha resuelto'),
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
        # La búsqueda ya devolvía este valor (`django_orm.py`, alta desde el
        # universo) pero no estaba en la lista, así que el propio backend producía
        # un payload que su serializer rechazaba con 400. En campo eso se leía
        # como "Revisa la conexión": un error de contrato disfrazado de falla de
        # red, que manda a buscar señal donde no hay nada que buscar.
        #
        # No se homologa a 'RUV' —que también haría pasar la validación— porque
        # es la ÚNICA traza de que la persona vino del universo y nunca fue
        # entrevistada. Son 8,12 M de personas: perder esa distinción las mezcla
        # con quienes sí tienen ficha.
        ('UNIVERSO_RUV',  'Universo del RUV — víctima aún sin caracterizar'),
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
    #
    # ⚠️ `estado_ruv` NUNCA se lee solo: se lee con `estado_ruv_fuente`. Un estado
    # sin procedencia no se puede auditar, y esa es justamente la lección de las
    # 5.926.004 filas que quedaron con `INCLUIDO` sin que nadie lo hubiera
    # verificado. Para saber si el valor vale algo, `es_estado_ruv_confiable`.
    estado_ruv = models.CharField(
        max_length=15, choices=ESTADO_RUV, default='EN_PROCESO', db_index=True
    )
    #: Default `SIN_VERIFICAR` a propósito: quien no diga de dónde sacó el estado,
    #: no lo sabe. Es el valor honesto y el que se quiere ver cuando algo falla.
    estado_ruv_fuente = models.CharField(
        max_length=15, choices=ESTADO_RUV_FUENTE, default='SIN_VERIFICAR',
        db_index=True,
        help_text='De dónde salió el estado RUV. Sin esto, "no lo sabemos" es '
                  'indistinguible de "lo sabemos y está incluido".',
    )
    #: Corte o momento del que viene el estado — p. ej. la fecha del snapshot del
    #: universo. Sirve para responder "¿de cuándo es este dato?" sin adivinar y
    #: para detectar fuentes congeladas, que es lo que pasó con
    #: `GIC_REPORTE_HOGAR`: llevaba desde 2021 sin actualizarse y nadie lo notó.
    estado_ruv_fecha = models.DateField(
        null=True, blank=True,
        help_text='Fecha del corte del que proviene el estado RUV.',
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

    #: Fuentes cuyo estado RUV sí se puede afirmar. `LEGACY_CARACT` NO está: es la
    #: del join roto. `SIN_VERIFICAR` tampoco, por definición.
    FUENTES_RUV_CONFIABLES = frozenset({'UNIVERSO_RUV', 'MANUAL'})

    @property
    def es_estado_ruv_confiable(self) -> bool:
        """
        ¿Se puede afirmar el `estado_ruv` de esta persona?

        Existe para que la pregunta tenga UNA respuesta y no la improvise cada
        pantalla. Antes no se podía ni formular: las 5.926.004 filas decían
        `INCLUIDO` y no había forma de distinguir las verificadas de las que
        heredaron el dato de otra persona — porque eran todas.

        Un `False` acá **no dice que la persona no sea víctima**. Dice que
        nosotros no lo hemos resuelto, que es una afirmación sobre nuestro dato y
        no sobre ella. La diferencia importa cuando el resultado se le muestra a
        alguien que está sentado enfrente del encuestador.
        """
        return self.estado_ruv_fuente in self.FUENTES_RUV_CONFIABLES

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
    id_origen = models.CharField(
        max_length=40, blank=True, db_index=True,
        verbose_name='id en el sistema de origen',
        help_text=(
            'Identificador del hecho en la fuente. Para RUV es '
            '`TBSINIESTROS_PERSONA.ID`. Permite volver a sincronizar sin '
            'duplicar y poder rastrear cada fila hasta su origen.'
        ),
    )
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Hecho Victimizante'
        verbose_name_plural = 'Hechos Victimizantes'
        # Una víctima puede tener el mismo tipo de hecho más de una vez
        # (e.g., desplazado dos veces), así que no se pone unique_together
        # sobre (victima, hecho).
        #
        # Sobre (fuente, id_origen) sí: dos filas con el mismo id en la misma
        # fuente son la MISMA fila traída dos veces. Sin esto, volver a correr
        # la importación duplicaría los hechos de todo el mundo en silencio, y
        # el reporte contaría dos veces a cada persona.
        constraints = [
            models.UniqueConstraint(
                fields=['fuente', 'id_origen'],
                condition=models.Q(id_origen__gt=''),
                name='hecho_unico_por_origen',
            ),
        ]
        indexes = [
            models.Index(fields=['victima', 'hecho']),
        ]
        ordering = ['fecha_hecho', 'hecho']

    def __str__(self):
        return f'{self.victima} — {self.hecho}'


class MarcaAguaLegacy(models.Model):
    """
    Hasta dónde llegó la última sincronización con el Oracle legacy.

    ─── Por qué existe ───────────────────────────────────────────────────────
    El legacy sigue vivo y caracterizando: **~592 personas y ~270 hogares por
    día** (medido sobre los últimos 30 días). Volver a leer el padrón entero para
    encontrarlos cuesta 19 horas; leer solo lo nuevo cuesta **segundos**. Esta
    tabla es lo único que hacía falta para poder pedir "lo que no había visto".

    ─── Por qué por ID y no por fecha ────────────────────────────────────────
    Medido contra producción el 2-ago-2026, sobre `GIC_PERSONA` (7,7 M filas):

        WHERE per_idpersona > 9.185.948   →  1.500 filas en  0,08 s
        WHERE usu_fechacreacion >= ayer   →    189 filas en 16,12 s

    **1.612 veces más rápido.** El motivo es simple: `PER_IDPERSONA` tiene un
    índice único (`KEY20`) y `USU_FECHACREACION` no, así que filtrar por fecha
    obliga a recorrer los 7,7 millones de filas. Y `PER_IDPERSONA` crece con el
    tiempo (2023: ~6,9 M → 2026: ~9,19 M), así que sirve de marca de agua.

    Para `GIC_HOGAR` es al revés —ahí sí hay índice sobre `USU_FECHACREACION` y la
    consulta tarda 0,0 s—, así que cada recurso se sincroniza por el camino que ya
    está indexado. De ahí que la marca tenga las dos formas.

    ⚠️ **Esto detecta ALTAS, no MODIFICACIONES.** Si el legacy corrige el nombre
    de una persona que ya teníamos, su `PER_IDPERSONA` no cambia y esta marca no
    la vuelve a traer. Cubrir eso exige otra estrategia (comparar, o una recarga
    completa periódica); mientras tanto, la recarga mensual sigue siendo la red.
    """
    RECURSO = [
        ('personas', 'Personas nuevas (GIC_PERSONA, por PER_IDPERSONA)'),
        ('hogares',  'Hogares caracterizados (GIC_HOGAR, por USU_FECHACREACION)'),
    ]

    recurso = models.CharField(max_length=20, primary_key=True, choices=RECURSO)

    ultimo_id = models.BigIntegerField(
        null=True, blank=True,
        help_text='Mayor identificador ya procesado. La próxima corrida pide > este.')
    ultima_fecha = models.DateTimeField(
        null=True, blank=True,
        help_text='Instante hasta el que se leyó. La próxima corrida pide >= este '
                  'menos el solape (ver SOLAPE_MINUTOS en el comando).')

    corridas = models.PositiveIntegerField(default=0)
    filas_ultima_corrida = models.PositiveIntegerField(default=0)
    segundos_ultima_corrida = models.FloatField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Marca de agua del legacy'
        verbose_name_plural = 'Marcas de agua del legacy'

    def __str__(self):
        donde = self.ultimo_id if self.ultimo_id is not None else self.ultima_fecha
        return f'{self.recurso} hasta {donde} ({self.corridas} corridas)'


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


class PersonaUniverso(models.Model):
    """
    El universo de víctimas, tal como lo publica la fuente — **no** nuestro dominio.

    ─── Por qué es una tabla aparte y no más filas en `Victima` ───────────────
    `Victima` es el padrón operativo de SICAV: tiene 24 índices, PII cifrada,
    hechos, colisiones resueltas y `cons_persona`, que es lo que se escribe al
    legacy. Meterle 12,5 M de filas de un *snapshot* externo tendría dos costos:
    encarece cada escritura del padrón operativo (medido: una fila cuesta 25×
    por los índices) y mezcla dos cosas con vidas distintas — el universo se
    reemplaza entero cada mes; `Victima` acumula historia.

    Acá vive el snapshot, liviano y desechable. `Victima` sigue siendo la fuente
    de verdad de lo que SICAV caracteriza.

    ─── 🔴 `cons_persona_universo` NO es `Victima.cons_persona` ──────────────
    Medido el 5-ago-2026 sobre 243.610 pares con el mismo documento: **cero
    coincidencias** entre `CONS_PERSONA` del universo y `PER_IDPERSONA` del
    legacy. Son espacios de identificadores distintos.

        1115724047 → universo    CONS_PERSONA  = 23664117
        1115724047 → GIC_PERSONA PER_IDPERSONA = 958858 / 6566478 / 9184606

    Por eso el id del universo tiene **campo propio**. Escribirlo en
    `Victima.cons_persona` haría que `apps/sincronizacion/oracle/mapeo.py` mande
    al legacy identificadores de otro sistema: no falla, escribe mal en silencio.

    **El cruce con `Victima` se hace por documento (hash), nunca por id.**
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    #: `CONS_PERSONA` del universo. Ver la advertencia de arriba.
    #: Este índice **se queda** aunque hoy marque 0 usos: la unicidad por corte
    #: empieza por `corte`, así que no sirve para buscar por el id solo, que es
    #: como llega una consulta desde la fuente ("¿qué es CONS_PERSONA 23988216?").
    cons_persona_universo = models.BigIntegerField(
        db_index=True,
        verbose_name='CONS_PERSONA del universo',
        help_text='Identificador en la fuente. NO es el cons_persona del legacy.',
    )

    # ── Documento: mismo patrón que `Victima` — cifrado + hash para buscar ──
    tipo_documento = models.CharField(
        max_length=10, blank=True, default='',
        help_text='TIPO_DOC tal como viene de la fuente, sin homologar.',
    )
    numero_documento = EncryptedField()
    #: Sin índice **a propósito**. Medido el 5-ago sobre la carga real: 0 usos, y
    #: 2.878 MB proyectados a 12 M entre el btree y el `_like` que Django agrega
    #: solo. Acá el cruce va por el hash SIN tipo (ver abajo), así que este campo
    #: se guarda para trazabilidad, no para buscar. Si algún día se busca por él,
    #: hay que reponer el índice con su migración — y sabiendo lo que cuesta.
    numero_documento_hash = models.CharField(max_length=64, blank=True, default='')
    #: Hash solo del número. Es la llave real del cruce con `Victima`, porque el
    #: tipo de documento no siempre viene y no siempre coincide entre fuentes.
    #:
    #: Tampoco lleva `db_index`: el índice compuesto
    #: `(numero_documento_hash_sin_tipo, corte)` de `Meta.indexes` ya lo cubre —
    #: es su prefijo izquierdo— y el suelto costaba otros 2.871 MB a 12 M, con
    #: 0 usos medidos.
    numero_documento_hash_sin_tipo = models.CharField(
        max_length=64, blank=True, default='')

    # ── Identidad y demografía ──────────────────────────────────────────────
    primer_nombre = EncryptedField(blank=True, default='')
    segundo_nombre = EncryptedField(blank=True, default='')
    primer_apellido = EncryptedField(blank=True, default='')
    segundo_apellido = EncryptedField(blank=True, default='')

    genero = models.CharField(max_length=20, blank=True, default='')
    pertenencia_etnica = models.CharField(max_length=60, blank=True, default='')
    discapacidad = models.BooleanField(default=False)
    tipo_discapacidad = models.CharField(max_length=20, blank=True, default='')
    ciclo_vital = models.CharField(max_length=20, blank=True, default='')

    #: `NUM_HECHOS` de la fuente. Es un CONTEO, no el detalle: los hechos con su
    #: fecha y lugar salen de `RUV.TBSINIESTROS_PERSONA` (ver `hechos_ruv.py`).
    num_hechos = models.IntegerField(null=True, blank=True)

    # ── Trazabilidad del snapshot ───────────────────────────────────────────
    #: Nombre del corte del que salió, p. ej. `TEMP_UNIV_VICT_PER_MI010726ALL`.
    #: Se guarda para poder responder "¿de cuándo es este dato?" sin adivinar, y
    #: para detectar cortes viejos: el antecedente de `GIC_REPORTE_HOGAR`,
    #: congelado desde 2021 sin que nadie lo notara, es la razón.
    #:
    #: Sin `db_index`: la tabla tiene **un solo valor** de corte (dos mientras se
    #: valida el nuevo), y un índice sobre una columna así no lo elige el planner
    #: — medido: 0 usos. Además `persona_universo_unica_por_corte` empieza por
    #: `corte`, así que ya está cubierto por su prefijo izquierdo.
    corte = models.CharField(max_length=40)
    fecha_corte = models.DateField(
        null=True, blank=True,
        help_text='Primer día del mes del corte (010726 → 2026-07-01).')

    #: Enlace con el padrón operativo, resuelto **por documento**. Nullable a
    #: propósito: la mayoría del universo no tiene fila en `Victima` —ese es
    #: justamente el hueco que esta tabla viene a cubrir— y forzar el enlace
    #: inventaría correspondencias.
    victima = models.ForeignKey(
        'victimas.Victima', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registros_universo',
    )

    #: Cuando varias filas del corte comparten documento, esta es la que la
    #: búsqueda debe devolver. Las otras se conservan —no se borran— y quedan
    #: con `False` más una fila en `DescarteUniverso` que dice por qué perdieron.
    #:
    #: Se marca DESPUÉS de cargar, con una consulta sobre la base, y no durante:
    #: deduplicar al vuelo obligaría a mantener 12 M de hashes en memoria (~800
    #: MB) y a ordenar por documento en Oracle, que ya está medido en 12 h sobre
    #: una tabla de este tamaño. Cargar y después resolver cuesta minutos.
    #: El índice **se queda**, aunque un booleano suele ser mala idea indexar: el
    #: reset de la fase 2 filtra por `es_preferida=False`, que son ~55.100 de 12 M
    #: (0,45 %). Ahí el índice es justamente lo que hace que ese UPDATE sea barato
    #: en vez de un recorrido de la tabla entera.
    es_preferida = models.BooleanField(
        default=True, db_index=True,
        help_text='False = otra fila del mismo corte ganó ese documento.')

    # ── Vigencia, resuelta contra el legado y guardada acá ───────────────────
    #: Última caracterización según `GIC_HOGAR`, para quien está en el universo
    #: pero NO en `Victima` — que es justo el caso que el universo vino a cubrir.
    #:
    #: El universo **no trae vigencia**: verificado sobre las 12.496.965 filas del
    #: corte, `IDENTIFICADO` viene en 0 y `ESTADO_RUV` ni siquiera existe como
    #: columna. Sin esto, una persona con ficha vigente aparecería como
    #: caracterizable y la regla de los 2 años se perdería en silencio.
    fecha_ult_caracterizacion = models.DateTimeField(null=True, blank=True)

    #: Fecha de nacimiento, que **el corte del universo no trae** —sus columnas
    #: de edad son `CICLO_VITAL`— y que el alta necesita para poder caracterizar.
    #: Se resuelve contra `GIC_PERSONA` en el mismo viaje que la vigencia.
    #:
    #: Queda vacía para quien nunca pasó por el legado (el caso de `28548486`):
    #: ahí la captura el encuestador en campo, que es un dato que la persona sabe.
    fecha_nacimiento = models.DateField(null=True, blank=True)

    #: Cuándo se resolvió lo anterior contra el legado. Se guarda para no volver
    #: a preguntarle a Oracle en cada búsqueda: la primera consulta paga el viaje
    #: y las siguientes se responden acá.
    #:
    #: `NULL` significa "todavía no se preguntó", que **no** es lo mismo que
    #: "no tiene fecha" (nunca caracterizada). Sin este campo, los dos casos son
    #: indistinguibles y el segundo se trataría como el primero cada vez.
    vigencia_verificada_en = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Persona del universo'
        verbose_name_plural = 'Personas del universo'
        constraints = [
            # Una persona por corte. Permite tener dos cortes conviviendo
            # mientras se valida el nuevo, sin que se pisen.
            models.UniqueConstraint(
                fields=['corte', 'cons_persona_universo'],
                name='persona_universo_unica_por_corte',
            ),
        ]
        indexes = [
            # El cruce con `Victima` y la búsqueda offline van por acá.
            models.Index(fields=['numero_documento_hash_sin_tipo', 'corte']),
        ]

    def __str__(self):
        return f'[{self.corte}] {self.cons_persona_universo}'


class DescarteUniverso(models.Model):
    """
    Filas del universo que la carga NO ingresó, con el motivo.

    Existe porque una carga que descarta en silencio es indistinguible de una
    fuente incompleta: sin esta tabla, "faltan 55.100 personas" no se puede
    responder. Medido sobre el corte 01/07/2026: 12.496.965 filas y 11.954.392
    documentos únicos, o sea **al menos 55.100 filas comparten documento**, más
    **487.473 sin documento usable**.
    """

    MOTIVO = [
        ('SIN_DOCUMENTO',      'Sin documento usable (menos de 5 caracteres)'),
        ('DOCUMENTO_REPETIDO', 'Otra fila del mismo corte ya tomó ese documento'),
        ('SIN_CONS_PERSONA',   'Sin identificador en la fuente'),
        # El documento resuelve a MÁS DE UNA víctima del padrón. No se enlaza a
        # ninguna: elegir una sería inventar una correspondencia, y el padrón
        # tiene documentos compartidos por cientos de filas.
        ('ENLACE_AMBIGUO',     'El documento resuelve a más de una víctima'),
        ('OTRO',               'Otro — ver detalle'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corte = models.CharField(max_length=40, db_index=True)
    cons_persona_universo = models.BigIntegerField(null=True, blank=True, db_index=True)
    #: Hash, no el documento: para contar y rastrear no hace falta el número.
    numero_documento_hash_sin_tipo = models.CharField(max_length=64, blank=True,
                                                      default='', db_index=True)
    motivo = models.CharField(max_length=20, choices=MOTIVO, db_index=True)
    detalle = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Descarte del universo'
        verbose_name_plural = 'Descartes del universo'
        indexes = [models.Index(fields=['corte', 'motivo'])]

    def __str__(self):
        return f'[{self.corte}] {self.motivo}'
