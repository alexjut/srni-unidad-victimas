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

# ── Validadores de la persona (pasos 4-6) ────────────────────────────────────
# `GIC_N_VALIDADORESXPERSONA` es de donde los reportes y la constancia sacan el
# ESTADO_RUV y los HECHO_VICTIMIZANTE_1..14. Sin estos tres procedures el hogar
# llega al legacy pero esas columnas salen VACÍAS.
#
# ⚠️ NINGUNO ES IDEMPOTENTE. Los tres hacen `INSERT` sin ningún `IF COUNT(*)=0`
# previo (a diferencia de GIC_INSERT_MIEMBRO_HOGAR, que sí lo tiene), y la tabla
# no tiene PK ni UNIQUE (`constraints.tsv:227-228`: solo dos FK, a instrumento y
# a hogar). Llamarlos dos veces deja la fila DUPLICADA y la base no lo impide.
# Por eso el escritor comprueba por SELECT si el validador ya está ANTES de
# invocar — ver `verificacion.contar_validador` y `escritor.paso_validador`.
#
# ⚠️ Y NINGUNO VALIDA SU ENTRADA. Un `VALIDADOR` fuera de dominio no da error:
# la variable local queda NULL y el INSERT se hace igual, dejando una fila con
# `VAL_IDVALIDADOR` NULL que ningún reporte va a encontrar nunca. El dominio se
# comprueba de este lado (ver las constantes de abajo y `mapeo`), no allá.

# Escribe TRES filas de una vez (cuerpo `src_GIC_CATEGORIZACION.sql:469-571`):
#   VAL_IDVALIDADOR=1     PRE_VALOR=VALIDADOR              → ESTADO_RUV del reporte
#   VAL_IDVALIDADOR=5001..5004 (o 7001..7018 del perfil 1558) → tipo de persona
#   VAL_IDVALIDADOR=5005  PRE_VALOR=VALIDADOR_TIPOPERFIL   → perfil del usuario
#
# ⚠️ Efecto colateral no evidente: al final hace
#   `UPDATE GIC_N_RUTA_CARACTERIZACION SET PER_IDPERSONA=…, HOG_CODIGO=…
#    WHERE DOCUMENTO = <el documento de esta persona> AND PER_IDPERSONA = 0`
# o sea que reclama para este hogar cualquier fila de "ruta de caracterización"
# pendiente que tenga ese mismo documento — filas que puede haber creado otro
# proceso. No está acotado por usuario ni por fecha (`:562-566`).
GIC_INSERT_VALIDADOR_HOGAR = Procedimiento(
    "GIC_CATEGORIZACION", "GIC_INSERT_VALIDADOR_HOGAR",
    [
        Param("IDPERSONA", Dir.IN),
        Param("CODHOGAR", Dir.IN),
        Param("VALIDADOR", Dir.IN),              # 'INCLUIDO' | 'NO INCLUIDO'
        Param("VALIDADOR_TIPOPERSONA", Dir.IN),  # '5001'..'5004'
        Param("VALIDADOR_TIPOPERFIL", Dir.IN),   # el ID_PERFIL_USUARIO, como texto
        Param("IDINSTRUMENTO", Dir.IN),
    ],
)

# Validador 20=JEFE / 21=NO JEFE (`:575-591`).
#
# Se escribe por FIDELIDAD, no porque un reporte lo lea: en el volcado entero no
# hay un solo objeto que consulte los validadores 20 ni 21. El `JEFE_HOGAR` de los
# reportes sale de otro lado —`CASE WHEN MH.PER_ENCUESTADA='SI'`, o sea de
# GIC_MIEMBROS_HOGAR (`src_PKG_REPORTE_CARACTERIZACION.sql:1060, 1081`)—. Se
# replica igual porque el objetivo declarado es que la forma del dato en el legacy
# sea la misma que dejaba la app vieja.
GIC_INSERT_VALIDADOR_PARENT = Procedimiento(
    "GIC_CATEGORIZACION", "GIC_INSERT_VALIDADOR_PARENT",
    [
        Param("IDPERSONA", Dir.IN),
        Param("CODHOGAR", Dir.IN),
        Param("VALIDADOR", Dir.IN),   # 'JEFE' | 'NO JEFE'
        Param("IDINSTRUMENTO", Dir.IN),
    ],
)

