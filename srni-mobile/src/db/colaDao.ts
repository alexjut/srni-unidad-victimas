/**
 * DAO para la cola de sincronización.
 *
 * Tipos de operación en orden de precedencia:
 *   1. CREAR_HOGAR       — debe ir primero; las sesiones dependen del hogar_id servidor
 *   2. CREAR_SESION      — depende de hogar_id servidor
 *   3. RESPONDER_PREGUNTA — depende de sesion_id servidor
 *   4. FINALIZAR_SESION  — debe ir al final
 *
 * Estados: pendiente → enviando → enviado
 *                                ↘ error (tras MAX_INTENTOS fallos)
 *
 * Los items en estado 'enviando' que queden de una sesión crasheada se
 * liberan con resetearBloqueados() al iniciar la app.
 */
import { openDb } from './schema';

export type TipoOperacion =
  | 'CREAR_HOGAR'
  | 'CREAR_SESION'
  | 'RESPONDER_PREGUNTA'
  | 'FINALIZAR_SESION';

export type EstadoCola = 'pendiente' | 'enviando' | 'enviado' | 'error';

export interface ColaItem {
  id: number;
  tipo: TipoOperacion;
  recurso_local_id: string;
  payload: string;          // JSON serializado
  estado: EstadoCola;
  intentos: number;
  ultimo_error: string;
  created_at: string;
  updated_at: string;
}

const MAX_INTENTOS = 3;

// Orden de procesamiento por tipo
const ORDEN_TIPO: Record<TipoOperacion, number> = {
  CREAR_HOGAR: 1,
  CREAR_SESION: 2,
  RESPONDER_PREGUNTA: 3,
  FINALIZAR_SESION: 4,
};

// ─────────────────────────────────────────────────────────────────────────────

export async function encolar(
  tipo: TipoOperacion,
  recursoLocalId: string,
  payload: object,
): Promise<number> {
  const db = await openDb();
  const now = new Date().toISOString();
  const result = await db.runAsync(
    `INSERT INTO cola_sincronizacion
       (tipo, recurso_local_id, payload, estado, intentos, ultimo_error, created_at, updated_at)
     VALUES (?, ?, ?, 'pendiente', 0, '', ?, ?)`,
    [tipo, recursoLocalId, JSON.stringify(payload), now, now],
  );
  return result.lastInsertRowId;
}

/**
 * Devuelve items pendientes ordenados por tipo (CREAR_HOGAR primero)
 * y por id (FIFO dentro del mismo tipo).
 */
export async function obtenerPendientes(): Promise<ColaItem[]> {
  const db = await openDb();
  const rows = await db.getAllAsync<ColaItem>(
    "SELECT * FROM cola_sincronizacion WHERE estado = 'pendiente' ORDER BY id",
  );
  // Ordenar por precedencia de tipo, luego por id
  return rows.sort((a, b) => {
    const diff = (ORDEN_TIPO[a.tipo] ?? 99) - (ORDEN_TIPO[b.tipo] ?? 99);
    return diff !== 0 ? diff : a.id - b.id;
  });
}

export async function contarPendientes(): Promise<number> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ n: number }>(
    "SELECT COUNT(*) AS n FROM cola_sincronizacion WHERE estado IN ('pendiente', 'error')",
  );
  return row?.n ?? 0;
}

export async function contarErrores(): Promise<number> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ n: number }>(
    "SELECT COUNT(*) AS n FROM cola_sincronizacion WHERE estado = 'error'",
  );
  return row?.n ?? 0;
}

export async function marcarEnviando(id: number): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE cola_sincronizacion SET estado = 'enviando', updated_at = ? WHERE id = ?",
    [new Date().toISOString(), id],
  );
}

export async function marcarEnviado(id: number): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE cola_sincronizacion SET estado = 'enviado', updated_at = ? WHERE id = ?",
    [new Date().toISOString(), id],
  );
}

export async function marcarError(id: number, mensaje: string): Promise<void> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ intentos: number }>(
    'SELECT intentos FROM cola_sincronizacion WHERE id = ?',
    [id],
  );
  const intentos = (row?.intentos ?? 0) + 1;
  const nuevoEstado: EstadoCola = intentos >= MAX_INTENTOS ? 'error' : 'pendiente';
  await db.runAsync(
    `UPDATE cola_sincronizacion
     SET estado = ?, intentos = ?, ultimo_error = ?, updated_at = ?
     WHERE id = ?`,
    [nuevoEstado, intentos, mensaje.slice(0, 500), new Date().toISOString(), id],
  );
}

/**
 * Libera items que quedaron en 'enviando' de una sesión anterior crasheada.
 * Se llama al iniciar la app, antes de cualquier sincronización.
 */
export async function resetearBloqueados(): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE cola_sincronizacion SET estado = 'pendiente', updated_at = ? WHERE estado = 'enviando'",
    [new Date().toISOString()],
  );
}

export async function limpiarEnviados(): Promise<void> {
  const db = await openDb();
  await db.runAsync("DELETE FROM cola_sincronizacion WHERE estado = 'enviado'");
}
