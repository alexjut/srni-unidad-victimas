# OE5 — Estructura de bases de datos

> **Obligación contractual:** *Crear, diseñar y documentar la estructura de bases de datos para garantizar la eficiencia, integridad y seguridad de los datos utilizados en los procedimientos de instrumentalización de la información y análisis tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se consolidó la **estructura completa de las dos bases de datos** del sistema: PostgreSQL en el servidor (con extensión `pgcrypto` habilitada para cifrado de PII a nivel de columna) y SQLite en el dispositivo móvil (para soporte offline). En PostgreSQL, las 8 apps Django evolucionaron a través de **27 migraciones versionadas en Git** (todas aplicables idempotentemente) que cubren el modelo del Diccionario UARIV V8, cifrado y hashing de PII, hogares v2 con autorizado + rol + estado_inclusion, sesiones con 4 FKs nuevas de ubicación de atención (Sprint 19), respuestas con FK opcional a miembro y UniqueConstraint compuesta `(sesion, pregunta, miembro)` (Sprint 21), paramétricas DANE + UARIV, usuario custom con perfiles de permisos granulares, LogAcceso inmutable y modelos de IA (consentimiento + logs Gemini). En SQLite móvil se versionó el schema desde **V0 hasta V5** con migraciones controladas por `PRAGMA user_version` y transaccionales: V0 incluía tablas iniciales de captura, V1 agregó instrumento_meta + hogares_offline + cola_sincronizacion, V2 migró a UUIDs, V3 agregó retry_after para backoff, V4 eliminó las tablas de instrumento (al pasar a arquitectura in-memory en el Sprint 18) y V5 (Sprint 21) agregó la columna `miembro_id` con nuevo UNIQUE index para soportar preguntas tipo PERSONA por miembro. El esquema garantiza integridad referencial con FK PROTECT, integridad lógica con validación en serializers (cascada DT→Depto→Mun, coherencia HOGAR/PERSONA), y eficiencia mediante 14 índices DB-level + cache en memoria de los catálogos paramétricos.

## Evidencia que soporta esta actividad

- **Migraciones Django versionadas:** carpetas `srni-backend/apps/*/migrations/` (27 archivos generados y aplicados en mayo).
- **Migraciones críticas del mes:**
  - `encuestas/0005_sesionencuesta_departamento_atencion_*.py` (4 FKs ubicación atención)
  - `encuestas/0006_alter_respuestaencuesta_options_*.py` (miembro FK + UniqueConstraint)
  - `hogares/0003_autorizado_rol_*.py` (Hogar v2)
  - `hogares/0004_remove_miembrohogar_*.py` (renames de índices)
- **Modelos Django:** `srni-backend/apps/encuestas/models.py`, `hogares/models.py`, `formulario/models.py`, `parametricas/models.py`.
- **Schema SQLite mobile:** `srni-mobile/src/db/schema.ts` (V5 con DDL_V0 + 5 migraciones idempotentes).
- **Habilitación pgcrypto:** `infra/postgres/init.sql`.
- **DAOs de acceso a datos en mobile:** `srni-mobile/src/db/borradoresDao.ts`, `colaDao.ts`, `hogaresOfflineDao.ts`, `instrumentoDao.ts`.
- **Diagrama ER en ASCII:** sección "Diseño de relaciones" del README.md de esta carpeta.
- **Copias locales en esta carpeta:** `encuestas-models.py`, `hogares-models.py`, `formulario-models.py`, `schema-mobile.ts`.

---

## Actividades del cronograma

1. **Diseño del modelo entidad-relación** completo del sistema
2. **Implementación modelos Django con migraciones versionadas** en Git
3. **Schema SQLite local** para app móvil (instrumento, temas, preguntas, borradores)
4. Documentación MODELOS.md

## Avances en Mayo 2026

### Modelos del backend (PostgreSQL)

Cada app Django tiene su carpeta `migrations/` versionada en Git. En mayo se generaron y aplicaron las siguientes migraciones:

| App | Migraciones nuevas en mayo | Tema principal |
|---|---|---|
| `formulario` | 0001-0007 | Diccionario V8, Instrumento + Capítulo + Pregunta + Opción + Regla |
| `victimas` | 0001-0003 | PII cifrado, hash SHA-256 |
| `hogares` | 0001-0004 | Hogar v2, MiembroHogar con rol + estado_inclusion + autorizado |
| `encuestas` | 0001-0006 | Sesión, Respuesta, ubicación atención (Sprint 19), miembro FK (Sprint 21) |
| `parametricas` | 0001-0002 | DT UARIV, Punto Atención, Departamento, Municipio, Vereda |
| `autenticacion` | 0001-0003 | Usuario custom, Perfil con permisos granulares |
| `auditoria` | 0001-0002 | LogAcceso inmutable |
| `ia` | 0001-0002 | ConsentimientoIA, logs Gemini |

### Migraciones críticas del mes

| Migración | Sprint | Lo que hace |
|---|---|---|
| `encuestas/0005_sesionencuesta_departamento_atencion_*` | 19 | + 4 FKs ubicación atención |
| `encuestas/0006_alter_respuestaencuesta_options_*` | 21 | + miembro FK + UniqueConstraint(sesion, pregunta, miembro) |
| `hogares/0003_autorizado_rol_*` | 12 | Modelo Hogar v2: autorizado, rol, estado_inclusion |
| `hogares/0004_remove_miembrohogar_*` | 21 | Renames de índices automáticos |
| `formulario/0007_*` | 21 | Activación `activa=False` para preguntas obsoletas DT_ATENCION etc. |

### Schema SQLite mobile (`srni_offline.db`)

Versiones del schema:

| Versión | Sprint | Cambios |
|---|---|---|
| V0 | 3 | Tablas iniciales: borradores, respuestas, sync_log |
| V1 | 4 | instrumento_meta, hogares_offline, cola_sincronizacion |
| V2 | 7 | UUIDs para tablas de instrumento |
| V3 | 9 | cola_sincronizacion.retry_after (backoff) |
| V4 | 18 | DROP tablas de instrumento (viven en memoria desde bundle) |
| **V5** | **21** | **respuestas.miembro_id + nuevo UNIQUE(borrador, pregunta, miembro)** |

Migraciones idempotentes con `PRAGMA user_version`. Cada upgrade es transaccional.

### Tablas vivas (post Sprint 18 V4)

```sql
-- Datos capturados por el encuestador
borradores              (id UUID, hogar_id, sesion_id, instrumento_id, estado, …)
respuestas              (id, borrador_id, pregunta_id, miembro_id, valor, updated_at)
hogares_offline         (id_local, id_servidor, autorizado_uuid, municipio_id, …)
cola_sincronizacion     (id, tipo, recurso_local_id, payload JSON, estado, intentos, retry_after, …)
sync_log                (id, borrador_id, intentado, resultado, detalle)
```

### Diseño de relaciones (resumen)

```
Victima
   ▲
   │ FK
   │
Hogar ──┬── MiembroHogar
   ▲    │
   │    │ M2M
   │    │
   │    └── (autorizado: uno solo por hogar)
   │
Hogar ──── SesionEncuesta ──── RespuestaEncuesta
   │           ▲    │              │
   │           │    │ FK           │ FK opcional
   │           │    │              ▼
   │           │    │           MiembroHogar (PERSONA)
   │           │    │
   │           │    ▼
   │           │  Instrumento ── Capitulo ── Pregunta ── Opcion
   │           │                                   │
   │           │                                   ▼
   │           │                              ReglaSkipLogic
   │           │
   │           └─ DireccionTerritorial, Departamento, Municipio, PuntoAtencion (FKs ubicación)
   │
   └── (Municipio)
```

## Archivos relevantes

Copias locales:

- [`encuestas-models.py`](encuestas-models.py) — modelo Sesión + Respuesta con miembro FK
- [`hogares-models.py`](hogares-models.py) — modelo Hogar v2 + MiembroHogar
- [`formulario-models.py`](formulario-models.py) — Instrumento + Capítulo + Pregunta + Opción
- [`schema-mobile.ts`](schema-mobile.ts) — schema SQLite V5 idempotente con migraciones

Referencias al repo:

- `srni-backend/apps/*/migrations/` — todas las migraciones versionadas
- `srni-mobile/src/db/schema.ts` — schema y migraciones SQLite
- `infra/postgres/init.sql` — habilitación de `pgcrypto`
- `docs/base-datos/` — diagrama ER (pendiente actualizar)

## Pendientes (a complementar Javier)

- Actualizar `docs/MODELOS.md` con los cambios de Sprint 19 (ubicación atención) y Sprint 21 (miembro FK)
- Diagrama ER visual (drawio o similar) — actualmente solo hay ascii
