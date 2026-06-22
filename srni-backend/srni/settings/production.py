"""Configuración de producción — seguridad máxima."""
import os
from datetime import timedelta

from .base import *   # noqa: F401, F403

DEBUG = False

# ─── Caché Redis (compartida entre workers de gunicorn) ───────────────────────
# Necesaria para que el throttle/rate-limit de DRF y el bloqueo de cuenta cuenten
# de forma CONSISTENTE entre workers. Con caché local (por defecto) cada worker
# lleva su propio contador y la protección anti-fuerza-bruta se diluye.
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://cz_redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            # Resiliencia: si Redis no responde, la caché degrada (get→None,
            # set→no-op) en vez de lanzar excepción. Así un hipo de Redis NO
            # tumba el login (el throttle/bloqueo simplemente no cuentan ese rato).
            'IGNORE_EXCEPTIONS': True,
        },
    }
}
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True

# ─── JWT — refresh largo para captura offline (entrevistas de varias horas) ───
# El access token sigue siendo CORTO (15 min, heredado de base) porque durante la
# captura offline NO se renueva nada contra el servidor: la entrevista se guarda
# localmente en la APK y solo se sincroniza al recuperar conexión. Lo que debe
# sobrevivir es el REFRESH token, que es lo que permite reanudar la sesión y subir
# los datos tras horas sin red. Por eso lo subimos de 8h a 7 días en producción.
# Mantenemos ROTATE_REFRESH_TOKENS=True (heredado): cada uso rota y revoca el anterior.
SIMPLE_JWT = {
    **SIMPLE_JWT,  # noqa: F405  (hereda ACCESS_TOKEN_LIFETIME=15min y demás de base)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

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
