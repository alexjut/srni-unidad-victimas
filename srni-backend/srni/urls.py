from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from drf_spectacular.utils import extend_schema
from .debug_views import log_error_mobile


def health_check(request):
    return JsonResponse({'status': 'ok', 'proyecto': 'SRNI — Unidad para las Víctimas'})


@extend_schema(exclude=True)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    """
    Raíz de la API SRNI — lista todos los endpoints disponibles.
    Accede a /api/docs/ para la documentación interactiva Swagger.
    """
    return Response({
        'descripcion': 'API REST — Sistema de Caracterización de Víctimas (SRNI)',
        'version': '1.0.0',
        'documentacion': {
            'swagger': request.build_absolute_uri('/api/docs/'),
            'redoc': request.build_absolute_uri('/api/redoc/'),
            'schema_json': request.build_absolute_uri('/api/schema/'),
        },
        'endpoints': {
            'autenticacion': {
                'login': reverse('auth-login', request=request, format=format),
                'refresh': reverse('auth-refresh', request=request, format=format),
                'logout': reverse('auth-logout', request=request, format=format),
                'me': reverse('auth-me', request=request, format=format),
                'cambiar_password': reverse('auth-cambiar-password', request=request, format=format),
            },
            'parametricas': request.build_absolute_uri('/api/parametricas/'),
            'formulario': request.build_absolute_uri('/api/formulario/'),
            'victimas': {
                'buscar': request.build_absolute_uri('/api/victimas/buscar/'),
                'detalle': request.build_absolute_uri('/api/victimas/{id}/'),
            },
            'hogares': request.build_absolute_uri('/api/hogares/'),
            'encuestas': request.build_absolute_uri('/api/encuestas/'),
            'habilitaciones': request.build_absolute_uri('/api/habilitaciones/'),
            'ia': request.build_absolute_uri('/api/ia/'),
            'reportes': {
                'produccion':        request.build_absolute_uri('/api/reportes/produccion/'),
                'produccion_detalle': request.build_absolute_uri('/api/reportes/produccion/detalle/'),
                'produccion_export':  request.build_absolute_uri('/api/reportes/produccion/export/'),
            },
            'auditoria': {
                'logs': request.build_absolute_uri('/api/auditoria/logs/'),
            },
            'sincronizacion_oracle': {
                'registros': request.build_absolute_uri('/api/sincronizacion/registros/'),
                'estado_por_hogar': request.build_absolute_uri('/api/sincronizacion/registros/estado/'),
            },
        },
        'health': request.build_absolute_uri('/health/'),
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),

    # Raíz browsable de la API
    path('api/', api_root, name='api-root'),

    # Autenticación JWT
    path('api/auth/', include('apps.autenticacion.urls')),

    # Módulos Sprint 2
    path('api/victimas/', include('apps.victimas.urls')),
    path('api/formulario/', include('apps.formulario.urls')),
    path('api/parametricas/', include('apps.parametricas.urls')),

    # Módulos Sprint 3
    path('api/hogares/', include('apps.hogares.urls')),
    path('api/encuestas/', include('apps.encuestas.urls')),

    # Excepciones de vigencia — las autoriza el front web, no la app de campo
    # (decidido el 14-ago-2026: el caracterizador no debe tener el soporte).
    path('api/habilitaciones/', include('apps.encuestas.urls_habilitaciones')),

    # Módulo Sprint 5 — IA Gemini
    path('api/ia/', include('apps.ia.urls')),

    # Módulo Sprint 10 — Reportes de producción
    path('api/reportes/', include('apps.reportes.urls')),

    # Auditoría — endpoint de logs para el panel web (Brando, Sprint integración jun-2026)
    path('api/auditoria/', include('apps.auditoria.urls')),

    # Sincronización SICAV → Oracle legacy: consulta del ledger de escritura.
    # Solo lectura; la escritura se dispara al cerrar la encuesta o por comando.
    path('api/sincronizacion/', include('apps.sincronizacion.urls')),

    # Distribución móvil — versión y descarga auditada de la APK
    path('api/movil/', include('apps.movil.urls')),

    # Administración de usuarios (panel web — solo administradores)
    path('api/usuarios/', include('apps.autenticacion.urls_admin')),

    # Documentación OpenAPI / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Sprint 17 — Endpoint de debug: recibe errores móvil y los printea en consola.
# Es AllowAny por diseño (el móvil reporta antes de autenticar), así que SOLO
# se registra en desarrollo: en producción no debe existir esta superficie.
if settings.DEBUG:
    urlpatterns += [
        path('api/_debug/log/', log_error_mobile, name='debug-log-mobile'),
    ]
