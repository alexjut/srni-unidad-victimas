import apiClient from './client';
import type { PaginatedResponse } from './hogares';

export interface SesionResumen {
  id: string;
  hogar: string;
  instrumento: string;
  instrumento_codigo: string | null;
  instrumento_nombre: string | null;
  instrumento_numero: string | null;
  encuestador: string;
  encuestador_nombre: string | null;
  direccion_territorial: number | null;
  direccion_territorial_nombre: string | null;
  estado: string;
  estado_display: string;
  porcentaje_completado: number;
  fecha_inicio: string;
  fecha_fin: string | null;
  created_at: string;
  updated_at: string;
}

export interface RespuestaEncuesta {
  id: string;
  sesion: string;
  pregunta: string;
  pregunta_codigo: string;
  pregunta_texto: string;
  miembro: string | null;
  valor: string;
  updated_at: string;
}

export interface SesionDetalle extends SesionResumen {
  ruta_entrevista: string;
  departamento_atencion: number | null;
  departamento_atencion_nombre: string | null;
  municipio_atencion: number | null;
  municipio_atencion_nombre: string | null;
  punto_atencion: number | null;
  punto_atencion_nombre: string | null;
  observaciones: string | null;
  respuestas: RespuestaEncuesta[];
  total_respuestas: number;
}

export const encuestasApi = {
  listar: (params?: { page?: number; estado?: string; hogar?: string }) =>
    apiClient.get<PaginatedResponse<SesionResumen>>('/api/encuestas/', { params }),

  detalle: (id: string) =>
    apiClient.get<SesionDetalle>(`/api/encuestas/${id}/`),
};
