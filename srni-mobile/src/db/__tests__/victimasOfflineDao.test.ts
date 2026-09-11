/**
 * El alta manual sin señal tiene que ser encontrable otra vez.
 *
 * ─── El defecto que esto cierra ────────────────────────────────────────────
 * Reportado el 11-sep-2026 por el equipo de caracterización: en personas no
 * incluidas en el RUV «los datos previamente diligenciados no permanecen
 * almacenados, lo que obliga al usuario a ingresarlos nuevamente».
 *
 * La causa, sin señal: `buscarOffline` consultaba el padrón precargado y el filtro
 * del universo, y `victimas_offline` solo se escribía, nunca se leía. Buscar otra
 * vez el mismo documento respondía «no está en el padrón» y ofrecía darla de alta
 * de nuevo. Se reescribía todo y quedaba un SEGUNDO registro encolado para
 * sincronizar — no solo reproceso: un duplicado en el padrón.
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

import { buscarPorDocumento } from '../victimasOfflineDao';

/** Fila como la guarda `crearVictimaOffline`: la ficha completa en el payload. */
function fila(idLocal: string, tipo: string, numero: string, nombre = 'ANA',
              createdAt = '2026-09-11T10:00:00.000Z') {
  return {
    id_local: idLocal,
    id_servidor: null,
    payload_json: JSON.stringify({
      tipo_documento: tipo,
      numero_documento: numero,
      primer_nombre: nombre,
      primer_apellido: 'PEREZ',
      estado_ruv: 'NO_VERIFICADO',
      fuente_origen: 'MANUAL',
    }),
    estado_sync: 'pendiente',
    created_at: createdAt,
    updated_at: createdAt,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetAllAsync.mockReset().mockResolvedValue([]);
  mockGetFirstAsync.mockReset().mockResolvedValue(null);
  mockRunAsync.mockReset().mockResolvedValue({ changes: 1 });
});

it('encuentra a la persona que se dio de alta en este teléfono', async () => {
  mockGetAllAsync.mockResolvedValue([fila('local-1', 'CC', '28548486')]);

  const hallada = await buscarPorDocumento('CC', '28548486');

  expect(hallada).not.toBeNull();
  expect(hallada!.row.id_local).toBe('local-1');
  expect(hallada!.victima.primer_nombre).toBe('ANA');
});

it('devuelve null cuando no hay ninguna con ese documento', async () => {
  mockGetAllAsync.mockResolvedValue([fila('local-1', 'CC', '28548486')]);

  expect(await buscarPorDocumento('CC', '1115724047')).toBeNull();
});

it('no confunde el mismo número con otro tipo de documento', async () => {
  // El mismo número puede ser la cédula de una persona y la tarjeta de identidad
  // de otra. Devolver la equivocada le entregaría al encuestador los datos de
  // alguien más sin que se entere, que es peor que no encontrar nada.
  mockGetAllAsync.mockResolvedValue([fila('local-1', 'TI', '28548486')]);

  expect(await buscarPorDocumento('CC', '28548486')).toBeNull();
});

it('ignora espacios y mayúsculas al comparar', async () => {
  mockGetAllAsync.mockResolvedValue([fila('local-1', 'CC', '28548486')]);

  const hallada = await buscarPorDocumento('cc', '  28548486  ');

  expect(hallada!.row.id_local).toBe('local-1');
});

it('con dos altas del mismo documento devuelve la más reciente', async () => {
  // La consulta pide `ORDER BY created_at DESC`, así que la primera fila es la
  // última capturada: es la que el encuestador acabó de confirmar con la persona.
  mockGetAllAsync.mockResolvedValue([
    fila('local-nueva', 'CC', '28548486', 'ANA MARIA', '2026-09-11T15:00:00.000Z'),
    fila('local-vieja', 'CC', '28548486', 'ANA', '2026-09-10T08:00:00.000Z'),
  ]);

  const hallada = await buscarPorDocumento('CC', '28548486');

  expect(hallada!.row.id_local).toBe('local-nueva');
});

it('una fila con payload corrupto no impide encontrar las demás', async () => {
  const corrupta = { ...fila('local-mala', 'CC', '999'), payload_json: '{no es json' };
  mockGetAllAsync.mockResolvedValue([corrupta, fila('local-1', 'CC', '28548486')]);

  const hallada = await buscarPorDocumento('CC', '28548486');

  expect(hallada!.row.id_local).toBe('local-1');
});

it('un documento vacío no dispara la consulta', async () => {
  // Sin esto, entrar a la pantalla y buscar en blanco devolvería la primera alta
  // manual del teléfono como si fuera la persona atendida.
  expect(await buscarPorDocumento('CC', '   ')).toBeNull();
  expect(mockGetAllAsync).not.toHaveBeenCalled();
});

it('pide las filas de la más reciente a la más antigua', async () => {
  await buscarPorDocumento('CC', '28548486');

  const sql = String(mockGetAllAsync.mock.calls[0][0]).replace(/\s+/g, ' ');
  expect(sql).toContain('ORDER BY created_at DESC');
});
