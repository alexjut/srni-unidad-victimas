"""
Extrae los municipios DANE desde la hoja DIVIPOLA del Excel del Diccionario
Territorial V7 (UARIV) y genera un CSV listo para cargar_departamentos_municipios.

Uso:
    python scripts/extraer_municipios_divipola.py

Salida: srni-backend/data/municipios_dane.csv
Formato CSV: codigo_dane_mun,nombre,codigo_dane_dep
"""
import csv
import os
import sys
import openpyxl


EXCEL_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'docs', 'perfiles', 'Perfil Territorial_web y offline',
    'Diccionario_de_datos__Entrevista de Caracterización_V7_Perfil Territorial.xlsx',
)

SALIDA = os.path.join(os.path.dirname(__file__), '..', 'data', 'municipios_dane.csv')


def main():
    excel_path = os.path.abspath(EXCEL_PATH)
    if not os.path.exists(excel_path):
        print(f'ERROR: no encuentro {excel_path}', file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.load_workbook(excel_path, data_only=True, read_only=True)
    ws = wb['DIVIPOLA']

    municipios = {}
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row or not row[0]:
            continue
        codigo_dep = row[0]
        codigo_mun = row[1]
        nombre_mun = row[4]
        tipo = row[6]
        if tipo != 'CM':
            continue
        if not (codigo_mun and nombre_mun and codigo_dep):
            continue
        codigo_mun = str(codigo_mun).strip()
        codigo_dep = str(codigo_dep).strip().zfill(2)
        municipios[codigo_mun] = (nombre_mun.strip(), codigo_dep)

    os.makedirs(os.path.dirname(os.path.abspath(SALIDA)), exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['codigo_dane_mun', 'nombre_municipio', 'codigo_dane_dep'])
        for codigo_mun in sorted(municipios.keys()):
            nombre, codigo_dep = municipios[codigo_mun]
            w.writerow([codigo_mun, nombre, codigo_dep])

    print(f'Generados {len(municipios)} municipios en {os.path.abspath(SALIDA)}')


if __name__ == '__main__':
    main()
