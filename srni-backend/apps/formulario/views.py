"""
Views del motor de formularios dinámico SRNI.

Endpoints de solo lectura para estructura del instrumento +
endpoint de evaluación de skip logic (PREDEPENDE / RESHABILITA / RESFINALIZA).
"""
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Instrumento, Tema, Pregunta, PreguntaDerivada
from .serializers import (
    InstrumentoSerializer, TemaListSerializer, TemaDetalleSerializer,
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
    list=extend_schema(summary='Listar instrumentos vigentes', tags=['Formulario']),
    retrieve=extend_schema(summary='Detalle de instrumento con sus temas', tags=['Formulario']),
)
class InstrumentoViewSet(ReadOnlyViewSet):
    queryset = Instrumento.objects.prefetch_related('temas').all()
    serializer_class = InstrumentoSerializer
    filterset_fields = ['vigente']
    search_fields = ['nombre', 'codigo']


@extend_schema_view(
    list=extend_schema(summary='Listar temas de un instrumento', tags=['Formulario']),
    retrieve=extend_schema(summary='Detalle de tema con todas sus preguntas', tags=['Formulario']),
)
class TemaViewSet(ReadOnlyViewSet):
    serializer_class = TemaListSerializer
    filterset_fields = ['instrumento', 'activo']
    search_fields = ['nombre', 'codigo']

    def get_queryset(self):
        return Tema.objects.prefetch_related(
            'preguntas__opciones',
            'preguntas__derivaciones_como_hija',
        ).all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TemaDetalleSerializer
        return TemaListSerializer


@extend_schema_view(
    list=extend_schema(summary='Listar preguntas de un tema', tags=['Formulario']),
    retrieve=extend_schema(summary='Detalle de pregunta con opciones y skip logic', tags=['Formulario']),
)
class PreguntaViewSet(ReadOnlyViewSet):
    serializer_class = PreguntaSerializer
    filterset_fields = ['tema', 'tipo_respuesta', 'requerida', 'activa']
    search_fields = ['codigo', 'texto']

    def get_queryset(self):
        return Pregunta.objects.prefetch_related(
            'opciones',
            'derivaciones_como_hija__pregunta_padre',
        ).select_related('tema').all()


@extend_schema(
    summary='Evaluar skip logic del formulario',
    description=(
        'Recibe el ID de un tema y las respuestas actuales del encuestador. '
        'Devuelve la lista de IDs de preguntas visibles aplicando las reglas '
        'PREDEPENDE / RESHABILITA del instrumento original.'
    ),
    tags=['Formulario'],
    request=EvaluarSkipLogicSerializer,
    responses={200: {'type': 'object', 'properties': {
        'preguntas_visibles': {'type': 'array', 'items': {'type': 'integer'}},
        'total': {'type': 'integer'},
    }}},
)
class EvaluarSkipLogicView(APIView):
    """
    Motor de evaluación de lógica condicional.

    Reglas de visibilidad:
    - Una pregunta SIN condiciones de habilitación es siempre visible.
    - Una pregunta CON condiciones es visible si AL MENOS UNA condición
      se cumple con las respuestas actuales.

    Operadores soportados:
      EQ       → valor == valor_condicion
      NEQ      → valor != valor_condicion
      GT       → float(valor) > float(valor_condicion)
      GTE      → float(valor) >= float(valor_condicion)
      LT       → float(valor) < float(valor_condicion)
      LTE      → float(valor) <= float(valor_condicion)
      IN       → valor in valor_condicion.split(',')
      NOTNULL  → valor no es vacío
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EvaluarSkipLogicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tema_id = serializer.validated_data['tema_id']
        respuestas_raw = serializer.validated_data['respuestas']

        # Construir mapa {pregunta_id: valor}
        respuestas = {r['pregunta_id']: r['valor'] for r in respuestas_raw}

        # Obtener preguntas activas del tema con sus condiciones
        preguntas = Pregunta.objects.filter(
            tema_id=tema_id, activa=True
        ).prefetch_related('derivaciones_como_hija').order_by('orden')

        visibles = []
        for pregunta in preguntas:
            condiciones = list(pregunta.derivaciones_como_hija.all())
            if not condiciones:
                # Sin condiciones → siempre visible
                visibles.append(pregunta.id)
            else:
                # Visible si al menos una condición se cumple
                if any(
                    self._evaluar(condicion, respuestas)
                    for condicion in condiciones
                ):
                    visibles.append(pregunta.id)

        return Response({
            'preguntas_visibles': visibles,
            'total': len(visibles),
        })

    @staticmethod
    def _evaluar(condicion: PreguntaDerivada, respuestas: dict) -> bool:
        """Evalúa si una condición de derivación se cumple con las respuestas actuales."""
        padre_id = condicion.pregunta_padre_id
        valor_actual = respuestas.get(padre_id, '')
        operador = condicion.operador
        valor_cond = condicion.valor_condicion

        if operador == 'NOTNULL':
            return bool(valor_actual)
        if operador == 'EQ':
            return str(valor_actual) == str(valor_cond)
        if operador == 'NEQ':
            return str(valor_actual) != str(valor_cond)
        if operador == 'IN':
            opciones = [v.strip() for v in valor_cond.split(',')]
            return str(valor_actual) in opciones

        # Operadores numéricos
        try:
            v_num = float(valor_actual)
            c_num = float(valor_cond)
            if operador == 'GT':
                return v_num > c_num
            if operador == 'GTE':
                return v_num >= c_num
            if operador == 'LT':
                return v_num < c_num
            if operador == 'LTE':
                return v_num <= c_num
        except (ValueError, TypeError):
            return False

        return False
