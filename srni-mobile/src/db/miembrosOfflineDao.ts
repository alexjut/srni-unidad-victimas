/**
 * DAO para integrantes del hogar agregados OFFLINE (Fase A).
 *
 * Cuando no hay red, no se puede llamar a POST hogares/{id}/agregar-miembro/.
 * Guardamos el miembro localmente vinculado al hogar por su id_local y encolamos
 * AGREGAR_MIEMBRO. Al sincronizar, tras crear el hogar en el servidor, se remapea
 * hogar_id_local → id_servidor en el payload pendiente (igual que CREAR_SESION).
 *
 * SEGURIDAD: payload_json contiene PII del integrante (nombre, documento). Es el
 * mismo dato que ya viaja en memoria en el flujo online. Cifrado en reposo:
 * pendiente (ver docs/offline-cifrado-reposo.md).
 */
import { openDb } from './schema';
import { uuidv4 } from '../utils/uuid';
import type { AgregarMiembroPayload } from '../api/hogares';

export interface MiembroOfflineRow {
  id_local: string;
  id_servidor: string | null;
  hogar_id_local: string;
  payload_json: string;
  estado_sync: 'pendiente' | 'enviando' | 'enviado' | 'error';
  created_at: string;
  updated_at: string;
}

/**
 * Guarda un integrante offline vinculado al hogar (por su id_local). Devuelve el
 * id_local del miembro generado.
 */
export async function crearMiembroOffline(
  hogarIdLocal: string,
  payload: AgregarMiembroPayload,
): Promise<MiembroOfflineRow> {
  const db = await openDb();
  const now = new Date().toISOString();
  const idLocal = uuidv4();

  const row: MiembroOfflineRow = {
    id_local: idLocal,
    id_servidor: null,
    hogar_id_local: hogarIdLocal,
    payload_json: JSON.stringify(payload),
    estado_sync: 'pendiente',
    created_at: now,
    updated_at: now,
  };

  await db.runAsync(
    `INSERT INTO miembros_offline
       (id_local, id_servidor, hogar_id_local, payload_json, estado_sync, created_at, updated_at)
     VALUES (?, NULL, ?, ?, 'pendiente', ?, ?)`,
    [row.id_local, row.hogar_id_local, row.payload_json, now, now],
  );

  return row;
}

/** Integrantes offline de un hogar (por id_local del hogar), en orden de creación. */
export async function listarPorHogar(hogarIdLocal: string): Promise<MiembroOfflineRow[]> {
  const db = await openDb();
  return db.getAllAsync<MiembroOfflineRow>(
    'SELECT * FROM miembros_offline WHERE hogar_id_local = ? ORDER BY created_at',
    [hogarIdLocal],
  );
}

export async function marcarSincronizado(
  idLocal: string,
  idServidor: string,
): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE miembros_offline SET id_servidor = ?, estado_sync = 'enviado', updated_at = ? WHERE id_local = ?",
    [idServidor, new Date().toISOString(), idLocal],
  );
}

export async function marcarError(idLocal: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE miembros_offline SET estado_sync = 'error', updated_at = ? WHERE id_local = ?",
    [new Date().toISOString(), idLocal],
  );
}
