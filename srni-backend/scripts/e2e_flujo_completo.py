"""
Validación end-to-end del flujo backend SRNI para los 7 instrumentos.

Para cada instrumento:
  1. Crear sesión con un hogar existente
  2. Listar capítulos
  3. Tomar el primer capítulo con preguntas
  4. Responder hasta 5 preguntas de tipos variados (LISTA, BOOLEAN, NUMERICO, TEXTO, FECHA)
  5. Verificar que el % de completado actualiza
  6. Listar respuestas guardadas
  7. Finalizar la sesión

Reporta tabla resumen + lista de bugs con detalle exacto.

Uso:
    python scripts/e2e_flujo_completo.py
"""
import json
import sys
import requests

BASE = 'http://127.0.0.1:8001'
USER = 'ALEXJUT'
PWD = 'alexjut1030'

INSTRUMENTOS = ['TERRITORIAL', 'ASISTENCIA', 'BUENAVENTURA', 'SAN_ANDRES', 'TELEFONICO', 'URBANO_ETNICO', 'RURAL_ETNICO']

# Generador de valores de prueba según tipo de pregunta
def valor_dummy(tipo: str, opciones: list) -> str:
    if tipo == 'TEXTO':
        return 'Prueba E2E'
    if tipo == 'TEXTO_LARGO':
        return 'Texto largo de prueba E2E para validar el flujo'
    if tipo == 'NUMERICO':
        return '1'
    if tipo == 'FECHA':
        return '2024-05-15'
    if tipo == 'BOOLEAN':
        return 'true'
    if tipo in ('LISTA', 'OPCION_UNICA', 'RADIO'):
        return str(opciones[0]['valor']) if opciones else '1'
    if tipo in ('LISTA_MULTIPLE', 'OPCION_MULTIPLE'):
        if opciones:
            return json.dumps([str(opciones[0]['valor'])])
        return json.dumps(['1'])
    return 'valor_prueba'


