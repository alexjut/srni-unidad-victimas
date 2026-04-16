import apiClient from './client';
import type {
  HogarResumen, HogarDetalle,
  MiembroHogarResumen, PaginatedResponse,
} from '../types';

export interface CrearHogarPayload {
  jefe_hogar: string;         // UUID de la Victima
  municipio?: number;
  tipo_vivienda?: string;
  condicion_ocupacion?: string;
  estrato?: number;
  numero_cuartos?: number;
  numero_personas?: number;
  observaciones?: string;
}

export interface AgregarMiembroPayload {
  victima?: string;           // UUID si está en el RNI
  nombre_completo?: string;   // Si NO está en el RNI
  tipo_documento?: number;
  numero_documento?: string;
  parentesco: string;
  genero?: string;
  edad?: number;
  discapacidad?: boolean;
  tipo_discapacidad?: string;
}

export const hogaresApi = {
  listar: (params?: { estado?: string; page?: number }) =>
    apiClient.get<PaginatedResponse<HogarResumen>>('/api/hogares/', { params }),

  detalle: (id: string) =>
    apiClient.get<HogarDetalle>(`/api/hogares/${id}/`),

  crear: (payload: CrearHogarPayload) =>
    apiClient.post<HogarDetalle>('/api/hogares/', payload),

  actualizar: (id: string, payload: Partial<CrearHogarPayload>) =>
    apiClient.patch<HogarDetalle>(`/api/hogares/${id}/`, payload),

  agregarMiembro: (hogarId: string, payload: AgregarMiembroPayload) =>
    apiClient.post<MiembroHogarResumen>(
      `/api/hogares/${hogarId}/agregar-miembro/`,
      payload,
    ),

  listarMiembros: (hogarId: string) =>
    apiClient.get<MiembroHogarResumen[]>(`/api/hogares/${hogarId}/miembros/`),
};
