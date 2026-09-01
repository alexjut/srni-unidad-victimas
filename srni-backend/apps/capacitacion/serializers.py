"""Serializadores de las pruebas de capacitación."""
from rest_framework import serializers

from .models import IntentoPrueba, PreguntaPrueba, Prueba


class PreguntaPublicaSerializer(serializers.ModelSerializer):
    """
    La pregunta tal como viaja al navegador.

    No incluye `correcta` ni `explicacion`: si las incluyera, el examen estaría
    resuelto con abrir las herramientas del navegador. La calificación se hace
    en el servidor.
    """

    class Meta:
        model = PreguntaPrueba
        fields = ['id', 'orden', 'enunciado', 'opciones']


class PruebaPublicaSerializer(serializers.ModelSerializer):
    preguntas = PreguntaPublicaSerializer(many=True, read_only=True)
    total_preguntas = serializers.IntegerField(read_only=True)

    class Meta:
        model = Prueba
        fields = ['codigo', 'titulo', 'descripcion', 'momento', 'abierta',
                  'total_preguntas', 'preguntas']


class ResponderSerializer(serializers.Serializer):
    """Lo que envía el participante al terminar."""
    correo = serializers.EmailField()
    nombre = serializers.CharField(max_length=180, required=False, allow_blank=True)
    territorial = serializers.CharField(max_length=120, required=False, allow_blank=True)
    respuestas = serializers.DictField(child=serializers.CharField(allow_blank=True))
    segundos = serializers.IntegerField(required=False, min_value=0, default=0)


class IntentoResumenSerializer(serializers.ModelSerializer):
    """Fila del tablero interno. Incluye porcentaje y nivel ya calculados."""
    porcentaje = serializers.IntegerField(read_only=True)
    nivel = serializers.CharField(read_only=True)
    prueba_codigo = serializers.CharField(source='prueba.codigo', read_only=True)
    momento = serializers.CharField(source='prueba.momento', read_only=True)

    class Meta:
        model = IntentoPrueba
        fields = ['id', 'prueba_codigo', 'momento', 'correo', 'nombre', 'territorial',
                  'puntaje', 'total', 'porcentaje', 'nivel', 'segundos', 'creado_en']
