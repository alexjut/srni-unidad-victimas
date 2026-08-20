/**
 * Tests del servicio de progreso offline — fix #8/#18.
 *
 * El bug: el denominador usaba el conteo estático de obligatorias, que incluye
 * obligatorias OCULTAS por skip-logic → el progreso nunca llegaba a 100%.
 * Estos tests fijan el contrato: el denominador son OBLIGATORIAS VISIBLES.
 *
 * Función pura — sin mocks, sin I/O.
 */
import { calcularProgresoOffline } from '../progreso';
import type { PreguntaRow, ReglaSkipLogicRow, CapituloRow } from '../../db/instrumentoDao';

// ── Helpers ──────────────────────────────────────────────────────────────────

function cap(id: string, nivel: 'HOGAR' | 'PERSONA' = 'HOGAR'): CapituloRow {
  return { id, codigo: id, nombre: id, orden: 0, nivel, activo: 1 };
}

function preg(
  codigo: string,
  opts: { nivel?: 'HOGAR' | 'PERSONA'; obligatoria?: 0 | 1 } = {},
): PreguntaRow {
  return {
    id: `id-${codigo}`,
    capitulo_id: 'C1',
    codigo_externo: codigo,
    no_pregunta: '',
    texto: codigo,
    descripcion_ayuda: '',
    tipo: 'TEXTO',
    nivel: opts.nivel ?? 'HOGAR',
    orden: 0,
    obligatoria: opts.obligatoria ?? 1,
    activa: 1,
    validaciones: '{}',
  };
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

/** Construye un getPreguntas a partir de un mapa capId → preguntas. */
function lookup(porCap: Record<string, PreguntaRow[]>) {
  return (capId: string) => porCap[capId] ?? [];
}

// ─────────────────────────────────────────────────────────────────────────────

describe('calcularProgresoOffline — HOGAR sin skip-logic', () => {
  const capitulos = [cap('C1')];
  const preguntas = { C1: [preg('P1'), preg('P2')] };

  it('0 respondidas → 0%', () => {
    const r = calcularProgresoOffline(capitulos, lookup(preguntas), [], [], {});
    expect(r.obligVisibles).toBe(2);
    expect(r.obligRespondidas).toBe(0);
    expect(r.progreso).toBe(0);
    expect(r.porCapitulo.C1.estado).toBe('pendiente');
  });

  it('todas respondidas → 100% y completado', () => {
    const r = calcularProgresoOffline(capitulos, lookup(preguntas), [], [], {
      'id-P1|': 'a',
      'id-P2|': 'b',
    });
    expect(r.obligRespondidas).toBe(2);
    expect(r.progreso).toBe(1);
    expect(r.capsCompletados).toBe(1);
    expect(r.porCapitulo.C1.estado).toBe('completado');
  });
});

describe('calcularProgresoOffline — obligatoria oculta por HABILITAR (el bug)', () => {
  // P2 obligatoria pero OCULTA hasta que P1 === 'SI'. Con el conteo estático el
  // denominador sería 2 y jamás llegaría a 100%. Con visibilidad real es 1.
  const capitulos = [cap('C1')];
  const preguntas = { C1: [preg('P1'), preg('P2')] };
  const reglas = [
    regla({ accion: 'HABILITAR', pregunta_origen_codigo: 'P1', valor_trigger: 'SI', pregunta_afectada_codigo: 'P2' }),
  ];

  it('P2 oculta no infla el denominador → responder P1 da 100%', () => {
    const r = calcularProgresoOffline(capitulos, lookup(preguntas), reglas, [], { 'id-P1|': 'NO' });
    expect(r.obligVisibles).toBe(1); // solo P1
    expect(r.obligRespondidas).toBe(1);
    expect(r.progreso).toBe(1);
    expect(r.porCapitulo.C1.estado).toBe('completado');
  });

  it('al disparar la condición, P2 aparece y baja el progreso', () => {
    const r = calcularProgresoOffline(capitulos, lookup(preguntas), reglas, [], { 'id-P1|': 'SI' });
    expect(r.obligVisibles).toBe(2); // P1 + P2 ahora visible
    expect(r.obligRespondidas).toBe(1); // P2 aún sin responder
    expect(r.progreso).toBe(0.5);
    expect(r.porCapitulo.C1.estado).toBe('en_progreso');
  });
});

describe('calcularProgresoOffline — PERSONA × miembros', () => {
  const capitulos = [cap('C1', 'PERSONA')];
  const preguntas = { C1: [preg('PP', { nivel: 'PERSONA' })] };
  const miembros = [{ id: 'm1' }, { id: 'm2' }];

  it('cuenta la obligatoria PERSONA una vez por miembro', () => {
    const r = calcularProgresoOffline(capitulos, lookup(preguntas), [], miembros, {
      'id-PP|m1': 'x',
    });
    expect(r.obligVisibles).toBe(2); // 1 pregunta × 2 miembros
    expect(r.obligRespondidas).toBe(1); // solo m1
    expect(r.progreso).toBe(0.5);
  });

  it('sin miembros usa un miembro fantasma (cuenta 1×)', () => {
    const r = calcularProgresoOffline(capitulos, lookup(preguntas), [], [], {});
    expect(r.obligVisibles).toBe(1);
    expect(r.obligRespondidas).toBe(0);
  });
});

describe('calcularProgresoOffline — no obligatorias no bloquean el total', () => {
  const capitulos = [cap('C1'), cap('C2')];
  const preguntas = {
    C1: [preg('P1', { obligatoria: 1 })],
    C2: [preg('Q1', { obligatoria: 0 })], // capítulo sin obligatorias
  };

  it('C2 (sin obligatorias) no entra al denominador y no impide 100%', () => {
    const r = calcularProgresoOffline(capitulos, lookup(preguntas), [], [], { 'id-P1|': 'a' });
    expect(r.obligVisibles).toBe(1);
    expect(r.progreso).toBe(1);
    expect(r.capsConObligatorias).toBe(1);
    expect(r.porCapitulo.C2.estado).toBe('pendiente'); // sin obligatorias → neutro
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Reglas por expresión: edad, sexo, RUV
//
// Este bloque existe por un defecto que estuvo vivo en las DOS capas a la vez:
// `calcularProgresoOffline` llamaba a `calcularVisibles` sin contexto, así que
// ninguna regla demográfica se disparaba. El denominador dejaba fuera el bloque
// de gestación/maternidad y la barra decía 100 % con la entrevista incompleta.
//
// El backend tenía el mismo agujero (`recalcular_porcentaje`). Los dos se
// arreglaron juntos: tienen que decidir igual sobre los mismos datos, o el
// panel y la APK informan distinto sobre la misma sesión.
// ─────────────────────────────────────────────────────────────────────────────

describe('calcularProgresoOffline — reglas por expresión', () => {
  const preguntas = [
    preg('A1', { nivel: 'PERSONA' }),
    preg('B2', { nivel: 'PERSONA' }),
  ];
  const capitulos = [cap('C1')];
  const reglas = [regla({
    expresion_origen: "sexo == '2' and edad >= 12",
    pregunta_afectada_codigo: 'B2',
    accion: 'HABILITAR',
  })];

  it('el bloque de gestación se le exige a ella y no a él', () => {
    const miembros = [
      { id: 'm1', genero: 'F', fecha_nacimiento: '1995-01-01' },
      { id: 'm2', genero: 'M', fecha_nacimiento: '1990-01-01' },
    ];
    const r = calcularProgresoOffline(capitulos, lookup({ C1: preguntas }), reglas, miembros, {
      'id-A1|m1': 'x',
      'id-A1|m2': 'x',
    });
    // A1 de cada uno (2) + B2 solo de ella (1) = 3. Respondidas: 2.
    expect(r.obligVisibles).toBe(3);
    expect(r.obligRespondidas).toBe(2);
  });

  it('a la menor de 12 no se le abre el bloque', () => {
    const miembros = [{ id: 'm1', genero: 'F', fecha_nacimiento: '2020-01-01' }];
    const r = calcularProgresoOffline(capitulos, lookup({ C1: preguntas }), reglas, miembros, {
      'id-A1|m1': 'x',
    });
    expect(r.obligVisibles).toBe(1);
    expect(r.progreso).toBe(1);
  });

  it('sin género conocido la regla no dispara — no afirma nada', () => {
    // El género del padrón no se hereda: acierta la mitad de las veces.
    const miembros = [{ id: 'm1', genero: '', fecha_nacimiento: '1990-01-01' }];
    const r = calcularProgresoOffline(capitulos, lookup({ C1: preguntas }), reglas, miembros, {
      'id-A1|m1': 'x',
    });
    expect(r.obligVisibles).toBe(1);
  });

  it('la edad respondida (B9) manda sobre la registrada', () => {
    const preguntasB9 = [
      preg('B9', { nivel: 'PERSONA' }),
      preg('X1', { nivel: 'PERSONA' }),
    ];
    const reglasEdad = [regla({
      expresion_origen: 'edad >= 18',
      pregunta_afectada_codigo: 'X1',
      accion: 'HABILITAR',
    })];
    // Registrada como menor, pero el encuestador capturó 40.
    const miembros = [{ id: 'm1', genero: 'F', fecha_nacimiento: '2015-01-01' }];
    const r = calcularProgresoOffline(capitulos, lookup({ C1: preguntasB9 }), reglasEdad, miembros, {
      'id-B9|m1': '40',
    });
    expect(r.obligVisibles).toBe(2);
    expect(r.obligRespondidas).toBe(1);
  });

  it('etnia distinta de ninguno no exige el capítulo étnico', () => {
    // La etnia se pregunta, no se hereda: el contexto la fija en 'ninguno'.
    // Con la variable en blanco, `etnia != 'ninguno'` daba verdadero y la
    // pregunta quedaba exigida a todo el mundo sin que nadie pudiera verla.
    const preguntasEtnia = [preg('A1', { nivel: 'PERSONA' }), preg('C7', { nivel: 'PERSONA' })];
    const reglasEtnia = [regla({
      expresion_origen: "etnia != 'ninguno'",
      pregunta_afectada_codigo: 'C7',
      accion: 'HABILITAR',
    })];
    const miembros = [{ id: 'm1', genero: 'F', fecha_nacimiento: '1990-01-01' }];
    const r = calcularProgresoOffline(capitulos, lookup({ C1: preguntasEtnia }), reglasEtnia, miembros, {
      'id-A1|m1': 'x',
    });
    expect(r.obligVisibles).toBe(1);
    expect(r.progreso).toBe(1);
  });

  it('las preguntas HOGAR se evalúan con el contexto del autorizado', () => {
    // Si se usara "el primero de la lista", el mismo hogar daría dos progresos
    // distintos según el orden en que vinieran los integrantes.
    const preguntasHogar = [preg('A1'), preg('H1')];
    const reglasHogar = [regla({
      expresion_origen: "sexo == '2'",
      pregunta_afectada_codigo: 'H1',
      accion: 'HABILITAR',
    })];
    const miembros = [
      { id: 'm1', genero: 'M', fecha_nacimiento: '1990-01-01' },
      { id: 'm2', genero: 'F', fecha_nacimiento: '1985-01-01', es_autorizado: true },
    ];
    const r = calcularProgresoOffline(capitulos, lookup({ C1: preguntasHogar }), reglasHogar, miembros, {
      'id-A1|': 'x',
    });
    // La autorizada es mujer → H1 aplica y falta.
    expect(r.obligVisibles).toBe(2);
    expect(r.obligRespondidas).toBe(1);

    // Invertir el orden no cambia nada.
    const invertido = calcularProgresoOffline(
      capitulos, lookup({ C1: preguntasHogar }), reglasHogar, [...miembros].reverse(),
      { 'id-A1|': 'x' },
    );
    expect(invertido.obligVisibles).toBe(2);
    expect(invertido.obligRespondidas).toBe(1);
  });
});
