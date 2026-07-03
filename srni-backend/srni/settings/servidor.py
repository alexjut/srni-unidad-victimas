"""
Configuración para despliegue en el SERVIDOR UARIV por IP/HTTP (fase de pruebas).

Hereda de `production` (BD PostgreSQL, CORS, cabeceras de seguridad), pero RELAJA
las exigencias de TLS porque el acceso temporal es por IP sin HTTPS, mientras la
Oficina de Seguridad habilita el dominio + certificado tras el Nginx Proxy Manager.

Cuando la app se publique con dominio y TLS (vía NPM), volver a usar
`srni.settings.production`.
"""
from .production import *  # noqa: F401, F403

# ─── Acceso temporal por IP / HTTP ────────────────────────────────────────────
# Sin redirección forzada a HTTPS ni cookies "Secure" (no hay TLS en esta fase).
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# ─── Logging a stdout (contenedor) en vez de /var/log/srni ────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{levelname}] {asctime} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'srni.auditoria': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
