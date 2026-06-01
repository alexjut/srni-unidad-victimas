import api from './client';

// --- Tipos ---
// Campos basados en el modelo auditoria_logacceso del backend

export interface LogAuditoria {
  id: string;
  codigo_usuario: string;
  usuario_nombre: string;
  accion: string;
  recurso: string;
  recurso_id: string;
  ip_origen: string;
  user_agent: string;
  resultado: string;
  detalle: string;
  timestamp: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- API ---

export const auditoriaApi = {
  logs: (params?: {
    accion?: string;
    fecha_desde?: string;
    fecha_hasta?: string;
    page?: number;
  }) =>
    api.get<PaginatedResponse<LogAuditoria>>('/api/auditoria/logs/', { params }),
};
