"""
Crosswalk SICAV → catálogos Oracle (Etapa A).

Valores REALES leídos de prod (RNIENTREVISTA, solo lectura, 2026-07-15) y cruzados
por nombre con los códigos SICAV. El volcado completo (incl. los 1370 registros de
GIC_N_DT_PUNTOS_ATENCION) está en `catalogos_oracle.json` (versionado, sin PII).

Regla: si un código SICAV no tiene entrada aquí, el resolver LANZA MapeoDesconocido
(modo estricto/confirmado). NUNCA se inventa un valor por defecto.
Claves = valor SICAV (código del modelo Django). Valores = id Oracle real.
"""
import functools
import json
import pathlib
import re
import unicodedata

# ── Catálogo 2 — tipo de caracterización (GIC_TIPOCARACTERIZACION) ───────────
# Oracle distingue solo 1=INDIVIDUO / 2=HOGAR (NO por instrumento). GIC_INSERT_HOGAR1
# crea una caracterización de HOGAR ⇒ SICAV usa 2. ⚠️ CONFIRMAR si algún flujo SICAV
# debe registrarse como INDIVIDUO (1).
TIPO_CARACTERIZACION_HOGAR = 2
TIPO_CARACTERIZACION_INDIVIDUO = 1

# ── Catálogo 3 — tipo de documento (parametricas.TipoDocumento.codigo → GIC_TIPODOC.TIP_IDTIPO) ──
# Cruce por nombre con las 8 filas del seed SICAV (cargar_tipos_documento.py).
TIPO_DOCUMENTO = {
    "CC": 1,    # Cédula de Ciudadanía
    "TI": 2,    # Tarjeta de Identidad
    "CE": 3,    # Cédula de Extranjería
    "RC": 4,    # Registro Civil de Nacimiento
    "PA": 7,    # Pasaporte
    "NIT": 9,   # Número de Identificación Tributaria
    # ⚠️ SIN equivalente claro en GIC_TIPODOC (14 filas) — decisión de negocio:
    #   "PE"  (Permiso Especial de Permanencia / PEP) → ¿Otro=13? ¿alta en catálogo?
    #   "NES" (Número de Entrada al Sistema, sin doc)  → ¿Indocumentado=14? ¿Ninguno=12?
    # Se dejan SIN mapear a propósito: el resolver lanzará MapeoDesconocido.
}

# ── Catálogo 4a — parentesco (MiembroHogar.parentesco → GIC_PARENTESCOGENEALOGICO.PRST_ID) ──
# Cruce por nombre con las 12 filas Oracle; las 8 choices SICAV mapean limpio.
PARENTESCO = {
    "CONYUGE": 4,        # Esposo(a)/Compañero(a)
    "HIJO_A": 3,         # Hijo(a)/Hijastro(a)
    "YERNO_NUERA": 8,    # Yerno/Nuera
    "NIETO_A": 5,        # Nieto(a)
    "PADRE_MADRE": 2,    # Padre o Madre
    "HERMANO_A": 7,      # Hermanos o Cuñados
    "OTRO_PARIENTE": 9,  # Otros Parientes
    "NO_PARIENTE": 10,   # No pariente
    # (Oracle 1=Jefe de hogar, 6=Suegros, 11=No sabe, 12=No responde no tienen
    #  choice SICAV directo; el jefe se marca por es_autorizado, no por parentesco.)
}

# ── Catálogo 4b — tipo de víctima → GIC_PERSONA.PER_TIPOVICTIMA ──────────────
# ⚠️ PENDIENTE: no se identificó tabla catálogo ni campo SICAV de origen. Vacío.
TIPO_VICTIMA: dict = {}

# ── Catálogo 5 — territorio (GIC_N_DT_PUNTOS_ATENCION) ───────────────────────
# Las 1370 filas del volcado real viven en catalogos_oracle.json → clave 'dt_puntos'.
# Cada fila es la combinación completa DT × departamento × punto × municipio, con
# los cuatro ids SURROGATE de Oracle (NO son DANE: TOLIMA=30, ALVARADO=32).
#
# Por qué se cruza por NOMBRE y por la FILA COMPLETA (no columna a columna):
# - Los ids son surrogate ⇒ el único puente estable con SICAV es el nombre.
# - Los nombres NO son únicos por separado: 68 nombres de municipio se repiten con
#   ids distintos (BUENAVISTA tiene 4) y 'JORNADAS DE ATENCION Y/O FERIAS DE
#   SERVICIO' existe con 39 ids (uno por DT). Cruzar cada columna suelta produciría
#   el id equivocado en silencio.
# - En cambio la TUPLA (dt, departamento, punto, municipio) SÍ es única: verificado
#   1370/1370 combinaciones distintas, 0 ambiguas. Ese es el eje del cruce.
ARCHIVO_CROSSWALK = pathlib.Path(__file__).with_name("catalogos_oracle.json")


