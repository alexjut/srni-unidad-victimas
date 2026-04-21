/**
 * Tests unitarios del motor de skip logic.
 * Función pura — sin mocks, sin I/O.
 */
import {
  evaluarOperador,
  calcularVisibles,
  construirPreguntasConCondiciones,
} from '../skipLogic';
import type { Condicion, PreguntaConCondiciones, RespuestasMap } from '../skipLogic';

// ─────────────────────────────────────────────────────────────────────────────
// evaluarOperador
// ─────────────────────────────────────────────────────────────────────────────

describe('evaluarOperador', () => {
  describe('EQ', () => {
    it('devuelve true cuando los valores son iguales', () => {
      expect(evaluarOperador('MASCULINO', 'EQ', 'MASCULINO')).toBe(true);
    });
    it('devuelve false cuando los valores difieren', () => {
      expect(evaluarOperador('FEMENINO', 'EQ', 'MASCULINO')).toBe(false);
    });
    it('es case-sensitive', () => {
      expect(evaluarOperador('masculino', 'EQ', 'MASCULINO')).toBe(false);
    });
  });

  describe('NEQ', () => {
    it('devuelve true cuando los valores difieren', () => {
      expect(evaluarOperador('A', 'NEQ', 'B')).toBe(true);
    });
    it('devuelve false cuando son iguales', () => {
      expect(evaluarOperador('A', 'NEQ', 'A')).toBe(false);
    });
  });

  describe('NOTNULL', () => {
    it('devuelve true para valor no vacío', () => {
      expect(evaluarOperador('algo', 'NOTNULL', '')).toBe(true);
    });
    it('devuelve false para string vacío', () => {
      expect(evaluarOperador('', 'NOTNULL', '')).toBe(false);
    });
    it('devuelve false para solo espacios', () => {
      expect(evaluarOperador('   ', 'NOTNULL', '')).toBe(false);
    });
  });

  describe('GT', () => {
    it('devuelve true cuando el valor es mayor', () => {
      expect(evaluarOperador('5', 'GT', '3')).toBe(true);
    });
    it('devuelve false cuando el valor es igual', () => {
      expect(evaluarOperador('3', 'GT', '3')).toBe(false);
    });
    it('devuelve false cuando el valor es menor', () => {
      expect(evaluarOperador('2', 'GT', '3')).toBe(false);
    });
  });

  describe('GTE', () => {
    it('devuelve true cuando el valor es mayor o igual', () => {
      expect(evaluarOperador('3', 'GTE', '3')).toBe(true);
      expect(evaluarOperador('4', 'GTE', '3')).toBe(true);
    });
    it('devuelve false cuando el valor es menor', () => {
      expect(evaluarOperador('2', 'GTE', '3')).toBe(false);
    });
  });

  describe('LT', () => {
    it('devuelve true cuando el valor es menor', () => {
      expect(evaluarOperador('2', 'LT', '5')).toBe(true);
    });
    it('devuelve false cuando el valor es igual o mayor', () => {
      expect(evaluarOperador('5', 'LT', '5')).toBe(false);
      expect(evaluarOperador('6', 'LT', '5')).toBe(false);
    });
  });

  describe('LTE', () => {
    it('devuelve true cuando el valor es menor o igual', () => {
      expect(evaluarOperador('5', 'LTE', '5')).toBe(true);
      expect(evaluarOperador('4', 'LTE', '5')).toBe(true);
    });
    it('devuelve false cuando el valor es mayor', () => {
      expect(evaluarOperador('6', 'LTE', '5')).toBe(false);
    });
  });

  describe('IN', () => {
    it('devuelve true cuando el valor está en el CSV', () => {
      expect(evaluarOperador('B', 'IN', 'A,B,C')).toBe(true);
    });
    it('devuelve false cuando el valor no está en el CSV', () => {
      expect(evaluarOperador('D', 'IN', 'A,B,C')).toBe(false);
    });
    it('soporta JSON array como valor_condicion', () => {
      expect(evaluarOperador('B', 'IN', '["A","B","C"]')).toBe(true);
      expect(evaluarOperador('D', 'IN', '["A","B","C"]')).toBe(false);
    });
    it('maneja valores con espacios en CSV', () => {
      expect(evaluarOperador('B', 'IN', 'A, B, C')).toBe(true);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// calcularVisibles
// ─────────────────────────────────────────────────────────────────────────────

describe('calcularVisibles', () => {
  it('pregunta sin condiciones siempre es visible', () => {
    const preguntas: PreguntaConCondiciones[] = [{ id: 1, condiciones: [] }];
    const visibles = calcularVisibles(preguntas, {});
    expect(visibles.has(1)).toBe(true);
  });

  it('pregunta con condición no cumplida NO es visible', () => {
    const preguntas: PreguntaConCondiciones[] = [{
      id: 2,
      condiciones: [{
        pregunta_padre_id: 1, pregunta_hija_id: 2,
        operador: 'EQ', valor_condicion: 'SI',
      }],
    }];
    const visibles = calcularVisibles(preguntas, { 1: 'NO' });
    expect(visibles.has(2)).toBe(false);
  });

  it('pregunta con condición cumplida ES visible', () => {
    const preguntas: PreguntaConCondiciones[] = [{
      id: 2,
      condiciones: [{
        pregunta_padre_id: 1, pregunta_hija_id: 2,
        operador: 'EQ', valor_condicion: 'SI',
      }],
    }];
    const visibles = calcularVisibles(preguntas, { 1: 'SI' });
    expect(visibles.has(2)).toBe(true);
  });

  it('basta con que UNA condición se cumpla (OR entre condiciones)', () => {
    const preguntas: PreguntaConCondiciones[] = [{
      id: 3,
      condiciones: [
        { pregunta_padre_id: 1, pregunta_hija_id: 3, operador: 'EQ', valor_condicion: 'A' },
        { pregunta_padre_id: 2, pregunta_hija_id: 3, operador: 'EQ', valor_condicion: 'B' },
      ],
    }];
    // Padre 1 no cumple, padre 2 sí cumple
    const visibles = calcularVisibles(preguntas, { 1: 'X', 2: 'B' });
    expect(visibles.has(3)).toBe(true);
  });

  it('pregunta condicionada con padre sin respuesta NO es visible', () => {
    const preguntas: PreguntaConCondiciones[] = [{
      id: 2,
      condiciones: [{
        pregunta_padre_id: 1, pregunta_hija_id: 2,
        operador: 'NOTNULL', valor_condicion: '',
      }],
    }];
    // padre 1 sin respuesta
    const visibles = calcularVisibles(preguntas, {});
    expect(visibles.has(2)).toBe(false);
  });

  it('pregunta con NOTNULL visible cuando padre tiene valor', () => {
    const preguntas: PreguntaConCondiciones[] = [{
      id: 2,
      condiciones: [{
        pregunta_padre_id: 1, pregunta_hija_id: 2,
        operador: 'NOTNULL', valor_condicion: '',
      }],
    }];
    const visibles = calcularVisibles(preguntas, { 1: 'cualquier_valor' });
    expect(visibles.has(2)).toBe(true);
  });

  it('mezcla de preguntas con y sin condiciones', () => {
    const preguntas: PreguntaConCondiciones[] = [
      { id: 1, condiciones: [] },
      {
        id: 2, condiciones: [{
          pregunta_padre_id: 1, pregunta_hija_id: 2,
          operador: 'EQ', valor_condicion: 'SI',
        }],
      },
      {
        id: 3, condiciones: [{
          pregunta_padre_id: 1, pregunta_hija_id: 3,
          operador: 'EQ', valor_condicion: 'NO',
        }],
      },
    ];
    const visibles = calcularVisibles(preguntas, { 1: 'SI' });
    expect(visibles.has(1)).toBe(true);   // sin condición → siempre visible
    expect(visibles.has(2)).toBe(true);   // condición cumplida
    expect(visibles.has(3)).toBe(false);  // condición no cumplida
  });

  it('condición IN con múltiples valores', () => {
    const preguntas: PreguntaConCondiciones[] = [{
      id: 2,
      condiciones: [{
        pregunta_padre_id: 1, pregunta_hija_id: 2,
        operador: 'IN', valor_condicion: 'CASA,APARTAMENTO',
      }],
    }];
    expect(calcularVisibles(preguntas, { 1: 'CASA' }).has(2)).toBe(true);
    expect(calcularVisibles(preguntas, { 1: 'CAMBUCHE' }).has(2)).toBe(false);
  });

  it('condición GT numérica', () => {
    const preguntas: PreguntaConCondiciones[] = [{
      id: 2,
      condiciones: [{
        pregunta_padre_id: 1, pregunta_hija_id: 2,
        operador: 'GT', valor_condicion: '18',
      }],
    }];
    expect(calcularVisibles(preguntas, { 1: '25' }).has(2)).toBe(true);
    expect(calcularVisibles(preguntas, { 1: '18' }).has(2)).toBe(false);
    expect(calcularVisibles(preguntas, { 1: '15' }).has(2)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// construirPreguntasConCondiciones
// ─────────────────────────────────────────────────────────────────────────────

describe('construirPreguntasConCondiciones', () => {
  it('asigna condiciones correctamente a cada pregunta hija', () => {
    const ids = [1, 2, 3];
    const derivadas: Condicion[] = [
      { pregunta_padre_id: 1, pregunta_hija_id: 2, operador: 'EQ', valor_condicion: 'SI' },
      { pregunta_padre_id: 1, pregunta_hija_id: 3, operador: 'EQ', valor_condicion: 'NO' },
    ];
    const resultado = construirPreguntasConCondiciones(ids, derivadas);

    expect(resultado.find((p) => p.id === 1)?.condiciones).toHaveLength(0);
    expect(resultado.find((p) => p.id === 2)?.condiciones).toHaveLength(1);
    expect(resultado.find((p) => p.id === 3)?.condiciones).toHaveLength(1);
  });

  it('una pregunta puede tener múltiples condiciones', () => {
    const ids = [1, 2, 3];
    const derivadas: Condicion[] = [
      { pregunta_padre_id: 1, pregunta_hija_id: 3, operador: 'EQ', valor_condicion: 'A' },
      { pregunta_padre_id: 2, pregunta_hija_id: 3, operador: 'EQ', valor_condicion: 'B' },
    ];
    const resultado = construirPreguntasConCondiciones(ids, derivadas);
    expect(resultado.find((p) => p.id === 3)?.condiciones).toHaveLength(2);
  });

  it('sin derivadas todas las preguntas quedan sin condiciones', () => {
    const resultado = construirPreguntasConCondiciones([1, 2, 3], []);
    for (const p of resultado) {
      expect(p.condiciones).toHaveLength(0);
    }
  });
});
