"""
Views del motor de formularios dinámico SRNI — alineadas con Diccionario V8.

Endpoints de solo lectura para estructura del instrumento +
endpoint POST de evaluación de skip logic (reglas HABILITAR/DESHABILITAR/OBLIGAR/FINALIZAR).
"""
import ast
import json
import operator as _op

from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.autenticacion.permissions import PuedeCaracterizar
from .models import Instrumento, Capitulo, Pregunta, ReglaSkipLogic, AccionSkipChoices
from django.shortcuts import get_object_or_404
from .serializers import (
    InstrumentoSerializer,
    CapituloListSerializer, CapituloDetalleSerializer,
    PreguntaSerializer, InstrumentoCompletoSerializer, EvaluarSkipLogicSerializer,
)

# ─── Evaluador AST seguro para expresiones de skip logic ─────────────────────
# Reemplaza eval() — solo permite comparaciones, operadores booleanos y literales.
# Las expresiones provienen de la BD (no de usuarios), pero usar eval() con datos
# externos es mala práctica incluso si la fuente es "confiable".

_CMP_OPS = {
    ast.Eq:    _op.eq,
    ast.NotEq: _op.ne,
    ast.Lt:    _op.lt,
    ast.LtE:   _op.le,
    ast.Gt:    _op.gt,
    ast.GtE:   _op.ge,
    ast.In:    lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

_BOOL_OPS = {
    ast.And: all,
    ast.Or:  any,
}


def _safe_eval(node: ast.AST, ctx: dict):
    """Evalúa un nodo AST restringido a comparaciones y literales."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return ctx.get(node.id, '')
    if isinstance(node, ast.List):
        return [_safe_eval(el, ctx) for el in node.elts]
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, ctx)
        for cmp_op, comparator in zip(node.ops, node.comparators):
            fn = _CMP_OPS.get(type(cmp_op))
            if fn is None:
                raise ValueError(f'Operador no permitido: {cmp_op}')
            if not fn(left, _safe_eval(comparator, ctx)):
                return False
            left = _safe_eval(comparator, ctx)
        return True
    if isinstance(node, ast.BoolOp):
        fn = _BOOL_OPS.get(type(node.op))
        if fn is None:
            raise ValueError(f'Operador booleano no permitido: {node.op}')
        values = [_safe_eval(v, ctx) for v in node.values]
        return fn(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, ctx)
    raise ValueError(f'Nodo AST no permitido: {type(node).__name__}')


def evaluar_expresion_segura(expresion: str, contexto: dict, respuestas: dict = None) -> bool:
    """Evalúa una expresión de skip logic de forma segura usando AST.

    El ámbito combina las respuestas ya capturadas (indexadas por codigo_externo)
    como base y el contexto de la víctima (edad/sexo/etnia/ruv_incluido) con
    precedencia. Así una expresión puede referenciar la respuesta de OTRA pregunta
    por su código, habilitando condiciones AND mixtas
    (ej. "etnia == 'indigena' and D6 == '2'"). Espejo de _evaluarExpresion (móvil).
    Convención: los valores del lado derecho van entre comillas ('2', 'true').
    """
    try:
        tree = ast.parse(expresion, mode='eval')
        ambito = dict(respuestas or {})
        ambito.update(contexto or {})
        return bool(_safe_eval(tree, ambito))
    except Exception:
        return False


class ReadOnlyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, PuedeCaracterizar]
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
def _valores_seleccionados(valor: str) -> list:
    """Descompone la respuesta en los valores seleccionados.

    Array JSON de un multi-select ('["1","3"]') → sus elementos como strings;
    cualquier otra cosa (selección única, texto, booleano) → un único valor escalar.
    Vacío → []. Espejo de _valoresSeleccionados() del móvil (skipLogic.ts).
    """
    s = (valor or "").strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except (ValueError, TypeError):
            pass
        return [s]
    return [s]


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

            tiene_habilitar = any(
                r.accion == AccionSkipChoices.HABILITAR for r in reglas_entrantes
            )
            visible = not tiene_habilitar

            for regla in reglas_entrantes:
                if self._regla_activa(regla, respuestas, contexto):
                    if regla.accion == AccionSkipChoices.HABILITAR:
                        visible = True
                    elif regla.accion == AccionSkipChoices.DESHABILITAR:
                        visible = False
                    elif regla.accion == AccionSkipChoices.OBLIGAR:
                        visible = True
                        obligatorias.add(pregunta.codigo_externo)
                    elif regla.accion == AccionSkipChoices.FINALIZAR:
                        finalizar = True

            if visible:
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
            # Soporta origen de selección ÚNICA (escalar) y MÚLTIPLE (LISTA_MULTIPLE,
            # que guarda un array JSON: '["1","3"]'). Dispara si CUALQUIER valor del
            # trigger está entre los seleccionados. Compatible hacia atrás: para un
            # escalar, seleccionados == [valor_actual].
            seleccionados = _valores_seleccionados(valor_actual)
            triggers = [v.strip() for v in regla.valor_trigger.split(",")]
            return any(t in seleccionados for t in triggers)

        if regla.expresion_origen:
            return evaluar_expresion_segura(regla.expresion_origen, contexto, respuestas)

        return False
