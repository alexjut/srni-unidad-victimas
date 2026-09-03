"""
Configuración BASE — SRNI Backend
Solo contiene ajustes comunes a todos los entornos.
DATABASES, CACHES y almacenamiento se definen en cada entorno (development / production).
NUNCA poner credenciales aquí.
"""
import os
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab   # para CELERY_BEAT_SCHEDULE (al final del archivo)
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
    'apps.capacitacion',
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

# ─── De dónde salen las personas al buscar por documento ─────────────────────
# 'DJANGO' → el padrón cargado en nuestra base (`cargar_padron_oracle`): lo real.
# 'MOCK'   → datos de prueba (ENC001, documentos 999…), para desarrollo y tests.
#
# El default es MOCK a propósito, y no DJANGO: si alguien despliega sin configurar
# esto, es preferible que el sistema responda con datos de prueba evidentes a que
# responda "no se encontró la persona" con un padrón vacío. Lo segundo se confunde
# con un dato real y llevaría a un encuestador a concluir que alguien no está en
# el RUV. → `apps/victimas/repository/__init__.py::get_repository`
#
# ⚠ Producción lo tuvo sin definir hasta el 31-jul-2026 y por eso respondía con el
# mock. El compose de despliegue ahora lo pone en DJANGO explícitamente.
VICTIMA_REPOSITORY = config('VICTIMA_REPOSITORY', default='MOCK')

# Techo de personas que devuelve /api/victimas/precarga/ al iniciar sesión.
# El padrón real tiene 5,9 M: servirlas en JSON revienta la memoria y agota el
# timeout de 30 s de la APK. El padrón completo va como archivo SQLite por
# `padron/download/`; esto es solo el arranque de la jornada.
PRECARGA_LIMITE_PERSONAS = config('PRECARGA_LIMITE_PERSONAS', default=5000, cast=int)

# ─── Distribución móvil (APK) ────────────────────────────────────────────────
MOVIL_VERSION = config('MOVIL_VERSION', default='1.0.0')
MOVIL_VERSION_CODE = config('MOVIL_VERSION_CODE', default=1, cast=int)
MOVIL_ACTUALIZACION_OBLIGATORIA = config('MOVIL_ACTUALIZACION_OBLIGATORIA', default=False, cast=bool)

# Dirección pública desde la que se descarga la APK, tal como la ve el celular.
# Detrás del WAF de la entidad no se puede deducir: FortiWeb termina el TLS y
# reenvía en claro al :80, así que Django ve una petición HTTP aunque el usuario
# haya entrado por HTTPS, y `build_absolute_uri` devolvía `http://…`. Si queda
# vacía se reconstruye desde la petición (ver apps/movil/views.py).
MOVIL_URL_BASE = config('MOVIL_URL_BASE', default='')

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

# --- Oracle legacy (RNIENTREVISTA) — SOLO para validación de paridad ---
# Conexión vía oracledb (thin mode), NO es un backend de Django ORM. Se consume
# desde los scripts/tests de validación (feat/oracle-legacy-writer). Por defecto
# apunta al Oracle LOCAL de Docker (infra/oracle-local); nunca a producción.
ORACLE_LEGACY = {
    'HOST':     config('ORACLE_LEGACY_HOST', default='localhost'),
    'PORT':     config('ORACLE_LEGACY_PORT', default=1521, cast=int),
    'SERVICE':  config('ORACLE_LEGACY_SERVICE', default='FREEPDB1'),
    'USER':     config('ORACLE_LEGACY_USER', default='RNIENTREVISTA'),
    'PASSWORD': config('ORACLE_LEGACY_PASSWORD', default=''),
    # Usuario/perfil de SERVICIO Oracle para hogares originados en SICAV Móvil
    # (Etapa A). PENDIENTE DE CONFIRMAR CON NEGOCIO (Oscar/UARIV): ¿existe un
    # usuario de servicio en GIC_USUARIO o hay que solicitarlo? Sin estos valores,
    # la ruta confirmada NO arranca (ResolverCatalogos.id_usuario_servicio lanza).
    'USUARIO_SERVICIO_ID': config('ORACLE_USUARIO_SERVICIO_ID', default=None),
    'PERFIL_SERVICIO_ID':  config('ORACLE_PERFIL_SERVICIO_ID', default=None),
}

