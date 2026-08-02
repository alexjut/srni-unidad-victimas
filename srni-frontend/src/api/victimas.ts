import api from './client';

// --- Tipos ---

export interface TipoDocumento {
  id: number;
  codigo: string;
  nombre: string;
  aplica_nacionales: boolean;
  aplica_extranjeros: boolean;
  activo: boolean;
}

export interface HogarActivo {
  id: string;
  estado: string;
  total_miembros: number;
  total_sesiones: number;
}

export interface VictimaResumen {
  id: string;
  tipo_documento_codigo: string;
  numero_documento_hash: string;
  genero: string;
  estado_civil: string;
  pertenencia_etnica: string;
  discapacidad: boolean;
  tipo_discapacidad: string;
  estado_ruv: string;
  municipio_residencia: string | null;
  municipio_residencia_nombre: string | null;
  departamento_nombre: string | null;
  created_at: string;
  hogar_activo: HogarActivo | null;
  es_victima_pruebas: boolean;
}

/**
 * Cuerpo del 409 de POST /api/victimas/buscar/.
 *
 * En el padrón real hay 768.096 documentos compartidos por más de una víctima
 * (~15,6 % de las búsquedas posibles). El backend NO elige uno: devuelve todos y
 * confirma quien tiene a la persona enfrente. Los candidatos vienen sin PII
 * —el nombre exige abrir el detalle, que pide permiso—, así que se distinguen
 * por municipio, estado RUV y demás metadatos.
 */
export interface BusquedaAmbigua {
  detail: string;
  ambiguo: true;
  candidatos: VictimaResumen[];
}

/** Extrae el cuerpo del 409, o null si el error es otra cosa. */
export function busquedaAmbigua(err: any): BusquedaAmbigua | null {
  const data = err?.response?.data;
  if (err?.response?.status === 409 && data?.ambiguo) return data as BusquedaAmbigua;
  return null;
}

export interface HechoVictimizante {
  id: string;
  hecho: {
    codigo: string;
    nombre: string;
    descripcion: string;
    activo: boolean;
    orden: number;
  };
  fecha_hecho: string | null;
  lugar_hecho: {
    id: number;
    codigo_dane: string;
    nombre: string;
    departamento_nombre: string;
  } | null;
  fuente: string;
  observaciones: string;
  created_at: string;
}

export interface VictimaDetalle {
  id: string;
  tipo_documento: TipoDocumento;
  numero_documento: string;
  primer_nombre: string;
  segundo_nombre: string;
  primer_apellido: string;
  segundo_apellido: string;
  fecha_nacimiento: string;
  genero: string;
  estado_civil: string;
  pertenencia_etnica: string;
  pueblo_indigena: string;
  discapacidad: boolean;
  tipo_discapacidad: string;
  estado_ruv: string;
  hechos_victimizantes: HechoVictimizante[];
  municipio_residencia: {
    id: number;
    codigo_dane: string;
    nombre: string;
    departamento_nombre: string;
  } | null;
  creado_por: number | null;
  creado_por_nombre: string | null;
  created_at: string;
  updated_at: string;
}

export interface RegistrarDesdeFuenteRequest {
  tipo_documento: string;
  numero_documento: string;
  primer_nombre: string;
  segundo_nombre?: string;
  primer_apellido: string;
  segundo_apellido?: string;
  fecha_nacimiento: string;
  genero?: string;
  estado_ruv?: string;
  pertenencia_etnica?: string;
  discapacidad?: boolean;
  municipio_residencia_codigo?: string;
  fuente_origen?: string;
}

export interface RegistrarDesdeFuenteResponse {
  victima_id: string;
  created: boolean;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- API ---

export const victimasApi = {
  buscar: (tipo_documento_codigo: string, numero_documento: string) =>
    api.post<VictimaResumen>('/api/victimas/buscar/', {
      tipo_documento_codigo,
      numero_documento,
    }),

  detalle: (id: string) =>
    api.get<VictimaDetalle>(`/api/victimas/${id}/`),

  registrarDesdeFuente: (data: RegistrarDesdeFuenteRequest) =>
    api.post<RegistrarDesdeFuenteResponse>('/api/victimas/registrar-desde-fuente/', data),
};

export const tiposDocumentoApi = {
  listar: () =>
    api.get<PaginatedResponse<TipoDocumento>>('/api/parametricas/tipos-documento/', {
      params: { activo: true },
    }),
};
