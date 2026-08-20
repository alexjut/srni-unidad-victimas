"""
Motor de skip-logic — UNA sola implementación para todo el backend.

Antes esto vivía dentro de `EvaluarSkipLogicView`, y el resto del backend que
necesitaba lo mismo se lo copiaba: `services/respuestas.py` importaba dos
helpers privados desde `views.py` y se reimplementaba el trigger, y
`SesionEncuesta.recalcular_porcentaje` directamente no evaluaba nada y contaba
TODAS las obligatorias del instrumento.

Eso último es lo que QA reportó como APK-005 —«sesión Completada con la barra en
0 %»— y no era un defecto de la barra: el denominador incluía obligatorias que
la skip-logic mantiene OCULTAS y que por lo tanto nadie puede responder nunca.
Una entrevista legítimamente terminada se guardaba en 55 %, o en 0 % si el
instrumento tenía muchas preguntas condicionales.

La regla que se sigue acá: **el criterio de visibilidad es uno solo**. Si la
vista tuviera el suyo y el modelo otro, el panel web y la APK podrían informar
distinto sobre la misma sesión, que es exactamente el tipo de contradicción que
le hace perder la confianza en el sistema a quien está en campo.

Este módulo es además el espejo de `src/services/skipLogic.ts` del móvil: los
dos tienen que decidir igual sobre los mismos datos.
"""
import ast
import json
import operator as _op

from .models import AccionSkipChoices

# ─── Evaluador AST seguro para expresiones de skip logic ─────────────────────
# Reemplaza eval() — solo permite comparaciones, operadores booleanos y literales.
# Las expresiones provienen de la BD (no de usuarios), pero usar eval() con datos
# externos es mala práctica incluso si la fuente es "confiable".

