import api from './client';

// --- Tipos ---
export interface Perfil {
  id: number;
  codigo: string;
  nombre: string;
  puede_buscar_rni: boolean;
  puede_caracterizar: boolean;
  puede_ver_reportes: boolean;
  puede_administrar: boolean;
  activo: boolean;
}

export interface Usuario {
  id: string;
  codigo_usuario: string;
  nombre_completo: string;
  email: string;
  perfil: number | null;
  perfil_codigo: string;
  perfil_nombre: string;
  activo: boolean;
  es_admin: boolean;
  fecha_ultimo_login: string | null;
  created_at: string;
}

export interface CrearUsuarioInput {
  codigo_usuario: string;
  nombre_completo: string;
  email: string;
  perfil: number | null;
  activo: boolean;
  es_admin: boolean;
  password: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- API ---
export const usuariosApi = {
  lista: (params?: {
    search?: string;
    activo?: boolean;
    perfil__codigo?: string;
    ordering?: string;
    page?: number;
    page_size?: number;
  }) => api.get<PaginatedResponse<Usuario>>('/api/usuarios/', { params }),

  crear: (data: CrearUsuarioInput) => api.post<Usuario>('/api/usuarios/', data),

  editar: (id: string, data: Partial<CrearUsuarioInput>) =>
    api.patch<Usuario>(`/api/usuarios/${id}/`, data),

  activar: (id: string) => api.post(`/api/usuarios/${id}/activar/`),
  desactivar: (id: string) => api.post(`/api/usuarios/${id}/desactivar/`),
  resetPassword: (id: string, password: string) =>
    api.post(`/api/usuarios/${id}/reset_password/`, { password }),

  eliminar: (id: string) => api.delete(`/api/usuarios/${id}/`),

  perfiles: () => api.get<Perfil[]>('/api/usuarios/perfiles/'),
};
