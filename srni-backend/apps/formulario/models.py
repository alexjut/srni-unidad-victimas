"""
Motor de formularios SRNI — Rediseño Sprint 7, alineado con Diccionario V8.

Decisiones de diseño:

1. Instrumento como modelo relacional (no enum): cada instrumento
   (TERRITORIAL, BUENAVENTURA, SAN_ANDRES, etc.) tiene su propio conjunto
   de capítulos y preguntas — NO son perfiles ni rutas de entrevista.
   El caracterizador elige el instrumento al crear la caracterización.

2. Instrumento unificado (sin InstrumentoVersion separado): el campo
   'version' vive en Instrumento. Las respuestas en SesionEncuesta quedan
   ancladas al Instrumento exacto (codigo + version) vigente al capturarlas,
   garantizando trazabilidad documental (Ley 1581 — auditoría).

3. codigo_externo con sufijo _tel: identificador del Diccionario V8 oficial
   (ej. C1_tel, B9_tel). Campo de integración, no PK, para no acoplar la
   integridad referencial a nombres externos que UARIV puede cambiar.

4. id_resp_vivanto en OpcionRespuesta: ID numéricos del Diccionario V8 para
   exportar respuestas al sistema legado VIVANTO sin transformación adicional.

5. aplicabilidad JSON en Capitulo: regla declarativa evaluada antes de
   presentar el capítulo. Evita hardcodear condiciones en el frontend.

6. ReglaSkipLogic unificada: soporta expresiones de contexto (edad, sexo,
   RUV) además de respuestas directas. Acciones tipadas: HABILITAR /
   DESHABILITAR / OBLIGAR / FINALIZAR. Motor genérico — sin lógica
   hardcodeada por instrumento.
"""
from django.db import models
import uuid


class TipoPreguntaChoices(models.TextChoices):
    TEXTO = "TEXTO", "Texto libre"
    TEXTO_LARGO = "TEXTO_LARGO", "Texto largo (observaciones)"
    NUMERICO = "NUMERICO", "Numérico"
    FECHA = "FECHA", "Fecha"
    BOOLEAN = "BOOLEAN", "Sí / No"
    RADIO = "RADIO", "Selección única (radio)"
    LISTA = "LISTA", "Lista desplegable"
    LISTA_MULTIPLE = "LISTA_MULTIPLE", "Selección múltiple"
    COMBO_DINAMICO = "COMBO_DINAMICO", "Combo dinámico (DIVIPOLA, etc.)"


class NivelPreguntaChoices(models.TextChoices):
    HOGAR = "HOGAR", "Aplica al hogar"
    PERSONA = "PERSONA", "Aplica a cada miembro"


class PoblacionObjetivoChoices(models.TextChoices):
    AUTORIZADO = "AUTORIZADO", "Solo autorizado"
    AUTORIZADO_TUTOR_CUIDADOR = "AUTORIZADO_TUTOR_CUIDADOR", "Autorizado/Tutor/Cuidador"
    TODOS_MIEMBROS = "TODOS_MIEMBROS", "Todos los miembros del hogar"
    VICTIMAS_RUV = "VICTIMAS_RUV", "Solo víctimas incluidas en RUV"
    VICTIMAS_RUV_3_ANOS_MAS = "VICTIMAS_RUV_3_ANOS_MAS", "Víctimas RUV de 3 años o más"


class AccionSkipChoices(models.TextChoices):
    HABILITAR = "HABILITAR", "Habilitar pregunta/capítulo"
    DESHABILITAR = "DESHABILITAR", "Deshabilitar pregunta/capítulo"
    OBLIGAR = "OBLIGAR", "Hacer obligatoria"
    FINALIZAR = "FINALIZAR", "Finalizar capítulo"


