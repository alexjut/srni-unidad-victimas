# Base de Datos Mobile — SQLite Offline (srni_offline.db)

**Motor:** expo-sqlite (SQLite 3.x en Android/iOS)
**Archivo:** `srni_offline.db` (en el sandbox privado de la app)
**Versión schema:** 1 (PRAGMA user_version)
**Última actualización:** 2026-05-04

---

## Principio fundamental

```
REGLA IRROMPIBLE: NUNCA almacenar PII en el dispositivo.
Sin nombres, sin documentos, sin fechas de nacimiento en SQLite local.
Solo UUIDs opacos, datos de vivienda y respuestas del formulario.
```

Esta regla corrige el error más grave del APK original (785 MB de víctimas sin cifrar en el dispositivo).

---

## Versiones del schema

| Versión | Sprint | Descripción |
|---------|--------|-------------|
| 0 (DDL_V0) | Sprint 3 | Instrumento offline: temas, preguntas, opciones, borradores, respuestas |
| 1 (MIGRATION_V1) | Sprint 4 | Motor offline completo: cola de sincronización, hogares offline |

Control de versión con `PRAGMA user_version`. Las migraciones son acumulativas e idempotentes.

---

## Schema v0 — DDL inicial (Sprint 3)

```sql
PRAGMA journal_mode = WAL;    -- Write-Ahead Logging: lecturas concurrentes sin bloqueo
PRAGMA foreign_keys = ON;     -- Integridad referencial habilitada

-- Capítulos del instrumento descargado (equivale a formulario_capitulo en backend)
CREATE TABLE IF NOT EXISTS temas (
    id      INTEGER PRIMARY KEY,
    codigo  TEXT    NOT NULL,       -- 'A', 'B', 'C'...
    nombre  TEXT    NOT NULL,
    orden   INTEGER NOT NULL DEFAULT 0,
    activo  INTEGER NOT NULL DEFAULT 1   -- 0/1 (SQLite no tiene BOOLEAN)
);

-- Preguntas del instrumento (equivale a formulario_pregunta en backend)
CREATE TABLE IF NOT EXISTS preguntas (
    id              INTEGER PRIMARY KEY,
    tema_id         INTEGER NOT NULL REFERENCES temas(id),
    codigo          TEXT    NOT NULL,       -- codigo_externo del backend
    texto           TEXT    NOT NULL,
    texto_ayuda     TEXT    NOT NULL DEFAULT '',
    tipo_respuesta  TEXT    NOT NULL DEFAULT 'OPCION_UNICA',
    -- TEXTO | NUMERICO | FECHA | BOOLEAN | RADIO | LISTA | LISTA_MULTIPLE | COMBO_DINAMICO
    orden           INTEGER NOT NULL DEFAULT 0,
    requerida       INTEGER NOT NULL DEFAULT 1,
    activa          INTEGER NOT NULL DEFAULT 1,
    validacion      TEXT    NOT NULL DEFAULT '{}'    -- JSON: {'min':0,'max':7}
);

-- Opciones de respuesta (equivale a formulario_opcionrespuesta en backend)
CREATE TABLE IF NOT EXISTS opciones_respuesta (
    id          INTEGER PRIMARY KEY,
    pregunta_id INTEGER NOT NULL REFERENCES preguntas(id),
    codigo      TEXT    NOT NULL,
    texto       TEXT    NOT NULL,
    orden       INTEGER NOT NULL DEFAULT 0
);

-- Reglas de skip logic (equivale a formulario_reglaskiplogic en backend)
CREATE TABLE IF NOT EXISTS preguntas_derivadas (
    id                  INTEGER PRIMARY KEY,
    pregunta_padre_id   INTEGER NOT NULL REFERENCES preguntas(id),
    pregunta_hija_id    INTEGER NOT NULL REFERENCES preguntas(id),
    operador            TEXT    NOT NULL DEFAULT 'EQ',
    -- EQ | NEQ | GT | GTE | LT | LTE | IN | NOTNULL
    valor_condicion     TEXT    NOT NULL DEFAULT ''
);

-- Sesiones de encuesta en borrador (sin PII)
CREATE TABLE IF NOT EXISTS borradores (
    id              TEXT    PRIMARY KEY,        -- UUID local
    hogar_id        TEXT,                       -- UUID del hogar (servidor o local)
    sesion_id       TEXT,                       -- UUID de sesión en servidor (null hasta sync)
    instrumento_id  INTEGER,
    estado          TEXT    NOT NULL DEFAULT 'EN_PROGRESO',   -- EN_PROGRESO | FINALIZADO
    created_at      TEXT    NOT NULL,           -- ISO 8601
    updated_at      TEXT    NOT NULL
);

-- Respuestas guardadas offline (sin PII — solo valores de formulario)
CREATE TABLE IF NOT EXISTS respuestas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    borrador_id TEXT    NOT NULL REFERENCES borradores(id),
    pregunta_id INTEGER NOT NULL REFERENCES preguntas(id),
    valor       TEXT    NOT NULL DEFAULT '',    -- String serializado (igual que backend)
    updated_at  TEXT    NOT NULL
);

-- Índice único: una sola respuesta por (borrador, pregunta) — permite upsert
CREATE UNIQUE INDEX IF NOT EXISTS idx_respuestas_unique
    ON respuestas(borrador_id, pregunta_id);

-- Log de intentos de sincronización
CREATE TABLE IF NOT EXISTS sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    borrador_id TEXT    NOT NULL,
    intentado   TEXT    NOT NULL,   -- ISO 8601
    resultado   TEXT    NOT NULL,   -- OK | ERROR
    detalle     TEXT    NOT NULL DEFAULT ''
);
```

