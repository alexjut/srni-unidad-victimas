/**
 * DAO para la cola de sincronización.
 *
 * Tipos de operación en orden de precedencia:
 *   0. REGISTRAR_VICTIMA  — Fase A: registra la víctima autorizada; el hogar depende de su UUID servidor
 *   1. CREAR_HOGAR        — depende del autorizado (víctima); las sesiones/miembros dependen del hogar_id servidor
 *   2. AGREGAR_MIEMBRO    — Fase A: integrante del hogar; depende del hogar_id servidor
 *   3. CREAR_SESION       — depende de hogar_id servidor
 *   4. RESPONDER_BULK     — bulk de N respuestas de un capítulo (reemplaza RESPONDER_PREGUNTA individual)
 *   5. RESPONDER_PREGUNTA — legado; se migra a bulk en el procesador
 *   6. FINALIZAR_SESION   — debe ir al final
 *
 * Estados: pendiente → enviando → enviado
 *                                ↘ error (tras MAX_INTENTOS fallos)
 *
 * Backoff exponencial:
 *   intento 1 → retry_after = now + 30 s
 *   intento 2 → retry_after = now + 2 min
 *   intento 3 → estado = 'error' definitivo (requiere acción del usuario)
 *
 * Los items en estado 'enviando' que queden de una sesión crasheada se
 * liberan con resetearBloqueados() al iniciar la app.
 */
import { openDb } from './schema';

export type TipoOperacion =
  | 'REGISTRAR_VICTIMA'
  | 'CREAR_HOGAR'
  | 'AGREGAR_MIEMBRO'
  | 'CREAR_SESION'
  | 'RESPONDER_BULK'
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
  retry_after: string | null;
  created_at: string;
  updated_at: string;
}

const MAX_INTENTOS = 6;

// Delays de backoff en segundos por intento (1→30s ... 5→30min). El intento 6
// agota y pasa a 'error'. Una jornada offline larga necesita reintentos amplios.
// (Los errores de red/infra ya NO consumen intentos — se difieren con reencolar.)
const BACKOFF_SEGUNDOS = [30, 120, 300, 900, 1800];

// Orden de procesamiento por tipo
const ORDEN_TIPO: Record<TipoOperacion, number> = {
  REGISTRAR_VICTIMA:  0,
  CREAR_HOGAR:        1,
  AGREGAR_MIEMBRO:    2,
  CREAR_SESION:       3,
  RESPONDER_BULK:     4,
  RESPONDER_PREGUNTA: 4,
  FINALIZAR_SESION:   5,
};

// ─────────────────────────────────────────────────────────────────────────────

export async function encolar(
  tipo: TipoOperacion,
  recursoLocalId: string,
  payload: object,
): Promise<number> {
  const db = await openDb();
  const now = new Date().toISOString();

  // Dedup de RESPONDER_PREGUNTA: una sola fila pendiente/errada por
  // (recurso, pregunta, miembro). Editar una respuesta N veces NO debe inflar la
  // cola ni dejar valores viejos que pisen el bulk al reintentar. Se borra la
  // fila previa antes de insertar la nueva (último valor gana).
  if (tipo === 'RESPONDER_PREGUNTA') {
    const p = payload as { pregunta_id?: string; miembro_id?: string | null };
    await db.runAsync(
      `DELETE FROM cola_sincronizacion
         WHERE tipo = 'RESPONDER_PREGUNTA' AND estado IN ('pendiente', 'error')
           AND recurso_local_id = ?
           AND json_extract(payload, '$.pregunta_id') = ?
           AND IFNULL(json_extract(payload, '$.miembro_id'), '') = IFNULL(?, '')`,
      [recursoLocalId, p.pregunta_id ?? '', p.miembro_id ?? null],
    );
  }

  const result = await db.runAsync(
    `INSERT INTO cola_sincronizacion
       (tipo, recurso_local_id, payload, estado, intentos, ultimo_error, retry_after, created_at, updated_at)
     VALUES (?, ?, ?, 'pendiente', 0, '', NULL, ?, ?)`,
    [tipo, recursoLocalId, JSON.stringify(payload), now, now],
  );
  return result.lastInsertRowId;
}

/**
 * Devuelve items pendientes cuyo retry_after ya venció (o no tienen).
 * Ordenados por tipo (CREAR_HOGAR primero) y por id (FIFO dentro del mismo tipo).
 */
export async function obtenerPendientes(): Promise<ColaItem[]> {
  const db = await openDb();
  const rows = await db.getAllAsync<ColaItem>(
    `SELECT * FROM cola_sincronizacion
     WHERE estado = 'pendiente'
       AND (retry_after IS NULL OR retry_after <= datetime('now'))
     ORDER BY id`,
  );
  return rows.sort((a, b) => {
    const diff = (ORDEN_TIPO[a.tipo] ?? 99) - (ORDEN_TIPO[b.tipo] ?? 99);
    return diff !== 0 ? diff : a.id - b.id;
  });
}

export async function obtenerTodos(): Promise<ColaItem[]> {
  const db = await openDb();
  return db.getAllAsync<ColaItem>(
    `SELECT * FROM cola_sincronizacion
     WHERE estado != 'enviado'
     ORDER BY
       CASE estado WHEN 'error' THEN 0 WHEN 'pendiente' THEN 1 ELSE 2 END,
       id DESC`,
  );
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
    "UPDATE cola_sincronizacion SET estado = 'enviado', retry_after = NULL, updated_at = ? WHERE id = ?",
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

  if (intentos >= MAX_INTENTOS) {
    await db.runAsync(
      `UPDATE cola_sincronizacion
       SET estado = 'error', intentos = ?, ultimo_error = ?, retry_after = NULL, updated_at = ?
       WHERE id = ?`,
      [intentos, mensaje.slice(0, 500), new Date().toISOString(), id],
    );
  } else {
    const delaySeg = BACKOFF_SEGUNDOS[intentos - 1] ?? 30;
    const retryAfter = new Date(Date.now() + delaySeg * 1000).toISOString();
    await db.runAsync(
      `UPDATE cola_sincronizacion
       SET estado = 'pendiente', intentos = ?, ultimo_error = ?, retry_after = ?, updated_at = ?
       WHERE id = ?`,
      [intentos, mensaje.slice(0, 500), retryAfter, new Date().toISOString(), id],
    );
  }
}

/**
 * Devuelve un item a 'pendiente' SIN penalizar (no incrementa intentos ni fija
 * backoff). Lo usa la sincronización cuando un item espera a que se procese su
 * dependencia (p.ej. RESPONDER_BULK antes de CREAR_SESION). Así un item diferido
 * no agota sus 3 intentos ni traba la cadena en 'error' permanente.
 */
export async function reencolar(id: number): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE cola_sincronizacion SET estado = 'pendiente', retry_after = NULL, updated_at = ? WHERE id = ?",
    [new Date().toISOString(), id],
  );
}

/**
 * Resetea items en estado 'error' a 'pendiente' para reintentar manualmente.
 */
export async function reintentarErrores(): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    `UPDATE cola_sincronizacion
     SET estado = 'pendiente', intentos = 0, retry_after = NULL, updated_at = ?
     WHERE estado = 'error'`,
    [new Date().toISOString()],
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
