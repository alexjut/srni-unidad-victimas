"""Configuración de producción — seguridad máxima."""
from .base import *

DEBUG = False

# HTTPS y seguridad
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

# CORS — solo el dominio del frontend
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True

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
