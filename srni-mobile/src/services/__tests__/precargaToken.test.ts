/**
 * Regresión de APK-003: el filtro del universo NUNCA se descargó en ningún
 * teléfono porque obtenerToken() leía el Bearer de
 * `apiClient.defaults.headers.common.Authorization`, que el cliente nunca
 * setea —inyecta el token por request desde SecureStore—. Siempre devolvía ''
 * y la descarga cortaba en `if (!token) return`.
 *
 * Ahora obtenerToken() lee de SecureStore, la misma fuente que el interceptor.
 * Este test corre ejecutarPrecarga con un token guardado y verifica que la
 * descarga del filtro SÍ se dispara con ese token.
 *
 * Verificado por mutación: volver a leer de headers.common hace fallar el
 * primer test (descargarFiltro no se llama).
 */

// ── Mocks ────────────────────────────────────────────────────────────────────
jest.mock('../../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn(), defaults: { headers: { common: {} } } },
}));
jest.mock('../../db/precargaDao', () => ({
  guardarPrecarga: jest.fn().mockResolvedValue(undefined),
  getParametrosBloom: jest.fn().mockResolvedValue(null),
  guardarParametrosBloom: jest.fn().mockResolvedValue(undefined),
}));
jest.mock('../filtroUniverso', () => ({
  parsearParametros: jest.fn().mockReturnValue(null),
  hayFiltro: jest.fn().mockReturnValue(false),
  descargarFiltro: jest.fn().mockResolvedValue(true),
}));

import * as SecureStore from 'expo-secure-store';
import apiClient from '../../api/client';
import * as filtroUniverso from '../filtroUniverso';
import { ejecutarPrecarga } from '../precarga';

const get = (apiClient as unknown as { get: jest.Mock }).get;
const descargar = filtroUniverso.descargarFiltro as jest.Mock;

const BLOOM = { url: 'https://srni/universo.bloom', m: 1000, k: 7 };
const PAYLOAD = { padron_archivo: { version: 'v7', bloom: BLOOM } };

beforeEach(async () => {
  jest.clearAllMocks();
  await SecureStore.deleteItemAsync('access_token');
  get.mockResolvedValue({ data: PAYLOAD });
  descargar.mockResolvedValue(true);
});

test('con token en SecureStore, la descarga del filtro se dispara con ESE token', async () => {
  await SecureStore.setItemAsync('access_token', 'TOKEN-REAL-123');

  await ejecutarPrecarga();

  expect(descargar).toHaveBeenCalledTimes(1);
  // Segundo argumento = token; debe ser el de SecureStore, no ''.
  expect(descargar.mock.calls[0][1]).toBe('TOKEN-REAL-123');
});

test('sin token, la descarga no se intenta (no revienta el login)', async () => {
  await ejecutarPrecarga();
  expect(descargar).not.toHaveBeenCalled();
});
