#!/usr/bin/env python
"""
Banco de pruebas de los casos de uso de la capacitación, contra producción.

Corre los tres casos de estudio del Anexo C tal como los va a hacer un
participante, por la misma API que usan la aplicación móvil y el panel, y dice
qué pasó en cada paso. Está pensado para correrse **varias veces seguidas**:
cada corrida deja el escenario como lo encontró.

    python scripts/qa/probar_casos_uso_capacitacion.py --credenciales cred.csv
    python scripts/qa/probar_casos_uso_capacitacion.py --credenciales cred.csv --sesion 1
    python scripts/qa/probar_casos_uso_capacitacion.py --credenciales cred.csv --vueltas 3

──────────────────────────────────────────────────────────────────────────────
POR QUÉ LIMPIA LO QUE CREA
──────────────────────────────────────────────────────────────────────────────
El Caso 2 autoriza una excepción de vigencia. Si la deja puesta, la persona
queda habilitada y **la siguiente corrida ya no ve el bloqueo**: la prueba
pasaría sin haber probado nada, que es la peor clase de prueba verde. Al
terminar cada caso 2 la anula, igual que haría coordinación si se hubiera
autorizado por error.

──────────────────────────────────────────────────────────────────────────────
DOS LÍMITES DEL SERVIDOR QUE HAY QUE RESPETAR
──────────────────────────────────────────────────────────────────────────────
`login` = 5 por minuto **por IP**, no por usuario. Probar siete cuentas seguidas
desde la misma máquina choca contra eso, así que hay una espera entre ingresos.
Es el mismo límite que van a encontrar 15 personas conectadas desde la misma
sala el día de la jornada: ver `--medir-limite-ingreso`.

`busqueda_rni` = 30 por hora por usuario, y solo aplica a `/api/victimas/buscar/`
—el endpoint del panel—. La aplicación móvil usa `consultar-fuente`, que no está
limitado. Por eso el banco usa `buscar` una sola vez por caso 2, para obtener el
identificador de la persona, y todo lo demás por `consultar-fuente`.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

BASE = 'https://caracterizacion.unidadvictimas.gov.co'

#: Espera entre ingresos. El límite es 5/minuto por IP: con 13 segundos van
#: 4,6 por minuto, que deja margen para un reintento sin pasarse.
ESPERA_INGRESO = 13

#: Ruta y radicado que usa el banco al autorizar. El radicado lleva la marca
#: `QA-` para que una autorización de prueba se distinga de una real en la
#: auditoría: la tabla no se limpia, y dentro de un mes nadie va a recordar
#: cuáles salieron de acá.
RUTA_EXCEPCION = 'ACCIONES_CONSTITUCIONALES'
RADICADO_QA = 'QA-CAPACITACION-{codigo}'
MOTIVO_QA = ('Prueba automatizada del Caso 2 del Anexo C. Se anula al terminar. '
             'No corresponde a un soporte real.')


# ───────────────────────────────────────────────────────────────────────────
# Cliente HTTP mínimo
# ───────────────────────────────────────────────────────────────────────────

class Respuesta:
    __slots__ = ('codigo', 'datos', 'error')

    def __init__(self, codigo, datos, error=''):
        self.codigo, self.datos, self.error = codigo, datos, error

    def __repr__(self):
        return f'<{self.codigo}>'


def pedir(metodo, ruta, *, token=None, cuerpo=None, tiempo=45) -> Respuesta:
    """
    Una petición. Nunca lanza: un fallo de red es un resultado de la prueba.

    Devuelve el código y el cuerpo ya interpretado. Los 4xx se devuelven igual
    que los 2xx —son respuestas válidas y a menudo son justo lo que se está
    comprobando—, así que `urllib` no puede tratarlos como excepción.
    """
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    pet.add_header('Content-Type', 'application/json')
    pet.add_header('Accept', 'application/json')
    if token:
        pet.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(pet, timeout=tiempo) as r:
            return Respuesta(r.status, _json(r.read()))
    except urllib.error.HTTPError as e:
        return Respuesta(e.code, _json(e.read()))
    except Exception as e:                       # red, DNS, TLS, tiempo agotado
        return Respuesta(0, None, f'{type(e).__name__}: {e}')


def _json(crudo):
    try:
        return json.loads(crudo.decode('utf-8'))
    except Exception:
        return None


# ───────────────────────────────────────────────────────────────────────────
# Registro de resultados
# ───────────────────────────────────────────────────────────────────────────

class Bitacora:
    """Lo que pasó, en orden, con lo suficiente para reproducirlo."""

    def __init__(self):
        self.filas = []

    def anotar(self, usuario, caso, paso, ok, detalle=''):
        self.filas.append(dict(usuario=usuario, caso=caso, paso=paso,
                               ok=ok, detalle=detalle))
        marca = 'ok  ' if ok else 'FALLA'
        print(f'  {marca} {caso:<8} {paso:<42} {detalle}', flush=True)
        return ok

    @property
    def fallas(self):
        return [f for f in self.filas if not f['ok']]

    def resumen(self):
        print()
        print('═' * 78)
        por_caso = Counter()
        fallas_caso = Counter()
        for f in self.filas:
            por_caso[f['caso']] += 1
            if not f['ok']:
                fallas_caso[f['caso']] += 1
        for caso in sorted(por_caso):
            n, mal = por_caso[caso], fallas_caso[caso]
            estado = 'OK' if not mal else f'{mal} FALLA(S)'
            print(f'  {caso:<10} {n - mal:>3}/{n:<3} {estado}')
        print('─' * 78)
        total, mal = len(self.filas), len(self.fallas)
        print(f'  TOTAL      {total - mal:>3}/{total:<3} '
              f'{"TODO OK" if not mal else str(mal) + " FALLA(S)"}')
        print('═' * 78)
        if self.fallas:
            print()
            print('Fallas, en orden:')
            for f in self.fallas:
                print(f'  · {f["usuario"]:<16} {f["caso"]:<8} {f["paso"]}')
                if f['detalle']:
                    print(f'      {f["detalle"]}')

    def escribir(self, ruta):
        with open(ruta, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=['usuario', 'caso', 'paso', 'ok', 'detalle'])
            w.writeheader()
            w.writerows(self.filas)


# ───────────────────────────────────────────────────────────────────────────
# Los casos
# ───────────────────────────────────────────────────────────────────────────

def consultar(token, documento, ruta=None):
    cuerpo = {'tipo_documento': 'CC', 'numero_documento': documento}
    if ruta:
        cuerpo['ruta_entrevista'] = ruta
    return pedir('POST', '/api/victimas/consultar-fuente/', token=token, cuerpo=cuerpo)


def ingresar(bit, fila):
    """Caso 0 — entrar. Sin esto no hay jornada, así que se prueba aparte."""
    codigo, clave = fila['codigo'], fila['clave']
    r = pedir('POST', '/api/auth/login/',
              cuerpo={'codigo_usuario': codigo, 'password': clave})

    if r.codigo == 429:
        bit.anotar(codigo, 'ingreso', 'POST /api/auth/login/', False,
                   'HTTP 429 — tope de ingresos por IP. No es la clave.')
        return None
    if r.codigo != 200 or not (r.datos or {}).get('access'):
        bit.anotar(codigo, 'ingreso', 'POST /api/auth/login/', False,
                   f'HTTP {r.codigo} {r.error or _detalle(r)}')
        return None

    token = r.datos['access']
    bit.anotar(codigo, 'ingreso', 'POST /api/auth/login/', True, 'token emitido')

    me = pedir('GET', '/api/auth/me/', token=token)
    perfil = ((me.datos or {}).get('perfil') or {}) if me.codigo == 200 else {}
    esperados = ('puede_buscar_rni', 'puede_caracterizar',
                 'puede_ver_reportes', 'puede_autorizar_excepciones')
    faltan = [p for p in esperados if not perfil.get(p)]
    bit.anotar(codigo, 'ingreso', 'perfil con los 4 permisos de la jornada',
               not faltan,
               f'perfil={perfil.get("codigo")}' + (f' · faltan {faltan}' if faltan else ''))
    return token


def caso_1(bit, token, fila):
    """Hogar de tres integrantes, ninguno con ficha previa."""
    codigo = fila['codigo']
    for etiqueta, doc in (('titular', fila['doc_caso1']),
                          ('hijo 14', fila['doc_caso1_hijo']),
                          ('madre 71', fila['doc_caso1_madre'])):
        r = consultar(token, doc)
        d = r.datos or {}
        v = d.get('victima') or {}
        ok = (r.codigo == 200 and d.get('encontrado')
              and v.get('habilitado_para_caracterizacion')
              and d.get('motivo') == 'ELEGIBLE')
        bit.anotar(codigo, 'caso 1', f'{etiqueta} {doc} elegible', ok,
                   f'HTTP {r.codigo} motivo={d.get("motivo")!r} '
                   f'habilitado={v.get("habilitado_para_caracterizacion")}')


def caso_2(bit, token, fila):
    """Ficha vigente: bloquea, coordinación autoriza, se desbloquea, se anula."""
    codigo, doc = fila['codigo'], fila['doc_caso2']

    # 1 — debe estar bloqueada, y el motivo tiene que ser el correcto: es lo que
    #     la aplicación usa para ofrecer «solicitar excepción» en vez de pintar
    #     un error sin salida.
    r = consultar(token, doc)
    d = r.datos or {}
    v = d.get('victima') or {}
    bloqueada = (r.codigo == 200 and d.get('encontrado')
                 and not v.get('habilitado_para_caracterizacion')
                 and d.get('motivo') == 'FICHA_VIGENTE')
    bit.anotar(codigo, 'caso 2', f'{doc} bloqueada por ficha vigente', bloqueada,
               f'HTTP {r.codigo} motivo={d.get("motivo")!r} '
               f'disponible_desde={d.get("disponible_desde")}')

    # 2 — el identificador para autorizar. Es la única llamada al endpoint del
    #     panel, que sí está limitado a 30 por hora.
    r = pedir('POST', '/api/victimas/buscar/', token=token,
              cuerpo={'tipo_documento_codigo': 'CC', 'numero_documento': doc})
    victima_id = (r.datos or {}).get('id')
    if not bit.anotar(codigo, 'caso 2', 'panel encuentra a la persona',
                      bool(victima_id), f'HTTP {r.codigo} id={victima_id}'):
        return

    # 3 — coordinación autoriza
    r = pedir('POST', '/api/habilitaciones/', token=token, cuerpo={
        'victima_id': victima_id, 'ruta': RUTA_EXCEPCION,
        'radicado': RADICADO_QA.format(codigo=codigo), 'observacion': MOTIVO_QA})
    hab_id = (r.datos or {}).get('id')
    if not bit.anotar(codigo, 'caso 2', 'coordinación registra la autorización',
                      r.codigo == 201 and bool(hab_id),
                      f'HTTP {r.codigo} {_detalle(r)}'):
        return

    # 4 — y el celular tiene que verlo. Este es el paso que importa: hubo un
    #     defecto en que se autorizaba en el panel y la aplicación seguía
    #     diciendo «No habilitado».
    r = consultar(token, doc, ruta=RUTA_EXCEPCION)
    d = r.datos or {}
    v = d.get('victima') or {}
    ok = (r.codigo == 200 and v.get('habilitado_para_caracterizacion')
          and d.get('motivo') == 'ELEGIBLE_POR_EXCEPCION')
    bit.anotar(codigo, 'caso 2', 'la aplicación ya la deja caracterizar', ok,
               f'HTTP {r.codigo} motivo={d.get("motivo")!r} '
               f'habilitado={v.get("habilitado_para_caracterizacion")}')

    # 5 — y tiene que poder CONTINUAR. Autorizar y que después el hogar no deje
    #     avanzar es el modo de falla que se reportó en campo el 11-sep: la
    #     excepción levanta la vigencia y no dice nada sobre el hogar, que tiene
    #     su propia regla («una víctima, un hogar no archivado»). Si el hogar es
    #     del propio encuestador el servidor lo reutiliza y responde 200; si es
    #     de otro, responde 409 y el encuestador queda sin salida.
    r = pedir('GET', f'/api/hogares/{fila["hogar"]}/', token=token)
    municipio = (r.datos or {}).get('municipio')
    if isinstance(municipio, dict):
        municipio = municipio.get('id')
    if not bit.anotar(codigo, 'caso 2', 'abre el hogar que ya tenía la persona',
                      r.codigo == 200, f'HTTP {r.codigo}'):
        return

    r = pedir('POST', '/api/hogares/', token=token,
              cuerpo={'autorizado': victima_id, 'municipio': municipio})
    hogar_id = (r.datos or {}).get('id')
    bit.anotar(codigo, 'caso 2', 'puede continuar sobre el hogar (no 409)',
               r.codigo in (200, 201) and hogar_id == fila['hogar'],
               f'HTTP {r.codigo} id={hogar_id} '
               f'{"— 409: autorizada pero bloqueada por el hogar" if r.codigo == 409 else ""}'
               f'{_detalle(r) if r.codigo >= 400 else ""}')

    # 6 — devolver el escenario a como estaba
    r = pedir('POST', f'/api/habilitaciones/{hab_id}/anular/', token=token,
              cuerpo={'motivo': 'Fin de la prueba automatizada: se restablece el bloqueo.'})
    bit.anotar(codigo, 'caso 2', 'se anula y vuelve a quedar bloqueada',
               r.codigo == 200, f'HTTP {r.codigo} {_detalle(r)}')

    r = consultar(token, doc)
    d = r.datos or {}
    v = d.get('victima') or {}
    bit.anotar(codigo, 'caso 2', 'escenario listo para la próxima corrida',
               not v.get('habilitado_para_caracterizacion')
               and d.get('motivo') == 'FICHA_VIGENTE',
               f'motivo={d.get("motivo")!r}')


def caso_3(bit, token, fila):
    """La persona que no aparece: tiene que decirlo, y bien."""
    codigo, doc = fila['codigo'], fila['doc_caso3']
    r = consultar(token, doc)
    d = r.datos or {}
    # Lo que se comprueba no es solo que no la encuentre: es que **no devuelva a
    # otra persona**. Un documento que no existe devolviendo una ficha es el
    # defecto grave, porque el encuestador caracterizaría a un desconocido.
    ok = r.codigo == 200 and not d.get('encontrado') and not d.get('victima')
    bit.anotar(codigo, 'caso 3', f'{doc} no aparece y no devuelve a nadie', ok,
               f'HTTP {r.codigo} encontrado={d.get("encontrado")} '
               f'motivo={d.get("motivo")!r}')


def bloque_b(bit, token, fila):
    """El panel: lo que el participante tiene que poder abrir, y lo que no."""
    codigo = fila['codigo']
    for etiqueta, ruta in (('hogares', '/api/hogares/'),
                           ('encuestas', '/api/encuestas/'),
                           ('autorizaciones', '/api/habilitaciones/'),
                           ('reportes de producción', '/api/reportes/produccion/'),
                           ('auditoría', '/api/auditoria/logs/')):
        r = pedir('GET', ruta, token=token)
        bit.anotar(codigo, 'bloque B', f'abre {etiqueta}', r.codigo == 200,
                   f'HTTP {r.codigo}')

    # El único que NO debe abrir. Un permiso de más no se nota en la jornada y
    # es justo el que no se quiere: administrar usuarios no es del coordinador.
    r = pedir('GET', '/api/usuarios/', token=token)
    bit.anotar(codigo, 'bloque B', 'NO puede administrar usuarios',
               r.codigo == 403, f'HTTP {r.codigo} (se espera 403)')


def _detalle(r):
    d = r.datos
    if isinstance(d, dict):
        return str(d.get('detail') or {k: v for k, v in d.items() if k != 'id'})[:160]
    return (r.error or '')[:160]


# ───────────────────────────────────────────────────────────────────────────
# El límite de ingresos, que es un riesgo del día de la jornada
# ───────────────────────────────────────────────────────────────────────────

def medir_limite_ingreso(bit, filas):
    """
    Cuántos ingresos seguidos aguanta una IP antes del 429.

    El día 15 hay 15 personas en una sala, detrás de una sola salida a internet.
    Si el tope es por IP y son 5 por minuto, la sexta persona que entre entre
    las 8:30 y las 8:31 va a ver «demasiados intentos» con la clave correcta, y
    eso se lee como que las credenciales no sirven. Medirlo antes cuesta un
    minuto; descubrirlo en la sala cuesta la jornada.

    Se usan códigos que NO existen: el bloqueo por intentos fallidos es por
    código de usuario, y gastar cinco fallos contra una cuenta real la dejaría
    bloqueada quince minutos.
    """
    print()
    print('─' * 78)
    print('  Midiendo el tope de ingresos por IP (con códigos inexistentes)')
    print('─' * 78)
    limite = None
    for i in range(1, 9):
        r = pedir('POST', '/api/auth/login/',
                  cuerpo={'codigo_usuario': f'NOEXISTE_QA_{i}', 'password': 'xxxxxxxxxx'})
        print(f'    intento {i}: HTTP {r.codigo}', flush=True)
        if r.codigo == 429:
            limite = i - 1
            break
    if limite is None:
        bit.anotar('(la IP)', 'ingreso', 'tope de ingresos por IP', True,
                   '8 ingresos seguidos sin 429 — el tope no se alcanza en sala')
    else:
        bit.anotar('(la IP)', 'ingreso', 'tope de ingresos por IP', False,
                   f'429 al ingreso número {limite + 1}: solo {limite} personas '
                   f'pueden entrar por minuto desde una misma salida a internet')


# ───────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--credenciales', required=True,
                   help='CSV que produce `preparar_capacitacion --salida`.')
    p.add_argument('--sesion', type=int, choices=[1, 2, 3], default=None)
    p.add_argument('--vueltas', type=int, default=1,
                   help='Cuántas veces repetir todo. Sirve para ver si algo '
                        'pasa la primera vez y falla la segunda.')
    p.add_argument('--solo', default=None,
                   help='Un solo código de usuario, para reproducir un fallo.')
    p.add_argument('--medir-limite-ingreso', action='store_true')
    p.add_argument('--salida', default=None, help='CSV con la bitácora.')
    args = p.parse_args()

    with open(args.credenciales, encoding='utf-8') as fh:
        filas = list(csv.DictReader(fh))
    if args.sesion:
        filas = [f for f in filas if f['sesion'] == str(args.sesion)]
    if args.solo:
        filas = [f for f in filas if f['codigo'] == args.solo]
    if not filas:
        sys.exit('No quedó ningún participante con ese filtro.')

    bit = Bitacora()
    print('═' * 78)
    print(f'CASOS DE USO · {BASE}')
    print(f'{len(filas)} participante(s) × {args.vueltas} vuelta(s)')
    print('═' * 78)

    if args.medir_limite_ingreso:
        medir_limite_ingreso(bit, filas)

    for vuelta in range(1, args.vueltas + 1):
        for i, fila in enumerate(filas):
            print()
            print(f'vuelta {vuelta} · {fila["codigo"]} — {fila["nombre"]}')
            token = ingresar(bit, fila)
            if token:
                caso_1(bit, token, fila)
                caso_2(bit, token, fila)
                caso_3(bit, token, fila)
                bloque_b(bit, token, fila)
            # Entre ingreso e ingreso, para no chocar con el tope por IP. No se
            # espera después del último: nadie más va a entrar.
            if not (vuelta == args.vueltas and i == len(filas) - 1):
                time.sleep(ESPERA_INGRESO)

    bit.resumen()
    if args.salida:
        bit.escribir(args.salida)
        print(f'\nBitácora en {args.salida}')
    sys.exit(1 if bit.fallas else 0)


if __name__ == '__main__':
    main()
