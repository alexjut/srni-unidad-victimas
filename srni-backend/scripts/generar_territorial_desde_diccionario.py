#!/usr/bin/env python3
"""
Genera el fixture del instrumento TERRITORIAL V7 leyendo el diccionario oficial
(Excel) como ÚNICA fuente de verdad — códigos, textos, tipos y opciones EXACTOS.

Motivo: el instrumento del APK estaba desalineado del diccionario (códigos
corridos, ~70 preguntas faltantes). Esto lo reconstruye 1:1 con el diccionario.

Uso:
    python scripts/generar_territorial_desde_diccionario.py            # inspección (no escribe)
    python scripts/generar_territorial_desde_diccionario.py --escribir # escribe el fixture
"""
import sys, json, re, unicodedata
from pathlib import Path
import openpyxl

XLSX = Path(__file__).resolve().parents[2] / "docs/perfiles/Perfil Territorial_web y offline/Diccionario_de_datos__Entrevista de Caracterización_V7_Perfil Territorial.xlsx"
OUT = Path(__file__).resolve().parents[1] / "apps/formulario/fixtures/perfil_territorial_v7.json"

# Mapa nombre de capítulo (diccionario) → (código corto, orden, nivel)
CAP_MAP = {
    'A. IDENTIFICACIÓN':            ('A', 1, 'HOGAR'),
    'B.DATOS BASICOS':              ('B', 2, 'PERSONA'),
    'C. VIVIENDA':                  ('C', 3, 'HOGAR'),
    'D. RETORNO Y REUBICACIONES':   ('D', 4, 'HOGAR'),
    'F. REUNIFICACIÓN FAMILIAR':    ('E', 5, 'HOGAR'),   # instrumento usa E
    'F. EDUCACIÓN':                 ('F', 6, 'PERSONA'),
    'G. SALUD':                     ('G', 7, 'PERSONA'),
    'H. REHABILITACIÓN':            ('H', 8, 'PERSONA'),
    'J.ALIMENTACIÓN':               ('JA', 9, 'HOGAR'),
    'J. FUERZA DE TRABAJO':         ('JF', 10, 'PERSONA'),
    'K. PERFIL SOCIOLABORAL':       ('K', 11, 'PERSONA'),
    'L. FUERZA PÚBLICA':            ('L', 12, 'PERSONA'),
    'USO Y DISFRUTE DEL TERRITORIO':('M', 13, 'HOGAR'),
    'T. CONTROL':                   ('T', 14, 'HOGAR'),
    # INFORMACIÓN PRECARGADA: metadatos precargados → se asignan al capítulo A
    'INFORMACIÓN PRECARGADA':       ('A', 1, 'HOGAR'),
}

CAP_NOMBRE = {
    'A': 'A. IDENTIFICACIÓN', 'B': 'B. DATOS BÁSICOS', 'C': 'C. VIVIENDA',
    'D': 'D. RETORNOS Y REUBICACIONES', 'E': 'E. REUNIFICACIÓN FAMILIAR',
    'F': 'F. EDUCACIÓN', 'G': 'G. SALUD', 'H': 'H. REHABILITACIÓN',
    'JA': 'J. ALIMENTACIÓN', 'JF': 'J. FUERZA DE TRABAJO', 'K': 'K. PERFIL SOCIOLABORAL',
    'L': 'L. FUERZA PÚBLICA', 'M': 'M. USO Y DISFRUTE DEL TERRITORIO', 'T': 'T. CONTROL',
}


def norm(s):
    if not s: return ''
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


# Valores de la columna "Valores" que son INDICADORES DE TIPO (no opciones reales)
TIPOS_ESPECIALES = {'texto', 'numerico', 'numero', 'divipola', 'fecha',
                    'dd/mm/aaa', 'moneda', 'alfanumerico', 'hora'}


def inferir_tipo(valores, opciones, texto):
    v = norm(valores)
    if v == 'texto' or v == 'alfanumerico':
        return 'TEXTO_LARGO' if 'observ' in norm(texto) else 'TEXTO'
    if v in ('numerico', 'numero', 'moneda'):
        return 'NUMERICO'
    if v in ('fecha', 'dd/mm/aaa'):
        return 'FECHA'
    if v == 'divipola':
        return 'COMBO_DINAMICO'
    if opciones:
        etis = {norm(o['etiqueta']) for o in opciones}
        if etis <= {'si', 'no'} and etis:
            return 'BOOLEAN'
        return 'LISTA'
    return 'TEXTO'


