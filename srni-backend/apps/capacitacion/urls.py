from django.urls import path

from .views import (EstadoParticipanteView, PruebaPublicaView, ResponderPruebaView,
                    ResultadosView)

urlpatterns = [
    # Públicas — el participante no tiene credenciales del sistema.
    path('prueba/<slug:codigo>/', PruebaPublicaView.as_view(), name='cap-prueba'),
    path('prueba/<slug:codigo>/estado/', EstadoParticipanteView.as_view(), name='cap-estado'),
    path('prueba/<slug:codigo>/responder/', ResponderPruebaView.as_view(), name='cap-responder'),
    # Interna — tablero del panel.
    path('resultados/', ResultadosView.as_view(), name='cap-resultados'),
]
