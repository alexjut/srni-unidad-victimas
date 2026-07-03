import api from './client';

// --- Tipos ---

export interface Departamento {
  id: number;
  codigo_dane: string;
  nombre: string;
}

export interface Municipio {
  id: number;
  codigo_dane: string;
  nombre: string;
  departamento: number;
  departamento_nombre: string;
}

export interface DireccionTerritorial {
  id: number;
  codigo: string;
  nombre: string;
}

export interface PuntoAtencion {
  id: number;
  codigo: string;
  nombre: string;
  direccion_territorial: number;
  direccion_territorial_nombre: string;
}

export interface TipoDocumento {
  codigo: string;
  nombre: string;
  activo: boolean;
}

export interface Vereda {
  id: number;
  codigo_dane: string;
  nombre: string;
  municipio: number;
  municipio_nombre: string;
  activo: boolean;
}

export interface ComunidadNegra {
  id: number;
  codigo: string;
  nombre: string;
  municipio: number;
  municipio_nombre: string;
  activo: boolean;
}

export interface ResguardoIndigena {
  id: number;
  codigo: string;
  nombre: string;
  municipio: number;
  municipio_nombre: string;
  pueblo: string;
  activo: boolean;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- API ---

export const parametricasApi = {
  departamentos: () =>
    api.get<PaginatedResponse<Departamento>>('/api/parametricas/departamentos/'),

  municipios: (params?: { departamento?: number; page?: number }) =>
    api.get<PaginatedResponse<Municipio>>('/api/parametricas/municipios/', { params }),

  municipiosTodos: () =>
    api.get<Municipio[]>('/api/parametricas/municipios/todos/'),

  direccionesTerritoriales: () =>
    api.get<PaginatedResponse<DireccionTerritorial>>('/api/parametricas/direcciones-territoriales/'),

  puntosAtencion: (params?: { direccion_territorial?: number }) =>
    api.get<PaginatedResponse<PuntoAtencion>>('/api/parametricas/puntos-atencion/', { params }),

  tiposDocumento: () =>
    api.get<PaginatedResponse<TipoDocumento>>('/api/parametricas/tipos-documento/'),

  veredas: (params?: { municipio?: number; page?: number }) =>
    api.get<PaginatedResponse<Vereda>>('/api/parametricas/veredas/', { params }),

  comunidadesNegras: (params?: { municipio?: number; page?: number }) =>
    api.get<PaginatedResponse<ComunidadNegra>>('/api/parametricas/comunidades-negras/', { params }),

  resguardosIndigenas: (params?: { municipio?: number; page?: number }) =>
    api.get<PaginatedResponse<ResguardoIndigena>>('/api/parametricas/resguardos-indigenas/', { params }),
};
