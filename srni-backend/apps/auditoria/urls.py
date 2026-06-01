"""URLs de auditoría — endpoint solo lectura para el panel web."""
from django.urls import path
from .views import LogAccesoListView

app_name = 'auditoria'

urlpatterns = [
    path('logs/', LogAccesoListView.as_view(), name='logs-list'),
]
