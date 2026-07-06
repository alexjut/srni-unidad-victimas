#!/usr/bin/env python3
"""
Migración del instrumento TERRITORIAL v7 → v8.

Aplica, por lotes, las observaciones del equipo funcional
(ver docs/instrumento/observaciones-territorial-triage.md).

Es IDEMPOTENTE: lee siempre el fixture base v7 y (re)genera el v8, registrando
cada cambio. Se ejecuta con el python del venv del backend:

    srni-backend/.venv/Scripts/python.exe srni-backend/scripts/migrar_territorial_v7_a_v8.py

No carga nada en BD ni toca el bundle: eso es el paso final del barrido
(cargar_perfil → exportar_a_mobile).
"""
import io
import json
import os
import sys
import uuid

# UUID v5 deterministas — misma convención que scripts/patch_primas_jf.py, para
# que fixture e (eventual) bundle compartan el mismo id por pregunta (paridad
# backend↔APK). El esquema exacto no importa mientras sea único y estable.
NS = uuid.UUID("5c1a0000-0000-5c1a-0000-000000000001")
PERFIL_ID = "territorial"


def pid(cod):
    return str(uuid.uuid5(NS, f"{PERFIL_ID}:{cod}"))


def oid(cod, v):
    return str(uuid.uuid5(NS, f"{PERFIL_ID}:{cod}:{v}"))


def rid(origen, afecta):
    return str(uuid.uuid5(NS, f"{PERFIL_ID}:rule:{origen}->{afecta}"))


def _nivel_cap(d, cap):
    for c in d["capitulos"]:
        if c["codigo"] == cap:
            return c.get("nivel", "HOGAR")
    return "HOGAR"


def _max_orden(d, cap):
    ordenes = [p.get("orden", 0) for p in d["preguntas"] if p.get("capitulo_codigo") == cap]
    return max(ordenes) if ordenes else 0


def _existe(d, cod):
    return any(p.get("codigo_externo") == cod for p in d["preguntas"])


def _next_idpreg(d):
    return max([p.get("id_preg", 0) or 0 for p in d["preguntas"]] + [0]) + 1


def _next_id_resp(d):
    ids = [o.get("id_resp_vivanto") for p in d["preguntas"] for o in p.get("opciones", [])
           if isinstance(o.get("id_resp_vivanto"), int)]
    return (max(ids) if ids else 0) + 1


def _insertar_despues(d, cap, cod_ref):
    """Orden para insertar una pregunta justo después de cod_ref, desplazando +1
    el orden de las preguntas posteriores del mismo capítulo (solo afecta el orden
    de despliegue; las reglas referencian por código, no por orden)."""
    ref = next((p for p in d["preguntas"] if p.get("codigo_externo") == cod_ref), None)
    base = ref["orden"] if ref else _max_orden(d, cap)
    for p in d["preguntas"]:
        if p.get("capitulo_codigo") == cap and p.get("orden", 0) > base:
            p["orden"] += 1
    return base + 1


def _insertar_bloque(d, cod_ref, n):
    """Reserva n posiciones de orden justo después de cod_ref (en su propio
    capítulo), desplazando +n las posteriores. Devuelve (capitulo, orden_base);
    el llamador asigna orden_base+1 .. orden_base+n."""
    ref = next((p for p in d["preguntas"] if p.get("codigo_externo") == cod_ref), None)
    if not ref:
        return None
    cap, base = ref["capitulo_codigo"], ref["orden"]
    for p in d["preguntas"]:
        if p.get("capitulo_codigo") == cap and p.get("orden", 0) > base:
            p["orden"] += n
    return cap, base


def _opciones_sino(d):
    rr = _next_id_resp(d)
    return [{"valor": "1", "etiqueta": "Si", "id_resp_vivanto": rr, "orden": 1},
            {"valor": "2", "etiqueta": "No", "id_resp_vivanto": rr + 1, "orden": 2}]


def _pseudo_tipo(valor):
    """Devuelve el tipo de una pseudo-opción embebida ('NUMÉRICO'→NUMERICO,
    'TEXTO'→TEXTO) o None si es una opción normal. Robusto a acentos/codificación."""
    v = str(valor).upper()
    if "NUM" in v:
        return "NUMERICO"
    if "TEXT" in v:
        return "TEXTO"
    return None


