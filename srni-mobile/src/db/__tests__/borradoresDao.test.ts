/**
 * Regresiones de borradoresDao — los dos filtros que hacían desaparecer trabajo.
 *
 * Acá se prueba la consulta que sale hacia SQLite, no el resultado: el mock de
 * expo-sqlite no ejecuta SQL. Y está bien que sea así, porque el defecto vivía
 * exactamente en el WHERE — las dos veces se perdió trabajo capturado por una
 * condición de más.
 */
const mockGetAllAsync = jest.fn();
const mockGetFirstAsync = jest.fn();
jest.mock('../schema', () => ({
  openDb: jest.fn().mockResolvedValue({
    getAllAsync: (...a: unknown[]) => mockGetAllAsync(...a),
    getFirstAsync: (...a: unknown[]) => mockGetFirstAsync(...a),
  }),
}));

import {
  listarBorradores,
  findBorradorOfflinePorHogarInstrumento,
} from '../borradoresDao';

/** Normaliza saltos de línea e indentación para poder buscar frases sueltas. */
function sqlDe(mock: jest.Mock): string {
  return String(mock.mock.calls[0][0]).replace(/\s+/g, ' ').trim();
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetAllAsync.mockReset().mockResolvedValue([]);
  mockGetFirstAsync.mockReset().mockResolvedValue(null);
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

  it('excluye solo el borrador ya cerrado contra el servidor', async () => {
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

  it('busca por hogar + instrumento y descarta el ya cerrado', async () => {
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
