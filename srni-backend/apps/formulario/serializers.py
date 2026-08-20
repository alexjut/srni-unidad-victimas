"""
Serializers del motor de formularios dinámico SRNI — alineados con Diccionario V8.

Jerarquía de lectura:
  Instrumento → Capitulo → Pregunta → OpcionRespuesta
                         ↘ ReglaSkipLogic
"""
from rest_framework import serializers
from .models import Instrumento, Capitulo, Pregunta, OpcionRespuesta, ReglaSkipLogic


class OpcionRespuestaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionRespuesta
        fields = ["id", "valor", "etiqueta", "id_resp_vivanto", "orden", "finaliza_capitulo"]


class ReglaSkipLogicSerializer(serializers.ModelSerializer):
    pregunta_origen_codigo = serializers.CharField(
        source="pregunta_origen.codigo_externo", read_only=True
    )
    pregunta_afectada_codigo = serializers.CharField(
        source="pregunta_afectada.codigo_externo", read_only=True
    )
    capitulo_afectado_codigo = serializers.CharField(
        source="capitulo_afectado.codigo", read_only=True
    )

    class Meta:
        model = ReglaSkipLogic
        fields = [
            "id",
            "pregunta_origen", "pregunta_origen_codigo",
            "expresion_origen", "valor_trigger",
            "pregunta_afectada", "pregunta_afectada_codigo",
            "capitulo_afectado", "capitulo_afectado_codigo",
            "accion", "descripcion",
        ]


class PreguntaSerializer(serializers.ModelSerializer):
    opciones = OpcionRespuestaSerializer(many=True, read_only=True)
    reglas_entrantes = ReglaSkipLogicSerializer(many=True, read_only=True)

    class Meta:
        model = Pregunta
        fields = [
            "id", "codigo_externo", "no_pregunta", "variable_bd",
            "texto", "descripcion_ayuda", "tipo", "nivel",
            "orden", "obligatoria", "activa", "es_precargada",
            "fuente_precarga", "validaciones",
            "opciones", "reglas_entrantes",
        ]


class CapituloListSerializer(serializers.ModelSerializer):
    total_preguntas = serializers.IntegerField(source="preguntas.count", read_only=True)

    class Meta:
        model = Capitulo
        fields = [
            "id", "codigo", "nombre", "orden",
            "poblacion_objetivo", "aplicabilidad", "total_preguntas",
        ]


class CapituloDetalleSerializer(serializers.ModelSerializer):
    preguntas = PreguntaSerializer(many=True, read_only=True)

    class Meta:
        model = Capitulo
        fields = [
            "id", "codigo", "nombre", "orden",
            "objetivo", "poblacion_objetivo", "aplicabilidad",
            "preguntas",
        ]


class InstrumentoSerializer(serializers.ModelSerializer):
    capitulos = CapituloListSerializer(many=True, read_only=True)
    total_capitulos = serializers.IntegerField(source="capitulos.count", read_only=True)
    vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Instrumento
        fields = [
            "id", "codigo", "nombre", "version",
            "activo", "vigente_desde", "vigente_hasta", "vigente",
            "fuente_documental", "total_capitulos", "capitulos",
        ]


# ---------------------------------------------------------------------------
# Serializer para descarga completa del instrumento (offline-first)
# ---------------------------------------------------------------------------

class CapituloConPreguntasSerializer(serializers.ModelSerializer):
    """Capítulo con preguntas + skip logic incluidos — para descarga offline."""
    preguntas = PreguntaSerializer(many=True, read_only=True)

    class Meta:
        model = Capitulo
        fields = [
            "id", "codigo", "nombre", "orden", "nivel",
            "objetivo", "poblacion_objetivo", "aplicabilidad",
            "preguntas",
        ]


class InstrumentoCompletoSerializer(serializers.ModelSerializer):
    """
    Instrumento completo listo para descarga offline.
    Una sola llamada devuelve: instrumento + capítulos + preguntas + opciones + skip logic.
    """
    vigente = serializers.BooleanField(read_only=True)
    capitulos = CapituloConPreguntasSerializer(many=True, read_only=True)
    reglas = ReglaSkipLogicSerializer(many=True, read_only=True)

    class Meta:
        model = Instrumento
        fields = [
            "id", "codigo", "nombre", "version",
            "vigente_desde", "vigente",
            "fuente_documental", "capitulos", "reglas",
        ]


# ---------------------------------------------------------------------------
# Serializers para el motor de evaluación de skip logic (endpoint POST)
# ---------------------------------------------------------------------------

class RespuestaActualSerializer(serializers.Serializer):
    """Par (codigo_externo, valor) que representa una respuesta actual del usuario."""
    codigo_externo = serializers.CharField()
    valor = serializers.CharField(allow_blank=True)


class ContextoPersonaSerializer(serializers.Serializer):
    """Contexto de la persona para evaluar reglas de expresión.

    Los nombres son los que aparecen EN LAS EXPRESIONES de los fixtures
    (`edad >= 18`, `sexo == '2'`, `etnia != 'ninguno'`, `ruv_incluido == false`).
    Antes faltaban `etnia` y `ruv_incluido`, y como un Serializer descarta lo que
    no declara, un cliente podía mandarlos y el motor no los veía nunca: las
    reglas étnicas y de RUV no se disparaban por este endpoint aunque el cliente
    hiciera todo bien.

    Ninguno lleva `default`. Un default como `edad = 0` no es «no sé la edad»:
    es «tiene cero años», y con eso una regla `edad < 5` se dispararía para todo
    el mundo. Ausente tiene que quedar ausente — el evaluador ya trata lo
    desconocido como condición no cumplida.
    """
    edad = serializers.IntegerField(required=False)
    sexo = serializers.CharField(required=False, allow_blank=True)
    etnia = serializers.CharField(required=False, allow_blank=True)
    ruv_incluido = serializers.BooleanField(required=False)
    # Se mantienen por compatibilidad con clientes que ya los mandaban.
    incluido_ruv = serializers.BooleanField(required=False)
    tipo_persona = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # `incluido_ruv` fue el nombre viejo; las expresiones dicen `ruv_incluido`.
        if 'ruv_incluido' not in attrs and 'incluido_ruv' in attrs:
            attrs['ruv_incluido'] = attrs['incluido_ruv']
        return attrs


class EvaluarSkipLogicSerializer(serializers.Serializer):
    """
    Input para POST /api/formulario/evaluar-skip-logic/
    Recibe el capítulo, respuestas actuales y contexto de persona/hogar.
    Devuelve códigos de preguntas visibles.
    """
    capitulo_id = serializers.UUIDField()
    respuestas = RespuestaActualSerializer(many=True)
    contexto = ContextoPersonaSerializer(required=False, default=dict)
