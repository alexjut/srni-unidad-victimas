/**
 * La clave decide si una pestaña oculta se remonta. Si dos entrevistas distintas
 * dieran la misma clave, la pantalla conservaría el borrador de la anterior
 * (bug de campo: «siempre me sale la entrevista que estaba haciendo»).
 */
jest.mock('expo-router', () => ({ useLocalSearchParams: () => ({}) }));
import { claveDeParams } from '../remontarPorParams';

const CAPITULO = ['temaId', 'sesionServerId', 'borradorId', 'hogarId', 'instrumentoId'] as const;

describe('claveDeParams', () => {
  it('mismo capítulo de OTRA entrevista → clave distinta (se remonta)', () => {
    const a = claveDeParams({ temaId: 'CAP_A', sesionServerId: 'ses-1', hogarId: 'h-1' }, CAPITULO);
    const b = claveDeParams({ temaId: 'CAP_A', sesionServerId: 'ses-2', hogarId: 'h-2' }, CAPITULO);
    expect(a).not.toBe(b);
  });

  it('volver a la misma entrevista y capítulo → misma clave (se conserva)', () => {
    const p = { temaId: 'CAP_A', sesionServerId: 'ses-1', hogarId: 'h-1', instrumentoId: 'i-1' };
    expect(claveDeParams({ ...p }, CAPITULO)).toBe(claveDeParams({ ...p }, CAPITULO));
  });

  it('offline: mismo hogar con otro borrador → clave distinta', () => {
    const a = claveDeParams({ temaId: 'CAP_A', borradorId: 'b-1', hogarId: 'h-1' }, CAPITULO);
    const b = claveDeParams({ temaId: 'CAP_A', borradorId: 'b-2', hogarId: 'h-1' }, CAPITULO);
    expect(a).not.toBe(b);
  });

  it('ignora parámetros que no son de identidad', () => {
    const a = claveDeParams({ hogarId: 'h-1', modo: 'x' }, ['hogarId']);
    const b = claveDeParams({ hogarId: 'h-1', modo: 'y' }, ['hogarId']);
    expect(a).toBe(b);
  });

  it('un parámetro ausente no se confunde con uno vacío de otra posición', () => {
    expect(claveDeParams({ sesionServerId: 'x' }, CAPITULO))
      .not.toBe(claveDeParams({ borradorId: 'x' }, CAPITULO));
  });
});
