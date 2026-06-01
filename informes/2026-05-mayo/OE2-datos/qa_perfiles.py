"""
QA detallado perfil por perfil — Sprint 20.

Para cada uno de los 8 instrumentos, contesta 3 preguntas:
  1. Cuántas preguntas activas tiene en BD vs cuántas vienen en el bundle.
  2. Cuántas preguntas son problemáticas: LISTA/RADIO/LISTA_MULTIPLE/COMBO sin opciones.
  3. Distribución por nivel (HOGAR vs PERSONA) y por tipo.

Salida: docs/qa-perfiles-sprint20.md con tabla por instrumento.

Uso:
    python scripts/qa_perfiles.py
"""
import os
import sys
import json
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'srni.settings.development')
import django
django.setup()

from apps.formulario.models import Instrumento, Pregunta, Capitulo


REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLES_DIR = REPO_ROOT / 'srni-mobile' / 'assets' / 'instrumentos'
SALIDA = REPO_ROOT / 'docs' / 'qa-perfiles-sprint20.md'

# Tipos que requieren tener opciones cargadas para renderizar correctamente
TIPOS_CON_OPCIONES = {'LISTA', 'LISTA_MULTIPLE', 'RADIO', 'COMBO_DINAMICO'}


def analizar_bundle(path: Path) -> dict:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    capitulos = data['capitulos']
    total = 0
    problemas = []
    por_tipo = Counter()
    por_nivel = Counter()
    sin_opciones = []
    cap_vacios = []
    for c in capitulos:
        pregs = c.get('preguntas', [])
        if not pregs:
            cap_vacios.append(c['codigo'])
        for p in pregs:
            total += 1
            por_tipo[p['tipo']] += 1
            por_nivel[p['nivel']] += 1
            if p['tipo'] in TIPOS_CON_OPCIONES and len(p.get('opciones', [])) == 0:
                sin_opciones.append(f"{c['codigo']}/{p.get('no_pregunta','?')}-{p.get('codigo_externo','?')}({p['tipo']})")
    return {
        'caps': len(capitulos),
        'total': total,
        'por_tipo': dict(por_tipo),
        'por_nivel': dict(por_nivel),
        'sin_opciones': sin_opciones,
        'cap_vacios': cap_vacios,
        'reglas': len(data.get('reglas', [])),
    }


def analizar_bd(instr: Instrumento) -> dict:
    activas = Pregunta.objects.filter(
        capitulo__instrumento=instr, activa=True,
    )
    inactivas = Pregunta.objects.filter(
        capitulo__instrumento=instr, activa=False,
    )
    por_tipo = Counter(activas.values_list('tipo', flat=True))
    por_nivel = Counter(activas.values_list('nivel', flat=True))
    return {
        'activas': activas.count(),
        'inactivas': inactivas.count(),
        'por_tipo': dict(por_tipo),
        'por_nivel': dict(por_nivel),
    }


def cargar_bundle_index() -> dict:
    """Mapa codigo → ruta del bundle."""
    idx = json.loads((BUNDLES_DIR / 'index.json').read_text(encoding='utf-8'))
    return {item['codigo']: BUNDLES_DIR / item['archivo'] for item in idx}


