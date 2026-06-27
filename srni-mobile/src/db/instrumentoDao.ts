/**
 * Tipos del instrumento — Sprint 18 Fase E (post-refactor a memoria).
 *
 * Este archivo originalmente era un DAO sobre SQLite (tablas capitulos,
 * preguntas, opciones_respuesta, reglas_skip_logic, instrumento_meta).
 * Tras el refactor F1B + Fase C, los instrumentos viven en memoria
 * (src/services/instrumentos.ts) cargados desde el bundle.
 *
 * Lo único que queda aquí son los TIPOS de fila, importados por:
 *   - src/services/instrumentos.ts (los devuelve)
 *   - src/services/skipLogic.ts (los consume)
 *   - app/(main)/formulario/index.tsx (CapituloRow, InstrumentoMeta)
 *   - app/(main)/formulario/[temaId].tsx (PreguntaRow, OpcionRow, ReglaSkipLogicRow)
 *   - app/(main)/formulario/grabacion-entrevista.tsx (PreguntaRow, OpcionRow)
 *
 * Si en el futuro se mueven a un archivo `types/instrumento.ts` puro, podemos
 * eliminar este archivo del todo. Por ahora se mantiene para minimizar el
 * diff del refactor.
 */

export interface InstrumentoMeta {
  instrumento_id: string;
  perfil_codigo: string;
  version: string;
  descargado_en: string;
}

export interface CapituloRow {
  id: string;
  codigo: string;
  nombre: string;
  orden: number;
  nivel: string;   // HOGAR | PERSONA
  activo: number;
}

export interface PreguntaRow {
  id: string;
  capitulo_id: string;
  codigo_externo: string;
  no_pregunta: string;
  texto: string;
  descripcion_ayuda: string;
  /** TEXTO | NUMERICO | FECHA | RADIO | LISTA | LISTA_MULTIPLE | BOOLEAN | TEXTO_LARGO | COMBO_DINAMICO */
  tipo: string;
  nivel: string;   // HOGAR | PERSONA
  orden: number;
  obligatoria: number;   // 0 | 1
  activa: number;        // 0 | 1
  es_precargada?: number; // 0 | 1 — datos que vienen del RUV/sesión, NO se preguntan
  validaciones: string;  // JSON serializado
}

export interface OpcionRow {
  id: string;
  pregunta_id: string;
  valor: string;
  etiqueta: string;
  orden: number;
  finaliza_capitulo: number; // 0 | 1
}

export interface ReglaSkipLogicRow {
  id: string;
  instrumento_id: string;
  pregunta_origen_codigo: string | null;
  valor_trigger: string;
  expresion_origen: string;
  pregunta_afectada_id: string | null;
  pregunta_afectada_codigo: string | null;
  capitulo_afectado_id: string | null;
  /** HABILITAR | DESHABILITAR | OBLIGAR | FINALIZAR */
  accion: string;
}
