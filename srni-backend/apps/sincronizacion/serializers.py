"""Serializers del ledger de escritura a Oracle (solo lectura)."""
from rest_framework import serializers

from .models import RegistroEscrituraOracle


class RegistroEscrituraSerializer(serializers.ModelSerializer):
    """
    Un paso del ledger.

    No expone `payload` ni `bloque_plsql`: aunque los binds con PII van redactados,
    son detalle de depuración y no tienen por qué viajar a un panel web. Quien los
    necesite los tiene en el admin y en la base.
    """
    hogar_codigo = serializers.CharField(source="hogar.codigo_hogar", read_only=True)

    class Meta:
        model = RegistroEscrituraOracle
        fields = ["id", "hogar_codigo", "paso", "estado", "intento",
                  "destino_entorno", "destino_hog_codigo", "destino_per_idpersona",
                  "resultado", "creado_en", "actualizado_en"]
        read_only_fields = fields


class EstadoHogarSerializer(serializers.Serializer):
    """Resumen por hogar: lo que un supervisor necesita ver de un vistazo."""
    hogar_codigo = serializers.CharField()
    destino = serializers.CharField()
    hog_codigo_oracle = serializers.CharField()
    estado = serializers.CharField()
    pasos_totales = serializers.IntegerField()
    pasos_verificados = serializers.IntegerField()
    pasos_fallidos = serializers.IntegerField()
    ultima_actualizacion = serializers.DateTimeField(allow_null=True)