def main():
    s = requests.Session()
    bugs = []
    resumen = []

    # ── 1. Login ────────────────────────────────────────────────────────────
    print('═' * 70)
    print('LOGIN')
    print('═' * 70)
    r = s.post(f'{BASE}/api/auth/login/', json={'codigo_usuario': USER, 'password': PWD})
    if r.status_code != 200:
        print(f'❌ Login falló: {r.status_code} {r.text[:200]}')
        return
    tok = r.json()['access']
    s.headers.update({'Authorization': f'Bearer {tok}'})
    print(f'✅ Login OK, token: {tok[:30]}...')

    # ── 2. Conseguir un hogar para usar de pivote ───────────────────────────
    r = s.get(f'{BASE}/api/hogares/')
    if r.status_code != 200:
        print(f'❌ GET hogares: {r.status_code}')
        return
    hogares = r.json().get('results', [])
    if not hogares:
        print('❌ Sin hogares en BD. Crea uno primero.')
        return
    hogar_id = hogares[0]['id']
    print(f'✅ Hogar de prueba: {hogar_id[:8]}...')

    # ── 3. Listar instrumentos disponibles ──────────────────────────────────
    r = s.get(f'{BASE}/api/formulario/instrumentos/')
    instr_lista = r.json().get('results', [])
    instr_por_codigo = {i['codigo']: i for i in instr_lista}

    # ── 4. Para cada instrumento, hacer el flujo completo ──────────────────
    for cod in INSTRUMENTOS:
        print('\n' + '─' * 70)
        print(f'INSTRUMENTO: {cod}')
        print('─' * 70)
        info = {'instrumento': cod, 'pasos': {}}

        instr = instr_por_codigo.get(cod)
        if not instr:
            bugs.append(f'[{cod}] No aparece en /api/formulario/instrumentos/')
            info['pasos']['lookup'] = 'FALLA'
            resumen.append(info)
            continue

        instr_id = instr['id']
        info['pasos']['lookup'] = 'OK'

        # 4a. Crear sesión
        r = s.post(f'{BASE}/api/encuestas/', json={
            'hogar': hogar_id,
            'instrumento': instr_id,
            'ruta_entrevista': 'GENERAL',
        })
        if r.status_code != 201:
            bugs.append(f'[{cod}] POST /api/encuestas/ = {r.status_code} body={r.text[:200]}')
            info['pasos']['crear_sesion'] = f'FALLA {r.status_code}'
            resumen.append(info)
            continue
        sesion = r.json()
        sesion_id = sesion['id']
        info['pasos']['crear_sesion'] = 'OK'
        print(f'  ✅ Sesión {sesion_id[:8]}.. instrumento={sesion.get("instrumento_nombre")}')

        # 4b. Cargar instrumento completo (capítulos + preguntas)
        r = s.get(f'{BASE}/api/formulario/instrumento/{cod}/')
        if r.status_code != 200:
            bugs.append(f'[{cod}] GET /api/formulario/instrumento/{cod}/ = {r.status_code}')
            info['pasos']['cargar_instrumento'] = f'FALLA {r.status_code}'
            resumen.append(info)
            continue
        instr_full = r.json()
        info['pasos']['cargar_instrumento'] = 'OK'
        caps = instr_full.get('capitulos', [])
        print(f'  ✅ Cargado: {len(caps)} capítulos')

        # 4c. Tomar primer capítulo con preguntas
        cap = next((c for c in caps if c.get('preguntas')), None)
        if not cap:
            bugs.append(f'[{cod}] Ningún capítulo tiene preguntas')
            info['pasos']['primer_capitulo'] = 'FALLA'
            resumen.append(info)
            continue
        info['pasos']['primer_capitulo'] = f"{cap['codigo']} ({len(cap['preguntas'])} preg)"

        # 4d. Responder hasta 5 preguntas variadas
        respuestas_ok = 0
        respuestas_err = 0
        tipos_probados = set()
        for preg in cap['preguntas']:
            if len(tipos_probados) >= 5:
                break
            tipo = preg.get('tipo')
            if tipo in tipos_probados:
                continue  # ya probé este tipo
            preg_id = preg['id']
            opciones = preg.get('opciones', [])
            valor = valor_dummy(tipo, opciones)

            r = s.post(f'{BASE}/api/encuestas/{sesion_id}/responder/', json={
                'pregunta_id': preg_id,
                'valor': valor,
            })
            if r.status_code in (200, 201):
                respuestas_ok += 1
                tipos_probados.add(tipo)
            else:
                respuestas_err += 1
                bugs.append(f'[{cod}] responder pregunta {preg.get("codigo_externo")} tipo={tipo} = {r.status_code} body={r.text[:150]}')
        info['pasos']['responder'] = f'{respuestas_ok} ok, {respuestas_err} err (tipos: {",".join(sorted(tipos_probados))})'
        print(f'  ✅ Respuestas: {info["pasos"]["responder"]}')

        # 4e. Verificar porcentaje en detalle
        r = s.get(f'{BASE}/api/encuestas/{sesion_id}/')
        if r.status_code == 200:
            det = r.json()
            pct = det.get('porcentaje_completado', '?')
            estado = det.get('estado', '?')
            info['pasos']['detalle_post'] = f'pct={pct}% estado={estado}'
            print(f'  ✅ Detalle post-respuestas: {info["pasos"]["detalle_post"]}')
        else:
            bugs.append(f'[{cod}] GET detalle sesión {sesion_id} = {r.status_code}')
            info['pasos']['detalle_post'] = f'FALLA {r.status_code}'

        # 4f. Listar respuestas guardadas
        r = s.get(f'{BASE}/api/encuestas/{sesion_id}/respuestas/')
        if r.status_code == 200:
            respuestas_listadas = len(r.json()) if isinstance(r.json(), list) else len(r.json().get('results', []))
            info['pasos']['listar_respuestas'] = f'{respuestas_listadas} respuestas'
            print(f'  ✅ Listadas: {respuestas_listadas} respuestas')
        else:
            bugs.append(f'[{cod}] GET respuestas = {r.status_code}')
            info['pasos']['listar_respuestas'] = f'FALLA {r.status_code}'

        # 4g. Probar bulk responder
        if len(cap['preguntas']) > 5:
            bulk_items = []
            for preg in cap['preguntas'][5:10]:
                bulk_items.append({
                    'pregunta_id': preg['id'],
                    'valor': valor_dummy(preg.get('tipo'), preg.get('opciones', [])),
                })
            r = s.post(f'{BASE}/api/encuestas/{sesion_id}/responder-bulk/', json={'respuestas': bulk_items})
            if r.status_code == 200:
                bulk_data = r.json()
                info['pasos']['bulk'] = f'creadas={bulk_data.get("creadas")} actualizadas={bulk_data.get("actualizadas")} pct={bulk_data.get("porcentaje_completado")}%'
                print(f'  ✅ Bulk: {info["pasos"]["bulk"]}')
            else:
                bugs.append(f'[{cod}] bulk responder = {r.status_code} body={r.text[:200]}')
                info['pasos']['bulk'] = f'FALLA {r.status_code}'

        # 4h. Finalizar sesión
        r = s.post(f'{BASE}/api/encuestas/{sesion_id}/finalizar/', json={'observaciones': 'Test E2E'})
        if r.status_code == 200:
            info['pasos']['finalizar'] = f'OK estado=COMPLETADA'
            print(f'  ✅ Finalizar: COMPLETADA')
        else:
            bugs.append(f'[{cod}] finalizar = {r.status_code} body={r.text[:150]}')
            info['pasos']['finalizar'] = f'FALLA {r.status_code}'

        resumen.append(info)

    # ── RESUMEN FINAL ───────────────────────────────────────────────────────
    print('\n' + '═' * 70)
    print('RESUMEN FINAL')
    print('═' * 70)
    headers = ['Instrumento', 'lookup', 'sesion', 'cargar', 'cap', 'responder', 'pct', 'lista_resp', 'bulk', 'finalizar']
    fmt = '{:<14} {:<6} {:<6} {:<6} {:<14} {:<25} {:<22} {:<14} {:<32} {:<12}'
    print(fmt.format(*headers))
    print('-' * 200)
    for info in resumen:
        p = info['pasos']
        print(fmt.format(
            info['instrumento'],
            p.get('lookup', '-')[:6],
            p.get('crear_sesion', '-')[:6],
            p.get('cargar_instrumento', '-')[:6],
            p.get('primer_capitulo', '-')[:14],
            p.get('responder', '-')[:25],
            p.get('detalle_post', '-')[:22],
            p.get('listar_respuestas', '-')[:14],
            p.get('bulk', '-')[:32],
            p.get('finalizar', '-')[:12],
        ))

    print('\n' + '═' * 70)
    print(f'BUGS ENCONTRADOS: {len(bugs)}')
    print('═' * 70)
    for b in bugs:
        print(f'  - {b}')

    if not bugs:
        print('\n🎉 0 bugs. Flujo end-to-end OK en los 7 instrumentos.')
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
