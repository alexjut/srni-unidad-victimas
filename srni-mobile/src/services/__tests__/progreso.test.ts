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
