"""
Serializers del motor de formularios dinámico SRNI.
Replica la estructura vivanto.db del APK: Instrumento → Tema → Pregunta → Opción.
La lógica de derivación (skip logic) se expone en PreguntaDerivadaSerializer
para que el frontend evalúe visibilidad de preguntas localmente.
"""
from rest_framework import serializers
from .models import Instrumento, Tema, Pregunta, OpcionRespuesta, PreguntaDerivada


class OpcionRespuestaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionRespuesta
        fields = ['id', 'codigo', 'texto', 'orden', 'activa']


class PreguntaDerivadaSerializer(serializers.ModelSerializer):
    """
    Expone la regla de skip logic para que el frontend evalúe
    qué preguntas mostrar u ocultar según las respuestas actuales.
    """
    pregunta_padre_codigo = serializers.CharField(
        source='pregunta_padre.codigo', read_only=True
    )
    pregunta_hija_codigo = serializers.CharField(
        source='pregunta_hija.codigo', read_only=True
    )

    class Meta:
        model = PreguntaDerivada
        fields = [
            'id',
            'pregunta_padre', 'pregunta_padre_codigo',
            'pregunta_hija', 'pregunta_hija_codigo',
            'operador', 'valor_condicion',
        ]


class PreguntaSerializer(serializers.ModelSerializer):
    """
    Serializer completo de pregunta: incluye opciones y reglas de derivación
    donde esta pregunta es la hija (condiciones que la habilitan).
    """
    opciones = OpcionRespuestaSerializer(many=True, read_only=True)
    condiciones_habilitacion = PreguntaDerivadaSerializer(
        source='derivaciones_como_hija', many=True, read_only=True
    )

    class Meta:
        model = Pregunta
        fields = [
            'id', 'codigo', 'texto', 'texto_ayuda',
            'tipo_respuesta', 'orden', 'requerida', 'activa',
            'columna_padre', 'validacion',
            'opciones', 'condiciones_habilitacion',
        ]


class TemaListSerializer(serializers.ModelSerializer):
    """Lista de temas — sin preguntas, para renderizar el índice de los 54 módulos."""
    total_preguntas = serializers.IntegerField(
        source='preguntas.count', read_only=True
    )

    class Meta:
        model = Tema
        fields = ['id', 'codigo', 'nombre', 'orden', 'activo', 'total_preguntas']


class TemaDetalleSerializer(serializers.ModelSerializer):
    """Detalle de un tema con todas sus preguntas."""
    preguntas = PreguntaSerializer(many=True, read_only=True)

    class Meta:
        model = Tema
        fields = ['id', 'codigo', 'nombre', 'orden', 'activo', 'preguntas']


class InstrumentoSerializer(serializers.ModelSerializer):
    temas = TemaListSerializer(many=True, read_only=True)
    total_temas = serializers.IntegerField(source='temas.count', read_only=True)

    class Meta:
        model = Instrumento
        fields = ['id', 'codigo', 'nombre', 'version', 'vigente', 'total_temas', 'temas']


# ---------------------------------------------------------------------------
# Serializer para el motor de evaluación de skip logic (endpoint POST)
# ---------------------------------------------------------------------------

class RespuestaActualSerializer(serializers.Serializer):
    """Par (pregunta_id, valor) que representa una respuesta actual del usuario."""
    pregunta_id = serializers.IntegerField()
    valor = serializers.CharField(allow_blank=True)


class EvaluarSkipLogicSerializer(serializers.Serializer):
    """
    Input para POST /api/formulario/evaluar-skip-logic/
    Recibe el tema y las respuestas actuales; devuelve IDs visibles.
    """
    tema_id = serializers.IntegerField()
    respuestas = RespuestaActualSerializer(many=True)
