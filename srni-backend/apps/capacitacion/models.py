"""
Pruebas de capacitación — pre-test y post-test.

Contexto. La capacitación a los enlaces territoriales se dicta el 1, 3 y 8 de
septiembre de 2026. El plan contemplaba aplicar el mismo cuestionario antes y
después de cada jornada: usar el mismo instrumento en los dos momentos es lo que
permite medir la **ganancia** por persona, que es el dato que dice si la jornada
sirvió — no el puntaje final aislado.

Decisiones de diseño, y por qué:

* **Sin inicio de sesión.** Ninguno de los participantes tiene todavía credenciales
  del sistema (al 1-sep hay 1.161 usuarios y ninguna encuestadora ha entrado). Pedir
  contraseña dejaría la prueba sin responder. Se identifican con su **correo
  institucional**, que sí tienen y que además es el que figura en el listado de
  convocatoria.
* **Un intento por persona y por prueba.** Garantizado en base de datos con una
  restricción de unicidad sobre (correo normalizado, prueba), no solo en la
  interfaz: la interfaz se puede recargar, la restricción no.
* **La calificación se hace en el servidor.** El cuestionario que viaja al navegador
  **no lleva cuál es la opción correcta**; si la llevara, bastaría con abrir las
  herramientas del navegador para tener el examen resuelto.
"""
import uuid

from django.core.validators import MinValueValidator
from django.db import models


def normalizar_correo(correo: str) -> str:
    """Minúsculas y sin espacios. Es la forma en que se compara la identidad."""
    return (correo or '').strip().lower()


class Prueba(models.Model):
    """Un cuestionario aplicable (pre-test o post-test de una capacitación)."""

    class Momento(models.TextChoices):
        PRE = 'PRE', 'Pre-test'
        POST = 'POST', 'Post-test'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(
        max_length=60, unique=True,
        help_text='Identificador de la URL pública. Ej: capacitacion-2026-09-pre')
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    momento = models.CharField(max_length=4, choices=Momento.choices)
    # Emparejar pre y post permite calcular la ganancia por persona.
    pareja = models.CharField(
        max_length=60, blank=True, db_index=True,
        help_text='Mismo valor en el pre y el post que se comparan entre sí.')
    abierta = models.BooleanField(
        default=True,
        help_text='Si está cerrada, no admite nuevos intentos.')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Prueba de capacitación'
        verbose_name_plural = 'Pruebas de capacitación'
        ordering = ['pareja', 'momento']

    def __str__(self) -> str:
        return f'{self.titulo} ({self.get_momento_display()})'

    @property
    def total_preguntas(self) -> int:
        return self.preguntas.count()


class PreguntaPrueba(models.Model):
    """Una pregunta de selección múltiple con una sola respuesta correcta."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='preguntas')
    orden = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    enunciado = models.TextField()
    # [{"clave": "A", "texto": "..."}, ...] — el orden de la lista es el de pantalla.
    opciones = models.JSONField(default=list)
    correcta = models.CharField(
        max_length=4,
        help_text='Clave de la opción correcta. NUNCA se envía al navegador.')
    explicacion = models.TextField(
        blank=True,
        help_text='Se muestra al final, solo sobre las que la persona falló.')

    class Meta:
        verbose_name = 'Pregunta de prueba'
        verbose_name_plural = 'Preguntas de prueba'
        ordering = ['prueba', 'orden']
        constraints = [
            models.UniqueConstraint(fields=['prueba', 'orden'],
                                    name='uniq_pregunta_orden_por_prueba'),
        ]

    def __str__(self) -> str:
        return f'{self.orden}. {self.enunciado[:60]}'


class IntentoPrueba(models.Model):
    """
    La presentación de una persona. Uno solo por correo y prueba.

    Se guarda el detalle de lo respondido (no solo el puntaje) porque el valor
    para la Subdirección está en saber **qué** se falló: una pregunta que falla
    el 70 % del grupo señala un tema mal explicado, no personas mal preparadas.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='intentos')

    correo = models.EmailField()
    correo_normalizado = models.CharField(max_length=254, db_index=True, editable=False)
    nombre = models.CharField(max_length=180, blank=True)
    territorial = models.CharField(max_length=120, blank=True)

    # {"<pregunta_id>": "B", ...}
    respuestas = models.JSONField(default=dict)
    puntaje = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    segundos = models.PositiveIntegerField(
        default=0, help_text='Cuánto tardó en resolverla.')
    ip = models.GenericIPAddressField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Intento de prueba'
        verbose_name_plural = 'Intentos de prueba'
        ordering = ['-creado_en']
        constraints = [
            models.UniqueConstraint(fields=['prueba', 'correo_normalizado'],
                                    name='uniq_intento_por_correo_y_prueba'),
        ]
        indexes = [models.Index(fields=['prueba', '-creado_en'])]

    def save(self, *args, **kwargs):
        self.correo_normalizado = normalizar_correo(self.correo)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.correo_normalizado} — {self.puntaje}/{self.total}'

    @property
    def porcentaje(self) -> int:
        return round(self.puntaje * 100 / self.total) if self.total else 0

    @property
    def nivel(self) -> str:
        """Escala del plan de capacitación (Anexo A), sobre porcentaje."""
        p = self.porcentaje
        if p >= 87:
            return 'APROPIADO'
        if p >= 67:
            return 'SUFICIENTE'
        if p >= 47:
            return 'BASICO'
        return 'INSUFICIENTE'