# --- Celery ---------------------------------------------------------------
# El broker sale de REDIS_URL, que el compose ya inyecta al backend y al worker.
#
# Hasta el 2026-07-28 esto NO estaba configurado: Celery caía a su default
# (`amqp://guest@localhost:5672`, RabbitMQ) y el contenedor `cz_celery` llevaba
# semanas reintentando contra un broker inexistente — "Cannot connect to
# amqp://... Connection refused", 100 reintentos— mientras Redis corría al lado
# sin que nadie lo usara. Por eso no había ninguna tarea ejecutándose.
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=config('REDIS_URL', default=''))
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
CELERY_TASK_DEFAULT_QUEUE = 'sync'
# Las colas que el worker de producción escucha (`celery -A srni worker -Q sync,reports`).
#
# `padron` va SEPARADA y la consume su propio worker (cz_celery_padron). No es un
# capricho de organización: la recarga del padrón ocupa un slot del worker durante
# horas, y con `--concurrency 2` en el worker de `sync` eso significa quedarse con la
# mitad de la capacidad de escritura a Oracle mientras dure. Con una cola aparte, la
# sincronización de hogares sigue fluyendo aunque el padrón lleve dos días cargando.
CELERY_TASK_ROUTES = {
    'apps.sincronizacion.tasks.*': {'queue': 'sync'},
    'apps.victimas.tasks.*': {'queue': 'padron'},
}
CELERY_TASK_ACKS_LATE = True            # si el worker muere, la tarea se re-entrega
CELERY_WORKER_PREFETCH_MULTIPLIER = 1   # una escritura a Oracle por vez, sin acaparar
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540
# Ojo: estos dos límites son el DEFAULT, pensado para escribir un hogar en Oracle.
# Las tareas del padrón declaran los suyos (`soft_time_limit`/`time_limit` en el
# decorador) porque 600 s mataría la recarga a los diez minutos.

# Zona horaria de las tareas programadas.
#
# Sin esto Celery interpreta los `crontab()` en UTC: un "a las 20:00" definido para
# la madrugada colombiana se dispararía a las 15:00 hora local, en plena jornada de
# campo y con la aplicación legacy usando el mismo Oracle. Se ata a TIME_ZONE para
# que el horario del schedule se lea como lo lee un operador aquí.
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Con Redis como broker, un mensaje que el worker no confirma en
# `visibility_timeout` segundos se RE-ENTREGA a otro worker. El default es 1 hora:
# con la recarga del padrón —del orden de un día— Redis la volvería a repartir una
# y otra vez, y habría varias cargas simultáneas contra Oracle. Se sube por encima
# del peor caso previsto. El bloqueo distribuido (srni/bloqueos.py) es la segunda
# red por si aun así se cuela una re-entrega.
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 50 * 3600}

# --- Recarga periódica del padrón ------------------------------------------
# Apagada por defecto, mismo criterio que ORACLE_SYNC: leer millones de filas del
# Oracle de producción es una decisión operativa, no un efecto de desplegar.
#
# Los horarios se leen del entorno (no del código) para poder moverlos editando el
# `.env` del servidor y recreando el contenedor de beat, sin reconstruir la imagen:
# "esta semana no corras, que OTI tiene mantenimiento" no debería exigir un release.
PADRON_RECARGA = {
    'HABILITADA': config('PADRON_RECARGA_HABILITADA', default=False, cast=bool),
    # Cadena completa (padrón + fechas + SQLite). Mensual: el primer sábado, 20:00.
    'HORA': config('PADRON_RECARGA_HORA', default=20, cast=int),
    'DIA_SEMANA': config('PADRON_RECARGA_DIA_SEMANA', default='saturday'),
    'DIAS_MES': config('PADRON_RECARGA_DIAS_MES', default='1-7'),
    # Refresco liviano (fechas + SQLite). Diario, de madrugada.
    'HORA_REFRESCO': config('PADRON_REFRESCO_HORA', default=3, cast=int),
}

