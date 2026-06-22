/**
 * Caché local de la lista de miembros de un hogar del SERVIDOR (fix #4/#38).
 *
 * Un hogar conformado ONLINE no deja rastro en hogares_offline/miembros_offline.
 * Si la red cae a mitad de la caracterización, construirMiembrosOffline no
 * encuentra nada y las preguntas PERSONA dejan de poderse capturar. Esta caché
 * espeja la respuesta de GET hogares/{id}/ (miembros con sus IDs de SERVIDOR)
 * cada vez que se carga online, para releerla sin red manteniendo los mismos
 * IDs → las respuestas (clave pregunta_id|miembro_id) quedan consistentes.
 *
 * SEGURIDAD: miembros_json contiene PII (nombre, fecha de nacimiento), el mismo
 * dato que ya guarda miembros_offline.payload_json. Cifrado en reposo pendiente
 * para Fase 1 (#21). Ver schema.ts MIGRATION_V9.
 */
import { openDb } from './schema';
import type { MiembroHogarResumen } from '../types';

interface HogarCacheRow {
  hogar_id: string;
  miembros_json: string;
  actualizado: string;
}

/** Persiste (upsert) la lista de miembros del hogar tal como la devolvió el servidor. */
export async function guardarMiembros(
  hogarId: string,
  miembros: MiembroHogarResumen[],
): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    `INSERT INTO hogares_cache (hogar_id, miembros_json, actualizado)
       VALUES (?, ?, ?)
     ON CONFLICT(hogar_id) DO UPDATE SET
       miembros_json = excluded.miembros_json,
       actualizado   = excluded.actualizado`,
    [hogarId, JSON.stringify(miembros), new Date().toISOString()],
  );
}

/** Devuelve los miembros cacheados de un hogar, o null si no hay caché. */
export async function obtenerMiembros(
  hogarId: string,
): Promise<MiembroHogarResumen[] | null> {
  const db = await openDb();
  const row = await db.getFirstAsync<HogarCacheRow>(
    'SELECT * FROM hogares_cache WHERE hogar_id = ?',
    [hogarId],
  );
  if (!row) return null;
  try {
    const parsed = JSON.parse(row.miembros_json);
    return Array.isArray(parsed) ? (parsed as MiembroHogarResumen[]) : null;
  } catch {
    return null;
  }
}

/** Borra la caché de un hogar (p.ej. al purgarlo de la lista). */
export async function eliminar(hogarId: string): Promise<void> {
  const db = await openDb();
  await db.runAsync('DELETE FROM hogares_cache WHERE hogar_id = ?', [hogarId]);
}
