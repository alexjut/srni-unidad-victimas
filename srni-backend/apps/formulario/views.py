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

from .models import Instrumento, Capitulo, Pregunta, ReglaSkipLogic
from django.shortcuts import get_object_or_404
from .serializers import (
    InstrumentoSerializer,
    CapituloListSerializer, CapituloDetalleSerializer,
    PreguntaSerializer, InstrumentoCompletoSerializer, EvaluarSkipLogicSerializer,
)

# El motor de skip-logic vive en `skiplogic.py`, no acá. Se reexportan estos
# nombres porque el resto del backend ya los importaba desde este módulo.
from .skiplogic import (  # noqa: F401
    evaluar_expresion_segura,
    valores_seleccionados as _valores_seleccionados,
    regla_activa,
    calcular_visibles,
)


class ReadOnlyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    # Los instrumentos, capítulos y preguntas son información de referencia
    # de solo lectura: cualquier usuario autenticado (campo, supervisión o
    # administración) puede consultarlos. No exige puede_caracterizar (Bug 1).
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]


@extend_schema_view(
    list=extend_schema(summary="Listar instrumentos activos", tags=["Formulario"]),
    retrieve=extend_schema(summary="Detalle de instrumento con capítulos", tags=["Formulario"]),
)
class InstrumentoViewSet(ReadOnlyViewSet):
    queryset = Instrumento.objects.prefetch_related("capitulos").filter(activo=True)
    serializer_class = InstrumentoSerializer
    search_fields = ["codigo", "nombre", "version"]
    filterset_fields = ["codigo", "activo"]


@extend_schema_view(
    list=extend_schema(summary="Listar capítulos de un instrumento", tags=["Formulario"]),
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
    summary="Instrumento completo para descarga offline",
    description=(
        "Devuelve el instrumento vigente con todos sus capítulos, preguntas, "
        "opciones de respuesta y reglas de skip logic en una sola llamada. "
        "Diseñado para descarga y almacenamiento en SQLite local (modo offline-first)."
    ),
    tags=["Formulario"],
    responses={200: InstrumentoCompletoSerializer},
)
class InstrumentoCompletoView(APIView):
    """
    GET /api/formulario/instrumento/{codigo}/

    Retorna el instrumento vigente con el código dado.
    Si hay varias versiones, devuelve la más reciente con vigente=True.
    404 si el instrumento no existe o no tiene versión vigente.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, codigo: str):
        instrumento = (
            Instrumento.objects
            .filter(codigo=codigo.upper(), activo=True)
            .prefetch_related(
                "capitulos__preguntas__opciones",
                "capitulos__preguntas__reglas_entrantes__pregunta_origen",
                "capitulos__preguntas__reglas_entrantes__capitulo_afectado",
                "reglas__pregunta_origen",
                "reglas__pregunta_afectada",
                "reglas__capitulo_afectado",
            )
            .order_by("-vigente_desde")
            .first()
        )

        if instrumento is None or not instrumento.vigente:
            from rest_framework.exceptions import NotFound
            raise NotFound(f"No hay instrumento vigente con código '{codigo}'.")

        serializer = InstrumentoCompletoSerializer(instrumento)
        return Response(serializer.data)


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

    La decisión de qué se ve y qué es obligatorio NO vive acá: vive en
    `skiplogic.calcular_visibles`, que es la misma que usa
    `SesionEncuesta.recalcular_porcentaje` y el espejo de `skipLogic.ts` del
    móvil. Tener el criterio en un solo lugar es lo que evita que el panel web y
    la APK informen distinto sobre la misma sesión.
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
        ).order_by("orden")

        reglas = list(ReglaSkipLogic.objects.filter(
            instrumento__capitulos__id=capitulo_id
        ).select_related("pregunta_origen", "pregunta_afectada", "capitulo_afectado"))

        visibles, obligatorias, finalizar = calcular_visibles(
            preguntas, reglas, respuestas, contexto,
        )

        return Response({
            "preguntas_visibles": sorted(visibles),
            "preguntas_obligatorias": sorted(obligatorias),
            "finalizar_capitulo": finalizar,
            "total": len(visibles),
        })