def _convertir_embebido(d, parent_code, trigger, child_texto, child_suffix, desc):
    """Convierte la pseudo-opción embebida de parent_code en una pregunta-hija
    tipada, gateada por trigger, y elimina la pseudo-opción del padre. Devuelve
    True si convirtió algo."""
    parent = next((p for p in d["preguntas"] if p.get("codigo_externo") == parent_code), None)
    if not parent:
        return False
    pseudo = next((o for o in parent.get("opciones", []) if _pseudo_tipo(o.get("valor"))), None)
    if pseudo is None:
        return False
    tipo = _pseudo_tipo(pseudo["valor"])
    parent["opciones"] = [o for o in parent["opciones"] if o is not pseudo]
    cod = f"{parent_code}_{child_suffix}"
    if _existe(d, cod):
        return False
    cap, base = _insertar_bloque(d, parent_code, 1)
    d["preguntas"].append({
        "no_pregunta": "",
        "codigo_externo": cod,
        "id_preg": _next_idpreg(d),
        "capitulo_codigo": cap,
        "texto": child_texto,
        "tipo": tipo,
        "nivel": parent.get("nivel", "HOGAR"),
        "obligatoria": False,
        "orden": base + 1,
        "es_precargada": False,
        "fuente_precarga": "",
        "validaciones": {},
        "opciones": [],
        "id": pid(cod),
    })
    reglas(d).append({
        "origen": parent_code,
        "valor_trigger": trigger,
        "accion": "HABILITAR",
        "afecta": cod,
        "descripcion": desc,
    })
    return True

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # …/srni-backend
FIX = os.path.join(BASE, "apps", "formulario", "fixtures")
SRC = os.path.join(FIX, "perfil_territorial_v7.json")
DST = os.path.join(FIX, "perfil_territorial_v8.json")

CAMBIOS = []


def log(msg):
    CAMBIOS.append(msg)


def reglas(d):
    return d["reglas_skip_logic"]


# ─── LOTE 1 — Skip-logic (arreglos) ────────────────────────────────────────────

def lote1_j2_l2(d):
    """J2 (L2) no debe desplegarse si L1=5 (Con limitación permanente para trabajar)."""
    for r in reglas(d):
        if (r.get("origen") == "L1" and r.get("afecta") == "L2"
                and r.get("accion") == "HABILITAR" and "5" in str(r.get("valor_trigger", "")).split(",")):
            r["valor_trigger"] = "2,3,4,6,7"
            r["descripcion"] = ("[flujo] L2 visible si L1=2,3,4,6,7 "
                                "(NO si 5=limitación permanente) [obs funcional]")
            log("J2/L2: quitado '5' (limitacion permanente) del trigger L1->L2")


def lote1_d7_d8_etnico(d):
    """D7/D8 (RR2/RR3) deben desplegarse para persona indígena.

    Las reglas usaban `etnia == 'indigena'` (contexto derivado del RUV, que no
    llega fiable → no disparaba). Se pasan al patrón establecido: gatillar por la
    respuesta a Z4 (pertenencia étnica), Indígena = valor '1'. Igual que Z4→B17.
    """
    for r in reglas(d):
        if r.get("afecta") in ("RR2", "RR3") and str(r.get("origen_expr", "")).replace(" ", "") == "etnia=='indigena'":
            afecta = r["afecta"]
            r.pop("origen_expr", None)
            r["origen"] = "Z4"
            r["valor_trigger"] = "1"
            r["descripcion"] = (f"[étnico] {afecta} visible si Z4=1 (Indígena) "
                                f"[obs funcional: antes por contexto etnia, no disparaba]")
            log(f"D7/D8: regla de {afecta} ahora dispara por Z4=1 (Indígena)")


def lote1_b26_b27_territorio(d):
    """P26/P27: B27 (B17, "¿en qué tipo de territorio?") solo debe mostrarse si
    B26 (A30, "¿habita territorio colectivo?") = Si.

    Antes se gatillaba por Z4 (etnia), sin relación con B26 → aparecía aunque
    B26=No. Como A30 ya está gateada por Z4=1..5, la condición étnica se conserva
    por encadenamiento (A30 visible solo para étnicos → B17 solo si A30=Si).
    """
    for r in reglas(d):
        if r.get("afecta") == "B17" and r.get("accion") == "HABILITAR" and r.get("origen") == "Z4":
            r["origen"] = "A30"
            # A30 es BOOLEAN: el motor hardcodea la respuesta como "true"/"false"
            # (ver reference_skiplogic_funcional_apk). Un trigger "1" NUNCA dispara
            # → B17 quedaba oculta para siempre. Debe ser "true".
            r["valor_trigger"] = "true"
            r["descripcion"] = ("[flujo] B27 (tipo territorio) visible si B26=Si (A30=true) "
                                "[obs funcional: 26=No no debe desplegar 27]")
            log("P26/P27 (B26/B27): B17 visible si A30=true (territorio colectivo=Si), ya no por Z4")


