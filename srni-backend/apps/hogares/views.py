"""
Views de Hogares SRNI.
Requieren permiso puede_caracterizar para todas las operaciones.
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.autenticacion.permissions import PuedeCaracterizar
from apps.auditoria.models import LogAcceso
from .models import Hogar, MiembroHogar
from .serializers import (
    HogarListSerializer, HogarDetalleSerializer,
    AgregarMiembroSerializer, MiembroHogarSerializer,
)


def _ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


@extend_schema_view(
    list=extend_schema(summary='Listar hogares del encuestador', tags=['Hogares']),
    retrieve=extend_schema(summary='Detalle de hogar con miembros', tags=['Hogares']),
    create=extend_schema(summary='Crear nuevo hogar', tags=['Hogares']),
    update=extend_schema(summary='Actualizar hogar', tags=['Hogares']),
    partial_update=extend_schema(summary='Actualizar hogar (parcial)', tags=['Hogares']),
)
class HogarViewSet(viewsets.ModelViewSet):
    """
    CRUD de hogares.
    El listado muestra solo los hogares creados por el encuestador autenticado
    (o todos, si tiene perfil administrador).
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'municipio', 'tipo_vivienda']
    ordering_fields = ['created_at', 'updated_at', 'estado']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Hogar.objects.select_related(
            'jefe_hogar', 'municipio__departamento', 'creado_por'
        ).prefetch_related('miembros')

        if not (user.puede('administrar')):
            qs = qs.filter(creado_por=user)
        return qs

    def get_serializer_class(self):
        if self.action in ('list',):
            return HogarListSerializer
        return HogarDetalleSerializer

    def perform_create(self, serializer):
        hogar = serializer.save(creado_por=self.request.user)
        LogAcceso.registrar(
            usuario=self.request.user,
            accion='CREAR_HOGAR',
            recurso='Hogar',
            recurso_id=str(hogar.id),
            ip=_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
        )

    @extend_schema(
        summary='Agregar miembro al hogar',
        tags=['Hogares'],
        request=AgregarMiembroSerializer,
        responses={201: MiembroHogarSerializer},
    )
    @action(detail=True, methods=['post'], url_path='agregar-miembro')
    def agregar_miembro(self, request, pk=None):
        hogar = self.get_object()
        serializer = AgregarMiembroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        miembro = serializer.save(hogar=hogar, creado_por=request.user)

        LogAcceso.registrar(
            usuario=request.user,
            accion='AGREGAR_MIEMBRO',
            recurso='MiembroHogar',
            recurso_id=str(miembro.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'hogar_id': str(hogar.id)},
        )
        return Response(
            MiembroHogarSerializer(miembro).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary='Listar miembros del hogar',
        tags=['Hogares'],
        responses={200: MiembroHogarSerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='miembros')
    def listar_miembros(self, request, pk=None):
        hogar = self.get_object()
        miembros = hogar.miembros.select_related('victima', 'tipo_documento').all()
        return Response(MiembroHogarSerializer(miembros, many=True).data)
