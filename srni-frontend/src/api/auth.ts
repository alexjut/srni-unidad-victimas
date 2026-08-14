import apiClient from './client';

export interface LoginPayload {
  codigo_usuario: string;
  password: string;
}

export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface PerfilUsuario {
  codigo_usuario: string;
  nombre_completo: string;
  email: string;
  perfil: {
    codigo: string;
    nombre: string;
    puede_buscar_rni: boolean;
    puede_caracterizar: boolean;
    puede_ver_reportes?: boolean;
    puede_administrar?: boolean;
    /** Autoriza excepciones de vigencia — ver `authStore`. */
    puede_autorizar_excepciones?: boolean;
  } | null;
}

export const authApi = {
  login: (payload: LoginPayload) =>
    apiClient.post<TokenResponse>('/api/auth/token/', payload),

  refresh: (refresh: string) =>
    apiClient.post<{ access: string }>('/api/auth/token/refresh/', { refresh }),

  perfil: () =>
    apiClient.get<PerfilUsuario>('/api/auth/perfil/'),

  logout: (refresh: string) =>
    apiClient.post('/api/auth/logout/', { refresh }),

  cambiarPassword: (payload: { password_actual: string; password_nueva: string }) =>
    apiClient.post('/api/auth/cambiar-password/', payload),
};
