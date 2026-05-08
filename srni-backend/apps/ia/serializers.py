from rest_framework import serializers
from .models import ConsentimientoIA, SesionIA


class ConsentimientoIASerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentimientoIA
        fields = ['id', 'sesion_encuesta', 'acepto', 'firma_digital', 'creado_en']
        read_only_fields = ['id', 'firma_digital', 'creado_en']


class ConsentimientoIAInputSerializer(serializers.Serializer):
    sesion_encuesta_id = serializers.UUIDField()
    acepto = serializers.BooleanField()


class MapearAudioInputSerializer(serializers.Serializer):
    sesion_encuesta_id = serializers.UUIDField()
    pregunta_id = serializers.UUIDField()
    texto_transcrito = serializers.CharField(
        max_length=2000,
        help_text='Texto ya transcrito del audio del encuestado.',
    )


class MapearAudioOutputSerializer(serializers.Serializer):
    sugerencia = serializers.CharField(allow_blank=True)
    confianza = serializers.FloatField()
    modelo = serializers.CharField()


class EstadoIASerializer(serializers.Serializer):
    activo = serializers.BooleanField()
    consentimiento_id = serializers.UUIDField(allow_null=True)
    sesion_ia_id = serializers.UUIDField(allow_null=True)
    total_llamadas = serializers.IntegerField()


class SesionIASerializer(serializers.ModelSerializer):
    class Meta:
        model = SesionIA
        fields = ['id', 'sesion_encuesta', 'inicio', 'fin', 'total_llamadas']
        read_only_fields = ['id', 'inicio', 'total_llamadas']


# ─── Batch: procesar entrevista completa ─────────────────────────────────────

class PreguntaBatchSerializer(serializers.Serializer):
    pregunta_id = serializers.UUIDField()
    codigo_externo = serializers.CharField()
    texto = serializers.CharField()
    tipo = serializers.CharField()
    opciones = serializers.ListField(child=serializers.CharField(), default=list)


class ProcesarEntrevistaInputSerializer(serializers.Serializer):
    sesion_encuesta_id = serializers.UUIDField()
    capitulo_id = serializers.UUIDField()
    transcripcion_completa = serializers.CharField(max_length=50000)
    preguntas = PreguntaBatchSerializer(many=True)


class ResultadoBatchSerializer(serializers.Serializer):
    pregunta_id = serializers.UUIDField()
    codigo_externo = serializers.CharField()
    sugerencia = serializers.CharField(allow_null=True)
    confianza = serializers.FloatField()
    razonamiento = serializers.CharField()


class ProcesarEntrevistaOutputSerializer(serializers.Serializer):
    resultados = ResultadoBatchSerializer(many=True)
    total_preguntas = serializers.IntegerField()
    con_sugerencia = serializers.IntegerField()
    sin_sugerencia = serializers.IntegerField()
