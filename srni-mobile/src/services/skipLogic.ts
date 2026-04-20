/**
 * Motor de skip logic — evaluador puro sin I/O.
 *
 * Replica la lógica PREDEPENDE/RESHABILITA del APK original.
 * Una pregunta es visible si:
 *   - No tiene condiciones → siempre visible
 *   - Tiene condiciones → al menos UNA condición padre se cumple
 *     (condiciones del mismo padre se evalúan individualmente;
 *      si hay múltiples padres, basta con que uno habilite)
 *
 * Operadores soportados (espejo del backend Django):
 *   EQ | NEQ | GT | GTE | LT | LTE | IN | NOTNULL
 */

export interface Condicion {
  pregunta_padre_id: number;
  pregunta_hija_id: number;
  operador: 'EQ' | 'NEQ' | 'GT' | 'GTE' | 'LT' | 'LTE' | 'IN' | 'NOTNULL';
  valor_condicion: string;
}

export interface PreguntaConCondiciones {
  id: number;
  condiciones: Condicion[];   // condiciones donde esta pregunta es la HIJA
}

/** Respuestas actuales: pregunta_id → valor (string vacío = no respondida) */
export type RespuestasMap = Record<number, string>;

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Evalúa un operador concreto.
 * @param valorRespuesta - Valor respondido por el usuario (puede ser vacío)
 * @param operador
 * @param valorCondicion - Valor de referencia definido en la condición
 */
export function evaluarOperador(
  valorRespuesta: string,
  operador: Condicion['operador'],
  valorCondicion: string,
): boolean {
  switch (operador) {
    case 'EQ':
      return valorRespuesta === valorCondicion;
    case 'NEQ':
      return valorRespuesta !== valorCondicion;
    case 'NOTNULL':
      return valorRespuesta.trim() !== '';
    case 'GT':
      return Number(valorRespuesta) > Number(valorCondicion);
    case 'GTE':
      return Number(valorRespuesta) >= Number(valorCondicion);
    case 'LT':
      return Number(valorRespuesta) < Number(valorCondicion);
    case 'LTE':
      return Number(valorRespuesta) <= Number(valorCondicion);
    case 'IN': {
      // valor_condicion puede ser CSV ("A,B,C") o JSON array ('["A","B"]')
      let opciones: string[];
      try {
        opciones = JSON.parse(valorCondicion);
      } catch {
        opciones = valorCondicion.split(',').map((s) => s.trim());
      }
      return opciones.includes(valorRespuesta);
    }
    default:
      return false;
  }
}

/**
 * Determina qué preguntas son visibles dado el estado actual de respuestas.
 *
 * @param preguntas - Lista de preguntas con sus condiciones de habilitación
 * @param respuestas - Mapa pregunta_id → valor actual
 * @returns Set de IDs de preguntas que deben mostrarse
 */
export function calcularVisibles(
  preguntas: PreguntaConCondiciones[],
  respuestas: RespuestasMap,
): Set<number> {
  const visibles = new Set<number>();

  for (const pregunta of preguntas) {
    if (pregunta.condiciones.length === 0) {
      // Sin condiciones → siempre visible
      visibles.add(pregunta.id);
      continue;
    }

    // Visible si AL MENOS UNA condición se cumple
    const alguna = pregunta.condiciones.some((c) => {
      const valorPadre = respuestas[c.pregunta_padre_id] ?? '';
      return evaluarOperador(valorPadre, c.operador, c.valor_condicion);
    });

    if (alguna) visibles.add(pregunta.id);
  }

  return visibles;
}

/**
 * Construye la estructura PreguntaConCondiciones a partir de las filas crudas
 * de los DAOs (preguntas + derivadas).
 */
export function construirPreguntasConCondiciones(
  preguntaIds: number[],
  derivadas: Condicion[],
): PreguntaConCondiciones[] {
  return preguntaIds.map((id) => ({
    id,
    condiciones: derivadas.filter((d) => d.pregunta_hija_id === id),
  }));
}
