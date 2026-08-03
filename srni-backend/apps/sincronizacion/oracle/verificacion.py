"""
Verificación POR CONSULTA del resultado de cada paso (solo SELECT).

Racional (ver ruta_escritura.md §4): los procedures hacen COMMIT interno y tragan
sus excepciones con `EXCEPTION WHEN OTHERS`. Por eso "el procedure no lanzó" NO
prueba que la fila quedó escrita. Tras CADA llamada, el escritor confirma el
resultado esperado con un SELECT; solo entonces marca el paso VERIFICADO y avanza.

Todo aquí es SOLO LECTURA. Devuelve (ok, detalle) donde `detalle` es auditable y
sin PII (conteos, códigos e ids, nunca nombres ni documentos).
"""
from . import procedimientos as P


def _scalar(cursor, sql, binds):
    cursor.execute(sql, binds)
    row = cursor.fetchone()
    return row[0] if row else None


#: Lo que `GIC_INSERT_HOGAR1` devuelve en MARCADOR cuando SÍ creó el hogar.
MARCADOR_HOGAR_CREADO = "1"


def reloj_oracle(cursor):
    """
    El instante actual **según Oracle**, para acotar "recién creado".

    No sirve la hora de Django: entre el servidor de aplicaciones y la base hay
    horas de diferencia, y una ventana calculada con el reloj equivocado deja
    pasar hogares ajenos o rechaza los propios.
    """
    return _scalar(cursor, "SELECT SYSDATE FROM DUAL", {})


