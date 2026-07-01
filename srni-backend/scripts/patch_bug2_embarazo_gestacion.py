# -*- coding: utf-8 -*-
"""
Reconciliación Bug 2 — condicional de embarazo + ajuste lactante (cap. B DATOS BÁSICOS).

Fuente de verdad: Manual de Usuario Vivanto — Perfil Asistencia (520.06.06-1, v01).
Idempotente: patchea los 4 fixtures (fuente de verdad) y sus bundles móviles.

Cambios aplicados por perfil (Buenaventura, San Andrés, Territorial, Urbano-Étnico):
  - B2 (embarazo): regla HABILITAR solo `sexo == '2'` (SIN edad — el manual muestra la
    pregunta a toda mujer; menores de 12 quedan como observación).
  - B2 opciones: "Sí, ¿Cuántas?" / "No" (elimina la opción huérfana TEXTO/"Campo Abierto").
  - B2_CANT: nueva pregunta hija NUMERICO (solo_numerico, SIN rango), HABILITAR si B2 == '1'.
  - B2A (lactante): DESVIACIÓN avalada por líder funcional — se quita el tope 50:
    `sexo == '2' and edad >= 12`.

IMPORTANTE: los generadores `generar_*_desde_diccionario.py` derivan del Excel y NO llevan
la curación manual (`[B manual]`) que vive en los fixtures. Si se vuelve a correr un generador
con --escribir, re-ejecutar ESTE script para reconciliar.

Uso:
    python scripts/patch_bug2_embarazo_gestacion.py            # aplica
    python scripts/patch_bug2_embarazo_gestacion.py --check    # solo verifica (no escribe)
"""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # .../unidad-victima
FIX_DIR = ROOT / "srni-backend" / "apps" / "formulario" / "fixtures"
BUN_DIR = ROOT / "srni-mobile" / "assets" / "instrumentos"
NS = uuid.UUID("5c1a0000-0000-5c1a-0000-000000000001")  # namespace fijo para uuid5

PERFILES = [
    ("perfil_buenaventura_v7.json", "buenaventura_v7.json"),
    ("perfil_san_andres_v7.json",   "san_andres_v7.json"),
    ("perfil_territorial_v7.json",  "territorial_v7.json"),
    ("perfil_urbano_etnico_v1.json", "urbano_etnico_v1.json"),
]

EXPR_B2 = "sexo == '2' and edad >= 12"
EXPR_B2A = "sexo == '2' and edad >= 12"
DESC_B2 = "[desviacion avalada por lider funcional Alejandro] embarazo: mujer 12+ (el manual 520.06.06-1 no pone piso; menores de 12 quedaban como observacion)"
DESC_B2A = "[desviacion avalada por lider funcional] lactante: mujer 12+ SIN tope 50 (una mujer puede lactar tras los 50)"
DESC_CANT = "[flujo] '¿Cuántas?' (gestación) visible si B2 = Sí (1)"
TEXTO_CANT = "¿Cuántas?"
NOPREG_CANT = "B21A"


def _detectar_indent(texto: str) -> int:
    """Indent (nº de espacios) del fixture, leído de su 2ª línea. Territorial usa
    indent=2; los generados por generar_*_desde_diccionario.py usan indent=1."""
    for linea in texto.split("\n")[1:]:
        despojada = linea.lstrip(" ")
        if despojada:
            return len(linea) - len(despojada)
    return 1


def patch_fixture(path: Path) -> None:
    texto = path.read_text(encoding="utf-8")
    indent = _detectar_indent(texto)
    d = json.loads(texto)
    preguntas = d["preguntas"]
    b2 = next(p for p in preguntas if p["codigo_externo"] == "B2")
    b2_orden = b2["orden"]
    cap = b2["capitulo_codigo"]

    old = {o["valor"]: o for o in b2.get("opciones", [])}
    b2["tipo"] = "LISTA"
    b2["opciones"] = [
        {"valor": "1", "etiqueta": "Sí, ¿Cuántas?",
         "id_resp_vivanto": old.get("1", {}).get("id_resp_vivanto"), "orden": 1},
        {"valor": "2", "etiqueta": "No",
         "id_resp_vivanto": old.get("2", {}).get("id_resp_vivanto"), "orden": 2},
    ]

    if not any(p["codigo_externo"] == "B2_CANT" for p in preguntas):
        for p in preguntas:
            if p["capitulo_codigo"] == cap and p["orden"] > b2_orden:
                p["orden"] += 1
        b2cant = {
            "no_pregunta": NOPREG_CANT, "codigo_externo": "B2_CANT", "id_preg": None,
            "capitulo_codigo": cap, "texto": TEXTO_CANT, "tipo": "NUMERICO",
            "nivel": "PERSONA", "obligatoria": False, "orden": b2_orden + 1,
            "es_precargada": False, "fuente_precarga": "",
            "validaciones": {"solo_numerico": True}, "opciones": [],
        }
        idx = next(i for i, p in enumerate(preguntas) if p["codigo_externo"] == "B2")
        preguntas.insert(idx + 1, b2cant)

    reglas = d.setdefault("reglas_skip_logic", [])
    for r in reglas:
        if r.get("afecta") == "B2" and (r.get("origen_expr") or "").strip():
            r["origen_expr"] = EXPR_B2
            r["descripcion"] = DESC_B2
        if r.get("afecta") == "B2A":
            r["origen_expr"] = EXPR_B2A
            r["descripcion"] = DESC_B2A
    if not any(r.get("afecta") == "B2_CANT" for r in reglas):
        reglas.append({"origen": "B2", "valor_trigger": "1", "accion": "HABILITAR",
                       "afecta": "B2_CANT", "descripcion": DESC_CANT})

    path.write_text(json.dumps(d, ensure_ascii=False, indent=indent) + "\n",
                    encoding="utf-8", newline="\n")


