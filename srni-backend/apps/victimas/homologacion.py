"""
Homologación de los dominios de la fuente Oracle a los catálogos de SICAV.

Todo lo de aquí está MEDIDO en producción el 2026-07-29, no supuesto. Cada mapa
lleva la frecuencia real de los valores que cubre, para que se vea qué se está
decidiendo y con cuánto peso.

Por qué existe un módulo aparte: la homologación es la parte de la carga que tiene
criterio, así que se prueba sola. Que el comando de carga funcione no dice nada
sobre si un `"CONTRASEÑA"` acabó siendo una cédula.
"""
import re
import unicodedata

# ── tipo de documento ────────────────────────────────────────────────────────
# `GIC_PERSONA.PER_TIPODOC` es un VARCHAR LIBRE, no una FK. Medición: **59 valores
# distintos con más de 100 usos**, entre ellos el mismo concepto escrito de siete
# formas ("CC", "CÉDULA DE CIUDADANÍA", "Cedula de Ciudadanía / Contraseña",
# "CEDULA CIUDADANIA", "CONTRASEÑA", "93", "1"…), ids numéricos de catálogo, y
# hasta mojibake ("CONTRASEÃ‘A", que es "CONTRASEÑA" leído con la codificación mal).
#
# Se homologa por PATRÓN sobre el texto normalizado, no por lista exacta: una lista
# exacta de 59 entradas se queda corta con el valor 60.
_PATRONES_TIPODOC = [
    # (regex sobre el texto normalizado, código SICAV, usos medidos aprox.)
    (r"cedula.*extranjer|^ce\d?$",              "CE",  3_400),
    (r"cedula|contrasena|^cc\d?$",              "CC",  3_820_000),
    (r"tarjeta.*identidad|^ti\d?$",             "TI",  1_390_000),
    (r"registro.*civil|^rc\w?$|nuip|niup",      "RC",  790_000),
    (r"pasaporte|^pa\d?$",                      "PA",  242),
    (r"^nit$",                                  "NIT", 674),
    (r"permiso.*proteccion.*temporal|^ppt$|pep", "PE", 651),
]

# Los ids numéricos son `RES_IDRESPUESTA` de la pregunta 30 (tipo de documento) del
# instrumento de Oracle. No se adivinan: se resuelven contra el catálogo real que ya
# está volcado en `sincronizacion/oracle/respuestas_oracle.json`.
_PREGUNTA_TIPODOC_ORACLE = 30

# Valores que declaran explícitamente que NO se sabe el tipo. No se homologan a
# ningún documento: van a NULL, que es la verdad. Suman ~15.000 usos medidos, más
# el 14,5 % que viene directamente vacío.
_SIN_DATO = re.compile(r"sin informacion|sin dato|sin datos|^ninguno$|^otro?$|^otr$|"
                       r"no responde|no sabe|indocumentado|^ind$|^ni$")


def _norm(texto) -> str:
    """Minúsculas, sin acentos, sin puntuación de más. Repara el mojibake común."""
    s = str(texto or "").strip()
    # "CONTRASEÃ‘A" es "CONTRASEÑA" con la codificación estropeada: los bytes UTF-8
    # de la Ñ (0xC3 0x91) se leyeron como dos caracteres sueltos.
    #
    # Se prueba cp1252 antes que latin-1 y el orden importa: en este caso el 0x91 se
    # convirtió en U+2018 (comilla tipográfica), que es un mapeo de cp1252 y que
    # latin-1 no sabe codificar de vuelta —falla y deja el texto intacto—. Con 319
    # usos medidos, no es una rareza que se pueda ignorar.
    if "Ã" in s:
        for codec in ("cp1252", "latin-1"):
            try:
                s = s.encode(codec).decode("utf-8")
                break
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def homologar_tipo_documento(valor, catalogo_respuestas=None):
    """
    Texto libre de `PER_TIPODOC` → código de `TipoDocumento` de SICAV, o None.

    None significa **"la fuente no permite saberlo"** y es un resultado legítimo, no
    un fallo: esas personas se cargan sin tipo y se encuentran por el índice de
    respaldo (ver `Victima.numero_documento_hash_sin_tipo`). Inventarles un tipo
    —asumir CC, que serían el ~90 %— afirmaría un documento que nadie verificó.

    `catalogo_respuestas`: dict {res_idrespuesta: texto} para resolver los valores
    numéricos. Si no se pasa, los numéricos devuelven None.
    """
    texto = _norm(valor)
    if not texto:
        return None

    # 1) los que declaran no saber, antes que nada: "OTRO" no es un documento.
    if _SIN_DATO.search(texto):
        return None

    # 2) id numérico de catálogo → se resuelve por su texto en Oracle, no a ojo.
    if texto.isdigit():
        if not catalogo_respuestas:
            return None
        texto_oracle = _norm(catalogo_respuestas.get(int(texto), ""))
        if not texto_oracle or _SIN_DATO.search(texto_oracle):
            return None
        texto = texto_oracle

    # 3) por patrón
    for patron, codigo, _usos in _PATRONES_TIPODOC:
        if re.search(patron, texto):
            return codigo
    return None