def verificar_hogar(cursor, *, id_usuario=None, marcador=None, creado_desde=None,
                    hog_codigo=None):
    """
    Confirma que el hogar que quedó en Oracle es **el nuestro**, recién creado.

    ─── El comportamiento del procedure, que es contraintuitivo ───────────────
    `GIC_INSERT_HOGAR1` **no siempre crea un hogar**. Su cuerpo solo inserta si el
    `ID_USUARIO` no tiene ningún hogar en estado ACTIVA; si ya tiene uno, no crea
    nada y devuelve en `MARCADOR` **el código del hogar viejo**. Y cuando sí crea,
    devuelve `MARCADOR = '1'`, no el código.

    O sea que la semántica está invertida respecto de lo que uno esperaría:

        MARCADOR == '1'   →  se creó un hogar nuevo (hay que averiguar su código)
        MARCADOR != '1'   →  NO se creó nada; eso es el código de un hogar PREVIO

    ─── Por qué esto no puede tratarse como éxito ────────────────────────────
    La versión anterior tomaba ese código previo como si fuera el hogar recién
    escrito. A partir de ahí, las personas, el territorio y las respuestas del
    hogar nuevo se colgaban de un hogar que ya existía: dos caracterizaciones
    fundidas en una.

    Y no queda en un dato mezclado. Escribir una sola respuesta en un hogar ajeno
    dispara `SP_INS_ETNIA_ARES`, que arranca con dos `DELETE` sobre
    `GIC_N_VALIDADORESXPERSONA` filtrando **solo por HOG_CODIGO**: borra los
    validadores de ese hogar, que es de donde salen su estado en el RUV y sus
    hechos victimizantes. Sobre datos reales de la UARIV y sin rollback posible,
    porque los procedures hacen COMMIT interno.

    ─── Qué exige ahora ──────────────────────────────────────────────────────
    1. `MARCADOR == '1'`. Cualquier otra cosa es "no se creó" → FALLIDO.
    2. El hogar resuelto tiene que ser **nuevo**: creado a partir de
       `creado_desde` (el reloj de Oracle tomado justo antes de invocar). Sin esa
       ventana, "el ACTIVA más reciente del usuario" puede ser de otra corrida o
       de otro encuestador que comparta el `ID_USUARIO`.

    Devuelve `(ok, detalle)`; el detalle explica el motivo del rechazo para que
    quede en el ledger y se pueda leer después.
    """
    if marcador is not None and str(marcador).strip() != MARCADOR_HOGAR_CREADO:
        # No creó nada: ese código es de un hogar que ya existía.
        return False, {
            "error": "hogar_no_creado",
            "motivo": ("GIC_INSERT_HOGAR1 no creó el hogar porque el ID_USUARIO ya "
                       "tenía uno en ACTIVA; el MARCADOR trae el código de ESE hogar. "
                       "Seguir escribiendo ahí fundiría dos caracterizaciones."),
            "codigo_preexistente": str(marcador),
            "id_usuario": id_usuario,
        }

    if id_usuario is None:
        return False, {"error": "sin id_usuario para resolver el hogar creado"}

    if creado_desde is None:
        # Sin ventana no se puede afirmar que el hogar es nuestro. Antes se
        # resolvía igual —"el ACTIVA más reciente"— y ahí estaba el agujero.
        return False, {
            "error": "sin_ventana_temporal",
            "motivo": ("Hace falta el instante previo a la invocación (reloj de "
                       "Oracle) para poder afirmar que el hogar es de esta corrida."),
        }

    cursor.execute(
        """SELECT hog_codigo, usu_fechacreacion FROM gic_hogar
            WHERE usu_idusuario = :u
              AND estado = 'ACTIVA'
              AND usu_fechacreacion >= :desde
            ORDER BY usu_fechacreacion DESC""",
        {"u": id_usuario, "desde": creado_desde},
    )
    filas = cursor.fetchall()

    if not filas:
        return False, {
            "error": "hogar_no_encontrado",
            "motivo": ("El procedure dijo que creó el hogar pero no aparece ninguno "
                       "nuevo para este usuario desde el inicio del paso."),
            "id_usuario": id_usuario, "desde": str(creado_desde),
        }

    if len(filas) > 1:
        # Dos hogares nuevos del mismo usuario en la misma ventana: no se puede
        # afirmar cuál es el nuestro. Pasa si dos escrituras corren a la vez con el
        # mismo ID_USUARIO — que es exactamente lo que hay que impedir.
        return False, {
            "error": "hogar_ambiguo",
            "motivo": ("Hay más de un hogar nuevo para este ID_USUARIO en la ventana: "
                       "no se puede afirmar cuál corresponde a esta escritura."),
            "candidatos": [str(f[0]) for f in filas],
            "id_usuario": id_usuario,
        }

    codigo = str(filas[0][0])
    return True, {"hog_codigo": codigo, "resuelto_por": "usuario+ventana",
                  "creado_en": str(filas[0][1])}


def verificar_persona(cursor, *, per_idpersona):
    """Confirma que el PER_IDPERSONA (VALSECUENCIA) existe en GIC_PERSONA."""
    if per_idpersona is None:
        return False, {"error": "VALSECUENCIA nulo"}
    existe = _scalar(
        cursor, "SELECT COUNT(*) FROM gic_persona WHERE per_idpersona = :p",
        {"p": per_idpersona},
    )
    return bool(existe), {"per_idpersona": per_idpersona, "encontrado": bool(existe)}


def verificar_miembro(cursor, *, hog_codigo, per_idpersona):
    """Confirma el vínculo (HOG_CODIGO, PER_IDPERSONA) en GIC_MIEMBROS_HOGAR."""
    existe = _scalar(
        cursor,
        """SELECT COUNT(*) FROM gic_miembros_hogar
            WHERE hog_codigo = :h AND per_idpersona = :p""",
        {"h": hog_codigo, "p": per_idpersona},
    )
    return bool(existe), {
        "hog_codigo": hog_codigo, "per_idpersona": per_idpersona,
        "encontrado": bool(existe),
    }


