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


def verificar_hogar(cursor, *, hog_codigo=None, id_usuario=None, marcador=None):
    """
    Confirma que el hogar existe en Oracle. Maneja la inconsistencia de MARCADOR:
    si MARCADOR != '1' es el HOG_CODIGO (existente o recién creado y devuelto);
    si MARCADOR == '1' hubo alta nueva y el código NO viene en el OUT → se resuelve
    consultando el hogar ACTIVA más reciente del ID_USUARIO.
    """
    codigo = None
    if marcador and marcador != "1":
        codigo = marcador
    elif hog_codigo:
        codigo = hog_codigo

    if codigo:
        existe = _scalar(
            cursor,
            "SELECT COUNT(*) FROM gic_hogar WHERE hog_codigo = :c AND estado = 'ACTIVA'",
            {"c": codigo},
        )
        return bool(existe), {"hog_codigo": codigo, "encontrado": bool(existe)}

    if id_usuario is not None:
        codigo = _scalar(
            cursor,
            """SELECT hog_codigo FROM gic_hogar
                WHERE usu_idusuario = :u AND estado = 'ACTIVA'
                ORDER BY usu_fechacreacion DESC FETCH FIRST 1 ROWS ONLY""",
            {"u": id_usuario},
        )
        return bool(codigo), {"hog_codigo": codigo, "resuelto_por": "id_usuario"}

    return False, {"error": "sin hog_codigo ni id_usuario para verificar"}


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
