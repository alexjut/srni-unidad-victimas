"""Rutas del ledger de sincronización a Oracle (solo lectura)."""
from rest_framework.routers import DefaultRouter

from .views import RegistroEscrituraViewSet

router = DefaultRouter()
router.register(r"registros", RegistroEscrituraViewSet, basename="sincronizacion-registro")

urlpatterns = router.urls
