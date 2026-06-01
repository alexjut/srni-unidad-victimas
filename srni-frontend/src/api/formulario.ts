import api from './client';

// --- Tipos ---

export interface Opcion {
  id: string;
  valor: string;
  etiqueta: string;
  orden: number;
  finaliza_capitulo: boolean;
}

export interface Pregunta {
  id: string;
  codigo_externo: string;
  no_pregunta: string;
  texto: string;
  descripcion_ayuda: string;
  tipo: string;
  nivel: string;
  orden: number;
  obligatoria: boolean;
  activa: boolean;
  opciones: Opcion[];
}

export interface CapituloResumen {
  id: string;
  codigo: string;
  nombre: string;
  orden: number;
  poblacion_objetivo: string;
  total_preguntas: number;
}

export interface CapituloDetalle extends CapituloResumen {
  objetivo: string;
  preguntas: Pregunta[];
}

export interface Instrumento {
  id: string;
  codigo: string;
  nombre: string;
  version: string;
  activo: boolean;
  vigente_desde: string;
  vigente_hasta: string | null;
  vigente: boolean;
  fuente_documental: string;
  total_capitulos: number;
  capitulos: CapituloResumen[];
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- API ---

export const formularioApi = {
  instrumentos: () =>
    api.get<PaginatedResponse<Instrumento>>('/api/formulario/instrumentos/'),

  instrumento: (id: string) =>
    api.get<Instrumento>(`/api/formulario/instrumentos/${id}/`),

  capituloDetalle: (id: string) =>
    api.get<CapituloDetalle>(`/api/formulario/capitulos/${id}/`),
};
