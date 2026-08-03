"""
Por qué una encuesta caracterizada no aparece: las consultas y el veredicto.

Vive acá y no dentro de un management command porque lo usan tres sitios: el
comando de diagnóstico, el que importa las caracterizaciones del legacy y la API
que le muestra a cada encuestador lo que hizo. Todo lo de este módulo es **solo
lectura** sobre Oracle.

`dictaminar` es **pura** —no toca la base— a propósito: es la parte que decide si
hay que volver a la vereda o no, y tiene que poder probarse sin depender de que
Oracle esté disponible, que es justo cuando uno la necesita.

Las seis causas de "no aparece" están explicadas en el comando
`diagnosticar_encuesta_legacy`; el caso real que las destapó, en
`docs/oracle-legacy/caso_pandi_encuesta_no_aparece.md`.
"""
from . import procedimientos as P

#: Estados en los que los reportes SÍ ven el hogar.
#:
#: `MIGRADOAHISTORICO` no es una excepción rara: es **el estado normal**. Medido
#: en producción el 3-ago-2026 sobre 1,1 M de hogares, `CERRADA` son **62** y
#: `MIGRADOAHISTORICO` 1.039.334, porque una tarea nocturna los mueve. Tratar
#: solo 'CERRADA' como visible marcaría como problema a un millón de hogares
#: sanos. `GIC_VALIDAR_PERSONA_ENCUESTAD1` hace lo mismo: lo muestra como
#: 'CERRADA' de cara al usuario.
ESTADOS_VISIBLES = ("CERRADA", "MIGRADOAHISTORICO")

#: Estados que el código del legacy declara pero la base contradice, y al revés.
#: Se listan para que un valor inesperado se lea como dato conocido y no como
#: error del lector. `HOGAR_NO_RESPONDE` está en el PL/SQL y tiene cero filas;
#: `ERROR` (8.979), `CERRADA_APP_MOVIL` (106) y `PRUEBA` (4) no están declarados
#: en ningún sitio. `MIGRADOHISTORICO` (1) es `MIGRADOAHISTORICO` con una letra
#: menos: sin CHECK que lo impida, el typo entró y ese hogar quedó fuera de todo
#: conteo para siempre.
ESTADOS_NO_DECLARADOS = ("ERROR", "CERRADA_APP_MOVIL", "PRUEBA", "MIGRADOHISTORICO")


def _filas(cur, sql, binds=None):
    cur.execute(sql, binds or {})
    return cur.fetchall()


def _uno(cur, sql, binds=None):
    filas = _filas(cur, sql, binds)
    return filas[0][0] if filas else None


def _presente(valor) -> bool:
    """En Oracle la cadena vacía ES NULL, así que basta con mirar si hay algo."""
    return valor is not None and str(valor).strip() != ""


# ── búsquedas ────────────────────────────────────────────────────────────────

def personas_por_documento(cur, documento):
    """Las filas de GIC_PERSONA con ese documento, por cualquiera de las dos vías.

    Se busca por las DOS columnas a propósito: si solo apareciera por
    `PER_NUMERODOC` y no por `R_NUMERODOC`, eso mismo **es** el diagnóstico (la
    persona existe y la consulta oficial no la encuentra).
    """
    return _filas(cur, """
        SELECT p.per_idpersona,
               CASE WHEN p.per_numerodoc = :d THEN 1 ELSE 0 END,
               CASE WHEN p.r_numerodoc   = :d THEN 1 ELSE 0 END,
               p.per_primernombre, p.r_primernombre, p.per_estado, p.per_fuente,
               p.per_idmodeloint,
               TO_CHAR(p.usu_fechacreacion,'YYYY-MM-DD HH24:MI'),
               p.usu_usuariocreacion
          FROM gic_persona p
         WHERE p.per_numerodoc = :d OR p.r_numerodoc = :d
         ORDER BY p.per_idpersona
    """, {"d": str(documento).strip()})


def hogares_de_persona(cur, per_idpersona):
    return [f[0] for f in _filas(cur, """
        SELECT hog_codigo FROM gic_miembros_hogar WHERE per_idpersona = :p
    """, {"p": per_idpersona})]


def hogares_de_usuario(cur, usuario, dias=None):
    """
    Los hogares que capturó ese encuestador, por la **cadena** del creador.

    ⚠️ Deliberadamente NO se pasa por `GIC_USUARIO`. Medido en producción:
    **1.077.712 hogares (97,7 %)** tienen un `USU_USUARIOCREACION` que no existe
    en esa tabla — `JGUARINH`, el del caso de Pandi, es uno de ellos, con 18
    hogares y sin fila de usuario. Cruzar por el catálogo perdería el 97 % del
    trabajo hecho, que es exactamente lo contrario de lo que se busca acá.

    `dias=None` trae todo su histórico: para "mostrarle a alguien lo que hizo",
    recortar por fecha es una decisión de la vista, no del acceso al dato.
    """
    sql = """SELECT hog_codigo FROM gic_hogar
              WHERE UPPER(usu_usuariocreacion) = UPPER(:u)"""
    binds = {"u": usuario}
    if dias:
        sql += " AND usu_fechacreacion >= SYSDATE - :n"
        binds["n"] = dias
    return [f[0] for f in _filas(cur, sql + " ORDER BY usu_fechacreacion DESC", binds)]


