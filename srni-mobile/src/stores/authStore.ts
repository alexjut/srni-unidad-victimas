/**
 * Store de autenticación con Zustand.
 * Los tokens viven SOLO en expo-secure-store (keychain nativo).
 * El estado en memoria solo guarda el perfil del usuario y flags de sesión.
 */
import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { authApi, type UsuarioMe } from '../api/auth';

interface AuthState {
  usuario: UsuarioMe | null;
  cargando: boolean;
  error: string | null;

  // Acciones
  login: (codigo: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  cargarPerfil: () => Promise<void>;
  limpiarError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  usuario: null,
  cargando: false,
  error: null,

  login: async (codigo, password) => {
    set({ cargando: true, error: null });
    try {
      const { data } = await authApi.login({
        codigo_usuario: codigo.trim().toUpperCase(),
        password,
      });

      await SecureStore.setItemAsync('access_token', data.access);
      await SecureStore.setItemAsync('refresh_token', data.refresh);

      // Cargar perfil inmediatamente tras login
      const { data: me } = await authApi.me();
      set({ usuario: me, cargando: false });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Error al iniciar sesión. Verifica tus credenciales.';
      set({ error: msg, cargando: false });
      throw err;
    }
  },

  logout: async () => {
    try {
      const refresh = await SecureStore.getItemAsync('refresh_token');
      if (refresh) await authApi.logout(refresh);
    } finally {
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
      set({ usuario: null, error: null });
    }
  },

  cargarPerfil: async () => {
    const token = await SecureStore.getItemAsync('access_token');
    if (!token) return;
    try {
      const { data } = await authApi.me();
      set({ usuario: data });
    } catch {
      // Token expirado y refresh también falló → limpiar
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
      set({ usuario: null });
    }
  },

  limpiarError: () => set({ error: null }),
}));
