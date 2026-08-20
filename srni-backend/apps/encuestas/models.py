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
        Porcentaje de obligatorias VISIBLES que están respondidas.

        La palabra que faltaba era «visibles», y por eso este método fue el
        APK-005: contaba TODAS las obligatorias del instrumento sin evaluar
        skip-logic. Una obligatoria que una regla HABILITAR mantiene oculta no
        se le puede mostrar a nadie, así que nunca se responde — pero engordaba
        el denominador igual. Una entrevista legítimamente terminada se cerraba
        en 55 %, o en 0 % si el instrumento tenía muchas condicionales, y en la
        app se veía una sesión «Completada» con la barra vacía.

        Se resolvió una vez en la app tapando el número (forzar 100 % si el
        estado era COMPLETADA), y eso era peor: mentía sobre las entrevistas
        que sí se cerraron a medias, y el panel web —que nunca aplicó ese
        maquillaje— mostraba otra cosa sobre la misma sesión.

        Cómo se cuenta ahora, que es lo mismo que hace el móvil en
        `calcularProgresoOffline`:

          · Denominador: obligatorias **visibles** con las respuestas actuales.
            Se excluyen las precargadas — vienen del padrón, no las responde
            nadie en la entrevista.
          · HOGAR: una vez. Su visibilidad no depende del miembro.
          · PERSONA: una vez POR MIEMBRO, y evaluando la visibilidad con las
            respuestas de ESE miembro. La misma pregunta puede estar visible
            para uno y oculta para otro; ese es justamente el punto de la
            skip-logic por persona.
          · Numerador: de esas mismas, las que tienen valor no vacío. Una
            respuesta que quedó fuera de flujo no suma: si no cuenta abajo,
            tampoco puede contar arriba.

        Sin miembros todavía se asume 1 (el autorizado) para no dividir por
        cero, igual que antes.
        """
        from apps.formulario.models import Pregunta, ReglaSkipLogic
        from apps.formulario.skiplogic import calcular_visibles

        preguntas = list(
            Pregunta.objects.filter(
                capitulo__instrumento=self.instrumento, activa=True,
            ).order_by('capitulo_id', 'orden')
        )
        if not preguntas:
            return 0

        reglas = list(
            ReglaSkipLogic.objects.filter(instrumento=self.instrumento)
            .select_related('pregunta_origen', 'pregunta_afectada')
        )

        # (pregunta_id, miembro_id) → valor. miembro_id None = nivel HOGAR.
        #
        # values_list y no .only(): con .only() el manager de la relación inversa
        # necesita `sesion_id` para cachear el objeto padre, y al estar diferido
        # lo releía CON UNA CONSULTA POR RESPUESTA. Con 150 respuestas eran 79
        # consultas en un método que corre en cada guardado. Acá no hace falta
        # instanciar modelos: se necesitan tres escalares.
        # El order_by() vacío saca el ORDER BY del Meta, que arrastraba un JOIN
        # con formulario_pregunta para nada.
        valores = {
            (preg_id, miembro_id): valor
            for preg_id, miembro_id, valor in self.respuestas.order_by().values_list(
                'pregunta_id', 'miembro_id', 'valor',
            )
        }

        # Los datos demográficos vienen en la MISMA consulta: las reglas por
        # expresión (`edad >= 18`, `sexo == '2'`) los necesitan, y traerlos
        # después sería una consulta por integrante.
        filas = (
            list(self.hogar.miembros.values_list(
                'id', 'genero', 'fecha_nacimiento', 'incluido_ruv',
                'es_autorizado', 'victima__fecha_nacimiento',
            ))
            if self.hogar_id else []
        )
        if not filas:
            filas = [(None, '', None, False, True, None)]

        datos_miembro = {
            f[0]: {
                'genero': f[1] or '',
                # Para el autorizado, la fecha del padrón sirve de respaldo si el
                # integrante se registró sin ella.
                'fecha_nacimiento': f[2] or (f[5] if f[4] else None),
                'incluido_ruv': bool(f[3]),
            }
            for f in filas
        }
        miembros = [f[0] for f in filas]
        # Las preguntas HOGAR se evalúan con el contexto del AUTORIZADO, no del
        # primero que devuelva la base: si no, el porcentaje del mismo hogar
        # cambiaría según el orden de los integrantes.
        autorizado = next((f[0] for f in filas if f[4]), miembros[0])

        def mapa_para(miembro_id):
            """codigo_externo → valor, en el contexto de un miembro.

            Cubre el instrumento COMPLETO y no solo el capítulo: una regla puede
            tener su origen en otro capítulo, y con un mapa recortado esa regla
            no se dispararía nunca.
            """
            return {
                p.codigo_externo: valores.get(
                    (p.pk, miembro_id if p.nivel == 'PERSONA' else None), ''
                )
                for p in preguntas
            }

        def contexto_para(miembro_id, mapa):
            """edad / sexo / etnia / ruv_incluido de un integrante.

            Mismo criterio que la pantalla de captura del móvil
            (`construirContextoMiembro` en formulario/[temaId].tsx). Tiene que
            ser el mismo: si el backend decidiera la visibilidad con otros datos,
            exigiría preguntas que la app nunca mostró.

            Lo que NO se hereda del padrón es deliberado y está documentado en
            `docs/oracle-legacy/join_caracterizacion_roto.md`: el género de allí
            acierta la mitad de las veces —el join empareja con otra persona— y
            la etnia no se hereda nunca, se pregunta. Sin dato, la variable queda
            desconocida y la regla no dispara, que es lo correcto: no afirma nada.
            """
            d = datos_miembro.get(miembro_id, {})
            ctx = {}

            # edad: la respondida (A6 fecha, B9 edad) manda sobre la registrada.
            edad = None
            b9 = (mapa.get('B9') or '').strip()
            if b9:
                try:
                    edad = int(float(b9))
                except (TypeError, ValueError):
                    edad = None
            if edad is None:
                nacimiento = _fecha(mapa.get('A6')) or d.get('fecha_nacimiento')
                edad = _edad(nacimiento)
            if edad is not None:
                ctx['edad'] = edad

            # sexo: '1' hombre / '2' mujer. A8 lo captura el encuestador; si no
            # está, cae al género del integrante.
            sexo = (mapa.get('A8') or '').strip()
            if not sexo:
                genero = d.get('genero') or ''
                sexo = {'M': '1', 'F': '2'}.get(genero, '')
            if sexo:
                ctx['sexo'] = sexo

            ctx['etnia'] = 'ninguno'
            ctx['ruv_incluido'] = bool(d.get('incluido_ruv'))
            return ctx

        def cuenta(p):
            """¿Esta pregunta entra en el denominador?"""
            return p.obligatoria and not p.es_precargada

        # ── HOGAR: una sola evaluación, con el contexto del autorizado ────────
        mapa_hogar = mapa_para(autorizado)
        vis_hogar, _, _ = calcular_visibles(
            preguntas, reglas, mapa_hogar, contexto_para(autorizado, mapa_hogar),
        )
        total = 0
        respondidas = 0
        for p in preguntas:
            if p.nivel != 'HOGAR' or not cuenta(p) or p.codigo_externo not in vis_hogar:
                continue
            total += 1
            if (valores.get((p.pk, None), '') or '').strip():
                respondidas += 1

        # ── PERSONA: una evaluación por miembro ───────────────────────────────
        for miembro_id in miembros:
            mapa = mapa_para(miembro_id)
            vis, _, _ = calcular_visibles(
                preguntas, reglas, mapa, contexto_para(miembro_id, mapa),
            )
            for p in preguntas:
                if p.nivel != 'PERSONA' or not cuenta(p) or p.codigo_externo not in vis:
                    continue
                total += 1
                if (valores.get((p.pk, miembro_id), '') or '').strip():
                    respondidas += 1

        if total == 0:
            return 0
        # El clamp no es decorativo: sin él, un dato inconsistente podría
        # devolver >100 y dibujar una barra más ancha que su tarjeta (APK-006).
        return max(0, min(100, int((respondidas / total) * 100)))


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


# ─── Helpers de edad ─────────────────────────────────────────────────────────

def _fecha(valor):
    """Interpreta una fecha capturada como texto. Devuelve None si no es una."""
    from datetime import date as _date
    if not valor:
        return None
    if isinstance(valor, _date):
        return valor
    try:
        return _date.fromisoformat(str(valor).strip()[:10])
    except (TypeError, ValueError):
        return None


def _edad(nacimiento):
    """Edad cumplida hoy, o None si no hay fecha utilizable."""
    from datetime import date as _date
    f = _fecha(nacimiento)
    if f is None:
        return None
    hoy = _date.today()
    edad = hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day))
    return edad if 0 <= edad < 130 else None
