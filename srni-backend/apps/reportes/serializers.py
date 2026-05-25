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


# ─── Sprint 13 — Vista supervisor ─────────────────────────────────────────────

class EncuestadorMetricaSerializer(serializers.Serializer):
    """Una fila por encuestador en la tabla del supervisor."""
    id = serializers.UUIDField()
    codigo_usuario = serializers.CharField()
    nombre_completo = serializers.CharField()
    perfil_codigo = serializers.CharField(allow_blank=True, allow_null=True)
    sesiones_total = serializers.IntegerField()
    sesiones_completadas = serializers.IntegerField()
    sesiones_en_progreso = serializers.IntegerField()
    sesiones_suspendidas = serializers.IntegerField()
    hogares_caracterizados = serializers.IntegerField()
    promedio_completado = serializers.FloatField()
    ultima_actividad = serializers.DateTimeField(allow_null=True)


class SupervisorTotalesSerializer(serializers.Serializer):
    """Agregado global del período (todos los encuestadores)."""
    sesiones_total = serializers.IntegerField()
    sesiones_completadas = serializers.IntegerField()
    sesiones_en_progreso = serializers.IntegerField()
    sesiones_suspendidas = serializers.IntegerField()
    hogares_caracterizados = serializers.IntegerField()
    promedio_completado = serializers.FloatField()


class SupervisorReporteSerializer(serializers.Serializer):
    """Respuesta del endpoint GET /api/reportes/supervisor/"""
    periodo_desde = serializers.DateField()
    periodo_hasta = serializers.DateField()
    encuestadores_activos = serializers.IntegerField()
    totales = SupervisorTotalesSerializer()
    encuestadores = EncuestadorMetricaSerializer(many=True)


# ─── Sprint 13 — Dashboard series temporales ─────────────────────────────────

class DashboardSerieDiariaSerializer(serializers.Serializer):
    """Un punto en la serie temporal."""
    fecha = serializers.DateField()
    sesiones_iniciadas = serializers.IntegerField()
    sesiones_completadas = serializers.IntegerField()


class DashboardDistribucionSerializer(serializers.Serializer):
    """Distribución de sesiones por código de instrumento."""
    instrumento_codigo = serializers.CharField()
    instrumento_nombre = serializers.CharField()
    total = serializers.IntegerField()


class DashboardSeriesSerializer(serializers.Serializer):
    """Respuesta del endpoint GET /api/reportes/dashboard/series/"""
    periodo_desde = serializers.DateField()
    periodo_hasta = serializers.DateField()
    serie_diaria = DashboardSerieDiariaSerializer(many=True)
    distribucion_por_instrumento = DashboardDistribucionSerializer(many=True)
