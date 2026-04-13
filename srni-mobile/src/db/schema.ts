/**
 * Schema SQLite local para modo offline.
 * Solo almacena el instrumento (temas + preguntas) y borradores de encuesta.
 * NUNCA almacena PII de víctimas en el dispositivo (lección del APK original).
 */
import * as SQLite from 'expo-sqlite';

export const DB_NAME = 'srni_offline.db';

export async function initDatabase(): Promise<SQLite.SQLiteDatabase> {
  const db = await SQLite.openDatabaseAsync(DB_NAME);

  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;

    -- Instrumento de caracterización (temas y preguntas, sin PII)
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

    -- Borradores de encuesta (solo IDs y respuestas, sin PII)
    CREATE TABLE IF NOT EXISTS borradores (
      id              TEXT    PRIMARY KEY,  -- UUID local
      hogar_id        TEXT,                 -- UUID del hogar en el servidor (si ya se sincronizó)
      instrumento_id  INTEGER,
      estado          TEXT    NOT NULL DEFAULT 'EN_PROGRESO',
      created_at      TEXT    NOT NULL,
      updated_at      TEXT    NOT NULL
    );

    CREATE TABLE IF NOT EXISTS respuestas (
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      borrador_id     TEXT    NOT NULL REFERENCES borradores(id),
      pregunta_id     INTEGER NOT NULL REFERENCES preguntas(id),
      valor           TEXT    NOT NULL DEFAULT '',
      created_at      TEXT    NOT NULL
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_respuestas_unique
      ON respuestas(borrador_id, pregunta_id);

    -- Metadatos de sincronización
    CREATE TABLE IF NOT EXISTS sync_log (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      borrador_id TEXT    NOT NULL,
      intentado   TEXT    NOT NULL,
      resultado   TEXT    NOT NULL,
      detalle     TEXT    NOT NULL DEFAULT ''
    );
  `);

  return db;
}
