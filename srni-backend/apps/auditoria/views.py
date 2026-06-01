"""
Views de auditoría — solo lectura para el panel web.

Acceso restringido: usuarios con permiso `administrar` o `ver_reportes`.
"""
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
import django_filters as df
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import LogAcceso
from .serializers import LogAccesoSerializer


class _PuedeVerAuditoria(permissions.BasePermission):
    """Permite acceso a administradores o supervisores con permiso de reportes."""
    message = 'Se requiere perfil administrador o supervisor para ver auditoría.'

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return u.puede('administrar') or u.puede('ver_reportes')


class LogAccesoFilterSet(df.FilterSet):
    accion = df.CharFilter(field_name='accion', lookup_expr='iexact')
    resultado = df.CharFilter(field_name='resultado', lookup_expr='iexact')
    codigo_usuario = df.CharFilter(field_name='codigo_usuario', lookup_expr='iexact')
    fecha_desde = df.DateFilter(field_name='timestamp', lookup_expr='date__gte')
    fecha_hasta = df.DateFilter(field_name='timestamp', lookup_expr='date__lte')

    class Meta:
        model = LogAcceso
        fields = ['accion', 'resultado', 'codigo_usuario', 'fecha_desde', 'fecha_hasta']


@extend_schema(
    summary='Listar logs de auditoría',
    description=(
        'Devuelve los registros de auditoría paginados, ordenados por timestamp '
        'descendente. Solo accesible para administradores o supervisores.\n\n'
        '**Filtros disponibles:**\n'
        '- `accion`: tipo de acción (LOGIN, BUSQUEDA_RNI, etc.)\n'
        '- `resultado`: EXITO, DENEGADO, ERROR\n'
        '- `codigo_usuario`: filtra por usuario\n'
        '- `fecha_desde` / `fecha_hasta`: rango de fechas (YYYY-MM-DD)\n'
        '- `search`: búsqueda libre en recurso, recurso_id, ip_origen'
    ),
    tags=['Auditoría'],
    parameters=[
        OpenApiParameter('accion', str, description='Acción exacta'),
        OpenApiParameter('resultado', str, description='EXITO | DENEGADO | ERROR'),
        OpenApiParameter('codigo_usuario', str),
        OpenApiParameter('fecha_desde', str, description='YYYY-MM-DD'),
        OpenApiParameter('fecha_hasta', str, description='YYYY-MM-DD'),
    ],
)
class LogAccesoListView(generics.ListAPIView):
    """
    GET /api/auditoria/logs/
    Paginación: PageNumberPagination (page_size por defecto del proyecto).
    """
    queryset = LogAcceso.objects.select_related('usuario').all()
    serializer_class = LogAccesoSerializer
    permission_classes = [permissions.IsAuthenticated, _PuedeVerAuditoria]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LogAccesoFilterSet
    search_fields = ['recurso', 'recurso_id', 'ip_origen', 'codigo_usuario']
    ordering_fields = ['timestamp', 'accion', 'resultado']
    ordering = ['-timestamp']
