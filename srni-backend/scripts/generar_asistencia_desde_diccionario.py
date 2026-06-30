#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el fixture del instrumento ASISTENCIA (= Telefónico SAAH) leyendo el
Diccionario de datos V8 del Perfil Telefónico como fuente de verdad de
contenido (códigos, textos, tipos, opciones), mapeado al orden de capítulos
del manual 14-MU (A..G).

Fuentes:
  - Contenido:  Diccionario_de_datos V8 Perfil Telefónico  (hojas HOGAR / PERSONAS)
  - Estructura: manual 14-MU (A Información General, B Datos Básicos, C Vivienda,
                D Educación, E Salud, F Rehabilitación, G Alimentación)
  - Flujos:     Flujograma V9.1  (se aplican aparte, no en este script)

OJO: el diccionario V8 tiene 9 columnas y NO trae columna "estado/ACTIVA"
(a diferencia del de Territorial). Layout:
  CAPITULO | VARIABLE BD | No.PREGUNTA | PREGUNTA | ID_PREG | Descripción | Valores | ID_RESP | FUENTE

Uso:
    python scripts/generar_asistencia_desde_diccionario.py            # inspección
    python scripts/generar_asistencia_desde_diccionario.py --escribir # escribe fixture
    python scripts/generar_asistencia_desde_diccionario.py --muestra  # + muestra