def patch_bundle(path: Path, code: str) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    cap_b = next(c for c in d["capitulos"] if c["codigo"] == "B")
    pregs = cap_b["preguntas"]
    b2 = next(p for p in pregs if p["codigo_externo"] == "B2")
    b2_orden = b2["orden"]
    b2cant_id = str(uuid.uuid5(NS, f"{code}:B2_CANT"))
    rule_id = str(uuid.uuid5(NS, f"{code}:rule:B2_CANT"))

    old = {o["valor"]: o for o in b2.get("opciones", [])}
    b2["tipo"] = "LISTA"
    b2["opciones"] = [
        {"id": old.get("1", {}).get("id") or str(uuid.uuid5(NS, f"{code}:B2:1")),
         "valor": "1", "etiqueta": "Sí, ¿Cuántas?", "orden": 1, "finaliza_capitulo": False},
        {"id": old.get("2", {}).get("id") or str(uuid.uuid5(NS, f"{code}:B2:2")),
         "valor": "2", "etiqueta": "No", "orden": 2, "finaliza_capitulo": False},
    ]

    if not any(p["codigo_externo"] == "B2_CANT" for p in pregs):
        for p in pregs:
            if p["orden"] > b2_orden:
                p["orden"] += 1
        b2cant = {
            "id": b2cant_id, "codigo_externo": "B2_CANT", "no_pregunta": NOPREG_CANT,
            "texto": TEXTO_CANT, "descripcion_ayuda": "", "tipo": "NUMERICO",
            "nivel": "PERSONA", "orden": b2_orden + 1, "obligatoria": False,
            "activa": True, "es_precargada": False,
            "validaciones": {"solo_numerico": True}, "opciones": [],
        }
        idx = next(i for i, p in enumerate(pregs) if p["codigo_externo"] == "B2")
        pregs.insert(idx + 1, b2cant)

    reglas = d.setdefault("reglas", [])
    for r in reglas:
        if r.get("pregunta_afectada_codigo") == "B2" and (r.get("expresion_origen") or "").strip():
            r["expresion_origen"] = EXPR_B2
        if r.get("pregunta_afectada_codigo") == "B2A":
            r["expresion_origen"] = EXPR_B2A
    if not any(r.get("pregunta_afectada_codigo") == "B2_CANT" for r in reglas):
        reglas.append({
            "id": rule_id, "pregunta_origen": b2["id"], "pregunta_origen_codigo": "B2",
            "valor_trigger": "1", "expresion_origen": "",
            "pregunta_afectada": b2cant_id, "pregunta_afectada_codigo": "B2_CANT",
            "capitulo_afectado": None, "accion": "HABILITAR",
        })

    path.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8", newline="\n")


def check() -> int:
    problemas = 0
    for fix, bun in PERFILES:
        d = json.loads((BUN_DIR / bun).read_text(encoding="utf-8"))
        cap_b = next(c for c in d["capitulos"] if c["codigo"] == "B")
        pregs = cap_b["preguntas"]
        b2 = next(p for p in pregs if p["codigo_externo"] == "B2")
        ops = [(o["valor"], o["etiqueta"]) for o in b2["opciones"]]
        tiene_cant = any(p["codigo_externo"] == "B2_CANT" for p in pregs)
        regla_cant = any(r.get("pregunta_afectada_codigo") == "B2_CANT" for r in d["reglas"])
        ok = ops == [("1", "Sí, ¿Cuántas?"), ("2", "No")] and tiene_cant and regla_cant
        print(f"  {bun:<24} ops={ops} B2_CANT={tiene_cant} regla={regla_cant} -> {'OK' if ok else 'FALLA'}")
        problemas += 0 if ok else 1
    return problemas


def main() -> None:
    if "--check" in sys.argv:
        sys.exit(1 if check() else 0)
    for fix, bun in PERFILES:
        code = bun.rsplit("_", 1)[0]  # buenaventura_v7 -> buenaventura
        patch_fixture(FIX_DIR / fix)
        patch_bundle(BUN_DIR / bun, code)
        print(f"OK {fix}  +  {bun}")
    print("Reconciliación aplicada.")


if __name__ == "__main__":
    main()
