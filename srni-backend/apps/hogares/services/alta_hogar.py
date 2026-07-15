"""
Bloque 1b — Alta de hogar con la regla "1 hogar abierto por usuario".

PORT de GIC_CATEGORIZACION.GIC_INSERT_HOGAR1 (package body líneas 193-206):

    IF TOTALHOGAR = 0 THEN                      -- código no colisiona
      SELECT COUNT(HO.HOG_CODIGO) INTO TOTALHOGARACTIVO
        FROM GIC_HOGAR HO
       WHERE HO.USU_IDUSUARIO = ID_USUARIO AND HO.ESTADO = 'ACTIVA';
      IF TOTALHOGARACTIVO = 0 THEN              -- no hay hogar ACTIVA del usuario
        INSERT INTO GIC_HOGAR VALUES (0, código, ..., 'ACTIVA', ...);
        MARCADOR := '1';
      ELSE                                       -- ya hay uno ACTIVA
        SELECT HO.HOG_CODIGO INTO HOGARACTIVO ...;
        MARCADOR := HOGARACTIVO;                 -- devuelve el existente, NO crea otro
      END IF;
    END IF;

MAPEO DE ESTADO (divergencia consciente — ver reporte de paridad):
- Oracle `ESTADO='ACTIVA'` = hogar ABIERTO / en captura (antes de CERRAR_ENCUESTA).
- El equivalente Django es `estado='BORRADOR'` ("en proceso de captura"); el cierre
  de la encuesta lo pasa a `ACTIVO` ("caracterización completa"). Por eso la regla
  "1 ACTIVA por usuario" se porta como "1 BORRADOR por usuario".
- La regla se llavea por `creado_por` (el encuestador), igual que Oracle la llavea
  por `USU_IDUSUARIO`. Es ORTOGONAL al constraint que Django ya tiene
  (`uniq_hogar_no_archivado_por_autorizado`, llaveado por la víctima autorizada).
"""
from dataclasses import dataclass

# Estado Django equivalente al 'ACTIVA' (abierto) de Oracle.
ESTADO_ABIERTO = "BORRADOR"


@dataclass
class ResultadoAltaHogar:
    """Resultado del alta. `creado=False` ⇒ ya existía un hogar abierto (se devuelve)."""
    hogar: "object"
    creado: bool


def hogar_abierto_del_usuario(user):
    """Devuelve el hogar abierto (BORRADOR) más antiguo del usuario, o None."""
    from apps.hogares.models import Hogar
    return (
        Hogar.objects.filter(creado_por=user, estado=ESTADO_ABIERTO)
        .order_by("created_at")
        .first()
    )


def crear_hogar(*, user, autorizado, municipio=None, **extra) -> ResultadoAltaHogar:
    """
    Crea un hogar abierto para `user`, salvo que ya tenga uno: en ese caso lo
    devuelve sin crear otro (paridad con MARCADOR := HOGARACTIVO).

    `extra` acepta campos opcionales de Hogar (tipo_vivienda, estrato, etc.).
    """
    from apps.hogares.models import Hogar
    from .codigo_hogar import generar_codigo_hogar

    existente = hogar_abierto_del_usuario(user)
    if existente is not None:
        return ResultadoAltaHogar(hogar=existente, creado=False)

    hogar = Hogar.objects.create(
        codigo_hogar=generar_codigo_hogar(user),
        autorizado=autorizado,
        municipio=municipio,
        estado=ESTADO_ABIERTO,
        creado_por=user,
        **extra,
    )
    return ResultadoAltaHogar(hogar=hogar, creado=True)
