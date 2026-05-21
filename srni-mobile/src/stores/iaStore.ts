/**
 * Store IA — estado del asistente de voz Gemini.
 *
 * Estados posibles:
 *   inactivo              — IA no activada (sin consentimiento o apagada manualmente)
 *   grabando              — micrófono activo, capturando audio
 *   grabando_entrevista   — capturando entrevista completa (modo batch)
 *   procesando            — texto enviado al backend, esperando sugerencia
 *   procesando_entrevista — entrevista completa enviada al backend en modo batch
 *   sugerida              — sugerencia disponible para aceptar/rechazar
 *   error                 — Gemini falló (503); formulario sigue funcionando
 */
import { create } from 'zustand';
import { iaApi } from '../api/ia';
import type { MapearAudioResponse, ResultadoBatch, PreguntaBatch } from '../api/ia';

export type EstadoIA =
  | 'inactivo'
  | 'grabando'
  | 'grabando_entrevista'
  | 'procesando'
  | 'procesando_entrevista'
  | 'sugerida'
  | 'error';

// Re-exportar para que los consumidores no importen directamente de api/ia
export type { ResultadoBatch };

interface IAState {
  estado: EstadoIA;
  activo: boolean;                           // consentimiento activo
  consentimientoId: string | null;
  sugerencia: MapearAudioResponse | null;
  preguntaActivaId: string | null;           // UUID de la pregunta activa (modo individual)
  resultadosBatch: ResultadoBatch[] | null;  // resultados del modo batch
  errorMensaje: string | null;

  // Acciones — modo individual
  activar: (sesionEncuestaId: string) => Promise<void>;
  desactivar: () => void;
  iniciarGrabacion: (preguntaId: string) => void;
  enviarTexto: (
    sesionEncuestaId: string,
    preguntaId: string,
    textoTranscrito: string,
  ) => Promise<void>;
  aceptarSugerencia: () => MapearAudioResponse | null;
  rechazarSugerencia: () => void;

  // Acciones — modo batch (entrevista completa)
  procesarEntrevista: (
    sesionEncuestaId: string,
    capituloId: string,
    transcripcion: string,
    preguntas: PreguntaBatch[],
  ) => Promise<void>;
  limpiarResultadosBatch: () => void;

  resetear: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────

export const useIAStore = create<IAState>((set, get) => ({
  estado: 'inactivo',
  activo: false,
  consentimientoId: null,
  sugerencia: null,
  preguntaActivaId: null,
  resultadosBatch: null,
  errorMensaje: null,

  /**
   * Registra el consentimiento y activa la IA para la sesión.
   * Si el consentimiento falla, no activa.
   */
  activar: async (sesionEncuestaId: string) => {
    try {
      const { data } = await iaApi.registrarConsentimiento({
        sesion_encuesta_id: sesionEncuestaId,
        acepto: true,
      });
      set({
        activo: true,
        estado: 'inactivo',
        consentimientoId: data.id,
        errorMensaje: null,
      });
    } catch {
      set({ activo: false, errorMensaje: 'No se pudo registrar el consentimiento.' });
    }
  },

  /** Desactiva la IA y limpia el estado. */
  desactivar: () => {
    set({
      activo: false,
      estado: 'inactivo',
      consentimientoId: null,
      sugerencia: null,
      preguntaActivaId: null,
      errorMensaje: null,
    });
  },

  /** Marca que la grabación comenzó para una pregunta específica. */
  iniciarGrabacion: (preguntaId: string) => {
    set({ estado: 'grabando', preguntaActivaId: preguntaId, sugerencia: null });
  },

  /**
   * Envía el texto transcrito al backend y espera la sugerencia.
   * La transcripción la hace el caller (expo-speech) antes de llamar esto.
   */
  enviarTexto: async (
    sesionEncuestaId: string,
    preguntaId: string,
    textoTranscrito: string,
  ) => {
    set({ estado: 'procesando', errorMensaje: null });
    try {
      const { data } = await iaApi.mapearAudio({
        sesion_encuesta_id: sesionEncuestaId,
        pregunta_id: preguntaId,
        texto_transcrito: textoTranscrito,
      });
      set({ estado: 'sugerida', sugerencia: data });
    } catch {
      set({
        estado: 'error',
        errorMensaje: 'El asistente IA no está disponible. Continúa de forma manual.',
      });
    }
  },

  /** Devuelve la sugerencia y limpia el estado (el caller aplica el valor). */
  aceptarSugerencia: () => {
    const { sugerencia } = get();
    set({ estado: 'inactivo', sugerencia: null, preguntaActivaId: null });
    return sugerencia;
  },

  /** Descarta la sugerencia sin aplicarla. */
  rechazarSugerencia: () => {
    set({ estado: 'inactivo', sugerencia: null, preguntaActivaId: null });
  },

  /**
   * Procesa la transcripción completa de una entrevista contra todas las
   * preguntas del capítulo en una sola llamada batch a Gemini.
   * Los resultados quedan en `resultadosBatch` para que la pantalla revision-ia los lea.
   */
  procesarEntrevista: async (
    sesionEncuestaId: string,
    capituloId: string,
    transcripcion: string,
    preguntas,
  ) => {
    set({ estado: 'procesando_entrevista', errorMensaje: null, resultadosBatch: null });
    try {
      const { data } = await iaApi.procesarEntrevista({
        sesion_encuesta_id: sesionEncuestaId,
        capitulo_id: capituloId,
        transcripcion_completa: transcripcion,
        preguntas,
      });
      set({ estado: 'inactivo', resultadosBatch: data.resultados });
    } catch {
      set({
        estado: 'error',
        errorMensaje: 'El asistente IA no está disponible. Continúa de forma manual.',
      });
    }
  },

  /** Limpia los resultados batch (llamar al salir de revision-ia). */
  limpiarResultadosBatch: () => {
    set({ resultadosBatch: null });
  },

  /** Reset completo — usar al salir del formulario. */
  resetear: () => {
    set({
      estado: 'inactivo',
      activo: false,
      consentimientoId: null,
      sugerencia: null,
      preguntaActivaId: null,
      resultadosBatch: null,
      errorMensaje: null,
    });
  },
}));
