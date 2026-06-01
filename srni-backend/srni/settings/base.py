"""
Configuración BASE — SRNI Backend
Solo contiene ajustes comunes a todos los entornos.
DATABASES, CACHES y almacenamiento se definen en cada entorno (development / production).
NUNCA poner credenciales aquí.
"""
from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.autenticacion',
    'apps.victimas',
    'apps.formulario',
    'apps.hogares',
    'apps.encuestas',
    'apps.parametricas',
    'apps.sincronizacion',
    'apps.auditoria',
    'apps.reportes',
    'apps.ia',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'srni.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'srni.wsgi.application'

AUTH_USER_MODEL = 'autenticacion.Usuario'

# --- JWT ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=8),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# --- DRF ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/hour',
        'user': '1000/hour',
        'login':        '5/minute',    # 5 intentos de login por minuto por IP
        'busqueda_rni': '30/hour',     # 30 búsquedas RNI por hora por usuario
        'ia_consulta':  '20/hour',     # 20 consultas IA por hora
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --- Swagger / OpenAPI (drf-spectacular) ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'SRNI API — Sistema de Caracterización de Víctimas',
    'DESCRIPTION': (
        'API REST del Sistema de Registro Nacional de Información (SRNI) '
        'de la Unidad para las Víctimas de Colombia.\n\n'
        '**Autenticación:** JWT Bearer token. Obtener en `POST /api/auth/login/`.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    # Seguridad en el schema
    'SECURITY': [{'jwtAuth': []}],
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
    },
}

# --- Contraseñas ---
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Localización ---
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- IA — Gemini ---
# La clave API NUNCA se envía a la app móvil. Solo el backend llama a Gemini.
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Datos de prueba del contratista (excepción a reglas de idempotencia) ---
# Documento de la víctima de pruebas (Javier Aguilar — contratista 2226-2026).
# Esta víctima específica puede tener N caracterizaciones bajo su único hogar,
# para que el contratista valide los 8 instrumentos UARIV sin restricciones.
# Para cualquier otra víctima real, aplica la regla 1 hogar → 1 caracterización.
# Configurable por entorno (.env) en producción.
VICTIMA_PRUEBAS_DOC = config('VICTIMA_PRUEBAS_DOC', default='1030547250')

# --- Cifrado de campos PII ---
# Clave AES-256 para EncryptedField personalizado (apps/victimas/fields.py)
# En desarrollo: valor de .env; en producción: Docker Secret
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')