def verificar_territorio(cursor, *, hog_codigo):
    """
    Confirma que GIC_N_RELACION_DT_PUNTO del hogar quedó COMPLETO (IDDT, IDMUNATEN,
    IDPUNTOATEN no nulos). Este es el punto que históricamente rompió los reportes.
    """
    cursor.execute(
        """SELECT iddt, idmunaten, idpuntoaten FROM gic_n_relacion_dt_punto
            WHERE hogarcodigo = :h""",
        {"h": hog_codigo},
    )
    row = cursor.fetchone()
    if not row:
        return False, {"hog_codigo": hog_codigo, "error": "sin fila de territorio"}
    iddt, idmun, idpto = (str(x).strip() if x is not None else "" for x in row)
    completo = bool(iddt and idmun and idpto)
    return completo, {
        "hog_codigo": hog_codigo, "iddt": iddt,
        "idmunaten": idmun, "idpuntoaten": idpto, "completo": completo,
    }


def verificar_respuesta(cursor, *, hog_codigo, per_idpersona, res_idrespuesta):
    """Confirma la respuesta (HOG_CODIGO, PER_IDPERSONA, RES_IDRESPUESTA)."""
    existe = _scalar(
        cursor,
        """SELECT COUNT(*) FROM gic_n_respuestasencuesta
            WHERE hog_codigo = :h AND per_idpersona = :p AND res_idrespuesta = :r""",
        {"h": hog_codigo, "p": per_idpersona, "r": res_idrespuesta},
    )
    return bool(existe), {
        "hog_codigo": hog_codigo, "per_idpersona": per_idpersona,
        "res_idrespuesta": res_idrespuesta, "encontrado": bool(existe),
    }


# ── validadores de la persona (pasos 4-6) ─────────────────────────────────────
#
# Estas comprobaciones tienen un uso EXTRA respecto de las demás: además de
# verificar después, se consultan ANTES de invocar. Los tres procedures de
# validadores hacen `INSERT` sin comprobar si la fila ya está, y la tabla no tiene
# PK ni UNIQUE que lo impida — así que un reintento sin este chequeo previo deja el
# validador DUPLICADO, y un `ESTADO_RUV` duplicado hace que el subconsulta escalar
# del reporte (`SELECT PRE_VALOR … WHERE VAL_IDVALIDADOR = 1`) falle con
# ORA-01427 en vez de devolver el estado.

def contar_validador(cursor, *, hog_codigo, per_idpersona, val_idvalidador) -> int:
    """Cuántas filas de ese validador tiene ya la persona en ese hogar."""
    return _scalar(
        cursor,
        """SELECT COUNT(*) FROM gic_n_validadoresxpersona
            WHERE hog_codigo = :h AND per_idpersona = :p
              AND val_idvalidador = :v""",
        {"h": hog_codigo, "p": per_idpersona, "v": val_idvalidador},
    ) or 0


def contar_validadores_en(cursor, *, hog_codigo, per_idpersona, valores) -> int:
    """Cuántas filas tiene la persona con cualquiera de esos `val_idvalidador`.

    Hace falta para el validador de parentesco, que puede ser 20 o 21 según el
    caso: preguntar solo por el que vamos a escribir dejaría pasar el reintento de
    una persona cuyo rol cambió, duplicando la fila con el otro código.
    """
    if not valores:
        return 0
    binds = {"h": hog_codigo, "p": per_idpersona}
    marcas = []
    for i, v in enumerate(valores):
        clave = f"v{i}"
        binds[clave] = v
        marcas.append(f":{clave}")
    return _scalar(
        cursor,
        f"""SELECT COUNT(*) FROM gic_n_validadoresxpersona
             WHERE hog_codigo = :h AND per_idpersona = :p
               AND val_idvalidador IN ({', '.join(marcas)})""",
        binds,
    ) or 0


