/**
 * DAO para borradores de encuesta y sus respuestas en SQLite.
 *
 * Un borrador es una sesión de encuesta aún no finalizada / no sincronizada.
 * Cuando se sincroniza con el servidor, se actualiza sesion_id con el UUID
 * devuelto por el backend.
 */
import { openDb } from './schema';
import { uuidv4 } from '../utils/uuid';

export interface BorradorRow {
  id: string;
  hogar_id: string | null;
  sesion_id: string | null;
  instrumento_id: number | null;
  estado: string;
  created_at: string;
  updated_at: string;
}

export interface RespuestaRow {
  id: number;
  borrador_id: string;
  pregunta_id: number;
  valor: string;
  updated_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────

export async function crearBorrador(
  instrumentoId: number,
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
 * Si la sesión ya está sincronizada la respuesta se marca para envío individual.
 */
export async function upsertRespuesta(
  borradorId: string,
  preguntaId: number,
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
  // Actualizar timestamp del borrador
  await db.runAsync('UPDATE borradores SET updated_at = ? WHERE id = ?', [now, borradorId]);
}

export async function getRespuestas(borradorId: string): Promise<RespuestaRow[]> {
  const db = await openDb();
  return db.getAllAsync<RespuestaRow>(
    'SELECT * FROM respuestas WHERE borrador_id = ?',
    [borradorId],
  );
}

export async function getRespuestaMap(borradorId: string): Promise<Record<number, string>> {
  const rows = await getRespuestas(borradorId);
  const map: Record<number, string> = {};
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
