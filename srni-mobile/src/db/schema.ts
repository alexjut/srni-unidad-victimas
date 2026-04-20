/**
 * Schema SQLite local — SRNI offline.
 *
 * REGLA IRROMPIBLE: NUNCA almacenar PII (nombre, documento, fecha nacimiento)
 * en el dispositivo. Solo UUIDs opacos y datos de vivienda/formulario.
 *
 * Versiones:
 *  0 → schema inicial (Sprint 3): temas, preguntas, opciones, derivadas, borradores, respuestas, sync_log
 *  1 → Sprint 4: instrumento_meta, hogares_offline, cola_sincronizacion + índices
 */
import * as SQLite from 'expo-sqlite';

export const DB_NAME = 'srni_offline.db';
const SCHEMA_VERSION = 1;

// ─── DDL base (idempotente) ───────────────────────────────────────────────────
const DDL_V0 = `
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;

  CREATE TABLE IF NOT EXISTS temas (
    id          INTEGER PRIMARY KEY,
    codigo      TEXT    NOT NULL,
    nombre      TEXT    NOT NULL,
    orden       INTEGER NOT NULL DEFAULT 0,
    activo      INTEGER NOT NULL DEFAULT 1
  );

  CREATE TABLE IF NOT EXISTS preguntas (
    id              INTEGER PRIMARY KEY,
    tema_id         INTEGER NOT NULL REFERENCES temas(id),
    codigo          TEXT    NOT NULL,
    texto           TEXT    NOT NULL,
    texto_ayuda     TEXT    NOT NULL DEFAULT '',
    tipo_respuesta  TEXT    NOT NULL DEFAULT 'OPCION_UNICA',
    orden           INTEGER NOT NULL DEFAULT 0,
    requerida       INTEGER NOT NULL DEFAULT 1,
    activa          INTEGER NOT NULL DEFAULT 1,
    validacion      TEXT    NOT NULL DEFAULT '{}'
  );

  CREATE TABLE IF NOT EXISTS opciones_respuesta (
    id          INTEGER PRIMARY KEY,
    pregunta_id INTEGER NOT NULL REFERENCES preguntas(id),
    codigo      TEXT    NOT NULL,
    texto       TEXT    NOT NULL,
    orden       INTEGER NOT NULL DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS preguntas_derivadas (
    id                  INTEGER PRIMARY KEY,
    pregunta_padre_id   INTEGER NOT NULL REFERENCES preguntas(id),
    pregunta_hija_id    INTEGER NOT NULL REFERENCES preguntas(id),
    operador            TEXT    NOT NULL DEFAULT 'EQ',
    valor_condicion     TEXT    NOT NULL DEFAULT ''
  );

  CREATE TABLE IF NOT EXISTS borradores (
    id              TEXT    PRIMARY KEY,
    hogar_id        TEXT,
    sesion_id       TEXT,
    instrumento_id  INTEGER,
    estado          TEXT    NOT NULL DEFAULT 'EN_PROGRESO',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
  );

  CREATE TABLE IF NOT EXISTS respuestas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    borrador_id TEXT    NOT NULL REFERENCES borradores(id),
    pregunta_id INTEGER NOT NULL REFERENCES preguntas(id),
    valor       TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT    NOT NULL
  );

  CREATE UNIQUE INDEX IF NOT EXISTS idx_respuestas_unique
    ON respuestas(borrador_id, pregunta_id);

  CREATE TABLE IF NOT EXISTS sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    borrador_id TEXT    NOT NULL,
    intentado   TEXT    NOT NULL,
    resultado   TEXT    NOT NULL,
    detalle     TEXT    NOT NULL DEFAULT ''
  );
`;

// ─── Migración v1 ─────────────────────────────────────────────────────────────
const MIGRATION_V1 = `
  CREATE TABLE IF NOT EXISTS instrumento_meta (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    instrumento_id  INTEGER NOT NULL,
    version         TEXT    NOT NULL DEFAULT '0',
    descargado_en   TEXT    NOT NULL
  );

  CREATE TABLE IF NOT EXISTS hogares_offline (
    id_local            TEXT    PRIMARY KEY,
    id_servidor         TEXT,
    jefe_hogar_uuid     TEXT    NOT NULL,
    municipio_id        INTEGER,
    tipo_vivienda       TEXT    NOT NULL DEFAULT '',
    condicion_ocupacion TEXT    NOT NULL DEFAULT '',
    estrato             INTEGER NOT NULL DEFAULT 0,
    numero_cuartos      INTEGER NOT NULL DEFAULT 0,
    numero_personas     INTEGER NOT NULL DEFAULT 1,
    observaciones       TEXT    NOT NULL DEFAULT '',
    estado_sync         TEXT    NOT NULL DEFAULT 'pendiente',
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL
  );

  CREATE TABLE IF NOT EXISTS cola_sincronizacion (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo             TEXT    NOT NULL,
    recurso_local_id TEXT    NOT NULL,
    payload          TEXT    NOT NULL DEFAULT '{}',
    estado           TEXT    NOT NULL DEFAULT 'pendiente',
    intentos         INTEGER NOT NULL DEFAULT 0,
    ultimo_error     TEXT    NOT NULL DEFAULT '',
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_cola_estado ON cola_sincronizacion(estado, id);
  CREATE INDEX IF NOT EXISTS idx_hogares_sync ON hogares_offline(estado_sync);
`;

// ─────────────────────────────────────────────────────────────────────────────

export async function initDatabase(): Promise<SQLite.SQLiteDatabase> {
  const db = await SQLite.openDatabaseAsync(DB_NAME);

  const row = await db.getFirstAsync<{ user_version: number }>('PRAGMA user_version');
  const currentVersion = row?.user_version ?? 0;

  await db.execAsync(DDL_V0);

  if (currentVersion < 1) {
    await db.execAsync(MIGRATION_V1);
    await db.execAsync(`PRAGMA user_version = ${SCHEMA_VERSION}`);
  }

  return db;
}

/** Abre la BD sin re-inicializar. Para uso en DAOs/servicios. */
export async function openDb(): Promise<SQLite.SQLiteDatabase> {
  return SQLite.openDatabaseAsync(DB_NAME);
}
