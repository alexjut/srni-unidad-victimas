# Sprint 4 — Motor Offline + Sincronización Automática

**Branch:** `main`
**Estado:** ✅ Completado
**Inicio:** 2026-04-19
**Cierre:** 2026-04-19
**Commit:** `6a66d64`

---

## Objetivos

1. Implementar schema SQLite local para operación sin conectividad
2. Crear la capa DAO para instrumento, borradores, hogares offline y cola de sincronización
3. Implementar el evaluador de skip logic en el cliente (TypeScript puro)
4. Crear el servicio de sincronización que resuelve conflictos offline → servidor

---

## Entregables mobile

### Schema SQLite (`src/db/schema.ts`)

Migración v1 con `PRAGMA user_version` para migraciones incrementales sin perder datos:

```sql
-- instrumento_meta: control de versión del instrumento descargado
CREATE TABLE instrumento_meta (
  clave TEXT PRIMARY KEY,
  valor TEXT NOT NULL
);

-- hogares_offline: hogares creados sin internet (sin PII)
CREATE TABLE hogares_offline (
  id_local TEXT PRIMARY KEY,
  datos_json TEXT NOT NULL,    -- sin campos PII
  sincronizado INTEGER DEFAULT 0,
  id_servidor TEXT             -- uuid asignado por el backend al sincronizar
);

-- cola_sincronizacion: queue ordenada de operaciones pendientes
CREATE TABLE cola_sincronizacion (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL,          -- CREAR_HOGAR | CREAR_SESION | RESPONDER | FINALIZAR
  payload TEXT NOT NULL,
  intentos INTEGER DEFAULT 0,
  error_ultimo TEXT,
  created_at TEXT NOT NULL
);
```

**Nota:** No se almacena ningún campo PII en SQLite local.

### Capa DAO (`src/db/`)

**`instrumentoDao.ts`**
- `guardarInstrumento(instrumento)` — batch INSERT de temas, preguntas, opciones y reglas skip logic
- `obtenerInstrumento()` — lee instrumento completo con joins (batch queries para rendimiento)
- `obtenerVersion()` — versión del instrumento almacenado (string semver)

**`borradoresDao.ts`**
- `crearBorrador(sesionId, hogarId)` — inicia borrador local
- `guardarRespuesta(sesionId, preguntaId, valor)` — upsert de respuesta
- `obtenerRespuestas(sesionId)` — todas las respuestas del borrador
- `marcarFinalizado(sesionId)` — cambia estado para sincronización

**`hogaresOfflineDao.ts`**
- `crearHogarOffline(datos)` — crea hogar con id local UUID
- `listarPendientes()` — hogares sin sincronizar
- `marcarSincronizado(idLocal, idServidor)` — actualiza tras sync exitoso

**`colaDao.ts`**
- Cola ordenada: `CREAR_HOGAR` < `CREAR_SESION` < `RESPONDER` < `FINALIZAR`
- `MAX_INTENTOS = 3` antes de marcar como error permanente
- `resetearBloqueados()` — limpia estado `procesando` tras crash de sesión
- `marcarErrorPermanente(id)` — para errores 4xx (no reintentables)

### Servicios (`src/services/`)

**`skipLogic.ts`** — Evaluador puro (sin I/O)
```typescript
// Evalúa si una pregunta debe habilitarse dado el estado actual de respuestas
function evaluarSkipLogic(
  pregunta: Pregunta,
  respuestas: Record<string, string>,
  reglas: ReglaSkipLogic[]
): boolean

// Operadores: EQ, NEQ, GT, GTE, LT, LTE, IN, NOTNULL
```

**`sincronizacion.ts`** — Orquestador
- Lee cola en orden de prioridad
- Procesa operaciones secuencialmente (CREAR_HOGAR antes que CREAR_SESION)
- Actualiza IDs locales → servidor en cadena (cascade update)
- Manejo de errores:
  - `4xx` → error permanente (no reintentar)
  - `5xx` / falla de red → incrementa `intentos`, reintenta hasta `MAX_INTENTOS`

### Store Zustand (`src/stores/syncStore.ts`)

```typescript
interface SyncState {
  estaOnline: boolean
  sincronizando: boolean
  pendientesCola: number
  erroresCola: number
  // Acciones
  iniciar(): void
  triggerSync(): Promise<void>
}
```

- `AppState` listener: triggeriza sync al volver a primer plano
- Descarga instrumento post-login si no hay versión local

### Pantallas actualizadas
- `_layout.tsx` — inicializa `syncStore` tras autenticación exitosa
- Indicador visual de estado de conectividad (online/offline)

---

## Flujo offline completo

```
Encuestador sin internet
       ↓
  Crea hogar → hogaresOfflineDao (id_local)
       ↓
  Inicia encuesta → borradoresDao (sesion_local)
       ↓
  Responde preguntas → borradoresDao.guardarRespuesta
       ↓
  Finaliza → colaDao.agregar(FINALIZAR, sesion_local)
       ↓
  [Vuelve a tener internet]
       ↓
  syncStore.triggerSync()
       ↓
  colaDao: CREAR_HOGAR → POST /api/hogares/ → id_servidor
       ↓
  cascade update: sustituye id_local por id_servidor
       ↓
  CREAR_SESION → POST /api/encuestas/ (con id_servidor del hogar)
       ↓
  RESPONDER (batch) → POST /api/encuestas/{id}/respuestas/
       ↓
  FINALIZAR → POST /api/encuestas/{id}/cerrar/
```

---

## Decisiones técnicas

**Por qué cola ordenada con prioridades:** Un CREAR_SESION sin el CREAR_HOGAR previo fallaría con FK violation. El orden garantiza consistencia en el servidor.

**Por qué `MAX_INTENTOS = 3`:** Equilibrio entre resiliencia (red intermitente en zonas rurales) y detección de errores permanentes (bug en el payload).

**Por qué skipLogic.ts es puro (sin I/O):** Facilita pruebas unitarias exhaustivas sin mock de base de datos. El evaluador es determinista: mismas entradas → mismo resultado.
