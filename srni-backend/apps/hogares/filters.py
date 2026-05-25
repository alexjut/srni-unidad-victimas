"""
FilterSets para Hogares SRNI.

Permite que el panel web (Brando) y la app móvil aplique filtros server-side
sobre el listado de hogares sin pedir endpoints adicionales.

Endpoints expuestos via query string:
  ?estado=ACTIVO
  ?municipio=<uuid>
  ?tipo_vivienda=CASA
  ?creado_por=<uuid>
  ?created_at_after=2026-01-01
  ?created_at_before=2026-06-30
  ?busqueda=<texto en codigo_hogar>

Los filtros se combinan con AND. Si no se envía ningún parámetro,
se retorna el listado completo aplicando el queryset base de la view
(que ya filtra por encuestador autenticado salvo perfil administrador).
"""
import django_filters
from django.db.models import Q

from .models import Hogar


class HogarFilterSet(django_filters.FilterSet):
    """Filtros del listado de hogares para panel web y mobile."""

    created_at_after = django_filters.DateFilter(
        field_name='created_at', lookup_expr='date__gte',
        help_text='Hogares creados a partir de esta fecha (inclusive).',
    )
    created_at_before = django_filters.DateFilter(
        field_name='created_at', lookup_expr='date__lte',
        help_text='Hogares creados hasta esta fecha (inclusive).',
    )
    busqueda = django_filters.CharFilter(
        method='filter_busqueda',
        help_text='Texto libre en código de hogar u observaciones.',
    )

    class Meta:
        model = Hogar
        fields = ['estado', 'municipio', 'tipo_vivienda', 'creado_por']

    def filter_busqueda(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(codigo_hogar__icontains=value) | Q(observaciones__icontains=value)
        )
