import apiClient from './client';

export interface ResumenEncuestador {
  sesiones_total: number;
  sesiones_completadas: number;
  sesiones_en_progreso: number;
  sesiones_suspendidas: number;
  hogares_caracterizados: number;
  respuestas_total: number;
  promedio_completado: number;
  periodo_desde: string;
  periodo_hasta: string;
}

export interface DetalleSesion {
  sesion_id: string;
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

export interface PaginatedDetalle {
  count: number;
  page: number;
  pages: number;
  results: DetalleSesion[];
}

// Rango amplio por defecto para no perder datos de meses anteriores
function desdeDefault(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 3);
  return d.toISOString().slice(0, 10);
}

export const reportesApi = {
  resumen: (params?: { desde?: string; hasta?: string }) =>
    apiClient.get<ResumenEncuestador>('/api/reportes/encuestador/', {
      params: { desde: desdeDefault(), ...params },
    }),

  detalle: (params?: { page?: number; desde?: string; hasta?: string }) =>
    apiClient.get<PaginatedDetalle>('/api/reportes/encuestador/detalle/', {
      params: { desde: desdeDefault(), ...params },
    }),

  exportarCsv: () =>
    apiClient.get('/api/reportes/encuestador/exportar/', {
      params: { formato: 'csv', desde: desdeDefault() },
      responseType: 'blob',
    }),
};
