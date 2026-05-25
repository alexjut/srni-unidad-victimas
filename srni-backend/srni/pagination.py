"""
Paginadores personalizados — SRNI.

- DefaultPageNumberPagination: el de DRF, page_size=20 (mismo default global).
- CursorTimePagination: paginación con cursor por created_at descendente.
  Recomendada para listados grandes y volátiles (sesiones de encuesta, respuestas).
  Evita el problema de offset/skip en listas que cambian durante la navegación.
"""
from rest_framework.pagination import CursorPagination, PageNumberPagination


class DefaultPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200


class CursorTimePagination(CursorPagination):
    """
    Paginación cursor estable basada en `created_at` descendente.

    Uso:
        class SesionEncuestaViewSet(viewsets.ModelViewSet):
            pagination_class = CursorTimePagination

    Cliente recibe `next` / `previous` con cursor opaco — no tiene que
    calcular offsets ni preocuparse por filas que llegan mientras pagina.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
    ordering = '-created_at'
    cursor_query_param = 'cursor'
