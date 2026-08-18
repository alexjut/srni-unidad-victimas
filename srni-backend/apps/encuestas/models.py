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
import os
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

        Sprint 21 — las preguntas tipo PERSONA cuentan N veces (una por cada
        miembro del hogar). Las HOGAR cuentan una sola vez.
        """
        from apps.formulario.models import Pregunta

        n_miembros = self.hogar.miembros.count() if self.hogar_id else 0
        # Si el hogar no tiene miembros registrados todavía, asumimos 1
        # (el autorizado) para no dividir por cero.
        n_miembros = max(n_miembros, 1)

        preg_hogar = Pregunta.objects.filter(
            capitulo__instrumento=self.instrumento,
            obligatoria=True, activa=True, nivel='HOGAR',
        ).count()
        preg_persona = Pregunta.objects.filter(
            capitulo__instrumento=self.instrumento,
            obligatoria=True, activa=True, nivel='PERSONA',
        ).count()

        total = preg_hogar + preg_persona * n_miembros
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

    Sprint 21 — Una pregunta de nivel HOGAR tiene UNA respuesta por sesión
    (miembro=NULL). Una pregunta de nivel PERSONA tiene UNA respuesta por
    cada miembro del hogar (miembro != NULL, FK a MiembroHogar).
    UniqueConstraint garantiza no duplicados.

    Para preguntas de selección múltiple, `valor` es un JSON array como string.
    """
    sesion = models.ForeignKey(
        SesionEncuesta, on_delete=models.CASCADE, related_name='respuestas'
    )
    pregunta = models.ForeignKey(
        'formulario.Pregunta', on_delete=models.PROTECT, related_name='respuestas'
    )
    # Sprint 21 — para preguntas PERSONA: a qué miembro del hogar aplica.
    # NULL si la pregunta es HOGAR. NOT NULL si es PERSONA (validado en serializer).
    miembro = models.ForeignKey(
        'hogares.MiembroHogar',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='respuestas',
        help_text='Miembro del hogar al que aplica la respuesta. NULL si la pregunta es HOGAR.',
    )
    # Para OPCION_UNICA: "A" / Para OPCION_MULTIPLE: '["A","B"]' / Para SINO: "true"
    valor = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Respuesta'
        verbose_name_plural = 'Respuestas'
        constraints = [
            # Sprint 21 — exactamente una respuesta por (sesion, pregunta, miembro).
            # SQLite/PostgreSQL tratan NULL como distinto en UNIQUE — eso es lo
            # que queremos: preguntas HOGAR (miembro=NULL) admiten 1 sola; las
            # PERSONA (miembro=ID) admiten N (una por miembro).
            models.UniqueConstraint(
                fields=['sesion', 'pregunta', 'miembro'],
                name='respuesta_unica_por_miembro',
            ),
        ]
        ordering = ['pregunta__orden', 'miembro_id']

    def __str__(self):
        miembro = f' [m={str(self.miembro_id)[:8]}]' if self.miembro_id else ''
        return f'[{self.pregunta.codigo_externo}]{miembro} → "{self.valor[:40]}"'


def ruta_soporte_excepcion(instance, filename):
    """
    Ruta del soporte que acredita la excepción de vigencia.

    Sin PII en el nombre: se organiza por sesión y se nombra con el id del
    registro (UUID). Conserva solo la extensión original.
    """
    ext = os.path.splitext(filename)[1].lower()[:10]
    return f'excepciones_vigencia/{instance.sesion_id}/{instance.id}{ext}'


