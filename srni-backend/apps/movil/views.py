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
from apps.auditoria.red import ip_de_request


def _client_ip(request) -> str:
    """
    IP real del cliente detrás de nginx/ngrok/WAF.

    Este módulo fue el primero en toparse con el `IP:puerto` del WAF y tenía su
    propia solución; ahora vive en `apps/auditoria/red.py`, que es de donde la
    toman los otros cinco módulos que arrastraban el mismo defecto.
    """
    return ip_de_request(request)


RUTA_DESCARGA = "/api/movil/descargar/"


def url_descarga(request) -> str:
    """
    Dirección pública de la APK, la que se le entrega al celular.

    `build_absolute_uri` sola devolvía `http://…` cuando se entraba por el
    dominio: FortiWeb termina el TLS y reenvía en claro al :80, así que Django ve
    una petición HTTP aunque el usuario haya entrado por HTTPS. Es el mismo
    engaño del proxy que ya nos costó las IPs con puerto (ver auditoria/red.py).

    Por eso el orden es: primero `MOVIL_URL_BASE` —explícita y verificable, la
    declara el compose—, y solo si está vacía se reconstruye desde la petición,
    corrigiendo el esquema cuando el proxy anuncia `X-Forwarded-Proto: https`.
    """
    base = (getattr(settings, "MOVIL_URL_BASE", "") or "").strip()
    if base:
        return base.rstrip("/") + RUTA_DESCARGA

    url = request.build_absolute_uri(RUTA_DESCARGA)
    proto = request.META.get("HTTP_X_FORWARDED_PROTO", "").split(",")[0].strip().lower()
    if proto == "https" and url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


@api_view(["GET"])
@permission_classes([AllowAny])
def version(request):
    """Última versión publicada de la APK."""
    return Response({
        "version": getattr(settings, "MOVIL_VERSION", "1.0.0"),
        "version_code": getattr(settings, "MOVIL_VERSION_CODE", 1),
        "url_descarga": url_descarga(request),
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