class Instrumento(models.Model):
    """
    Instrumento de caracterización SRNI.

    Cada instrumento representa un cuestionario completo con sus propios
    capítulos y preguntas. El caracterizador lo elige al crear la caracterización.

    # TODO: confirmar lista oficial de instrumentos y códigos exactos
    #       con área funcional / tablas Oracle (GIC_TIPO_INSTRUMENTO o equivalente).
    #       Los 7 valores actuales son semilla inicial, no definitiva.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=30, db_index=True)
    nombre = models.CharField(max_length=150)
    version = models.CharField(max_length=20, help_text="Ej: V7, V8, V8.1, V9")
    activo = models.BooleanField(default=True, db_index=True)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    fuente_documental = models.CharField(
        max_length=300, blank=True,
        help_text="Ej: Manual UARIV 520.06.06-1 v01, 07/10/2021",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("codigo", "version")]
        ordering = ["codigo", "-vigente_desde"]
        verbose_name = "Instrumento"
        verbose_name_plural = "Instrumentos"

    def __str__(self):
        return f"{self.codigo}-{self.version}"

    @property
    def vigente(self) -> bool:
        from datetime import date
        hoy = date.today()
        if self.vigente_desde > hoy:
            return False
        if self.vigente_hasta and self.vigente_hasta < hoy:
            return False
        return True


class Capitulo(models.Model):
    """
    Capítulo (sección) del instrumento. Equivale a los módulos del APK original.

    nivel: indica si el capítulo entero se responde una vez por HOGAR o una
      vez por cada PERSONA del hogar. Determina cómo el motor itera respuestas.
      Territorial V7 — HOGAR: A, C, D, E, J(Alim), M, T
      Territorial V7 — PERSONA: B, F(Educ), G, H, J(FT), K, L

    'aplicabilidad' es una regla declarativa evaluada antes de mostrar el capítulo:
      {'ruv_incluido': True, 'edad_min': 3}  → solo víctimas RUV de ≥3 años
      {'tipo_persona': ['5001','5002','5003']}  → solo esos roles
    Esto evita hardcodear condiciones de negocio en el frontend.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instrumento = models.ForeignKey(
        Instrumento, on_delete=models.CASCADE, related_name="capitulos"
    )
    codigo = models.CharField(max_length=10, help_text="A, B, C, D, E, F, G, M, T")
    nombre = models.CharField(max_length=200)
    orden = models.PositiveSmallIntegerField()
    nivel = models.CharField(
        max_length=10,
        choices=NivelPreguntaChoices.choices,
        default=NivelPreguntaChoices.HOGAR,
        help_text="HOGAR: se responde una vez por hogar. PERSONA: una vez por cada miembro.",
    )
    objetivo = models.TextField(blank=True)
    poblacion_objetivo = models.CharField(
        max_length=50,
        choices=PoblacionObjetivoChoices.choices,
        default=PoblacionObjetivoChoices.TODOS_MIEMBROS,
    )
    aplicabilidad = models.JSONField(
        default=dict, blank=True,
        help_text="Reglas declarativas: {'ruv_incluido': True, 'edad_min': 3}",
    )

    class Meta:
        unique_together = [("instrumento", "codigo")]
        ordering = ["orden"]
        verbose_name = "Capítulo"
        verbose_name_plural = "Capítulos"

    def __str__(self):
        return f"[{self.codigo}] {self.nombre}"


class Pregunta(models.Model):
    """
    Pregunta del formulario alineada con el Diccionario V8.

    codigo_externo: identificador del Diccionario V8 (ej. C1_tel, B9_tel).
      Se almacena como campo de integración — no como PK — para no acoplar
      la integridad referencial a nombres externos que UARIV puede cambiar.

    variable_bd: nombre de columna para reportes y exportación a VIVANTO.

    nivel: HOGAR (se responde una vez por hogar) o PERSONA (una vez por miembro).
      Controla cómo el motor itera al rellenar las respuestas.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    capitulo = models.ForeignKey(Capitulo, on_delete=models.CASCADE, related_name="preguntas")
    codigo_externo = models.CharField(
        max_length=40, db_index=True,
        help_text="Variable BD del diccionario oficial: DT_ATENCION, C1_tel, Z3, PL1...",
    )
    no_pregunta = models.CharField(
        max_length=10, blank=True, db_index=True,
        help_text="Número en diagrama de flujo: A1, A2, B1, C1, J1... (columna 'No. PREGUNTA VARIABLE')",
    )
    id_preg = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text="ID_PREG del diccionario UARIV — para export a sistema VIVANTO",
    )
    variable_bd = models.CharField(
        max_length=50,
        help_text="Nombre de columna en reportes/VIVANTO export (mismo que codigo_externo sin sufijo _tel)",
    )
    texto = models.TextField(help_text="Pregunta literal mostrada al entrevistado")
    descripcion_ayuda = models.TextField(
        blank=True,
        help_text="Conceptos y notas del manual PDF para el encuestador",
    )
    tipo = models.CharField(max_length=20, choices=TipoPreguntaChoices.choices)
    nivel = models.CharField(
        max_length=10, choices=NivelPreguntaChoices.choices,
        help_text="Heredado del capítulo. Se guarda aquí para queries directas sin JOIN.",
    )
    obligatoria = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField()
    es_precargada = models.BooleanField(
        default=False,
        help_text="True si el dato viene precargado del RUV — no editable por el encuestador",
    )
    fuente_precarga = models.CharField(
        max_length=60, blank=True,
        help_text="RUV | DIVIPOLA | TABLA_USUARIOS | TABLA_CONFORMACION_HOGAR",
    )
    validaciones = models.JSONField(
        default=dict, blank=True,
        help_text="{'min':0,'max':7} | {'regex':'^[0-9]{10}$'} | {'max_length':500}",
    )
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = [("capitulo", "codigo_externo")]
        ordering = ["orden"]
        indexes = [
            models.Index(fields=["codigo_externo"]),
            models.Index(fields=["no_pregunta"]),
            models.Index(fields=["id_preg"]),
            models.Index(fields=["capitulo", "orden"]),
        ]
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"

    def __str__(self):
        ref = self.no_pregunta or self.codigo_externo
        return f"[{ref}] {self.texto[:60]}"

    def save(self, *args, **kwargs):
        if not self.variable_bd and self.codigo_externo:
            self.variable_bd = self.codigo_externo.replace("_tel", "")
        super().save(*args, **kwargs)


class OpcionRespuesta(models.Model):
    """
    Opción de respuesta para preguntas RADIO, LISTA, LISTA_MULTIPLE.

    id_resp_vivanto: ID numérico del Diccionario V8 (columna ID_RESP del Excel).
      Opcional — solo presente en opciones que necesitan exportarse al sistema
      legado VIVANTO. Permite la exportación directa sin transformación adicional.

    finaliza_capitulo: equivale a RESFINALIZA del APK original — al seleccionar
      esta opción el motor cierra el capítulo actual sin mostrar más preguntas.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name="opciones")
    valor = models.CharField(max_length=100, help_text="Valor almacenado en la respuesta")
    etiqueta = models.CharField(max_length=500, help_text="Texto visible al usuario")
    id_resp_vivanto = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text="ID_RESP del Diccionario V8 para export a VIVANTO legacy",
    )
    orden = models.PositiveSmallIntegerField()
    finaliza_capitulo = models.BooleanField(
        default=False,
        help_text="Equivale a RESFINALIZA del APK: cierra el capítulo al seleccionar",
    )

    class Meta:
        unique_together = [("pregunta", "valor")]
        ordering = ["orden"]
        verbose_name = "Opción de Respuesta"
        verbose_name_plural = "Opciones de Respuesta"

    def __str__(self):
        return f"{self.pregunta.codigo_externo} = {self.valor} ({self.etiqueta[:40]})"


