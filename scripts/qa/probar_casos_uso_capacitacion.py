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
El Caso 2 retira del hogar a un integrante. Si lo deja retirado, la siguiente
corrida ya no tiene a quién retirar y el paso pasaría sin haber probado nada
—la peor clase de prueba verde—. Al terminar lo reincorpora, igual que haría un
encuestador que se equivocó de fila.

**Lo que NO hace: cerrar una caracterización.** Sería el único modo de ver
nacer una fila del libro de recaracterizaciones, pero cerrar es irreversible:
escribe la fecha de caracterización en el padrón y no se puede devolver. Este
banco tiene que poder correrse tres veces seguidas. Que la fila se escriba lo
cubren las pruebas del backend; que la consulta responda en producción se
verifica acá, que es lo que sí se puede comprobar sin dejar rastro.

──────────────────────────────────────────────────────────────────────────────
11-SEP-2026 — EL CASO 2 CAMBIÓ DE RAÍZ
──────────────────────────────────────────────────────────────────────────────
Se retiró el control de vigencia. El Caso 2 era «bloquea, coordinación autoriza,
se desbloquea»; ahora es «no bloquea, la familia que ya estaba aparece, y al que
ya no pertenece al hogar se lo retira».

La versión anterior de este banco afirmaba `motivo == FICHA_VIGENTE` en su primer
paso. Contra producción eso ahora es falso, así que fallaba de entrada y los pasos
siguientes ni se ejecutaban.

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
#: La fecha del HECHO del retiro, y no la de hoy: es exactamente la distinción
#: que el caso tiene que enseñar. Fija —no calculada— para que dos corridas del
#: mismo día produzcan el mismo escenario y el aserto sea exacto.
#:
#: `RUTA_EXCEPCION` y `RADICADO_QA` vivían acá hasta el 11-sep-2026: eran del
#: flujo de autorización, que dejó de existir. Se quitaron en vez de dejarlas
#: sin uso, porque una constante huérfana hace buscar dónde se usa.
FECHA_RETIRO_QA = '2026-03-15'
MOTIVO_QA = ('Prueba automatizada del Caso 2 del Anexo C: se reincorpora al '
             'terminar. Si esta observación quedó en el sistema, la corrida se '
             'interrumpió y hay que reincorporar al integrante a mano.')


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
    """
    Persona ya caracterizada, y una familia que cambió.

    Lo que se verifica, en el orden en que lo vive el encuestador:

      1. que la ficha vigente **no lo detenga**, y que quede marcada para el libro;
      2. que el hogar que ya existía vuelva **con su familia**, no vacío;
      3. que se pueda **retirar** a quien ya no pertenece, con la fecha del hecho;
      4. que retirar **no borre** la fila;
      5. que la consulta de supervisión responda;
      6. y que el escenario quede como estaba.
    """
    codigo, doc = fila['codigo'], fila['doc_caso2']

    # 1 — ya no bloquea, y el motivo importa: `ELEGIBLE_SIN_CONTROL_VIGENCIA` es
    #     lo que hace que al cerrar la encuesta se escriba la fila del libro. Con
    #     `ELEGIBLE` a secas la persona se caracterizaría igual y **no quedaría
    #     registrada**, que es el modo de falla silencioso que más importa acá.
    r = consultar(token, doc)
    d = r.datos or {}
    v = d.get('victima') or {}
    ok = (r.codigo == 200 and d.get('encontrado')
          and v.get('habilitado_para_caracterizacion')
          and d.get('motivo') == 'ELEGIBLE_SIN_CONTROL_VIGENCIA')
    bit.anotar(codigo, 'caso 2', f'{doc} ya no la detiene, y queda marcada', ok,
               f'HTTP {r.codigo} motivo={d.get("motivo")!r} '
               f'habilitado={v.get("habilitado_para_caracterizacion")} '
               f'vigente_hasta={d.get("disponible_desde")}')

    # 2 — el hogar que la persona ya tenía, CON su familia. Si volviera con un
    #     solo integrante, el encuestador recapturaría al resto y cada persona
    #     quedaría dos veces en el hogar.
    r = pedir('GET', f'/api/hogares/{fila["hogar"]}/', token=token)
    hogar = r.datos or {}
    miembros = hogar.get('miembros') or []
    municipio = hogar.get('municipio')
    if isinstance(municipio, dict):
        municipio = municipio.get('id')
    if not bit.anotar(codigo, 'caso 2', 'abre el hogar que ya tenía, con su familia',
                      r.codigo == 200 and len(miembros) >= 2,
                      f'HTTP {r.codigo} integrantes={len(miembros)}'):
        return

    # 3 — y conformar tiene que devolver ESE hogar, no crear otro ni responder 409.
    r = pedir('POST', '/api/hogares/', token=token,
              cuerpo={'autorizado': (hogar.get('autorizado') or {}).get('id')
                      or fila.get('victima_caso2'),
                      'municipio': municipio})
    devuelto = (r.datos or {}).get('id')
    bit.anotar(codigo, 'caso 2', 'conformar devuelve el hogar existente (no 409)',
               r.codigo in (200, 201) and devuelto == fila['hogar'],
               f'HTTP {r.codigo} id={devuelto}'
               f'{" — 409: el hogar sigue bloqueando" if r.codigo == 409 else ""}'
               f'{_detalle(r) if r.codigo >= 400 else ""}')

    # 4 — retirar a quien ya no pertenece. Se elige un integrante que NO sea el
    #     autorizado: al titular no se le puede retirar, y probar sobre él mediría
    #     la guarda equivocada.
    otro = next((m for m in miembros if not m.get('es_autorizado')), None)
    if not bit.anotar(codigo, 'caso 2', 'hay un integrante no titular para retirar',
                      otro is not None, f'integrantes={len(miembros)}'):
        return

    mid = otro['id']
    r = pedir('POST', f'/api/hogares/{fila["hogar"]}/miembros/{mid}/retirar/',
              token=token, cuerpo={'motivo': 'FALLECIMIENTO',
                                   'fecha': FECHA_RETIRO_QA,
                                   'observacion': MOTIVO_QA})
    retirado = (r.datos or {}).get('retirado_en')
    if not bit.anotar(codigo, 'caso 2', 'retira del hogar con la fecha del hecho',
                      r.codigo == 200 and retirado == FECHA_RETIRO_QA,
                      f'HTTP {r.codigo} retirado_en={retirado!r} {_detalle(r)}'):
        return

    # 5 — retirar NO es borrar. La fila tiene que seguir ahí: las respuestas de la
    #     caracterización anterior apuntan a ella.
    r = pedir('GET', f'/api/hogares/{fila["hogar"]}/miembros/', token=token)
    lista = r.datos if isinstance(r.datos, list) else []
    sigue = next((m for m in lista if m.get('id') == mid), None)
    bit.anotar(codigo, 'caso 2', 'sigue en el hogar, marcado como retirado',
               sigue is not None and sigue.get('retirado_en') == FECHA_RETIRO_QA,
               f'HTTP {r.codigo} integrantes={len(lista)} '
               f'motivo={(sigue or {}).get("motivo_retiro_display")!r}')

    # 6 — el punto de control tiene que responder. No se comprueba que haya filas:
    #     este banco no cierra encuestas, así que puede estar legítimamente vacío.
    #     Lo que se verifica es que la consulta EXISTA y el perfil la alcance —si
    #     devolviera 403 o 404, el libro no se podría mirar el día que haga falta.
    r = pedir('GET', '/api/recaracterizaciones/resumen/', token=token)
    d = r.datos or {}
    bit.anotar(codigo, 'caso 2', 'la consulta de supervisión responde',
               r.codigo == 200 and 'total' in d,
               f'HTTP {r.codigo} total={d.get("total")} '
               f'personas={d.get("personas_distintas")}')

    # 7 — devolver el escenario a como estaba, o la próxima corrida no tiene a
    #     quién retirar y este caso pasaría sin probar nada.
    r = pedir('POST', f'/api/hogares/{fila["hogar"]}/miembros/{mid}/reincorporar/',
              token=token, cuerpo={})
    bit.anotar(codigo, 'caso 2', 'escenario listo para la próxima corrida',
               r.codigo == 200 and (r.datos or {}).get('retirado_en') is None,
               f'HTTP {r.codigo} {_detalle(r)}')


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
                           # Queda como consulta del histórico: con el control de
                           # vigencia retirado ya nadie autoriza, pero lo otorgado
                           # antes es evidencia y hay que poder verlo.
                           ('histórico de autorizaciones', '/api/habilitaciones/'),
                           # El punto de control que lo reemplaza, y que es lo
                           # ÚNICO que puede responder cuántas recaracterizaciones
                           # se hicieron. Si no abre, el libro no se puede mirar.
                           ('recaracterizaciones', '/api/recaracterizaciones/'),
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
