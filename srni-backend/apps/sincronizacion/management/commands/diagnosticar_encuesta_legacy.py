"""
Management command: diagnosticar_encuesta_legacy

Responde una sola pregunta, la que llega del territorio: **"se caracterizó a esta
persona y la encuesta no aparece — ¿dónde está?"**

──────────────────────────────────────────────────────────────────────────────
POR QUÉ HACE FALTA UN COMANDO PARA ESTO
──────────────────────────────────────────────────────────────────────────────
Porque en el legacy "no aparece" tiene **al menos seis causas distintas**, todas
se ven igual desde la consulta, y en cuatro de ellas **el dato NO se perdió**:
está escrito y solo le falta un paso para ser visible. Distinguirlas mirando ocho
tablas a mano, caso por caso, no escala — y la diferencia entre una y otra es si
hay que volver a la vereda o no.

Las causas, con lo que las delata:

1. **La encuesta nunca se cerró.** `SP_ACTUALIZAR_ESTADO_ENCUESTA(...,'4')` solo
   archiva si el hogar tiene **más de 3 capítulos** terminados; con 3 o menos cae
   en un `ELSE NULL` literal y **termina sin error**. El aplicativo mostró
   "guardado". El hogar queda ACTIVA y las respuestas se quedan en
   `GIC_N_RESPUESTASENCUESTA` (la tabla de trabajo), sin pasar nunca a
   `GIC_N_RESPUESTASENCUESTA_C`, que es **la única que leen los reportes**.
   ⇒ *El dato está. Es recuperable.*

2. **El hogar se fundió con otro.** `GIC_INSERT_HOGAR1` solo crea si el usuario
   **no tiene ningún hogar en ACTIVA**; si lo tiene, no crea nada y devuelve el
   código del hogar viejo. Todo lo que el encuestador capture después entra en la
   caracterización anterior, que puede ser de otra familia.
   ⇒ *El dato está, colgado del hogar equivocado.*

3. **La persona existe pero es invisible para la búsqueda por documento.** Los
   reportes y la consulta cruzan por `R_NUMERODOC` —la columna espejo—, no por
   `PER_NUMERODOC`. Una fila con el espejo vacío existe y no la encuentra nadie.
   ⇒ *El dato está, y la consulta miente.*

4. **Se cerró pero sin archivar.** `CERRAR_ENCUESTA` (que no es el mismo
   procedure) hace `UPDATE ESTADO='CERRADA'` y no mueve nada: hogar marcado como
   terminado con cero respuestas en la definitiva. El peor estado posible.

5. **Nunca llegó a la base.** La aplicación móvil vieja no escribe en la base:
   deja un JSON en un FTP que recogen **cuatro jobs encadenados de noche**
   (20:15 → 20:45 → 22:30 → 23:30). Si cualquiera falla, no hay error para nadie
   y el encuestador ya vio "enviado".
   ⇒ *Este es el único caso en que el dato puede haberse perdido de verdad.*

6. **Se migró al histórico.** `GIC_HOGAR_HISTORICO` existe y hay un job a la
   01:30; una consulta que solo mire `GIC_HOGAR` no lo encuentra.

7. **El encuestador no existe en `GIC_USUARIO`.** `SP_REPORTE_MIEMBROSXCODIGO`
   arma "mis encuestas" con un **`INNER JOIN GIC_USUARIO US ON US.USU_USUARIO =
   T.USU_USUARIOCREACION`** (`src_GIC_N_CARACTERIZACION.sql:2451`). Si el usuario
   que capturó no tiene fila en esa tabla, el hogar **desaparece del listado**
   aunque esté cerrado, archivado y perfecto.
   Y no es un caso raro: medido sobre producción, **1.077.712 hogares (97,7 %)**
   tienen un `USU_USUARIOCREACION` que no existe en `GIC_USUARIO`, y el
   `USU_IDUSUARIO` no cruza en el 99,7 %.
   ⇒ *El dato está, y el listado que lo debería mostrar lo excluye por un JOIN.*

──────────────────────────────────────────────────────────────────────────────
SOLO LECTURA — SIN EXCEPCIONES
──────────────────────────────────────────────────────────────────────────────
Este comando **solo ejecuta SELECT**. No tiene `--confirmar` ni forma de
escribir, a propósito: es la herramienta que se usa cuando algo ya salió mal, y
en ese momento la tentación de "arreglarlo de una" es máxima. Reparar es otra
decisión, con respaldo previo y por la ruta de procedures.

No imprime PII. De los nombres y documentos informa si están **presentes o
vacíos** —que es justamente el diagnóstico del caso 3— nunca su contenido.

──────────────────────────────────────────────────────────────────────────────
USO
──────────────────────────────────────────────────────────────────────────────
    # Un caso reportado desde el territorio
    python manage.py diagnosticar_encuesta_legacy --documento 1070752540

    # Todo lo de un encuestador (p.ej. tras una novedad)
    python manage.py diagnosticar_encuesta_legacy --usuario JGUARINH --dias 90

    # Un hogar concreto
    python manage.py diagnosticar_encuesta_legacy --hogar 999999-2W832

    # BARRIDO: encontrar todas las encuestas invisibles antes de que las reporten
    python manage.py diagnosticar_encuesta_legacy --perdidas --dias 60
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.sincronizacion.oracle.conexion import abrir_conexion, describir_destino
from apps.sincronizacion.oracle import procedimientos as P

#: Estados en los que los reportes SÍ ven el hogar. `PKG_REPORTE_CARACTERIZACION`
#: filtra `ESTADO='CERRADA'` en 45 sitios; `MIGRADOAHISTORICO` se muestra como
#: CERRADA (`GIC_VALIDAR_PERSONA_ENCUESTAD1`).
ESTADOS_VISIBLES = ("CERRADA", "MIGRADOAHISTORICO")


def _filas(cur, sql, binds=None):
    cur.execute(sql, binds or {})
    return cur.fetchall()


def _uno(cur, sql, binds=None):
    filas = _filas(cur, sql, binds)
    return filas[0][0] if filas else None


def _presente(valor) -> bool:
    """En Oracle la cadena vacía ES NULL, así que basta con mirar si hay algo."""
    return valor is not None and str(valor).strip() != ""


def personas_por_documento(cur, documento):
    """Las filas de GIC_PERSONA con ese documento, por cualquiera de las dos vías.

    Se busca por las DOS columnas a propósito: si solo apareciera por
    `PER_NUMERODOC` y no por `R_NUMERODOC`, eso mismo **es** el diagnóstico
    (la persona existe y la consulta oficial no la encuentra).
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


