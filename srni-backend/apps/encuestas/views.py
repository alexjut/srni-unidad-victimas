"""
Views de Encuestas SRNI.

Flujo de uso:
  1. POST /api/encuestas/          → crea SesionEncuesta (estado=INICIADA)
  2. POST /api/encuestas/{id}/responder/   → guarda/actualiza respuesta individual
  3. GET  /api/encuestas/{id}/             → detalle con todas las respuestas
  4. POST /api/encuestas/{id}/finalizar/   → cierra la sesión (COMPLETADA)
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.autenticacion.permissions import PuedeCaracterizar
from apps.auditoria.models import LogAcceso
from apps.formulario.models import Pregunta
from .models import SesionEncuesta, RespuestaEncuesta
from .serializers import (
    SesionEncuestaListSerializer, SesionEncuestaDetalleSerializer,
    RespuestaEncuestaSerializer,
    ResponderPreguntaSerializer, FinalizarSesionSerializer,
)


def _ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


@extend_schema_view(
    list=extend_schema(summary='Listar sesiones del encuestador', tags=['Encuestas']),
    retrieve=extend_schema(summary='Detalle de sesión con respuestas', tags=['Encuestas']),
    create=extend_schema(summary='Iniciar nueva sesión de encuesta', tags=['Encuestas']),
)
class SesionEncuestaViewSet(viewsets.ModelViewSet):
    """
    Gestión de sesiones de encuesta.
    Solo los encuestadores con puede_caracterizar pueden operar este endpoint.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['estado', 'hogar', 'instrumento']
    ordering_fields = ['created_at', 'updated_at', 'porcentaje_completado']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = SesionEncuesta.objects.select_related(
            'hogar', 'instrumento', 'encuestador'
        ).prefetch_related('respuestas')
        if not user.puede('administrar'):
            qs = qs.filter(encuestador=user)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return SesionEncuestaListSerializer
        return SesionEncuestaDetalleSerializer

    def perform_create(self, serializer):
        sesion = serializer.save(encuestador=self.request.user, estado='INICIADA')
        LogAcceso.registrar(
            usuario=self.request.user,
            accion='RESPONDER_PREGUNTA',
            recurso='SesionEncuesta',
            recurso_id=str(sesion.id),
            ip=_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'accion': 'CREAR_SESION', 'hogar_id': str(sesion.hogar_id)},
        )

    @extend_schema(
        summary='Guardar o actualizar una respuesta',
        description=(
            'Upsert: si la pregunta ya tiene respuesta en esta sesión, la actualiza. '
            'Si no, la crea. Actualiza automáticamente el porcentaje de completado.'
        ),
        tags=['Encuestas'],
        request=ResponderPreguntaSerializer,
        responses={200: RespuestaEncuestaSerializer},
    )
    @action(detail=True, methods=['post'], url_path='responder')
    def responder(self, request, pk=None):
        sesion = self.get_object()

        if sesion.estado == 'COMPLETADA':
            return Response(
                {'detail': 'La sesión ya está completada. No se pueden modificar respuestas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResponderPreguntaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pregunta_id = serializer.validated_data['pregunta_id']
        valor = serializer.validated_data['valor']

        # Verificar que la pregunta pertenece al instrumento de la sesión
        try:
            pregunta = Pregunta.objects.get(
                pk=pregunta_id,
                tema__instrumento=sesion.instrumento,
            )
        except Pregunta.DoesNotExist:
            return Response(
                {'detail': f'La pregunta {pregunta_id} no pertenece al instrumento de esta sesión.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Upsert de la respuesta
        respuesta, created = RespuestaEncuesta.objects.update_or_create(
            sesion=sesion,
            pregunta=pregunta,
            defaults={'valor': valor},
        )

        # Actualizar estado y porcentaje
        nuevo_pct = sesion.recalcular_porcentaje()
        SesionEncuesta.objects.filter(pk=sesion.pk).update(
            porcentaje_completado=nuevo_pct,
            estado='EN_PROGRESO',
        )

        LogAcceso.registrar(
            usuario=request.user,
            accion='RESPONDER_PREGUNTA',
            recurso='RespuestaEncuesta',
            recurso_id=str(respuesta.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={
                'sesion_id': str(sesion.id),
                'pregunta_codigo': pregunta.codigo,
                'creada': created,
            },
        )

        return Response(
            RespuestaEncuestaSerializer(respuesta).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        summary='Finalizar sesión de encuesta',
        description='Marca la sesión como COMPLETADA. Solo se puede hacer una vez.',
        tags=['Encuestas'],
        request=FinalizarSesionSerializer,
        responses={200: SesionEncuestaDetalleSerializer},
    )
    @action(detail=True, methods=['post'], url_path='finalizar')
    def finalizar(self, request, pk=None):
        sesion = self.get_object()

        if sesion.estado == 'COMPLETADA':
            return Response(
                {'detail': 'La sesión ya está completada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FinalizarSesionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        observaciones = serializer.validated_data.get('observaciones', '')

        pct_final = sesion.recalcular_porcentaje()
        sesion.estado = 'COMPLETADA'
        sesion.fecha_fin = timezone.now()
        sesion.porcentaje_completado = pct_final
        if observaciones:
            sesion.observaciones = observaciones
        sesion.save(update_fields=[
            'estado', 'fecha_fin', 'porcentaje_completado', 'observaciones'
        ])

        LogAcceso.registrar(
            usuario=request.user,
            accion='FINALIZAR_ENCUESTA',
            recurso='SesionEncuesta',
            recurso_id=str(sesion.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'porcentaje_completado': pct_final, 'hogar_id': str(sesion.hogar_id)},
        )

        return Response(SesionEncuestaDetalleSerializer(sesion).data)
