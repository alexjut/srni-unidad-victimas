/**
 * Motor de skip logic offline — evaluador puro sin I/O.
 *
 * Replica exactamente la lógica del backend (EvaluarSkipLogicView):
 *   - HABILITAR: pregunta oculta por defecto; visible solo si la condición se cumple.
 *   - DESHABILITAR: pregunta visible por defecto; oculta si la condición se cumple.
 *   - OBLIGAR: hace la pregunta obligatoria (y visible).
 *   - FINALIZAR: cierra el capítulo cuando se cumple.
 *
 * Dos tipos de condición:
 *   - pregunta_origen_codigo + valor_trigger → depende de la respuesta a otra pregunta.
 *   - expresion_origen → depende del CONTEXTO de la víctima (edad, sexo, etnia, RUV).
 *     Ej: "edad >= 18 and edad <= 50", "sexo == '1'", "etnia == 'indigena'".
 *     Antes NO se evaluaba offline; ahora sí, con el ContextoVictima.
 *
 * Identificadores: código_externo (strings del diccionario V8).
 */

import type { ReglaSkipLogicRow, PreguntaRow } from '../db/instrumentoDao';

// ─── Tipos públicos ───────────────────────────────────────────────────────────

/** Mapa de respuestas: codigo_externo → valor actual ('' si sin respuesta) */
export type RespuestasMap = Record<string, string>;

/**
 * Contexto de la víctima para evaluar expresiones demográficas/étnicas offline.
 * Se arma desde VictimaResumenFuente (datos que el RUV ya tiene).
 */
export interface ContextoVictima {
  edad?: number;          // años cumplidos
  sexo?: string;          // '1'=hombre, '2'=mujer (valores del diccionario A8)
  etnia?: string;         // 'indigena' | 'negro_afro' | 'rom' | 'ninguno'
  ruvIncluido?: boolean;  // incluido en el RUV
}

export interface ResultadoSkipLogic {
  visibles: Set<string>;      // Set de codigo_externo visibles
  obligatorias: Set<string>;  // Set de codigo_externo ahora obligatorias
  finalizar: boolean;
}

// ─── Motor ────────────────────────────────────────────────────────────────────

/**
 * Determina qué preguntas son visibles dado el estado actual de respuestas
 * y el contexto de la víctima. Espejo de EvaluarSkipLogicView.post() del backend.
 */
export function calcularVisibles(
  preguntas: Pick<PreguntaRow, 'id' | 'codigo_externo' | 'obligatoria'>[],
  reglas: ReglaSkipLogicRow[],
  respuestas: RespuestasMap,
  contexto: ContextoVictima = {},
): ResultadoSkipLogic {
  const visibles = new Set<string>();
  const obligatorias = new Set<string>();
  let finalizar = false;

  for (const pregunta of preguntas) {
    const reglasEntrantes = reglas.filter(
      (r) => r.pregunta_afectada_codigo === pregunta.codigo_externo,
    );

    if (reglasEntrantes.length === 0) {
      visibles.add(pregunta.codigo_externo);
      if (pregunta.obligatoria) obligatorias.add(pregunta.codigo_externo);
      continue;
    }

    const tieneHabilitar = reglasEntrantes.some((r) => r.accion === 'HABILITAR');
    let visible = !tieneHabilitar;

    for (const regla of reglasEntrantes) {
      if (_reglaActiva(regla, respuestas, contexto)) {
        if (regla.accion === 'HABILITAR') {
          visible = true;
        } else if (regla.accion === 'DESHABILITAR') {
          visible = false;
        } else if (regla.accion === 'OBLIGAR') {
          visible = true;
          obligatorias.add(pregunta.codigo_externo);
        } else if (regla.accion === 'FINALIZAR') {
          finalizar = true;
        }
      }
    }

    if (visible) {
      visibles.add(pregunta.codigo_externo);
      if (pregunta.obligatoria) obligatorias.add(pregunta.codigo_externo);
    }
  }

  // Reglas FINALIZAR a nivel capítulo (sin pregunta_afectada): se evalúan aparte.
  for (const regla of reglas) {
    if (regla.accion === 'FINALIZAR' && !regla.pregunta_afectada_codigo) {
      if (_reglaActiva(regla, respuestas, contexto)) finalizar = true;
    }
  }

  return { visibles, obligatorias, finalizar };
}

