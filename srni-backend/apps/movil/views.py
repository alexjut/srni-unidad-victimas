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


def _strip_port(addr: str) -> str:
    """Quita el puerto si viene pegado a la IP.

    El WAF (FortiWeb) reenvía al cliente como ``IP:puerto`` (p.ej.
    ``190.25.98.28:59530``), lo que rompía el campo IP de auditoría. Soporta
    IPv4 (``a.b.c.d:puerto``) e IPv6 (``[::1]:puerto``); deja intacta una IPv6
    sin puerto (que tiene varios ``:``).
    """
    addr = (addr or "").strip()
    if not addr:
        return "0.0.0.0"
    if addr.startswith("["):            # [IPv6]:puerto
        return addr[1:].split("]", 1)[0]
    if addr.count(":") == 1:            # IPv4:puerto
        return addr.split(":", 1)[0]
    return addr                          # IPv4 pura o IPv6 sin puerto


def _client_ip(request) -> str:
    """IP real del cliente (detrás de nginx/ngrok/WAF respeta X-Forwarded-For)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    raw = xff.split(",")[0] if xff else request.META.get("REMOTE_ADDR", "")
    return _strip_port(raw) or "0.0.0.0"


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
