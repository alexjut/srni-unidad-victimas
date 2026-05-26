/**
 * Schema SQLite local — SRNI offline.
 *
 * REGLA IRROMPIBLE: NUNCA almacenar PII (nombre, documento, fecha nacimiento)
 * en el dispositivo. Solo UUIDs opacos y datos de vivienda/formulario.
 *
 * Versiones:
 *  0 → schema inicial (Sprint 3): temas, preguntas, opciones, derivadas, borradores, respuestas, sync_log
 *  1 → Sprint 4: instrumento_meta, hogares_offline, cola_sincronizacion + índices
 *  2 → Sprint 7: tablas de instrumento migradas a UUID (capitulos, reglas_skip_logic)
 *               borradores.instrumento_id TEXT, respuestas.pregunta_id TEXT
 *  3 → Sprint 9: cola_sincronizacion.retry_after TEXT (backoff exponencial)
 */
import * as SQLite from 'expo-sqlite';

export const DB_NAME = 'srni_offline.db';
const SCHEMA_VERSION = 5;

// ─── DDL base (idempotente) ───────────────────────────────────────────────────
// Sprint 18 Fase F: las tablas del INSTRUMENTO ya no se crean aquí. Los
// instrumentos viven en memoria (bundle JSON). DDL_V0 solo crea las tablas
// de DATOS CAPTURADOS (borradores, respuestas, sync_log). Las tablas de
// instrumentos viejas se eliminan en MIGRATION_V4 para usuarios existentes.
//
// NO se incluyen FOREIGN KEYS hacia tablas de instrumento — solo entre
// respuestas y borradores (ambas vivas).
const DDL_V0 = `
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;
  PRAGMA busy_timeout = 5000;

  CREATE TABLE IF NOT EXISTS borradores (
    id              TEXT    PRIMARY KEY,
    hogar_id        TEXT,
    sesion_id       TEXT,
    instrumento_id  TEXT,
    estado          TEXT    NOT NULL DEFAULT 'EN_PROGRESO',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
  );

  CREATE TABLE IF NOT EXISTS respuestas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    borrador_id TEXT    NOT NULL REFERENCES borradores(id),
    pregunta_id TEXT    NOT NULL,
    miembro_id  TEXT,
    valor       TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT    NOT NULL
  );

  -- Sprint 21: unique por (borrador, pregunta, miembro). SQLite trata NULL
  -- como distinto en UNIQUE → preguntas HOGAR (miembro=NULL) admiten 1 sola;
  -- PERSONA (miembro=ID) admiten N (una por miembro del hogar).
  CREATE UNIQUE INDEX IF NOT EXISTS idx_respuestas_unique
    ON respuestas(borrador_id, pregunta_id, miembro_id);

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

// ─── Migración v2 — tablas del instrumento con UUIDs ─────────────────────────
const MIGRATION_V2 = `
  PRAGMA foreign_keys = OFF;

  DROP TABLE IF EXISTS preguntas_derivadas;
  DROP TABLE IF EXISTS opciones_respuesta;
  DROP TABLE IF EXISTS preguntas;
  DROP TABLE IF EXISTS temas;
  DROP TABLE IF EXISTS respuestas;
  DROP TABLE IF EXISTS borradores;
  DROP TABLE IF EXISTS instrumento_meta;

  CREATE TABLE IF NOT EXISTS capitulos (
    id      TEXT    PRIMARY KEY,
    codigo  TEXT    NOT NULL,
    nombre  TEXT    NOT NULL,
    orden   INTEGER NOT NULL DEFAULT 0,
    nivel   TEXT    NOT NULL DEFAULT 'HOGAR',
    activo  INTEGER NOT NULL DEFAULT 1
  );

  CREATE TABLE IF NOT EXISTS preguntas (
    id                TEXT    PRIMARY KEY,
    capitulo_id       TEXT    NOT NULL REFERENCES capitulos(id),
    codigo_externo    TEXT    NOT NULL,
    no_pregunta       TEXT    NOT NULL DEFAULT '',
    texto             TEXT    NOT NULL,
    descripcion_ayuda TEXT    NOT NULL DEFAULT '',
    tipo              TEXT    NOT NULL DEFAULT 'TEXTO',
    nivel             TEXT    NOT NULL DEFAULT 'HOGAR',
    orden             INTEGER NOT NULL DEFAULT 0,
    obligatoria       INTEGER NOT NULL DEFAULT 1,
    activa            INTEGER NOT NULL DEFAULT 1,
    validaciones      TEXT    NOT NULL DEFAULT '{}'
  );

  CREATE INDEX IF NOT EXISTS idx_preguntas_capitulo ON preguntas(capitulo_id, orden);
  CREATE INDEX IF NOT EXISTS idx_preguntas_codigo   ON preguntas(codigo_externo);

  CREATE TABLE IF NOT EXISTS opciones_respuesta (
    id                TEXT    PRIMARY KEY,
    pregunta_id       TEXT    NOT NULL REFERENCES preguntas(id),
    valor             TEXT    NOT NULL,
    etiqueta          TEXT    NOT NULL,
    orden             INTEGER NOT NULL DEFAULT 0,
    finaliza_capitulo INTEGER NOT NULL DEFAULT 0
  );

  CREATE INDEX IF NOT EXISTS idx_opciones_pregunta ON opciones_respuesta(pregunta_id, orden);

  CREATE TABLE IF NOT EXISTS reglas_skip_logic (
    id                      TEXT    PRIMARY KEY,
    instrumento_id          TEXT    NOT NULL,
    pregunta_origen_codigo  TEXT,
    valor_trigger           TEXT    NOT NULL DEFAULT '',
    expresion_origen        TEXT    NOT NULL DEFAULT '',
    pregunta_afectada_id    TEXT    REFERENCES preguntas(id),
    pregunta_afectada_codigo TEXT,
    capitulo_afectado_id    TEXT    REFERENCES capitulos(id),
    accion                  TEXT    NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_reglas_instrumento ON reglas_skip_logic(instrumento_id);
  CREATE INDEX IF NOT EXISTS idx_reglas_afectada    ON reglas_skip_logic(pregunta_afectada_id);

  CREATE TABLE IF NOT EXISTS instrumento_meta (
    id             INTEGER PRIMARY KEY DEFAULT 1,
    instrumento_id TEXT    NOT NULL DEFAULT '',
    perfil_codigo  TEXT    NOT NULL DEFAULT '',
    version        TEXT    NOT NULL DEFAULT '0',
    descargado_en  TEXT    NOT NULL
  );

  CREATE TABLE IF NOT EXISTS borradores (
    id              TEXT    PRIMARY KEY,
    hogar_id        TEXT,
    sesion_id       TEXT,
    instrumento_id  TEXT,
    estado          TEXT    NOT NULL DEFAULT 'EN_PROGRESO',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
  );

  CREATE TABLE IF NOT EXISTS respuestas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    borrador_id TEXT    NOT NULL REFERENCES borradores(id),
    pregunta_id TEXT    NOT NULL,
    valor       TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT    NOT NULL
  );

  CREATE UNIQUE INDEX IF NOT EXISTS idx_respuestas_unique
    ON respuestas(borrador_id, pregunta_id);

  PRAGMA foreign_keys = ON;