class ReglaSkipLogic(models.Model):
    """
    Regla declarativa de skip logic. Motor genérico — sin lógica hardcodeada
    por instrumento. Evalúa las reglas del instrumento que corresponda.

    Soporta:
    - Reglas basadas en respuesta directa (pregunta_origen + valor_trigger)
    - Reglas basadas en contexto del hogar/persona (expresion_origen: edad, sexo, RUV)
    - Acciones tipadas: HABILITAR, DESHABILITAR, OBLIGAR, FINALIZAR
    - Afectación a pregunta individual o a capítulo completo
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instrumento = models.ForeignKey(
        Instrumento, on_delete=models.CASCADE, related_name="reglas"
    )
    pregunta_origen = models.ForeignKey(
        Pregunta, on_delete=models.CASCADE, related_name="reglas_salientes",
        null=True, blank=True,
        help_text="Pregunta cuya respuesta dispara la regla. Null si la regla "
                  "depende de expresión de contexto (ej. edad, inclusión RUV)",
    )
    expresion_origen = models.TextField(
        blank=True,
        help_text="Expresión evaluada contra contexto del hogar/persona. "
                  "Ej: 'sexo == \"Hombre\" and 18 <= edad <= 49'",
    )
    valor_trigger = models.CharField(
        max_length=100, blank=True,
        help_text="Valor que debe tomar pregunta_origen para activar la regla",
    )
    pregunta_afectada = models.ForeignKey(
        Pregunta, on_delete=models.CASCADE, related_name="reglas_entrantes",
        null=True, blank=True,
    )
    capitulo_afectado = models.ForeignKey(
        Capitulo, on_delete=models.CASCADE, related_name="reglas_aplicables",
        null=True, blank=True,
        help_text="Si la regla afecta a un capítulo completo (ej. habilitar cap D/E)",
    )
    accion = models.CharField(max_length=20, choices=AccionSkipChoices.choices)
    descripcion = models.CharField(
        max_length=300, blank=True,
        help_text="Referencia al manual PDF, ej: 'Manual §6.1 — Cap D solo RUV ≥3 años'",
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Regla Skip Logic"
        verbose_name_plural = "Reglas Skip Logic"

    def __str__(self):
        origen = (
            f"{self.pregunta_origen.codigo_externo}={self.valor_trigger}"
            if self.pregunta_origen
            else f"expr:{self.expresion_origen[:30]}"
        )
        afectado = (
            self.pregunta_afectada.codigo_externo
            if self.pregunta_afectada
            else f"cap:{self.capitulo_afectado.codigo if self.capitulo_afectado else '?'}"
        )
        return f"{origen} → {self.accion} {afectado}"
