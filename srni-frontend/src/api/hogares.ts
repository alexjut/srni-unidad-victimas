import apiClient from './client';

export interface HogarResumen {
  id: string;
  codigo_hogar: string;
  estado: string;
  estado_display: string;
  autorizado: string;
  autorizado_hash: string;
  municipio: number | null;
  municipio_nombre: string | null;
  total_miembros: number;
  numero_personas: number;
  encuestador_nombre: string | null;
  created_at: string;
  updated_at: string;
}

export interface MiembroResumen {
  id: string;
  nombre_completo: string;
  parentesco: string;
  parentesco_display: string;
  genero: string;
  fecha_nacimiento: string | null;
  rol: string;
  rol_display: string;
  es_autorizado: boolean;
  estado_inclusion: string;
  estado_inclusion_display: string;
  tipo_persona: string;
  incluido_ruv: boolean;
  tiene_discapacidad: boolean;
  victima: string | null;
  victima_hash: string | null;
}

export interface SesionAnidada {
  id: string;
  hogar: string;
  instrumento_codigo: string | null;
  instrumento_nombre: string | null;
  instrumento_numero: string | null;
  encuestador_nombre: string | null;
  estado: string;
  estado_display: string;
  porcentaje_completado: number;
  fecha_inicio: string;
  fecha_fin: string | null;
  created_at: string;
}

export interface HogarDetalle {
  id: string;
  codigo_hogar: string;
  autorizado: string;
  autorizado_hash: string;
  municipio: number | null;
  municipio_nombre: string | null;
  tipo_vivienda: string;
  tipo_vivienda_display: string;
  condicion_ocupacion: string;
  condicion_ocupacion_display: string;
  estrato: number;
  numero_cuartos: number;
  numero_personas: number;
  estado: string;
  estado_display: string;
  observaciones: string | null;
  miembros: MiembroResumen[];
  total_miembros: number;
  sesiones: SesionAnidada[];
  total_sesiones: number;
  encuestador_nombre: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const hogaresApi = {
  listar: (params?: { page?: number; estado?: string; search?: string }) =>
    apiClient.get<PaginatedResponse<HogarResumen>>('/api/hogares/', { params }),

  detalle: (id: string) =>
    apiClient.get<HogarDetalle>(`/api/hogares/${id}/`),
};
