from django.urls import path
from .views import ConsentimientoIAView, EstadoIAView, MapearAudioView, ProcesarEntrevistaView

urlpatterns = [
    path('consentimiento/', ConsentimientoIAView.as_view(), name='ia-consentimiento'),
    path('estado/', EstadoIAView.as_view(), name='ia-estado'),
    path('mapear-audio/', MapearAudioView.as_view(), name='ia-mapear-audio'),
    path('procesar-entrevista/', ProcesarEntrevistaView.as_view(), name='ia-procesar-entrevista'),
]