def verificar_validadores(cursor, *, hog_codigo, per_idpersona, estado_esperado,
                          tipo_persona_esperado, jefe_esperado):
    """
    Confirma los CUATRO validadores que deja el paso: estado en el RUV (1), tipo de
    persona (5001-5004), perfil (5005) y parentesco (20 o 21).

    Se comprueba el TEXTO del validador 1, no solo que exista, porque el
    procedure asigna `VAL_IDVALIDADOR := 1` tanto para INCLUIDO como para NO
    INCLUIDO —las dos ramas del `IF` ponen el mismo número—: lo único que
    distingue un estado del otro es el `PRE_VALOR`, que es justo lo que el reporte
    imprime. Mirar solo el id daría por buena una persona con el estado cambiado.

    Y se comprueba que NO haya duplicados: dos filas del validador 1 rompen el
    reporte con ORA-01427 (subconsulta escalar con más de una fila).
    """
    cursor.execute(
        """SELECT val_idvalidador, pre_valor FROM gic_n_validadoresxpersona
            WHERE hog_codigo = :h AND per_idpersona = :p""",
        {"h": hog_codigo, "p": per_idpersona},
    )
    filas = cursor.fetchall()
    encontrados = {}
    for val, pre in filas:
        clave = int(val) if val is not None else None
        encontrados.setdefault(clave, []).append(
            str(pre).strip() if pre is not None else "")

    val_jefe = P.VALIDADORES_PARENTESCO[jefe_esperado]
    detalle = {
        "hog_codigo": hog_codigo, "per_idpersona": per_idpersona,
        "validadores": {str(k): v for k, v in sorted(
            encontrados.items(), key=lambda kv: (kv[0] is None, kv[0]))},
    }

    # Una fila con VAL_IDVALIDADOR NULL es la marca de un valor fuera de dominio:
    # el procedure la insertó igual y no sirve para nada. Se reporta, porque es la
    # única señal de que un bind salió mal.
    if None in encontrados:
        detalle["error"] = "validador_nulo"
        detalle["motivo"] = ("Quedó una fila con VAL_IDVALIDADOR NULL: el procedure "
                             "recibió un valor fuera de su dominio y la insertó igual.")
        return False, detalle

    esperados = [
        (P.VALIDADOR_ESTADO_RUV, estado_esperado),
        (int(tipo_persona_esperado), None),
        (P.VALIDADOR_PERFIL, None),
        (val_jefe, jefe_esperado),
    ]
    for val, texto in esperados:
        valores = encontrados.get(val, [])
        if not valores:
            detalle["error"] = "validador_faltante"
            detalle["val_idvalidador"] = val
            return False, detalle
        if len(valores) > 1:
            detalle["error"] = "validador_duplicado"
            detalle["val_idvalidador"] = val
            detalle["motivo"] = (
                f"El validador {val} quedó {len(valores)} veces. Los reportes lo "
                f"leen con una subconsulta escalar: con más de una fila devuelven "
                f"ORA-01427 en vez del dato.")
            return False, detalle
        if texto is not None and valores[0].upper() != texto.upper():
            detalle["error"] = "validador_con_texto_distinto"
            detalle["val_idvalidador"] = val
            detalle["esperado"] = texto
            detalle["encontrado"] = valores[0]
            return False, detalle

    return True, detalle


def verificar_hecho(cursor, *, hog_codigo, per_idpersona, id_hecho):
    """Confirma el validador 100+`id_hecho` de la persona, y que sea único."""
    val = P.validador_de_hecho(id_hecho)
    cuantos = contar_validador(cursor, hog_codigo=hog_codigo,
                               per_idpersona=per_idpersona, val_idvalidador=val)
    detalle = {"hog_codigo": hog_codigo, "per_idpersona": per_idpersona,
               "id_hecho": id_hecho, "val_idvalidador": val, "filas": cuantos}
    if cuantos == 0:
        detalle["error"] = "hecho_no_escrito"
        detalle["motivo"] = ("GIC_INSERT_VALIDADOR_HECHO_AUX no dejó el validador. "
                             "Con un ID_HECHO fuera de 1..14 no inserta nada y "
                             "tampoco falla.")
        return False, detalle
    if cuantos > 1:
        detalle["error"] = "hecho_duplicado"
        return False, detalle
    return True, detalle


