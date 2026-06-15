"""
Distribución y control de la APK móvil.

- GET /api/movil/version/    → última versión disponible (para avisar de actualización)
- GET /api/movil/descargar/  → registra la descarga en auditoría y entrega la APK

Ambos endpoints son públicos (el encuestador descarga antes de autenticarse).
"""
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.auditoria.models import LogAcceso


def _client_ip(request) -> str:
    """IP real del cliente (detrás de nginx/ngrok respeta X-Forwarded-For)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "0.0.0.0"


@api_view(["GET"])
@permission_classes([AllowAny])
def version(request):
    """Última versión publicada de la APK."""
    return Response({
        "version": getattr(settings, "MOVIL_VERSION", "1.0.0"),
        "version_code": getattr(settings, "MOVIL_VERSION_CODE", 1),
        "url_descarga": request.build_absolute_uri("/api/movil/descargar/"),
        "actualizacion_obligatoria": getattr(settings, "MOVIL_ACTUALIZACION_OBLIGATORIA", False),
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def descargar(request):
    """Registra la descarga en auditoría y redirige al archivo servido por Nginx."""
    LogAcceso.registrar(
        accion="DESCARGA_APK",
        ip=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        recurso="APK",
        detalle={"version": getattr(settings, "MOVIL_VERSION", "1.0.0")},
    )
    # Nginx sirve el archivo grande de forma eficiente (no lo streamea Django).
    return HttpResponseRedirect("/movil/app.apk")
