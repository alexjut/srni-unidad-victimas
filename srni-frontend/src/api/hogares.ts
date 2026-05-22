import apiClient from './client';

export interface HogarResumen {
  id: string;
  codigo: string;
  estado: string;
  numero_personas: number;
  municipio_nombre: string | null;
  created_at: string;
  autorizado_nombre: string;
}

export interface MiembroResumen {
  id: string;
  nombre_completo: string;
  tipo_documento: string;
  numero_documento: string;
  parentesco_display: string;
  rol: string;
  rol_display: string;
  es_autorizado: boolean;
  genero: string;
}

export interface HogarDetalle extends HogarResumen {
  miembros: MiembroResumen[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const hogaresApi = {
  listar: (params?: { page?: number; estado?: string }) =>
    apiClient.get<PaginatedResponse<HogarResumen>>('/api/hogares/', { params }),

  detalle: (id: string) =>
    apiClient.get<HogarDetalle>(`/api/hogares/${id}/`),
};
