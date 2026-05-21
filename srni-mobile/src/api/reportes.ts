import apiClient from './client';

export interface ResumenInstrumento {
  instrumento_id: string;
  instrumento_nombre: string;
  perfil_codigo: string;
  total: number;
  completadas: number;
  promedio_completado: number;
}

export interface SesionReporte {
  id: string;
  hogar_id: string;
  instrumento_nombre: string;
  perfil_codigo: string;
  estado: string;
  estado_display: string;
  porcentaje_completado: number;
  respuestas_total: number;
  fecha_inicio: string;
  fecha_fin: string | null;
  duracion_minutos: number | null;
}

export interface ProduccionResumen {
  encuestador_id: string;
  encuestador_nombre: string;
  periodo_desde: string;
  periodo_hasta: string;
  sesiones_total: number;
  sesiones_completadas: number;
  sesiones_en_progreso: number;
  sesiones_suspendidas: number;
  hogares_caracterizados: number;
  respuestas_total: number;
  promedio_completado: number;
  por_instrumento: ResumenInstrumento[];
  sesiones_recientes: SesionReporte[];
}

export interface ProduccionDetalle {
  count: number;
  page: number;
  pages: number;
  results: SesionReporte[];
}

export interface ProduccionFiltros {
  desde?: string;   // YYYY-MM-DD
  hasta?: string;   // YYYY-MM-DD
  encuestador?: string;  // UUID — solo admins
  estado?: string;
  page?: number;
}

export const reportesApi = {
  resumen: (params?: ProduccionFiltros) =>
    apiClient.get<ProduccionResumen>('/api/reportes/produccion/', { params }),

  detalle: (params?: ProduccionFiltros) =>
    apiClient.get<ProduccionDetalle>('/api/reportes/produccion/detalle/', { params }),

  exportUrl: (params?: Pick<ProduccionFiltros, 'desde' | 'hasta' | 'encuestador'>) => {
    const base = apiClient.defaults.baseURL ?? '';
    const qs = new URLSearchParams();
    if (params?.desde) qs.set('desde', params.desde);
    if (params?.hasta) qs.set('hasta', params.hasta);
    if (params?.encuestador) qs.set('encuestador', params.encuestador);
    return `${base}/api/reportes/produccion/export/?${qs.toString()}`;
  },
};
