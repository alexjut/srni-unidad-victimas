"""Rutas de la jerarquía de equipos."""
from rest_framework.routers import DefaultRouter

from .views_equipos import EquipoViewSet

router = DefaultRouter()
router.register(r'', EquipoViewSet, basename='equipo')

urlpatterns = router.urls
