import apiClient from './client';
import type {
  SesionResumen, SesionDetalle,
  RespuestaEncuesta, PaginatedResponse,
} from '../types';

export interface CrearSesionPayload {
  hogar: string;
  instrumento: string;
  ruta_entrevista?: string;
}

export interface ResponderPayload {
  pregunta_id: string;  // UUID de Pregunta (Sprint 7: cambio de number a string)
  valor: string;
}

export interface FinalizarPayload {
  observaciones?: string;
}

export const encuestasApi = {
  listar: (params?: { hogar?: string; estado?: string; page?: number }) =>
    apiClient.get<PaginatedResponse<SesionResumen>>('/api/encuestas/', { params }),

  detalle: (id: string) =>
    apiClient.get<SesionDetalle>(`/api/encuestas/${id}/`),

  crear: (payload: CrearSesionPayload) =>
    apiClient.post<SesionDetalle>('/api/encuestas/', payload),

  responder: (sesionId: string, payload: ResponderPayload) =>
    apiClient.post<RespuestaEncuesta>(
      `/api/encuestas/${sesionId}/responder/`,
      payload,
    ),

  finalizar: (sesionId: string, payload?: FinalizarPayload) =>
    apiClient.post<SesionDetalle>(
      `/api/encuestas/${sesionId}/finalizar/`,
      payload ?? {},
    ),
};
