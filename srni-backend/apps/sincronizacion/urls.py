"""Rutas del ledger de sincronización a Oracle y del trabajo hecho en el legacy."""
from rest_framework.routers import DefaultRouter

from .views import MisCaracterizacionesLegacyViewSet, RegistroEscrituraViewSet

router = DefaultRouter()
router.register(r"registros", RegistroEscrituraViewSet,
                basename="sincronizacion-registro")
# "Lo que hice en el sistema anterior". Va acá y no en `hogares` a propósito:
# no son hogares de SICAV, son el recibo de un trabajo que vive en otra base.
router.register(r"mis-caracterizaciones", MisCaracterizacionesLegacyViewSet,
                basename="mis-caracterizaciones-legacy")

urlpatterns = router.urls
