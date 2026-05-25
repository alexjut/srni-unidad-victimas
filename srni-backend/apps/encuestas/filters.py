"""
FilterSet para SesionEncuesta — Sprint 13 backend habilitador.

Permite al panel web filtrar el listado de sesiones server-side por:
  ?estado=COMPLETADA
  ?instrumento=<uuid>
  ?ruta_entrevista=GENERAL
  ?encuestador=<uuid>
  ?hogar=<uuid>
  ?fecha_inicio_after=2026-01-01
  ?fecha_inicio_before=2026-06-30
  ?porcentaje_min=80
"""
import django_filters

from .models import SesionEncuesta


class SesionEncuestaFilterSet(django_filters.FilterSet):
    """Filtros del listado de sesiones para panel web y mobile."""

    fecha_inicio_after = django_filters.DateFilter(
        field_name='fecha_inicio', lookup_expr='date__gte',
        help_text='Sesiones iniciadas a partir de esta fecha (inclusive).',
    )
    fecha_inicio_before = django_filters.DateFilter(
        field_name='fecha_inicio', lookup_expr='date__lte',
        help_text='Sesiones iniciadas hasta esta fecha (inclusive).',
    )
    porcentaje_min = django_filters.NumberFilter(
        field_name='porcentaje_completado', lookup_expr='gte',
        help_text='Sesiones con porcentaje de completado >= este valor.',
    )
    porcentaje_max = django_filters.NumberFilter(
        field_name='porcentaje_completado', lookup_expr='lte',
        help_text='Sesiones con porcentaje de completado <= este valor.',
    )

    class Meta:
        model = SesionEncuesta
        fields = ['estado', 'instrumento', 'ruta_entrevista', 'encuestador', 'hogar']
