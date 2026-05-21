from .base import (
    VictimaRepository,
    VictimaResumen,
    ResultadoBusqueda,
    HechoResumen,
    EstadoHabilitacion,
)
from .mock import MockVictimaRepository


def get_repository() -> VictimaRepository:
    """
    Retorna la implementación activa del repositorio de víctimas.

    Selección vía settings.VICTIMA_REPOSITORY (string):
      'MOCK'   → MockVictimaRepository (desarrollo / tests)
      'ORACLE' → OracleVictimaRepository (producción — pendiente de implementar)

    Si el valor no se reconoce o no se configura, usa MOCK como fallback seguro.
    """
    from django.conf import settings
    backend = getattr(settings, "VICTIMA_REPOSITORY", "MOCK")
    if backend == "MOCK":
        return MockVictimaRepository()
    # TODO: elif backend == "ORACLE": return OracleVictimaRepository()
    return MockVictimaRepository()


__all__ = [
    "VictimaRepository",
    "VictimaResumen",
    "ResultadoBusqueda",
    "HechoResumen",
    "EstadoHabilitacion",
    "MockVictimaRepository",
    "get_repository",
]
