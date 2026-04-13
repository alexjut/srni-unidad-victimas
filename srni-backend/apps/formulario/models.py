"""
Motor de formularios SRNI.
Replica la estructura de vivanto.db del APK original:
  vivanto_instrumentos → Instrumento
  vivanto_temas        → Tema
  vivanto_preguntas    → Pregunta
  vivanto_opciones     → OpcionRespuesta
  vivanto_derivadas    → PreguntaDerivada
"""
from django.db import models


class Instrumento(models.Model):
    """Versión del instrumento de caracterización (p.ej. PAARI 4.1)."""
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default='1.0')
    vigente = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Instrumento'
        verbose_name_plural = 'Instrumentos'

    def __str__(self):
        return f'{self.nombre} v{self.version}'


class Tema(models.Model):
    """
    Módulo / sección del formulario.
    El campo 'orden' preserva el mismo orden del APK original.
    """
    instrumento = models.ForeignKey(
        Instrumento, on_delete=models.CASCADE, related_name='temas'
    )
    codigo = models.CharField(max_length=20, db_index=True)
    nombre = models.CharField(max_length=300)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden']
        unique_together = [('instrumento', 'codigo')]
        verbose_name = 'Tema'
        verbose_name_plural = 'Temas'

    def __str__(self):
        return f'{self.orden:02d}. {self.nombre}'


class Pregunta(models.Model):
    """
    Pregunta del formulario con metadatos para el motor de renderizado.
    tipo_respuesta controla qué componente Angular renderiza el encuestador.
    """
    TIPO_RESPUESTA = [
        ('TEXTO', 'Texto libre'),
        ('NUMERICO', 'Numérico'),
        ('FECHA', 'Fecha'),
        ('OPCION_UNICA', 'Selección única'),
        ('OPCION_MULTIPLE', 'Selección múltiple'),
        ('SINO', 'Sí / No'),
        ('TABLA', 'Tabla dinámica'),
        ('CALCULO', 'Campo calculado'),
    ]

    tema = models.ForeignKey(Tema, on_delete=models.CASCADE, related_name='preguntas')
    codigo = models.CharField(max_length=30, db_index=True)
    texto = models.TextField()
    texto_ayuda = models.TextField(blank=True)
    tipo_respuesta = models.CharField(max_length=20, choices=TIPO_RESPUESTA, default='OPCION_UNICA')
    orden = models.PositiveSmallIntegerField(default=0)
    requerida = models.BooleanField(default=True)
    activa = models.BooleanField(default=True)
    # Para preguntas de tabla: nombre de la columna padre
    columna_padre = models.CharField(max_length=50, blank=True)
    # Validación extra en JSON: {"min": 0, "max": 100, "regex": "..."}
    validacion = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['orden']
        unique_together = [('tema', 'codigo')]
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'

    def __str__(self):
        return f'[{self.codigo}] {self.texto[:80]}'


class OpcionRespuesta(models.Model):
    """Opción de respuesta para preguntas de selección (única o múltiple)."""
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    codigo = models.CharField(max_length=20)
    texto = models.CharField(max_length=500)
    orden = models.PositiveSmallIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden']
        unique_together = [('pregunta', 'codigo')]
        verbose_name = 'Opción de Respuesta'
        verbose_name_plural = 'Opciones de Respuesta'

    def __str__(self):
        return f'{self.codigo}: {self.texto}'


class PreguntaDerivada(models.Model):
    """
    Lógica de derivación (skip logic):
    si 'pregunta_padre' tiene el valor 'valor_condicion'
    entonces 'pregunta_hija' se muestra / activa.
    """
    OPERADOR = [
        ('EQ', 'Igual a'),
        ('NEQ', 'Diferente de'),
        ('GT', 'Mayor que'),
        ('GTE', 'Mayor o igual'),
        ('LT', 'Menor que'),
        ('LTE', 'Menor o igual'),
        ('IN', 'Está en'),
        ('NOTNULL', 'Tiene respuesta'),
    ]

    pregunta_padre = models.ForeignKey(
        Pregunta, on_delete=models.CASCADE, related_name='derivaciones_como_padre'
    )
    pregunta_hija = models.ForeignKey(
        Pregunta, on_delete=models.CASCADE, related_name='derivaciones_como_hija'
    )
    operador = models.CharField(max_length=10, choices=OPERADOR, default='EQ')
    # El valor de comparación se serializa como string; el front lo convierte
    valor_condicion = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Pregunta Derivada'
        verbose_name_plural = 'Preguntas Derivadas'
        unique_together = [('pregunta_padre', 'pregunta_hija', 'valor_condicion')]

    def __str__(self):
        return f'{self.pregunta_padre.codigo} {self.operador} "{self.valor_condicion}" → {self.pregunta_hija.codigo}'
