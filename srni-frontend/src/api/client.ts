/**
 * Cliente Axios para el backend SRNI
 *
 * Interceptores:
 *  1. Request  → añade Authorization: Bearer <access_token>
 *  2. Response → si 401, intenta renovar con refresh token y reintenta
 *                si el refresh falla → logout automático
 */
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Interceptor de request: añade Bearer token ────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// ── Interceptor de response: refresh automático en 401 ───────────────────────
let refrescando = false;
let colaEspera: Array<(token: string) => void> = [];

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    // Solo manejar 401 que no sea la propia URL de refresh
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes('/api/auth/token/refresh/')
    ) {
      original._retry = true;

      if (refrescando) {
        // Encola la petición hasta que el refresh termine
        return new Promise((resolve) => {
          colaEspera.push((newToken: string) => {
            original.headers['Authorization'] = `Bearer ${newToken}`;
            resolve(apiClient(original));
          });
        });
      }

      refrescando = true;
      const refreshToken = sessionStorage.getItem('refresh_token');

      try {
        const { data } = await axios.post(
          `${import.meta.env.VITE_API_URL ?? ''}/api/auth/token/refresh/`,
          { refresh: refreshToken },
        );
        const newAccess: string = data.access;
        useAuthStore.getState().setTokens(newAccess, refreshToken!);

        // Liberar cola
        colaEspera.forEach((cb) => cb(newAccess));
        colaEspera = [];

        original.headers['Authorization'] = `Bearer ${newAccess}`;
        return apiClient(original);
      } catch {
        // Refresh falló → logout
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(error);
      } finally {
        refrescando = false;
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
