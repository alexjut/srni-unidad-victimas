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
    // Sin red (o id de hogar local). Se juntan las dos fuentes locales:
    //  - construirMiembrosOffline: el hogar completo si se creó sin red, o SOLO
    //    los integrantes agregados sin red si el hogar ya estaba en el servidor.
    //  - la caché del servidor (poblada en el camino online).
    //
    // Antes se devolvía la primera que no viniera vacía. Con un hogar del
    // servidor y un integrante agregado sin señal, la lista offline traía solo a
    // ese integrante y ganaba: el autorizado y el resto del hogar desaparecían de
    // las preguntas por persona hasta que volviera la red.
    let locales: MiembroHogarResumen[] = [];
    let cache: MiembroHogarResumen[] = [];
    try {
      cache = (await hogaresCacheDao.obtenerMiembros(hogarId)) ?? [];
    } catch { /* sin caché */ }
    try {
      // Con caché, los integrantes que ya subieron vienen en ella con su id de
      // servidor: sumarlos otra vez con el id local los duplicaría. Sin caché,
      // lo local es lo único que hay y se usa completo.
      locales = await miembrosOfflineDao.construirMiembrosOffline(
        hogarId, { excluirEnviados: cache.length > 0 });
    } catch { /* solo la caché */ }
    return ordenarMiembros(combinarMiembros(cache, locales));
  }
}

/**
 * Caché del servidor + integrantes locales, sin repetir a nadie. Si la caché ya
 * trae un autorizado, el «autorizado» reconstruido offline sobra (es el mismo).
 */
export function combinarMiembros(
  cache: MiembroHogarResumen[],
  locales: MiembroHogarResumen[],
): MiembroHogarResumen[] {
  if (cache.length === 0) return locales;
  const ids = new Set(cache.map((m) => m.id));
  const hayAutorizado = cache.some((m) => m.es_autorizado);
  const extra = locales.filter((m) => !ids.has(m.id) && !(hayAutorizado && m.es_autorizado));
  return [...cache, ...extra];
}
