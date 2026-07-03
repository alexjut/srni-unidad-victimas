# -*- coding: utf-8 -*-
"""
Reconstruye la cadena de PRIMAS del cap. J. Fuerza de Trabajo (nivel PERSONA) según el
diccionario oficial V7. El fixture solo tenía Prima de servicios (L22) + su "¿cuánto?"
mal-codeado como L22C1, y saltaba directo a accidentes (L22E). Faltaban navidad,
vacaciones y viáticos (VIVANTO J24/J25/J26) y varios "¿cuánto?".

Diccionario (PERSONAS, J. FUERZA DE TRABAJO):
  L22  J23  Prima de servicios      + L22A1  ¿cuánto?
  L22B J24  Prima de navidad        + L221   ¿cuánto?
  L22C J25  Prima de vacaciones     + L22C1  ¿cuánto?
  L22D J26  Viáticos/bonificaciones + L22D1  ¿cuánto?
  L22E J27  Pagos por accidentes    + L22E1  ¿cuánto?

Acciones (idempotente): renombra el L22C1 existente (que era el ¿cuánto? de servicios)
a su código correcto L22A1; agrega L22B, L221, L22C, L22C1(nuevo=vacaciones), L22D, L22D1,
L22E1; encadena el flujo L22→L22B→L22C→L22D→L22E y cada "¿cuánto?" visible si su prima=Sí.
Fixture y bundle usan el MISMO id (uuid5) por pregunta para la paridad backend↔APK.

Uso: python scripts/patch_primas_jf.py [--check]
"""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "srni-backend/apps/formulario/fixtures/perfil_territorial_v7.json"
BUN = ROOT / "srni-mobile/assets/instrumentos/territorial_v7.json"
NS = uuid.UUID("5c1a0000-0000-5c1a-0000-000000000001")
PERFIL = "territorial"
CAP = "JF"

def pid(cod):   return str(uuid.uuid5(NS, f"{PERFIL}:{cod}"))
def oid(cod, v): return str(uuid.uuid5(NS, f"{PERFIL}:{cod}:{v}"))
def rid(o, a):   return str(uuid.uuid5(NS, f"{PERFIL}:rule:{o}->{a}"))

CUANTO = "¿Cuánto recibió? $"
# (codigo, no_pregunta, texto, id_preg, id_resp_si, id_resp_no)  — None = pregunta "¿cuánto?" NUMERICO
NUEVAS = [
    ("L22B", "J24", "¿En los últimos 12 meses recibió: Prima de navidad?", 142, 498, 499),
    ("L221", "",    CUANTO, None, None, None),
    ("L22C", "J25", "¿En los últimos 12 meses recibió: Prima de vacaciones?", 143, 500, 501),
    ("L22C1", "",   CUANTO, None, None, None),          # nuevo = ¿cuánto? de vacaciones
    ("L22D", "J26", "¿En los últimos 12 meses recibió: Viáticos permanentes y/o bonificaciones anuales?", 144, 502, 503),
    ("L22D1", "",   CUANTO, None, None, None),
]
L22E1 = ("L22E1", "", CUANTO, None, None, None)         # ¿cuánto? de accidentes (va tras L22E)

# Flujo secuencial (valor_trigger vacío) y "¿cuánto?" (trigger true)
CADENA = [("L22", "L22B"), ("L22B", "L22C"), ("L22C", "L22D"), ("L22D", "L22E")]
CUANTOS = [("L22", "L22A1"), ("L22B", "L221"), ("L22C", "L22C1"), ("L22D", "L22D1"), ("L22E", "L22E1")]


def _indent(txt):
    for l in txt.split("\n")[1:]:
        s = l.lstrip(" ")
        if s:
            return len(l) - len(s)
    return 2


def preg_fixture(cod, no, texto, id_preg, si, no_):
    es_bool = si is not None
    return {
        "no_pregunta": no, "codigo_externo": cod, "id_preg": id_preg, "capitulo_codigo": CAP,
        "texto": texto, "tipo": "BOOLEAN" if es_bool else "NUMERICO", "nivel": "PERSONA",
        "obligatoria": True, "orden": 0, "es_precargada": False, "fuente_precarga": "",
        "validaciones": {}, "id": pid(cod),
        "opciones": ([{"valor": "1", "etiqueta": "Si", "id_resp_vivanto": si, "orden": 1},
                      {"valor": "2", "etiqueta": "No", "id_resp_vivanto": no_, "orden": 2}]
                     if es_bool else []),
    }


def preg_bundle(cod, no, texto, id_preg, si, no_):
    es_bool = si is not None
    return {
        "id": pid(cod), "codigo_externo": cod, "no_pregunta": no, "texto": texto,
        "descripcion_ayuda": "", "tipo": "BOOLEAN" if es_bool else "NUMERICO", "nivel": "PERSONA",
        "orden": 0, "obligatoria": True, "activa": True, "validaciones": {},
        "opciones": ([{"id": oid(cod, "1"), "valor": "1", "etiqueta": "Si", "orden": 1, "finaliza_capitulo": False},
                      {"id": oid(cod, "2"), "valor": "2", "etiqueta": "No", "orden": 2, "finaliza_capitulo": False}]
                     if es_bool else []),
        "es_precargada": False,
    }


