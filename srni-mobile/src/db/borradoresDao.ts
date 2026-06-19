/**
 * DAO para borradores de encuesta y sus respuestas en SQLite.
 *
 * Un borrador es una sesión de encuesta aún no finalizada / no sincronizada.
 * Cuando se sincroniza con el servidor, se actualiza sesion_id con el UUID
 * devuelto por el backend.
 *
 * Sprint 7: instrumento_id y pregunta_id son ahora UUID strings.
 */
import { openDb } from './schema';
import { uuidv4 } from '../utils/uuid';

export interface BorradorRow {
  id: string;
  hogar_id: string | null;
  sesion_id: string | null;
  instrumento_id: string | null;  // UUID de InstrumentoVersion
  estado: string;
  created_at: string;
  updated_at: string;
}

export interface RespuestaRow {
  id: number;
  borrador_id: string;
  pregunta_id: string;       // UUID de Pregunta
  miembro_id: string | null; // Sprint 21: null para preguntas HOGAR, UUID de MiembroHogar para PERSONA
  valor: string;
  updated_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────

export async function crearBorrador(
  instrumentoId: string,  // UUID de InstrumentoVersion
  hogarId?: string,
): Promise<BorradorRow> {
  const db = await openDb();
  const now = new Date().toISOString();
  const id = uuidv4();
  await db.runAsync(
    `INSERT INTO borradores (id, hogar_id, sesion_id, instrumento_id, estado, created_at, updated_at)
     VALUES (?, ?, NULL, ?, 'EN_PROGRESO', ?, ?)`,
    [id, hogarId ?? null, instrumentoId, now, now],
  );
  return { id, hogar_id: hogarId ?? null, sesion_id: null, instrumento_id: instrumentoId, estado: 'EN_PROGRESO', created_at: now, updated_at: now };
}

export async function getBorrador(id: string): Promise<BorradorRow | null> {
  const db = await openDb();
  return db.getFirstAsync<BorradorRow>('SELECT * FROM borradores WHERE id = ?', [id]);
}

export async function listarBorradores(): Promise<BorradorRow[]> {
  const db = await openDb();
  return db.getAllAsync<BorradorRow>(
    "SELECT * FROM borradores WHERE estado != 'SINCRONIZADO' ORDER BY updated_at DESC",
  );
}

/**
 * Guarda o actualiza una respuesta (upsert).
 *
 * Sprint 21 — `miembroId` es:
 *   - null/undefined si la pregunta es nivel HOGAR (1 respuesta por sesión)
 *   - UUID del miembro si la pregunta es nivel PERSONA (N respuestas, una por miembro)
 *
 * El unique index (borrador_id, pregunta_id, miembro_id) garantiza no duplicar.
 * SQLite trata NULL como distinto en UNIQUE, así que el ON CONFLICT funciona
 * tanto para HOGAR (miembro_id=NULL) como para PERSONA (miembro_id=<uuid>).
 */
export async function upsertRespuesta(
  borradorId: string,
  preguntaId: string,
  valor: string,
  miembroId?: string | null,
): Promise<void> {
  const db = await openDb();
  const now = new Date().toISOString();
  const mid = miembroId ?? null;
  await db.runAsync(
    `INSERT INTO respuestas (borrador_id, pregunta_id, miembro_id, valor, updated_at)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(borrador_id, pregunta_id, miembro_id)
     DO UPDATE SET valor = excluded.valor, updated_at = excluded.updated_at`,
    [borradorId, preguntaId, mid, valor, now],
  );
  await db.runAsync('UPDATE borradores SET updated_at = ? WHERE id = ?', [now, borradorId]);
}

export async function getRespuestas(borradorId: string): Promise<RespuestaRow[]> {
  const db = await openDb();
  return db.getAllAsync<RespuestaRow>(
    'SELECT * FROM respuestas WHERE borrador_id = ?',
    [borradorId],
  );
}

/**
 * Devuelve mapa pregunta_id → valor. Solo respuestas tipo HOGAR (miembro_id null).
 * Mantiene compatibilidad con el motor pre-Sprint 21.
 */
export async function getRespuestaMap(borradorId: string): Promise<Record<string, string>> {
  const rows = await getRespuestas(borradorId);
  const map: Record<string, string> = {};
  for (const r of rows) {
    if (r.miembro_id == null) map[r.pregunta_id] = r.valor;
  }
  return map;
}

/**
 * Sprint 21 — devuelve mapa con clave compuesta `pregunta_id|miembro_id` o
 * `pregunta_id|` para HOGAR. Permite al motor restaurar borradores con
 * preguntas PERSONA por miembro.
 *
 * Ejemplo:
 *   { "p-uuid|" : "valor HOGAR",
 *     "p-uuid|m1-uuid" : "valor para miembro 1",
 *     "p-uuid|m2-uuid" : "valor para miembro 2" }
 */
export function claveRespuesta(preguntaId: string, miembroId?: string | null): string {
  return `${preguntaId}|${miembroId ?? ''}`;
}

export async function getRespuestaMapCompuesto(
  borradorId: string,
): Promise<Record<string, string>> {
  const rows = await getRespuestas(borradorId);
  const map: Record<string, string> = {};
  for (const r of rows) {
    map[claveRespuesta(r.pregunta_id, r.miembro_id)] = r.valor;
  }
  return map;
}

export async function marcarSincronizado(
  borradorId: string,
  sesionIdServidor: string,
): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE borradores SET sesion_id = ?, estado = 'SINCRONIZADO', updated_at = ? WHERE id = ?",
    [sesionIdServidor, new Date().toISOString(), borradorId],
  );
}