def main():
    bundles = cargar_bundle_index()
    lineas = []
    lineas.append('# QA detallado perfil por perfil — Sprint 20\n')
    lineas.append('**Fecha:** 2026-05-26\n')
    lineas.append('**Generado automáticamente** por `srni-backend/scripts/qa_perfiles.py`\n')
    lineas.append('')
    lineas.append('Compara para cada instrumento: BD ↔ Bundle ↔ Tipos problemáticos.\n')

    # Tabla resumen
    lineas.append('## Resumen ejecutivo\n')
    lineas.append('| Instrumento | Caps | BD activas | Bundle | Coincide | Sin opciones | Hogar / Persona |')
    lineas.append('|---|---:|---:|---:|:-:|---:|---|')

    detalle = []

    for instr in Instrumento.objects.filter(activo=True).order_by('codigo'):
        bd = analizar_bd(instr)
        bundle_path = bundles.get(instr.codigo)
        if not bundle_path or not bundle_path.exists():
            lineas.append(f'| {instr.codigo} | ? | {bd["activas"]} | (sin bundle) | ❌ | ? | ? |')
            continue
        bd_bundle = analizar_bundle(bundle_path)
        coincide = '✅' if bd['activas'] == bd_bundle['total'] else '⚠️'
        n_sin_opc = len(bd_bundle['sin_opciones'])
        hogar = bd_bundle['por_nivel'].get('HOGAR', 0)
        persona = bd_bundle['por_nivel'].get('PERSONA', 0)
        lineas.append(
            f'| {instr.codigo} | {bd_bundle["caps"]} | {bd["activas"]} | '
            f'{bd_bundle["total"]} | {coincide} | {n_sin_opc} | {hogar} / {persona} |'
        )
        detalle.append((instr, bd, bd_bundle))

    lineas.append('')
    lineas.append('**Leyenda:** "Coincide" indica si el número de preguntas activas en BD coincide con las del bundle exportado.')
    lineas.append('"Sin opciones" cuenta preguntas LISTA/RADIO/LISTA_MULTIPLE/COMBO_DINAMICO sin opciones cargadas (no renderizan bien).\n')

    # Detalle por instrumento
    lineas.append('## Detalle por instrumento\n')
    for instr, bd, bundle in detalle:
        lineas.append(f'### {instr.codigo} — {instr.nombre} (v{instr.version})\n')
        lineas.append(f'- Capítulos: **{bundle["caps"]}**')
        lineas.append(f'- Preguntas activas en BD: **{bd["activas"]}** (inactivas: {bd["inactivas"]})')
        lineas.append(f'- Preguntas en bundle: **{bundle["total"]}**')
        if bd['activas'] != bundle['total']:
            lineas.append(f'- ⚠️ **Discrepancia: {abs(bd["activas"] - bundle["total"])} pregunta(s)**')
        lineas.append(f'- Reglas skip logic en bundle: {bundle["reglas"]}')
        lineas.append('')
        lineas.append('**Tipos de pregunta (bundle):**')
        for t, n in sorted(bundle['por_tipo'].items(), key=lambda x: -x[1]):
            lineas.append(f'  - `{t}`: {n}')
        lineas.append('')
        lineas.append('**Nivel (bundle):**')
        for nv, n in sorted(bundle['por_nivel'].items()):
            lineas.append(f'  - `{nv}`: {n}')
        if bundle['sin_opciones']:
            lineas.append('')
            lineas.append(f'**⚠️ Preguntas sin opciones cargadas ({len(bundle["sin_opciones"])}):**')
            for x in bundle['sin_opciones']:
                lineas.append(f'  - `{x}`')
        if bundle['cap_vacios']:
            lineas.append('')
            lineas.append(f'**⚠️ Capítulos sin preguntas:** {bundle["cap_vacios"]}')
        lineas.append('')

    # Resumen global de problemas
    lineas.append('## Problemas globales\n')
    total_sin_opc = sum(len(b['sin_opciones']) for _, _, b in detalle)
    total_caps_vacios = sum(len(b['cap_vacios']) for _, _, b in detalle)
    discrepancias = sum(1 for _, bd, b in detalle if bd['activas'] != b['total'])
    lineas.append(f'- Total preguntas sin opciones cargadas: **{total_sin_opc}**')
    lineas.append(f'- Total capítulos vacíos: **{total_caps_vacios}**')
    lineas.append(f'- Instrumentos con discrepancia BD↔Bundle: **{discrepancias}** / {len(detalle)}')
    lineas.append('')

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text('\n'.join(lineas), encoding='utf-8')
    print(f'Generado {SALIDA} ({SALIDA.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
