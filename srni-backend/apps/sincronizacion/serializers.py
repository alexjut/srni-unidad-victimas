"""Serializers del ledger de escritura a Oracle (solo lectura)."""
from rest_framework import serializers

from .models import CaracterizacionLegacy, RegistroEscrituraOracle


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


class CaracterizacionLegacySerializer(serializers.ModelSerializer):
    """
    Una caracterización que el encuestador hizo en la aplicación vieja.

    Lleva `visible_en_reportes` porque sin esa columna esto sería una lista de
    códigos. Con ella el encuestador puede ver que un trabajo suyo **no está
    contando**, que es la información que hoy no tiene por ningún lado.

    No expone PII: el modelo no la guarda. Es el recibo, no la encuesta.
    """
    encuestador = serializers.CharField(source="usuario_creador", read_only=True)

    class Meta:
        model = CaracterizacionLegacy
        fields = ["hog_codigo", "encuestador", "estado", "creado_en_legacy",
                  "fecha_estado", "miembros", "respuestas_definitivas",
                  "respuestas_trabajo", "capitulos", "veredicto",
                  "visible_en_reportes"]
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