def hogares_de_usuario(cur, usuario, dias):
    """Hogares creados por ese usuario del legacy en la ventana."""
    return [f[0] for f in _filas(cur, """
        SELECT hog_codigo FROM gic_hogar
         WHERE UPPER(usu_usuariocreacion) = UPPER(:u)
           AND usu_fechacreacion >= SYSDATE - :n
         ORDER BY usu_fechacreacion DESC
    """, {"u": usuario, "n": dias})]


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

    # ── personas del hogar y su visibilidad ──────────────────────────────────
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
    d["sin_identidad"] = sum(1 for f in personas
                             if not _presente(f[4]) and not _presente(f[2]))

    # ── respuestas: trabajo vs definitiva ────────────────────────────────────
    d["en_trabajo"] = _uno(cur, """
        SELECT COUNT(*) FROM gic_n_respuestasencuesta WHERE hog_codigo = :h
    """, {"h": hog_codigo}) or 0
    d["definitivas"] = _uno(cur, """
        SELECT COUNT(*) FROM gic_n_respuestasencuesta_c WHERE hog_codigo = :h
    """, {"h": hog_codigo}) or 0
    d["capitulos"] = _uno(cur, """
        SELECT COUNT(*) FROM gic_n_capitulos_ter WHERE hog_codigo = :h
    """, {"h": hog_codigo}) or 0

    # ── validadores y territorio ─────────────────────────────────────────────
    d["con_estado_ruv"] = _uno(cur, """
        SELECT COUNT(DISTINCT per_idpersona) FROM gic_n_validadoresxpersona
         WHERE hog_codigo = :h AND val_idvalidador = :v
    """, {"h": hog_codigo, "v": P.VALIDADOR_ESTADO_RUV}) or 0
    d["con_hechos"] = _uno(cur, """
        SELECT COUNT(DISTINCT per_idpersona) FROM gic_n_validadoresxpersona
         WHERE hog_codigo = :h AND val_idvalidador BETWEEN 101 AND 114
    """, {"h": hog_codigo}) or 0
    # ── ¿el encuestador existe en el catálogo de usuarios? ───────────────────
    # No es cosmético: "mis encuestas" se arma con un INNER JOIN contra
    # GIC_USUARIO. Sin fila ahí, el hogar no sale del listado aunque esté perfecto.
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

    Separada de la consulta a propósito: es la parte que decide si hay que volver
    a la vereda o no, y tiene que poder probarse sin depender de que Oracle esté
    disponible — que es justamente cuando uno necesita esta herramienta.
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
    else:
        d["veredicto"] = "REVISAR"
        d["explicacion"] = f"Estado {estado!r} sin patrón conocido."
    return d


def barrido(cur, dias):
    """Hogares con captura que los reportes NO ven. Los 'casos Mónica' sin reportar."""
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


