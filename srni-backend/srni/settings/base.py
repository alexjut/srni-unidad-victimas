"""
Configuración BASE — SRNI Backend
Solo contiene ajustes comunes a todos los entornos.
DATABASES, CACHES y almacenamiento se definen en cada entorno (development / production).
NUNCA poner credenciales aquí.
"""
import os
from pathlib import Path
from datetime import timedelta
from decouple import config
from django.templatetags.static import static
from django.urls import reverse_lazy

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
    'apps.movil',
]

# 'unfold' (+ contrib) debe ir ANTES de django.contrib.admin (que vive en DJANGO_APPS).
UNFOLD_APPS = ['unfold', 'unfold.contrib.filters']
INSTALLED_APPS = UNFOLD_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ─── Indicador de entorno (banner del panel) ─────────────────────────────────
# CRÍTICO: distinguir visualmente PRODUCCIÓN (servidor con datos reales de
# víctimas) de DESARROLLO. Lee DJANGO_SETTINGS_MODULE en tiempo de ejecución.
def unfold_environment_callback(request):
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
    if 'servidor' in settings_module or 'production' in settings_module:
        return ['PRODUCCIÓN', 'danger']
    return ['DESARROLLO', 'warning']


# ─── Tema del panel de administración (django-unfold) ─────────────────────────
UNFOLD = {
    'SITE_TITLE': 'SRNI · Unidad para las Víctimas',
    'SITE_HEADER': 'SRNI · Unidad para las Víctimas',
    'SITE_SUBHEADER': 'Sistema de Caracterización (SRNI)',
    'SITE_BRAND': 'SRNI',
    'THEME': 'dark',              # fuerza el tema oscuro de Unfold (usa el logo en negativo)
    # Logo institucional de la Unidad para las Víctimas (servido desde static/marca/).
    # Horizontal a color en modo claro, en negativo (blanco) en modo oscuro.
    'SITE_LOGO': {
        'light': lambda request: static('marca/logo-unidad-horizontal-color.svg'),
        'dark': lambda request: static('marca/logo-unidad-horizontal-negativo.svg'),
    },
    'SITE_ICON': {
        'light': lambda request: static('marca/logo-unidad-vertical-color.svg'),
        'dark': lambda request: static('marca/logo-unidad-vertical-bn-negativo.svg'),
    },
    # CSS propio para compactar el panel (se ve "muy grande" por defecto).
    'STYLES': [
        lambda request: static('marca/admin-extra.css'),
    ],
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': True,
    'SHOW_THEME_SWITCHER': True,   # selector claro/oscuro (dark mode disponible)
    'ENVIRONMENT': 'srni.settings.base.unfold_environment_callback',
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': True,
        'navigation': [
            {
                'title': 'Formularios / Diccionario',
                'icon': 'menu_book',
                'items': [
                    {'title': 'Instrumentos', 'icon': 'assignment',
                     'link': reverse_lazy('admin:formulario_instrumento_changelist')},
                    {'title': 'Capítulos', 'icon': 'folder',
                     'link': reverse_lazy('admin:formulario_capitulo_changelist')},
                    {'title': 'Preguntas', 'icon': 'quiz',
                     'link': reverse_lazy('admin:formulario_pregunta_changelist')},
                    # Nota: OpcionRespuesta solo existe como inline (sin changelist) → se omite.
                    {'title': 'Reglas Skip-Logic', 'icon': 'account_tree',
                     'link': reverse_lazy('admin:formulario_reglaskiplogic_changelist')},
                ],
            },
            {
                'title': 'Caracterización / Entrevistas',
                'icon': 'how_to_reg',
                'items': [
                    {'title': 'Sesiones de encuesta', 'icon': 'fact_check',
                     'link': reverse_lazy('admin:encuestas_sesionencuesta_changelist')},
                    {'title': 'Respuestas', 'icon': 'checklist',
                     'link': reverse_lazy('admin:encuestas_respuestaencuesta_changelist')},
                    {'title': 'Hogares', 'icon': 'home',
                     'link': reverse_lazy('admin:hogares_hogar_changelist')},
                    {'title': 'Miembros del hogar', 'icon': 'groups',
                     'link': reverse_lazy('admin:hogares_miembrohogar_changelist')},
                ],
            },
            {
                'title': 'Víctimas',
                'icon': 'shield_person',
                'items': [
                    {'title': 'Víctimas', 'icon': 'shield_person',
                     'link': reverse_lazy('admin:victimas_victima_changelist')},
                ],
            },
            {
                'title': 'Paramétricas',
                'icon': 'map',
                'items': [
                    {'title': 'Departamentos', 'icon': 'map',
                     'link': reverse_lazy('admin:parametricas_departamento_changelist')},
                    {'title': 'Municipios', 'icon': 'location_city',
                     'link': reverse_lazy('admin:parametricas_municipio_changelist')},
                    {'title': 'Veredas', 'icon': 'cottage',
                     'link': reverse_lazy('admin:parametricas_vereda_changelist')},
                    {'title': 'Tipos de documento', 'icon': 'badge',
                     'link': reverse_lazy('admin:parametricas_tipodocumento_changelist')},
                    {'title': 'Comunidades negras', 'icon': 'diversity_3',
                     'link': reverse_lazy('admin:parametricas_comunidadnegra_changelist')},
                    {'title': 'Resguardos indígenas', 'icon': 'forest',
                     'link': reverse_lazy('admin:parametricas_resguardoindigena_changelist')},
                    {'title': 'Direcciones territoriales', 'icon': 'apartment',
                     'link': reverse_lazy('admin:parametricas_direccionterritorial_changelist')},
                    {'title': 'Puntos de atención', 'icon': 'support_agent',
                     'link': reverse_lazy('admin:parametricas_puntoatencion_changelist')},
                ],
            },
            {
                'title': 'IA / Asistente',
                'icon': 'smart_toy',
                'items': [
                    {'title': 'Consentimientos IA', 'icon': 'verified_user',
                     'link': reverse_lazy('admin:ia_consentimientoia_changelist')},
                    {'title': 'Sesiones IA', 'icon': 'smart_toy',
                     'link': reverse_lazy('admin:ia_sesionia_changelist')},
                ],
            },
            {
                'title': 'Usuarios y accesos',
                'icon': 'admin_panel_settings',
                'items': [
                    {'title': 'Usuarios', 'icon': 'person',
                     'link': reverse_lazy('admin:autenticacion_usuario_changelist')},
                    {'title': 'Perfiles', 'icon': 'badge',
                     'link': reverse_lazy('admin:autenticacion_perfil_changelist')},
                    {'title': 'Log de acceso (auditoría)', 'icon': 'shield',
                     'link': reverse_lazy('admin:auditoria_logacceso_changelist')},
                ],
            },
        ],
    },
}

