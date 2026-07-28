"""
Servicios de negocio de Hogares — port de la lógica PL/SQL legacy (RNIENTREVISTA).

Cada módulo reimplementa, sobre los modelos Django existentes (Hogar, MiembroHogar),
una porción de la lógica de los packages GIC_CATEGORIZACION / GIC_N_CARACTERIZACION,
SIN tocar Oracle. Ver docs/oracle-legacy/paridad_logica_portada.md para el mapa
"portado igual vs. mejorado".
"""
from .codigo_hogar import generar_codigo_hogar
from .alta_hogar import crear_hogar, hogar_abierto_del_usuario, ResultadoAltaHogar, ESTADO_ABIERTO
from .alta_miembro import (
    agregar_miembro,
    documento_ya_en_hogar_activo_reciente,
    MiembroDuplicadoError,
    VENTANA_DUPLICADO,
)

__all__ = [
    "generar_codigo_hogar",
    "crear_hogar",
    "hogar_abierto_del_usuario",
    "ResultadoAltaHogar",
    "ESTADO_ABIERTO",
    "agregar_miembro",
    "documento_ya_en_hogar_activo_reciente",
    "MiembroDuplicadoError",
    "VENTANA_DUPLICADO",
]