def verificar_encuestado(cursor, *, hog_codigo, per_idpersona):
    """Confirma `PER_ENCUESTADA='SI'` para esa persona en ese hogar."""
    valor = _scalar(
        cursor,
        """SELECT per_encuestada FROM gic_miembros_hogar
            WHERE hog_codigo = :h AND per_idpersona = :p""",
        {"h": hog_codigo, "p": per_idpersona},
    )
    texto = str(valor).strip().upper() if valor is not None else ""
    detalle = {"hog_codigo": hog_codigo, "per_idpersona": per_idpersona,
               "per_encuestada": texto}
    if texto != "SI":
        detalle["error"] = "no_marcado_encuestado"
        detalle["motivo"] = (
            f"PER_ENCUESTADA quedó en {texto!r}. El reporte deriva JEFE_HOGAR de "
            f"ese literal exacto ('SI'), así que con cualquier otra cosa nadie "
            f"figura como la persona entrevistada.")
        return False, detalle
    return True, detalle


def verificar_capitulo(cursor, *, hog_codigo, tem_idtema):
    """Confirma la fila (HOG_CODIGO, TEM_IDTEMA) en GIC_N_CAPITULOS_TER."""
    existe = _scalar(
        cursor,
        """SELECT COUNT(*) FROM gic_n_capitulos_ter
            WHERE hog_codigo = :h AND tem_idtema = :t""",
        {"h": hog_codigo, "t": tem_idtema},
    )
    return bool(existe), {"hog_codigo": hog_codigo, "tem_idtema": tem_idtema,
                          "encontrado": bool(existe)}


def contar_capitulos(cursor, *, hog_codigo) -> int:
    """Cuántos capítulos terminados tiene el hogar. El cierre exige más de 3."""
    return _scalar(
        cursor, "SELECT COUNT(*) FROM gic_n_capitulos_ter WHERE hog_codigo = :h",
        {"h": hog_codigo},
    ) or 0


#: Un hogar cerrado NO se queda en 'CERRADA': una tarea nocturna lo pasa a
#: `MIGRADOAHISTORICO`, y ese es su estado normal el resto de su vida.
#:
#: Medido en producción el 3-ago-2026 sobre `GIC_HOGAR` (1,1 M de filas):
#:
#:     MIGRADOAHISTORICO  1.039.334      ERROR                8.979
#:     APLAZADA              38.085      ACTIVA               1.451
#:     ANULADA               16.493      CERRADA_APP_MOVIL      106
#:     MANUAL                    50      CERRADA                 62  ←
#:     PRUEBA                     4      MIGRADOHISTORICO         1
#:
#: **62.** Sesenta y dos hogares en 'CERRADA' en toda la base. Exigir ese literal
#: para dar un cierre por bueno funciona en los minutos siguientes a cerrarlo y
#: falla para siempre después. Por eso se acepta también el estado archivado:
#: `GIC_VALIDAR_PERSONA_ENCUESTAD1` hace lo mismo — muestra MIGRADOAHISTORICO
#: como 'CERRADA' de cara al usuario.
ESTADOS_CERRADO = ("CERRADA", "MIGRADOAHISTORICO")

#: El `ESTADO` que deja cada `TIPO_APLAZAMIENTO` (el CASE del cuerpo,
#: `src_GIC_N_CARACTERIZACION.sql:1575-1581`). Sin esto, verificar un hogar anulado
#: contra el literal 'CERRADA' lo daba por fallido siempre.
ESTADO_POR_TIPO_CIERRE = {
    P.CIERRE_ANULADA: "ANULADA",
    P.CIERRE_NO_RESPONDE: "HOGAR_NO_RESPONDE",
    P.CIERRE_APLAZADA: "APLAZADA",
    P.CIERRE_CERRADA: "CERRADA",
    P.CIERRE_REABRIR: "ACTIVA",
}