def barrido(cur, dias):
    """Hogares con captura que los reportes NO ven. Los casos sin reportar."""
    return _filas(cur, """
        SELECT h.hog_codigo, h.estado, h.usu_usuariocreacion,
               TO_CHAR(h.usu_fechacreacion,'YYYY-MM-DD'),
               (SELECT COUNT(*) FROM gic_n_respuestasencuesta r
                 WHERE r.hog_codigo = h.hog_codigo),
               (SELECT COUNT(*) FROM gic_n_capitulos_ter c
                 WHERE c.hog_codigo = h.hog_codigo)
          FROM gic_hogar h
         WHERE h.usu_fechacreacion >= SYSDATE - :n
           AND h.estado NOT IN ('CERRADA','MIGRADOAHISTORICO','ANULADA')
           AND EXISTS (SELECT 1 FROM gic_n_respuestasencuesta r
                        WHERE r.hog_codigo = h.hog_codigo)
         ORDER BY h.usu_fechacreacion
    """, {"n": dias})


# ── el diagnóstico de un hogar ───────────────────────────────────────────────

def diagnosticar(cur, hog_codigo) -> dict:
    """Los diez pasos de un hogar, y dónde está su dato. Solo SELECT."""
    d = {"hog_codigo": hog_codigo, "carencias": []}

    cab = _filas(cur, """
        SELECT estado, usu_usuariocreacion, usu_idusuario, id_perfil_usuario,
               TO_CHAR(usu_fechacreacion,'YYYY-MM-DD HH24:MI'),
               TO_CHAR(fecha_estado,'YYYY-MM-DD HH24:MI'), usu_usuarioestado
          FROM gic_hogar WHERE hog_codigo = :h
    """, {"h": hog_codigo})

    if cab:
        (d["estado"], d["creado_por"], d["id_usuario"], d["perfil"],
         d["creado_en"], d["fecha_estado"], d["cerrado_por"]) = cab[0]
        d["donde"] = "GIC_HOGAR"
    else:
        en_hist = _uno(cur, """
            SELECT COUNT(*) FROM gic_hogar_historico WHERE hog_codigo = :h
        """, {"h": hog_codigo}) or 0
        d["donde"] = "GIC_HOGAR_HISTORICO" if en_hist else "NO EXISTE"
        d["estado"] = None
        if not en_hist:
            d["veredicto"] = "NO_LLEGO"
            d["explicacion"] = (
                "El hogar no está en GIC_HOGAR ni en el histórico. Si la captura "
                "fue con la aplicación móvil vieja, el JSON viaja por FTP y lo "
                "recogen cuatro jobs de noche; si alguno falló, la encuesta no "
                "llegó nunca y nadie recibió un error. Es el único caso en que el "
                "dato puede haberse perdido de verdad.")
            return d

    personas = _filas(cur, """
        SELECT mh.per_idpersona, mh.per_encuestada,
               p.r_numerodoc, p.r_primernombre, p.per_numerodoc, p.per_primernombre
          FROM gic_miembros_hogar mh
          LEFT JOIN gic_persona p ON p.per_idpersona = mh.per_idpersona
         WHERE mh.hog_codigo = :h
    """, {"h": hog_codigo})
    d["miembros"] = len(personas)
    d["encuestados"] = sum(1 for f in personas
                           if str(f[1] or "").strip().upper() == "SI")
    d["sin_espejo"] = sum(1 for f in personas if not _presente(f[2]))

    d["en_trabajo"] = _uno(cur, """
        SELECT COUNT(*) FROM gic_n_respuestasencuesta WHERE hog_codigo = :h
    """, {"h": hog_codigo}) or 0
    d["definitivas"] = _uno(cur, """
        SELECT COUNT(*) FROM gic_n_respuestasencuesta_c WHERE hog_codigo = :h
    """, {"h": hog_codigo}) or 0
    d["capitulos"] = _uno(cur, """
        SELECT COUNT(*) FROM gic_n_capitulos_ter WHERE hog_codigo = :h
    """, {"h": hog_codigo}) or 0

    d["con_estado_ruv"] = _uno(cur, """
        SELECT COUNT(DISTINCT per_idpersona) FROM gic_n_validadoresxpersona
         WHERE hog_codigo = :h AND val_idvalidador = :v
    """, {"h": hog_codigo, "v": P.VALIDADOR_ESTADO_RUV}) or 0
    d["con_hechos"] = _uno(cur, """
        SELECT COUNT(DISTINCT per_idpersona) FROM gic_n_validadoresxpersona
         WHERE hog_codigo = :h AND val_idvalidador BETWEEN 101 AND 114
    """, {"h": hog_codigo}) or 0

    # ¿el encuestador existe en el catálogo? "Mis encuestas" del legacy se arma
    # con un INNER JOIN contra GIC_USUARIO: sin fila ahí, el hogar no sale del
    # listado aunque esté perfecto.
    d["usuario_en_catalogo"] = bool(_uno(cur, """
        SELECT COUNT(*) FROM gic_usuario WHERE UPPER(usu_usuario) = UPPER(:u)
    """, {"u": d.get("creado_por") or ""}) or 0)
    d["id_usuario_en_catalogo"] = bool(_uno(cur, """
        SELECT COUNT(*) FROM gic_usuario WHERE usu_idusuario = :i
    """, {"i": d.get("id_usuario")}) or 0) if d.get("id_usuario") is not None else False

    terr = _filas(cur, """
        SELECT iddt, iddeptoaten, idpuntoaten, idmunaten
          FROM gic_n_relacion_dt_punto WHERE hogarcodigo = :h
    """, {"h": hog_codigo})
    d["territorio"] = "completo" if (terr and all(_presente(x) for x in terr[0])) \
        else ("incompleto" if terr else "sin fila")

    return dictaminar(d)