# --- Sincronización de NOVEDADES con el legacy -----------------------------
# Otra cosa que la recarga: no relee el padrón, pide solo lo que entró desde la
# última corrida. El legacy mueve ~592 personas y ~270 hogares por día, así que
# cada corrida son segundos (4,2 s medidos) y puede correr cada pocos minutos.
#
# Interruptor propio, separado de PADRON_RECARGA: esto es barato y se quiere
# encendido casi siempre; aquello es caro y se enciende con cuidado. Compartir el
# interruptor obligaría a elegir entre las dos cosas.
PADRON_NOVEDADES = {
    'HABILITADA': config('PADRON_NOVEDADES_HABILITADA', default=False, cast=bool),
    'CADA_MINUTOS': config('PADRON_NOVEDADES_CADA_MINUTOS', default=15, cast=int),
}

# --- Barrida de reintento de la sincronización a Oracle ---------------------
# Recoge los hogares que quedaron sin escribirse (broker caído al cerrar la
# encuesta, interruptor apagado en ese momento, reintentos agotados, máquina de
# estados a medias). Ver apps/sincronizacion/tasks.py.
SYNC_REINTENTO = {
    'HABILITADO': config('SYNC_REINTENTO_HABILITADO', default=False, cast=bool),
    'CADA_MINUTOS': config('SYNC_REINTENTO_CADA_MINUTOS', default=15, cast=int),
    # Cuántos hogares como máximo por corrida. Con `--concurrency 2` y una escritura
    # que puede tardar minutos, encolar de a miles solo alarga la cola: el resto
    # entra en la corrida siguiente, que es dentro de un cuarto de hora.
    'LIMITE': config('SYNC_REINTENTO_LIMITE', default=50, cast=int),
    # No reintentar algo que falló recién: volvería a fallar igual y ensuciaría el
    # log cada cuarto de hora. También evita pisar la tarea original todavía en vuelo.
    'ENFRIAMIENTO_MINUTOS': config('SYNC_REINTENTO_ENFRIAMIENTO', default=30, cast=int),
    # A partir de aquí el hogar necesita que alguien lo mire: insistir no lo arregla.
    'MAX_INTENTOS': config('SYNC_REINTENTO_MAX_INTENTOS', default=5, cast=int),
}

