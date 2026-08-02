"""
Verificación del padrón descargable recién generado. SOLO LECTURA.

Comprueba, contra el archivo real y contra PostgreSQL, que se cumple lo que el
diseño promete. Cada bloque imprime OK o FALLA con el dato que lo sustenta, para
que el resultado sea afirmable y no una impresión.
"""
import sys
sys.path.insert(0, '/app')
import json
import os
import sqlite3

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'srni.settings.production')
django.setup()

from django.conf import settings                                    # noqa: E402
from apps.victimas.models import ColisionDocumento, Victima         # noqa: E402
from apps.victimas.repository.base import doc_hash                  # noqa: E402

fallas = []


def check(nombre, condicion, detalle=''):
    estado = 'OK   ' if condicion else 'FALLA'
    if not condicion:
        fallas.append(nombre)
    print(f'  [{estado}] {nombre}{("  — " + detalle) if detalle else ""}', flush=True)


d = os.path.join(str(settings.MEDIA_ROOT), 'padron')
manifiesto = json.load(open(os.path.join(d, 'padron-latest.json'), encoding='utf-8'))
archivo = os.path.join(d, manifiesto['archivo'])
tam = os.path.getsize(archivo)

print('=== MANIFIESTO ===', flush=True)
for k, v in manifiesto.items():
    print(f'  {k}: {v}', flush=True)
print(f'  TAMAÑO REAL: {tam / 1024 / 1024:,.0f} MB', flush=True)

conn = sqlite3.connect(archivo)

print('\n=== 1. Integridad del archivo ===', flush=True)
filas = conn.execute('SELECT count(*) FROM padron').fetchone()[0]
check('el manifiesto declara las filas que el archivo tiene',
      filas == manifiesto['total_registros'], f'archivo {filas:,} · manifiesto {manifiesto["total_registros"]:,}')

idx = conn.execute(
    "SELECT count(*) FROM sqlite_master WHERE type='index' AND tbl_name='padron'").fetchone()[0]
check('hay índice sobre doc_hash', idx >= 1, f'{idx} índice(s)')

pk = conn.execute("SELECT sql FROM sqlite_master WHERE name='padron'").fetchone()[0]
check('doc_hash YA NO es PRIMARY KEY (o se pierde la 2a persona)',
      'PRIMARY KEY' not in pk.upper())

integridad = conn.execute('PRAGMA integrity_check').fetchone()[0]
check('integrity_check', integridad == 'ok', integridad)

print('\n=== 2. Nadie se pierde: los AMBIGUO viajan completos ===', flush=True)
ambiguos_bd = list(ColisionDocumento.objects.filter(clase='AMBIGUO')
                   .values_list('doc_hash', 'personas')[:200])
malos = []
for h, personas in ambiguos_bd:
    n = conn.execute('SELECT count(*) FROM padron WHERE doc_hash = ?', (h,)).fetchone()[0]
    if n < personas:
        malos.append((h[:12], personas, n))
check('cada documento ambiguo lleva al menos una fila por persona',
      not malos, f'{len(malos)} documentos con menos filas de las debidas · muestra {malos[:3]}')

total_ambiguas = conn.execute(
    "SELECT count(*) FROM padron WHERE clase_colision = 'AMBIGUO'").fetchone()[0]
check('el manifiesto reporta bien las filas ambiguas',
      total_ambiguas == manifiesto.get('filas_ambiguas'),
      f'archivo {total_ambiguas:,} · manifiesto {manifiesto.get("filas_ambiguas"):,}')

print('\n=== 3. Los duplicados de la fuente viajan UNA vez ===', flush=True)
dups = list(ColisionDocumento.objects
            .filter(clase__in=('DUPLICADO_FUENTE', 'VARIANTE_NOMBRE'))
            .values_list('doc_hash', 'filas')[:200])
repetidos = []
for h, n_filas in dups:
    n = conn.execute('SELECT count(*) FROM padron WHERE doc_hash = ?', (h,)).fetchone()[0]
    if n != 1:
        repetidos.append((h[:12], n_filas, n))
check('un documento por persona duplicada, no N',
      not repetidos, f'{len(repetidos)} con más de una fila · muestra {repetidos[:3]}')

print('\n=== 4. Los documentos de relleno no llevan datos de nadie ===', flush=True)
no_ident = conn.execute(
    "SELECT count(*), sum(length(nombre)), sum(CASE WHEN cons_persona IS NOT NULL THEN 1 ELSE 0 END) "
    "FROM padron WHERE clase_colision = 'NO_IDENTIFICANTE'").fetchone()
check('ninguna fila de relleno lleva nombre', (no_ident[1] or 0) == 0,
      f'{no_ident[0]} filas, {no_ident[1] or 0} caracteres de nombre')
check('ninguna fila de relleno lleva cons_persona', (no_ident[2] or 0) == 0)

h99 = doc_hash('CC', '99')
n99 = conn.execute('SELECT count(*) FROM padron WHERE doc_hash = ?', (h99,)).fetchone()[0]
check("el documento '99' (CC) deja UNA marca, no 128 filas", n99 <= 1, f'{n99} fila(s)')

print('\n=== 5. Caso conocido: ALBA TAPIA (505 filas en la fuente) ===', flush=True)
alba = ColisionDocumento.objects.filter(filas__gte=400).first()
if alba:
    n = conn.execute('SELECT count(*) FROM padron WHERE doc_hash = ?', (alba.doc_hash,)).fetchone()[0]
    check(f'{alba.filas} filas en la fuente → 1 en el padrón', n == 1,
          f'clase {alba.clase} · {n} fila(s) en el archivo')

print('\n=== 6. Cobertura: cuánta gente hay ===', flush=True)
victimas = Victima.objects.count()
docs_distintos = conn.execute('SELECT count(DISTINCT doc_hash) FROM padron').fetchone()[0]
print(f'  victimas en PostgreSQL:       {victimas:,}', flush=True)
print(f'  filas en el padron:           {filas:,}', flush=True)
print(f'  documentos distintos:         {docs_distintos:,}', flush=True)
print(f'  filas por encima de 1 doc:    {filas - docs_distintos:,}  '
      f'(personas que el colapso ciego habria borrado)', flush=True)

por_clase = dict(conn.execute(
    "SELECT COALESCE(clase_colision,'(limpio)'), count(*) FROM padron GROUP BY 1").fetchall())
for k, v in sorted(por_clase.items(), key=lambda x: -x[1]):
    print(f'    {v:>10,}  {k}', flush=True)

conn.close()

print('\n=== RESULTADO ===', flush=True)
if fallas:
    print(f'  {len(fallas)} VERIFICACIONES FALLIDAS:', flush=True)
    for f in fallas:
        print(f'    - {f}', flush=True)
    sys.exit(1)
print('  Todas las verificaciones pasaron.', flush=True)