def normalizar_nombre(valor: str) -> str:
    """
    Forma canónica para comparar nombres SICAV ↔ Oracle.

    Hace falta porque los dos lados difieren en cosas que no son semánticas:
    - Oracle trae espacios de sobra ('DIRECCION TERRITORIAL ANTIOQUIA ', y la DT 14
      aparece con uno y con dos espacios finales).
    - SICAV acentúa y Oracle no ('JORNADAS DE ATENCIÓN…' vs 'JORNADAS DE ATENCION…').
    Se quitan diacríticos en AMBOS lados, así que el plegado es simétrico (NARIÑO y
    NARINO colapsan al mismo valor a los dos lados: no se pierde el cruce).

    También se pliega el formato de puntuación que difiere sin cambiar el significado
    ('Palenquero(a)' vs 'Palenquero (a)'; 'Cédula…/Contraseña' vs '…/ Contraseña') y el
    guion bajo que SICAV usa como separador ('Básica_primaria' → 'BASICA PRIMARIA'). Es
    simétrico en ambos lados. NO es fuzzy: tras plegar se sigue exigiendo IGUALDAD, así
    que dos opciones con distinto significado nunca colapsan (y si colapsaran, el
    resolver reporta ambigüedad en vez de escribir mal).
    """
    texto = unicodedata.normalize("NFD", (valor or "").strip().upper())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace("_", " ")
    # Colapsar espacios pegados a puntuación no semántica (simétrico en ambos lados).
    texto = re.sub(r"\s*([/(),.:;\-])\s*", r"\1", texto)
    return " ".join(texto.split())


@functools.lru_cache(maxsize=1)
def cargar_dt_puntos() -> tuple:
    """Filas de GIC_N_DT_PUNTOS_ATENCION con sus nombres ya normalizados (cacheado)."""
    with open(ARCHIVO_CROSSWALK, encoding="utf-8") as fh:
        datos = json.load(fh)
    filas = []
    for fila in datos["dt_puntos"]:
        filas.append({
            "iddt": fila["iddt"],
            "iddepartamento": fila["iddepartamento"],
            "idpuntoatencion": fila["idpuntoatencion"],
            "idmunicipio": fila["idmunicipio"],
            # Nombres tal cual vienen (para mensajes de error legibles)…
            "dt": fila["dt"].strip(),
            "departamento": fila["departamento"].strip(),
            "punto": fila["punto"].strip(),
            "municipio": fila["municipio"].strip(),
            # …y normalizados (para comparar).
            "_dt": normalizar_nombre(fila["dt"]),
            "_departamento": normalizar_nombre(fila["departamento"]),
            "_punto": normalizar_nombre(fila["punto"]),
            "_municipio": normalizar_nombre(fila["municipio"]),
        })
    return tuple(filas)


# ── Catálogo 6 — instrumento y respuestas (GIC_N_RESPUESTAS) ─────────────────
# Volcado real en `respuestas_oracle.json` (Query A de §3b-bis del traspaso).
#
# Oracle tiene UN SOLO instrumento (Query B: GIC_INSTRUMENTO = 1 fila,
# 1='CARACTERIZACION'). No separa por instrumento como SICAV, que tiene 8: todo el
# cuestionario cuelga de ese id. Por eso INS_IDINSTRUMENTO no necesita crosswalk.
INS_IDINSTRUMENTO_CARACTERIZACION = 1

