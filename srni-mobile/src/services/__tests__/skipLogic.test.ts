/**
 * Tests unitarios del motor de skip logic (API Sprint 18+).
 * Función pura — sin mocks, sin I/O.
 *
 * calcularVisibles(preguntas, reglas, respuestas) espejo de
 * EvaluarSkipLogicView del backend:
 *   - HABILITAR: oculta por defecto; visible solo si la condición se cumple.
 *   - DESHABILITAR: visible por defecto; oculta si la condición se cumple.
 *   - OBLIGAR: hace la pregunta obligatoria (y visible).
 *   - FINALIZAR: cierra el capítulo cuando se cumple.
 */
import { calcularVisibles, motivoOcultaPregunta } from '../skipLogic';
import type { RespuestasMap } from '../skipLogic';
import type { ReglaSkipLogicRow } from '../../db/instrumentoDao';

// ── Helpers ──────────────────────────────────────────────────────────────────

function pregunta(codigo: string, obligatoria = 0) {
  return { id: `id-${codigo}`, codigo_externo: codigo, obligatoria };
}

function regla(overrides: Partial<ReglaSkipLogicRow>): ReglaSkipLogicRow {
  return {
    id: 'r-1',
    instrumento_id: 'inst-1',
    pregunta_origen_codigo: null,
    valor_trigger: '',
    expresion_origen: '',
    pregunta_afectada_id: null,
    pregunta_afectada_codigo: null,
    capitulo_afectado_id: null,
    accion: 'HABILITAR',
    ...overrides,
  };
}

// ─────────────────────────────────────────────────────────────────────────────

describe('calcularVisibles — sin reglas', () => {
  it('todas las preguntas son visibles', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], [], {});
    expect(r.visibles.has('P1')).toBe(true);
    expect(r.visibles.has('P2')).toBe(true);
    expect(r.finalizar).toBe(false);
  });

  it('las obligatorias del diccionario quedan en el set de obligatorias', () => {
    const r = calcularVisibles([pregunta('P1', 1), pregunta('P2', 0)], [], {});
    expect(r.obligatorias.has('P1')).toBe(true);
    expect(r.obligatorias.has('P2')).toBe(false);
  });
});

describe('calcularVisibles — HABILITAR', () => {
  const reglas = [
    regla({
      accion: 'HABILITAR',
      pregunta_origen_codigo: 'P1',
      valor_trigger: 'SI',
      pregunta_afectada_codigo: 'P2',
    }),
  ];

  it('la pregunta afectada queda OCULTA por defecto', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, {});
    expect(r.visibles.has('P2')).toBe(false);
  });

  it('se muestra cuando la respuesta origen coincide con el trigger', () => {
    const respuestas: RespuestasMap = { P1: 'SI' };
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, respuestas);
    expect(r.visibles.has('P2')).toBe(true);
  });

  it('sigue oculta cuando la respuesta origen NO coincide', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, { P1: 'NO' });
    expect(r.visibles.has('P2')).toBe(false);
  });

  it('una pregunta HABILITAR oculta no aparece en obligatorias aunque lo sea', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2', 1)], reglas, {});
    expect(r.obligatorias.has('P2')).toBe(false);
  });
});

describe('calcularVisibles — DESHABILITAR', () => {
  const reglas = [
    regla({
      accion: 'DESHABILITAR',
      pregunta_origen_codigo: 'P1',
      valor_trigger: 'NO',
      pregunta_afectada_codigo: 'P2',
    }),
  ];

  it('la pregunta afectada es VISIBLE por defecto', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, {});
    expect(r.visibles.has('P2')).toBe(true);
  });

  it('se oculta cuando la condición se cumple', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, { P1: 'NO' });
    expect(r.visibles.has('P2')).toBe(false);
  });
});

describe('calcularVisibles — OBLIGAR', () => {
  const reglas = [
    regla({
      accion: 'OBLIGAR',
      pregunta_origen_codigo: 'P1',
      valor_trigger: 'SI',
      pregunta_afectada_codigo: 'P2',
    }),
  ];

  it('marca la pregunta como obligatoria cuando la condición se cumple', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2', 0)], reglas, { P1: 'SI' });
    expect(r.visibles.has('P2')).toBe(true);
    expect(r.obligatorias.has('P2')).toBe(true);
  });

  it('no la marca cuando la condición no se cumple', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2', 0)], reglas, { P1: 'NO' });
    expect(r.obligatorias.has('P2')).toBe(false);
  });
});