/**
 * Descompone la respuesta en los valores seleccionados:
 *   - array JSON de multi-select ('["1","3"]') → sus elementos como strings;
 *   - cualquier otra cosa (selección única, texto, booleano) → un único valor escalar.
 * Vacío → []. Espejo de _valores_seleccionados() del backend.
 */
function _valoresSeleccionados(raw: string): string[] {
  const s = (raw ?? '').trim();
  if (!s) return [];
  if (s.startsWith('[')) {
    try {
      const arr = JSON.parse(s);
      return Array.isArray(arr) ? arr.map((x) => String(x)) : [s];
    } catch {
      return [s];
    }
  }
  return [s];
}

/** Evalúa si una regla debe dispararse. Espejo de _regla_activa() del backend. */
function _reglaActiva(
  regla: ReglaSkipLogicRow,
  respuestas: RespuestasMap,
  contexto: ContextoVictima,
): boolean {
  if (regla.pregunta_origen_codigo) {
    const valorActual = respuestas[regla.pregunta_origen_codigo] ?? '';
    if (!regla.valor_trigger) return !!valorActual;
    // Soporta origen de selección ÚNICA (escalar) y MÚLTIPLE (LISTA_MULTIPLE, que
    // guarda un array JSON: '["1","3"]'). La regla dispara si CUALQUIER valor del
    // trigger está entre los seleccionados. Compatible hacia atrás: para un escalar,
    // seleccionados = [valorActual] → equivale a la comparación anterior.
    const seleccionados = _valoresSeleccionados(valorActual);
    const triggers = regla.valor_trigger.split(',').map((v) => v.trim());
    return triggers.some((t) => seleccionados.includes(t));
  }
  // expresion_origen — se evalúa con el contexto de la víctima (edad/sexo/etnia/RUV)
  // Y, además, puede referenciar la respuesta de OTRA pregunta por su codigo_externo,
  // lo que permite condiciones AND mixtas (ej. "etnia == 'indigena' and D6 == '2'").
  if (regla.expresion_origen) {
    return _evaluarExpresion(regla.expresion_origen, contexto, respuestas);
  }
  return false;
}

// ─── Evaluador de expresiones (seguro, sin eval) ────────────────────────────────

/**
 * Evalúa expresiones simples del diccionario contra el contexto de la víctima
 * y, opcionalmente, contra las respuestas ya capturadas.
 * Soporta: and / or · operadores < <= > >= == != · variables edad, sexo, etnia,
 * ruv_incluido · valores numéricos, 'string' entre comillas, true/false ·
 * REFERENCIA a otra pregunta por su codigo_externo (cualquier nombre que no sea
 * una variable de contexto se busca en `respuestas`).
 * Ejemplos: "edad >= 18 and edad <= 50" · "sexo == '2'" · "etnia == 'indigena'"
 *           · "etnia == 'indigena' and D6 == '2'"  (AND étnico + respuesta).
 * Para orígenes multi-select (respuesta = array JSON), == / != son pertenencia.
 */
export function _evaluarExpresion(
  expr: string,
  ctx: ContextoVictima,
  respuestas: RespuestasMap = {},
): boolean {
  const e = expr.trim();
  if (!e) return false;
  // Precedencia: OR (más bajo) → AND → comparación.
  const ors = e.split(/\s+or\s+/i);
  if (ors.length > 1) return ors.some((p) => _evaluarExpresion(p, ctx, respuestas));
  const ands = e.split(/\s+and\s+/i);
  if (ands.length > 1) return ands.every((p) => _evaluarExpresion(p, ctx, respuestas));

  const m = e.match(/^(\w+)\s*(<=|>=|==|!=|<|>)\s*(.+)$/);
  if (!m) return false;
  const [, nombre, op, rawVal] = m;
  const izq = _varContexto(nombre, ctx, respuestas);
  if (izq === undefined || izq === null) return false;
  const der = _parseValor(rawVal.trim());
  // Origen multi-select: la respuesta es un array JSON ('["1","3"]') → == / != es pertenencia.
  if (typeof izq === 'string' && izq.trim().startsWith('[')) {
    const sel = _valoresSeleccionados(izq);
    const dv = String(der);
    if (op === '==') return sel.includes(dv);
    if (op === '!=') return !sel.includes(dv);
  }
  return _comparar(izq, op, der);
}

