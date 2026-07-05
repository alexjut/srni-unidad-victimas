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
            r["valor_trigger"] = "1"
            r["descripcion"] = ("[flujo] B27 (tipo territorio) visible si B26=Si (A30=1) "
                                "[obs funcional: 26=No no debe desplegar 27]")
            log("P26/P27 (B26/B27): B17 visible si A30=1 (territorio colectivo=Si), ya no por Z4")


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


LOTES = [
    ("LOTE 1 — skip-logic", [lote1_j2_l2, lote1_d7_d8_etnico, lote1_b26_b27_territorio]),
    ("LOTE 2 — preguntas faltantes",
     [lote2_observaciones, lote2_estrato, lote2_cursos_subcampos, lote2_k35_cual]),
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # consola Windows (cp1252) → utf-8
    except Exception:
        pass
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)

    d["instrumento_version"] = "V8"

    for nombre, fns in LOTES:
        for fn in fns:
            fn(d)

    with io.open(DST, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    print(f"Generado: {os.path.relpath(DST, BASE)}")
    print(f"Versión: {d['instrumento_version']} | preguntas={len(d['preguntas'])} | reglas={len(reglas(d))}")
    print(f"Cambios aplicados ({len(CAMBIOS)}):")
    for c in CAMBIOS:
        print(f"  - {c}")


if __name__ == "__main__":
    main()
