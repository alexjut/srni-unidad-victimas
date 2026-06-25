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

/** Evalúa si una regla debe dispararse. Espejo de _regla_activa() del backend. */
function _reglaActiva(
  regla: ReglaSkipLogicRow,
  respuestas: RespuestasMap,
  contexto: ContextoVictima,
): boolean {
  if (regla.pregunta_origen_codigo) {
    const valorActual = respuestas[regla.pregunta_origen_codigo] ?? '';
    if (!regla.valor_trigger) return !!valorActual;
    const trigger = regla.valor_trigger;
    if (trigger.includes(',')) {
      return trigger.split(',').map((v) => v.trim()).includes(valorActual);
    }
    return valorActual === trigger;
  }
  // expresion_origen — se evalúa con el contexto de la víctima (edad/sexo/etnia/RUV).
  if (regla.expresion_origen) {
    return _evaluarExpresion(regla.expresion_origen, contexto);
  }
  return false;
}

// ─── Evaluador de expresiones (seguro, sin eval) ────────────────────────────────

/**
 * Evalúa expresiones simples del diccionario contra el contexto de la víctima.
 * Soporta: and / or · operadores < <= > >= == != · variables edad, sexo, etnia,
 * ruv_incluido · valores numéricos, 'string' entre comillas, true/false.
 * Ejemplos: "edad >= 18 and edad <= 50" · "sexo == '2'" · "etnia == 'indigena'".
 */
export function _evaluarExpresion(expr: string, ctx: ContextoVictima): boolean {
  const e = expr.trim();
  if (!e) return false;
  // Precedencia: OR (más bajo) → AND → comparación.
  const ors = e.split(/\s+or\s+/i);
  if (ors.length > 1) return ors.some((p) => _evaluarExpresion(p, ctx));
  const ands = e.split(/\s+and\s+/i);
  if (ands.length > 1) return ands.every((p) => _evaluarExpresion(p, ctx));

  const m = e.match(/^(\w+)\s*(<=|>=|==|!=|<|>)\s*(.+)$/);
  if (!m) return false;
  const [, nombre, op, rawVal] = m;
  const izq = _varContexto(nombre, ctx);
  if (izq === undefined || izq === null) return false;
  const der = _parseValor(rawVal.trim());
  return _comparar(izq, op, der);
}

function _varContexto(nombre: string, ctx: ContextoVictima): number | string | boolean | undefined {
  switch (nombre) {
    case 'edad': return ctx.edad;
    case 'sexo': return ctx.sexo;
    case 'etnia': return ctx.etnia;
    case 'ruv_incluido': return ctx.ruvIncluido;
    default: return undefined;
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
