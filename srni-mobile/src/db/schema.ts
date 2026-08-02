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
 *  6 → Fase 0 Offline: padron, jornada, parametricas_cache, meta_offline
 *  7 → Fase A Offline: victimas_offline, miembros_offline (conformación 100% offline)
 *  8 → hogares_offline.ultimo_error TEXT (motivo del fallo de sincronización)
 *  9 → hogares_cache: espejo de la lista de miembros del servidor para que un
 *      hogar creado ONLINE siga capturable si cae la red (fix #4/#38)
 * 10 → padron sin PRIMARY KEY en documento_hash + clase_colision: un mismo
 *      documento puede pertenecer a dos personas distintas y las dos tienen que
 *      caber (antes la segunda se perdía en silencio)
 * 11 → jornada con el mismo arreglo + cons_persona: traía el defecto gemelo y
 *      pisaba la persona que el encuestador acababa de elegir
 */
import * as SQLite from 'expo-sqlite';

export const DB_NAME = 'srni_offline.db';
const SCHEMA_VERSION = 11;

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

// ─── Migración v6 — almacén OFFLINE de precarga (Fase 0) ─────────────────────
// Tablas para trabajar offline desde el login:
//   - padron: índice ligero de personas (documento HASHEADO, sin PII fuerte).
//             Se busca por documento_hash; documento_display = últimos 4 dígitos.
//   - jornada: VictimaResumenFuente COMPLETO por documento (json) para continuar
//              el flujo offline cuando la persona viene en la jornada del día.
//   - parametricas_cache: municipios / DT / puntos serializados como json por tipo.
//   - meta_offline: clave/valor para guardar la "version" del padrón y timestamps.
//
// TODO(cifrado-en-reposo): Fase 0 NO cifra. Para una fase posterior con PII real
// se debe migrar a SQLCipher (expo-sqlite con `enableChangeListener` + libsql/
// op-sqlite, o expo-sqlite-storage cifrado) y derivar la llave desde SecureStore.
// El padron ya guarda el documento HASHEADO (no reversible) como mitigación parcial.
const MIGRATION_V6 = `
  CREATE TABLE IF NOT EXISTS padron (
    documento_hash    TEXT    PRIMARY KEY,
    tipo_documento    TEXT    NOT NULL DEFAULT '',
    documento_display TEXT    NOT NULL DEFAULT '',
    nombre            TEXT    NOT NULL DEFAULT '',
    ubicacion         TEXT    NOT NULL DEFAULT '',
    cantidad_hechos   INTEGER NOT NULL DEFAULT 0,
    en_ruv            INTEGER NOT NULL DEFAULT 0,
    habilitada        INTEGER NOT NULL DEFAULT 0,
    ya_caracterizada  INTEGER NOT NULL DEFAULT 0,
    cons_persona      INTEGER
  );

  CREATE INDEX IF NOT EXISTS idx_padron_hash ON padron(documento_hash);

  CREATE TABLE IF NOT EXISTS jornada (
    documento_hash TEXT PRIMARY KEY,
    json           TEXT NOT NULL DEFAULT '{}'
  );

  CREATE TABLE IF NOT EXISTS parametricas_cache (
    tipo TEXT PRIMARY KEY,
    json TEXT NOT NULL DEFAULT '[]'
  );

  CREATE TABLE IF NOT EXISTS meta_offline (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL DEFAULT ''
  );
`;

// ─── Migración v7 — conformación 100% OFFLINE (Fase A) ───────────────────────
// Permite registrar víctima + conformar hogar + agregar miembros SIN red, igual
// que hogares_offline ya hace para el hogar. Cada fila lleva id_local (UUID),
// id_servidor (NULL hasta sincronizar) y estado_sync.
//
//   - victimas_offline: la víctima "autorizada" registrada offline. Guarda el
//       VictimaResumenFuente COMPLETO en `payload_json` para re-registrarlo en el
//       servidor al recuperar red (POST registrar-desde-fuente). El id_local es
//       el UUID que se usa como `autorizado` del hogar mientras no haya red.
//   - miembros_offline: integrantes agregados al hogar sin red. hogar_id_local
//       apunta al hogar (id_local) y se remapea a id_servidor al sincronizar.
//
// SEGURIDAD: payload_json SÍ contiene PII (nombre, documento) de la persona —
// es el mismo dato que ya viaja en memoria por el flujo online. Queda pendiente
// el cifrado en reposo (ver docs/offline-cifrado-reposo.md y TODO en MIGRATION_V6).
const MIGRATION_V7 = `
  CREATE TABLE IF NOT EXISTS victimas_offline (
    id_local      TEXT    PRIMARY KEY,
    id_servidor   TEXT,
    payload_json  TEXT    NOT NULL DEFAULT '{}',
    estado_sync   TEXT    NOT NULL DEFAULT 'pendiente',
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
  );

  CREATE TABLE IF NOT EXISTS miembros_offline (
    id_local         TEXT    PRIMARY KEY,
    id_servidor      TEXT,
    hogar_id_local   TEXT    NOT NULL,
    payload_json     TEXT    NOT NULL DEFAULT '{}',
    estado_sync      TEXT    NOT NULL DEFAULT 'pendiente',
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_victimas_off_sync ON victimas_offline(estado_sync);
  CREATE INDEX IF NOT EXISTS idx_miembros_off_hogar ON miembros_offline(hogar_id_local);
`;

// ─── Migración v9 — caché de miembros de hogares creados ONLINE (fix #4/#38) ──
// Un hogar conformado ONLINE vive en el servidor, no en hogares_offline/
// miembros_offline. Si la red cae a mitad de captura, construirMiembrosOffline
// no encuentra nada y las preguntas PERSONA dejan de poderse capturar.
// Esta tabla espeja la respuesta de GET hogares/{id}/ (la lista de miembros con
// sus IDs de SERVIDOR) cada vez que se carga online, para releerla sin red. Al
// usar los mismos IDs del servidor, las respuestas (clave pregunta_id|miembro_id)
// quedan consistentes entre el camino online y el offline.
//
// SEGURIDAD: miembros_json contiene PII (nombre, fecha de nacimiento) — el mismo
// dato que ya guarda miembros_offline.payload_json y que viaja en memoria en el
// flujo online. Cifrado en reposo (SQLCipher) sigue pendiente para Fase 1 (#21).
const MIGRATION_V9 = `
  CREATE TABLE IF NOT EXISTS hogares_cache (
    hogar_id      TEXT    PRIMARY KEY,
    miembros_json TEXT    NOT NULL DEFAULT '[]',
    actualizado   TEXT    NOT NULL
  );
`;

// ─── Migración v10 — un documento puede ser de más de una persona ────────────
//
// `documento_hash` era PRIMARY KEY, o sea: una fila por documento. Sonaba obvio y
// era falso. En el padrón real hay 768.096 documentos compartidos por más de un
// registro, y de esos, ~7 % son PERSONAS DISTINTAS: dos víctimas con el mismo
// número. Con la PK, la segunda no entraba —el `INSERT OR REPLACE` de la
// precarga pisaba a la primera— y en campo, sin señal, esa persona simplemente
// no existía. Extrapolado al padrón completo, ~53 mil personas.
//
// Ahora el documento puede repetirse y `clase_colision` dice qué hay detrás:
//   NULL               → documento limpio, una persona. El 92 % restante ya viene
//                        resuelto desde el servidor (una fila por persona).
//   'AMBIGUO'          → varias personas lo comparten: hay que PREGUNTAR.
//   'NO_IDENTIFICANTE' → valor de relleno ('99', '0'): no identifica a nadie y la
//                        fila viene vacía a propósito.
//
// La tabla se MIGRA, no se borra. La versión anterior hacía `DROP TABLE padron`
// dando por hecho que la precarga la repuebla — y no es así: `ejecutarPrecarga`
// solo se dispara en `login` y `loginBiometrico`, no al restaurar una sesión ya
// abierta. Un encuestador que actualiza la app y sale a campo con la sesión
// puesta se quedaba SIN padrón y sin forma de recuperarlo hasta volver a
// entrar con red. Las columnas viejas son un subconjunto exacto de las nuevas y
// `clase_colision` NULL significa justo lo que la v9 asumía de todas: documento
// limpio, una persona.
const MIGRATION_V10 = `
  ALTER TABLE padron RENAME TO padron_v9;

  CREATE TABLE padron (
    documento_hash    TEXT    NOT NULL,
    tipo_documento    TEXT    NOT NULL DEFAULT '',
    documento_display TEXT    NOT NULL DEFAULT '',
    nombre            TEXT    NOT NULL DEFAULT '',
    ubicacion         TEXT    NOT NULL DEFAULT '',
    cantidad_hechos   INTEGER NOT NULL DEFAULT 0,
    en_ruv            INTEGER NOT NULL DEFAULT 0,
    habilitada        INTEGER NOT NULL DEFAULT 0,
    ya_caracterizada  INTEGER NOT NULL DEFAULT 0,
    cons_persona      INTEGER,
    clase_colision    TEXT
  );

  INSERT INTO padron
    (documento_hash, tipo_documento, documento_display, nombre, ubicacion,
     cantidad_hechos, en_ruv, habilitada, ya_caracterizada, cons_persona,
     clase_colision)
  SELECT documento_hash, tipo_documento, documento_display, nombre, ubicacion,
         cantidad_hechos, en_ruv, habilitada, ya_caracterizada, cons_persona,
         NULL
    FROM padron_v9;

  DROP TABLE padron_v9;

  CREATE INDEX IF NOT EXISTS idx_padron_hash ON padron(documento_hash);
`;

// ─── Migración v11 — la jornada tampoco es "una fila por documento" ──────────
//
// `jornada` arrastraba el mismo defecto que el padrón: `documento_hash TEXT
// PRIMARY KEY` + `INSERT OR REPLACE`, sobre EXACTAMENTE la misma lista de
// víctimas que llega en la precarga. De dos personas que comparten documento
// sobrevivía la última, y como `resultadoDesdePadron` le da prioridad a la
// jornada, esa fila pisaba la elección que el encuestador acababa de hacer entre
// los candidatos: elegía a MARIA y veía los datos de ROSA.
//
// `cons_persona` permite quedarse con la fila de la persona elegida y no con
// cualquiera de las que comparten el número.
const MIGRATION_V11 = `
  DROP TABLE IF EXISTS jornada;

  CREATE TABLE jornada (
    documento_hash TEXT    NOT NULL,
    cons_persona   INTEGER,
    json           TEXT    NOT NULL DEFAULT '{}'
  );

  CREATE INDEX IF NOT EXISTS idx_jornada_hash ON jornada(documento_hash);
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

  if (currentVersion < 6) {
    // Fase 0: tablas del almacén offline de precarga. Idempotente (IF NOT EXISTS).
    await db.execAsync(MIGRATION_V6);
  }

  if (currentVersion < 7) {
    // Fase A: víctimas y miembros offline para conformación 100% sin red.
    // Idempotente (IF NOT EXISTS).
    await db.execAsync(MIGRATION_V7);
  }

  if (currentVersion < 8) {
    // hogares_offline.ultimo_error: guarda el motivo del fallo de sincronización.
    // ALTER TABLE ADD COLUMN no es idempotente en SQLite si la columna ya existe.
    try {
      await db.execAsync(
        "ALTER TABLE hogares_offline ADD COLUMN ultimo_error TEXT NOT NULL DEFAULT ''",
      );
    } catch (e: any) {
      if (!/duplicate column/i.test(String(e?.message ?? e))) throw e;
    }
  }

  if (currentVersion < 9) {
    // Fix #4/#38: caché de miembros de hogares creados online. Idempotente.
    await db.execAsync(MIGRATION_V9);
  }

  if (currentVersion < 10) {
    // El padrón deja de tener UNA fila por documento (ver MIGRATION_V10).
    // Migra los datos existentes: la precarga NO se dispara al restaurar sesión,
    // así que borrarlos dejaría al encuestador sin padrón en pleno campo.
    await db.execAsync(MIGRATION_V10);
  }

  if (currentVersion < 11) {
    // La jornada, con el mismo arreglo (ver MIGRATION_V11). Aquí sí se recrea
    // vacía: la jornada es del día y se repuebla en la precarga siguiente; su
    // json no sirve para nada sin el padrón que lo acompaña.
    await db.execAsync(MIGRATION_V11);
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
