"""
Views del motor de formularios dinámico SRNI — alineadas con Diccionario V8.

Endpoints de solo lectura para estructura del instrumento +
endpoint POST de evaluación de skip logic (reglas HABILITAR/DESHABILITAR/OBLIGAR/FINALIZAR).
"""
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Perfil, InstrumentoVersion, Capitulo, Pregunta, ReglaSkipLogic, AccionSkipChoices
from .serializers import (
    PerfilSerializer, InstrumentoVersionSerializer,
    CapituloListSerializer, CapituloDetalleSerializer,
    PreguntaSerializer, EvaluarSkipLogicSerializer,
)


class ReadOnlyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]


@extend_schema_view(
    list=extend_schema(summary="Listar perfiles de instrumento", tags=["Formulario"]),
    retrieve=extend_schema(summary="Detalle de perfil con versiones", tags=["Formulario"]),
)
class PerfilViewSet(ReadOnlyViewSet):
    queryset = Perfil.objects.prefetch_related("versiones__capitulos").filter(activo=True)
    serializer_class = PerfilSerializer
    search_fields = ["codigo", "nombre"]


@extend_schema_view(
    list=extend_schema(summary="Listar versiones del instrumento", tags=["Formulario"]),
    retrieve=extend_schema(summary="Detalle de versión con capítulos", tags=["Formulario"]),
)
class InstrumentoVersionViewSet(ReadOnlyViewSet):
    queryset = InstrumentoVersion.objects.select_related("perfil").prefetch_related("capitulos")
    serializer_class = InstrumentoVersionSerializer
    filterset_fields = ["perfil"]


@extend_schema_view(
    list=extend_schema(summary="Listar capítulos de una versión", tags=["Formulario"]),
    retrieve=extend_schema(summary="Detalle de capítulo con preguntas completas", tags=["Formulario"]),
)
class CapituloViewSet(ReadOnlyViewSet):
    filterset_fields = ["instrumento", "poblacion_objetivo"]
    search_fields = ["codigo", "nombre"]

    def get_queryset(self):
        return Capitulo.objects.prefetch_related(
            "preguntas__opciones",
            "preguntas__reglas_entrantes__pregunta_origen",
        ).all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CapituloDetalleSerializer
        return CapituloListSerializer


@extend_schema_view(
    list=extend_schema(summary="Listar preguntas de un capítulo", tags=["Formulario"]),
    retrieve=extend_schema(summary="Detalle de pregunta con opciones y skip logic", tags=["Formulario"]),
)
class PreguntaViewSet(ReadOnlyViewSet):
    serializer_class = PreguntaSerializer
    filterset_fields = ["capitulo", "tipo", "nivel", "obligatoria", "activa"]
    search_fields = ["codigo_externo", "variable_bd", "texto"]

    def get_queryset(self):
        return Pregunta.objects.prefetch_related(
            "opciones",
            "reglas_entrantes__pregunta_origen",
        ).select_related("capitulo").all()


@extend_schema(
    summary="Evaluar skip logic del formulario",
    description=(
        "Recibe el ID de un capítulo, las respuestas actuales del encuestador "
        "y el contexto de la persona (edad, sexo, RUV). "
        "Devuelve los códigos de preguntas visibles/habilitadas aplicando las "
        "reglas HABILITAR/DESHABILITAR/OBLIGAR del instrumento."
    ),
    tags=["Formulario"],
    request=EvaluarSkipLogicSerializer,
    responses={200: {"type": "object", "properties": {
        "preguntas_visibles": {"type": "array", "items": {"type": "string"}},
        "preguntas_obligatorias": {"type": "array", "items": {"type": "string"}},
        "finalizar_capitulo": {"type": "boolean"},
        "total": {"type": "integer"},
    }}},
)
class EvaluarSkipLogicView(APIView):
    """
    Motor de evaluación de skip logic basado en reglas declarativas (ReglaSkipLogic).

    Lógica de visibilidad:
    - Una pregunta sin reglas DESHABILITAR entrantes activas es visible por defecto.
    - Una regla HABILITAR activa sobreescribe un DESHABILITAR previo.
    - Una regla OBLIGAR hace la pregunta obligatoria aunque no lo fuera.
    - Una regla FINALIZAR con cualquier opción cierra el capítulo.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EvaluarSkipLogicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        capitulo_id = serializer.validated_data["capitulo_id"]
        respuestas_raw = serializer.validated_data["respuestas"]
        contexto = serializer.validated_data.get("contexto", {})

        respuestas = {r["codigo_externo"]: r["valor"] for r in respuestas_raw}

        preguntas = Pregunta.objects.filter(
            capitulo_id=capitulo_id, activa=True
        ).prefetch_related(
            "reglas_entrantes__pregunta_origen"
        ).order_by("orden")

        reglas = list(ReglaSkipLogic.objects.filter(
            instrumento__capitulos__id=capitulo_id
        ).select_related("pregunta_origen", "pregunta_afectada", "capitulo_afectado"))

        visibles = set()
        obligatorias = set()
        finalizar = False

        for pregunta in preguntas:
            reglas_entrantes = [r for r in reglas if r.pregunta_afectada_id == pregunta.pk]

            if not reglas_entrantes:
                visibles.add(pregunta.codigo_externo)
                if pregunta.obligatoria:
                    obligatorias.add(pregunta.codigo_externo)
                continue

            deshabilitada = False
            for regla in reglas_entrantes:
                if self._regla_activa(regla, respuestas, contexto):
                    if regla.accion == AccionSkipChoices.DESHABILITAR:
                        deshabilitada = True
                    elif regla.accion == AccionSkipChoices.HABILITAR:
                        deshabilitada = False
                        visibles.add(pregunta.codigo_externo)
                    elif regla.accion == AccionSkipChoices.OBLIGAR:
                        visibles.add(pregunta.codigo_externo)
                        obligatorias.add(pregunta.codigo_externo)
                    elif regla.accion == AccionSkipChoices.FINALIZAR:
                        finalizar = True

            if not deshabilitada:
                visibles.add(pregunta.codigo_externo)
                if pregunta.obligatoria:
                    obligatorias.add(pregunta.codigo_externo)

        return Response({
            "preguntas_visibles": sorted(visibles),
            "preguntas_obligatorias": sorted(obligatorias),
            "finalizar_capitulo": finalizar,
            "total": len(visibles),
        })

    @staticmethod
    def _regla_activa(regla: ReglaSkipLogic, respuestas: dict, contexto: dict) -> bool:
        """Evalúa si una regla debe dispararse con las respuestas y contexto actuales."""
        if regla.pregunta_origen:
            valor_actual = respuestas.get(regla.pregunta_origen.codigo_externo, "")
            if not regla.valor_trigger:
                return bool(valor_actual)
            trigger = regla.valor_trigger
            if "," in trigger:
                return valor_actual in [v.strip() for v in trigger.split(",")]
            return valor_actual == trigger

        if regla.expresion_origen:
            try:
                return bool(eval(regla.expresion_origen, {}, contexto))  # noqa: S307
            except Exception:
                return False

        return False
