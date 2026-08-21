/**
 * Excepciones de vigencia — autorizar la actualización de una ficha vigente.
 *
 * Una persona caracterizada hace menos de dos años no se puede recaracterizar.
 * El Manual §5.1.1 autoriza tres rutas a omitir esa regla con un soporte —fallo,
 * tutela, auto—, y desde el 14-ago-2026 esa autorización se otorga acá: el
 * caracterizador no debe tener ese documento, le llega por canal institucional a
 * quien coordina.
 *
 * El celular solo consume el resultado: lo ve en la búsqueda o en la precarga de
 * la jornada, y la habilitación se consume al finalizar la encuesta.
 */
import apiClient from './client';

export const RUTAS_EXCEPCION = [
  { value: 'ACCIONES_CONSTITUCIONALES', label: 'Acciones constitucionales — fallo, tutela o auto' },
  { value: 'MODIFICACION_NUCLEO',       label: 'Modificación del núcleo familiar' },
  { value: 'ESPECIAL',                  label: 'Ruta especial' },
];

export const ESTADOS_HABILITACION = [
  { value: 'VIGENTE', label: 'Vigentes' },
  { value: 'USADA',   label: 'Usadas' },
  { value: 'ANULADA', label: 'Anuladas' },
];

export interface Habilitacion {
  id: string;
  victima: string;
  victima_documento: string;
  victima_nombre: string;
  ruta: string;
  ruta_display: string;
  radicado: string;
  observacion: string;
  estado: 'VIGENTE' | 'USADA' | 'ANULADA';
  estado_display: string;
  fecha_ult_caracterizacion: string | null;
  vigente_hasta: string | null;
  soporte_nombre: string;
  autorizada_por_codigo: string;
  created_at: string;
  usada_at: string | null;
  anulada_at: string | null;
  motivo_anulacion: string;
}

/** Una persona encontrada por documento, con su situación actual. */
export interface PersonaBuscada {
  /**
   * El id de la ficha en el padrón. Es `null` cuando la persona viene del corte
   * del RUV y todavía no tiene ficha: ahí manda `universo_id`, y la ficha se
   * crea al autorizar.
   */
  id: string | null;
  universo_id: string | null;
  /** De dónde salió la fila. `UNIVERSO` = está en el RUV, sin ficha todavía. */
  origen: 'PADRON' | 'UNIVERSO';
  nombre: string;
  tipo_documento: string;
  numero_documento: string;
  fecha_nacimiento: string | null;
  estado_ruv: string;
  motivo: string;
  mensaje: string;
  ficha_vigente_hasta: string | null;
  /** true = tiene ficha vigente y se le puede autorizar la excepción. */
  requiere_excepcion: boolean;
  habilitacion_vigente: Habilitacion | null;
  /**
   * Se encontró por número, pero el tipo de documento registrado es otro (o no
   * tiene). Hay que verificar la identidad antes de autorizar: 1,04 M de
   * víctimas están cargadas sin tipo.
   */
  coincide_solo_por_numero?: boolean;
}

export interface ResultadoBusqueda {
  total: number;
  resultados: PersonaBuscada[];
  /** Documentos que no están en el padrón — hay que mostrarlos, no callarlos. */
  sin_coincidencia: string[];
}

export interface ResultadoLote {
  autorizadas: Habilitacion[];
  omitidas: Array<{
    victima_id?: string; universo_id?: string; motivo: string; detail?: string;
  }>;
  total_autorizadas: number;
  total_omitidas: number;
}

export const habilitacionesApi = {
  /** Uno o muchos documentos: un fallo suele amparar a un hogar entero. */
  buscar: (tipo_documento: string, documentos: string[]) =>
    apiClient.post<ResultadoBusqueda>('/api/habilitaciones/buscar/', {
      tipo_documento, documentos,
    }),

  listar: (estado?: string) =>
    apiClient.get<Habilitacion[] | { results: Habilitacion[] }>(
      '/api/habilitaciones/', { params: estado ? { estado } : {} }),

  /**
   * Autoriza sobre una o varias personas con el mismo soporte.
   *
   * Siempre por `lote/`, aunque sea una sola: un único camino evita que el caso
   * de "una" y el de "varias" se comporten distinto el día que algo cambie.
   * Va como multipart porque puede llevar el archivo adjunto.
   */
  autorizar: (datos: {
    victima_ids: string[];
    /** Los del corte del RUV, que todavía no tienen ficha en el padrón. */
    universo_ids?: string[];
    ruta: string;
    radicado: string;
    observacion: string;
    soporte?: File | null;
  }) => {
    const fd = new FormData();
    datos.victima_ids.forEach((id) => fd.append('victima_ids', id));
    (datos.universo_ids ?? []).forEach((id) => fd.append('universo_ids', id));
    fd.append('ruta', datos.ruta);
    fd.append('radicado', datos.radicado);
    fd.append('observacion', datos.observacion);
    if (datos.soporte) fd.append('soporte', datos.soporte);
    return apiClient.post<ResultadoLote>('/api/habilitaciones/lote/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  anular: (id: string, motivo: string) =>
    apiClient.post<Habilitacion>(`/api/habilitaciones/${id}/anular/`, { motivo }),
};
