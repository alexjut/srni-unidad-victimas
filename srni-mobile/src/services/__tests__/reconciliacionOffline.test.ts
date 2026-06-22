/**
 * Tests de reconciliarColaOffline — fix #14.
 * BD mockeada con un mockGetAllAsync por tabla y un mockGetFirstAsync para el guard.
 */
jest.mock('../../db/colaDao', () => ({
  encolar: jest.fn().mockResolvedValue(1),
}));

const mockGetAllAsync = jest.fn();
const mockGetFirstAsync = jest.fn();
jest.mock('../../db/schema', () => ({
  openDb: jest.fn().mockResolvedValue({
    getAllAsync: (...a: unknown[]) => mockGetAllAsync(...a),
    getFirstAsync: (...a: unknown[]) => mockGetFirstAsync(...a),
  }),
}));

import * as colaDao from '../../db/colaDao';
import { reconciliarColaOffline } from '../reconciliacionOffline';

const mockEncolar = colaDao.encolar as jest.Mock;

// El guard tieneEnCola() consulta COUNT(*); por defecto devolvemos 0 (sin item).
function sinItemsEnCola() {
  mockGetFirstAsync.mockResolvedValue({ n: 0 });
}

// mockGetAllAsync se llama 3 veces en orden: victimas, hogares, miembros.
function tablas(victimas: unknown[], hogares: unknown[], miembros: unknown[]) {
  mockGetAllAsync
    .mockResolvedValueOnce(victimas)
    .mockResolvedValueOnce(hogares)
    .mockResolvedValueOnce(miembros);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetAllAsync.mockReset();
  mockGetFirstAsync.mockReset();
});

describe('reconciliarColaOffline', () => {
  it('re-encola un hogar huérfano (sin item en cola)', async () => {
    sinItemsEnCola();
    tablas(
      [],
      [{
        id_local: 'H1', jefe_hogar_uuid: 'V1', municipio_id: 5,
        tipo_vivienda: 'CASA', condicion_ocupacion: 'PROPIA', estrato: 2,
        numero_cuartos: 3, numero_personas: 4, observaciones: '',
      }],
      [],
    );

    const n = await reconciliarColaOffline();

    expect(n).toBe(1);
    expect(mockEncolar).toHaveBeenCalledWith('CREAR_HOGAR', 'H1', expect.objectContaining({
      id_local: 'H1', autorizado: 'V1', numero_personas: 4,
    }));
  });

  it('NO re-encola si ya existe un item de cola para el recurso', async () => {
    mockGetFirstAsync.mockResolvedValue({ n: 1 }); // ya hay item
    tablas([], [{ id_local: 'H1', jefe_hogar_uuid: 'V1', municipio_id: null,
      tipo_vivienda: '', condicion_ocupacion: '', estrato: 0,
      numero_cuartos: 0, numero_personas: 1, observaciones: '' }], []);

    const n = await reconciliarColaOffline();

    expect(n).toBe(0);
    expect(mockEncolar).not.toHaveBeenCalled();
  });

  it('reconcilia los tres tipos (víctima, hogar, miembro)', async () => {
    sinItemsEnCola();
    tablas(
      [{ id_local: 'V1', payload_json: '{"primer_nombre":"Ana"}' }],
      [{ id_local: 'H1', jefe_hogar_uuid: 'V1', municipio_id: null,
        tipo_vivienda: '', condicion_ocupacion: '', estrato: 0,
        numero_cuartos: 0, numero_personas: 1, observaciones: '' }],
      [{ id_local: 'M1', hogar_id_local: 'H1', payload_json: '{"nombre_completo":"Beto"}' }],
    );

    const n = await reconciliarColaOffline();

    expect(n).toBe(3);
    expect(mockEncolar).toHaveBeenCalledWith('REGISTRAR_VICTIMA', 'V1', expect.any(Object));
    expect(mockEncolar).toHaveBeenCalledWith('CREAR_HOGAR', 'H1', expect.any(Object));
    expect(mockEncolar).toHaveBeenCalledWith('AGREGAR_MIEMBRO', 'M1', expect.objectContaining({
      hogar: 'H1',
    }));
  });

  it('salta payloads corruptos sin romper', async () => {
    sinItemsEnCola();
    tablas(
      [{ id_local: 'V1', payload_json: '{corrupto' }],
      [],
      [],
    );

    const n = await reconciliarColaOffline();

    expect(n).toBe(0);
    expect(mockEncolar).not.toHaveBeenCalled();
  });
});
