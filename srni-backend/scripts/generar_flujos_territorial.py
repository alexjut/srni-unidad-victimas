#!/usr/bin/env python3
"""
Genera (best-effort) las reglas de skip-logic del Territorial a partir del patrón
"pregunta FILTRO (Sí/No) seguida de pregunta(s) de DETALLE" en cada capítulo.

Heurística: una pregunta cuyo texto empieza con ¿Cuál/¿Qué tipo/¿Cuánt/¿A qué/
¿En qué/¿Dónde… (DETALLE) depende de la pregunta BOOLEAN o LISTA-Sí/No
inmediatamente anterior (FILTRO): se muestra solo si el FILTRO = Sí.

Trigger correcto por tipo de filtro:
  - BOOLEAN  → 'true'  (el móvil guarda true/false)
  - LISTA    → valor de la opción 'Sí' (típicamente '1')

NO es exhaustivo ni infalible: las reglas se marcan para VALIDACIÓN del área
funcional. Solo cubre dependencias por respuesta (no demográficas/étnicas).

Uso:
    python scripts/generar_flujos_territorial.py            # inspección
    python scripts/generar_flujos_territorial.py --escribir # agrega reglas al fixture
"""
import sys, json, re, unicodedata
from pathlib import Path

FIX = Path(__file__).resolve().parents[1] / "apps/formulario/fixtures/perfil_territorial_v7.json"

DETALLE_PREFIJOS = ('cual', 'cuales', 'que tipo', 'cuant', 'a que', 'en que',
                    'donde', 'ingrese nombre', 'indique cual')


def norm(s):
    return unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower().strip()


def es_detalle(texto):
    t = norm(texto)
    return any(t.startswith(p) for p in DETALLE_PREFIJOS)


def valor_si(opciones):
    """Valor de la opción 'Sí' de una LISTA; '1' por defecto."""
    for o in opciones:
        if norm(o['etiqueta']) in ('si', 'si '):
            return o['valor']
    return '1'


def main():
    escribir = '--escribir' in sys.argv
    d = json.loads(FIX.read_text(encoding='utf-8'))
    por_cap = {}
    for p in d['preguntas']:
        por_cap.setdefault(p['capitulo_codigo'], []).append(p)

    reglas = []
    for cap, ps in por_cap.items():
        ps = sorted(ps, key=lambda x: x['orden'])
        for i, p in enumerate(ps):
            if not es_detalle(p['texto']):
                continue
            # buscar el filtro: la pregunta anterior que sea BOOLEAN o LISTA-Sí/No
            for j in range(i - 1, max(i - 3, -1), -1):
                f = ps[j]
                if f['tipo'] == 'BOOLEAN':
                    reglas.append((f['codigo_externo'], 'true', p['codigo_externo'], cap, f['texto'], p['texto']))
                    break
                if f['tipo'] == 'LISTA':
                    etis = {norm(o['etiqueta']) for o in f['opciones']}
                    if 'si' in etis and 'no' in etis:
                        reglas.append((f['codigo_externo'], valor_si(f['opciones']), p['codigo_externo'], cap, f['texto'], p['texto']))
                    break

    # Reporte
    print(f"Reglas HABILITAR propuestas (filtro Sí → detalle): {len(reglas)}\n")
    capant = None
    for orig, trig, afec, cap, ftxt, dtxt in reglas:
        if cap != capant:
            print(f"--- Capítulo {cap} ---"); capant = cap
        print(f"  {orig} = {trig!r} → mostrar {afec}")
        print(f"      filtro:  {ftxt[:55]}")
        print(f"      detalle: {dtxt[:55]}")

    if escribir:
        d.setdefault('reglas_skip_logic', [])
        existentes = {(r.get('origen'), r.get('afecta'), r.get('accion')) for r in d['reglas_skip_logic']}
        n = 0
        for orig, trig, afec, cap, ftxt, dtxt in reglas:
            k = (orig, afec, 'HABILITAR')
            if k in existentes:
                continue
            d['reglas_skip_logic'].append({
                'origen': orig, 'valor_trigger': trig, 'accion': 'HABILITAR',
                'afecta': afec,
                'descripcion': f'[auto/validar] {afec} visible solo si {orig}=Sí',
            })
            existentes.add(k); n += 1
        FIX.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
        print(f"\nOK: {n} reglas agregadas al fixture. Total reglas: {len(d['reglas_skip_logic'])}")
    else:
        print("\n(inspección — usar --escribir para agregar al fixture)")


if __name__ == '__main__':
    main()