#: Los dos códigos que NO mueven las respuestas a la tabla definitiva
#: (`IF TIPO_APLAZAMIENTO NOT IN ('5','3')`, `:1593`). Aplazar y reabrir dejan la
#: encuesta viva a propósito: exigirles filas en `_C` sería exigir lo contrario.
TIPOS_CIERRE_QUE_NO_ARCHIVAN = {P.CIERRE_APLAZADA, P.CIERRE_REABRIR}


def verificar_cierre(cursor, *, hog_codigo, tipo=None):
    """
    Confirma que la encuesta quedó CERRADA **y que las respuestas se movieron**.

    `tipo` es el `TIPO_APLAZAMIENTO` con el que se invocó. Se acepta porque el
    escritor lo pasa —y sin el parámetro esta llamada moría con `TypeError` en la
    ruta confirmada, la única donde se verifica; los tests, todos en DRY-RUN, no
    llegaban nunca hasta acá—. Hoy solo cambia el estado que se espera encontrar:
    anular deja 'ANULADA', no 'CERRADA', y también archiva las respuestas.

    Las dos cosas, no una. `SP_ACTUALIZAR_ESTADO_ENCUESTA` con '4' solo hace su
    trabajo si el hogar tiene más de 3 capítulos terminados; si no, cae en un
    `ELSE NULL` literal y **termina sin error**. Mirar solo el retorno del
    procedure daría por cerrada una encuesta que sigue abierta y cuyas respuestas
    nunca llegaron a la tabla que leen los reportes.

    Por eso se comprueba lo que de verdad importa: que `GIC_N_RESPUESTASENCUESTA_C`
    —la definitiva— tenga las filas, y que la de trabajo haya quedado vacía, que es
    exactamente lo que el procedure hace cuando funciona.
    """
    estado = _scalar(
        cursor, "SELECT estado FROM gic_hogar WHERE hog_codigo = :h", {"h": hog_codigo})
    definitivas = _scalar(
        cursor,
        "SELECT COUNT(*) FROM gic_n_respuestasencuesta_c WHERE hog_codigo = :h",
        {"h": hog_codigo}) or 0
    en_trabajo = _scalar(
        cursor,
        "SELECT COUNT(*) FROM gic_n_respuestasencuesta WHERE hog_codigo = :h",
        {"h": hog_codigo}) or 0
    capitulos = contar_capitulos(cursor, hog_codigo=hog_codigo)

    tipo = str(tipo or P.CIERRE_CERRADA)
    esperado = ESTADO_POR_TIPO_CIERRE.get(tipo, "CERRADA")
    archiva = tipo not in TIPOS_CIERRE_QUE_NO_ARCHIVAN

    detalle = {
        "hog_codigo": hog_codigo, "estado": estado, "estado_esperado": esperado,
        "respuestas_definitivas": definitivas,
        "respuestas_en_trabajo": en_trabajo,
        "capitulos_terminados": capitulos,
    }

    # Cerrar admite dos estados válidos: el que deja el procedure y el que deja
    # la migración nocturna. Los demás códigos (anular, aplazar…) exigen el suyo.
    aceptados = (ESTADOS_CERRADO if esperado == "CERRADA" else (esperado,))
    if estado not in aceptados:
        detalle["error"] = "no_cerro"
        detalle["motivo"] = (
            f"El hogar quedó en {estado!r} y se esperaba {esperado!r}. Si tiene "
            f"{capitulos} capítulos y el procedure exige más de 3, cayó en el "
            f"ELSE NULL y terminó sin error.")
        return False, detalle

    if archiva and definitivas == 0:
        # Cerrado pero sin respuestas en la definitiva: para los reportes, ese
        # hogar no existe. Es el escenario que deja `CERRAR_ENCUESTA`.
        detalle["error"] = "cerrado_sin_respuestas"
        detalle["motivo"] = (f"Quedó {esperado} pero GIC_N_RESPUESTASENCUESTA_C está "
                             "vacía: los reportes no verán nada de este hogar.")
        return False, detalle

    return True, detalle
