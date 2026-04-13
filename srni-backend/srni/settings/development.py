"""
Configuración de DESARROLLO
- SQLite (sin PostgreSQL ni Docker necesario)
- Sin Redis ni Celery
- CORS abierto
- DEBUG activo
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# --- SQLite para desarrollo ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Caché en memoria (sin Redis) ---
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'srni-dev-cache',
    }
}

# --- Celery síncrono (sin broker) ---
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# --- Archivos locales (sin MinIO) ---
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- CORS abierto en desarrollo ---
CORS_ALLOW_ALL_ORIGINS = True

# --- Email en consola ---
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# --- Logging detallado ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'django.db.backends': {'handlers': ['console'], 'level': 'WARNING'},
        'apps': {'handlers': ['console'], 'level': 'DEBUG'},
    },
}

# JWT más laxo en desarrollo (tokens más largos para no interrumpir pruebas)
from datetime import timedelta
SIMPLE_JWT = {
    **SIMPLE_JWT,
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