# --- Programación (celery beat) --------------------------------------------
# Schedule ESTÁTICO aquí, NO django-celery-beat (que guarda el calendario en la BD
# y lo deja editable desde el admin). Se evaluaron los dos; el razonamiento:
#
# 1. Lo que estas tareas disparan no es inocuo. Una lee millones de filas del Oracle
#    de la UARIV durante horas; la otra escribe en él de forma irreversible. Un
#    horario así debe pasar por revisión de código y quedar en el historial de git,
#    no a dos clics de cualquiera con permisos de admin — hoy son tres personas, y
#    "cada 5 minutos" en vez de "mensual" es un incidente contra producción.
# 2. Ninguna dependencia ni migración nuevas. El proyecto ya arrastra tres
#    incompatibilidades documentadas con Python 3.14 (ver requirements.txt), y una
#    migración sobre la BD de producción para poder programar tareas es un costo
#    que no hace falta pagar.
# 3. Beat no depende de PostgreSQL: si la base va lenta o está en mantenimiento, el
#    reloj sigue funcionando. Con django-celery-beat, la BD es parte del reloj.
# 4. La flexibilidad que SÍ se necesita —apagar una tarea, mover la hora sin un
#    release— ya está resuelta con las variables de entorno de arriba: se edita el
#    `.env` del servidor y se recrea cz_beat, sin reconstruir la imagen.
#
# Si algún día los horarios pasan a cambiar seguido o los define alguien de negocio,
# django-celery-beat es el paso natural: las tareas no cambian, solo el scheduler.
#
# Beat solo DISPARA; que no se solapen lo garantiza el bloqueo dentro de cada tarea.
CELERY_BEAT_SCHEDULE = {
    'padron-recarga-mensual': {
        'task': 'apps.victimas.tasks.recargar_padron',
        'schedule': crontab(minute=0, hour=PADRON_RECARGA['HORA'],
                            day_of_month=PADRON_RECARGA['DIAS_MES'],
                            day_of_week=PADRON_RECARGA['DIA_SEMANA']),
        # ⚠️ En el crontab de Celery `day_of_month` y `day_of_week` se combinan con
        # Y lógico (en el cron de Unix es O). Por eso '1-7' + 'saturday' significa
        # exactamente "el primer sábado del mes", que es lo que se busca: la ventana
        # de la carga cae íntegra en fin de semana, cuando ni los encuestadores en
        # campo ni la aplicación legacy están golpeando el mismo Oracle.
        #
        # `expires` de 12 h: si el worker estuvo caído todo el sábado, la corrida se
        # descarta en vez de arrancar el lunes a las nueve de la mañana y tener el
        # Oracle de producción ocupado durante la jornada. Se pierde un mes de
        # actualización del padrón —recuperable a mano— y no una semana de trabajo.
        'options': {'queue': 'padron', 'expires': 12 * 3600},
    },
    'padron-refresco-diario': {
        'task': 'apps.victimas.tasks.refrescar_fechas_padron',
        'schedule': crontab(minute=30, hour=PADRON_RECARGA['HORA_REFRESCO']),
        'options': {'queue': 'padron', 'expires': 6 * 3600},
    },
    'padron-novedades': {
        'task': 'apps.victimas.tasks.sincronizar_novedades',
        'schedule': timedelta(minutes=PADRON_NOVEDADES['CADA_MINUTOS']),
        # `expires` de un intervalo: si el worker estuvo caído, no tiene sentido
        # ejecutar las corridas acumuladas — la siguiente ve lo mismo y más, porque
        # el criterio es la marca de agua, no la hora.
        'options': {'queue': 'padron',
                    'expires': 60 * PADRON_NOVEDADES['CADA_MINUTOS']},
    },
    'sincronizacion-reintento': {
        'task': 'apps.sincronizacion.tasks.reintentar_sincronizaciones_pendientes',
        'schedule': timedelta(minutes=SYNC_REINTENTO['CADA_MINUTOS']),
        # `expires` es lo que impide el efecto "tormenta al volver": si el worker
        # estuvo caído seis horas, sin esto arrancaría con dos docenas de barridas
        # acumuladas ejecutándose una tras otra. Con expiración, las vencidas se
        # descartan y solo corre la vigente — que de todos modos ve los mismos
        # pendientes, porque el criterio es el estado de la base, no la hora.
        'options': {'queue': 'sync', 'expires': 60 * SYNC_REINTENTO['CADA_MINUTOS']},
    },
}

# --- Sincronización SICAV → Oracle legacy ---------------------------------
# Interruptor de la escritura AUTOMÁTICA al cerrar una encuesta.
#
# Apagado por defecto, y a propósito: escribir en el Oracle de la UARIV es
# irreversible (los procedures hacen COMMIT interno). Encenderlo es una decisión
# operativa explícita, no algo que deba pasar porque alguien despliegue.
#
# Con AUTOMATICA=False la sesión finalizada igual queda registrada como pendiente
# de sincronizar: no se pierde nada, solo no se escribe todavía.
ORACLE_SYNC = {
    'AUTOMATICA': config('ORACLE_SYNC_AUTOMATICA', default=False, cast=bool),
    'DESTINO':    config('ORACLE_SYNC_DESTINO', default=''),   # 'local' | 'produccion'
}
