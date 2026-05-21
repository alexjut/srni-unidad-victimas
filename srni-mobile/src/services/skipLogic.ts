/**
 * Motor de skip logic offline — evaluador puro sin I/O.
 *
 * Replica exactamente la lógica del backend (EvaluarSkipLogicView):
 *   - HABILITAR: pregunta oculta por defecto; visible solo si la condición se cumple.
 *   - DESHABILITAR: pregunta visible por defecto; oculta si la condición se cumple.
 *   - OBLIGAR: hace la pregunta obligatoria (y visible).
 *   - FINALIZAR: cierra el capítulo cuando se cumple.
 *
 * Identificadores: código_externo (strings del diccionario V8).
 */

import type { ReglaSkipLogicRow, PreguntaRow } from '../db/instrumentoDao';

// ─── Tipos públicos ───────────────────────────────────────────────────────────

/** Mapa de respuestas: codigo_externo → valor actual ('' si sin respuesta) */
export type RespuestasMap = Record<string, string>;

export interface ResultadoSkipLogic {
  visibles: Set<string>;      // Set de codigo_externo visibles
  obligatorias: Set<string>;  // Set de codigo_externo ahora obligatorias
  finalizar: boolean;
}

// ─── Motor ────────────────────────────────────────────────────────────────────

/**
 * Determina qué preguntas son visibles dado el estado actual de respuestas.
 * Espejo exacto de EvaluarSkipLogicView.post() del backend.
 */
export function calcularVisibles(
  preguntas: Pick<PreguntaRow, 'id' | 'codigo_externo' | 'obligatoria'>[],
  reglas: ReglaSkipLogicRow[],
  respuestas: RespuestasMap,
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
      if (_reglaActiva(regla, respuestas)) {
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

  return { visibles, obligatorias, finalizar };
}

/** Evalúa si una regla debe dispararse. Espejo de _regla_activa() del backend. */
function _reglaActiva(regla: ReglaSkipLogicRow, respuestas: RespuestasMap): boolean {
  if (regla.pregunta_origen_codigo) {
    const valorActual = respuestas[regla.pregunta_origen_codigo] ?? '';
    if (!regla.valor_trigger) return !!valorActual;
    const trigger = regla.valor_trigger;
    if (trigger.includes(',')) {
      return trigger.split(',').map((v) => v.trim()).includes(valorActual);
    }
    return valorActual === trigger;
  }
  // expresion_origen — no evaluable offline sin contexto de edad/RUV
  return false;
}
