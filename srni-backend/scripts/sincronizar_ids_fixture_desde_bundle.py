# -*- coding: utf-8 -*-
"""
Sincroniza los UUID de PREGUNTA de cada fixture con los del bundle móvil ya
empaquetado en el APK (match por `codigo_externo`).

Motivo: el APK sirve bundles con UUID fijos. El backend (vía cargar_perfil) solo
respetaba UUID en Territorial; los demás fixtures no traían `id` → al cargar tomaban
uuid4 aleatorio ≠ al del bundle → el backend rechazaba las respuestas del móvil con
HTTP 400. Fijando en el fixture el MISMO id que el bundle, `cargar_perfil` reproduce
exactamente los UUID del APK y la sincronización funciona sin reconstruir el APK.

Reglas: NO se tocan (cargar_perfil las borra y recrea por codigo; RespuestaEncuesta
no referencia reglas). Opciones: NO se tocan (el móvil envía `valor`, no el id de opción).

Idempotente. Uso:
    python scripts/sincronizar_ids_fixture_desde_bundle.py           # aplica
    python scripts/sincronizar_ids_fixture_desde_bundle.py --check   # solo reporta
"""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX_DIR = ROOT / "srni-backend" / "apps" / "formulario" / "fixtures"
BUN_DIR = ROOT / "srni-mobile" / "assets" / "instrumentos"
NS = uuid.UUID("5c1a0000-0000-5c1a-0000-000000000001")  # mismo namespace del patch B2

PARES = [
    ("perfil_territorial_v7.json",       "territorial_v7.json"),
    ("perfil_buenaventura_v7.json",      "buenaventura_v7.json"),
    ("perfil_san_andres_v7.json",        "san_andres_v7.json"),
    ("perfil_urbano_etnico_v1.json",     "urbano_etnico_v1.json"),
    ("perfil_asistencia_v8.json",        "asistencia_v8.json"),
    ("perfil_rural_etnico_v1.json",      "rural_etnico_v1.json"),
    ("perfil_telefonico_v8.json",        "telefonico_v8.json"),
    ("perfil_victimas_exterior_v1.json", "victimas_exterior_v1.json"),
]


def _detectar_indent(texto: str) -> int:
    for linea in texto.split("\n")[1:]:
        despojada = linea.lstrip(" ")
        if despojada:
            return len(linea) - len(despojada)
    return 1


def _bundle_ids(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {p["codigo_externo"]: p["id"]
            for c in d["capitulos"] for p in c["preguntas"] if p.get("id")}


def procesar(pf: str, pb: str, aplicar: bool) -> tuple:
    fpath = FIX_DIR / pf
    texto = fpath.read_text(encoding="utf-8")
    indent = _detectar_indent(texto)
    d = json.loads(texto)
    bmap = _bundle_ids(BUN_DIR / pb)
    perfil = pb.rsplit(".", 1)[0]

    desde_bundle = 0      # id tomado del bundle (coincide con APK)
    deterministas = 0     # pregunta solo-fixture → id uuid5 estable
    cambiados = 0
    for p in d["preguntas"]:
        cod = p["codigo_externo"]
        if cod in bmap:
            nuevo = bmap[cod]
            desde_bundle += 1
        else:
            nuevo = str(uuid.uuid5(NS, f"{perfil}:{cod}"))
            deterministas += 1
        if p.get("id") != nuevo:
            cambiados += 1
            if aplicar:
                p["id"] = nuevo

    solo_bundle = sorted(set(bmap) - {p["codigo_externo"] for p in d["preguntas"]})
    if aplicar:
        fpath.write_text(json.dumps(d, ensure_ascii=False, indent=indent) + "\n",
                         encoding="utf-8", newline="\n")
    return desde_bundle, deterministas, cambiados, solo_bundle


def main() -> None:
    aplicar = "--check" not in sys.argv
    print(f"{'fixture':<28}{'bundle-id':>10}{'determin.':>10}{'cambios':>9}  gaps(solo en bundle)")
    total_gaps = 0
    for pf, pb in PARES:
        db, det, ch, solo = procesar(pf, pb, aplicar)
        total_gaps += len(solo)
        gaps = ",".join(solo) if solo else "-"
        print(f"{pf:<28}{db:>10}{det:>10}{ch:>9}  {gaps}")
    accion = "APLICADO" if aplicar else "CHECK (sin escribir)"
    print(f"\n{accion}. Gaps totales (preguntas en bundle sin fixture): {total_gaps}")
    if total_gaps:
        print("  -> esas preguntas NO tendran contraparte en el backend (perfil no critico).")


if __name__ == "__main__":
    main()
