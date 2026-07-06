#!/usr/bin/env python3
"""
Porta el "barrido V8" de Territorial a otro perfil que COMPARTE códigos estándar
(Buenaventura, San Andrés, Urbano Étnico), operando sobre el FIXTURE (fuente de
verdad). NO toca el bundle: eso se regenera después con cargar_perfil +
exportar_a_mobile (ver reference_pipeline_instrumentos).

Aplica, solo cuando el código existe en el perfil destino:
  1. Cambios de TIPO (multi-select LISTA→LISTA_MULTIPLE; DIVIPOLA TEXTO→COMBO_DINAMICO).
  2. Reglas de skip-logic PORTABLES: reglas de Territorial cuyos dos extremos existen
     en el destino, la pareja (origen,afecta) aún no está, y el TEXTO de la pregunta
     origen coincide ≥0.85 con la de Territorial (guarda anti-falso-positivo, igual
     criterio que generar_buenaventura/san_andres).

Uso:
    .venv/Scripts/python.exe scripts/portar_barrido_v8_a_perfil.py <perfil_destino.json> [--escribir]
"""
import json, os, sys, io
from difflib import SequenceMatcher

# Windows: consola cp1252 rompe con Unicode → forzar utf-8 en stdout.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass


def _detectar_indent(path):
    """Preserva el indent del fixture (buenaventura/san_andres/urbano = 1, otros = 2)."""
    with open(path, encoding="utf-8") as f:
        f.readline()
        seg = f.readline()
    n = len(seg) - len(seg.lstrip(" "))
    return n or 2

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(BASE, "apps", "formulario", "fixtures")
TERR = os.path.join(FIX, "perfil_territorial_v8.json")

MULTISELECT = {"C6A", "C17A", "I10A", "I11A", "I1A1", "PL21A"}
DIVIPOLA = {"RR1", "RR6"}
COMBO_OPC = [{"valor": "", "etiqueta": "Departamento", "id_resp_vivanto": None, "orden": 1}]
UMBRAL = 0.85


def sim(a, b):
    return SequenceMatcher(None, (a or "").strip().lower(), (b or "").strip().lower()).ratio()


def main(destino_path, escribir):
    terr = json.load(open(TERR, encoding="utf-8"))
    dst = json.load(open(destino_path, encoding="utf-8"))

    terr_txt = {p["codigo_externo"]: p.get("texto", "") for p in terr["preguntas"]}
    dst_preg = {p["codigo_externo"]: p for p in dst["preguntas"]}
    dst_txt = {c: p.get("texto", "") for c, p in dst_preg.items()}

    # 1) cambios de tipo
    cambios_tipo = []
    for cod, p in dst_preg.items():
        if cod in MULTISELECT and p.get("tipo") == "LISTA":
            p["tipo"] = "LISTA_MULTIPLE"
            cambios_tipo.append(f"{cod} LISTA -> LISTA_MULTIPLE")
        elif cod in DIVIPOLA and p.get("tipo") != "COMBO_DINAMICO":
            prev = p.get("tipo")
            p["tipo"] = "COMBO_DINAMICO"
            p["opciones"] = [dict(o) for o in COMBO_OPC]
            cambios_tipo.append(f"{cod} {prev} -> COMBO_DINAMICO")

    # 2) reglas portables
    pares = set((r.get("origen"), r.get("afecta")) for r in dst["reglas_skip_logic"])
    portadas, saltadas = [], []
    for r in terr["reglas_skip_logic"]:
        o, a = r.get("origen"), r.get("afecta")
        if not o or not a:
            continue  # regla por expresión / nivel capítulo → no portar ciegamente
        if o not in dst_preg or a not in dst_preg:
            continue
        if (o, a) in pares:
            continue
        s = sim(terr_txt.get(o, ""), dst_txt.get(o, ""))
        if s < UMBRAL:
            saltadas.append(f"{o}->{a} (sim texto origen {s:.2f}<{UMBRAL})")
            continue
        nueva = {
            "origen": o,
            "valor_trigger": r.get("valor_trigger", ""),
            "accion": r.get("accion"),
            "afecta": a,
            "descripcion": "[portado V8] " + (r.get("descripcion", "") or f"{o}->{a}"),
        }
        dst["reglas_skip_logic"].append(nueva)
        pares.add((o, a))
        portadas.append(f"{o}--{r.get('accion')}[{r.get('valor_trigger')}]-->{a}")

    print(f"== {os.path.basename(destino_path)} ==")
    print(f"  Cambios de tipo: {len(cambios_tipo)}")
    for c in cambios_tipo:
        print("    -", c)
    print(f"  Reglas portadas: {len(portadas)}")
    for c in portadas:
        print("    +", c)
    print(f"  Reglas saltadas (guarda texto): {len(saltadas)}")
    for c in saltadas:
        print("    ·", c)
    print(f"  Total reglas destino ahora: {len(dst['reglas_skip_logic'])}")

    if escribir:
        indent = _detectar_indent(destino_path)
        json.dump(dst, open(destino_path, "w", encoding="utf-8"), ensure_ascii=False, indent=indent)
        print(f"  >> ESCRITO (indent={indent})")
    else:
        print("  (dry-run; usa --escribir para persistir)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], "--escribir" in sys.argv)