describe('calcularVisibles — FINALIZAR', () => {
  const reglas = [
    regla({
      accion: 'FINALIZAR',
      pregunta_origen_codigo: 'P1',
      valor_trigger: 'NINGUNA',
      pregunta_afectada_codigo: 'P2',
    }),
  ];

  it('activa el flag finalizar cuando la condición se cumple', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, { P1: 'NINGUNA' });
    expect(r.finalizar).toBe(true);
  });

  it('no finaliza cuando la condición no se cumple', () => {
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, { P1: 'ALGUNA' });
    expect(r.finalizar).toBe(false);
  });
});

describe('calcularVisibles — triggers', () => {
  it('trigger multivalor (separado por comas) acepta cualquiera de los valores', () => {
    const reglas = [
      regla({
        accion: 'HABILITAR',
        pregunta_origen_codigo: 'P1',
        valor_trigger: 'A, B, C',
        pregunta_afectada_codigo: 'P2',
      }),
    ];
    const preguntas = [pregunta('P1'), pregunta('P2')];
    expect(calcularVisibles(preguntas, reglas, { P1: 'B' }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles(preguntas, reglas, { P1: 'D' }).visibles.has('P2')).toBe(false);
  });

  it('trigger vacío se dispara con cualquier respuesta no vacía', () => {
    const reglas = [
      regla({
        accion: 'HABILITAR',
        pregunta_origen_codigo: 'P1',
        valor_trigger: '',
        pregunta_afectada_codigo: 'P2',
      }),
    ];
    const preguntas = [pregunta('P1'), pregunta('P2')];
    expect(calcularVisibles(preguntas, reglas, { P1: 'cualquier cosa' }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles(preguntas, reglas, {}).visibles.has('P2')).toBe(false);
  });

  it('valor_trigger null no crashea (bundle defensivo)', () => {
    const reglas = [
      regla({
        accion: 'HABILITAR',
        pregunta_origen_codigo: 'P1',
        valor_trigger: null as unknown as string,
        pregunta_afectada_codigo: 'P2',
      }),
    ];
    const r = calcularVisibles([pregunta('P1'), pregunta('P2')], reglas, { P1: 'X' });
    expect(r.visibles.has('P2')).toBe(true);
  });

  it('expresion_origen sin contexto: variable desconocida → no se dispara', () => {
    const reglas = [
      regla({ accion: 'HABILITAR', pregunta_origen_codigo: null,
        expresion_origen: 'edad > 18', pregunta_afectada_codigo: 'P2' }),
    ];
    const r = calcularVisibles([pregunta('P2')], reglas, {}, {});
    expect(r.visibles.has('P2')).toBe(false);
  });
});

describe('calcularVisibles — expresion_origen con ContextoVictima', () => {
  function reglaExpr(expr: string) {
    return [regla({ accion: 'HABILITAR', pregunta_origen_codigo: null,
      expresion_origen: expr, pregunta_afectada_codigo: 'P2' })];
  }

  it('edad en rango (18-50) muestra la pregunta', () => {
    const reglas = reglaExpr('edad >= 18 and edad <= 50');
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { edad: 30 }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { edad: 60 }).visibles.has('P2')).toBe(false);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { edad: 10 }).visibles.has('P2')).toBe(false);
  });

  it('sexo == 2 (mujer) muestra la pregunta', () => {
    const reglas = reglaExpr("sexo == '2'");
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { sexo: '2' }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { sexo: '1' }).visibles.has('P2')).toBe(false);
  });

  it('etnia == indigena muestra la pregunta (fan-out étnico)', () => {
    const reglas = reglaExpr("etnia == 'indigena'");
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { etnia: 'indigena' }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { etnia: 'rom' }).visibles.has('P2')).toBe(false);
  });

  it('combinación and: hombre 18-50 (libreta militar)', () => {
    const reglas = reglaExpr("sexo == '1' and edad >= 18 and edad <= 50");
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { sexo: '1', edad: 30 }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { sexo: '2', edad: 30 }).visibles.has('P2')).toBe(false);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { sexo: '1', edad: 60 }).visibles.has('P2')).toBe(false);
  });

  it('combinación or: ruv no incluido o menor de 3', () => {
    const reglas = reglaExpr('ruv_incluido == false or edad < 3');
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { ruvIncluido: false, edad: 40 }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { ruvIncluido: true, edad: 2 }).visibles.has('P2')).toBe(true);
    expect(calcularVisibles([pregunta('P2')], reglas, {}, { ruvIncluido: true, edad: 40 }).visibles.has('P2')).toBe(false);
  });
});

