/**
 * Store de autenticación — Zustand
 *
 * SEGURIDAD:
 * - Tokens en sessionStorage (nunca localStorage)
 * - sessionStorage.clear() al hacer logout
 * - Compatible con el backend Django JWT (access 15 min / refresh 8 h)
 */
import { create } from 'zustand';

export interface Usuario {
  codigo_usuario: string;
  nombre_completo: string;
  email: string;
  perfil: {
    codigo: string;
    nombre: string;
    puede_caracterizar: boolean;
    puede_buscar_rni: boolean;
    puede_ver_reportes?: boolean;
    puede_administrar?: boolean;
    /**
     * Autoriza excepciones de vigencia (14-ago-2026). Opcional: un backend
     * anterior no lo manda y el menú simplemente no muestra la opción, en vez
     * de romper la sesión de quien ya estaba dentro.
     */
    puede_autorizar_excepciones?: boolean;
  } | null;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  usuario: Usuario | null;

  setTokens: (access: string, refresh: string) => void;
  setUsuario: (u: Usuario) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  // Restaurar tokens desde sessionStorage al cargar
  accessToken:  sessionStorage.getItem('access_token'),
  refreshToken: sessionStorage.getItem('refresh_token'),
  usuario: null,

  setTokens: (access, refresh) => {
    sessionStorage.setItem('access_token',  access);
    sessionStorage.setItem('refresh_token', refresh);
    set({ accessToken: access, refreshToken: refresh });
  },

  setUsuario: (u) => set({ usuario: u }),

  logout: () => {
    sessionStorage.clear();   // limpia tokens Y datos cacheados
    set({ accessToken: null, refreshToken: null, usuario: null });
  },
}));