# Homologa el hecho 1..14 al validador 101..114 y guarda la fecha (`:741-824`).
# Un `ID_HECHO` fuera de 1..14 NO inserta nada y tampoco falla (el `IF
# VALIDADOR_P <> 0` lo filtra): silencio total, que es peor que un error.
#
# Al terminar llama a `GIC_INSERT_VALIDADOR_ARES`, que crea el validador 506
# (DESPLAZAMIENTO FORZADO a nivel hogar) si el hogar tiene un 105 y un 5001. Ese
# procedure hace `SELECT PER_IDPERSONA INTO …  WHERE VAL_IDVALIDADOR IN (5001)`
# **sin MAX**: con dos personas marcadas 5001 en el mismo hogar lanza
# TOO_MANY_ROWS, su `WHEN OTHERS` se lo traga y el 506 no se crea. En SICAV eso no
# puede pasar —`MiembroHogar` tiene un UNIQUE de un solo `es_autorizado` por
# hogar—, y es justamente lo que lo garantiza.
GIC_INSERT_VALIDADOR_HECHO_AUX = Procedimiento(
    "GIC_CATEGORIZACION", "GIC_INSERT_VALIDADOR_HECHO_AUX",
    [
        Param("IDPERSONA", Dir.IN),
        Param("CODHOGAR", Dir.IN),
        Param("ID_HECHO", Dir.IN),      # 1..14, el dominio de Oracle
        Param("IDINSTRUMENTO", Dir.IN),
        # Fecha del hecho, como TEXTO (la columna es NVARCHAR2(20)). Se redacta:
        # la fecha en que una persona identificada sufrió un hecho victimizante es
        # dato sensible, y en el ledger no aporta nada que el id del hecho no diga.
        Param("FECHA_HECHO", Dir.IN, pii=True),
    ],
)

# `UPDATE GIC_MIEMBROS_HOGAR SET PER_ENCUESTADA='SI'` para UNA persona (`:928-940`).
#
# No es redundante con el `ENCUESTADA` de GIC_INSERT_MIEMBRO_HOGAR aunque escriba
# la misma columna: ese procedure solo inserta `IF CONTEO = 0`, así que en un
# re-run —o si el vínculo ya existía— el valor no se corrige nunca. Este es el
# único camino para arreglarlo, y es idempotente por naturaleza (es un UPDATE).
GIC_ACTUALIZA_ENCUESTADO = Procedimiento(
    "GIC_CATEGORIZACION", "GIC_ACTUALIZA_ENCUESTADO",
    [
        Param("PIDPERSONA", Dir.IN),
        Param("PCODIGO", Dir.IN),
    ],
)

#: `VAL_IDVALIDADOR` del estado en el RUV. Es el que leen los reportes como
#: `ESTADO_RUV` (`src_GIC_N_CARACTERIZACION.sql:3905`, y 8 sitios más).
#:
#: ⚠️ Vale 1 tanto para INCLUIDO como para NO INCLUIDO: el cuerpo asigna
#: `VALIDADOR_P := 1` en las DOS ramas (`:476-482`). Lo que distingue un caso del
#: otro es el TEXTO de `PRE_VALOR`, que es justo lo que el reporte selecciona.
VALIDADOR_ESTADO_RUV = 1

#: Los dos únicos textos que el cuerpo reconoce en `VALIDADOR`. Cualquier otro deja
#: `VAL_IDVALIDADOR` NULL y la fila se vuelve invisible para los reportes.
VALIDADORES_ESTADO_RUV = ("INCLUIDO", "NO INCLUIDO")

#: Tipos de persona que el procedure sabe homologar (`:484-495`). Los 7001-7018 son
#: del perfil 1558 (autoridades étnicas) y SICAV no los usa hoy.
VALIDADORES_TIPO_PERSONA = ("5001", "5002", "5003", "5004")

#: `VAL_IDVALIDADOR` del perfil de usuario — texto libre, lo pone el llamador.
VALIDADOR_PERFIL = 5005

#: Textos del validador de parentesco y los ids que generan.
VALIDADOR_JEFE = "JEFE"
VALIDADOR_NO_JEFE = "NO JEFE"
VALIDADORES_PARENTESCO = {VALIDADOR_JEFE: 20, VALIDADOR_NO_JEFE: 21}

#: Los hechos que el legacy sabe homologar, y el validador de cada uno. El reporte
#: lee `HECHO_VICTIMIZANTE_N` como el `PRE_VALOR` del validador `100+N`, así que la
#: POSICIÓN es fija: el hecho 5 siempre es desplazamiento forzado, esté o no.
HECHO_MINIMO, HECHO_MAXIMO = 1, 14


def validador_de_hecho(id_hecho: int) -> int:
    """El `VAL_IDVALIDADOR` que deja el hecho `id_hecho` (1..14 → 101..114)."""
    return 100 + int(id_hecho)


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
# El archivado de respuestas —copiar de la tabla de trabajo a
# GIC_N_RESPUESTASENCUESTA_C, la definitiva que leen los reportes, y borrar la de
# trabajo— ocurre con TODOS los códigos MENOS '5' (reabrir) y '3' (aplazar). O sea
# que anular también archiva. Verificado en producción el 2-ago al anular el hogar
# piloto: sus 3 respuestas pasaron de la de trabajo a la definitiva.
#
# La diferencia entre '4' y el resto está en OTRA cosa: solo el camino de CERRADA
# exige **más de 3 capítulos terminados** (`IF totalCT > 3`). Si no los hay, esa
# rama cae en un `ELSE NULL` y termina sin error — ni cambia el estado ni archiva.
# Los demás códigos no piden capítulos: su rama hace el UPDATE directo.
#
# Por eso el resultado SIEMPRE se verifica por SELECT, en los dos caminos.
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
