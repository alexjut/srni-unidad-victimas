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
  consultarFuente: (
    tipo_documento: string,
    numero_documento: string,
    ruta_entrevista?: string,
  ) =>
    apiClient.post<ResultadoBusquedaFuente>('/api/victimas/consultar-fuente/', {
      tipo_documento,
      numero_documento,
      // Sin ruta, el servidor aplica la GENERAL — que respeta la regla de los
      // dos años. Por eso una persona con ficha vigente salía "no habilitada"
      // sin salida posible: la app nunca le decía por qué ruta iba a
      // caracterizarla. Con una de las tres rutas de excepción del Manual
      // §5.1.1, la misma consulta devuelve ELEGIBLE_POR_EXCEPCION.
      ...(ruta_entrevista ? { ruta_entrevista } : {}),
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