def parsear_hoja(ws, nivel_default):
    """Devuelve lista de preguntas con sus opciones, en orden de aparición."""
    preguntas = []
    cap_actual = None
    actual = None  # pregunta en construcción
    for row in ws.iter_rows(min_row=2, values_only=True):
        r = (list(row) + [''] * 12)[:12]
        cap, var, diag, preg, idp, desc, val, idresp, _, _, estado, fuente = r
        if cap and str(cap).strip():
            cap_actual = str(cap).strip()
        var = str(var).strip() if var else ''
        preg_txt = str(preg).strip() if preg else ''
        est = str(estado).strip().upper() if estado else ''

        if var and preg_txt:
            # nueva pregunta
            if est != 'ACTIVA':
                actual = None
                continue
            mapinfo = CAP_MAP.get(cap_actual)
            if not mapinfo:
                actual = None
                continue
            cod_cap, orden_cap, nivel_cap = mapinfo
            actual = {
                'cap_codigo': cod_cap, 'cap_orden': orden_cap, 'nivel': nivel_cap,
                'codigo_externo': var,
                'no_pregunta': str(diag).strip() if diag else '',
                'texto': preg_txt,
                'id_preg': int(idp) if isinstance(idp, (int, float)) else None,
                'valores': val, 'fuente': str(fuente).strip() if fuente else '',
                'opciones': [],
            }
            # primera opción inline solo si Valores NO es un indicador de tipo
            if desc and norm(val) not in TIPOS_ESPECIALES:
                actual['opciones'].append({
                    'valor': str(val).strip(), 'etiqueta': str(desc).strip(),
                    'id_resp_vivanto': int(idresp) if isinstance(idresp, (int, float)) else None,
                    'orden': 1,
                })
            preguntas.append(actual)
        elif actual is not None and desc and not preg_txt:
            # fila de opción adicional: tiene etiqueta (Descripción) y NO es una
            # pregunta nueva (sin texto). Puede traer su PROPIO código de
            # sub-respuesta en multi-respuesta (I7K, I7L...) — antes se descartaba
            # por tener código; ese era el bug que dejaba las listas con 1 opción.
            actual['opciones'].append({
                'valor': str(val).strip() if val is not None else '',
                'etiqueta': str(desc).strip(),
                'id_resp_vivanto': int(idresp) if isinstance(idresp, (int, float)) else None,
                'orden': len(actual['opciones']) + 1,
            })
    # Multi-respuesta: el diccionario pone valor=1 en todas las opciones. Para que
    # los valores sean ÚNICOS (necesario en LISTA), renumerar 1..N solo si hay
    # colisión; las que ya traen valores únicos del diccionario se respetan.
    for q in preguntas:
        ops = q['opciones']
        valores = [o['valor'] for o in ops]
        if len(set(valores)) < len(valores):
            for i, o in enumerate(ops, 1):
                o['valor'] = str(i)
    return preguntas


def main():
    escribir = '--escribir' in sys.argv
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    todas = []
    todas += parsear_hoja(wb['HOGAR Caracterización'], 'HOGAR')
    todas += parsear_hoja(wb['PERSONAS-Caracterización '], 'PERSONA')

    # Construir capítulos + preguntas en formato fixture
    caps_orden = {}
    preguntas_fix = []
    seen = set()
    for i, q in enumerate(todas):
        cod = q['codigo_externo']
        if cod in seen:   # dedup por código (gana la primera)
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
    # asignar orden secuencial por capítulo
    contador = {}
    for p in preguntas_fix:
        c = p['capitulo_codigo']
        contador[c] = contador.get(c, 0) + 1
        p['orden'] = contador[c]

    capitulos = [{'codigo': c, 'nombre': CAP_NOMBRE.get(c, c), 'orden': o, 'nivel':
                  next((q['nivel'] for q in todas if q['cap_codigo'] == c), 'HOGAR'),
                  'poblacion_objetivo': 'TODOS_MIEMBROS', 'objetivo': ''}
                 for c, o in sorted(caps_orden.items(), key=lambda x: x[1])]

    data = {
        'perfil': {'codigo': 'TERRITORIAL', 'nombre': 'Caracterización territorial'},
        'instrumento_version': {'numero': 'V7', 'vigente_desde': '2023-07-14'},
        'capitulos': capitulos,
        'preguntas': preguntas_fix,
        'reglas_skip_logic': [],
    }

    # Reporte
    print(f"Capítulos: {len(capitulos)} | Preguntas: {len(preguntas_fix)}")
    print(f"Opciones totales: {sum(len(p['opciones']) for p in preguntas_fix)}")
    tipos = {}
    for p in preguntas_fix:
        tipos[p['tipo']] = tipos.get(p['tipo'], 0) + 1
    print("Tipos:", tipos)
    print("\nPor capítulo (orden | código | #preg | nivel):")
    for c in capitulos:
        n = sum(1 for p in preguntas_fix if p['capitulo_codigo'] == c['codigo'])
        print(f"  {c['orden']:>2} | {c['codigo']:3} | {n:>3} preg | {c['nivel']:7} | {c['nombre']}")

    if '--muestra' in sys.argv:
        print("\n=== MUESTRA de preguntas (texto · tipo · opciones) ===")
        muestras = ['C1', 'D8A', 'B10', 'A21', 'I1A1', 'I1B', 'A3', 'C2']
        idx = {p['codigo_externo']: p for p in preguntas_fix}
        for cod in muestras:
            p = idx.get(cod)
            if not p:
                print(f"  {cod}: (no está)")
                continue
            ops = ' / '.join(f"{o['valor']}={o['etiqueta']}" for o in p['opciones'][:6])
            print(f"  [{p['no_pregunta']}] {cod} | {p['tipo']}")
            print(f"      texto: {p['texto']}")
            if ops:
                print(f"      opciones: {ops}{' …' if len(p['opciones'])>6 else ''}")

    if escribir:
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
        print(f"\nOK escrito: {OUT}")
    else:
        print("\n(inspección — usar --escribir para guardar el fixture)")
    return data


if __name__ == '__main__':
    main()