# ─── LOTE 2 — Preguntas faltantes ──────────────────────────────────────────────

# Capítulos sin "Observaciones a este capitulo" (C ya tiene C_OBSERVA; E tiene
# F_OBSERVA "finales"). Falta en D, F(educación), J.Alimentación(JA),
# J.Fuerza(JF), K y L. (capitulo, codigo_nuevo, no_pregunta)
OBSERVACIONES = [
    ("D", "OBS_D", "D17"),
    ("F", "OBS_F", "F9"),
    ("JA", "OBS_JA", ""),
    ("JF", "OBS_JF", ""),
    ("K", "OBS_K", ""),
    ("L", "OBS_L", ""),
]


def lote2_observaciones(d):
    """Agrega una pregunta TEXTO_LARGO de observaciones al final de cada capítulo
    que no la tenga, con el nivel del capítulo y id uuid5 determinista."""
    seq = _next_idpreg(d)
    for cap, cod, nopreg in OBSERVACIONES:
        if _existe(d, cod):
            continue
        q = {
            "no_pregunta": nopreg,
            "codigo_externo": cod,
            "id_preg": seq,
            "capitulo_codigo": cap,
            "texto": "Observaciones a este capitulo",
            "tipo": "TEXTO_LARGO",
            "nivel": _nivel_cap(d, cap),
            "obligatoria": False,
            "orden": _max_orden(d, cap) + 1,
            "es_precargada": False,
            "fuente_precarga": "",
            "validaciones": {},
            "opciones": [],
            "id": pid(cod),
        }
        d["preguntas"].append(q)
        seq += 1
        log(f"Observaciones: +{cod} ({nopreg or 'obs'}) en cap {cap} "
            f"(orden {q['orden']}, {q['nivel']})")


ESTRATO_OPC = [("1", "Estrato 1"), ("2", "Estrato 2"), ("3", "Estrato 3"),
               ("4", "Estrato 4"), ("5", "Estrato 5"), ("6", "Estrato 6"),
               ("0", "Sin estrato")]


def lote2_estrato(d):
    """C7 (D8A, energía eléctrica): si el hogar SÍ cuenta con energía, preguntar
    el estrato — el manual lo trae como sub-opción 'Si ¿Estrato?'. Nueva pregunta
    LISTA gateada por D8A=true (BOOLEAN), justo después de energía. [manual C7]"""
    cod = "D8A_ESTRATO"
    if _existe(d, cod):
        return
    rr = _next_id_resp(d)
    opciones = []
    for i, (val, et) in enumerate(ESTRATO_OPC, start=1):
        opciones.append({"valor": val, "etiqueta": et, "id_resp_vivanto": rr, "orden": i})
        rr += 1
    d["preguntas"].append({
        "no_pregunta": "C7_1",
        "codigo_externo": cod,
        "id_preg": _next_idpreg(d),
        "capitulo_codigo": "C",
        "texto": "¿Cuál es el estrato de la vivienda?",
        "tipo": "LISTA",
        "nivel": "HOGAR",
        "obligatoria": False,
        "orden": _insertar_despues(d, "C", "D8A"),
        "es_precargada": False,
        "fuente_precarga": "",
        "validaciones": {},
        "opciones": opciones,
        "id": pid(cod),
    })
    reglas(d).append({
        "origen": "D8A",
        "valor_trigger": "true",
        "accion": "HABILITAR",
        "afecta": cod,
        "descripcion": "[manual C7] estrato visible si el hogar cuenta con energía eléctrica (D8A=Sí)",
    })
    log("Estrato: +D8A_ESTRATO (LISTA 1-6/Sin estrato) en cap C, visible si D8A=true")