"""
import sys, json, re, unicodedata
from pathlib import Path
import openpyxl

XLSX = Path(r"D:/desarrollo/perfiles/Perfil Telefonico_SAAH__web/Diccionario_de_datos__Entrevista de Caracterización_V8_Perfil Telefónico.xlsx")
OUT = Path(__file__).resolve().parents[1] / "apps/formulario/fixtures/perfil_asistencia_v8.json"

# Nombre de capítulo (diccionario telefónico) -> (código manual 14-MU, orden, nivel)
# El manual ordena A..G. T.CONTROL es metadata (no se incluye, igual que el fixture actual).
CAP_MAP = {
    'INFORMACIÓN PRECARGADA':   ('A', 1, 'HOGAR'),
    'A. IDENTIFICACIÓN':        ('A', 1, 'HOGAR'),
    'B.DATOS BASICOS':          ('B', 2, 'PERSONA'),
    'C. VIVIENDA':              ('C', 3, 'HOGAR'),
    'F. EDUCACIÓN':             ('D', 4, 'PERSONA'),
    'SALUD':                    ('E', 5, 'PERSONA'),
    'H. REHABILITACIÓN_SAAH':   ('F', 6, 'PERSONA'),
    'J.ALIMENTACIÓN':           ('G', 7, 'HOGAR'),
    # 'T. CONTROL': excluido (metadata)
}

CAP_NOMBRE = {
    'A': 'A. Información General', 'B': 'B. Datos Básicos', 'C': 'C. Vivienda',
    'D': 'D. Educación', 'E': 'E. Salud', 'F': 'F. Rehabilitación',
    'G': 'G. Alimentación',
}
CAP_NIVEL = {'A': 'HOGAR', 'B': 'PERSONA', 'C': 'HOGAR', 'D': 'PERSONA',
             'E': 'PERSONA', 'F': 'PERSONA', 'G': 'HOGAR'}

TIPOS_ESPECIALES = {'texto', 'numerico', 'numero', 'divipola', 'fecha',
                    'dd/mm/aaa', 'dd/mm/aaaa', 'moneda', 'alfanumerico', 'hora'}


def norm(s):
    if not s:
        return ''
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


def parsear_hoja(ws):
    """Layout de 9 columnas, sin columna ACTIVA."""
    preguntas = []
    cap_actual = None
    actual = None
    for row in ws.iter_rows(min_row=2, values_only=True):
        r = (list(row) + [''] * 9)[:9]
        cap, var, diag, preg, idp, desc, val, idresp, fuente = r
        if cap and str(cap).strip():
            cap_actual = str(cap).strip()
        var = str(var).strip() if var else ''
        preg_txt = str(preg).strip() if preg else ''
        desc_txt = str(desc).strip() if desc else ''

        if var and preg_txt:
            mapinfo = CAP_MAP.get(cap_actual)
            if not mapinfo:
                actual = None
                continue
            cod_cap, orden_cap, _nivel = mapinfo
            actual = {
                'cap_codigo': cod_cap, 'cap_orden': orden_cap,
                'codigo_externo': var,
                'no_pregunta': str(diag).strip() if diag and str(diag).strip() not in ('---', 'N/A') else '',
                'texto': preg_txt,
                'id_preg': int(idp) if isinstance(idp, (int, float)) else None,
                'valores': val, 'fuente': str(fuente).strip() if fuente else '',
                'opciones': [],
            }
            if desc_txt and norm(val) not in TIPOS_ESPECIALES:
                actual['opciones'].append({
                    'valor': str(val).strip() if val is not None else '',
                    'etiqueta': desc_txt,
                    'id_resp_vivanto': int(idresp) if isinstance(idresp, (int, float)) else None,
                    'orden': 1,
                })
            preguntas.append(actual)
        elif (actual is not None and desc_txt and not preg_txt
              and not var and norm(val) not in TIPOS_ESPECIALES):
            # fila de opción adicional: SOLO si VARIABLE BD vacía (no es una
            # sub-variable precargada como DEPTO_ATENCION) y el valor no es un
            # indicador de tipo (filtra "NUMÉRICO=Valor 1 a 7" de alimentación).
            actual['opciones'].append({
                'valor': str(val).strip() if val is not None else '',
                'etiqueta': desc_txt,
                'id_resp_vivanto': int(idresp) if isinstance(idresp, (int, float)) else None,
                'orden': len(actual['opciones']) + 1,
            })

    # Valores únicos en multi-respuesta (cuando el diccionario repite valor=1)
    for q in preguntas:
        vals = [o['valor'] for o in q['opciones']]
        if vals and len(set(vals)) < len(vals):
            for i, o in enumerate(q['opciones'], 1):
                o['valor'] = str(i)
    return preguntas


def reunificacion_preguntas():
    """Capítulo RF desde Flujograma V9.1 (SAAH). nivel HOGAR."""
    def q(cod, no, texto, tipo, opciones):
        return {'no_pregunta': no, 'codigo_externo': cod, 'id_preg': None,
                'capitulo_codigo': 'RF', 'texto': texto, 'tipo': tipo, 'nivel': 'HOGAR',
                'obligatoria': False, 'orden': 0, 'es_precargada': False,
                'fuente_precarga': '', 'validaciones': {},
                'opciones': [{'valor': v, 'etiqueta': e, 'id_resp_vivanto': i, 'orden': n}
                             for n, (v, e, i) in enumerate(opciones, 1)]}
    return [
        q('F1_tel', 'E1', '¿A causa del hecho victimizante, el hogar se vió obligado a separarse?',
          'BOOLEAN', [('1', 'Sí', 236), ('2', 'No', 237)]),
        q('F3_tel', 'E2', '¿El hogar solicitó apoyo del gobierno u otra entidad privada para la reunificación familiar?',
          'BOOLEAN', [('1', 'Sí', 240), ('2', 'No', 241)]),
        q('F5_tel', 'E3', '¿El hogar logró reunificarse?',
          'BOOLEAN', [('1', 'Sí', 2391), ('2', 'No', 2392)]),
        q('F6_tel', 'E4', '¿Está interesado en iniciar un proceso de reunificación familiar?',
          'LISTA', [('1', 'Si', 3864), ('2', 'No le interesa', 2393),
                    ('4', 'No conoce el proceso de reunificación', 2394)]),
    ]


# Re-letrado de capítulo Territorial -> Asistencia (para derivar skip-logic)
RELET_CAP = {'A': 'A', 'B': 'B', 'C': 'C', 'F': 'D', 'G': 'E', 'H': 'F', 'JA': 'G'}


def _base(c):
    return c[:-4] if c and c.endswith('_tel') else c


def derivar_skip_logic(preguntas_fix):
    """Deriva reglas desde el fixture Territorial (que codifica el mismo manual),
    remapeando por código base (_tel) y re-letrando capítulos. Añade reglas
    propias de Asistencia (D7, C5A, sabe-leer) y de Reunificación."""
    terr_path = Path(__file__).resolve().parents[1] / "apps/formulario/fixtures/perfil_territorial_v7.json"
    terr = json.loads(terr_path.read_text(encoding='utf-8'))
    codes = [p['codigo_externo'] for p in preguntas_fix]
    base2code = {_base(c): c for c in codes}
    code_set = set(codes)
    # capítulo Territorial de cada código, para excluir reglas de capítulos que
    # NO conservo (p.ej. cap E Reunificación, cuyos códigos F1/F3/F5 colisionan
    # con los que añado manualmente desde el Flujograma V9.1).
    terr_cap = {p['codigo_externo']: p['capitulo_codigo'] for p in terr['preguntas']}
    keep_caps = set(RELET_CAP)

    def mapcode(code):
        if code is None:
            return None, True
        if _base(code) in base2code:
            return base2code[_base(code)], True
        return code, False

    reglas = []
    for r in terr['reglas_skip_logic']:
        a, ac, o = r.get('afecta'), r.get('afecta_capitulo'), r.get('origen')
        # El FINALIZAR de C1 se re-añade abajo con 11,12,98 (manual). Saltar el de Territorial.
        if r.get('accion') == 'FINALIZAR' and _base(o) == 'C1':
            continue
        # Excluir reglas cuyo origen/afecta vive en un capítulo Territorial que no conservo
        # (evita que reglas de Reunificación/Retornos de Territorial contaminen Asistencia).
        if a is not None and terr_cap.get(a) not in keep_caps:
            continue
        if o and terr_cap.get(o) not in keep_caps:
            continue
        na = no = nac = None
        if a is not None:
            na, ok = mapcode(a)
            if not ok:
                continue
        if ac is not None:
            if ac not in RELET_CAP:
                continue
            nac = RELET_CAP[ac]
        if o:
            no, ok = mapcode(o)
            if not ok:
                continue
        nr = dict(r)
        if na is not None:
            nr['afecta'] = na
        if no is not None:
            nr['origen'] = no
        if nac is not None:
            nr['afecta_capitulo'] = nac
        reglas.append(nr)

    # --- Reglas propias de Asistencia (códigos que Territorial no tiene) ---
    def add(origen, valor, accion, afecta=None, afecta_cap=None, expr=None, desc=''):
        if afecta and afecta not in code_set:
            return
        rule = {'valor_trigger': valor, 'accion': accion, 'descripcion': desc}
        if expr:
            rule['origen_expr'] = expr
        else:
            rule['origen'] = origen
        if afecta:
            rule['afecta'] = afecta
        if afecta_cap:
            rule['afecta_capitulo'] = afecta_cap
        reglas.append(rule)

    # Vivienda: D7 (documento soporte) ← tenencia Propia (D5=1)
    add('D5_tel', '1', 'HABILITAR', afecta='D7_tel', desc='[asistencia] doc soporte si vivienda propia')
    # Vivienda: C5A (nombre autoridad) ← zona alto riesgo = Si (C5=1)
    add('C5_tel', '1', 'HABILITAR', afecta='C5A_tel', desc='[asistencia] nombre autoridad si C5=Si')
    # Vivienda: finaliza también en calle/ilegal/otra (manual: 11,12,98)
    add('C1_tel', '11,12,98', 'FINALIZAR', afecta_cap='C', desc='[asistencia] finaliza si calle/ilegal/otra')
    # Educación: sabe leer (G15) ← edad ≥ 5 (manual F2)
    add(None, '', 'HABILITAR', afecta='G15_tel', expr='edad >= 5', desc='[asistencia] sabe leer: edad>=5')

    # --- Reunificación (Flujograma V9.1) ---
    # F1/F3/F5 son BOOLEAN ⇒ la APK guarda 'true'/'false' (no 1/2). El trigger
    # debe ser 'true'/'false' o la regla NO dispara (ver skipLogic.ts / reference).
    add('F1_tel', 'false', 'FINALIZAR', afecta_cap='RF', desc='[reunif] finaliza si no se separó')
    add('F1_tel', 'true', 'HABILITAR', afecta='F3_tel', desc='[reunif] solicitó apoyo si se separó')
    add('F3_tel', 'true', 'HABILITAR', afecta='F5_tel', desc='[reunif] logró reunificarse si solicitó')

    return reglas


def main():
    escribir = '--escribir' in sys.argv
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    todas = []
    todas += parsear_hoja(wb['HOGAR Caracterización'])
    todas += parsear_hoja(wb['PERSONAS-Caracterización '])

    preguntas_fix, seen, caps_orden = [], set(), {}
    for q in todas:
        cod = q['codigo_externo']
        if cod in seen:
            continue
        seen.add(cod)
        caps_orden[q['cap_codigo']] = q['cap_orden']
        tipo = inferir_tipo(q['valores'], q['opciones'], q['texto'])
        es_prec = bool(q['fuente']) and 'precarg' in norm(q['fuente'])
        # no_pregunta: blanquear cuando repite el código (precargadas Estado_/RUV)
        nopreg = q['no_pregunta']
        if nopreg == cod or nopreg.upper() in ('ESTADO_', 'ID_ENTREVISTA'):
            nopreg = ''
        preguntas_fix.append({
            'no_pregunta': nopreg, 'codigo_externo': cod, 'id_preg': q['id_preg'],
            'capitulo_codigo': q['cap_codigo'], 'texto': q['texto'], 'tipo': tipo,
            'nivel': CAP_NIVEL[q['cap_codigo']], 'obligatoria': False, 'orden': 0,
            'es_precargada': es_prec, 'fuente_precarga': q['fuente'], 'validaciones': {},
            'opciones': [{'valor': o['valor'], 'etiqueta': o['etiqueta'],
                          'id_resp_vivanto': o['id_resp_vivanto'], 'orden': o['orden']}
                         for o in q['opciones']],
        })

    # --- Capítulo Reunificación Familiar (Flujograma V9.1; NO está en diccionario V8) ---
    # Códigos variable_bd reusan los de Territorial (F1/F3/F5/F6) con sufijo _tel.
    # id_resp_vivanto tomados del Flujograma V9.1. E5 (relacionar personas en primer
    # grado de consanguinidad) requiere widget relacional → pendiente, no se incluye.
    preguntas_fix += reunificacion_preguntas()
    caps_orden['RF'] = 8

    contador = {}
    for p in preguntas_fix:
        c = p['capitulo_codigo']
        contador[c] = contador.get(c, 0) + 1
        p['orden'] = contador[c]

    cap_nombre = dict(CAP_NOMBRE, RF='Reunificación Familiar')
    cap_nivel = dict(CAP_NIVEL, RF='HOGAR')
    capitulos = [{'codigo': c, 'nombre': cap_nombre[c], 'orden': o, 'nivel': cap_nivel[c],
                  'poblacion_objetivo': 'TODOS_MIEMBROS', 'objetivo': ''}
                 for c, o in sorted(caps_orden.items(), key=lambda x: x[1])]

    reglas = derivar_skip_logic(preguntas_fix)

    data = {
        'perfil': {'codigo': 'ASISTENCIA', 'nombre': 'Asistencia humanitaria'},
        'instrumento_version': {'numero': 'V8', 'vigente_desde': '2023-07-14'},
        'capitulos': capitulos,
        'preguntas': preguntas_fix,
        'reglas_skip_logic': reglas,
    }
    print(f"\nReglas skip-logic: {len(reglas)}")

    print(f"Capítulos: {len(capitulos)} | Preguntas: {len(preguntas_fix)} | "
          f"Opciones: {sum(len(p['opciones']) for p in preguntas_fix)}")
    tipos = {}
    for p in preguntas_fix:
        tipos[p['tipo']] = tipos.get(p['tipo'], 0) + 1
    print("Tipos:", tipos)
    print("\nPor capítulo:")
    for c in capitulos:
        qs = [p for p in preguntas_fix if p['capitulo_codigo'] == c['codigo']]
        print(f"  {c['orden']} | {c['codigo']} | {len(qs):>2} preg | {c['nivel']:7} | {c['nombre']}")

    if '--muestra' in sys.argv:
        print("\n=== MUESTRA ===")
        for p in preguntas_fix:
            ops = ' / '.join(f"{o['valor']}={o['etiqueta']}" for o in p['opciones'][:5])
            print(f"  [{p['capitulo_codigo']}|{p['no_pregunta'] or '-'}] {p['codigo_externo']:<18} {p['tipo']:<13} {p['texto'][:45]}")
            if ops:
                print(f"        {ops}{' …' if len(p['opciones'])>5 else ''}")

    if escribir:
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
        print(f"\nOK escrito: {OUT}")
    else:
        print("\n(inspección — usar --escribir para guardar)")
    return data


if __name__ == '__main__':
    main()
