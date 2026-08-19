/**
 * Regresiones de borradoresDao — los filtros que hacían desaparecer trabajo.
 *
 * Acá se prueba la consulta que sale hacia SQLite, no el resultado: el mock de
 * expo-sqlite no ejecuta SQL. Y está bien que sea así, porque el defecto vivía
 * exactamente en el WHERE — las tres veces se perdió trabajo capturado por una
 * condición de más.
 */
const mockGetAllAsync = jest.fn();
const mockGetFirstAsync = jest.fn();
const mockRunAsync = jest.fn();
jest.mock('../schema', () => ({
  openDb: jest.fn().mockResolvedValue({
    getAllAsync: (...a: unknown[]) => mockGetAllAsync(...a),
    getFirstAsync: (...a: unknown[]) => mockGetFirstAsync(...a),
    runAsync: (...a: unknown[]) => mockRunAsync(...a),
  }),
}));

import {
  listarBorradores,
  findBorradorOfflinePorHogarInstrumento,
  marcarCerradoLocal,
  marcarCompletado,
} from '../borradoresDao';

/** Normaliza saltos de línea e indentación para poder buscar frases sueltas. */
function sqlDe(mock: jest.Mock): string {
  return String(mock.mock.calls[0][0]).replace(/\s+/g, ' ').trim();
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetAllAsync.mockReset().mockResolvedValue([]);
  mockGetFirstAsync.mockReset().mockResolvedValue(null);
  mockRunAsync.mockReset().mockResolvedValue({ changes: 1 });
});

describe('listarBorradores', () => {
  it('no esconde el borrador cuya sesión ya se creó en el servidor', async () => {
    // 'SINCRONIZADO' lo escribe marcarSincronizado apenas la cola logra CREAR la
    // sesión, con las respuestas todavía sin subir. Filtrar por ese estado hacía
    // que la entrevista desapareciera de la lista, y sin red tampoco tenía
    // tarjeta de servidor: quedaba invisible por los dos lados.
    await listarBorradores();
    expect(sqlDe(mockGetAllAsync)).not.toContain('SINCRONIZADO');
  });

  it('no esconde la entrevista que se finalizó sin señal', async () => {
    // Finalizar sin red deja el borrador en CERRADO_LOCAL con el FINALIZAR
    // todavía en cola. Es trabajo pendiente de ella: tiene que seguir en lista.
    await listarBorradores();
    expect(sqlDe(mockGetAllAsync)).not.toContain('CERRADO_LOCAL');
  });

  it('excluye solo el borrador que el servidor ya confirmó cerrado', async () => {
    await listarBorradores();
    expect(sqlDe(mockGetAllAsync)).toContain("estado != 'COMPLETADO'");
  });
});

describe('findBorradorOfflinePorHogarInstrumento', () => {
  it('encuentra el borrador aunque ya esté vinculado a una sesión', async () => {
    // Con `sesion_id IS NULL` en el WHERE, volver a entrar por un hogar ya
    // sincronizado no encontraba su borrador y el formulario creaba uno EN
    // BLANCO: los capítulos aparecían en 0/N y la entrevista quedaba partida en
    // dos filas con el mismo sesion_id.
    await findBorradorOfflinePorHogarInstrumento('hogar-1', 'instr-1');
    expect(sqlDe(mockGetFirstAsync)).not.toContain('sesion_id IS NULL');
  });

  it('encuentra el borrador finalizado sin señal, para no abrir uno en blanco al lado', async () => {
    await findBorradorOfflinePorHogarInstrumento('hogar-1', 'instr-1');
    expect(sqlDe(mockGetFirstAsync)).not.toContain('CERRADO_LOCAL');
  });

  it('busca por hogar + instrumento y descarta el ya cerrado contra el servidor', async () => {
    await findBorradorOfflinePorHogarInstrumento('hogar-1', 'instr-1');
    const sql = sqlDe(mockGetFirstAsync);
    expect(sql).toContain('hogar_id = ?');
    expect(sql).toContain('instrumento_id = ?');
    expect(sql).toContain("estado != 'COMPLETADO'");
    expect(mockGetFirstAsync.mock.calls[0][1]).toEqual(['hogar-1', 'instr-1']);
  });

  it('devuelve el más reciente cuando hay más de uno', async () => {
    await findBorradorOfflinePorHogarInstrumento('hogar-1', 'instr-1');
    const sql = sqlDe(mockGetFirstAsync);
    expect(sql).toContain('ORDER BY updated_at DESC');
    expect(sql).toContain('LIMIT 1');
  });
});

describe('cierre local vs cierre confirmado', () => {
  // Son dos hechos distintos y confundirlos costó una entrevista entera: hasta
  // la v1.2.1, finalizar en modo avión escribía COMPLETADO antes de que nada
  // saliera del teléfono, y los dos WHERE de arriba la daban por cerrada.
  it('marcarCerradoLocal NO escribe COMPLETADO', async () => {
    await marcarCerradoLocal('b-1');
    const sql = String(mockRunAsync.mock.calls[0][0]);
    expect(sql).toContain("estado = 'CERRADO_LOCAL'");
    expect(sql).not.toContain("estado = 'COMPLETADO'");
  });

  it('marcarCompletado sigue siendo el cierre confirmado por el servidor', async () => {
    await marcarCompletado('b-1');
    expect(String(mockRunAsync.mock.calls[0][0])).toContain("estado = 'COMPLETADO'");
  });
});