export async function marcarCompletado(borradorId: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE borradores SET estado = 'COMPLETADO', updated_at = ? WHERE id = ?",
    [new Date().toISOString(), borradorId],
  );
}

export async function vincularSesionServidor(borradorId: string, sesionId: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    'UPDATE borradores SET sesion_id = ?, updated_at = ? WHERE id = ?',
    [sesionId, new Date().toISOString(), borradorId],
  );
}

/** Busca un borrador local vinculado a una sesión del servidor. */
export async function findBySesionId(sesionId: string): Promise<BorradorRow | null> {
  const db = await openDb();
  return db.getFirstAsync<BorradorRow>(
    'SELECT * FROM borradores WHERE sesion_id = ?',
    [sesionId],
  );
}

/**
 * Busca el borrador OFFLINE (aún sin sesion_id de servidor) de un hogar +
 * instrumento. Sirve para que el flujo offline gire sobre UN ÚNICO borrador:
 * la lista de capítulos lo resuelve una sola vez y se lo pasa a cada capítulo.
 *
 * Se restringe a `sesion_id IS NULL` para no colisionar con borradores ya
 * sincronizados/vinculados a una sesión (camino online). Si hay varios
 * (no debería), devuelve el más reciente.
 */
export async function findBorradorOfflinePorHogarInstrumento(
  hogarId: string,
  instrumentoId: string,
): Promise<BorradorRow | null> {
  const db = await openDb();
  return db.getFirstAsync<BorradorRow>(
    `SELECT * FROM borradores
       WHERE sesion_id IS NULL AND hogar_id = ? AND instrumento_id = ?
       ORDER BY updated_at DESC
       LIMIT 1`,
    [hogarId, instrumentoId],
  );
}

/**
 * Cuenta respuestas no vacías por capítulo para un borrador dado.
 * Sprint 18: las preguntas viven en memoria (no SQLite), así que el JOIN
 * lo hacemos en JS usando el cache de instrumentos.
 */
export async function contarRespuestasPorCapitulo(
  borradorId: string,
): Promise<Record<string, number>> {
  const { getCapituloIdDePregunta } = await import('../services/instrumentos');
  const db = await openDb();
  const rows = await db.getAllAsync<{ pregunta_id: string }>(
    `SELECT pregunta_id FROM respuestas WHERE borrador_id = ? AND valor != ''`,
    [borradorId],
  );
  const map: Record<string, number> = {};
  for (const r of rows) {
    const capId = getCapituloIdDePregunta(r.pregunta_id);
    if (capId) {
      map[capId] = (map[capId] ?? 0) + 1;
    }
  }
  return map;
}