# Dashboard personalizado del panel (solo presentación — KPIs, gráficos, tabla).
# Enriquece el context del index del admin. Ver srni/dashboard.py.
UNFOLD['DASHBOARD_CALLBACK'] = 'srni.dashboard.dashboard_callback'

# ─── Distribución móvil (APK) ────────────────────────────────────────────────
MOVIL_VERSION = config('MOVIL_VERSION', default='1.0.0')
MOVIL_VERSION_CODE = config('MOVIL_VERSION_CODE', default=1, cast=int)
MOVIL_ACTUALIZACION_OBLIGATORIA = config('MOVIL_ACTUALIZACION_OBLIGATORIA', default=False, cast=bool)

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
STATICFILES_DIRS = [BASE_DIR / 'static']   # incluye static/marca/ (logos del admin)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- IA — Gemini ---
# La clave API NUNCA se envía a la app móvil. Solo el backend llama a Gemini.
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Regla universal vigente: 1 víctima → 1 hogar → 1 caracterización activa.
# Para probar otro instrumento sobre la misma víctima: completar la sesión actual,
# archivar el hogar, crear hogar nuevo con la misma víctima.

# --- Cifrado de campos PII ---
# Clave AES-256 para EncryptedField personalizado (apps/victimas/fields.py)
# En desarrollo: valor de .env; en producción: Docker Secret
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')
