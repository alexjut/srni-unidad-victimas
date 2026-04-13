# Importar app Celery cuando esté disponible (no requerido en desarrollo)
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    pass
