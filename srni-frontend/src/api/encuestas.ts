import apiClient from './client';
import type { PaginatedResponse } from './hogares';

export interface SesionResumen {
  id: string;
  hogar: string;
  hogar_codigo: string;
  instrumento_nombre: string;
  ruta_entrevista: string;
  estado: 'EN_PROCESO' | 'FINALIZADA' | 'CANCELADA';
  porcentaje_completado: number;
  encuestador_nombre: string;
  created_at: string;
  updated_at: string;
}

export const encuestasApi = {
  listar: (params?: { page?: number; estado?: string; hogar?: string }) =>
    apiClient.get<PaginatedResponse<SesionResumen>>('/api/encuestas/', { params }),

  detalle: (id: string) =>
    apiClient.get<SesionResumen>(`/api/encuestas/${id}/`),
};
