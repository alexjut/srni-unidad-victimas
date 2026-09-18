/**
 * Tests de cargarMiembrosHogar — resolución tolerante a red (fix #4/#38).
 * DAOs/API mockeados; sin red ni BD real.
 */

// ── Mocks ────────────────────────────────────────────────────────────────────
jest.mock('../../api/hogares', () => ({
  hogaresApi: { detalle: jest.fn() },
}));
jest.mock('../../db/miembrosOfflineDao', () => ({
  construirMiembrosOffline: jest.fn(),
}));
jest.mock('../../db/hogaresCacheDao', () => ({
  guardarMiembros: jest.fn(),
  obtenerMiembros: jest.fn(),
}));

import { hogaresApi } from '../../api/hogares';
import * as miembrosOfflineDao from '../../db/miembrosOfflineDao';
import * as hogaresCacheDao from '../../db/hogaresCacheDao';
import { cargarMiembrosHogar } from '../miembrosHogar';

const mockApi = hogaresApi as jest.Mocked<typeof hogaresApi>;
const mockOffline = miembrosOfflineDao as jest.Mocked<typeof miembrosOfflineDao>;
const mockCache = hogaresCacheDao as jest.Mocked<typeof hogaresCacheDao>;

function miembro(id: string, es_autorizado = false): any {
  return { id, es_autorizado, nombre_completo: id };
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('cargarMiembrosHogar — ONLINE', () => {
  it('devuelve los miembros del servidor (autorizado primero) y los cachea', async () => {
    mockApi.detalle.mockResolvedValue({
      data: { miembros: [miembro('m2'), miembro('m1', true)] },
    } as any);

    const r = await cargarMiembrosHogar('H1');

    expect(r.map((m) => m.id)).toEqual(['m1', 'm2']); // autorizado primero
    expect(mockCache.guardarMiembros).toHaveBeenCalledWith('H1', expect.any(Array));
    expect(mockOffline.construirMiembrosOffline).not.toHaveBeenCalled();
  });

  it('no cachea si el servidor devuelve lista vacía', async () => {
    mockApi.detalle.mockResolvedValue({ data: { miembros: [] } } as any);
    const r = await cargarMiembrosHogar('H1');
    expect(r).toEqual([]);
    expect(mockCache.guardarMiembros).not.toHaveBeenCalled();
  });
});

describe('cargarMiembrosHogar — OFFLINE', () => {
  it('hogar creado offline: usa construirMiembrosOffline', async () => {
    mockApi.detalle.mockRejectedValue(new Error('network'));
    mockOffline.construirMiembrosOffline.mockResolvedValue([miembro('loc1', true)] as any);

    mockCache.obtenerMiembros.mockResolvedValue(null);

    const r = await cargarMiembrosHogar('Hlocal');

    expect(r.map((m) => m.id)).toEqual(['loc1']);
    // Sin caché, lo local es todo lo que hay: no se excluye nada.
    expect(mockOffline.construirMiembrosOffline).toHaveBeenCalledWith('Hlocal', { excluirEnviados: false });
  });

  // QA 16-sep-2026: integrante agregado sin señal a un hogar que ya estaba en el
  // servidor. La lista offline traía solo a ese integrante y ganaba sobre la caché:
  // el autorizado y el resto desaparecían de las preguntas por persona.
  it('hogar del servidor + integrante agregado sin señal: caché y nuevo juntos', async () => {
    mockApi.detalle.mockRejectedValue(new Error('network'));
    mockCache.obtenerMiembros.mockResolvedValue([miembro('srv1', true), miembro('srv2')] as any);
    mockOffline.construirMiembrosOffline.mockResolvedValue([miembro('loc-nuevo')] as any);

    const r = await cargarMiembrosHogar('H1');

    expect(r.map((m) => m.id)).toEqual(['srv1', 'srv2', 'loc-nuevo']);
    // Con caché, los ya subidos vienen en ella: se excluyen de lo local.
    expect(mockOffline.construirMiembrosOffline).toHaveBeenCalledWith('H1', { excluirEnviados: true });
  });

  it('no repite al autorizado reconstruido offline si la caché ya lo trae', async () => {
    mockApi.detalle.mockRejectedValue(new Error('network'));
    mockCache.obtenerMiembros.mockResolvedValue([miembro('srv1', true)] as any);
    mockOffline.construirMiembrosOffline.mockResolvedValue(
      [miembro('vic-local', true), miembro('loc-nuevo')] as any);

    const r = await cargarMiembrosHogar('H1');

    expect(r.map((m) => m.id)).toEqual(['srv1', 'loc-nuevo']);
  });

  it('no repite un integrante que está en la caché y en lo local con el mismo id', async () => {
    mockApi.detalle.mockRejectedValue(new Error('network'));
    mockCache.obtenerMiembros.mockResolvedValue([miembro('srv1', true), miembro('m2')] as any);
    mockOffline.construirMiembrosOffline.mockResolvedValue([miembro('m2')] as any);

    const r = await cargarMiembrosHogar('H1');

    expect(r.map((m) => m.id)).toEqual(['srv1', 'm2']);
  });

  it('hogar creado ONLINE y red caída: cae a la caché del servidor (el bug #4/#38)', async () => {
    mockApi.detalle.mockRejectedValue(new Error('network'));
    mockOffline.construirMiembrosOffline.mockResolvedValue([]); // no hay filas offline
    mockCache.obtenerMiembros.mockResolvedValue([miembro('srv2'), miembro('srv1', true)] as any);

    const r = await cargarMiembrosHogar('H1');

    expect(r.map((m) => m.id)).toEqual(['srv1', 'srv2']); // autorizado primero
  });

  it('sin red, sin offline y sin caché: lista vacía (degrada a solo HOGAR)', async () => {
    mockApi.detalle.mockRejectedValue(new Error('network'));
    mockOffline.construirMiembrosOffline.mockResolvedValue([]);
    mockCache.obtenerMiembros.mockResolvedValue(null);

    const r = await cargarMiembrosHogar('H1');
    expect(r).toEqual([]);
  });

  // Regresión del fix "carga infinita": con el timeout del refresh (client.ts),
  // una petición colgada por 401→refresh ahora RECHAZA (ECONNABORTED) en vez de
  // quedar pendiente. Esto garantiza que cargarMiembrosHogar entre a su catch y
  // caiga al fallback de caché, en lugar de dejar la lista de integrantes vacía
  // para siempre. hogaresApi.detalle va por apiClient (timeout 15 s heredado).
  it('detalle rechaza por timeout (ECONNABORTED): cae al fallback de caché, no queda colgado', async () => {
    const timeoutErr = Object.assign(new Error('timeout of 15000ms exceeded'), {
      code: 'ECONNABORTED',
      isAxiosError: true,
    });
    mockApi.detalle.mockRejectedValue(timeoutErr);
    mockOffline.construirMiembrosOffline.mockResolvedValue([]);
    mockCache.obtenerMiembros.mockResolvedValue([miembro('srv1', true)] as any);

    const r = await cargarMiembrosHogar('H1');

    expect(r.map((m) => m.id)).toEqual(['srv1']);
  });
});
