import apiClient from './client';

export interface LoginPayload {
  codigo_usuario: string;
  password: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface UsuarioMe {
  id: string;
  codigo_usuario: string;
  nombre_completo: string;
  email: string;
  perfil: {
    codigo: string;
    nombre: string;
    puede_buscar_rni: boolean;
    puede_caracterizar: boolean;
    puede_ver_reportes: boolean;
    puede_administrar: boolean;
  } | null;
}

export const authApi = {
  login: (payload: LoginPayload) =>
    apiClient.post<TokenPair>('/api/auth/login/', payload),

  refresh: (refresh: string) =>
    apiClient.post<TokenPair>('/api/auth/refresh/', { refresh }),

  logout: (refresh: string) =>
    apiClient.post('/api/auth/logout/', { refresh }),

  me: () =>
    apiClient.get<UsuarioMe>('/api/auth/me/'),

  cambiarPassword: (payload: {
    password_actual: string;
    password_nuevo: string;
    refresh?: string;
  }) => apiClient.post('/api/auth/cambiar-password/', payload),
};
