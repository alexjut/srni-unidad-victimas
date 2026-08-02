"""
Verificación POR CONSULTA del resultado de cada paso (solo SELECT).

Racional (ver ruta_escritura.md §4): los procedures hacen COMMIT interno y tragan
sus excepciones con `EXCEPTION WHEN OTHERS`. Por eso "el procedure no lanzó" NO
prueba que la fila quedó escrita. Tras CADA llamada, el escritor confirma el
resultado esperado con un SELECT; solo entonces marca el paso VERIFICADO y avanza.

Todo aquí es SOLO LECTURA. Devuelve (ok, detalle) donde `detalle` es auditable y
sin PII (conteos, códigos e ids, nunca nombres ni documentos).
"""


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
