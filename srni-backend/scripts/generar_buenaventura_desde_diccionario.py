#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el fixture del instrumento BUENAVENTURA V7 leyendo el diccionario oficial
(Excel) como ÚNICA fuente de verdad — códigos, textos, tipos y opciones EXACTOS.

Motivo: el bundle previo de Buenaventura estaba desalineado del diccionario
(códigos con sufijo `_bv` y un capítulo "BV. Condiciones Especiales" inventado
que NO está en el diccionario oficial). El diccionario oficial reusa los códigos
estándar (C1, C2, D5, D8*, B*...) compatibles con Territorial, más capítulos
propios: USO Y DISFRUTE DEL TERRITORIO (AT*) y SEGURIDAD JURÍDICA (ST*).

Mismo layout de 12 columnas que Territorial (col [10]=ESTADO, [11]=Fuente).
A diferencia de Territorial, varios capítulos (K, INFORMACIÓN ADICIONAL) aparecen
en ambas hojas → el nivel de cada pregunta se toma de la HOJA, no del capítulo.

Uso:
    python scripts/generar_buenaventura_desde_diccionario.py            # inspección
    python scripts/generar_buenaventura_desde_diccionario.py --escribir # escribe fixture
    python scripts/generar_buenaventura_desde_diccionario.py --muestra  # + muestra