_CMP_OPS = {
    ast.Eq:    _op.eq,
    ast.NotEq: _op.ne,
    ast.Lt:    _op.lt,
    ast.LtE:   _op.le,
    ast.Gt:    _op.gt,
    ast.GtE:   _op.ge,
    ast.In:    lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

_BOOL_OPS = {
    ast.And: all,
    ast.Or:  any,
}


class ValorDesconocido(Exception):
    """Una variable de la expresión no tiene valor conocido.

    No es un error de programación: es «todavía no sé la edad de esta persona».
    La expresión entera se resuelve como False, que es lo mismo que hace el
    móvil (`_varContexto` devuelve undefined y `_evaluarExpresion` corta).
    """


# `true`/`false`/`null` van en minúscula en las expresiones de los fixtures
# —vienen del diccionario, no de Python—, así que el AST los ve como nombres.
# Sin esto, `ruv_incluido == false` compararía contra un valor desconocido.
_LITERALES = {'true': True, 'false': False, 'null': None, 'none': None}


def _safe_eval(node: ast.AST, ctx: dict):
    """Evalúa un nodo AST restringido a comparaciones y literales."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in _LITERALES:
            return _LITERALES[node.id]
        # Ausente o vacío = desconocido. Antes esto devolvía '', y ese default
        # silencioso decidía mal en la dirección peligrosa: `etnia != 'ninguno'`
        # daba VERDADERO contra el vacío, así que preguntas del capítulo étnico
        # quedaban exigidas a todo el mundo y ninguna sesión llegaba nunca al
        # 100 %. Desconocido tiene que significar «no sé», no «distinto».
        if node.id not in ctx:
            raise ValorDesconocido(node.id)
        valor = ctx[node.id]
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            raise ValorDesconocido(node.id)
        return valor
    if isinstance(node, ast.List):
        return [_safe_eval(el, ctx) for el in node.elts]
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, ctx)
        for cmp_op, comparator in zip(node.ops, node.comparators):
            fn = _CMP_OPS.get(type(cmp_op))
            if fn is None:
                raise ValueError(f'Operador no permitido: {cmp_op}')
            if not fn(left, _safe_eval(comparator, ctx)):
                return False
            left = _safe_eval(comparator, ctx)
        return True
    if isinstance(node, ast.BoolOp):
        fn = _BOOL_OPS.get(type(node.op))
        if fn is None:
            raise ValueError(f'Operador booleano no permitido: {node.op}')
        values = [_safe_eval(v, ctx) for v in node.values]
        return fn(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, ctx)
    raise ValueError(f'Nodo AST no permitido: {type(node).__name__}')


def evaluar_expresion_segura(expresion: str, contexto: dict, respuestas: dict = None) -> bool:
    """Evalúa una expresión de skip logic de forma segura usando AST.

    El ámbito combina las respuestas ya capturadas (indexadas por codigo_externo)
    como base y el contexto de la víctima (edad/sexo/etnia/ruv_incluido) con
    precedencia. Así una expresión puede referenciar la respuesta de OTRA pregunta
    por su código, habilitando condiciones AND mixtas
    (ej. "etnia == 'indigena' and D6 == '2'"). Espejo de _evaluarExpresion (móvil).
    Convención: los valores del lado derecho van entre comillas ('2', 'true').

    Ante cualquier problema devuelve False —variable desconocida, tipos que no
    se comparan, expresión mal escrita—. Es deliberado: una regla que no se
    puede evaluar NO se dispara, así que en el peor caso la pregunta se comporta
    como si su condición no se cumpliera, en vez de reventar la captura en campo.
    """
    try:
        tree = ast.parse(expresion, mode='eval')
        ambito = dict(respuestas or {})
        ambito.update(contexto or {})
        return bool(_safe_eval(tree, ambito))
    except Exception:
        return False


# ─── Motor declarativo ───────────────────────────────────────────────────────

def valores_seleccionados(valor: str) -> list:
    """Descompone la respuesta en los valores seleccionados.

    Array JSON de un multi-select ('["1","3"]') → sus elementos como strings;
    cualquier otra cosa (selección única, texto, booleano) → un único valor escalar.
    Vacío → []. Espejo de _valoresSeleccionados() del móvil (skipLogic.ts).
    """
    s = (valor or "").strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except (ValueError, TypeError):
            pass
        return [s]
    return [s]


def regla_activa(regla, respuestas: dict, contexto: dict = None) -> bool:
    """¿Esta regla se dispara con las respuestas y el contexto actuales?

    `respuestas` va indexado por `codigo_externo`, no por id: es la clave con la
    que están escritas las reglas y la que usa el móvil.
    """
    contexto = contexto or {}

    if regla.pregunta_origen_id:
        valor_actual = respuestas.get(regla.pregunta_origen.codigo_externo, "")
        if not regla.valor_trigger:
            return bool(valor_actual)
        # Soporta origen de selección ÚNICA (escalar) y MÚLTIPLE (LISTA_MULTIPLE,
        # que guarda un array JSON: '["1","3"]'). Dispara si CUALQUIER valor del
        # trigger está entre los seleccionados. Compatible hacia atrás: para un
        # escalar, seleccionados == [valor_actual].
        seleccionados = valores_seleccionados(valor_actual)
        triggers = [v.strip() for v in regla.valor_trigger.split(",")]
        return any(t in seleccionados for t in triggers)

    if regla.expresion_origen:
        return evaluar_expresion_segura(regla.expresion_origen, contexto, respuestas)

    return False


def calcular_visibles(preguntas, reglas, respuestas: dict, contexto: dict = None):
    """Decide qué preguntas están visibles y cuáles son obligatorias.

    Reglas de visibilidad (idénticas a `calcularVisibles` del móvil):
      - Sin reglas entrantes → visible.
      - Con alguna regla HABILITAR entrante → oculta por defecto; se muestra solo
        si esa regla se dispara.
      - DESHABILITAR activa → oculta.
      - OBLIGAR activa → visible Y obligatoria, aunque la pregunta no lo fuera.
      - FINALIZAR activa → cierra el capítulo.

    Devuelve `(visibles, obligatorias, finalizar)` con los dos primeros como
    conjuntos de `codigo_externo`.
    """
    contexto = contexto or {}
    visibles = set()
    obligatorias = set()
    finalizar = False

    # Un índice por pregunta afectada evita recorrer TODAS las reglas por cada
    # pregunta: con ~300 preguntas y ~200 reglas eso era 60.000 comparaciones en
    # un método que corre en cada respuesta guardada.
    entrantes = {}
    for r in reglas:
        if r.pregunta_afectada_id:
            entrantes.setdefault(r.pregunta_afectada_id, []).append(r)

    for pregunta in preguntas:
        reglas_entrantes = entrantes.get(pregunta.pk, [])

        if not reglas_entrantes:
            visibles.add(pregunta.codigo_externo)
            if pregunta.obligatoria:
                obligatorias.add(pregunta.codigo_externo)
            continue

        tiene_habilitar = any(
            r.accion == AccionSkipChoices.HABILITAR for r in reglas_entrantes
        )
        visible = not tiene_habilitar

        for regla in reglas_entrantes:
            if regla_activa(regla, respuestas, contexto):
                if regla.accion == AccionSkipChoices.HABILITAR:
                    visible = True
                elif regla.accion == AccionSkipChoices.DESHABILITAR:
                    visible = False
                elif regla.accion == AccionSkipChoices.OBLIGAR:
                    visible = True
                    obligatorias.add(pregunta.codigo_externo)
                elif regla.accion == AccionSkipChoices.FINALIZAR:
                    finalizar = True

        if visible:
            visibles.add(pregunta.codigo_externo)
            if pregunta.obligatoria:
                obligatorias.add(pregunta.codigo_externo)

    # Reglas FINALIZAR a nivel capítulo (sin pregunta_afectada): se evalúan aparte.
    for regla in reglas:
        if regla.accion == AccionSkipChoices.FINALIZAR and not regla.pregunta_afectada_id:
            if regla_activa(regla, respuestas, contexto):
                finalizar = True

    return visibles, obligatorias, finalizar