class ExcepcionVigencia(models.Model):
    """
    Habilitación para caracterizar a una persona que tiene ficha vigente.

    ─── Por qué existe ───────────────────────────────────────────────────────
    El Manual UARIV §5.1.1 (pág. 22) define tres rutas que **omiten la regla de
    vigencia**: acciones constitucionales, modificación de núcleo familiar y
    ruta especial. Hasta agosto de 2026 `ruta_entrevista` era solo una etiqueta
    y no omitía nada, así que una tutela no habilitaba absolutamente nada —lo
    contrario de para lo que existe la ruta— y esos casos se escalaban a
    soporte.

    ─── Por qué se autoriza desde el front y no desde el celular ─────────────
    La primera versión (6-ago) dejaba que el encuestador eligiera la ruta en
    campo y adjuntara una **foto del soporte** desde el celular. Se cambió el
    14-ago por indicación de la operación: **el caracterizador no debe tener el
    documento**. El fallo, la tutela o el auto llegan por canal institucional al
    nivel central, no a quien está parado frente a la víctima.

    El efecto secundario es el que importa: quien autoriza el salto de un
    control deja de ser quien lo ejecuta. Antes la excepción se registraba
    *después* de usarla y el encuestador se autoautorizaba; ahora se otorga
    *antes*, desde el front, por un perfil con
    `puede_autorizar_excepciones`, y el celular solo la consume.

    Por eso cada habilitación queda con **quién la autorizó**, **sobre quién**,
    **cuándo**, **por qué ruta**, **con qué radicado** y **con qué motivo**. El
    archivo de soporte sigue siendo posible —cargado desde el computador— pero
    ya no es obligatorio: exigirlo dejaría fuera los casos que llegan por correo
    o por teléfono.

    ─── De un solo uso ──────────────────────────────────────────────────────
    Se consume al finalizar la caracterización que la usó (`estado='USADA'`).
    Una habilitación que quedara abierta sería un permiso permanente para
    saltarse la vigencia de esa persona, que es exactamente lo que la regla
    existe para impedir.
    """

    VIGENTE = 'VIGENTE'
    USADA = 'USADA'
    ANULADA = 'ANULADA'
    ESTADOS = [
        (VIGENTE, 'Vigente — la persona puede caracterizarse'),
        (USADA, 'Usada — ya se caracterizó con ella'),
        (ANULADA, 'Anulada — se dejó sin efecto'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Nace SIN sesión: la habilitación se otorga antes de que exista la
    # encuesta, y muchas veces días antes. La sesión que la consumió queda en
    # `usada_en_sesion`.
    sesion = models.ForeignKey(
        SesionEncuesta,
        on_delete=models.CASCADE,
        related_name='excepciones_vigencia',
        null=True, blank=True,
        help_text='Obsoleto — histórico de las excepciones registradas desde el '
                  'celular antes del 14-ago-2026. Las nuevas nacen sin sesión.',
    )
    victima = models.ForeignKey(
        'victimas.Victima',
        on_delete=models.PROTECT,
        related_name='excepciones_vigencia',
        help_text='La persona que tenía ficha vigente.',
    )
    ruta = models.CharField(
        max_length=30,
        choices=SesionEncuesta.RUTA_ENTREVISTA,
        help_text='Ruta por la que se omitió la vigencia.',
    )

    # Lo que hacía vigente la ficha, congelado en el momento de la excepción.
    # Se copia en vez de referenciarse: si la persona se recaracteriza, la fecha
    # del modelo cambia y se perdería la razón por la que se hizo la excepción.
    fecha_ult_caracterizacion = models.DateField(
        null=True, blank=True,
        help_text='Fecha de la caracterización que estaba vigente.',
    )
    vigente_hasta = models.DateField(
        null=True, blank=True,
        help_text='Hasta cuándo estaba vigente esa ficha.',
    )

    # El radicado reemplaza a la foto como identificador del soporte. Es lo que
    # permite ir a buscar el documento después: sin él, "hubo una tutela" no se
    # puede verificar contra nada.
    radicado = models.CharField(
        max_length=100, blank=True,
        help_text='Número de radicado del fallo, auto o solicitud que sustenta '
                  'la excepción.',
    )

    # El archivo dejó de ser obligatorio el 14-ago-2026. Se conserva porque quien
    # autoriza desde el computador sí suele tener el PDF, y adjuntarlo es mejor
    # que no adjuntarlo. Lo que ya no se hace es tomarle una foto en campo.
    soporte = models.FileField(
        upload_to=ruta_soporte_excepcion, null=True, blank=True,
        help_text='Opcional — el documento que acredita la excepción, cargado '
                  'desde el front. Ya no se captura en campo.',
    )
    soporte_nombre = models.CharField(
        max_length=255, blank=True,
        help_text='Nombre original del archivo (para mostrar al usuario).',
    )
    observacion = models.TextField(
        blank=True,
        help_text='Motivo de la excepción, escrito por quien la autoriza.',
    )

    estado = models.CharField(
        max_length=10, choices=ESTADOS, default=VIGENTE, db_index=True,
        help_text='Una habilitación se consume al usarse.',
    )
    usada_en_sesion = models.ForeignKey(
        SesionEncuesta,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='habilitacion_consumida',
        help_text='La sesión de encuesta que consumió esta habilitación.',
    )
    usada_at = models.DateTimeField(null=True, blank=True)

    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='excepciones_vigencia_anuladas',
    )
    anulada_at = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)

    autorizada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='excepciones_vigencia',
        help_text='Quién autorizó la excepción desde el front. Nunca el '
                  'encuestador que la ejecuta.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Excepción de vigencia'
        verbose_name_plural = 'Excepciones de vigencia'
        indexes = [
            models.Index(fields=['victima', 'created_at']),
            models.Index(fields=['ruta']),
            # El camino caliente: "¿esta persona tiene habilitación vigente?",
            # que se pregunta en cada búsqueda y en cada precarga de jornada.
            models.Index(fields=['victima', 'estado'],
                         name='exc_vig_victima_estado_idx'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_ruta_display()} — {self.victima_id} ({self.created_at:%Y-%m-%d})'

    @property
    def tiene_soporte(self) -> bool:
        return bool(self.soporte)

    @property
    def esta_vigente(self) -> bool:
        return self.estado == self.VIGENTE

    def marcar_usada(self, sesion=None):
        """
        La consume. Idempotente: llamarla dos veces no revive una anulada ni
        pisa la sesión de la primera vez.
        """
        from django.utils import timezone

        if self.estado != self.VIGENTE:
            return False
        self.estado = self.USADA
        self.usada_en_sesion = sesion
        self.usada_at = timezone.now()
        self.save(update_fields=['estado', 'usada_en_sesion', 'usada_at'])
        return True

    def anular(self, usuario, motivo=''):
        """
        La deja sin efecto. No se borra: una habilitación otorgada y retirada es
        justamente lo que una auditoría necesita poder ver.
        """
        from django.utils import timezone

        if self.estado != self.VIGENTE:
            return False
        self.estado = self.ANULADA
        self.anulada_por = usuario
        self.anulada_at = timezone.now()
        self.motivo_anulacion = motivo or ''
        self.save(update_fields=['estado', 'anulada_por', 'anulada_at',
                                 'motivo_anulacion'])
        return True

    @classmethod
    def vigente_para(cls, victima_id):
        """
        La habilitación vigente de una persona, o `None`.

        Se toma la más reciente: si por lo que sea hay dos, la última autorizada
        es la que refleja la decisión actual.
        """
        if not victima_id:
            return None
        return (cls.objects
                .filter(victima_id=victima_id, estado=cls.VIGENTE)
                .order_by('-created_at')
                .first())
