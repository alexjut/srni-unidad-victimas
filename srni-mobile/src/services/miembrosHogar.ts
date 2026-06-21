/**
 * Resolución tolerante a red de la lista de miembros de un hogar.
 *
 * Unifica el patrón que antes estaba duplicado en formulario/index.tsx y
 * formulario/[temaId].tsx, y agrega el fallback a caché que arregla #4/#38
 * (hogar creado ONLINE que dejaba de ser capturable al caer la red).
 *
 * Orden de resolución:
 *   1. ONLINE — GET hogares/{id}/. Se cachea (IDs del servidor) para offline.
 *   2. OFFLINE, hogar creado sin red (id local) — construirMiembrosOffline.
 *   3. OFFLINE, hogar creado ONLINE (id de servidor, red caída) — la caché
 *      poblada en (1). Sin esto las preguntas PERSONA no se podían capturar.
 */
import { hogaresApi } from '../api/hogares';
import * as miembrosOfflineDao from '../db/miembrosOfflineDao';
import * as hogaresCacheDao from '../db/hogaresCacheDao';
import type { MiembroHogarResumen } from '../types';

/** Ordena la lista dejando al autorizado primero. */
export function ordenarMiembros(ms: MiembroHogarResumen[]): MiembroHogarResumen[] {
  return [...ms].sort((a, b) => {
    if (a.es_autorizado && !b.es_autorizado) return -1;
    if (!a.es_autorizado && b.es_autorizado) return 1;
    return 0;
  });
}

export async function cargarMiembrosHogar(
  hogarId: string,
): Promise<MiembroHogarResumen[]> {
  try {
    const { data } = await hogaresApi.detalle(hogarId);
    const ms = ordenarMiembros((data.miembros ?? []) as MiembroHogarResumen[]);
    // Cachear solo si hay miembros: nunca pisar una caché válida con [].
    if (ms.length > 0) {
      try { await hogaresCacheDao.guardarMiembros(hogarId, ms); }
      catch { /* caché best-effort */ }
    }
    return ms;
  } catch {
    // Sin red (o id de hogar local). Primero los creados offline, luego la caché.
    try {
      const locales = await miembrosOfflineDao.construirMiembrosOffline(hogarId);
      if (locales.length > 0) return ordenarMiembros(locales);
    } catch { /* sigue a la caché */ }
    try {
      const cache = await hogaresCacheDao.obtenerMiembros(hogarId);
      if (cache && cache.length > 0) return ordenarMiembros(cache);
    } catch { /* sin caché */ }
    return [];
  }
}