function _varContexto(
  nombre: string,
  ctx: ContextoVictima,
  respuestas: RespuestasMap = {},
): number | string | boolean | undefined {
  switch (nombre) {
    case 'edad': return ctx.edad;
    case 'sexo': return ctx.sexo;
    case 'etnia': return ctx.etnia;
    case 'ruv_incluido': return ctx.ruvIncluido;
    // Cualquier otro nombre se interpreta como codigo_externo de otra pregunta:
    // se busca su respuesta. undefined si aún no fue respondida (condición → false).
    default: {
      const v = respuestas[nombre];
      return v === undefined || v === '' ? undefined : v;
    }
  }
}

function _parseValor(raw: string): number | string | boolean {
  if (/^'.*'$/.test(raw) || /^".*"$/.test(raw)) return raw.slice(1, -1);
  if (raw === 'true') return true;
  if (raw === 'false') return false;
  const n = Number(raw);
  return Number.isNaN(n) ? raw : n;
}

function _comparar(izq: number | string | boolean, op: string, der: number | string | boolean): boolean {
  if (op === '==') return String(izq) === String(der);
  if (op === '!=') return String(izq) !== String(der);
  // comparaciones de orden: numéricas
  const a = Number(izq), b = Number(der);
  if (Number.isNaN(a) || Number.isNaN(b)) return false;
  switch (op) {
    case '<':  return a < b;
    case '<=': return a <= b;
    case '>':  return a > b;
    case '>=': return a >= b;
    default:   return false;
  }
}

// ─── Motivo legible de "no aplica" (Sprint — captura agrupada) ──────────────────
//
// En la captura agrupada, cada pregunta PERSONA se muestra UNA vez con una fila
// por miembro. Cuando la pregunta NO aplica a un miembro (no quedó visible al
// evaluar con el contexto/respuestas de ESE miembro), se muestra la fila en gris
// con un MOTIVO. Esta función deriva ese motivo a partir de las reglas entrantes,
// SIN re-evaluar visibilidad (eso lo hace calcularVisibles): aquí solo se explica.
//
// No altera el motor: es puramente descriptivo. Cubre los casos comunes
// (respuesta previa, edad, sexo, étnico). Si no logra derivar uno específico,
// devuelve un motivo genérico ("no cumple la condición").

