from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import VictimaViewSet, BuscarVictimaView, ConsultarFuenteView, GrupoFamiliarView, RegistrarDesdeFuenteView

router = DefaultRouter()
router.register(r'', VictimaViewSet, basename='victima')

# Rutas específicas van ANTES de router.urls para que el DefaultRouter
# no capture sus nombres como <pk>.
urlpatterns = [
    path('buscar/', BuscarVictimaView.as_view(), name='victima-buscar'),
    path('consultar-fuente/', ConsultarFuenteView.as_view(), name='victima-consultar-fuente'),
    path('grupo-familiar/<int:cons_persona>/', GrupoFamiliarView.as_view(), name='victima-grupo-familiar'),
    path('registrar-desde-fuente/', RegistrarDesdeFuenteView.as_view(), name='victima-registrar-desde-fuente'),
] + router.urls