# El puente de PREGUNTAS ya existía en SICAV y está VERIFICADO:
#   formulario.Pregunta.id_preg == GIC_N_PREGUNTAS.PRE_IDPREGUNTA
# Evidencia (2026-07-16): 14/14 ids del volcado existen en SICAV y, comparando el
# texto de la pregunta, 52/59 coinciden (39 idénticos tras normalizar + 13
# compatibles). Ej.: id_preg=5 → 'ZONA DE RESIDENCIA' en ambos lados.
#
# ⚠️ Lo que NO es puente: `OpcionRespuesta.id_resp_vivanto` NO es RES_IDRESPUESTA.
# Refutado con datos reales, 0/14: Mujer es 4599 en SICAV y 69 en Oracle; Indígena
# 4565 vs 112; Heterosexual 4602 vs 2351. Usarlo habría escrito ids ajenos, y como
# el procedure traga el NO_DATA_FOUND, en silencio. Las OPCIONES se cruzan por TEXTO
# dentro de su pregunta (universo de 2-14 candidatas ⇒ auto-desambiguado).
#
# ✅ CATÁLOGO COMPLETO (2026-07-22). El volcado truncado a 200 filas del 2026-07-16 se
# reemplazó: se cargó el catálogo entero del Oracle local (poblado por SELECT directo de
# prod, sin PII) y se regeneró `respuestas_oracle.json` → `_meta.completo=True`
# (902 preguntas / 3069 respuestas). Ver `scripts/cargar_catalogo_local.py` y el §0 del
# traspaso. El código conserva a propósito el CAMINO de "volcado parcial" (por si algún
# día se recarga incompleto): si `_meta.completo` fuese False, una pregunta ausente NO
# implica que no exista en Oracle, y el resolver jamás concluye "no existe" desde una
# ausencia. Con el catálogo completo actual, una ausencia sí es real (pendiente de negocio).
ARCHIVO_RESPUESTAS = pathlib.Path(__file__).with_name("respuestas_oracle.json")


@functools.lru_cache(maxsize=1)
def cargar_respuestas() -> dict:
    """
    Catálogo de preguntas/respuestas de Oracle, indexado por PRE_IDPREGUNTA.

    Devuelve {'_meta', 'huerfanas', 'preguntas'}:
      - `_meta.completo`: si es False, el volcado NO cubre todo el instrumento y una
        pregunta ausente puede existir perfectamente en Oracle. `_meta.cobertura` lo
        resume en una frase lista para meter en un mensaje de error.
      - `huerfanas`: RES_IDRESPUESTA sin fila en GIC_N_INSTRUMENTOXRESP, derivadas de
        la columna ESCRIBIBLE del export. NO son todas las de Oracle (Query C2 reportó
        153 en toda la tabla): son las de las filas exportadas.
      - `preguntas`: por PRE_IDPREGUNTA, con el texto de cada opción ya normalizado.
    """
    with open(ARCHIVO_RESPUESTAS, encoding="utf-8") as fh:
        datos = json.load(fh)
    meta = dict(datos["_meta"])
    preguntas = {}
    huerfanas = set()
    for p in datos["preguntas"]:
        opciones = []
        for r in p["respuestas"]:
            if not r["escribible"]:
                huerfanas.add(r["res_idrespuesta"])
            opciones.append({
                "res_idrespuesta": r["res_idrespuesta"],
                "res_respuesta": r["res_respuesta"],
                "_texto": normalizar_nombre(r["res_respuesta"]),
                "res_activa": r["res_activa"],
                "escribible": r["escribible"],
            })
        preguntas[p["pre_idpregunta"]] = {
            "pre_idpregunta": p["pre_idpregunta"],
            "tem_idtema": p["tem_idtema"],
            "ixp_orden": p["ixp_orden"],
            # GE / IN. Ojo: NO es el tipo de widget, es el NIVEL de la pregunta.
            # Ver PRE_TIPOPREGUNTA más abajo.
            "pre_tipopregunta": p["pre_tipopregunta"],
            "pre_pregunta": p["pre_pregunta"],
            "respuestas": opciones,
        }
    meta["cobertura"] = _describir_cobertura(meta)
    return {
        "_meta": meta,
        "huerfanas": frozenset(huerfanas),
        "preguntas": preguntas,
    }


def _describir_cobertura(meta) -> str:
    """Una frase que explique, dentro de un error, hasta dónde llega el volcado."""
    if meta.get("completo"):
        return "el volcado cubre el instrumento completo"
    t = meta.get("truncado") or {}
    temas = ", ".join(str(x) for x in (t.get("temas_cubiertos") or []))
    return (
        f"el volcado está TRUNCADO en {t.get('filas_exportadas')} filas (lo cortó el "
        f"cliente SQL, no es el final del instrumento): solo cubre los temas {temas}, "
        f"hasta la pregunta {t.get('ultima_pregunta')} (orden {t.get('ultimo_ixp_orden')})"
    )


