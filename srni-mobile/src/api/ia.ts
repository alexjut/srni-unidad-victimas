/**
 * API del módulo IA — proxy hacia Gemini vía backend Django.
 *
 * Regla de seguridad: el móvil NUNCA llama a Google directamente.
 * Toda llamada pasa por /api/ia/ en el backend SRNI.
 */
import apiClient from './client';

export interface ConsentimientoPayload {
  sesion_encuesta_id: string;
  acepto: boolean;
}

export interface ConsentimientoResponse {
  id: string;
  sesion_encuesta: string;
  acepto: boolean;
  firma_digital: string;
  creado_en: string;
}

export interface EstadoIAResponse {
  activo: boolean;
  consentimiento_id: string | null;
  sesion_ia_id: string | null;
  total_llamadas: number;
}

export interface MapearAudioPayload {
  sesion_encuesta_id: string;
  pregunta_id: number;
  texto_transcrito: string;
}

export interface MapearAudioResponse {
  sugerencia: string;
  confianza: number;
  modelo: string;
}

export const iaApi = {
  /** Registrar consentimiento del encuestador antes de activar IA. */
  registrarConsentimiento: (payload: ConsentimientoPayload) =>
    apiClient.post<ConsentimientoResponse>('/api/ia/consentimiento/', payload),

  /** Consultar si la IA está activa para una sesión. */
  estado: (sesionEncuestaId: string) =>
    apiClient.get<EstadoIAResponse>('/api/ia/estado/', {
      params: { sesion_encuesta_id: sesionEncuestaId },
    }),

  /**
   * Enviar texto transcrito al proxy IA → Gemini.
   * El audio ya fue transcrito en el dispositivo con expo-speech.
   * NUNCA se envía el audio crudo.
   */
  mapearAudio: (payload: MapearAudioPayload) =>
    apiClient.post<MapearAudioResponse>('/api/ia/mapear-audio/', payload),
};
