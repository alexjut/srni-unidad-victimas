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
  pregunta_id: string;  // UUID de Pregunta
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
 * pregunta_id es UUID de Pregunta.
 */
export async function upsertRespuesta(
  borradorId: string,
  preguntaId: string,  // UUID
  valor: string,
): Promise<void> {
  const db = await openDb();
  const now = new Date().toISOString();
  await db.runAsync(
    `INSERT INTO respuestas (borrador_id, pregunta_id, valor, updated_at)
     VALUES (?, ?, ?, ?)
     ON CONFLICT(borrador_id, pregunta_id) DO UPDATE SET valor = excluded.valor, updated_at = excluded.updated_at`,
    [borradorId, preguntaId, valor, now],
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

/** Devuelve mapa pregunta_id (UUID) → valor. */
export async function getRespuestaMap(borradorId: string): Promise<Record<string, string>> {
  const rows = await getRespuestas(borradorId);
  const map: Record<string, string> = {};
  for (const r of rows) map[r.pregunta_id] = r.valor;
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
