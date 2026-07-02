/**
 * Prueba de paridad — Bug 2 (cap. B DATOS BÁSICOS): embarazo (B2) → "¿Cuántas?"
 * (B2_CANT) y lactante (B2A) sin tope de 50. Usa el bundle REAL patcheado y el
 * motor real (calcularVisibles), replicando la evaluación por-miembro del
 * formulario (contexto edad/sexo de cada miembro).
 */
import { calcularVisibles } from '../skipLogic';
import type { ReglaSkipLogicRow, PreguntaRow } from '../../db/instrumentoDao';
import bundle from '../../../assets/instrumentos/buenaventura_v7.json';

// Preguntas del cap B en el shape mínimo que consume el motor.
const capB = bundle.capitulos.find((c: any) => c.codigo === 'B')!;
const preguntas = capB.preguntas.map((p: any) => ({
  id: p.id, codigo_externo: p.codigo_externo, obligatoria: p.obligatoria ? 1 : 0,
})) as Pick<PreguntaRow, 'id' | 'codigo_externo' | 'obligatoria'>[];
const reglas = bundle.reglas as unknown as ReglaSkipLogicRow[];

const visiblesCodigos = (respuestas: Record<string, string>, contexto: any) => {
  const { visibles } = calcularVisibles(preguntas, reglas, respuestas, contexto);
  return visibles;
};

describe('cap B — embarazo (B2), gestación (B2_CANT) y lactante (B2A)', () => {
  it('mujer de 60 años: embarazo y lactante VISIBLES (lactante ya no topa en 50)', () => {
    const vis = visiblesCodigos({}, { sexo: '2', edad: 60 });
    expect(vis.has('B2')).toBe(true);
    expect(vis.has('B2A')).toBe(true);
    expect(vis.has('B2_CANT')).toBe(false); // aún no responde "Sí"
  });

  it('mujer de 10 años: embarazo y lactante OCULTOS (piso de 12 avalado por Alejandro)', () => {
    const vis = visiblesCodigos({}, { sexo: '2', edad: 10 });
    expect(vis.has('B2')).toBe(false);
    expect(vis.has('B2A')).toBe(false);
  });

  it('mujer de 12 años: embarazo y lactante VISIBLES (justo en el piso)', () => {
    const vis = visiblesCodigos({}, { sexo: '2', edad: 12 });
    expect(vis.has('B2')).toBe(true);
    expect(vis.has('B2A')).toBe(true);
  });

  it('hombre: embarazo, gestación y lactante OCULTOS', () => {
    const vis = visiblesCodigos({}, { sexo: '1', edad: 30 });
    expect(vis.has('B2')).toBe(false);
    expect(vis.has('B2A')).toBe(false);
    expect(vis.has('B2_CANT')).toBe(false);
  });

  it('mujer que responde embarazo = "Sí" (1): aparece el campo "¿Cuántas?" (B2_CANT)', () => {
    const vis = visiblesCodigos({ B2: '1' }, { sexo: '2', edad: 25 });
    expect(vis.has('B2_CANT')).toBe(true);
  });

  it('mujer que responde embarazo = "No" (2): NO aparece "¿Cuántas?"', () => {
    const vis = visiblesCodigos({ B2: '2' }, { sexo: '2', edad: 25 });
    expect(vis.has('B2_CANT')).toBe(false);
  });
});