# ── Catálogo 6-bis — crosswalk CURADO de opciones (SICAV → RES_IDRESPUESTA) ───
# Por qué existe: el resolver cruza la opción por TEXTO normalizado dentro de su
# pregunta, y jamás por aproximación (fuzzy escribiría la opción equivocada y el
# procedure se traga el error). Pero hay 164 opciones cuya redacción SICAV≠Oracle
# de verdad —'Otro' vs 'Otro, ¿cuál?', o el typo real de SICAV 'Combares' vs
# 'Combates'—: ahí el texto NO cruza y, sin ayuda, esos casos caen en el error de
# curaduría manual. Este archivo ES esa curaduría, hecha a mano contra el manual
# oficial: fija, opción por opción, qué RES_IDRESPUESTA de Oracle le corresponde.
#
# AUTORIDAD, no heurística. VERIFICADO (2026-07-22: 164/164 res_id existen en
# GIC_N_RESPUESTAS y son escribibles). Por eso en el resolver tiene PRECEDENCIA
# sobre el fallo de cruce por texto. Dos disciplinas que NO se relajan:
#   1. Solo clave EXACTA (pre_id + texto normalizado de la opción SICAV). Nada de
#      fuzzy; lo que no esté aquí se comporta EXACTAMENTE igual que sin crosswalk.
#   2. El res_id curado NO se escribe a ciegas: el resolver lo pasa igual por
#      `_verificar_escribible`, así que si algún día una entrada apuntara a una
#      huérfana, fallaría ruidosamente en vez de escribir en silencio.
ARCHIVO_CROSSWALK_OPCIONES = pathlib.Path(__file__).with_name("crosswalk_opciones.json")


@functools.lru_cache(maxsize=1)
def cargar_crosswalk_opciones() -> dict:
    """
    Crosswalk curado de opciones, indexado {(pre_id:int, texto_norm): res_id:int}.

    - `pre_id`  = PRE_IDPREGUNTA (int), el mismo puente que usa `cargar_respuestas`.
    - `texto_norm` = `normalizar_nombre(opcion_sicav)` — el MISMO plegado que el
      resolver aplica a la etiqueta de la opción, para que casen sin depender de
      acentos / espacios / puntuación no semántica.
    - valor = RES_IDRESPUESTA (int).

    Es un mapa EXACTO (dict), no fuzzy: una clave ausente significa "no curado", y el
    resolver debe comportarse como si el crosswalk no existiera para ese caso. El
    archivo trae la clave repetida solo con variantes que colapsan al mismo texto y
    apuntan al mismo res_id (verificado: 0 conflictos), así que el último-gana es inocuo.
    """
    with open(ARCHIVO_CROSSWALK_OPCIONES, encoding="utf-8") as fh:
        datos = json.load(fh)
    indice = {}
    for m in datos["mapeos"]:
        clave = (int(m["pre_id"]), normalizar_nombre(m["opcion_sicav"]))
        indice[clave] = int(m["res_id"])
    return indice


# ── geografía: DANE de SICAV → ID_MUNI_DEPTO de Oracle ───────────────────────
# Las preguntas de "departamento y municipio" (PRE_TIPOCAMPO='DP') NO guardan un
# RES_IDRESPUESTA por municipio: cada una tiene UNA respuesta contenedora y el
# municipio viaja como texto en RXP_TEXTORESPUESTA.
#
# La convención está MEDIDA EN PRODUCCIÓN (2026-07-28), no supuesta: el texto es
# `GIC_MUNICIPIO.ID_MUNI_DEPTO` — que resultó ser el propio código DIVIPOLA/DANE
# como número, SIN el cero a la izquierda:
#     Medellín '5001' (DANE 05001) · Alvarado '73026' · Cali '76001' · Ibagué '73001'
# Cruce total contra el catálogo: **28.151 de 28.151 respuestas reales (100%)**.
#
# SICAV escribe el DANE de 5 dígitos CON cero ('05001'), porque así lo guarda el
# selector de municipio del móvil. Sin normalizar, el INSERT entra con un texto que
# ningún reporte territorial resuelve — y el `WHEN OTHERS` del procedure no avisa.
#
# La otra convención que existe en el legacy (`SP_CONSTANCIA_GAVE`, que parte el
# texto por '-' contra AP_GEOGRAFIA) NO aparece en los datos reales de estas
# preguntas: en el propio paquete, las líneas de la convención escalar quedaron
# comentadas al lado de la nueva (body 4510-4511). Se implementa lo medido.
ARCHIVO_GEOGRAFIA = pathlib.Path(__file__).with_name("geografia_oracle.json")


