from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import VictimaViewSet, BuscarVictimaView

router = DefaultRouter()
router.register(r'', VictimaViewSet, basename='victima')

# IMPORTANTE: 'buscar/' debe ir ANTES de router.urls para que el router
# no capture 'buscar' como <pk> (DefaultRouter con prefijo vacío lo haría).
urlpatterns = [
    path('buscar/', BuscarVictimaView.as_view(), name='victima-buscar'),
] + router.urls
