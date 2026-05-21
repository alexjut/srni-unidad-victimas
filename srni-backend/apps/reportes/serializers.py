"""
Serializers para el módulo de reportes de producción.
"""
from rest_framework import serializers


class ResumenInstrumentoSerializer(serializers.Serializer):
    instrumento_id = serializers.UUIDField()
    instrumento_nombre = serializers.CharField()
    perfil_codigo = serializers.CharField()
    total = serializers.IntegerField()
    completadas = serializers.IntegerField()
    promedio_completado = serializers.FloatField()


class SesionResumenReporteSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    hogar_id = serializers.UUIDField()
    instrumento_nombre = serializers.CharField()
    perfil_codigo = serializers.CharField()
    estado = serializers.CharField()
    estado_display = serializers.CharField()
    porcentaje_completado = serializers.IntegerField()
    respuestas_total = serializers.IntegerField()
    fecha_inicio = serializers.DateTimeField()
    fecha_fin = serializers.DateTimeField(allow_null=True)
    duracion_minutos = serializers.FloatField(allow_null=True)


class ProduccionEncuestadorSerializer(serializers.Serializer):
    encuestador_id = serializers.UUIDField()
    encuestador_nombre = serializers.CharField()
    periodo_desde = serializers.DateField()
    periodo_hasta = serializers.DateField()
    sesiones_total = serializers.IntegerField()
    sesiones_completadas = serializers.IntegerField()
    sesiones_en_progreso = serializers.IntegerField()
    sesiones_suspendidas = serializers.IntegerField()
    hogares_caracterizados = serializers.IntegerField()
    respuestas_total = serializers.IntegerField()
    promedio_completado = serializers.FloatField()
    por_instrumento = ResumenInstrumentoSerializer(many=True)
    sesiones_recientes = SesionResumenReporteSerializer(many=True)
