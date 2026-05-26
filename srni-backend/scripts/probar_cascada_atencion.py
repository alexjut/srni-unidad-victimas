"""
Probador de la cascada Dirección Territorial -> Depto -> Municipio/Punto.
Uso: python scripts/probar_cascada_atencion.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'srni.settings.development')
django.setup()

import requests
from rest_framework_simplejwt.tokens import RefreshToken
from apps.autenticacion.models import Usuario


def main():
    u = Usuario.objects.get(codigo_usuario='ALEXJUT')
    token = str(RefreshToken.for_user(u).access_token)
    H = {'Authorization': f'Bearer {token}'}
    BASE = 'http://127.0.0.1:8001/api/parametricas'

    # 1) 21 DTs
    r = requests.get(f'{BASE}/direcciones-territoriales/?activo=true&page_size=50',
                     headers=H, timeout=5)
    print(f"1) DTs activas: status={r.status_code} count={r.json().get('count')}")
    dt_atl = next(d for d in r.json()['results'] if d['codigo'] == 'DT_ATLANTICO')
    print(f"   DT_ATLANTICO id={dt_atl['id']}")

    # 2) Deptos de la DT
    r = requests.get(
        f"{BASE}/departamentos/?direcciones_territoriales={dt_atl['id']}&activo=true",
        headers=H, timeout=5,
    )
    deptos = r.json().get('results', [])
    nombres_deptos = [d['nombre'] for d in deptos]
    print(f"2) Deptos de DT_ATLANTICO: status={r.status_code} -> {nombres_deptos}")

    # 3) Municipios del depto
    if not deptos:
        print('   No hay deptos; skip 3 y 4.')
        return
    depto_atl_id = deptos[0]['id']
    r = requests.get(
        f'{BASE}/municipios/?departamento={depto_atl_id}&activo=true&page_size=50',
        headers=H, timeout=5,
    )
    muns_json = r.json()
    primeros = [m['nombre'] for m in muns_json['results'][:3]]
    print(f"3) Municipios de Atlantico: status={r.status_code} "
          f"count={muns_json.get('count')} (primeros 3: {primeros})")

    # 4) Puntos de la DT
    r = requests.get(
        f"{BASE}/puntos-atencion/?direccion_territorial={dt_atl['id']}&activo=true",
        headers=H, timeout=5,
    )
    puntos = [p['nombre'] for p in r.json().get('results', [])]
    print(f"4) Puntos de DT_ATLANTICO: status={r.status_code} -> {puntos}")

    # 5) Caso DT con 3 deptos (CENTRAL = Bogota + Cundinamarca + Tolima)
    r = requests.get(f'{BASE}/direcciones-territoriales/?activo=true&page_size=50',
                     headers=H, timeout=5)
    dt_central = next((d for d in r.json()['results'] if d['codigo'] == 'DT_CENTRAL'), None)
    if dt_central:
        r2 = requests.get(
            f"{BASE}/departamentos/?direcciones_territoriales={dt_central['id']}",
            headers=H, timeout=5,
        )
        print(f"5) Deptos de DT_CENTRAL: {[d['nombre'] for d in r2.json()['results']]}")


if __name__ == '__main__':
    main()
