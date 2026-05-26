"""
Views de paramétricas — todos los endpoints son de solo lectura.
Accesibles con autenticación JWT; no requieren permisos especiales.
"""
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import (
    Departamento, Municipio, Vereda,
    TipoDocumento, ComunidadNegra, ResguardoIndigena,
    DireccionTerritorial, PuntoAtencion,
)
from .serializers import (
    DepartamentoSerializer, MunicipioSerializer, VeredaSerializer,
    TipoDocumentoSerializer, ComunidadNegraSerializer, ResguardoIndigenaSerializer,
    DireccionTerritorialSerializer, PuntoAtencionSerializer,
)


class ReadOnlyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet base de solo lectura."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]


@extend_schema_view(
    list=extend_schema(summary='Listar departamentos', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de departamento', tags=['Paramétricas']),
)
class DepartamentoViewSet(ReadOnlyViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer
    # Sprint 19: filtro M2M para cascada DT→Depto.
    # GET /api/parametricas/departamentos/?direcciones_territoriales=<dt_id>
    filterset_fields = ['activo', 'direcciones_territoriales']
    search_fields = ['nombre', 'codigo_dane']
    ordering_fields = ['nombre', 'codigo_dane']
    ordering = ['nombre']


@extend_schema_view(
    list=extend_schema(summary='Listar municipios', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de municipio', tags=['Paramétricas']),
)
class MunicipioViewSet(ReadOnlyViewSet):
    queryset = Municipio.objects.select_related('departamento').all()
    serializer_class = MunicipioSerializer
    filterset_fields = ['departamento', 'activo']
    search_fields = ['nombre', 'codigo_dane']
    ordering_fields = ['nombre', 'codigo_dane', 'departamento__nombre']
    ordering = ['departamento__nombre', 'nombre']


@extend_schema_view(
    list=extend_schema(summary='Listar veredas', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de vereda', tags=['Paramétricas']),
)
class VeredaViewSet(ReadOnlyViewSet):
    queryset = Vereda.objects.select_related('municipio__departamento').all()
    serializer_class = VeredaSerializer
    filterset_fields = ['municipio', 'activo']
    search_fields = ['nombre', 'codigo_dane']
    ordering_fields = ['nombre']
    ordering = ['nombre']


@extend_schema_view(
    list=extend_schema(summary='Listar tipos de documento', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de tipo de documento', tags=['Paramétricas']),
)
class TipoDocumentoViewSet(ReadOnlyViewSet):
    queryset = TipoDocumento.objects.all()
    serializer_class = TipoDocumentoSerializer
    filterset_fields = ['activo', 'aplica_nacionales', 'aplica_extranjeros']
    search_fields = ['codigo', 'nombre']
    ordering = ['nombre']


@extend_schema_view(
    list=extend_schema(summary='Listar comunidades negras', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de comunidad negra', tags=['Paramétricas']),
)
class ComunidadNegraViewSet(ReadOnlyViewSet):
    queryset = ComunidadNegra.objects.select_related('municipio').all()
    serializer_class = ComunidadNegraSerializer
    filterset_fields = ['municipio', 'activo']
    search_fields = ['nombre', 'codigo']
    ordering = ['nombre']


@extend_schema_view(
    list=extend_schema(summary='Listar resguardos indígenas', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de resguardo indígena', tags=['Paramétricas']),
)
class ResguardoIndigenaViewSet(ReadOnlyViewSet):
    queryset = ResguardoIndigena.objects.select_related('municipio').all()
    serializer_class = ResguardoIndigenaSerializer
    filterset_fields = ['municipio', 'activo']
    search_fields = ['nombre', 'pueblo', 'codigo']
    ordering = ['nombre']


@extend_schema_view(
    list=extend_schema(summary='Listar direcciones territoriales', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de dirección territorial', tags=['Paramétricas']),
)
class DireccionTerritorialViewSet(ReadOnlyViewSet):
    queryset = DireccionTerritorial.objects.prefetch_related('departamentos').all()
    serializer_class = DireccionTerritorialSerializer
    filterset_fields = ['activo']
    search_fields = ['nombre', 'codigo']
    ordering = ['nombre']


@extend_schema_view(
    list=extend_schema(summary='Listar puntos de atención', tags=['Paramétricas']),
    retrieve=extend_schema(summary='Detalle de punto de atención', tags=['Paramétricas']),
)
class PuntoAtencionViewSet(ReadOnlyViewSet):
    queryset = PuntoAtencion.objects.select_related(
        'direccion_territorial', 'municipio__departamento'
    ).all()
    serializer_class = PuntoAtencionSerializer
    filterset_fields = ['direccion_territorial', 'municipio', 'activo']
    search_fields = ['nombre', 'codigo']
    ordering = ['nombre']
