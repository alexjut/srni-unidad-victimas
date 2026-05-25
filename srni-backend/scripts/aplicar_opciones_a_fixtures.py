"""
Aplica las opciones extraídas del Excel oficial a las fixtures.

Lee opciones_extraidas.json (generado por extraer_opciones_oficiales.py),
modifica perfil_territorial_v7.json y perfil_telefonico_v8.json:

- OPCIONES_CLASICAS / MATRIZ_SINO → reemplaza "opciones": [] por la lista extraída
- TEXTO_LIBRE                     → cambia "tipo": "LISTA"/"LISTA_MULTIPLE" → "TEXTO_LARGO"
- NO_ENCONTRADA (solo M5/AT5)     → aplica opciones agropecuarias hardcoded

Es idempotente: se puede correr varias veces.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / 'opciones_extraidas.json'
FIXTURES = {
    'TERRITORIAL': ROOT / 'srni-backend' / 'apps' / 'formulario' / 'fixtures' / 'perfil_territorial_v7.json',
    'TELEFONICO':  ROOT / 'srni-backend' / 'apps' / 'formulario' / 'fixtures' / 'perfil_telefonico_v8.json',
}

# Caso especial AT5 (no encontrado en Excel oficial — opciones agropecuarias estándar)
HARDCODED = {
    'TERRITORIAL': {
        'AT5': [
            {'valor': '1', 'etiqueta': 'Cultivos transitorios (yuca, maíz, frijol, etc.)', 'id_resp_vivanto': 0, 'orden': 1},
            {'valor': '2', 'etiqueta': 'Cultivos permanentes (café, cacao, frutales, etc.)', 'id_resp_vivanto': 0, 'orden': 2},
            {'valor': '3', 'etiqueta': 'Pastos / Ganadería',                                  'id_resp_vivanto': 0, 'orden': 3},
            {'valor': '4', 'etiqueta': 'Bosque natural o plantado',                           'id_resp_vivanto': 0, 'orden': 4},
            {'valor': '5', 'etiqueta': 'Vivienda',                                            'id_resp_vivanto': 0, 'orden': 5},
            {'valor': '6', 'etiqueta': 'Recreación o conservación',                           'id_resp_vivanto': 0, 'orden': 6},
            {'valor': '7', 'etiqueta': 'Sin uso productivo',                                  'id_resp_vivanto': 0, 'orden': 7},
            {'valor': '98', 'etiqueta': 'Otro uso',                                           'id_resp_vivanto': 0, 'orden': 8},
        ],
    },
}


def main():
    data = json.loads(DATA.read_text(encoding='utf-8'))

    total_actualizadas = 0
    total_tipo_cambiado = 0
    total_hardcoded = 0
    total_omitidas = 0

    for perfil, items in data.items():
        fixture_path = FIXTURES[perfil]
        fixture = json.loads(fixture_path.read_text(encoding='utf-8'))

        # Indexar preguntas por codigo_externo para búsqueda rápida
        # En las fixtures, "preguntas" es lista top-level (no anidadas en capitulos)
        preguntas_por_codigo = {p.get('codigo_externo'): p for p in fixture.get('preguntas', [])}

        for item in items:
            cod = item['codigo_externo']
            analisis = item['analisis']
            # Si no se encontró en ningún Excel, tratar como NO_ENCONTRADA
            if not analisis.get('encontrada'):
                tipo_det = 'NO_ENCONTRADA'
            else:
                tipo_det = analisis.get('tipo_detectado') or 'NO_ENCONTRADA'
            opciones = analisis.get('opciones', [])

            preg = preguntas_por_codigo.get(cod)
            if not preg:
                print(f'  [SKIP] {perfil} {cod}: no existe en fixture')
                total_omitidas += 1
                continue

            # Aplicar según el tipo detectado
            if tipo_det in ('OPCIONES_CLASICAS', 'MATRIZ_SINO') and opciones:
                preg['opciones'] = opciones
                print(f'  [OK]   {perfil} {cod}: {len(opciones)} opciones aplicadas ({tipo_det})')
                total_actualizadas += 1

            elif tipo_det == 'TEXTO_LIBRE':
                preg['tipo'] = 'TEXTO_LARGO'
                preg['opciones'] = []
                if 'validaciones' not in preg or not preg['validaciones']:
                    preg['validaciones'] = {'max_length': 500}
                print(f'  [TIPO] {perfil} {cod}: LISTA → TEXTO_LARGO (era campo libre en Excel)')
                total_tipo_cambiado += 1

            elif tipo_det == 'NO_ENCONTRADA':
                # Probar hardcoded
                hc = HARDCODED.get(perfil, {}).get(cod)
                if hc:
                    preg['opciones'] = hc
                    print(f'  [HARD] {perfil} {cod}: {len(hc)} opciones hardcoded aplicadas')
                    total_hardcoded += 1
                else:
                    print(f'  [SKIP] {perfil} {cod}: NO_ENCONTRADA y sin hardcoded')
                    total_omitidas += 1
            else:
                print(f'  [SKIP] {perfil} {cod}: tipo={tipo_det} sin acción definida')
                total_omitidas += 1

        # Guardar fixture actualizada
        fixture_path.write_text(
            json.dumps(fixture, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )
        print(f'  -> Guardado: {fixture_path.name}')
        print()

    print(f'═══ RESUMEN ═══')
    print(f'  Opciones aplicadas: {total_actualizadas}')
    print(f'  Tipo cambiado a TEXTO_LARGO: {total_tipo_cambiado}')
    print(f'  Hardcoded (AT5): {total_hardcoded}')
    print(f'  Omitidas: {total_omitidas}')


if __name__ == '__main__':
    main()
