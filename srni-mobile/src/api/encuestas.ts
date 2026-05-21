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
  pregunta_id: string;
  valor: string;
}

export interface FinalizarPayload {
  observaciones?: string;
}

export interface RespuestaServidor {
  id: string;
  pregunta: string;       // UUID de Pregunta
  pregunta_codigo: string;
  pregunta_texto: string;
  valor: string;
  updated_at: string;
}

export interface BulkRespuestaResult {
  porcentaje_completado: number;
  creadas: number;
  actualizadas: number;
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

  /** Envía N respuestas en una sola transacción — mucho más eficiente que N llamadas individuales. */
  responderBulk: (sesionId: string, respuestas: ResponderPayload[]) =>
    apiClient.post<BulkRespuestaResult>(
      `/api/encuestas/${sesionId}/responder-bulk/`,
      { respuestas },
    ),

  /** Descarga todas las respuestas guardadas para restaurar borradores al abrir un capítulo. */
  getRespuestas: (sesionId: string) =>
    apiClient.get<RespuestaServidor[]>(`/api/encuestas/${sesionId}/respuestas/`),

  finalizar: (sesionId: string, payload?: FinalizarPayload) =>
    apiClient.post<SesionDetalle>(
      `/api/encuestas/${sesionId}/finalizar/`,
      payload ?? {},
    ),
};
