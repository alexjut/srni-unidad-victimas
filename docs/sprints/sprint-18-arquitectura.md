# Sprint 18 — Arquitectura offline-first híbrida

**Branch:** `main` (sin rama feature — convención post-Sprint 16)
**Inicio:** 2026-05-26
**Estado:** Fase 1 en curso

---

## Contexto

El usuario reportó en producción dev: bug "no se descarga el instrumento" + `database is locked` al iniciar formulario. El diagnóstico mostró que la arquitectura lazy (descargar instrumento al crear sesión) genera:

- Múltiples descargas concurrentes que colisionan en SQLite
- Dependencia de red en cada cambio de instrumento
- Capítulos viejos confunden cuando el usuario cambia de perfil
- Encuestadores en campo con red intermitente sufren

**Propuesta del usuario** (documento "Arquitectura de datos offline-first"): separar **INSTRUMENTO** (definición, replica completa, read-only) de **RESPUESTAS** (captura, fuente=device hasta sync). Hacer el instrumento offline-first vía bundle empaquetado en el APK.

---

## Principios rectores (del documento del usuario)

1. **INSTRUMENTO** (perfiles, capítulos, preguntas, opciones, skip logic): fuente de verdad backend, replica COMPLETA en SQLite, read-only en cliente.
2. **RESPUESTAS** (hogares, miembros, sesiones, respuestas): fuente de verdad device hasta sincronizar.

### Reglas innegociables

- Skip logic se ejecuta **SIEMPRE local** (`services/skipLogic.ts`).
- Validación obligatorias: cliente para UX + backend re-valida en POST.
- IDs UUID en cliente (no autoincrement) — Schema V2 ya cumple.
- Búsqueda RNI **única operación** que requiere red. Nunca datos PII al device.
- Cada `SesionEncuesta` guarda `version_instrumento`.

---

## Estado actual del puzzle (al inicio de Sprint 18)

| Punto | Estado | Acción |
|---|---|---|
| Separación INSTRUMENTO/RESPUESTAS | ✅ DAOs separados | — |
| Skip logic local | ✅ `services/skipLogic.ts` | — |
| Validación obligatorias UX | ✅ `formulario/[temaId].tsx` | — |
| Validación obligatorias backend | ⚠️ singular sí, bulk no | Fase 3 |
| UUIDs cliente | ✅ Schema V2 | — |
| RNI server-side only | ✅ | — |
| `version_instrumento` en SesionEncuesta | ❌ | Fase 2 |
| `cola_sincronizacion` con estados/intentos/error/timestamp | ✅ Schema V3 | — |
| Backoff exponencial | ✅ 30s/120s + estado 'error' | — |
| RESPONDER_BULK | ✅ existe | Fase 3 (item-by-item) |
| Idempotencia UUIDs | ⚠️ unique(sesion,pregunta) | Fase 3 (`cliente_uuid`) |
| Orden dependencias en cola | ✅ `ORDEN_TIPO` | — |
| Endpoint `/api/formulario/versiones/` | ❌ | Fase 2 |
| Descarga 304 si no cambió | ⚠️ cliente decide | Fase 2 |
| **Bundle de instrumentos en APK** | 🚧 Fase 1 | Esta fase |

---

## Plan por fases

### Fase 1 — Bundle de instrumentos (1 h) — EN CURSO

1. ✅ Comando Django `exportar_a_mobile` que serializa los 8 instrumentos desde BD al formato `InstrumentoCompletoView` y los guarda como JSON en `srni-mobile/assets/instrumentos/`. Total 674 KB.
2. ✅ Servicio `src/services/bundledInstrumentos.ts` con:
   - `BUNDLED` (require static de los 8 JSON)
   - `cargarInstrumentoBundled(perfil)` — escribe en SQLite
   - `asegurarInstrumentoLocal(perfil)` — idempotente, no hace nada si ya está
3. ✅ `caracterizar/index.tsx`: tras crear sesión, llama `asegurarInstrumentoLocal(codigo)` en lugar de `descargarInstrumento` (no usa red).
4. ✅ `formulario/index.tsx`: en el fallback de "no hay capítulos" usa `asegurarInstrumentoLocal`.
5. ✅ `[sesionId].tsx`: el botón "Continuar formulario" llama `asegurarInstrumentoLocal`.
6. ✅ `_layout.tsx`: tras login, precalentamiento de TERRITORIAL en background.
7. ⏳ Validar en celular con los 8 perfiles.

**Resultado esperado:** muere el bug "no descarga". App funciona offline desde minuto 1.

### Fase 2 — Versionado servidor (2 h)

1. Backend: agregar `version_instrumento` a `SesionEncuesta` (migration).
2. Backend: `GET /api/formulario/versiones/` → `{TERRITORIAL: 'V7', ...}` (lectura barata, sin payload pesado).
3. Backend: `GET /api/formulario/instrumento/<codigo>/` acepta `If-None-Match: <version>` → 304 Not Modified si coincide.
4. Mobile: tras login, llamar versiones/, comparar contra `index.json` bundled. Si servidor tiene versión nueva, descargar delta.
5. Mobile: cada `crearSesion` envía `version_instrumento` desde meta SQLite.

### Fase 3 — Idempotencia + bulk response item-by-item (3 h)

1. Backend migration: agregar `RespuestaEncuesta.cliente_uuid` (UUID único).
2. Backend serializer/view: `POST /encuestas/{id}/responder-bulk/` acepta items con `cliente_uuid`, retorna `[{cliente_uuid, status: 'ok'|'duplicado'|'error', detalle}, ...]`.
3. Mobile schema V4: agregar `cliente_uuid` a tabla `respuestas` y `cola_sincronizacion`.
4. Mobile cola: al recibir respuesta bulk, marca confirmados según `cliente_uuid`.
5. Migration v4 idempotente en `db/schema.ts`.

### Fase 4 — QA exhaustivo + docs (1 h)

1. Test offline → online: modo avión, llenar 10 preguntas, encender red, verificar sync.
2. Test idempotencia: enviar mismo bulk 2 veces, verificar que backend no duplica.
3. Test versionado: bump version en backend, verificar que mobile detecta y actualiza.
4. Documentar el contrato cliente↔servidor en `docs/arquitectura/sincronizacion.md`.

---

## Cómo trabajar (recomendación)

| Fase | Agentes | Estado |
|---|---|---|
| 1 | Yo solo (lineal corto) | En curso |
| 2 | Yo + 1 agente paralelo (backend serializer/migration en paralelo con cliente mobile) | Pendiente |
| 3 | Yo + 1 agente (migration BD + endpoint) en paralelo con yo (mobile schema v4) | Pendiente |
| 4 | 1 agente QA + yo en docs | Pendiente |

**Tiempo total estimado:** ~7 horas individuales, ~4 h reales con agentes paralelos.

---

## Decisiones tomadas en Sprint 18

- **NO migrar a Oracle real ahora.** Sigue el mock — la regla [feedback_oracle_no_migrar_sin_contexto] aplica.
- **NO crear ramas feature.** Trabajo directo en main siguiendo [feedback_convencion_ramas].
- **SÍ push a ambos remotes** (`git push all main`) — [feedback_push_azure_origin].
- **NO tocar `srni-frontend/`** — [feedback_division_trabajo] (Brando).
- **Bundle de instrumentos en APK** es la solución definitiva al bug "no descarga". El sync remoto queda solo para versiones nuevas (Fase 2).
