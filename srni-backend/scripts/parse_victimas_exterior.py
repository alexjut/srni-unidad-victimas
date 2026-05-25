"""
Parser del perfil 'Víctimas en el Exterior' desde Historias de Usuario.xlsx.

Estructura del Excel (Hoja1, 464 filas):
  A: Capítulo
  B: Orden de la pregunta
  C: Pregunta (texto)
  D: Descripción (texto de la opción)
  E: Valor (valor de la opción o tipo: TEXTO, FECHA, NUMERICO)
  F: Condición (skip logic)
  G: Aplicación

Lógica:
- Una fila con C poblado = inicio de pregunta nueva (texto = C)
- Filas siguientes con D + E numérico/letra = opciones
- Filas siguientes con E='TEXTO'/'FECHA'/'NUMERICO' = tipo de la pregunta (no opciones)
- Filas con F poblado = condición skip logic

Genera srni-backend/apps/formulario/fixtures/perfil_victimas_exterior_v1.json
con misma estructura que los otros 7 perfiles.
"""
import json
import re
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'docs' / 'perfiles' / 'Perfil Victimas en el Exterior_web' / 'Historias de Usuario.xlsx'
OUT = ROOT / 'srni-backend' / 'apps' / 'formulario' / 'fixtures' / 'perfil_victimas_exterior_v1.json'

# Mapeo capítulo nombre → código y orden
CAPITULOS_DEF = [
    ('A', 'Datos Demográficos', 1),
    ('B', 'Datos de Ubicación',  2),
    ('C', 'Victimización y Derechos', 3),
    ('D', 'Dinámica Migratoria', 4),
    ('E', 'Estatus Migratorio',  5),
    ('F', 'Integración Local y Calidad de Vida', 6),
    ('G', 'Restitución de Tierras', 7),
    ('H', 'Intención de Retorno', 8),
]

