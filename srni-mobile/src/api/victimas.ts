import apiClient from './client';
import type {
  ResultadoBusquedaFuente,
  VictimaResumenFuente,
} from '../types';

export const victimasApi = {
  /**
   * Busca a la persona en el repositorio externo (RUV / Oracle / Mock).
   * No modifica ni consulta la DB local Django.
   * POST /api/victimas/consultar-fuente/
   */
  consultarFuente: (tipo_documento: string, numero_documento: string) =>
    apiClient.post<ResultadoBusquedaFuente>('/api/victimas/consultar-fuente/', {
      tipo_documento,
      numero_documento,
    }),

  /**
   * Crea o actualiza la Victima en la DB local Django a partir de los datos
   * del repositorio. Retorna el UUID local para usar en hogaresApi.crear().
   * POST /api/victimas/registrar-desde-fuente/
   */
  registrarDesdeFuente: (victima: VictimaResumenFuente) =>
    apiClient.post<{ victima_id: string; created: boolean }>(
      '/api/victimas/registrar-desde-fuente/',
      victima,
    ),

  /**
   * Retorna el grupo familiar desde el repositorio externo.
   * GET /api/victimas/grupo-familiar/{cons_persona}/
   */
  grupoFamiliar: (cons_persona: number) =>
    apiClient.get<VictimaResumenFuente[]>(
      `/api/victimas/grupo-familiar/${cons_persona}/`,
    ),
};