/** Etiqueta humana para el valor de sexo del diccionario ('1'/'2'/'Hombre'…). */
function _etiquetaSexo(raw: string): string {
  const v = raw.replace(/^['"]|['"]$/g, '');
  if (v === '1' || /hombre/i.test(v)) return 'hombre';
  if (v === '2' || /mujer/i.test(v)) return 'mujer';
  if (v === '3') return 'intersexual';
  return v;
}

/** Etiqueta humana para el valor de etnia ('indigena'/'negro_afro'/'rom'/'ninguno'). */
function _etiquetaEtnia(raw: string): string {
  const v = raw.replace(/^['"]|['"]$/g, '');
  switch (v) {
    case 'indigena':   return 'indígena';
    case 'negro_afro': return 'negro/afro';
    case 'rom':        return 'Rom/gitano';
    case 'ninguno':    return 'sin pertenencia étnica';
    default:           return v;
  }
}

/** Traduce un átomo de comparación (edad/sexo/etnia/ruv) a texto legible. */
function _atomoLegible(atomo: string): string {
  const e = atomo.trim();
  // ruv_incluido (solo, sin comparación) → "incluido en el RUV"
  if (/^ruv_incluido$/i.test(e)) return 'requiere estar incluido en el RUV';
  // comparación encadenada "18 <= edad <= 49"
  const enc = e.match(/^(\d+)\s*(<=|<)\s*edad\s*(<=|<)\s*(\d+)$/i);
  if (enc) return `edad entre ${enc[1]} y ${enc[4]} años`;
  const m = e.match(/^(\w+)\s*(<=|>=|==|!=|<|>)\s*(.+)$/);
  if (!m) return e;
  const [, nombre, op, rawValRaw] = m;
  const rawVal = rawValRaw.trim();
  if (nombre === 'edad') {
    const txt: Record<string, string> = { '>=': 'edad ≥', '>': 'edad >', '<=': 'edad ≤', '<': 'edad <', '==': 'edad =', '!=': 'edad ≠' };
    return `${txt[op] ?? 'edad'} ${rawVal} años`;
  }
  if (nombre === 'sexo') {
    return op === '!=' ? `no es ${_etiquetaSexo(rawVal)}` : `es ${_etiquetaSexo(rawVal)}`;
  }
  if (nombre === 'etnia') {
    return op === '!=' ? `no es ${_etiquetaEtnia(rawVal)}` : `es ${_etiquetaEtnia(rawVal)}`;
  }
  if (nombre === 'ruv_incluido') {
    const val = rawVal.toLowerCase();
    return val === 'true' ? 'incluido en el RUV' : 'no incluido en el RUV';
  }
  return e;
}

/** Convierte una expresion_origen completa (con and/or) a texto legible. */
function _expresionLegible(expr: string): string {
  const e = expr.trim();
  if (!e) return 'no cumple la condición';
  const ors = e.split(/\s+or\s+/i);
  if (ors.length > 1) return ors.map((p) => _expresionLegible(p)).join(' o ');
  const ands = e.split(/\s+and\s+/i);
  if (ands.length > 1) return ands.map((p) => _atomoLegible(p)).join(' y ');
  return _atomoLegible(e);
}

/** Describe la condición de UNA regla en términos legibles (origen del motivo). */
function _condicionLegible(regla: ReglaSkipLogicRow): string {
  if (regla.pregunta_origen_codigo) {
    const trig = (regla.valor_trigger ?? '').trim();
    if (!trig) return `depende de ${regla.pregunta_origen_codigo}`;
    const valores = trig.includes(',')
      ? trig.split(',').map((v) => v.trim()).join(' / ')
      : trig;
    return `${regla.pregunta_origen_codigo} = ${valores}`;
  }
  if (regla.expresion_origen) return _expresionLegible(regla.expresion_origen);
  return 'no cumple la condición';
}

/**
 * Deriva el motivo legible por el que una pregunta PERSONA NO aplica a un
 * miembro. Recibe el mismo contexto/respuestas con que se evaluó visibilidad
 * para ESE miembro. Devuelve undefined si la pregunta en realidad SÍ aplica
 * (no debería llamarse en ese caso) o si no hay reglas que la oculten.
 *
 *   - Si está oculta por defecto (tiene HABILITAR pero ninguna se cumplió):
 *     motivo = la condición de la regla HABILITAR (requisito para que aparezca).
 *   - Si una DESHABILITAR se cumplió: motivo = esa condición (la que la ocultó).
 */
export function motivoOcultaPregunta(
  pregunta: Pick<PreguntaRow, 'codigo_externo'>,
  reglas: ReglaSkipLogicRow[],
  respuestas: RespuestasMap,
  contexto: ContextoVictima = {},
): string | undefined {
  const entrantes = reglas.filter(
    (r) => r.pregunta_afectada_codigo === pregunta.codigo_externo,
  );
  if (entrantes.length === 0) return undefined;

  // 1) ¿Una DESHABILITAR activa la ocultó? Ese es el motivo más directo.
  const deshabilitan = entrantes.filter((r) => r.accion === 'DESHABILITAR');
  for (const r of deshabilitan) {
    if (_reglaActiva(r, respuestas, contexto)) {
      return _condicionLegible(r);
    }
  }

  // 2) Oculta por defecto: tiene HABILITAR/OBLIGAR pero ninguna se cumplió.
  //    El motivo es el REQUISITO no satisfecho (la condición que la mostraría).
  const habilitan = entrantes.filter(
    (r) => r.accion === 'HABILITAR' || r.accion === 'OBLIGAR',
  );
  if (habilitan.length > 0) {
    const condiciones = habilitan.map((r) => _condicionLegible(r));
    // Si hay varias rutas para habilitarla, se listan como alternativas.
    const unicas = [...new Set(condiciones)];
    return `requiere ${unicas.join(' o ')}`;
  }

  return 'no cumple la condición';
}
