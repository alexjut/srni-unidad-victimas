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

/**
 * Registra el uso de una ruta que OMITE la regla de vigencia (Manual §5.1.1).
 *
 * Va aparte de `encuestasApi` porque es multipart: lleva la foto del fallo, la
 * tutela o el auto. El soporte no es opcional — un control que se salta sin
 * dejar rastro deja de ser un control, y la ruta la elige el encuestador.
 */
export async function registrarExcepcionVigencia(
  sesionId: string,
  datos: {
    victima_id: string;
    ruta: string;
    soporte_uri: string;
    soporte_nombre: string;
    observacion?: string;
  },
) {
  const form = new FormData();
  form.append('victima_id', datos.victima_id);
  form.append('ruta', datos.ruta);
  form.append('observacion', datos.observacion ?? '');
  // React Native arma el multipart con esta forma de objeto; `fetch`/axios no
  // aceptan un Blob desde una uri local en Android.
  form.append('soporte', {
    uri: datos.soporte_uri,
    name: datos.soporte_nombre || 'soporte.jpg',
    type: 'image/jpeg',
  } as unknown as Blob);

  return apiClient.post<{ id: string; ruta: string; vigente_hasta: string }>(
    `/api/encuestas/${sesionId}/excepcion-vigencia/`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
}
