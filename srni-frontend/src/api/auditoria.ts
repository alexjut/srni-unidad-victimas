import api from './client';

// --- Tipos ---

export interface LogAuditoria {
  id: string;
  codigo_usuario: string;
  usuario_nombre: string;
  accion: string;
  accion_display: string;
  recurso: string;
  recurso_id: string;
  ip_origen: string;
  resultado: string;
  resultado_display: string;
  detalle: Record<string, unknown> | null;
  timestamp: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Acciones disponibles en el backend
export const ACCIONES_AUDITORIA = [
  'LOGIN', 'LOGOUT', 'LOGIN_FALLIDO', 'BUSQUEDA_RNI', 'VER_VICTIMA',
  'CREAR_HOGAR', 'AGREGAR_MIEMBRO', 'RESPONDER_PREGUNTA', 'FINALIZAR_ENCUESTA',
  'EXPORTAR', 'CAMBIO_PASSWORD', 'CAMBIO_USUARIO', 'ACCESO_DENEGADO',
  'LLAMADA_GEMINI', 'CONSENTIMIENTO_IA',
] as const;

// --- API ---

export const auditoriaApi = {
  logs: (params?: {
    accion?: string;
    resultado?: string;
    codigo_usuario?: string;
    fecha_desde?: string;
    fecha_hasta?: string;
    search?: string;
    ordering?: string;
    page?: number;
    page_size?: number;
  }) =>
    api.get<PaginatedResponse<LogAuditoria>>('/api/auditoria/logs/', { params }),
};
