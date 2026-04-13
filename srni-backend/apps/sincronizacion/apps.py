from django.apps import AppConfig

APP_NAMES = {
    'victimas': 'Registro Nacional de Información (Víctimas)',
    'formulario': 'Motor de Formularios Dinámico',
    'hogares': 'Hogares y Miembros',
    'encuestas': 'Sesiones de Encuesta',
    'parametricas': 'Paramétricas Geográficas y Étnicas',
    'sincronizacion': 'Sincronización de Datos',
    'reportes': 'Reportes de Producción',
}

class SincronizacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sincronizacion'
    verbose_name = APP_NAMES.get('sincronizacion', 'sincronizacion')