# Normalizar nombre de capítulo del Excel → código (matching flexible)
def nombre_a_codigo(nombre: str) -> tuple:
    """Devuelve (codigo, nombre_oficial, orden) o (None, None, None) si no se encuentra."""
    if not nombre:
        return (None, None, None)
    n = re.sub(r'\s+', ' ', str(nombre).strip()).lower()
    # Quitar acentos para matching más permisivo
    n = (n.replace('á', 'a').replace('é', 'e').replace('í', 'i')
           .replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n'))
    # Detectar por palabras clave
    if 'datos demogra' in n:
        return ('A', 'Datos Demográficos', 1)
    if 'datos de ubica' in n or 'ubicacion' in n:
        return ('B', 'Datos de Ubicación', 2)
    if 'victimiza' in n and 'derecho' in n:
        return ('C', 'Victimización y Derechos', 3)
    if 'dinamica migra' in n:
        return ('D', 'Dinámica Migratoria', 4)
    if 'estatus migra' in n:
        return ('E', 'Estatus Migratorio', 5)
    if 'integracion local' in n:
        return ('F', 'Integración Local y Calidad de Vida', 6)
    if 'restituc' in n and 'tierra' in n:
        return ('G', 'Restitución de Tierras', 7)
    if 'intencion de retorno' in n:
        return ('H', 'Intención de Retorno', 8)
    return (None, None, None)


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    ws = wb['Hoja1']

    # Parsear filas
    preguntas_por_cap = {cod: [] for cod, _, _ in CAPITULOS_DEF}
    pregunta_actual = None
    pregunta_idx_por_cap = {cod: 0 for cod, _, _ in CAPITULOS_DEF}

    for fila_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        cap_raw = row[0] if len(row) > 0 else None
        orden = row[1] if len(row) > 1 else None
        pregunta_txt = row[2] if len(row) > 2 else None
        desc = row[3] if len(row) > 3 else None
        valor = row[4] if len(row) > 4 else None
        condicion = row[5] if len(row) > 5 else None
        aplicacion = row[6] if len(row) > 6 else None

        cap_cod, cap_nombre, _ = nombre_a_codigo(cap_raw) if cap_raw else (None, None, None)

        # Si C tiene texto, es una pregunta nueva
        if pregunta_txt and cap_cod:
            pregunta_idx_por_cap[cap_cod] += 1
            ordn = pregunta_idx_por_cap[cap_cod]
            pregunta_actual = {
                'no_pregunta': f'{cap_cod}{ordn}',
                'codigo_externo': f'{cap_cod}{ordn}_vex',
                'capitulo_codigo': cap_cod,
                'texto': str(pregunta_txt).strip(),
                'tipo': None,
                'nivel': 'HOGAR',
                'obligatoria': True,
                'orden': ordn,
                'es_precargada': False,
                'fuente_precarga': '',
                'validaciones': {},
                'opciones': [],
                'condicion_excel': str(condicion).strip() if condicion else None,
            }
            preguntas_por_cap[cap_cod].append(pregunta_actual)

            # Si D + E son la misma fila, la pregunta tiene tipo directo o primera opción
            if desc and valor is not None:
                _agregar_opcion_o_tipo(pregunta_actual, desc, valor)
            elif desc and not valor:
                # Es solo descripción adicional del texto
                pregunta_actual['descripcion_ayuda'] = str(desc).strip()
            continue

        # Si no hay pregunta nueva pero hay D + E, es una opción de la pregunta actual
        if pregunta_actual and (desc or valor is not None):
            _agregar_opcion_o_tipo(pregunta_actual, desc, valor)

    # Cerrar tipo de cada pregunta (si no se detectó, decidir según opciones)
    for cap_cod, preguntas in preguntas_por_cap.items():
        for p in preguntas:
            if p['tipo'] is None:
                p['tipo'] = 'LISTA' if p['opciones'] else 'TEXTO'

    # ── Generar fixture en formato estándar ────────────────────────────────
    capitulos = []
    preguntas_flat = []
    for cap_cod, cap_nombre, cap_orden in CAPITULOS_DEF:
        capitulos.append({
            'codigo': cap_cod,
            'nombre': cap_nombre,
            'orden': cap_orden,
            'objetivo': '',
            'poblacion_objetivo': 'AUTORIZADO',
            'aplicabilidad': {},
        })
        for p in preguntas_por_cap[cap_cod]:
            # Limpiar el campo condicion antes de exportar (lo usaremos para skip logic más adelante)
            p_clean = {k: v for k, v in p.items() if k != 'condicion_excel'}
            preguntas_flat.append(p_clean)

    fixture = {
        'perfil': {
            'codigo': 'VICTIMAS_EXTERIOR',
            'nombre': 'Perfil Víctimas en el Exterior UARIV',
        },
        'instrumento_version': {
            'numero': 'V1',
            'vigente_desde': '2024-01-01',
            'vigente_hasta': None,
            'fuente_documental': 'Historias de Usuario - Perfil Víctimas en el Exterior',
        },
        'capitulos': capitulos,
        'preguntas': preguntas_flat,
        'reglas_skip_logic': [],
        'validaciones_cruzadas': [],
    }

    OUT.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # ── Reporte ─────────────────────────────────────────────────────────────
    print('═' * 60)
    print('RESUMEN PARSEO VÍCTIMAS EN EL EXTERIOR')
    print('═' * 60)
    total_pregs = 0
    total_opcs = 0
    for cap_cod, _, _ in CAPITULOS_DEF:
        ps = preguntas_por_cap[cap_cod]
        n_pregs = len(ps)
        n_opcs = sum(len(p['opciones']) for p in ps)
        total_pregs += n_pregs
        total_opcs += n_opcs
        tipos = {}
        for p in ps:
            tipos[p['tipo']] = tipos.get(p['tipo'], 0) + 1
        print(f'  Cap {cap_cod}: {n_pregs:>3} preguntas, {n_opcs:>3} opciones, tipos={tipos}')
    print(f'\n  TOTAL: {len(CAPITULOS_DEF)} capítulos, {total_pregs} preguntas, {total_opcs} opciones')
    print(f'\n  Fixture guardada en: {OUT.name}')


def _agregar_opcion_o_tipo(pregunta, desc, valor):
    """Agrega opción a la pregunta o detecta tipo si valor es marcador."""
    if valor is None and not desc:
        return

    valor_str = str(valor).strip() if valor is not None else ''
    desc_str = str(desc).strip() if desc else ''

    # Detección de tipo cuando la descripción es "Campo Abierto" + tipo en valor
    tipo_marker = valor_str.upper()
    desc_upper = desc_str.upper()

    # Caso A: descripción "Campo Abierto" → tipo libre, no es opción
    if desc_upper == 'CAMPO ABIERTO':
        if tipo_marker in ('NUMERICO', 'NÚMERICO'):
            pregunta['tipo'] = 'NUMERICO'
        elif tipo_marker == 'FECHA':
            pregunta['tipo'] = 'FECHA'
        elif tipo_marker == 'BOOLEAN':
            pregunta['tipo'] = 'BOOLEAN'
        elif tipo_marker == 'ALFANUMÉRICO':
            pregunta['tipo'] = 'TEXTO'
        else:
            pregunta['tipo'] = 'TEXTO'
        return

    # Caso B: valor es marcador de tipo (sin Campo Abierto)
    if tipo_marker in ('TEXTO', 'TEXTO LARGO', 'NUMERICO', 'NÚMERICO', 'FECHA', 'BOOLEAN', 'ALFANUMÉRICO'):
        mapping = {
            'TEXTO': 'TEXTO', 'TEXTO LARGO': 'TEXTO_LARGO',
            'NUMERICO': 'NUMERICO', 'NÚMERICO': 'NUMERICO', 'ALFANUMÉRICO': 'TEXTO',
            'FECHA': 'FECHA', 'BOOLEAN': 'BOOLEAN',
        }
        pregunta['tipo'] = mapping[tipo_marker]
        return

    # Caso C: hay descripción de opción + valor numérico → opción explícita
    if desc_str and valor_str:
        try:
            int_val = str(int(float(valor_str)))
            pregunta['opciones'].append({
                'valor': int_val,
                'etiqueta': desc_str,
                'id_resp_vivanto': 0,
                'orden': len(pregunta['opciones']) + 1,
            })
            return
        except (ValueError, TypeError):
            pass

    # Caso D: hay descripción SIN valor → opción con valor auto-asignado
    if desc_str:
        siguiente_valor = str(len(pregunta['opciones']) + 1)
        pregunta['opciones'].append({
            'valor': siguiente_valor,
            'etiqueta': desc_str,
            'id_resp_vivanto': 0,
            'orden': len(pregunta['opciones']) + 1,
        })


if __name__ == '__main__':
    main()
