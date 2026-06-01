"""Serializers de auditoría — solo lectura, expuestos al panel web."""
from rest_framework import serializers
from .models import LogAcceso


class LogAccesoSerializer(serializers.ModelSerializer):
    """
    Vista de un registro de auditoría para supervisores/admins.
    No expone datos cifrados ni información sensible adicional al detalle ya capturado.
    """
    usuario_nombre = serializers.CharField(
        source='usuario.nombre_completo', read_only=True, default=''
    )
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)

    class Meta:
        model = LogAcceso
        fields = [
            'id',
            'codigo_usuario',
            'usuario_nombre',
            'accion', 'accion_display',
            'recurso',
            'recurso_id',
            'ip_origen',
            'resultado', 'resultado_display',
            'detalle',
            'timestamp',
        ]
        read_only_fields = fields  # registro inmutable
