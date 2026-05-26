from django.urls import path
from . import views

urlpatterns = [
    path('produccion/',         views.produccion_resumen,    name='reportes-produccion'),
    path('produccion/detalle/', views.produccion_detalle,   name='reportes-produccion-detalle'),
    path('produccion/export/',  views.produccion_export_csv, name='reportes-produccion-export'),
    # Sprint 13 — backend habilitador para panel web
    path('supervisor/',         views.supervisor_reporte,   name='reportes-supervisor'),
    path('dashboard/series/',   views.dashboard_series,     name='reportes-dashboard-series'),
    # Sprint 20 — aliases /encuestador/ que usa el panel web (srni-frontend).
    # Apuntan a las mismas views — no duplican lógica.
    path('encuestador/',          views.produccion_resumen,    name='reportes-encuestador'),
    path('encuestador/detalle/',  views.produccion_detalle,    name='reportes-encuestador-detalle'),
    path('encuestador/exportar/', views.produccion_export_csv, name='reportes-encuestador-exportar'),
]
