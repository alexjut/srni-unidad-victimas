"""
Serializers de Encuestas SRNI.
"""
from rest_framework import serializers
from apps.formulario.serializers import PreguntaSerializer
from .models import SesionEncuesta, RespuestaEncuesta


class RespuestaEncuestaSerializer(serializers.ModelSerializer):
    pregunta_codigo = serializers.CharField(
        source='pregunta.codigo_externo', read_only=True
    )
    pregunta_texto = serializers.CharField(
        source='pregunta.texto', read_only=True
    )

    class Meta:
        model = RespuestaEncuesta
        fields = [
            'id', 'sesion', 'pregunta',
            'pregunta_codigo', 'pregunta_texto',
            'valor', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at', 'pregunta_codigo', 'pregunta_texto']


class SesionEncuestaListSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    instrumento_codigo = serializers.CharField(
        source='instrumento.codigo', read_only=True, default=None
    )
    instrumento_nombre = serializers.CharField(
        source='instrumento.nombre', read_only=True, default=None
    )
    instrumento_numero = serializers.CharField(
        source='instrumento.version', read_only=True, default=None
    )
    encuestador_nombre = serializers.CharField(
        source='encuestador.nombre_completo', read_only=True, default=None
    )

    class Meta:
        model = SesionEncuesta
        fields = [
            'id', 'hogar',
            'instrumento', 'instrumento_nombre', 'instrumento_numero',
            'encuestador', 'encuestador_nombre',
            'estado', 'estado_display',
            'porcentaje_completado',
            'fecha_inicio', 'fecha_fin',
            'created_at', 'updated_at',
        ]


class SesionEncuestaDetalleSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    instrumento_codigo = serializers.CharField(
        source='instrumento.codigo', read_only=True, default=None
    )
    instrumento_nombre = serializers.CharField(
        source='instrumento.nombre', read_only=True, default=None
    )
    instrumento_numero = serializers.CharField(
        source='instrumento.version', read_only=True, default=None
    )
    respuestas = RespuestaEncuestaSerializer(many=True, read_only=True)
    total_respuestas = serializers.IntegerField(source='respuestas.count', read_only=True)

    class Meta:
        model = SesionEncuesta
        fields = [
            'id', 'hogar',
            'instrumento', 'instrumento_codigo', 'instrumento_nombre', 'instrumento_numero',
            'ruta_entrevista',
            'encuestador',
            'estado', 'estado_display',
            'porcentaje_completado',
            'fecha_inicio', 'fecha_fin',
            'observaciones',
            'respuestas', 'total_respuestas',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'porcentaje_completado', 'fecha_inicio',
            'estado_display', 'instrumento_codigo', 'instrumento_nombre', 'instrumento_numero',
            'respuestas', 'total_respuestas',
            'created_at', 'updated_at',
        ]


class ResponderPreguntaSerializer(serializers.Serializer):
    """Input para POST /api/encuestas/{id}/responder/"""
    pregunta_id = serializers.UUIDField()
    valor = serializers.CharField(allow_blank=True, max_length=50_000)

    def validate_valor(self, value):
        return value.strip()


class BulkItemSerializer(serializers.Serializer):
    """Un ítem dentro del bulk — pregunta_id + valor."""
    pregunta_id = serializers.UUIDField()
    valor = serializers.CharField(allow_blank=True, max_length=50_000)

    def validate_valor(self, value):
        return value.strip()


class ResponderBulkSerializer(serializers.Serializer):
    """Input para POST /api/encuestas/{id}/responder-bulk/"""
    respuestas = BulkItemSerializer(many=True)

    def validate_respuestas(self, value):
        if not value:
            raise serializers.ValidationError('Se requiere al menos una respuesta.')
        if len(value) > 2_000:
            raise serializers.ValidationError('Máximo 2000 respuestas por lote.')
        return value


class FinalizarSesionSerializer(serializers.Serializer):
    """Input opcional para POST /api/encuestas/{id}/finalizar/"""
    observaciones = serializers.CharField(
        allow_blank=True, required=False, default='', max_length=2_000,
    )