# Cursos K17/K18/K19 (PL9A/PL10A/PL11A): hoy solo "Nombre del curso". El manual
# pide 4 campos por curso; faltan Institución, Tipo y ¿Certificó?. Cada sub-campo
# se gatilla con el mismo trigger PL25 que su curso padre.
CURSO_SUB = [
    ("INST", "Institución", "TEXTO"),
    ("TIPO", "Tipo", "TEXTO"),
    ("CERT", "¿Terminó y obtuvo certificación?", "BOOLEAN"),
]
CURSOS = [("PL9A", "1,2,3"), ("PL10A", "1,2"), ("PL11A", "1")]  # (curso, trigger PL25)


def lote2_cursos_subcampos(d):
    """Agrega Institución / Tipo / ¿Certificó? a cada uno de los 3 cursos (K17-19),
    justo después del nombre del curso, con el mismo gate PL25 del curso. [manual]"""
    for curso, trig in CURSOS:
        res = _insertar_bloque(d, curso, len(CURSO_SUB))
        if res is None:
            continue
        cap, base = res
        for i, (suf, txt, tipo) in enumerate(CURSO_SUB, start=1):
            cod = f"{curso}_{suf}"
            if _existe(d, cod):
                continue
            d["preguntas"].append({
                "no_pregunta": "",
                "codigo_externo": cod,
                "id_preg": _next_idpreg(d),
                "capitulo_codigo": cap,
                "texto": txt,
                "tipo": tipo,
                "nivel": "PERSONA",
                "obligatoria": False,
                "orden": base + i,
                "es_precargada": False,
                "fuente_precarga": "",
                "validaciones": {},
                "opciones": _opciones_sino(d) if tipo == "BOOLEAN" else [],
                "id": pid(cod),
            })
            reglas(d).append({
                "origen": "PL25",
                "valor_trigger": trig,
                "accion": "HABILITAR",
                "afecta": cod,
                "descripcion": f"[manual K17-19] {txt} del curso visible si recibió cursos (PL25={trig})",
            })
        log(f"Cursos: +{curso}_INST/_TIPO/_CERT (3 sub-campos, gate PL25={trig})")


def lote2_k35_cual(d):
    """K35 (PL23, "¿Conoce servicios ofrecidos por alguna institución?"): agrega
    "¿Cuál servicio?" (TEXTO) visible si PL23=Sí. [manual K35]"""
    cod = "PL23_CUAL"
    if _existe(d, cod):
        return
    res = _insertar_bloque(d, "PL23", 1)
    if res is None:
        return
    cap, base = res
    d["preguntas"].append({
        "no_pregunta": "",
        "codigo_externo": cod,
        "id_preg": _next_idpreg(d),
        "capitulo_codigo": cap,
        "texto": "¿Cuál servicio?",
        "tipo": "TEXTO",
        "nivel": "PERSONA",
        "obligatoria": False,
        "orden": base + 1,
        "es_precargada": False,
        "fuente_precarga": "",
        "validaciones": {},
        "opciones": [],
        "id": pid(cod),
    })
    reglas(d).append({
        "origen": "PL23",
        "valor_trigger": "true",
        "accion": "HABILITAR",
        "afecta": cod,
        "descripcion": "[manual K35] ¿cuál servicio? visible si conoce servicios de alguna institución (PL23=Sí)",
    })
    log("K35: +PL23_CUAL (¿cuál servicio?) visible si PL23=true")


# J31-J40 (M2A,M2B,M2C,M5-M11): ingresos del mes pasado. El manual pide en cada
# uno "Si ¿Valor del mes pasado?". Se agrega un hijo NUMERICO ($) gateado por =Sí.
INGRESOS = ["M2A", "M2B", "M2C", "M5", "M6", "M7", "M8", "M9", "M10", "M11"]
_PSEUDO_OPC = {"NUMÉRICO", "NUMERICO", "TEXTO"}