`;

// ─── Migración v4 — DROP tablas de instrumento (Sprint 18 Fase F) ────────────
// Los instrumentos viven en memoria desde el bundle. Las tablas viejas en
// SQLite están vacías (post F1B) y solo ocupan espacio. Se eliminan limpiamente.
// IMPORTANTE: NO se tocan respuestas, cola_sincronizacion, borradores,
// hogares_offline — eso es trabajo del usuario que NO se debe perder.
const MIGRATION_V4 = `
  DROP TABLE IF EXISTS reglas_skip_logic;
  DROP TABLE IF EXISTS opciones_respuesta;
  DROP TABLE IF EXISTS preguntas;
  DROP TABLE IF EXISTS capitulos;
  DROP TABLE IF EXISTS temas;
  DROP TABLE IF EXISTS preguntas_derivadas;
  DROP TABLE IF EXISTS instrumento_meta;
`;

// ─── Migración v5 — respuestas.miembro_id (Sprint 21) ────────────────────────
// Agrega columna miembro_id a respuestas + recrea el unique index para incluirla.
// SQLite no soporta ALTER COLUMN para cambiar unique, así que dropeamos el
// index viejo y creamos uno nuevo.
const MIGRATION_V5 = `
  ALTER TABLE respuestas ADD COLUMN miembro_id TEXT;
  DROP INDEX IF EXISTS idx_respuestas_unique;
  CREATE UNIQUE INDEX idx_respuestas_unique
    ON respuestas(borrador_id, pregunta_id, miembro_id);