describe('calcularVisibles — reglas combinadas sobre la misma pregunta', () => {
  it('HABILITAR cumplida + DESHABILITAR cumplida → gana la última en orden (DESHABILITAR oculta)', () => {
    const reglas = [
      regla({
        id: 'r-hab',
        accion: 'HABILITAR',
        pregunta_origen_codigo: 'P1',
        valor_trigger: 'SI',
        pregunta_afectada_codigo: 'P3',
      }),
      regla({
        id: 'r-des',
        accion: 'DESHABILITAR',
        pregunta_origen_codigo: 'P2',
        valor_trigger: 'NO',
        pregunta_afectada_codigo: 'P3',
      }),
    ];
    const preguntas = [pregunta('P1'), pregunta('P2'), pregunta('P3')];
    const r = calcularVisibles(preguntas, reglas, { P1: 'SI', P2: 'NO' });
    expect(r.visibles.has('P3')).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// motivoOcultaPregunta — motivo legible de "no aplica" en la captura agrupada.
// Se usa para explicar por qué una pregunta PERSONA no aplica a un miembro.
// ─────────────────────────────────────────────────────────────────────────────
describe('motivoOcultaPregunta — pregunta_origen (respuesta previa)', () => {
  it('oculta por defecto (HABILITAR no cumplida) → motivo = requiere X = valor', () => {
    const reglas = [
      regla({ accion: 'HABILITAR', pregunta_origen_codigo: 'B16',
        valor_trigger: '1', pregunta_afectada_codigo: 'H3' }),
    ];
    const m = motivoOcultaPregunta(pregunta('H3'), reglas, { B16: '2' });
    expect(m).toBe('requiere B16 = 1');
  });

  it('trigger multivalor lista los valores con /', () => {
    const reglas = [
      regla({ accion: 'HABILITAR', pregunta_origen_codigo: 'A4',
        valor_trigger: '1,2,3', pregunta_afectada_codigo: 'A5' }),
    ];
    const m = motivoOcultaPregunta(pregunta('A5'), reglas, {});
    expect(m).toBe('requiere A4 = 1 / 2 / 3');
  });

  it('DESHABILITAR activa → motivo = la condición que la ocultó', () => {
    const reglas = [
      regla({ accion: 'DESHABILITAR', pregunta_origen_codigo: 'B16',
        valor_trigger: 'No', pregunta_afectada_codigo: 'H3' }),
    ];
    const m = motivoOcultaPregunta(pregunta('H3'), reglas, { B16: 'No' });
    expect(m).toBe('B16 = No');
  });
});

describe('motivoOcultaPregunta — expresion_origen (demográfico)', () => {
  function reglaExpr(expr: string, afectada = 'P2') {
    return [regla({ accion: 'HABILITAR', pregunta_origen_codigo: null,
      expresion_origen: expr, pregunta_afectada_codigo: afectada })];
  }

  it('edad mínima → "edad ≥ N años"', () => {
    const m = motivoOcultaPregunta(pregunta('P2'), reglaExpr('edad >= 18'), {}, { edad: 10 });
    expect(m).toBe('requiere edad ≥ 18 años');
  });

  it('sexo == 1 → "es hombre"', () => {
    const m = motivoOcultaPregunta(pregunta('P2'), reglaExpr("sexo == '1'"), {}, { sexo: '2' });
    expect(m).toBe('requiere es hombre');
  });

  it('etnia == indigena → "es indígena"', () => {
    const m = motivoOcultaPregunta(pregunta('P2'), reglaExpr("etnia == 'indigena'"), {}, { etnia: 'ninguno' });
    expect(m).toBe('requiere es indígena');
  });

  it('combinación and: hombre 18-49 (libreta militar) se describe con "y"', () => {
    const m = motivoOcultaPregunta(
      pregunta('P2'),
      reglaExpr("sexo == '1' and edad >= 18 and edad <= 49"),
      {}, { sexo: '2', edad: 30 },
    );
    expect(m).toBe('requiere es hombre y edad ≥ 18 años y edad ≤ 49 años');
  });

  it('comparación encadenada "18 <= edad <= 49" → rango legible', () => {
    const m = motivoOcultaPregunta(
      pregunta('P2'),
      reglaExpr("sexo == 'Hombre' and 18 <= edad <= 49"),
      {}, { sexo: '1', edad: 60 },
    );
    expect(m).toBe('requiere es hombre y edad entre 18 y 49 años');
  });

  it('pregunta sin reglas entrantes → undefined (sí aplica / no hay motivo)', () => {
    expect(motivoOcultaPregunta(pregunta('PX'), [], {})).toBeUndefined();
  });
});
