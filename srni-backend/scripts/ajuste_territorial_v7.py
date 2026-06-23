#!/usr/bin/env python3
"""
Ajuste del instrumento TERRITORIAL V7 (in-place) — oleada de cambios al
instrumento de caracterización (2026-06).

Edita el FIXTURE backend perfil_territorial_v7.json (fuente de verdad junto a los
modelos). Después: `cargar_perfil` + `exportar_a_mobile` regeneran el bundle del
APK. Idempotente: si un cambio ya está aplicado, no lo duplica.

Todos los cambios son de DATOS (definición del instrumento):
 1. Cap B (DATOS BÁSICOS): + "Novedades en el RUV" (LISTA 4 op) + "¿Hace cuántos
    años vive en el municipio?" (NUMERICO).
 2. Cap C (VIVIENDA): textos C7-C11 → "¿El hogar cuenta con el servicio de [x]?";
    sub-campo condicional "¿Estrato?" SOLO en C7 (energía) vía regla HABILITAR;
    texto de C21 (factores del conflicto → factores en general, últimos 2 años).
 3. Cap D (RETORNOS): desactiva las 2 Sí/No (retorno/reubicación); agrega
    "Observaciones iniciales" (P1, texto) y "¿En la actualidad, respecto al
    derecho del retorno o reubicación?" (LISTA 3 op, P2).
 4. Cap G (SALUD): + "¿Su IPS primaria…?" (Sí/No).
 5. Cap JA (ALIMENTACIÓN): sub-campo "¿Cuántos días fueron?" (NUMERICO) en las 14
    preguntas de consumo (J1A-J1N) vía reglas HABILITAR.
 6. Cap K (PERFIL SOCIOLABORAL): amplía texto de PL14 (…o ha participado en alguna?).
"""
import json
from pathlib import Path

FIX = Path(__file__).resolve().parents[2] / "srni-backend/apps/formulario/fixtures/perfil_territorial_v7.json"

data = json.loads(FIX.read_text(encoding="utf-8"))
P = data["preguntas"]
R = data.setdefault("reglas_skip_logic", [])
by = {p["codigo_externo"]: p for p in P}


def nueva(cap, cod, no, texto, tipo, nivel, orden, obligatoria, opciones=None, val=None):
    return {
        "no_pregunta": no, "codigo_externo": cod, "id_preg": None,
        "capitulo_codigo": cap, "texto": texto, "tipo": tipo, "nivel": nivel,
        "obligatoria": obligatoria, "orden": orden, "es_precargada": False,
        "fuente_precarga": "", "validaciones": val or {}, "activa": True,
        "opciones": opciones or [],
    }


def opt(v, et, o):
    return {"valor": str(v), "etiqueta": et, "orden": o}


# ── 1. Cambios de texto (in-place, idempotentes) ────────────────────────────
TEXTOS = {
    "D8A": "¿El hogar cuenta con el servicio de energía eléctrica?",
    "D8B": "¿El hogar cuenta con el servicio de alcantarillado?",
    "D8C": "¿El hogar cuenta con el servicio de acueducto?",
    "D8D": "¿El hogar cuenta con el servicio de gas natural conectado a red pública?",
    "D8E": "¿El hogar cuenta con el servicio de recolección de basuras?",
    "C17A": "En los últimos dos años, ¿por cuáles de los siguientes factores se ha visto afectada esta zona?",
    "PL14": "¿Alguna vez ha llevado a cabo una iniciativa de negocio propio o ha participado en alguna?",
}
for cod, txt in TEXTOS.items():
    by[cod]["texto"] = txt

# ── 2. Cap D: desactivar las dos Sí/No (las reemplaza la LISTA de 3 opciones) ─
by["E1A"]["activa"] = False  # D2 ¿en proceso de retorno?
by["E1B"]["activa"] = False  # D3 ¿en proceso de reubicación?

# ── 3. Preguntas nuevas ─────────────────────────────────────────────────────
nuevas = []


def add(p):
    if p["codigo_externo"] not in by:
        nuevas.append(p)
        by[p["codigo_externo"]] = p


# Cap B (PERSONA)
add(nueva("B", "A_NOVEDAD_RUV", "B48", "Novedades en el RUV", "LISTA", "PERSONA", 47, False,
          [opt(1, "Ninguno", 1), opt(2, "Actualización fecha de nacimiento", 2),
           opt(3, "Actualización de documento de identidad", 3),
           opt(4, "Actualización de nombres y/o Apellidos", 4)]))