def lote2_valores_ingresos(d):
    """Agrega '¿Valor recibido el mes pasado? $' (NUMERICO) a cada ingreso J31-J40,
    visible si el ingreso = Sí (valor 1). Limpia la pseudo-opción embebida
    'NUMÉRICO/Valor' (patrón roto, reemplazado por la pregunta hija). [manual]"""
    P = {p["codigo_externo"]: p for p in d["preguntas"]}
    for code in INGRESOS:
        parent = P.get(code)
        if not parent:
            continue
        antes = len(parent["opciones"])
        parent["opciones"] = [o for o in parent["opciones"]
                              if str(o.get("valor")) not in _PSEUDO_OPC]
        if len(parent["opciones"]) != antes:
            log(f"Ingresos: limpiada pseudo-opción embebida de {code}")
        cod = f"{code}_VALOR"
        if _existe(d, cod):
            continue
        res = _insertar_bloque(d, code, 1)
        if res is None:
            continue
        cap, base = res
        d["preguntas"].append({
            "no_pregunta": "",
            "codigo_externo": cod,
            "id_preg": _next_idpreg(d),
            "capitulo_codigo": cap,
            "texto": "¿Valor recibido el mes pasado? $",
            "tipo": "NUMERICO",
            "nivel": "PERSONA",
            "obligatoria": False,
            "orden": base + 1,
            "es_precargada": False,
            "fuente_precarga": "",
            "validaciones": {},
            "opciones": [],
            "id": pid(cod),
        })
        reglas(d).append({
            "origen": code,
            "valor_trigger": "1",
            "accion": "HABILITAR",
            "afecta": cod,
            "descripcion": f"[manual J31-J40] valor $ visible si {code}=Sí",
        })
        log(f"Ingresos: +{cod} (valor $) visible si {code}=Sí")


def lote2_frecuencia_alimentos(d):
    """I4-I17 (J1A..J1N): consumo de alimentos en los últimos 7 días. Cada uno es
    BOOLEAN con pseudo-opción 'Valor (1 a 7)'. Se convierte en hijo NUMERICO
    '¿En cuántos días? (1 a 7)' visible si el alimento=Sí (BOOLEAN → true)."""
    codes = [p["codigo_externo"] for p in d["preguntas"]
             if p.get("capitulo_codigo") == "JA"
             and any(_pseudo_tipo(o.get("valor")) == "NUMERICO" for o in p.get("opciones", []))]
    for code in codes:
        if _convertir_embebido(d, code, "true",
                               "¿En cuántos de los últimos 7 días lo consumió? (1 a 7)", "DIAS",
                               f"[manual I4-I17] días de consumo (1-7) visible si {code}=Sí"):
            log(f"Frecuencia alimentos: +{code}_DIAS (1-7) si {code}=Sí")


def lote2_i18_porque(d):
    """I18 (I1D, ¿la alimentación es suficiente?): pseudo-opción 'Campo Abierto'
    del 'No Por qué' → hijo TEXTO '¿Por qué?' visible si I1D=No (valor 2)."""
    if _convertir_embebido(d, "I1D", "2", "¿Por qué?", "PORQUE",
                           "[manual I18] motivo visible si considera que la alimentación NO es suficiente (I1D=No)"):
        log("I18: +I1D_PORQUE (texto) si I1D=No")


def lote2_k29_cual(d):
    """K29 (PL20, ¿recibió apoyo económico de alguna institución?): pseudo-opción
    'Cuál' → hijo TEXTO '¿Cuál institución?' visible si PL20=Sí (BOOLEAN → true)."""
    if _convertir_embebido(d, "PL20", "true", "¿Cuál institución?", "CUAL",
                           "[manual K29] institución visible si recibió apoyo económico (PL20=Sí)"):
        log("K29: +PL20_CUAL (texto) si PL20=Sí")


def lote2_fix_posicion_ocupacional_otro(d):
    """PL5C/PL6C/PL7C (K8/K11/K14, posición ocupacional): la opción 10='Otro ¿Cuál?'
    debe habilitar el campo _OTRO, pero la regla apuntaba a valor 7 (bug). Corrige el
    trigger a '10' y elimina la pseudo-opción TEXTO '¿Cuál?' que renderizaba como
    radio fantasma (el _OTRO ya la reemplaza)."""
    for code in ("PL5C", "PL6C", "PL7C"):
        parent = next((p for p in d["preguntas"] if p.get("codigo_externo") == code), None)
        if parent:
            parent["opciones"] = [o for o in parent["opciones"] if _pseudo_tipo(o.get("valor")) is None]
        for r in reglas(d):
            if (r.get("origen") == code and r.get("afecta") == f"{code}_OTRO"
                    and str(r.get("valor_trigger")) == "7"):
                r["valor_trigger"] = "10"
                r["descripcion"] = f"[fix] {code}_OTRO visible si posición ocupacional = Otro (opción 10)"
                log(f"Posición ocupacional: {code}_OTRO dispara con 'Otro' (10), no 7; pseudo-opción eliminada")


