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


LOTES = [
    ("LOTE 1 — skip-logic", [lote1_j2_l2, lote1_d7_d8_etnico, lote1_b26_b27_territorio]),
    ("LOTE 2 — preguntas faltantes", [lote2_observaciones]),
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
