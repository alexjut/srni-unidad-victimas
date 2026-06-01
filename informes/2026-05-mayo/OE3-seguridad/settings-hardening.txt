"""Configuración de producción — seguridad máxima."""
from .base import *   # noqa: F401, F403

DEBUG = False

# ─── Base de datos (requerida en producción) ──────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     config('DB_NAME'),
        'USER':     config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST':     config('DB_HOST', default='localhost'),
        'PORT':     config('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': config('DB_SSL_MODE', default='require'),
        },
        'CONN_MAX_AGE': 60,
    }
}

# ─── HTTPS y headers de seguridad ────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000       # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# ─── Content-Security-Policy (mitigación XSS) ────────────────────────────────
# Añadir header CSP via middleware de Nginx o directamente aquí.
# El SecurityMiddleware de Django 4.x+ no gestiona CSP nativo;
# se recomienda configurarlo en Nginx. Documentado aquí para trazabilidad.
#
# Nginx recomendado (infra/nginx/srni.conf):
#   add_header Content-Security-Policy
#     "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline';
#      script-src 'self'; connect-src 'self' https://generativelanguage.googleapis.com"
#     always;

# ─── CORS — solo el dominio del frontend ─────────────────────────────────────
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/srni/django.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
        },
    },
    'loggers': {
        'django': {'handlers': ['file'], 'level': 'WARNING'},
        'srni.auditoria': {'handlers': ['file'], 'level': 'INFO'},
    },
}
