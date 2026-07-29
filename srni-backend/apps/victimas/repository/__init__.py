from .base import (
    VictimaRepository,
    VictimaResumen,
    ResultadoBusqueda,
    HechoResumen,
    EstadoHabilitacion,
)
from .django_orm import DjangoVictimaRepository
from .mock import MockVictimaRepository


def get_repository() -> VictimaRepository:
    """
    Retorna la implementación activa del repositorio de víctimas.

    Selección vía settings.VICTIMA_REPOSITORY (string):
      'DJANGO' → DjangoVictimaRepository — el padrón cargado en NUESTRA base.
                 Es la fuente de verdad de SICAV: la APK es offline-first y
                 consulta el padrón que descargó, no un servicio en vivo.
      'MOCK'   → MockVictimaRepository (desarrollo / tests).

    El fallback es MOCK a propósito, y no DJANGO: si alguien despliega sin
    configurar la variable, es preferible que el sistema responda con datos de
    prueba evidentes —ENC001, documentos 999…— a que responda "no se encontró la
    persona" con un padrón vacío. Lo segundo se confunde con un dato real y
    llevaría a un encuestador a concluir que alguien no está en el RUV.
    """
    from django.conf import settings
    backend = getattr(settings, "VICTIMA_REPOSITORY", "MOCK")
    if backend == "DJANGO":
        return DjangoVictimaRepository()
    if backend == "MOCK":
        return MockVictimaRepository()
    return MockVictimaRepository()


__all__ = [
    "VictimaRepository",
    "VictimaResumen",
    "ResultadoBusqueda",
    "HechoResumen",
    "EstadoHabilitacion",
    "DjangoVictimaRepository",
    "MockVictimaRepository",
    "get_repository",
]
