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

    const r = await cargarMiembrosHogar('Hlocal');

    expect(r.map((m) => m.id)).toEqual(['loc1']);
    expect(mockCache.obtenerMiembros).not.toHaveBeenCalled();
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
});
