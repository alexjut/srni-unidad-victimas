import apiClient from './client';

export interface ResumenEncuestador {
  sesiones_total: number;
  sesiones_finalizadas: number;
  sesiones_en_proceso: number;
  hogares_total: number;
  victimas_caracterizadas: number;
  periodo_inicio: string | null;
  periodo_fin: string | null;
}

export interface DetalleSesion {
  sesion_id: string;
  hogar_codigo: string;
  instrumento: string;
  ruta_entrevista: string;
  estado: string;
  porcentaje_completado: number;
  municipio: string | null;
  fecha_inicio: string;
  fecha_fin: string | null;
}

export interface PaginatedDetalle {
  count: number;
  next: string | null;
  previous: string | null;
  results: DetalleSesion[];
}

export const reportesApi = {
  resumen: () =>
    apiClient.get<ResumenEncuestador>('/api/reportes/encuestador/'),

  detalle: (params?: { page?: number }) =>
    apiClient.get<PaginatedDetalle>('/api/reportes/encuestador/detalle/', { params }),

  exportarCsv: () =>
    apiClient.get('/api/reportes/encuestador/exportar/', {
      params: { formato: 'csv' },
      responseType: 'blob',
    }),
};
