/**
 * APK-003 — sin señal no se puede crear dos veces el hogar de la misma persona.
 *
 * ─── El defecto que esto cierra ────────────────────────────────────────────
 * Conformar el hogar sin señal creaba un hogar NUEVO en cada visita a la
 * pantalla. Basta salir y volver a buscar la misma cédula —corriente en campo, y
 * seguro si la app se cierra— para terminar con dos hogares del mismo autorizado
 * y dos `CREAR_HOGAR` en la cola.
 *
 * Al sincronizar, el servidor crea el primero y para el segundo devuelve ese
 * mismo hogar: la caracterización capturada contra el hogar duplicado queda
 * apuntando a un id que allá no existe. Con señal nunca pasó, porque el backend
 * devuelve el hogar existente; offline no había quien lo hiciera.
 */
const mockGetFirstAsync = jest.fn();
const mockRunAsync = jest.fn();
jest.mock('../schema', () => ({
  openDb: jest.fn().mockResolvedValue({
    getFirstAsync: (...a: unknown[]) => mockGetFirstAsync(...a),
    runAsync: (...a: unknown[]) => mockRunAsync(...a),
  }),
}));

import { buscarPorAutorizado, crearHogarOffline } from '../hogaresOfflineDao';

function fila(over: Record<string, unknown> = {}) {
  return {
    id_local: 'hogar-local-1',
    id_servidor: null,
    jefe_hogar_uuid: 'victima-1',
    estado_sync: 'pendiente',
    created_at: '2026-09-18T10:00:00.000Z',
    ...over,
  };
}

beforeEach(() => jest.clearAllMocks());

describe('buscarPorAutorizado', () => {
  it('encuentra el hogar que esa persona ya tiene en el teléfono', async () => {
    mockGetFirstAsync.mockResolvedValue(fila());

    const r = await buscarPorAutorizado('victima-1');

    expect(r?.id_local).toBe('hogar-local-1');
    const [sql, params] = mockGetFirstAsync.mock.calls[0];
    expect(sql).toContain('jefe_hogar_uuid = ?');
    expect(params).toEqual(['victima-1']);
  });

  it('devuelve el más reciente si quedaron varios de antes del arreglo', async () => {
    await buscarPorAutorizado('victima-1');

    const [sql] = mockGetFirstAsync.mock.calls[0];
    expect(sql).toContain('ORDER BY created_at DESC');
    expect(sql).toContain('LIMIT 1');
  });

  it('devuelve null si esa persona todavía no tiene hogar acá', async () => {
    mockGetFirstAsync.mockResolvedValue(null);

    expect(await buscarPorAutorizado('victima-nueva')).toBeNull();
  });

  it('el hogar ya sincronizado también se encuentra: es el mismo hogar', async () => {
    // Con `id_servidor` la pantalla sigue con el id del servidor, y los
    // integrantes van por POST directo en vez de encolarse otra vez.
    mockGetFirstAsync.mockResolvedValue(fila({ id_servidor: 'uuid-servidor', estado_sync: 'enviado' }));

    const r = await buscarPorAutorizado('victima-1');

    expect(r?.id_servidor).toBe('uuid-servidor');
  });
});

describe('crearHogarOffline', () => {
  it('guarda el hogar pendiente de sincronizar, con su autorizado', async () => {
    const r = await crearHogarOffline({ jefe_hogar_uuid: 'victima-9', numero_personas: 1 });

    expect(r.jefe_hogar_uuid).toBe('victima-9');
    expect(r.estado_sync).toBe('pendiente');
    expect(r.id_servidor).toBeNull();
    expect(mockRunAsync).toHaveBeenCalledTimes(1);
  });

  it('cada hogar nuevo lleva su propio id local', async () => {
    const a = await crearHogarOffline({ jefe_hogar_uuid: 'v1' });
    const b = await crearHogarOffline({ jefe_hogar_uuid: 'v2' });

    expect(a.id_local).not.toBe(b.id_local);
  });
});
