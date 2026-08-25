/**
 * Tests de authStore.cargarPerfil — el arranque de la app.
 *
 * Regresión de APK-003: al abrir la app SIN red, cargarPerfil() llamaba a
 * `me()`, fallaba, y en el `catch` borraba los tokens y dejaba usuario=null.
 * Resultado: la encuestadora quedaba fuera del sistema en pleno campo y encima
 * perdía el token. Ahora:
 *   - 401/403  -> credenciales de verdad inválidas: se limpia todo.
 *   - sin red / 5xx -> se CONSERVA la sesión y se rehidrata el perfil del caché.
 *
 * Verificado por mutación: revertir cargarPerfil al `catch` que borra siempre
 * hace fallar los dos primeros tests.
 */

// ── Mocks ────────────────────────────────────────────────────────────────────
jest.mock('../../api/auth', () => ({
  authApi: { me: jest.fn(), login: jest.fn(), refresh: jest.fn(), logout: jest.fn() },
}));
jest.mock('../../services/precarga', () => ({ precargarEnSegundoPlano: jest.fn() }));
jest.mock('../../db/precargaDao', () => ({
  limpiarTodoOffline: jest.fn().mockResolvedValue(undefined),
  limpiarPrecarga: jest.fn().mockResolvedValue(undefined),
}));
jest.mock('../../db/colaDao', () => ({ contarPendientes: jest.fn().mockResolvedValue(0) }));
jest.mock('../../services/filtroUniverso', () => ({ borrarFiltro: jest.fn() }));
jest.mock('expo-local-authentication', () => ({
  hasHardwareAsync: jest.fn().mockResolvedValue(false),
  isEnrolledAsync: jest.fn().mockResolvedValue(false),
  authenticateAsync: jest.fn(),
}));

import * as SecureStore from 'expo-secure-store';
import { authApi } from '../../api/auth';
import { useAuthStore } from '../authStore';

const me = authApi.me as jest.Mock;

const PERFIL = { id: 7, codigo_usuario: 'ENC_UNO', nombre_completo: 'Encuestadora Uno' };

beforeEach(async () => {
  jest.clearAllMocks();
  // El mock de SecureStore guarda estado a nivel de módulo: limpiar a mano.
  await SecureStore.deleteItemAsync('access_token');
  await SecureStore.deleteItemAsync('refresh_token');
  await SecureStore.deleteItemAsync('perfil_cache');
  useAuthStore.setState({ usuario: null, perfilCargado: false, error: null });
});

test('sin token guardado, cargarPerfil termina sin sesión y sin llamar a la red', async () => {
  await useAuthStore.getState().cargarPerfil();
  expect(me).not.toHaveBeenCalled();
  expect(useAuthStore.getState().usuario).toBeNull();
  expect(useAuthStore.getState().perfilCargado).toBe(true);
});

test('con red, cargarPerfil trae el perfil y lo cachea', async () => {
  await SecureStore.setItemAsync('access_token', 'tok');
  me.mockResolvedValueOnce({ data: PERFIL });

  await useAuthStore.getState().cargarPerfil();

  expect(useAuthStore.getState().usuario).toEqual(PERFIL);
  const cache = await SecureStore.getItemAsync('perfil_cache');
  expect(JSON.parse(cache as string)).toEqual(PERFIL);
});

test('SIN red (error sin response): conserva el token y rehidrata del caché', async () => {
  await SecureStore.setItemAsync('access_token', 'tok');
  await SecureStore.setItemAsync('refresh_token', 'ref');
  await SecureStore.setItemAsync('perfil_cache', JSON.stringify(PERFIL));
  me.mockRejectedValueOnce(new Error('Network Error')); // axios sin .response

  await useAuthStore.getState().cargarPerfil();

  // La sesión NO se cierra:
  expect(useAuthStore.getState().usuario).toEqual(PERFIL);
  expect(await SecureStore.getItemAsync('access_token')).toBe('tok');
  expect(await SecureStore.getItemAsync('refresh_token')).toBe('ref');
});

test('error 5xx del servidor: tampoco cierra la sesión', async () => {
  await SecureStore.setItemAsync('access_token', 'tok');
  await SecureStore.setItemAsync('perfil_cache', JSON.stringify(PERFIL));
  me.mockRejectedValueOnce({ response: { status: 503 } });

  await useAuthStore.getState().cargarPerfil();

  expect(useAuthStore.getState().usuario).toEqual(PERFIL);
  expect(await SecureStore.getItemAsync('access_token')).toBe('tok');
});

test('401 (refresh también falló): limpia tokens y caché', async () => {
  await SecureStore.setItemAsync('access_token', 'tok');
  await SecureStore.setItemAsync('refresh_token', 'ref');
  await SecureStore.setItemAsync('perfil_cache', JSON.stringify(PERFIL));
  me.mockRejectedValueOnce({ response: { status: 401 } });

  await useAuthStore.getState().cargarPerfil();

  expect(useAuthStore.getState().usuario).toBeNull();
  expect(await SecureStore.getItemAsync('access_token')).toBeNull();
  expect(await SecureStore.getItemAsync('refresh_token')).toBeNull();
  expect(await SecureStore.getItemAsync('perfil_cache')).toBeNull();
});

test('sin red y sin caché (primer arranque tras instalar): conserva token, sin perfil', async () => {
  await SecureStore.setItemAsync('access_token', 'tok');
  me.mockRejectedValueOnce(new Error('Network Error'));

  await useAuthStore.getState().cargarPerfil();

  expect(useAuthStore.getState().usuario).toBeNull();
  expect(useAuthStore.getState().perfilCargado).toBe(true);
  // El token se conserva para el próximo arranque con señal.
  expect(await SecureStore.getItemAsync('access_token')).toBe('tok');
});
