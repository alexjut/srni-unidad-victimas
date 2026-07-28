"""
Bloque 4 — Cascada territorial de atención.

PORT de los procedures de GIC_N_CARACTERIZACION que pueblan
`GIC_N_RELACION_DT_PUNTO` incrementalmente:
  GIC_SP_OBDEPTOPORDT      → IDDT / IDDEPTOATEN
  GIC_SP_OBTPUNTOATECION   → IDPUNTOATEN
  GIC_SP_OBMUNICIPIOATECION→ IDMUNATEN
  GIC_SP_GUARDAMUNATEN     → guardado final

Evidencia (GIC_SP_OBDEPTOPORDT, package body líneas 3069-3104):
    SELECT count(*) INTO THogar FROM GIC_N_RELACION_DT_PUNTO WHERE hogarcodigo = Hogar_Codigo;
    IF THogar = 0 THEN
       INSERT INTO GIC_N_RELACION_DT_PUNTO VALUES (Hogar_Codigo, '1', Id_dt, '', '', '');
    ELSE
       UPDATE GIC_N_RELACION_DT_PUNTO SET IDDT = Id_dt WHERE hogarcodigo = Hogar_Codigo;
    END IF;
La clave es (HOGARCODIGO, IDPERSONA='1'): UNA fila de territorio por hogar.

MAPEO A DJANGO:
- Esa "fila única por hogar" es la propia `SesionEncuesta` (una por hogar+instrumento);
  el `IDPERSONA='1'` fijo de Oracle equivale a "territorio a nivel de sesión, no por
  persona". Los 4 IDs son 4 FKs: direccion_territorial, departamento_atencion,
  municipio_atencion, punto_atencion.
- La semántica incremental "insert-once-then-update" se traduce a fijar los campos
  sobre la misma sesión, EN ORDEN de dependencia, validando coherencia jerárquica
  (cada nivel debe pertenecer a su padre) para no crear el estado inconsistente que
  en el APK móvil dejaba territorio mal poblado.

RELACIONES REALES (apps/parametricas):
  DireccionTerritorial.departamentos  (M2M → Departamento)
  Municipio.departamento               (FK → Departamento)
  PuntoAtencion.direccion_territorial  (FK → DireccionTerritorial)
  PuntoAtencion.municipio              (FK → Municipio)
"""


class CascadaTerritorialError(ValueError):
    """Se intentó fijar un nivel territorial incoherente con su padre."""


def set_cascada_territorial(
    sesion,
    *,
    direccion_territorial=None,
    departamento=None,
    municipio=None,
    punto=None,
    guardar: bool = True,
):
    """
    Puebla la cascada territorial de una SesionEncuesta en orden de dependencia,
    validando coherencia jerárquica. Devuelve la sesión.

    Orden (igual que Oracle: DT primero, luego dependientes):
      1. direccion_territorial (DT)
      2. departamento  — debe pertenecer a los departamentos de la DT
      3. punto         — su direccion_territorial debe ser la DT
      4. municipio     — su departamento debe ser el fijado; si hay punto con
                         municipio, deben coincidir
    """
    # 1. Dirección territorial (raíz de la cascada).
    if direccion_territorial is not None:
        sesion.direccion_territorial = direccion_territorial

    dt = sesion.direccion_territorial

    # 2. Departamento de atención — debe estar bajo la DT.
    if departamento is not None:
        if dt is None:
            raise CascadaTerritorialError(
                "No se puede fijar departamento sin dirección territorial."
            )
        if not dt.departamentos.filter(pk=departamento.pk).exists():
            raise CascadaTerritorialError(
                f"El departamento {departamento} no pertenece a la DT {dt}."
            )
        sesion.departamento_atencion = departamento

    # 3. Punto de atención — debe colgar de la misma DT.
    if punto is not None:
        if dt is None:
            raise CascadaTerritorialError(
                "No se puede fijar punto de atención sin dirección territorial."
            )
        if punto.direccion_territorial_id != dt.pk:
            raise CascadaTerritorialError(
                f"El punto {punto} no pertenece a la DT {dt}."
            )
        sesion.punto_atencion = punto

    # 4. Municipio de atención — debe estar bajo el departamento fijado, y
    #    coincidir con el municipio del punto si éste lo define.
    if municipio is not None:
        depto = sesion.departamento_atencion
        if depto is not None and municipio.departamento_id != depto.pk:
            raise CascadaTerritorialError(
                f"El municipio {municipio} no pertenece al departamento {depto}."
            )
        punto_final = sesion.punto_atencion
        if punto_final is not None and punto_final.municipio_id not in (None, municipio.pk):
            raise CascadaTerritorialError(
                f"El municipio {municipio} no coincide con el del punto {punto_final}."
            )
        sesion.municipio_atencion = municipio

    if guardar:
        sesion.save(update_fields=[
            "direccion_territorial",
            "departamento_atencion",
            "municipio_atencion",
            "punto_atencion",
            "updated_at",
        ])
    return sesion
