from django.urls import path
from . import views

urlpatterns = [
    path('produccion/',         views.produccion_resumen,    name='reportes-produccion'),
    path('produccion/detalle/', views.produccion_detalle,   name='reportes-produccion-detalle'),
    path('produccion/export/',  views.produccion_export_csv, name='reportes-produccion-export'),
    # Sprint 13 — backend habilitador para panel web
    path('supervisor/',         views.supervisor_reporte,   name='reportes-supervisor'),
    path('dashboard/series/',   views.dashboard_series,     name='reportes-dashboard-series'),
]
