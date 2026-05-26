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
            'miembro',          # Sprint 21 — null si HOGAR, FK a MiembroHogar si PERSONA
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

    direccion_territorial_nombre = serializers.CharField(
        source='direccion_territorial.nombre', read_only=True, default=None,
    )

    class Meta:
        model = SesionEncuesta
        fields = [
            'id', 'hogar',
            'instrumento', 'instrumento_codigo', 'instrumento_nombre', 'instrumento_numero',
            'encuestador', 'encuestador_nombre',
            'direccion_territorial', 'direccion_territorial_nombre',
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
    # Sprint 19 — campos legibles de ubicación de atención (read-only).
    # Los IDs (direccion_territorial, departamento_atencion, etc.) los expone
    # el ModelSerializer base; estos son los nombres para mostrar.
    direccion_territorial_nombre = serializers.CharField(
        source='direccion_territorial.nombre', read_only=True, default=None,
    )
    departamento_atencion_nombre = serializers.CharField(
        source='departamento_atencion.nombre', read_only=True, default=None,
    )
    municipio_atencion_nombre = serializers.CharField(
        source='municipio_atencion.nombre', read_only=True, default=None,
    )
    punto_atencion_nombre = serializers.CharField(
        source='punto_atencion.nombre', read_only=True, default=None,
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
            'direccion_territorial', 'direccion_territorial_nombre',
            'departamento_atencion', 'departamento_atencion_nombre',
            'municipio_atencion', 'municipio_atencion_nombre',
            'punto_atencion', 'punto_atencion_nombre',
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
            'direccion_territorial_nombre', 'departamento_atencion_nombre',
            'municipio_atencion_nombre', 'punto_atencion_nombre',
            'respuestas', 'total_respuestas',
            'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        """
        Sprint 19 — valida coherencia de cascada DT → Depto/Punto → Municipio.
        Se valida solo si los campos vienen presentes y no nulos (creación con
        ubicación). Una sesión puede crearse sin ubicación y completarse después.
        """
        # En update parcial, leer el valor existente cuando no venga en attrs.
        instance = getattr(self, 'instance', None)
        def get(name):
            if name in attrs:
                return attrs[name]
            return getattr(instance, name, None) if instance else None

        dt = get('direccion_territorial')
        depto = get('departamento_atencion')
        mun = get('municipio_atencion')
        punto = get('punto_atencion')

        if depto and dt and not dt.departamentos.filter(pk=depto.pk).exists():
            raise serializers.ValidationError({
                'departamento_atencion': 'No pertenece a la Dirección Territorial indicada.',
            })
        if mun and depto and mun.departamento_id != depto.pk:
            raise serializers.ValidationError({
                'municipio_atencion': 'No pertenece al Departamento indicado.',
            })
        if punto and dt and punto.direccion_territorial_id != dt.pk:
            raise serializers.ValidationError({
                'punto_atencion': 'No pertenece a la Dirección Territorial indicada.',
            })
        return attrs


class ResponderPreguntaSerializer(serializers.Serializer):
    """Input para POST /api/encuestas/{id}/responder/"""
    pregunta_id = serializers.UUIDField()
    miembro_id = serializers.UUIDField(required=False, allow_null=True)
    valor = serializers.CharField(allow_blank=True, max_length=50_000)

    def validate_valor(self, value):
        return value.strip()


class BulkItemSerializer(serializers.Serializer):
    """Un ítem dentro del bulk — pregunta_id + miembro_id (opcional) + valor."""
    pregunta_id = serializers.UUIDField()
    miembro_id = serializers.UUIDField(required=False, allow_null=True)
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