def dictaminar(d: dict) -> dict:
    """
    El veredicto a partir de lo medido. **Función pura**, sin base de datos.
    """
    d.setdefault("carencias", [])
    # `.get` con default en vez de indexar: así un dict parcial —el de un test, o
    # el de un hogar del que una consulta no devolvió nada— produce un veredicto
    # en vez de un KeyError. Esta herramienta se usa cuando algo ya salió mal; que
    # ella misma reviente es el peor momento posible.
    miembros = d.get("miembros", 0)
    d.update(miembros=miembros,
             encuestados=d.get("encuestados", 0),
             sin_espejo=d.get("sin_espejo", 0),
             en_trabajo=d.get("en_trabajo", 0),
             definitivas=d.get("definitivas", 0),
             capitulos=d.get("capitulos", 0),
             con_estado_ruv=d.get("con_estado_ruv", 0),
             con_hechos=d.get("con_hechos", 0),
             territorio=d.get("territorio", "sin fila"),
             usuario_en_catalogo=d.get("usuario_en_catalogo", True),
             id_usuario_en_catalogo=d.get("id_usuario_en_catalogo", True))

    # ── carencias (ortogonales al veredicto principal) ───────────────────────
    if miembros and not d["con_estado_ruv"]:
        d["carencias"].append(
            "sin validador de estado en el RUV → la columna ESTADO_RUV sale vacía")
    if miembros and not d["con_hechos"]:
        d["carencias"].append(
            "sin validadores de hechos → HECHO_VICTIMIZANTE_1..14 salen vacías")
    if d["territorio"] != "completo":
        d["carencias"].append(
            f"territorio {d['territorio']} → no sale en reportes por depto/municipio")
    if d["sin_espejo"]:
        d["carencias"].append(
            f"{d['sin_espejo']} de {miembros} personas con R_NUMERODOC vacío → "
            "existen, pero la búsqueda por documento no las encuentra")
    if miembros and not d["encuestados"]:
        d["carencias"].append(
            "nadie con PER_ENCUESTADA='SI' → JEFE_HOGAR sale 'NO' para todo el hogar")
    if not d["usuario_en_catalogo"]:
        d["carencias"].append(
            f"el usuario {d.get('creado_por')!r} NO existe en GIC_USUARIO → "
            "'mis encuestas' lo arma con un INNER JOIN contra esa tabla, así que "
            "este hogar no sale del listado aunque esté cerrado y archivado")
    if not d["id_usuario_en_catalogo"]:
        d["carencias"].append(
            f"el USU_IDUSUARIO {d.get('id_usuario')} no cruza con GIC_USUARIO → "
            "el encuestador sale NULL en los reportes de productividad")

    # ── veredicto principal ──────────────────────────────────────────────────
    estado = (d.get("estado") or "").strip().upper()

    # ── estados TERMINALES: una decisión, no un problema ─────────────────────
    # Van primero. Sin esta rama, un hogar anulado con respuestas archivadas caía
    # en ARCHIVADO_FUERA_DE_REPORTES y el listado le decía a su encuestador que
    # "está completo y solo le sobra un literal, no hay que repetirlo" — sobre un
    # hogar que él mismo anuló. Medido al importar los 1.148 encuestadores: eran
    # **3.284 hogares** recibiendo esa afirmación, falsa y creíble a la vez.
    if estado == "ANULADA":
        d["veredicto"] = "ANULADA"
        d["explicacion"] = (
            "Anulada a propósito. Los microdatos la excluyen por diseño y eso está "
            "bien: no es trabajo perdido ni hay nada que reparar.")
        return d
    if estado == "ERROR":
        d["veredicto"] = "MARCADA_ERROR"
        d["explicacion"] = (
            "El legacy la marcó como ERROR (el TIPO_APLAZAMIENTO '6'). Son 8.979 "
            "en total y **ninguna** tiene respuestas archivadas, así que acá no "
            "hay dato que rescatar — conviene saberlo antes de prometerlo.")
        return d

    if d.get("donde") == "GIC_HOGAR_HISTORICO":
        d["veredicto"] = "EN_HISTORICO"
        d["explicacion"] = ("El hogar se migró a GIC_HOGAR_HISTORICO. Una consulta "
                            "que solo mire GIC_HOGAR no lo encuentra, pero el dato está.")
    elif estado not in ESTADOS_VISIBLES and d["en_trabajo"]:
        if d["capitulos"] < P.CAPITULOS_MINIMOS_PARA_CERRAR:
            d["veredicto"] = "NO_CERRO_POR_CAPITULOS"
            d["explicacion"] = (
                f"El hogar está en {estado!r} con {d['en_trabajo']} respuestas en la "
                f"tabla de trabajo y solo {d['capitulos']} capítulos terminados. "
                f"SP_ACTUALIZAR_ESTADO_ENCUESTA exige más de "
                f"{P.CAPITULOS_MINIMOS_PARA_CERRAR - 1}: por debajo de eso cae en un "
                f"ELSE NULL y devuelve éxito SIN cerrar. Por eso el aplicativo dijo "
                f"'guardado' y el reporte no muestra nada. EL DATO ESTÁ.")
        else:
            d["veredicto"] = "ABIERTO_CON_DATOS"
            d["explicacion"] = (
                f"El hogar está en {estado!r} con {d['en_trabajo']} respuestas en la "
                f"tabla de trabajo y {d['capitulos']} capítulos: tiene capítulos de "
                f"sobra para cerrar, pero el cierre no se ejecutó. Los reportes solo "
                f"leen la tabla definitiva. EL DATO ESTÁ.")
    elif estado in ESTADOS_VISIBLES and not d["definitivas"]:
        d["veredicto"] = "CERRADO_SIN_ARCHIVAR"
        d["explicacion"] = (
            "Figura como cerrado pero GIC_N_RESPUESTASENCUESTA_C está vacía: para "
            "los reportes este hogar no existe. Es lo que deja CERRAR_ENCUESTA, que "
            "marca el estado sin mover las respuestas.")
    elif not d["en_trabajo"] and not d["definitivas"]:
        d["veredicto"] = "SIN_RESPUESTAS"
        d["explicacion"] = ("El hogar existe pero no tiene respuestas en ninguna de "
                            "las dos tablas. Se abrió y no se capturó, o la captura "
                            "no llegó.")
    elif estado in ESTADOS_VISIBLES and d["definitivas"]:
        d["veredicto"] = "COMPLETO"
        d["explicacion"] = (f"Cerrado con {d['definitivas']} respuestas en la tabla "
                            f"definitiva: los reportes deberían verlo.")
    elif d["definitivas"]:
        # Terminado y archivado, pero con un estado que los reportes no filtran.
        # No es "revisar": es una caracterización completa a la que solo le sobra
        # una cadena. Medido el 3-ago: **111 hogares** están así —106 en
        # `CERRADA_APP_MOVIL`, 4 en `PRUEBA`, 1 en `MIGRADOHISTORICO`— y los 111
        # tienen sus respuestas en la tabla definitiva. Es el caso más barato de
        # arreglar de toda la lista y el que más trabajo devuelve: no hay que
        # volver a campo, hay que reconocer un literal.
        d["veredicto"] = "ARCHIVADO_FUERA_DE_REPORTES"
        d["explicacion"] = (
            f"Está terminado y archivado —{d['definitivas']} respuestas en la tabla "
            f"definitiva— pero su estado es {estado!r}, que los reportes no filtran: "
            f"`PKG_REPORTE_CARACTERIZACION` busca 'CERRADA' en 45 sitios. El trabajo "
            f"está completo y no lo cuenta nadie. NO hay que repetirlo.")
    else:
        d["veredicto"] = "REVISAR"
        d["explicacion"] = f"Estado {estado!r} sin patrón conocido."
    return d
