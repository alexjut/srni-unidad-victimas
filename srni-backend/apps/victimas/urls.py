from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    VictimaViewSet, BuscarVictimaView, ConsultarFuenteView, GrupoFamiliarView,
    RegistrarDesdeFuenteView, PrecargaOfflineView,
    PadronVersionView, PadronDownloadView, PadronBloomView,
)

router = DefaultRouter()
router.register(r'', VictimaViewSet, basename='victima')

# Rutas específicas van ANTES de router.urls para que el DefaultRouter
# no capture sus nombres como <pk>.
urlpatterns = [
    path('buscar/', BuscarVictimaView.as_view(), name='victima-buscar'),
    path('consultar-fuente/', ConsultarFuenteView.as_view(), name='victima-consultar-fuente'),
    path('precarga/', PrecargaOfflineView.as_view(), name='victima-precarga'),
    path('padron/version/', PadronVersionView.as_view(), name='victima-padron-version'),
    path('padron/download/', PadronDownloadView.as_view(), name='victima-padron-download'),
    # Solo el filtro del universo (22,7 MB), sin el resto del padrón: es lo que
    # habilita el alta manual en campo sin bajar cientos de MB.
    path('padron/bloom/', PadronBloomView.as_view(), name='victima-padron-bloom'),
    path('grupo-familiar/<int:cons_persona>/', GrupoFamiliarView.as_view(), name='victima-grupo-familiar'),
    path('registrar-desde-fuente/', RegistrarDesdeFuenteView.as_view(), name='victima-registrar-desde-fuente'),
] + router.urls