def cargar_catalogo_tipodoc_oracle():
    """
    {res_idrespuesta: texto} de la pregunta de tipo de documento, desde el volcado
    que ya existe. Es lo que permite traducir los `PER_TIPODOC` numéricos.
    """
    from apps.sincronizacion.oracle import catalogos
    # `cargar_respuestas()["preguntas"]` es un DICT indexado por pre_idpregunta, no
    # una lista. Iterarlo devuelve las claves (ints), no las filas.
    cat = catalogos.cargar_respuestas()
    fila = cat["preguntas"].get(_PREGUNTA_TIPODOC_ORACLE)
    if not fila:
        return {}
    return {int(r["res_idrespuesta"]): (r.get("res_respuesta") or "")
            for r in fila["respuestas"]}


# ── pertenencia étnica ───────────────────────────────────────────────────────
# `M_CARACT_TABLA_RA_PER.PERT_ETNICA` sí viene limpio: 6 valores + NULL. Medido.
_ETNIA = {
    "ninguna": "NINGUNA",                                  # 6.877.003
    "negro(a) o afrocolombiano(a)": "AFROCOLOMBIANO",      # 741.326
    "indigena": "INDIGENA",                                # 168.707
    "gitano(a) rom": "ROM",                                # 29.788
    "palenquero": "PALENQUERO",                            # 1.021
}
# El valor de raizal viene TRUNCADO en el corte ("Raizal del Archipielago de San
# Andres y Prov"), así que se casa por prefijo y no por igualdad. 9.764 personas.
_ETNIA_PREFIJO = [("raizal", "RAIZAL")]


def homologar_etnia(valor):
    """PERT_ETNICA → nuestra opción. NULL/desconocido → '' (sin dato), no 'NINGUNA'.

    Esa distinción importa: "no sabemos su pertenencia étnica" (2.133.894 personas
    con NULL) no es lo mismo que "declaró no pertenecer a ningún grupo" (6.877.003).
    Colapsarlas borraría de las estadísticas a dos millones de personas sin dato.
    """
    texto = _norm(valor)
    if not texto or texto == "none":
        return ""
    if texto in _ETNIA:
        return _ETNIA[texto]
    for prefijo, codigo in _ETNIA_PREFIJO:
        if texto.startswith(prefijo):
            return codigo
    return ""


# ── género ───────────────────────────────────────────────────────────────────
# Medido: Mujer 3.885.620 · Hombre 3.882.341 · NULL 2.133.894 · No Informa 57.964
# · LGBTI 1.684.
_GENERO = {"mujer": "F", "hombre": "M", "no informa": "ND"}


def homologar_genero(valor):
    """
    GENERO_HOM → M/F/NB/ND.

    "LGBTI" (1.684 personas) se homologa a **ND (no declara)**, no a NB (no binario).
    LGBTI describe orientación o identidad de forma agregada; asumir que esas personas
    son no binarias sería atribuirles una identidad que no declararon. ND dice la
    verdad: el dato que tenemos no responde a esta pregunta.
    """
    texto = _norm(valor)
    if not texto or texto == "none":
        return "ND"
    return _GENERO.get(texto, "ND")


# ── discapacidad ─────────────────────────────────────────────────────────────
def homologar_discapacidad(valor):
    """
    DISCAP → bool. Medido: 194.603 con 1, y **9.766.900 con NULL**.

    NULL se toma como False porque el campo es booleano y no admite otra cosa, pero
    conviene tenerlo claro: ese NULL es "no consta", no "no tiene discapacidad". Con
    el 98 % del corte en NULL, este campo NO sirve para afirmar que alguien no tiene
    discapacidad — solo para saber quién sí la tiene registrada.
    """
    return str(valor or "").strip() == "1"


