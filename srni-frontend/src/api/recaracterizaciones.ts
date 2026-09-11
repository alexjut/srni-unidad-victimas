/**
 * Recaracterizaciones sobre ficha vigente — el punto de control.
 *
 * El 11-sep-2026 se retiró el bloqueo por ficha vigente: cualquier persona del
 * padrón se caracteriza cuando la operación lo necesite, sin autorización y sin
 * soporte. Lo único que se conservó es el DATO: el sistema anota, al cerrar cada
 * encuesta, toda caracterización hecha sobre una persona que todavía tenía ficha
 * vigente.
 *
 * Esto es la consulta de ese registro, y es la mitad que hace útil a la otra: un
 * registro que nadie mira equivale a no tenerlo.
 *
 * Solo supervisión (`administrar` o `ver_reportes`). El encuestador de campo
 * recibe 403 — un instrumento para mirar cómo opera el equipo no se le entrega al
 * equipo que se está mirando.
 */
import api from './client';

// --- Tipos ---

export interface Recaracterizacion {
  id: string;
  victima: string;
  /** El documento va HASHEADO: para contar y agrupar alcanza, y esta pantalla
   *  muestra miles de filas de datos personales de víctimas. */
  documento_hash: string;
  /** Cuántas veces se ha recaracterizado a esta persona, contando esta vez. */
  veces_esta_persona: number;
  realizada_por: string | null;
  realizada_por_codigo: string;
  realizada_por_nombre: string;
  realizada_at: string;
  ruta: string;
  ruta_display: string;
  /** La caracterización ANTERIOR, la que estaba vigente. */
  fecha_ult_caracterizacion: string | null;
  vigente_hasta: string | null;
  /**
   * Días que le FALTABAN por vencer.
   *
   * ⚠️ Contraintuitivo y decisivo: el número más ALTO es la recaracterización más
   * temprana, y por tanto la más grave. 720 significa que la ficha tenía tres días
   * de hecha; 30 significa que ya casi vencía. Ordenar al revés esconde justo el
   * caso que se busca.
   */
  dias_restantes: number | null;
  sesion: string;
  hogar: string | null;
  codigo_hogar: string;
  municipio_nombre: string;
  departamento_nombre: string;
  created_at: string;
}

export interface PersonaRecaracterizada {
  victima: string;
  documento_hash: string;
  veces: number;
  primera: string;
  ultima: string;
  /** La MAYOR anticipación de todas: el peor caso de esta persona. */
  menor_dias_restantes: number | null;
  /** Encuestadores distintos. Más de uno = nadie se enteró de lo del otro. */
  autores: number;
}

export interface ResumenRecaracterizaciones {
  total: number;
  personas_distintas: number;
  /** Mayor que 1 significa que hay personas recaracterizadas más de una vez. */
  promedio_por_persona: number;
  por_autor: Array<{ codigo_usuario: string; nombre: string; veces: number }>;
  por_territorial: Array<{ departamento: string; veces: number }>;
  por_ruta: Array<{ ruta: string; veces: number }>;
  /** Franjas de gravedad. Un promedio mezclaría «a los tres días» con «a los 22
   *  meses» hasta volver invisible el primero. */
  anticipacion: {
    hasta_7_dias: number;
    hasta_30_dias: number;
    hasta_6_meses: number;
    mas_de_6_meses: number;
    sin_dato: number;
  };
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface FiltrosRecaracterizaciones {
  fecha_desde?: string;
  fecha_hasta?: string;
  codigo_usuario?: string;
  ruta?: string;
  municipio?: string;
  departamento?: string;
  /** Solo las hechas con AL MENOS estos días de anticipación (las más graves). */
  dias_restantes_min?: number;
  documento_hash?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

/**
 * Las cuatro rutas del Manual §5.1.1. Se listan acá y no se piden al servidor
 * porque son un catálogo cerrado del instrumento, no un dato variable.
 */
export const RUTAS_ENTREVISTA = [
  { valor: 'GENERAL', etiqueta: 'General' },
  { valor: 'ACCIONES_CONSTITUCIONALES', etiqueta: 'Acciones constitucionales' },
  { valor: 'MODIFICACION_NUCLEO_FAMILIAR', etiqueta: 'Modificación de núcleo familiar' },
  { valor: 'RUTA_ESPECIAL', etiqueta: 'Ruta especial' },
] as const;

/**
 * Umbral de días restantes que separa cada franja de gravedad.
 *
 * Los dos años son 730 días, así que «le faltaban 723» es lo mismo que «la
 * caracterización anterior tenía 7 días». Se expresa en días restantes porque es
 * lo que guarda el registro, y se traduce acá para no obligar a nadie a hacer la
 * resta mentalmente.
 */
export const DIAS_DEL_PERIODO = 730;

export function antiguedadDeLaFichaEnDias(diasRestantes: number | null): number | null {
  if (diasRestantes === null || diasRestantes === undefined) return null;
  return Math.max(0, DIAS_DEL_PERIODO - diasRestantes);
}

// --- API ---

export const recaracterizacionesApi = {
  listar: (params?: FiltrosRecaracterizaciones) =>
    api.get<PaginatedResponse<Recaracterizacion>>('/api/recaracterizaciones/', { params }),

  resumen: (params?: FiltrosRecaracterizaciones) =>
    api.get<ResumenRecaracterizaciones>('/api/recaracterizaciones/resumen/', { params }),

  /** Agrupado por persona. `veces_min` por defecto 2 en el servidor. */
  personas: (params?: FiltrosRecaracterizaciones & { veces_min?: number }) =>
    api.get<PaginatedResponse<PersonaRecaracterizada>>(
      '/api/recaracterizaciones/personas/', { params }),
};