def _reordenar(preguntas):
    """Renumera 'orden' de las preguntas del cap JF en el orden de la lista."""
    jf = [p for p in preguntas if p.get("capitulo_codigo") == CAP]
    base = min((p["orden"] for p in jf), default=1)
    for i, p in enumerate(jf):
        p["orden"] = base + i


def patch_fixture(check=False):
    txt = FIX.read_text(encoding="utf-8")
    ind = _indent(txt)
    d = json.loads(txt)
    P = d["preguntas"]
    if any(p["codigo_externo"] == "L22B" for p in P):
        print("  fixture: ya tiene L22B (idempotente, no cambia)."); return
    if check:
        print("  fixture: agregaría L22A1(rename)+L22B/L221/L22C/L22C1/L22D/L22D1/L22E1 y reglas."); return
    # 1) renombrar L22C1 -> L22A1 (¿cuánto? de servicios)
    ex = next(p for p in P if p["codigo_externo"] == "L22C1")
    ex["codigo_externo"] = "L22A1"
    # 2) insertar bloque primas tras L22A1, y L22E1 tras L22E
    idx = P.index(ex)
    nuevas = [preg_fixture(*n) for n in NUEVAS]
    P[idx + 1: idx + 1] = nuevas
    ie = next(i for i, p in enumerate(P) if p["codigo_externo"] == "L22E")
    P[ie + 1: ie + 1] = [preg_fixture(*L22E1)]
    _reordenar(P)
    # 3) reglas
    R = d["reglas_skip_logic"]
    for r in R:
        if r.get("origen") == "L22" and r.get("afecta") == "L22C1":
            r["afecta"] = "L22A1"; r["descripcion"] = "[flujo] L22A1 (¿cuánto? servicios) visible si L22=true"
        if r.get("origen") == "L22" and r.get("afecta") == "L22E" and r.get("valor_trigger") == "":
            r["afecta"] = "L22B"; r["descripcion"] = "[flujo] L22B (navidad) visible tras L22"
    for o, a in CADENA[1:]:  # L22B->L22C, L22C->L22D, L22D->L22E
        R.append({"origen": o, "valor_trigger": "", "accion": "HABILITAR", "afecta": a,
                  "descripcion": f"[flujo] {a} visible tras {o}"})
    for o, a in CUANTOS[1:]:  # cuántos de navidad/vacaciones/viáticos/accidentes
        R.append({"origen": o, "valor_trigger": "true", "accion": "HABILITAR", "afecta": a,
                  "descripcion": f"[flujo] {a} (¿cuánto?) visible si {o}=true"})
    FIX.write_text(json.dumps(d, ensure_ascii=False, indent=ind) + "\n", encoding="utf-8", newline="\n")
    print(f"  fixture: +{len(nuevas)+1} preguntas, cadena de primas completa.")


def patch_bundle(check=False):
    d = json.loads(BUN.read_text(encoding="utf-8"))
    cap = next(c for c in d["capitulos"] if c["codigo"] == CAP)
    P = cap["preguntas"]
    if any(p["codigo_externo"] == "L22B" for p in P):
        print("  bundle: ya tiene L22B (idempotente)."); return
    if check:
        print("  bundle: mismo cambio que el fixture con ids compartidos."); return
    ex = next(p for p in P if p["codigo_externo"] == "L22C1")
    ex["codigo_externo"] = "L22A1"
    idx = P.index(ex)
    P[idx + 1: idx + 1] = [preg_bundle(*n) for n in NUEVAS]
    ie = next(i for i, p in enumerate(P) if p["codigo_externo"] == "L22E")
    P[ie + 1: ie + 1] = [preg_bundle(*L22E1)]
    for i, p in enumerate(P):
        p["orden"] = i + 1
    # ids por codigo (existentes + nuevos)
    idpc = {p["codigo_externo"]: p["id"] for p in P}
    R = d["reglas"]
    for r in R:
        if r.get("pregunta_origen_codigo") == "L22" and r.get("pregunta_afectada_codigo") == "L22C1":
            r["pregunta_afectada_codigo"] = "L22A1"; r["pregunta_afectada"] = idpc["L22A1"]
        if (r.get("pregunta_origen_codigo") == "L22" and r.get("pregunta_afectada_codigo") == "L22E"
                and r.get("valor_trigger") == ""):
            r["pregunta_afectada_codigo"] = "L22B"; r["pregunta_afectada"] = idpc["L22B"]
    def add(o, a, trig):
        R.append({"id": rid(o, a), "pregunta_origen": idpc[o], "pregunta_origen_codigo": o,
                  "valor_trigger": trig, "expresion_origen": "", "pregunta_afectada": idpc[a],
                  "pregunta_afectada_codigo": a, "capitulo_afectado": None, "accion": "HABILITAR"})
    for o, a in CADENA[1:]:
        add(o, a, "")
    for o, a in CUANTOS[1:]:
        add(o, a, "true")
    BUN.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"  bundle: +{len(NUEVAS)+1} preguntas + reglas.")


if __name__ == "__main__":
    chk = "--check" in sys.argv
    print("PRIMAS J. Fuerza de Trabajo — Territorial")
    patch_fixture(chk)
    patch_bundle(chk)
    print("Listo." if not chk else "CHECK (sin escribir).")