# ── estado en el RUV ─────────────────────────────────────────────────────────
# ✅ CONFIRMADO el 2026-07-31 con el catálogo oficial: **`RUV.TBESTADO_VAL`**
# (esquema RUV, vía la conexión `Ruv_tns`). Son SIETE estados, no cuatro:
#
#   1 Incluido                    5 No Valorado - Devuelto
#   2 No Incluido                 6 Afectado - No Valorado
#   3 En Valoración               7 No Afectado - No Valorado
#   4 Excluido
#
# Historia de cómo se llegó, que vale la pena conservar: circularon DOS versiones
# verbales contradictorias —una decía 3=en valoración/4=excluido y otra 3=excluido/
# 4=cesado—. La medición ya apuntaba a la primera: entre las personas **ya
# caracterizadas** el estado 3 cae de 4,3 % a 0,5 %, ocho veces menos, que es lo
# propio de un caso en trámite. El catálogo confirmó esa lectura.
#
# Moraleja para la próxima: el dato medido resolvió bien antes de que llegara el
# catálogo, y el segundo testimonio verbal —más reciente— era el equivocado.
_ESTADO_RUV = {
    1: "INCLUIDO",
    2: "NO_INCLUIDO",
    3: "EN_PROCESO",      # "En Valoración"
    4: "EXCLUIDO",
    # Los tres siguientes NO aparecen en el corte `M_CARACT_TABLA_RA_PER` —que solo
    # trae 1-4— pero existen en el catálogo y pueden llegar por otra vía. Se mapean
    # a lo más cercano de nuestros cuatro valores, sin inventar categorías nuevas:
    5: "EN_PROCESO",      # "No Valorado - Devuelto": sigue sin decisión
    6: "EN_PROCESO",      # "Afectado - No Valorado": afectado, pendiente de valorar
    7: "NO_INCLUIDO",     # "No Afectado - No Valorado": no hay afectación que valorar
}

# Los estados que, para el RUV, significan que la persona ES víctima reconocida.
# Es el filtro del padrón: la Unidad caracteriza a víctimas incluidas.
ESTADOS_VICTIMA = frozenset({1})


def homologar_estado_ruv(valor):
    """
    Código de `RUV.TBESTADO_VAL` → nuestro `estado_ruv`. '' si no se reconoce.

    Con el catálogo confirmado, este valor **ya puede usarse como criterio**. Aun así
    la habilitación para caracterizar no se deriva sola de aquí: ver
    `debe_recaracterizarse`, porque una persona incluida también deja de estar al día
    si su caracterización venció.
    """
    try:
        return _ESTADO_RUV.get(int(valor), "")
    except (TypeError, ValueError):
        return ""


def es_victima(valor) -> bool:
    """
    ¿Esta persona va al padrón que descarga la APK?

    Solo las **incluidas en el RUV**. Importa porque `MI_PERSONAS` tiene 49.529.433
    personas —el registro completo del modelo integrado, no solo víctimas— y el padrón
    descargable no puede llevarlas todas: el diseño calculaba ~150 MB para 10 M.
    """
    try:
        return int(valor) in ESTADOS_VICTIMA
    except (TypeError, ValueError):
        return False


# ── vigencia de la caracterización ───────────────────────────────────────────
# La norma: se recaracteriza **cada 2 años** para actualizar datos.
#
# Medido el 2026-07-31 sobre las 3.331.733 personas con caracterización:
#
#     este año     685.381   (20,6 %)
#     hace 1 año   707.853   (41,8 % acumulado)
#     hace 2 años  711.347   (63,2 %)
#     hace 3 años  246.122   (70,6 %)
#     hace 4 años  912.630   (97,9 %)   ← campaña masiva de 2022
#     5+ años       ~70.000
#
# ⇒ con la regla de 2 años, **1.936.352 personas (58,2 %) están vencidas** y deberían
# recaracterizarse. Ese es el trabajo pendiente que el sistema tiene que poder señalar.
ANIOS_VIGENCIA_CARACTERIZACION = 2


def debe_recaracterizarse(fecha_ult_caracterizacion, hoy=None) -> bool:
    """
    ¿Toca actualizar los datos de esta persona?

    Sin fecha → **True**: nunca caracterizada (o no consta) es justamente a quien hay
    que caracterizar. Devolver False dejaría fuera a quien más lo necesita.
    """
    import datetime

    if not fecha_ult_caracterizacion:
        return True
    hoy = hoy or datetime.date.today()
    fecha = fecha_ult_caracterizacion
    if isinstance(fecha, datetime.datetime):
        fecha = fecha.date()
    # Comparación por años cumplidos, no por días: "hace más de 2 años".
    cumplidos = (hoy.year - fecha.year) - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
    return cumplidos >= ANIOS_VIGENCIA_CARACTERIZACION