┌───────────────────────────────────────────────────────────────────────────────┐
│ ⚠  ATENCIÓN: este generador deriva del EXCEL y NO incluye la curación manual del │
│    capítulo B (Bug 2): opciones limpias de B2, pregunta hija B2_CANT y reglas de │
│    embarazo/lactante ajustadas. Esa curación vive SOLO en el fixture.            │
│    → Tras cualquier `--escribir`, ejecutar OBLIGATORIAMENTE:                     │
│        python scripts/patch_bug2_embarazo_gestacion.py                           │
│    (idempotente; reconcilia fixture + bundle). Ver ese script para el detalle.   │
└───────────────────────────────────────────────────────────────────────────────┘
"""
import sys, json, re, unicodedata
from pathlib import Path
from difflib import SequenceMatcher
import openpyxl

XLSX = Path(r"D:/desarrollo/perfiles/Perfil Buenaventura_web y offline/Diccionario_de_datos__Entrevista de Caracterización_V7_perfilBuenaventura.xlsx")
OUT = Path(__file__).resolve().parents[1] / "apps/formulario/fixtures/perfil_buenaventura_v7.json"
TERR_FIX = Path(__file__).resolve().parents[1] / "apps/formulario/fixtures/perfil_territorial_v7.json"

# Nombre de capítulo (diccionario) → (código corto, orden). El nivel se toma de la hoja.
CAP_MAP = {
    'INFORMACIÓN PRECARGADA':         ('A', 1),
    'A. IDENTIFICACIÓN':              ('A', 1),
    'B.DATOS BASICOS':                ('B', 2),
    'C. VIVIENDA':                    ('C', 3),
    'D. RETORNO Y REUBICACIONES':     ('D', 4),
    'F. REUNIFICACIÓN FAMILIAR':      ('E', 5),
    'F. EDUCACIÓN':                   ('F', 6),
    'G. SALUD':                       ('G', 7),
    'H. REHABILITACIÓN':              ('H', 8),
    'J.ALIMENTACIÓN':                 ('JA', 9),
    'J. FUERZA DE TRABAJO':           ('JF', 10),
    'K. PERFIL SOCIOLABORAL':         ('K', 11),
    'L. FUERZA PÚBLICA':              ('L', 12),
    'USO Y DISFRUTE DEL TERRITORIO':  ('M', 13),
    'SEGURIDAD JURIDICA TERRITORIO':  ('ST', 14),
    'INFORMACIÓN ADICIONAL':          ('IF', 15),
    'T. CONTROL':                     ('T', 16),
}

CAP_NOMBRE = {
    'A': 'A. IDENTIFICACIÓN', 'B': 'B. DATOS BÁSICOS', 'C': 'C. VIVIENDA',
    'D': 'D. RETORNOS Y REUBICACIONES', 'E': 'E. REUNIFICACIÓN FAMILIAR',
    'F': 'F. EDUCACIÓN', 'G': 'G. SALUD', 'H': 'H. REHABILITACIÓN',
    'JA': 'J. ALIMENTACIÓN', 'JF': 'J. FUERZA DE TRABAJO', 'K': 'K. PERFIL SOCIOLABORAL',
    'L': 'L. FUERZA PÚBLICA', 'M': 'M. USO Y DISFRUTE DEL TERRITORIO',
    'ST': 'ST. SEGURIDAD JURÍDICA DEL TERRITORIO', 'IF': 'IF. INFORMACIÓN ADICIONAL',
    'T': 'T. CONTROL',
}

TIPOS_ESPECIALES = {'texto', 'numerico', 'numero', 'divipola', 'fecha',
                    'dd/mm/aaa', 'dd/mm/aaaa', 'moneda', 'alfanumerico', 'hora'}


def norm(s):
    if not s: return ''
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


def inferir_tipo(valores, opciones, texto):
    v = norm(valores)
    if v in ('texto', 'alfanumerico'):
        return 'TEXTO_LARGO' if 'observ' in norm(texto) else 'TEXTO'
    if v in ('numerico', 'numero', 'moneda'):
        return 'NUMERICO'
    if v in ('fecha', 'dd/mm/aaa', 'dd/mm/aaaa'):
        return 'FECHA'
    if v == 'divipola':
        return 'COMBO_DINAMICO'
    if opciones:
        etis = {norm(o['etiqueta']) for o in opciones}
        if etis and etis <= {'si', 'no'}:
            return 'BOOLEAN'
        return 'LISTA'
    return 'TEXTO'


def parsear_hoja(ws, nivel_hoja):
    """Layout 12 columnas con col [10]=ESTADO. El nivel de la pregunta = nivel_hoja."""
    preguntas = []
    cap_actual = None
    actual = None
    for row in ws.iter_rows(min_row=2, values_only=True):
        r = (list(row) + [''] * 12)[:12]
        cap, var, diag, preg, idp, desc, val, idresp, _fc, _fi, estado, fuente = r
        if cap and str(cap).strip():
            cap_actual = str(cap).strip()
        var = str(var).strip() if var else ''
        preg_txt = str(preg).strip() if preg else ''
        est = str(estado).strip().upper() if estado else ''

        if var and preg_txt:
            if est and est != 'ACTIVA':
                actual = None
                continue
            mapinfo = CAP_MAP.get(cap_actual)
            if not mapinfo:
                actual = None
                continue
            cod_cap, orden_cap = mapinfo
            actual = {
                'cap_codigo': cod_cap, 'cap_orden': orden_cap, 'nivel': nivel_hoja,
                'codigo_externo': var,
                'no_pregunta': str(diag).strip() if diag else '',
                'texto': preg_txt,
                'id_preg': int(idp) if isinstance(idp, (int, float)) else None,
                'valores': val, 'fuente': str(fuente).strip() if fuente else '',
                'opciones': [],
            }
            if desc and norm(val) not in TIPOS_ESPECIALES:
                actual['opciones'].append({
                    'valor': str(val).strip(), 'etiqueta': str(desc).strip(),
                    'id_resp_vivanto': int(idresp) if isinstance(idresp, (int, float)) else None,
                    'orden': 1,
                })
            preguntas.append(actual)
        elif actual is not None and desc and not preg_txt:
            actual['opciones'].append({
                'valor': str(val).strip() if val is not None else '',
                'etiqueta': str(desc).strip(),
                'id_resp_vivanto': int(idresp) if isinstance(idresp, (int, float)) else None,
                'orden': len(actual['opciones']) + 1,
            })
    # Multi-respuesta: renumerar valores 1..N solo si hay colisión.
    for q in preguntas:
        vals = [o['valor'] for o in q['opciones']]
        if vals and len(set(vals)) < len(vals):
            for i, o in enumerate(q['opciones'], 1):
                o['valor'] = str(i)
    return preguntas


def derivar_skip_logic(preguntas_fix):
    """Reusa las reglas de Territorial: Buenaventura comparte 270 códigos (mismo
    diccionario base). Una regla se conserva SOLO si su pregunta de origen y la
    afectada existen en Buenaventura con texto ~igual al de Territorial (evita
    arrastrar reglas sobre preguntas que Buenaventura renumeró). Los capítulos
    propios de Buenaventura (ST seguridad jurídica, IF info adicional) NO tienen
    reglas aquí: su flujograma es un diagrama visual no parseable → revisión manual.
    """
    terr = json.loads(TERR_FIX.read_text(encoding='utf-8'))
    bv_text = {p['codigo_externo']: norm(p['texto']) for p in preguntas_fix}
    te_text = {p['codigo_externo']: norm(p['texto']) for p in terr['preguntas']}
    bv_caps = {p['capitulo_codigo'] for p in preguntas_fix}

    def coincide(cod):
        if cod not in bv_text:
            return False
        b = te_text.get(cod, '')
        return bool(b) and SequenceMatcher(None, bv_text[cod], b).ratio() >= 0.85

    reglas, descartadas = [], 0
    for r in terr['reglas_skip_logic']:
        o, a, ac, ex = r.get('origen'), r.get('afecta'), r.get('afecta_capitulo'), r.get('origen_expr')
        # origen: expresión (edad/sexo/etnia) siempre vale; pregunta debe coincidir
        if o and not coincide(o):
            descartadas += 1; continue
        if not o and not ex:
            descartadas += 1; continue
        # destino: pregunta afectada debe coincidir, o capítulo afectado debe existir
        if a and not coincide(a):
            descartadas += 1; continue
        if ac and ac not in bv_caps:
            descartadas += 1; continue
        if not a and not ac:
            descartadas += 1; continue
        reglas.append(dict(r))
    print(f"  Skip-logic derivado de Territorial: {len(reglas)} reglas "
          f"({descartadas} descartadas por no coincidir en Buenaventura)")
    return reglas


def main():
    escribir = '--escribir' in sys.argv
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    todas = []
    todas += parsear_hoja(wb['HOGAR Caracterización'], 'HOGAR')
    todas += parsear_hoja(wb['PERSONAS-Caracterización '], 'PERSONA')

    preguntas_fix, seen, caps_orden = [], set(), {}
    for q in todas:
        cod = q['codigo_externo']
        if cod in seen:
            continue
        seen.add(cod)
        caps_orden[q['cap_codigo']] = q['cap_orden']
        tipo = inferir_tipo(q['valores'], q['opciones'], q['texto'])
        preguntas_fix.append({
            'no_pregunta': q['no_pregunta'], 'codigo_externo': cod, 'id_preg': q['id_preg'],
            'capitulo_codigo': q['cap_codigo'], 'texto': q['texto'], 'tipo': tipo,
            'nivel': q['nivel'], 'obligatoria': False, 'orden': 0,
            'es_precargada': bool(q['fuente']) and 'precarg' in norm(q['fuente']),
            'fuente_precarga': q['fuente'], 'validaciones': {},
            'opciones': [{'valor': o['valor'], 'etiqueta': o['etiqueta'],
                          'id_resp_vivanto': o['id_resp_vivanto'], 'orden': o['orden']}
                         for o in q['opciones']],
        })

    contador = {}
    for p in preguntas_fix:
        c = p['capitulo_codigo']
        contador[c] = contador.get(c, 0) + 1
        p['orden'] = contador[c]

    # nivel del capítulo = nivel mayoritario de sus preguntas
    def nivel_cap(c):
        niveles = [p['nivel'] for p in preguntas_fix if p['capitulo_codigo'] == c]
        return max(set(niveles), key=niveles.count) if niveles else 'HOGAR'

    capitulos = [{'codigo': c, 'nombre': CAP_NOMBRE.get(c, c), 'orden': o,
                  'nivel': nivel_cap(c), 'poblacion_objetivo': 'TODOS_MIEMBROS', 'objetivo': ''}
                 for c, o in sorted(caps_orden.items(), key=lambda x: x[1])]

    reglas = derivar_skip_logic(preguntas_fix)

    data = {
        'perfil': {'codigo': 'BUENAVENTURA', 'nombre': 'Caracterización Buenaventura'},
        'instrumento_version': {'numero': 'V7', 'vigente_desde': '2023-07-14'},
        'capitulos': capitulos,
        'preguntas': preguntas_fix,
        'reglas_skip_logic': reglas,
    }

    print(f"Capítulos: {len(capitulos)} | Preguntas: {len(preguntas_fix)} | "
          f"Opciones: {sum(len(p['opciones']) for p in preguntas_fix)}")
    tipos = {}
    for p in preguntas_fix:
        tipos[p['tipo']] = tipos.get(p['tipo'], 0) + 1
    print("Tipos:", tipos)
    print("\nPor capítulo:")
    for c in capitulos:
        n = sum(1 for p in preguntas_fix if p['capitulo_codigo'] == c['codigo'])
        print(f"  {c['orden']:>2} | {c['codigo']:3} | {n:>3} preg | {c['nivel']:7} | {c['nombre']}")

    if '--muestra' in sys.argv:
        print("\n=== MUESTRA ===")
        for p in preguntas_fix:
            ops = ' / '.join(f"{o['valor']}={o['etiqueta']}" for o in p['opciones'][:5])
            print(f"  [{p['capitulo_codigo']}|{p['no_pregunta'] or '-'}] {p['codigo_externo']:<14} {p['tipo']:<13} {p['texto'][:45]}")
            if ops:
                print(f"        {ops}{' …' if len(p['opciones'])>5 else ''}")

    if escribir:
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
        print(f"\nOK escrito: {OUT}")
        print("\n⚠  RECUERDA: este fixture NO trae la curación del cap. B (Bug 2).")
        print("   Ejecuta ahora: python scripts/patch_bug2_embarazo_gestacion.py")
    else:
        print("\n(inspección — usar --escribir para guardar)")
    return data


if __name__ == '__main__':
    main()
