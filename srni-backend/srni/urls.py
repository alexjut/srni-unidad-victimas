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
            # Próximos sprints:
            # 'reportes': {...},
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

    # Módulos futuros
    # path('api/reportes/', include('apps.reportes.urls')),

    # Documentación OpenAPI / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
