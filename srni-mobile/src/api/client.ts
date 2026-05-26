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

// Sprint 18 Fase G — Redactor de PII para logs remotos.
// Endpoints donde la URL o el body pueden contener PII de víctimas:
//   - /api/victimas/*           (búsqueda con documento, detalle)
//   - /api/hogares/*/agregar-miembro/ (nombres, documentos)
//   - /api/hogares/*/cambiar-autorizado/
//   - /api/encuestas/*/responder*    (valor de respuestas puede ser PII)
//   - /api/auth/login/          (password en body de request)
const ENDPOINTS_PII = [
  '/api/victimas/',
  '/api/hogares/',
  '/api/encuestas/',
  '/api/auth/login',
  '/api/auth/cambiar-password',
];

function sanitizarUrl(url: string | undefined): string {
  if (!url) return '?';
  // Si el endpoint maneja PII, quitar query string y dejar solo el path
  const sinQuery = url.split('?')[0];
  for (const pii of ENDPOINTS_PII) {
    if (sinQuery.includes(pii)) {
      return `${sinQuery} [query+body redactados por PII]`;
    }
  }
  return url;
}

function sanitizarBody(url: string | undefined, body: unknown): unknown {
  if (!url) return body;
  const sinQuery = url.split('?')[0];
  for (const pii of ENDPOINTS_PII) {
    if (sinQuery.includes(pii)) {
      return '[REDACTADO — endpoint PII]';
    }
  }
  if (typeof body === 'object') return body;
  return String(body ?? '').slice(0, 300);
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Sprint 17: loguear errores HTTP al backend para visibilidad
    // Sprint 18 Fase G: sanitizar URL+body si el endpoint es de PII (víctimas,
    // hogares, encuestas, login). Solo se loguea el path, sin query string.
    if (error.response?.status !== 401) {
      import('../services/errorReporter').then(({ reportarError }) => {
        const urlSafe = sanitizarUrl(original?.url);
        const bodySafe = sanitizarBody(original?.url, error.response?.data);
        reportarError({
          nivel: error.response?.status && error.response.status >= 500 ? 'error' : 'warn',
          mensaje: `HTTP ${error.response?.status ?? 'red'} ${original?.method?.toUpperCase()} ${urlSafe}`,
          pantalla: '[axios-interceptor]',
          contexto: {
            status: error.response?.status,
            body: bodySafe,
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
