"""
Servicios de negocio de Encuestas — port de la lógica PL/SQL legacy (RNIENTREVISTA).

- territorio: cascada de atención (GIC_SP_OB* / GIC_N_RELACION_DT_PUNTO).
- respuestas: guardado de respuesta + limpieza de derivadas (SP_SET_RESPUESTAS_DE_ENCUESTA).

Ver docs/oracle-legacy/paridad_logica_portada.md.
"""
from .territorio import (
    set_cascada_territorial,
    CascadaTerritorialError,
)
from .respuestas import guardar_respuesta, ResultadoGuardarRespuesta

__all__ = [
    "set_cascada_territorial",
    "CascadaTerritorialError",
    "guardar_respuesta",
    "ResultadoGuardarRespuesta",
]
