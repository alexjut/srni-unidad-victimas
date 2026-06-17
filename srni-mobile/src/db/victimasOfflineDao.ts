/**
 * DAO para víctimas registradas OFFLINE (Fase A).
 *
 * Cuando no hay red, no se puede llamar a POST registrar-desde-fuente/, así que
 * generamos un id_local (UUID) que actúa como `autorizado` del hogar y guardamos
 * el VictimaResumenFuente COMPLETO para re-registrarlo al recuperar señal. Al
 * sincronizar, el servidor devuelve victima_id y remapeamos id_local → id_servidor
 * en el payload de CREAR_HOGAR pendiente (mismo patrón que hogares→sesiones).
 *
 * SEGURIDAD: payload_json contiene PII (es el mismo dato que ya viaja en memoria
 * en el flujo online). Cifrado en reposo: pendiente (ver docs/offline-cifrado-reposo.md).
 */
import { openDb } from './schema';
import { uuidv4 } from '../utils/uuid';
import type { VictimaResumenFuente } from '../types';

export interface VictimaOfflineRow {
  id_local: string;
  id_servidor: string | null;
  payload_json: string;
  estado_sync: 'pendiente' | 'enviando' | 'enviado' | 'error';
  created_at: string;
  updated_at: string;
}

/**
 * Crea una víctima offline a partir del VictimaResumenFuente. Devuelve el
 * id_local (UUID) que se usará como `autorizado` del hogar mientras no haya red.
 */
export async function crearVictimaOffline(
  victima: VictimaResumenFuente,
): Promise<VictimaOfflineRow> {
  const db = await openDb();
  const now = new Date().toISOString();
  const idLocal = uuidv4();

  const row: VictimaOfflineRow = {
    id_local: idLocal,
    id_servidor: null,
    payload_json: JSON.stringify(victima),
    estado_sync: 'pendiente',
    created_at: now,
    updated_at: now,
  };

  await db.runAsync(
    `INSERT INTO victimas_offline
       (id_local, id_servidor, payload_json, estado_sync, created_at, updated_at)
     VALUES (?, NULL, ?, 'pendiente', ?, ?)`,
    [row.id_local, row.payload_json, now, now],
  );

  return row;
}

export async function marcarSincronizado(
  idLocal: string,
  idServidor: string,
): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE victimas_offline SET id_servidor = ?, estado_sync = 'enviado', updated_at = ? WHERE id_local = ?",
    [idServidor, new Date().toISOString(), idLocal],
  );
}

export async function marcarError(idLocal: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE victimas_offline SET estado_sync = 'error', updated_at = ? WHERE id_local = ?",
    [new Date().toISOString(), idLocal],
  );
}
