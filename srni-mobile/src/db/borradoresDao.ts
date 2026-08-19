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

/**
 * Borradores vivos, del más reciente al más viejo.
 *
 * Excluye COMPLETADO y NO 'SINCRONIZADO', que es lo que hacía antes. Ese estado
 * no quiere decir «ya subió todo»: lo pone `marcarSincronizado` apenas la cola
 * logra CREAR la sesión en el servidor, con las respuestas todavía en cola. Con
 * el filtro viejo, una entrevista con sesión creada y respuestas sin subir
 * desaparecía de la lista, y sin red tampoco tenía tarjeta de servidor: quedaba
 * invisible por los dos lados. COMPLETADO sí es el cierre real (lo escribe
 * `marcarCompletado` cuando el FINALIZAR llegó al servidor).
 */
export async function listarBorradores(): Promise<BorradorRow[]> {
  const db = await openDb();
  return db.getAllAsync<BorradorRow>(
    "SELECT * FROM borradores WHERE estado != 'COMPLETADO' ORDER BY updated_at DESC",
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

/**
 * Remapea el miembro_id local → id de servidor en las respuestas ya guardadas.
 * Lo usa la sincronización tras crear el hogar/miembro en el servidor: las
 * respuestas PERSONA capturadas offline quedan ligadas al id de MiembroHogar real,
 * para que un guardado posterior (online) no envíe un miembro_id que el backend
 * rechazaría con 400.
 */
export async function remapMiembro(idLocal: string, idServidor: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    'UPDATE respuestas SET miembro_id = ? WHERE miembro_id = ?',
    [idServidor, idLocal],
  );
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
 * Busca EL borrador de un hogar + instrumento. El flujo offline gira sobre uno
 * solo: la lista de capítulos lo resuelve una vez y se lo pasa a cada capítulo.
 *
 * Antes esto filtraba por `sesion_id IS NULL` para «no colisionar con el camino
 * online», y ese filtro perdía trabajo. En cuanto la cola crea la sesión en el
 * servidor, `marcarSincronizado` le pone el `sesion_id` al borrador — o sea que
 * el borrador de la entrevista de ayer deja de cumplir la condición. Al volver
 * a entrar por ese mismo hogar sin red, esta función no lo encontraba y el
 * formulario creaba uno EN BLANCO: todos los capítulos en 0/N, con las
 * respuestas viejas todavía en el `.db` pero colgando del otro borrador. Y al
 * sincronizar quedaban dos filas con el mismo `sesion_id` —el backend responde
 * con la misma sesión, es idempotente—, así que `findBySesionId` (que usa
 * `getFirstAsync`) devolvía una cualquiera de las dos y la mitad de la
 * entrevista dejaba de verse.
 *
 * Ahora el criterio es el que corresponde: el borrador vivo de ese hogar e
 * instrumento, esté vinculado o no. Solo se excluye COMPLETADO, que es el que
 * ya se cerró contra el servidor y `purgarSincronizados` va a borrar.
 * Si hay varios (no debería), devuelve el más reciente.
 */
export async function findBorradorOfflinePorHogarInstrumento(
  hogarId: string,
  instrumentoId: string,
): Promise<BorradorRow | null> {
  const db = await openDb();
  return db.getFirstAsync<BorradorRow>(
    `SELECT * FROM borradores
       WHERE hogar_id = ? AND instrumento_id = ? AND estado != 'COMPLETADO'
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