`;

// ─────────────────────────────────────────────────────────────────────────────
// SINGLETON DE CONEXIÓN — evita race conditions al abrir la BD múltiples
// veces desde DAOs concurrentes (Sprint 17 fix).
// ─────────────────────────────────────────────────────────────────────────────

let _dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;
let _initialized = false;

async function _abrirConexion(): Promise<SQLite.SQLiteDatabase> {
  if (!_dbPromise) {
    _dbPromise = (async () => {
      const db = await SQLite.openDatabaseAsync(DB_NAME);
      // Sprint 18 fix: busy_timeout hace que SQLite espere hasta 5s antes
      // de fallar con 'database is locked' en lugar de fallar inmediato.
      // Resuelve race conditions entre transacción de instrumento + escrituras
      // simultáneas de cola/borradores/respuestas.
      try {
        await db.execAsync('PRAGMA busy_timeout = 5000');
      } catch { /* idempotente */ }
      return db;
    })();
  }
  return _dbPromise;
}

export async function initDatabase(): Promise<SQLite.SQLiteDatabase> {
  const db = await _abrirConexion();

  if (_initialized) {
    return db;
  }

  const row = await db.getFirstAsync<{ user_version: number }>('PRAGMA user_version');
  const currentVersion = row?.user_version ?? 0;

  await db.execAsync(DDL_V0);

  if (currentVersion < 1) {
    await db.execAsync(MIGRATION_V1);
  }

  if (currentVersion < 2) {
    await db.execAsync(MIGRATION_V2);
  }

  if (currentVersion < 3) {
    await db.execAsync(
      'ALTER TABLE cola_sincronizacion ADD COLUMN retry_after TEXT',
    );
  }

  if (currentVersion < 4) {
    // Sprint 18 Fase F: drop tablas de instrumento (vacias post F1B).
    // Idempotente — usa DROP IF EXISTS. No toca borradores/respuestas/cola/hogares_offline.
    await db.execAsync(MIGRATION_V4);
  }

  if (currentVersion < 5) {
    // Sprint 21: respuestas.miembro_id para soportar preguntas PERSONA por miembro.
    try {
      await db.execAsync(MIGRATION_V5);
    } catch (e: any) {
      // ALTER TABLE ADD COLUMN no es idempotente en SQLite si la columna ya existe.
      // En ese caso, solo recreamos el index.
      if (!/duplicate column/i.test(String(e?.message ?? e))) throw e;
      await db.execAsync(`
        DROP INDEX IF EXISTS idx_respuestas_unique;
        CREATE UNIQUE INDEX idx_respuestas_unique
          ON respuestas(borrador_id, pregunta_id, miembro_id);
      `);
    }
  }

  if (currentVersion < SCHEMA_VERSION) {
    await db.execAsync(`PRAGMA user_version = ${SCHEMA_VERSION}`);
  }

  _initialized = true;
  return db;
}

/**
 * Abre la BD reutilizando la conexión singleton.
 * IMPORTANTE: si initDatabase aún no terminó, espera a que termine antes de
 * retornar — evita NPE en prepareAsync por usar la BD antes de tener tablas.
 */
export async function openDb(): Promise<SQLite.SQLiteDatabase> {
  if (!_initialized) {
    return initDatabase();
  }
  return _abrirConexion();
}
