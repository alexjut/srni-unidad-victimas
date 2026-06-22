/**
 * Tests del ciclo de sincronización con DAOs mockeados.
 * Verifica el comportamiento del orquestador sin necesidad de red ni BD real.
 */

// ── Mocks ────────────────────────────────────────────────────────────────────

jest.mock('../../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}));

jest.mock('../../api/hogares', () => ({
  hogaresApi: { crear: jest.fn() },
}));

jest.mock('../../api/encuestas', () => ({
  encuestasApi: {
    crear: jest.fn(),
    responder: jest.fn(),
    finalizar: jest.fn(),
  },
}));

jest.mock('../../db/colaDao');
jest.mock('../../db/borradoresDao');
jest.mock('../../db/hogaresOfflineDao');
jest.mock('../../db/schema', () => ({
  openDb: jest.fn().mockResolvedValue({
    runAsync: jest.fn().mockResolvedValue(undefined),
    getAllAsync: jest.fn().mockResolvedValue([]),
    getFirstAsync: jest.fn().mockResolvedValue(null),
  }),
}));

import * as colaDao from '../../db/colaDao';
import * as borradoresDao from '../../db/borradoresDao';
import * as hogaresOfflineDao from '../../db/hogaresOfflineDao';
import { hogaresApi } from '../../api/hogares';
import { encuestasApi } from '../../api/encuestas';
import { intentarSincronizar, estaOnline } from '../sincronizacion';
import apiClient from '../../api/client';

const mockCola = colaDao as jest.Mocked<typeof colaDao>;
const mockBorradores = borradoresDao as jest.Mocked<typeof borradoresDao>;
const mockHogaresOffline = hogaresOfflineDao as jest.Mocked<typeof hogaresOfflineDao>;
const mockHogaresApi = hogaresApi as jest.Mocked<typeof hogaresApi>;
const mockEncuestasApi = encuestasApi as jest.Mocked<typeof encuestasApi>;
const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

// ─────────────────────────────────────────────────────────────────────────────

function crearItem(overrides: Partial<colaDao.ColaItem> = {}): colaDao.ColaItem {
  return {
    id: 1,
    tipo: 'CREAR_HOGAR',
    recurso_local_id: 'local-uuid-001',
    payload: JSON.stringify({
      id_local: 'local-uuid-001',
      jefe_hogar: 'victima-uuid-001',
      numero_personas: 3,
    }),
    estado: 'pendiente',
    intentos: 0,
    ultimo_error: '',
    retry_after: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  mockCola.resetearBloqueados.mockResolvedValue(undefined);
  mockCola.marcarEnviando.mockResolvedValue(undefined);
  mockCola.marcarEnviado.mockResolvedValue(undefined);
  mockCola.marcarError.mockResolvedValue(undefined);
  mockCola.contarPendientes.mockResolvedValue(0);
  mockBorradores.marcarSincronizado.mockResolvedValue(undefined);
  mockBorradores.marcarCompletado.mockResolvedValue(undefined);
  mockHogaresOffline.marcarSincronizado.mockResolvedValue(undefined);
});

// ─────────────────────────────────────────────────────────────────────────────
// estaOnline
// ─────────────────────────────────────────────────────────────────────────────

describe('estaOnline', () => {
  it('devuelve true cuando /health/ responde', async () => {
    (mockApiClient.get as jest.Mock).mockResolvedValueOnce({ status: 200 });
    expect(await estaOnline()).toBe(true);
  });

  it('devuelve false cuando /health/ falla', async () => {
    (mockApiClient.get as jest.Mock).mockRejectedValueOnce(new Error('timeout'));
    expect(await estaOnline()).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// intentarSincronizar — cola vacía
// ─────────────────────────────────────────────────────────────────────────────

describe('intentarSincronizar — cola vacía', () => {
  it('no llama a ninguna API cuando no hay pendientes', async () => {
    mockCola.obtenerPendientes.mockResolvedValue([]);

    const resultado = await intentarSincronizar();

    expect(resultado.procesados).toBe(0);
    expect(resultado.errores).toBe(0);
    expect(mockHogaresApi.crear).not.toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// CREAR_HOGAR
// ─────────────────────────────────────────────────────────────────────────────

describe('intentarSincronizar — CREAR_HOGAR', () => {
  it('llama a hogaresApi.crear y marca como enviado', async () => {
    const item = crearItem({ tipo: 'CREAR_HOGAR' });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(0);
    mockHogaresApi.crear.mockResolvedValue({ data: { id: 'servidor-uuid-001' } } as any);

    const resultado = await intentarSincronizar();

    expect(mockCola.marcarEnviando).toHaveBeenCalledWith(item.id);
    expect(mockHogaresApi.crear).toHaveBeenCalled();
    expect(mockHogaresOffline.marcarSincronizado).toHaveBeenCalledWith('local-uuid-001', 'servidor-uuid-001');
    expect(mockCola.marcarEnviado).toHaveBeenCalledWith(item.id);
    expect(resultado.procesados).toBe(1);
    expect(resultado.errores).toBe(0);
  });

  it('marca error en un fallo de red y no procesa más items', async () => {
    const item = crearItem({ tipo: 'CREAR_HOGAR' });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(1);
    mockHogaresApi.crear.mockRejectedValue(new Error('Network Error'));

    const resultado = await intentarSincronizar();

    expect(mockCola.marcarError).toHaveBeenCalledWith(item.id, expect.any(String));
    expect(mockCola.marcarEnviado).not.toHaveBeenCalled();
    expect(resultado.procesados).toBe(0);
    expect(resultado.errores).toBe(1);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// CREAR_SESION
// ─────────────────────────────────────────────────────────────────────────────

describe('intentarSincronizar — CREAR_SESION', () => {
  it('llama a encuestasApi.crear y actualiza borrador_id', async () => {
    const item = crearItem({
      id: 2,
      tipo: 'CREAR_SESION',
      recurso_local_id: 'borrador-001',
      payload: JSON.stringify({
        borrador_id: 'borrador-001',
        hogar: 'hogar-servidor-001',
        instrumento: 1,
      }),
    });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(0);
    mockEncuestasApi.crear.mockResolvedValue({ data: { id: 'sesion-servidor-001' } } as any);

    await intentarSincronizar();

    expect(mockEncuestasApi.crear).toHaveBeenCalledWith({
      hogar: 'hogar-servidor-001',
      instrumento: 1,
      ruta_entrevista: 'GENERAL',
    });
    expect(mockBorradores.marcarSincronizado).toHaveBeenCalledWith('borrador-001', 'sesion-servidor-001');
    expect(mockCola.marcarEnviado).toHaveBeenCalledWith(2);
  });

  it('marca error permanente en 4xx (datos inválidos)', async () => {
    const item = crearItem({
      tipo: 'CREAR_SESION',
      payload: JSON.stringify({ borrador_id: 'b-001', hogar: 'h-001', instrumento: 1 }),
    });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(1);
    const err = Object.assign(new Error('Bad Request'), { response: { status: 400, data: { detail: 'hogar no existe' } } });
    mockEncuestasApi.crear.mockRejectedValue(err);

    await intentarSincronizar();

    expect(mockCola.marcarError).toHaveBeenCalledWith(item.id, expect.stringContaining('400'));
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// RESPONDER_PREGUNTA
// ─────────────────────────────────────────────────────────────────────────────

describe('intentarSincronizar — RESPONDER_PREGUNTA', () => {
  it('llama a encuestasApi.responder con sesion_id y pregunta_id', async () => {
    const item = crearItem({
      tipo: 'RESPONDER_PREGUNTA',
      payload: JSON.stringify({
        borrador_id: 'b-001',
        sesion_id: 'sesion-servidor-001',
        pregunta_id: 42,
        valor: 'SI',
      }),
    });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(0);
    mockEncuestasApi.responder.mockResolvedValue({ data: {} } as any);

    await intentarSincronizar();

    expect(mockEncuestasApi.responder).toHaveBeenCalledWith('sesion-servidor-001', {
      pregunta_id: 42,
      miembro_id: null,
      valor: 'SI',
    });
    expect(mockCola.marcarEnviado).toHaveBeenCalledWith(item.id);
  });

  it('difiere (reencolar) sin error si sesion_id es null (CREAR_SESION aún no procesado)', async () => {
    // C4 — esperar una dependencia NO es un fallo: el item se devuelve a
    // 'pendiente' sin gastar intentos ni marcarse como error, para no trabar la
    // cadena. Antes esto consumía los 3 intentos y mataba la respuesta.
    const item = crearItem({
      tipo: 'RESPONDER_PREGUNTA',
      payload: JSON.stringify({
        borrador_id: 'b-001',
        sesion_id: null,
        pregunta_id: 42,
        valor: 'SI',
      }),
    });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(1);

    const resultado = await intentarSincronizar();

    expect(mockCola.reencolar).toHaveBeenCalledWith(item.id);
    expect(mockCola.marcarError).not.toHaveBeenCalled();
    expect(resultado.errores).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Reintento y errores permanentes
// ─────────────────────────────────────────────────────────────────────────────

describe('manejo de reintentos', () => {
  it('items de tipo desconocido se marcan como error sin reintentar', async () => {
    const item = crearItem({ tipo: 'TIPO_INEXISTENTE' as any });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(1);

    const resultado = await intentarSincronizar();

    expect(mockCola.marcarError).toHaveBeenCalledWith(item.id, expect.stringContaining('desconocido'));
    expect(resultado.errores).toBe(1);
  });

  it('resetearBloqueados se llama siempre al inicio', async () => {
    mockCola.obtenerPendientes.mockResolvedValue([]);

    await intentarSincronizar();

    expect(mockCola.resetearBloqueados).toHaveBeenCalledTimes(1);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// FINALIZAR_SESION
// ─────────────────────────────────────────────────────────────────────────────

describe('intentarSincronizar — FINALIZAR_SESION', () => {
  it('llama a encuestasApi.finalizar y marca el borrador como completado', async () => {
    const item = crearItem({
      tipo: 'FINALIZAR_SESION',
      payload: JSON.stringify({
        borrador_id: 'b-001',
        sesion_id: 'sesion-001',
        observaciones: 'Encuesta completa',
      }),
    });
    mockCola.obtenerPendientes.mockResolvedValue([item]);
    mockCola.contarPendientes.mockResolvedValue(0);
    mockEncuestasApi.finalizar.mockResolvedValue({ data: { estado: 'COMPLETADA' } } as any);

    await intentarSincronizar();

    expect(mockEncuestasApi.finalizar).toHaveBeenCalledWith('sesion-001', {
      observaciones: 'Encuesta completa',
    });
    expect(mockBorradores.marcarCompletado).toHaveBeenCalledWith('b-001');
    expect(mockCola.marcarEnviado).toHaveBeenCalledWith(item.id);
  });
});
