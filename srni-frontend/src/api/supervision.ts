import api from './client';

// --- Tipos ---

export interface EncuestadorMetrica {
  id: string;
  codigo_usuario: string;
  nombre_completo: string;
  perfil_codigo: string;
  sesiones_total: number;
  sesiones_completadas: number;
  sesiones_en_progreso: number;
  sesiones_suspendidas: number;
  hogares_caracterizados: number;
  promedio_completado: number;
  ultima_actividad: string | null;
}

export interface SupervisorResponse {
  periodo_desde: string;
  periodo_hasta: string;
  encuestadores_activos: number;
  totales: {
    sesiones_total: number;
    sesiones_completadas: number;
    sesiones_en_progreso: number;
    sesiones_suspendidas: number;
    hogares_caracterizados: number;
    promedio_completado: number;
  };
  encuestadores: EncuestadorMetrica[];
}

export interface SerieDiaria {
  fecha: string;
  sesiones_iniciadas: number;
  sesiones_completadas: number;
}

export interface DistribucionInstrumento {
  instrumento_codigo: string;
  instrumento_nombre: string;
  total: number;
}

export interface DashboardSeriesResponse {
  periodo_desde: string;
  periodo_hasta: string;
  serie_diaria: SerieDiaria[];
  distribucion_por_instrumento: DistribucionInstrumento[];
}

// --- API ---

export const supervisionApi = {
  resumen: (params?: { desde?: string; hasta?: string }) =>
    api.get<SupervisorResponse>('/api/reportes/supervisor/', { params }),

  series: (params?: { desde?: string; hasta?: string }) =>
    api.get<DashboardSeriesResponse>('/api/reportes/dashboard/series/', { params }),
};