@functools.lru_cache(maxsize=1)
def cargar_geografia() -> dict:
    """
    {'preguntas_dp': frozenset[int], 'preguntas_dt': frozenset[int],
     'municipios': dict[str, str]}  — municipios indexado por ID_MUNI_DEPTO (texto).

    Volcado de producción (catálogo, sin PII): 1.126 municipios, 33 departamentos y
    las 19 preguntas con tipo de campo DP/DT.
    """
    with open(ARCHIVO_GEOGRAFIA, encoding="utf-8") as fh:
        datos = json.load(fh)
    dp, dt = set(), set()
    for p in datos["preguntas_geograficas"]:
        (dp if p["tipo_campo"] == "DP" else dt).add(int(p["id_preg"]))
    return {
        "preguntas_dp": frozenset(dp),
        "preguntas_dt": frozenset(dt),
        "municipios": {str(m["id_muni_depto"]): m["nombre"] for m in datos["municipios"]},
    }


def normalizar_codigo_municipio(valor):
    """
    DANE de SICAV → ID_MUNI_DEPTO de Oracle. Devuelve None si no cruza.

    Es quitar el cero a la izquierda ('05001'→'5001') y comprobar contra el catálogo
    real. NO inventa: un municipio que Oracle no tiene devuelve None y el llamador
    decide (estricto → excepción; dry-run → marcador).
    """
    if valor is None:
        return None
    crudo = str(valor).strip()
    if not crudo.isdigit():
        return None
    normalizado = str(int(crudo))  # '05001' → '5001'; '5001' → '5001'
    return normalizado if normalizado in cargar_geografia()["municipios"] else None


# ── PRE_TIPOPREGUNTA — pista fuerte, todavía SIN confirmar ───────────────────
# GIC_N_INSTRUMENTOXPREG.PRE_TIPOPREGUNTA vale 'GE' o 'IN'. Pese al nombre NO es el
# tipo de pregunta (radio/texto/…): es el NIVEL. Evidencia (2026-07-16), cruzando las
# 62 preguntas del volcado con `formulario.Pregunta.nivel` de SICAV, que se llenó de
# forma independiente leyendo el manual:
#     GE → HOGAR    18        IN → PERSONA  43        IN → HOGAR     2
# 61 de 63 concuerdan. Y las 2 excepciones refuerzan la lectura en vez de romperla:
# son las preguntas 35 (autorreconocimiento étnico) y 8 (teléfono celular), donde el
# manual pide "pertenencia étnica POR PERSONA" — o sea Oracle acierta y el que está
# mal es SICAV (defecto ya conocido, ver memoria de flujos/manual).
#
# Por qué NO se cablea todavía: falta probar que RXP_TIPOPREGUNTA (el bind del
# procedure, en GIC_N_RESPUESTASENCUESTA) comparta dominio con PRE_TIPOPREGUNTA. Los
# nombres se parecen y sería el origen natural del dato — pero "se parece" no es
# evidencia, y aquí ya nos mordió una vez (id_resp_vivanto también "se parecía").
# Query de un renglón para cerrarlo, en §3b del traspaso:
#     SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA;
# Si sale {GE, IN}, el pendiente 3a.10 se resuelve sin crosswalk: se copia el valor
# que el propio Oracle ya tiene para esa pregunta.
TIPOPREGUNTA_NIVEL = {"GE": "HOGAR", "IN": "PERSONA"}


# Nombre canónico de cada catálogo (para mensajes de error y auditoría).
NOMBRES = {
    "tipo_caracterizacion": "GIC_TIPOCARACTERIZACION.TPOCRN_ID",
    "tipo_documento": "GIC_TIPODOC.TIP_IDTIPO",
    "parentesco": "GIC_PARENTESCOGENEALOGICO.PRST_ID",
    "tipo_victima": "GIC_PERSONA.PER_TIPOVICTIMA",
    "territorio": "GIC_N_DT_PUNTOS_ATENCION",
    "instrumento": "GIC_N_INSTRUMENTOXPREG.INS_IDINSTRUMENTO",
    "res_idrespuesta": "GIC_N_RESPUESTAS.RES_IDRESPUESTA",
    "tipo_pregunta": "GIC_N_RESPUESTASENCUESTA.RXP_TIPOPREGUNTA",
}
