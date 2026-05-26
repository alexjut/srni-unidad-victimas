/**
 * Cliente axios para el backend Django SRNI en :8001.
 * - Inyecta Bearer token en cada request
 * - Interceptor de respuesta: refresca token al recibir 401 (una sola vez por request)
 * - Nunca guarda tokens en memoria plana; los lee de SecureStore en cada request
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from 'expo-secure-store';

// En desarrollo apunta al backend local. En producción se sobreescribe con variable de entorno.
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8001';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// ── Request interceptor ──────────────────────────────────────────────────────
apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await SecureStore.getItemAsync('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — manejo de 401 + refresh ──────────────────────────
let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

function processQueue(newToken: string) {
  refreshQueue.forEach((resolve) => resolve(newToken));
  refreshQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Sprint 17: loguear todos los errores HTTP al backend para visibilidad
    // No bloquea — usa dynamic import por si client.ts se carga muy temprano.
    if (error.response?.status !== 401) {
      import('../services/errorReporter').then(({ reportarError }) => {
        reportarError({
          nivel: error.response?.status && error.response.status >= 500 ? 'error' : 'warn',
          mensaje: `HTTP ${error.response?.status ?? 'red'} ${original?.method?.toUpperCase()} ${original?.url}`,
          pantalla: '[axios-interceptor]',
          contexto: {
            status: error.response?.status,
            body: typeof error.response?.data === 'object' ? error.response?.data : String(error.response?.data ?? '').slice(0, 300),
          },
        });
      }).catch(() => {});
    }

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Encolar requests que lleguen mientras se refresca
      return new Promise((resolve) => {
        refreshQueue.push((token: string) => {
          original.headers.Authorization = `Bearer ${token}`;
          resolve(apiClient(original));
        });
      });
    }

    original._retry = true;
    isRefreshing = true;

    try {
      const refresh = await SecureStore.getItemAsync('refresh_token');
      if (!refresh) throw new Error('No refresh token');

      const { data } = await axios.post(`${BASE_URL}/api/auth/refresh/`, { refresh });
      const newAccess: string = data.access;

      await SecureStore.setItemAsync('access_token', newAccess);
      if (data.refresh) {
        await SecureStore.setItemAsync('refresh_token', data.refresh);
      }

      processQueue(newAccess);
      original.headers.Authorization = `Bearer ${newAccess}`;
      return apiClient(original);
    } catch {
      // Refresh falló — limpiar tokens y dejar que el guard redirija al login
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
      return Promise.reject(error);
    } finally {
      isRefreshing = false;
    }
  },
);

export default apiClient;