---

## Schema v1 — Migración Sprint 4

```sql
-- Control de versión del instrumento descargado
CREATE TABLE IF NOT EXISTS instrumento_meta (
    id              INTEGER PRIMARY KEY DEFAULT 1,   -- singleton: solo 1 fila
    instrumento_id  INTEGER NOT NULL,
    version         TEXT    NOT NULL DEFAULT '0',    -- semver del instrumento
    descargado_en   TEXT    NOT NULL                 -- ISO 8601
);

-- Hogares creados sin conexión (SIN PII — solo datos de vivienda)
CREATE TABLE IF NOT EXISTS hogares_offline (
    id_local            TEXT    PRIMARY KEY,         -- UUID generado localmente
    id_servidor         TEXT,                        -- UUID asignado por backend al sincronizar
    jefe_hogar_uuid     TEXT    NOT NULL,            -- UUID opaco de la víctima (sin nombre/doc)
    municipio_id        INTEGER,
    tipo_vivienda       TEXT    NOT NULL DEFAULT '',
    condicion_ocupacion TEXT    NOT NULL DEFAULT '',
    estrato             INTEGER NOT NULL DEFAULT 0,
    numero_cuartos      INTEGER NOT NULL DEFAULT 0,
    numero_personas     INTEGER NOT NULL DEFAULT 1,
    observaciones       TEXT    NOT NULL DEFAULT '',
    estado_sync         TEXT    NOT NULL DEFAULT 'pendiente',
    -- pendiente | enviando | sincronizado | error_permanente
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hogares_sync ON hogares_offline(estado_sync);

-- Cola de operaciones pendientes de sincronización
CREATE TABLE IF NOT EXISTS cola_sincronizacion (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo             TEXT    NOT NULL,
    -- CREAR_HOGAR | CREAR_SESION | RESPONDER | FINALIZAR
    -- Orden de prioridad: CREAR_HOGAR < CREAR_SESION < RESPONDER < FINALIZAR
    recurso_local_id TEXT    NOT NULL,    -- UUID local del recurso
    payload          TEXT    NOT NULL DEFAULT '{}',   -- JSON del body a enviar
    estado           TEXT    NOT NULL DEFAULT 'pendiente',
    -- pendiente | procesando | sincronizado | error_permanente
    intentos         INTEGER NOT NULL DEFAULT 0,      -- MAX_INTENTOS = 3
    ultimo_error     TEXT    NOT NULL DEFAULT '',
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
);

-- Índice de proceso: primero por tipo (prioridad implícita), luego por id (FIFO)
CREATE INDEX IF NOT EXISTS idx_cola_estado ON cola_sincronizacion(estado, id);
```

---

## Flujo de migraciones

```typescript
// src/db/schema.ts — initDatabase()
const db = await SQLite.openDatabaseAsync('srni_offline.db');
const { user_version } = await db.getFirstAsync('PRAGMA user_version');

await db.execAsync(DDL_V0);       // idempotente: CREATE TABLE IF NOT EXISTS

if (user_version < 1) {
    await db.execAsync(MIGRATION_V1);
    await db.execAsync('PRAGMA user_version = 1');
}
```

Agregar futuras migraciones siguiendo el mismo patrón: `if (user_version < N)`.

---

## Comparativa con BD original del APK

| Aspecto | APK original (dbencuestadormovil.db) | SRNI mobile (srni_offline.db) |
|---------|--------------------------------------|-------------------------------|
| Tamaño | 785 MB | < 5 MB (solo instrumento + borradores) |
| Datos de víctimas | 9.4M registros con PII completo | 0 registros — RNI en servidor |
| Nombre/apellido | Texto plano | No almacenado |
| Número documento | Texto plano | No almacenado |
| Fecha nacimiento | Texto plano | No almacenado |
| WAL mode | No | Sí (rendimiento en móvil) |
| Foreign keys | No (sin integridad) | Sí |
| Índice único respuestas | No (duplicados posibles) | Sí (upsert seguro) |
| Migraciones versionadas | No | Sí (PRAGMA user_version) |

---

## Consultas útiles para debug

```sql
-- Estado actual del instrumento descargado
SELECT * FROM instrumento_meta;

-- Borradores pendientes de sincronizar
SELECT b.id, b.hogar_id, b.estado,
       COUNT(r.id) AS respuestas_guardadas
FROM borradores b
LEFT JOIN respuestas r ON r.borrador_id = b.id
GROUP BY b.id;

-- Cola de sincronización por tipo y estado
SELECT tipo, estado, COUNT(*) as total, MAX(intentos) as max_intentos
FROM cola_sincronizacion
GROUP BY tipo, estado
ORDER BY id;

-- Hogares pendientes de sincronizar
SELECT id_local, id_servidor, municipio_id, estado_sync, created_at
FROM hogares_offline
WHERE estado_sync != 'sincronizado';

-- Verificar que no hay PII en ninguna tabla
-- (ningún campo de texto debe contener nombres o documentos)
PRAGMA table_info(hogares_offline);
-- Solo debe haber: UUIDs, ids numéricos, textos de vivienda, fechas ISO
```

---

## Seguridad del archivo SQLite

El archivo `srni_offline.db` reside en:
```
/data/data/com.srni.encuestador/databases/srni_offline.db
```

Protecciones:
- **Sandbox de Android/iOS:** solo accesible por la propia app
- **`allowBackup=false`** en `AndroidManifest.xml` — impide backup ADB
- Sin datos PII: aunque se extrajera el archivo, no contiene información sensible
- Sin SQLCipher: no necesario dado que no hay PII (y SQLCipher tiene overhead de rendimiento)