add(nueva("B", "B_ANIOS_MPIO", "B49",
          "¿Hace cuántos años vive en el municipio? (Si lleva menos de 1 año registre 00)",
          "NUMERICO", "PERSONA", 48, False, val={"min": 0, "max": 120}))

# Cap C (HOGAR) — estrato condicional; orden temporal alto, se renumera
add(nueva("C", "D8A_ESTRATO", "C7E", "¿Estrato?", "NUMERICO", "HOGAR", 999, True, val={"min": 0, "max": 6}))

# Cap D (HOGAR) — observaciones + lista 3 opciones; orden 0 = quedan primeras
add(nueva("D", "D_OBS_INI", "D1N", "Observaciones iniciales", "TEXTO_LARGO", "HOGAR", 0, False))
add(nueva("D", "D_RETORNO_ACT", "D2N",
          "¿En la actualidad, respecto al derecho del retorno o reubicación?", "LISTA", "HOGAR", 0, False,
          [opt(1, "Ya regresó al municipio que abandonó a causa del desplazamiento forzado", 1),
           opt(2, "Ya se reubicó en un municipio diferente al que abandonó a causa del desplazamiento forzado", 2),
           opt(3, "Ninguna de las anteriores", 3)]))

# Cap G (PERSONA) — IPS primaria
add(nueva("G", "G_IPS_PRIMARIA", "G8",
          "¿Su IPS primaria le brinda atención en salud en el municipio de residencia?",
          "BOOLEAN", "PERSONA", 8, False))

# Cap JA (HOGAR) — 14 sub-campos "¿Cuántos días fueron?"
CONSUMO = ["J1A", "J1B", "J1C", "J1D", "J1E", "J1F", "J1T", "J1G", "J1H", "J1J", "J1K", "J1L", "J1M", "J1N"]
for cod in CONSUMO:
    add(nueva("JA", cod + "_DIAS", by[cod]["no_pregunta"] + "D", "¿Cuántos días fueron?",
              "NUMERICO", "HOGAR", 999, False, val={"min": 1, "max": 7}))

P.extend(nuevas)


# ── 4. Renumerar capítulos con inserciones (C, D, JA) ───────────────────────
def renumerar(cap, despues):
    """Reasigna orden 1..N a las preguntas ACTIVAS del capítulo, insertando los
    sub-campos de `despues` justo detrás de su ancla."""
    insertados = {c for lst in despues.values() for c in lst}
    activos = [p for p in P if p["capitulo_codigo"] == cap and p.get("activa", True)]
    activos.sort(key=lambda p: p["orden"])
    seq = []
    for p in activos:
        if p["codigo_externo"] in insertados:
            continue
        seq.append(p)
        for c in despues.get(p["codigo_externo"], []):
            seq.append(by[c])
    for i, p in enumerate(seq, 1):
        p["orden"] = i


renumerar("C", {"D8A": ["D8A_ESTRATO"]})
renumerar("D", {})  # las 2 nuevas (orden 0) primero; el resto detrás
renumerar("JA", {c: [c + "_DIAS"] for c in CONSUMO})


# ── 5. Reglas HABILITAR (sub-campos condicionales) ──────────────────────────
def hab(origen, afecta, desc):
    return {"origen": origen, "valor_trigger": "true", "accion": "HABILITAR",
            "afecta": afecta, "descripcion": desc}


reglas_nuevas = [hab("D8A", "D8A_ESTRATO", "Estrato visible solo si el hogar tiene energía eléctrica")]
for cod in CONSUMO:
    reglas_nuevas.append(hab(cod, cod + "_DIAS", f"Días de consumo visibles solo si consumió ({cod})"))

vistas = {(r.get("origen"), r.get("afecta"), r.get("accion")) for r in R}
for nr in reglas_nuevas:
    k = (nr["origen"], nr["afecta"], nr["accion"])
    if k not in vistas:
        R.append(nr)
        vistas.add(k)

# ── Guardar ─────────────────────────────────────────────────────────────────
FIX.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"OK fixture actualizado: {FIX.name}")
print(f"  preguntas nuevas agregadas: {len(nuevas)}")
print(f"  preguntas totales: {len(P)}")
print(f"  reglas skip-logic totales: {len(R)}")