class Command(BaseCommand):
    help = ("Diagnostica por qué una encuesta caracterizada no aparece en los "
            "reportes del legacy. SOLO LECTURA.")

    def add_arguments(self, parser):
        parser.add_argument("--documento", help="Documento de la persona reportada.")
        parser.add_argument("--usuario", help="Usuario del legacy (p.ej. JGUARINH).")
        parser.add_argument("--hogar", help="HOG_CODIGO concreto.")
        parser.add_argument("--perdidas", action="store_true",
                            help="Barrido: encuestas con datos que los reportes no ven.")
        parser.add_argument("--dias", type=int, default=60,
                            help="Ventana hacia atrás (default 60).")
        parser.add_argument("--destino", default="produccion",
                            choices=["produccion", "local"])

    def handle(self, *a, **o):
        modos = [o.get("documento"), o.get("usuario"), o.get("hogar"), o.get("perdidas")]
        if sum(1 for m in modos if m) != 1:
            raise CommandError(
                "Elegí exactamente un modo: --documento, --usuario, --hogar o --perdidas.")

        self.stdout.write(self.style.WARNING(
            f"SOLO LECTURA · {describir_destino(o['destino'])}"))
        con = abrir_conexion(o["destino"])
        try:
            cur = con.cursor()
            if o["perdidas"]:
                self._barrido(cur, o["dias"])
            else:
                self._caso(cur, o)
        finally:
            con.close()

    # ── modos ────────────────────────────────────────────────────────────────
    def _caso(self, cur, o):
        codigos = []
        if o.get("hogar"):
            codigos = [o["hogar"]]
        elif o.get("usuario"):
            codigos = hogares_de_usuario(cur, o["usuario"], o["dias"])
            self.stdout.write(f"\nUsuario {o['usuario']}: {len(codigos)} hogar(es) "
                              f"en los últimos {o['dias']} días.")
        else:
            personas = personas_por_documento(cur, o["documento"])
            self.stdout.write(f"\n=== La persona en GIC_PERSONA: {len(personas)} fila(s) ===")
            if not personas:
                self.stdout.write(self.style.ERROR(
                    "  Ninguna fila con ese documento, ni por PER_NUMERODOC ni por "
                    "R_NUMERODOC. La persona no está en la base."))
                return
            for (pid, por_per, por_r, pn, rn, est, fuente, idmi, fcre, usu) in personas:
                aviso = "" if por_r else "  ⚠️ INVISIBLE para la búsqueda por documento"
                self.stdout.write(
                    f"  per_idpersona={pid} estado={est} fuente={fuente} "
                    f"idmodelint={idmi} creada={fcre} por={usu}")
                self.stdout.write(
                    f"    identidad: PER_* {'presente' if _presente(pn) else 'VACÍA'} · "
                    f"espejo R_* {'presente' if _presente(rn) else 'VACÍA'}"
                    f"{self.style.ERROR(aviso) if aviso else ''}")
                for h in hogares_de_persona(cur, pid):
                    if h not in codigos:
                        codigos.append(h)

        if not codigos:
            self.stdout.write(self.style.ERROR(
                "\nLa persona existe pero NO está en ningún hogar "
                "(GIC_MIEMBROS_HOGAR vacío): la caracterización no la vinculó."))
            return

        for codigo in codigos:
            self._imprimir(diagnosticar(cur, codigo))

    def _imprimir(self, d):
        self.stdout.write(f"\n=== Hogar {d['hog_codigo']} ({d['donde']}) ===")
        if d.get("estado") is not None:
            self.stdout.write(
                f"  estado={d['estado']} creado={d.get('creado_en')} "
                f"por={d.get('creado_por')} (id_usuario={d.get('id_usuario')}, "
                f"perfil={d.get('perfil')})")
            self.stdout.write(
                f"  miembros={d['miembros']} encuestados={d['encuestados']} · "
                f"respuestas: trabajo={d['en_trabajo']} definitiva={d['definitivas']} · "
                f"capítulos={d['capitulos']} · territorio={d['territorio']}")

        estilo = {
            "COMPLETO": self.style.SUCCESS,
            "NO_LLEGO": self.style.ERROR,
            "CERRADO_SIN_ARCHIVAR": self.style.ERROR,
            "SIN_RESPUESTAS": self.style.ERROR,
        }.get(d["veredicto"], self.style.WARNING)
        self.stdout.write(estilo(f"  ⇒ {d['veredicto']}"))
        self.stdout.write(f"    {d['explicacion']}")
        for c in d.get("carencias", []):
            self.stdout.write(f"    · {c}")

    def _barrido(self, cur, dias):
        filas = barrido(cur, dias)
        self.stdout.write(
            f"\n=== Encuestas con datos que los reportes NO ven "
            f"(últimos {dias} días) ===")
        if not filas:
            self.stdout.write(self.style.SUCCESS("  Ninguna. "))
            return
        self.stdout.write(
            f"  {len(filas)} hogar(es). Cada uno tiene respuestas capturadas en la "
            f"tabla de trabajo y un estado que los reportes filtran.\n")
        self.stdout.write("  hogar                estado        usuario      fecha       resp  cap")
        for hog, est, usu, fecha, resp, cap in filas:
            marca = "  ← el cierre no puede funcionar" if cap < P.CAPITULOS_MINIMOS_PARA_CERRAR else ""
            self.stdout.write(
                f"  {str(hog):<20} {str(est):<13} {str(usu or ''):<12} {fecha}  "
                f"{resp:>4}  {cap:>3}{marca}")
        self.stdout.write(self.style.WARNING(
            f"\n  Son {len(filas)} caracterizaciones hechas cuyo dato existe y "
            f"nadie ve. Cada una es una visita a campo que puede no repetirse."))
