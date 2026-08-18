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
  /** Sprint 21: null si la pregunta es HOGAR, UUID del miembro si es PERSONA. */
  miembro_id?: string | null;
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

  /**
   * Sprint 19 — actualiza campos de una sesión (PATCH).
   * Usado para guardar ubicación de atención (DT/Depto/Mun/Punto) después de
   * que el encuestador la elija en la pantalla ubicacion-atencion.
   */
  actualizar: (id: string, payload: Partial<{
    direccion_territorial: number | null;
    departamento_atencion: number | null;
    municipio_atencion: number | null;
    punto_atencion: number | null;
  }>) =>
    apiClient.patch<SesionDetalle>(`/api/encuestas/${id}/`, payload),

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

/*
 * Acá vivía `registrarExcepcionVigencia`, que subía por multipart la foto del
 * fallo, la tutela o el auto desde el celular.
 *
 * Se retiró el 14-ago-2026: el caracterizador no debe tener ese documento —le
 * llega por canal institucional a quien coordina—. La excepción se autoriza
 * antes, desde el front web (`POST /api/habilitaciones/`), y la app solo la
 * consume: viaja en la precarga de la jornada como `habilitada_por_excepcion`.
 *
 * El endpoint viejo responde 410 y explica a dónde ir, para que una APK
 * anterior a la v1.2.0 que siga instalada no muestre un error de red.
 */