def lote2_at2_porque(d):
    """AT2 (M2, ¿se le adjudicó terreno?): pseudo-opción TEXTO 'Por qué (Histórico)'
    → hijo TEXTO opcional visible si AT2=2 (No dispongo). Elimina el radio fantasma."""
    if _convertir_embebido(d, "AT2", "2", "¿Por qué? (Histórico)", "PORQUE",
                           "[histórico M2] motivo si no dispone de terreno/lote/predio (AT2=No dispongo)"):
        log("AT2: +AT2_PORQUE (texto) si AT2=2")


# ─── LOTE 3 — Multi-select ─────────────────────────────────────────────────────

# Preguntas que el manual define como "selección múltiple con múltiple respuesta"
# pero el fixture tenía como LISTA (única). El motor de skip-logic ya soporta
# orígenes multi-select (helper _valoresSeleccionados, mirror en views.py).
#   C6A=C20, C17A=C21 (factores que afectan la zona) · I10A=H3 tipo rehabilitación ·
#   I11A psicosocial · I1A1=I2 aprovisionamiento · PL21A=K33 motivos cierre negocio
MULTISELECT = ["C6A", "C17A", "I10A", "I11A", "I1A1", "PL21A"]


def lote3_multiselect(d):
    for code in MULTISELECT:
        p = next((x for x in d["preguntas"] if x.get("codigo_externo") == code), None)
        if p and p.get("tipo") == "LISTA":
            p["tipo"] = "LISTA_MULTIPLE"
            log(f"Multi-select: {code} ({p.get('no_pregunta') or '·'}) LISTA → LISTA_MULTIPLE")


# ─── LOTE 4 — DIVIPOLA ─────────────────────────────────────────────────────────

# D6 (RR1) y D11 (RR6): 'departamento y municipio' de retorno. Eran TEXTO libre;
# se pasan a COMBO_DINAMICO para usar el SelectorMunicipio (1102 muns DANE, con
# buscador y offline). El renderer mapea por tipo (esCombo = COMBO_DINAMICO) y el
# componente ya precarga los municipios (obs H3) y busca por depto/mun (obs H4).
# PL28 (negocio) ya era COMBO_DINAMICO.
COMBO_MUNICIPIO = ["RR1", "RR6"]
_COMBO_PLACEHOLDER = {"valor": "", "etiqueta": "Departamento", "id_resp_vivanto": None, "orden": 1}


def lote4_divipola(d):
    for code in COMBO_MUNICIPIO:
        p = next((x for x in d["preguntas"] if x.get("codigo_externo") == code), None)
        if p and p.get("tipo") == "TEXTO":
            p["tipo"] = "COMBO_DINAMICO"
            if not p.get("opciones"):
                p["opciones"] = [dict(_COMBO_PLACEHOLDER)]
            log(f"DIVIPOLA: {code} ({p.get('no_pregunta')}) TEXTO → COMBO_DINAMICO (SelectorMunicipio)")


LOTES = [
    ("LOTE 1 — skip-logic", [lote1_j2_l2, lote1_d7_d8_etnico, lote1_b26_b27_territorio]),
    ("LOTE 2 — preguntas faltantes",
     [lote2_observaciones, lote2_estrato, lote2_cursos_subcampos, lote2_k35_cual,
      lote2_valores_ingresos, lote2_frecuencia_alimentos, lote2_i18_porque, lote2_k29_cual,
      lote2_fix_posicion_ocupacional_otro, lote2_at2_porque]),
    ("LOTE 3 — multi-select", [lote3_multiselect]),
    ("LOTE 4 — DIVIPOLA", [lote4_divipola]),
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # consola Windows (cp1252) → utf-8
    except Exception:
        pass
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)

    iv = d.get("instrumento_version")
    if not isinstance(iv, dict):
        iv = {}
        d["instrumento_version"] = iv
    iv["numero"] = "V8"
    iv["vigente_desde"] = "2026-07-05"

    for nombre, fns in LOTES:
        for fn in fns:
            fn(d)

    with io.open(DST, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    print(f"Generado: {os.path.relpath(DST, BASE)}")
    print(f"Versión: {iv['numero']} | preguntas={len(d['preguntas'])} | reglas={len(reglas(d))}")
    print(f"Cambios aplicados ({len(CAMBIOS)}):")
    for c in CAMBIOS:
        print(f"  - {c}")


if __name__ == "__main__":
    main()
