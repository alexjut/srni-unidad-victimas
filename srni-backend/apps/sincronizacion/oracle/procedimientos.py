"""
Capa de invocación de los PROCEDURES OFICIALES de Oracle (Etapa A).

Cada función envuelve un procedure real de RNIENTREVISTA con firma clara y arma
el bloque PL/SQL anónimo de invocación (BEGIN PKG.PROC(...); END;) con binds por
NOMBRE. Las firmas provienen de all_arguments del esquema real (verificadas contra
el Oracle local, 2026-07-15).

DRY-RUN por defecto (patrón de generar_expdp_estructura.py): si `confirmar=False`
se construye y devuelve el bloque + binds redactados SIN ejecutar ni conectar.
Solo con `confirmar=True` y un `cursor` real se ejecuta y se leen los OUT.

PII: los binds marcados PII (nombres, documento, fecha de nacimiento) JAMÁS se
imprimen ni se guardan en claro. En el bloque renderizado y en el payload de
auditoría aparecen como '***'. Los valores reales solo viven en memoria y solo
se envían a Oracle en la ruta confirmada.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class Dir(Enum):
    IN = "IN"
    OUT = "OUT"


@dataclass
class Param:
    nombre: str          # nombre del argumento formal en Oracle (p.ej. 'ID_USUARIO')
    direccion: Dir
    pii: bool = False    # si True, se redacta en logs/auditoría


@dataclass
class Procedimiento:
    """Descriptor de un procedure oficial y su lista de argumentos (orden real)."""
    paquete: str
    nombre: str
    params: list  # list[Param]

    @property
    def ref(self) -> str:
        return f"{self.paquete}.{self.nombre}"


# ── Firmas reales (all_arguments, esquema RNIENTREVISTA) ─────────────────────
GIC_INSERT_HOGAR1 = Procedimiento(
    "GIC_CATEGORIZACION", "GIC_INSERT_HOGAR1",
    [
        Param("USUA_CREACION", Dir.IN),
        Param("ID_USUARIO", Dir.IN),
        Param("ID_PERFIL_USUARIO", Dir.IN),
        Param("ID_TIPO_CARACTERIZACION", Dir.IN),
        Param("MARCADOR", Dir.OUT),  # HOG_CODIGO existente, o '1' si creó uno nuevo
    ],
)

GIC_INSERT_PERSONAS = Procedimiento(
    "GIC_CATEGORIZACION", "GIC_INSERT_PERSONAS",
    [
        Param("PNOMBRE", Dir.IN, pii=True),
        Param("SNOMBRE", Dir.IN, pii=True),
        Param("PAPELLIDO", Dir.IN, pii=True),
        Param("SAPELLIDO", Dir.IN, pii=True),
        Param("FNACIMIENTO", Dir.IN, pii=True),
        Param("TDOC", Dir.IN),
        Param("USUARIO", Dir.IN),
        Param("USU_FCREACION", Dir.IN),
        Param("NDOCU", Dir.IN, pii=True),
        Param("RELAC", Dir.IN),
        Param("ID_DECLAR", Dir.IN),
        Param("ID_PERS_FUENTE", Dir.IN),
        Param("T_VICTIMA", Dir.IN),
        Param("ID_SINIESTRO", Dir.IN),
        Param("FUENTEE", Dir.IN),
        Param("ESTADO", Dir.IN),
        Param("IDPERMI", Dir.IN),
        Param("VALSECUENCIA", Dir.OUT),  # PER_IDPERSONA generado
    ],
)

GIC_INSERT_MIEMBRO_HOGAR = Procedimiento(
    "GIC_CATEGORIZACION", "GIC_INSERT_MIEMBRO_HOGAR",
    [
        Param("IDHOGAR", Dir.IN),        # = HOG_CODIGO
        Param("ID_PERSONA", Dir.IN),     # = PER_IDPERSONA (VALSECUENCIA)
        Param("USUARIO", Dir.IN),
        Param("ID_USUARIO", Dir.IN),
        Param("ENCUESTADA", Dir.IN),
    ],
)

SP_SET_RESPUESTAS_DE_ENCUESTA = Procedimiento(
    "GIC_N_CARACTERIZACION", "SP_SET_RESPUESTAS_DE_ENCUESTA",
    [
        Param("PCOD_HOGAR", Dir.IN),
        Param("PPER_IDPERSONA", Dir.IN),
        Param("PRES_IDRESPUESTA", Dir.IN),
        # Texto libre de la respuesta. Se redacta SIEMPRE: en una caracterización de
        # víctimas el texto libre puede traer nombres, direcciones o relatos de los
        # hechos, y desde aquí no se sabe qué pregunta lo originó. Se prefiere perder
        # detalle en la auditoría antes que filtrar PII al ledger o a la consola.
        Param("PRXP_TEXTORESPUESTA", Dir.IN, pii=True),
        Param("PRXP_TIPOPREGUNTARESPUESTA", Dir.IN),
        Param("PINS_IDINSTRUMENTO", Dir.IN),
        Param("PUSU_USUARIOCREACION", Dir.IN),
        Param("PPER_IDPREGUNTAPADRE", Dir.IN),
        Param("PBANDERA", Dir.IN),
    ],
)

# ── Cascada territorial ──────────────────────────────────────────────────────
# Son procedures de UI (el front web los llama para llenar cada combo), pero cada
# uno escribe UNA columna de GIC_N_RELACION_DT_PUNTO por efecto colateral y devuelve
# un REF CURSOR con las opciones del nivel siguiente, que aquí se ignora: solo
# interesa la escritura. Orden y semántica verificados en el package body
# (líneas 3069-3252); ver mapeo.binds_territorio para el detalle y las trampas.
#
#   procedure                  | recibe        | escribe
#   GIC_SP_OBDEPTOPORDT        | id de DT      | IDDT        (+ INSERT de la fila)
#   GIC_SP_OBTPUNTOATECION     | id de DEPTO ⚠ | IDDEPTOATEN
#   GIC_SP_OBMUNICIPIOATECION  | id de PUNTO   | IDPUNTOATEN
#   GIC_SP_GUARDAMUNATEN       | id de MUNIC.  | IDMUNATEN
# Marca un capítulo como terminado. DELETE + INSERT sobre GIC_N_CAPITULOS_TER, o
# sea idempotente por (hogar, tema): repetirlo no duplica.
#
# Existe por una razón que no es cosmética: el cierre EXIGE más de 3 capítulos
# terminados. Sin este paso, `SP_ACTUALIZAR_ESTADO_ENCUESTA` cae en un `ELSE NULL`
# y devuelve éxito **sin cerrar nada** — y sin cierre no hay fila en
# GIC_N_RESPUESTASENCUESTA_C, que es de donde salen los reportes.
SP_FINALIZARCAPITULO = Procedimiento(
    "GIC_N_CARACTERIZACION", "SP_FINALIZARCAPITULO",
    [
        Param("PCODHOGAR", Dir.IN),
        Param("PIDTEMA", Dir.IN),
        Param("PUSUARIO", Dir.IN),
    ],
)

# El cierre REAL de la encuesta. `TIPO_APLAZAMIENTO` es un código, no un texto:
#   '1' ANULADA · '2' HOGAR_NO_RESPONDE · '3' APLAZADA
#   '4' CERRADA  · '5' ACTIVA (reabre)  · '6' ERROR
#
# Con '4' el procedure copia las respuestas de la tabla de trabajo a
# GIC_N_RESPUESTASENCUESTA_C (la definitiva, la que leen los reportes), borra la de
# trabajo y las preguntas derivadas. **Solo si hay más de 3 capítulos terminados**;
# si no, no hace nada y termina sin error, así que el resultado hay que verificarlo
# por SELECT.
SP_ACTUALIZAR_ESTADO_ENCUESTA = Procedimiento(
    "GIC_N_CARACTERIZACION", "SP_ACTUALIZAR_ESTADO_ENCUESTA",
    [
        Param("HOGCODIGO", Dir.IN),
        Param("USUARIO", Dir.IN),
        Param("TIPO_APLAZAMIENTO", Dir.IN),
    ],
)

#: Los códigos de `TIPO_APLAZAMIENTO`, para no escribir literales sueltos.
CIERRE_ANULADA = "1"
CIERRE_NO_RESPONDE = "2"
CIERRE_APLAZADA = "3"
CIERRE_CERRADA = "4"
CIERRE_REABRIR = "5"

#: Mínimo de capítulos terminados que el procedure exige para cerrar de verdad
#: (`IF totalCT > 3`, cuerpo de SP_ACTUALIZAR_ESTADO_ENCUESTA).
CAPITULOS_MINIMOS_PARA_CERRAR = 4


GIC_SP_OBDEPTOPORDT = Procedimiento(
    "GIC_N_CARACTERIZACION", "GIC_SP_OBDEPTOPORDT",
    [Param("PHOGAR_CODIGO", Dir.IN), Param("ID_DT", Dir.IN), Param("CUR_OUT", Dir.OUT)],
)
# ⚠️ El formal se llama ID_DT pero el cuerpo hace `SET iddeptoaten = Id_dt` y filtra
# `T.IDDEPARTAMENTO = pId_DT`: espera el id de DEPARTAMENTO. El nombre miente; el
# bind debe conservarlo (se invoca por nombre formal) pero el VALOR es el depto.
GIC_SP_OBTPUNTOATECION = Procedimiento(
    "GIC_N_CARACTERIZACION", "GIC_SP_OBTPUNTOATECION",
    [Param("PHOGAR_CODIGO", Dir.IN), Param("ID_DT", Dir.IN), Param("CUR_OUT", Dir.OUT)],
)
GIC_SP_OBMUNICIPIOATECION = Procedimiento(
    "GIC_N_CARACTERIZACION", "GIC_SP_OBMUNICIPIOATECION",
    [Param("PHOGAR_CODIGO", Dir.IN), Param("ID_PT", Dir.IN), Param("CUR_OUT", Dir.OUT)],
)
GIC_SP_GUARDAMUNATEN = Procedimiento(
    "GIC_N_CARACTERIZACION", "GIC_SP_GUARDAMUNATEN",
    [Param("PHOGAR_CODIGO", Dir.IN), Param("ID_MA", Dir.IN), Param("CUR_OUT", Dir.OUT)],
)

REDACTADO = "***"


@dataclass
class ResultadoInvocacion:
    """
    Lo que devuelve invocar(). En DRY-RUN, `ejecutado=False` y `salidas={}`.
    `bloque` y `binds_redactados` son seguros para log/auditoría (sin PII).
    """
    procedimiento: str
    bloque: str                       # bloque PL/SQL parametrizado (con :binds)
    binds_redactados: dict            # binds IN con PII enmascarada — para auditoría
    ejecutado: bool
    salidas: dict = field(default_factory=dict)  # valores OUT (solo si ejecutado)


def _construir_bloque(proc: Procedimiento) -> str:
    """BEGIN PKG.PROC(FORMAL => :formal, ...); END; con binds por nombre."""
    args = ",\n    ".join(f"{p.nombre} => :{p.nombre.lower()}" for p in proc.params)
    return f"BEGIN\n  {proc.ref}(\n    {args}\n  );\nEND;"


def _valor_bind(v):
    """Normaliza un valor Python a algo que oracledb acepte como bind IN."""
    if isinstance(v, (datetime, date)):
        return v
    return v


def _json_safe(v):
    """Coerciona a algo serializable en el JSONField de auditoría."""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _redactar(proc: Procedimiento, valores: dict) -> dict:
    """Copia de `valores` con los binds PII enmascarados (para logs/auditoría).

    El resultado es JSON-safe: las fechas NO-PII se serializan a ISO. Las PII
    (incluida fecha de nacimiento) van como '***', nunca en claro.
    """
    pii = {p.nombre.lower() for p in proc.params if p.pii}
    salida = {}
    for p in proc.params:
        if p.direccion is not Dir.IN:
            continue
        k = p.nombre.lower()
        salida[k] = REDACTADO if k in pii else _json_safe(valores.get(k))
    return salida


def invocar(proc: Procedimiento, valores: dict, *, confirmar: bool = False, cursor=None) -> ResultadoInvocacion:
    """
    Arma (y opcionalmente ejecuta) la invocación de `proc` con `valores`
    (dict formal_lower → valor). DRY-RUN salvo confirmar=True + cursor real.

    - DRY-RUN: NO conecta, NO ejecuta; devuelve bloque + binds redactados.
    - Confirmado: ejecuta en `cursor`, lee los OUT y los devuelve en `salidas`.
      OJO: por el WHEN OTHERS interno del procedure, que esto no lance NO prueba
      que la escritura ocurrió — la verificación real es por SELECT (ver
      verificacion.py). Los OUT (MARCADOR/VALSECUENCIA) son pistas, no garantía.
    """
    bloque = _construir_bloque(proc)
    binds_redactados = _redactar(proc, valores)

    if not confirmar:
        return ResultadoInvocacion(
            procedimiento=proc.ref, bloque=bloque,
            binds_redactados=binds_redactados, ejecutado=False,
        )

    if cursor is None:
        raise ValueError("confirmar=True requiere un cursor de Oracle real.")

    # Binds reales: IN con su valor; OUT como variables de salida tipadas.
    binds = {}
    out_vars = {}
    import oracledb
    for p in proc.params:
        k = p.nombre.lower()
        if p.direccion is Dir.IN:
            binds[k] = _valor_bind(valores.get(k))
        else:
            # OUT: REF CURSOR para los cascade; NUMBER/STRING para el resto.
            if p.nombre == "CUR_OUT":
                # DEBE ser un OBJETO cursor separado, NO cursor.var(DB_TYPE_CURSOR)
                # sobre el mismo cursor que ejecuta el bloque: esos procedures hacen
                # INSERT+COMMIT y luego OPEN cur_OUT, y con cursor.var la llamada CUELGA
                # indefinidamente. Verificado 2026-07-24 en la réplica local: cursor
                # separado / callproc = 0.01 s; cursor.var(mismo cursor) = timeout.
                var = cursor.connection.cursor()
            elif p.nombre in ("VALSECUENCIA",):
                var = cursor.var(oracledb.DB_TYPE_NUMBER)
            else:  # MARCADOR y afines
                var = cursor.var(oracledb.DB_TYPE_NVARCHAR)
            out_vars[k] = var
            binds[k] = var

    cursor.execute(bloque, binds)
    salidas = {}
    for k, var in out_vars.items():
        if k == "cur_out":
            continue  # el REF CURSOR de los cascade no aporta al ledger
        salidas[k] = var.getvalue()

    return ResultadoInvocacion(
        procedimiento=proc.ref, bloque=bloque,
        binds_redactados=binds_redactados, ejecutado=True, salidas=salidas,
    )
