# OE1 — Desarrollo, mantenimiento, documentación y soporte

> **Obligación contractual:** *Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se ejecutaron **16 sprints técnicos (6 al 21)** con un total de **80 commits firmados** distribuidos en los 3 componentes del sistema: backend Django REST Framework, app móvil React Native + Expo SDK 54 y panel web React + Vite. Los avances incluyeron: rediseño completo de UX del login con biometría y flujo de caracterización (Sprint 7), motor de formulario end-to-end con bulk sync (Sprint 8), sincronización masiva robusta con backoff exponencial (Sprint 9), reportes de producción del encuestador (Sprint 10), hardening de seguridad para producción (Sprint 11), implementación del panel web React + Tailwind para supervisores (Sprint 12), backend habilitador con filtros server-side y endpoints de supervisor/dashboard (Sprint 13), refactor del flujo móvil a un hub de caracterizaciones por hogar (Sprint 14), carga completa de los 8 instrumentos UARIV (Sprint 15), fix de 3 bugs críticos en el flujo móvil (Sprint 16), QA exhaustivo con sistema de captura de errores en producción (Sprint 17), refactor a arquitectura in-memory que elimina el "database is locked" recurrente (Sprint 18), implementación de la ubicación de atención como metadata de la sesión con cascada UARIV de 21 DTs y 1102 municipios (Sprint 19), backend habilitador para el panel web con renombrado descriptivo de instrumentos y render del selector dinámico de municipio (Sprint 20) y, finalmente, soporte de preguntas tipo PERSONA por cada miembro del hogar con wizard de navegación + calendario nativo en fechas (Sprint 21). El soporte continuo del mes resolvió 8 bugs críticos sin afectar la disponibilidad del entorno de desarrollo.

## Evidencia que soporta esta actividad

- **Repositorio Git:** `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04` (Azure DevOps oficial UARIV) y `github.com/alexjut/srni-unidad-victimas` (GitHub backup) — rama `main` al commit `7d1a6b9`.
- **Bitácora de commits:** `OE8-informes/git-log-mayo-2026.txt` (80 commits con fecha, hash y mensaje).
- **Documentación de sprints:** `docs/sprints/sprint-07.md` a `sprint-11.md` + bitácora interna `docs/frontend/bitacora-desarrollo.md`.
- **Snapshot del estado del proyecto:** `docs/estado-actual.md`.
- **Reporte automatizado de QA por instrumento:** `docs/qa-perfiles-sprint20.md` (regenerable con `scripts/qa_perfiles.py`).
- **Correo de coordinación con frontend (Brando):** `docs/correo-brando.md`.
- **Código fuente:** carpetas `srni-backend/`, `srni-mobile/`, `srni-frontend/` en el repositorio versionado.

---

## Actividades del cronograma

1. Análisis del aplicativo móvil existente (APK Vivanto v4.1)
2. Ingeniería inversa del APK
3. Análisis con usuarios funcionales
4. Plan de contingencia
5. Desarrollo backend Django Sprint 1 (auth JWT, modelos base, Swagger, 33 tests)
6. Desarrollo backend Django Sprint 2 (paramétricas, motor formularios, víctimas PII)
7. Desarrollo app móvil React Native + Expo
8. Motor de formularios offline (54 módulos, 1416 preguntas, skip logic)
9. Módulo IA Gemini Live (audio en tiempo real)
10. Pruebas unitarias, integración y regresión por sprint
11. **Documentación técnica:** arquitectura, APIs, manuales
12. **Soporte y mantenimiento continuo** — corrección de bugs y ajustes semanales

## Avances en Mayo 2026

### Sprint 7 — UX rediseño + Gemini batch (4-8 mayo)

- Rediseño completo del login con gradiente azul y franja GOV.CO + biometría
- Pantalla de búsqueda RNI con imagen indígena y formulario flotante
- Flujo víctima habilitada/no incluida
- Lista de instrumentos inline (no pantalla separada)
- Modo Gemini batch: grabación-entrevista + revisión-IA

**Commits:**
- `4742167` feat(sprint7): UX rediseño login + búsqueda + flujo caracterización completo
- `c8d9d37` feat(sprint7): modo Gemini batch — grabación-entrevista + revisión-ia
- `0266f66` feat(formulario/sprint7): loader data-driven + catálogo opciones compartidas
- `caa8e59` feat(mobile/sprint7): migrar a UUIDs, skip logic V8 y flujo sesión→formulario

### Sprint 8 — Motor de formulario end-to-end (21 mayo)

- Motor lee respuestas previas del servidor (no se pierde nada)
- Validación de obligatorias con alertas tipadas
- Bulk sync de respuestas (envío masivo en una sola petición)
- Progreso real por capítulo (% calculado del servidor)

**Commits:** `2c5230c`, `de6a08c`

### Sprint 9 — Sincronización masiva robusta (21 mayo)

- Cola con backoff exponencial (retry inteligente)
- Endpoint RESPONDER_BULK en backend
- Polling cada 60 s en mobile
- Pantalla de sincronización con métricas en tiempo real
- Path offline completamente funcional

**Commits:** `6648be8`, `c3ec661`

### Sprint 10 — Reportes de producción (21 mayo)

- Resumen del encuestador (sesiones totales, completadas, en progreso, hogares)
- Detalle paginado con cursor pagination
- Export CSV
- Pantalla móvil con métricas

**Commits:** `9373d0b`, `031f2a6`

### Sprint 12 — Panel Web React + scaffold (22 mayo)

- Scaffold completo de `srni-frontend/`: Vite + Tailwind + Zustand + React 18
- Modelo Hogar v2: autorizado + rol miembro + estado inclusión
- Pantalla `hogares/conformar.tsx` en mobile (rol del miembro)

**Commits:** `eeb3737`, `88d7195`, `bdffdca`

### Sprint 14 — Mobile flujo cosido (25 mayo)

- Hub de caracterizaciones por hogar (`hogares/[hogarId]/caracterizaciones.tsx`)
- Eliminación de botones sueltos; navegación lineal
- Migas de pan + back coherente

**Commits:** `908dc4b`, `dba81ce`

### Sprint 15 — Cargar 8 instrumentos completos (25 mayo)

- ASISTENCIA, TERRITORIAL, BUENAVENTURA, SAN_ANDRÉS, TELEFÓNICO, URBANO_ÉTNICO, RURAL_ÉTNICO, VÍCTIMAS_EXTERIOR
- +18 listas nuevas en catálogo de opciones
- Scripts `arrancar-backend.ps1` + `arrancar-mobile.ps1` con detección automática de IP

**Commits:** `27dbe60`, `54ac0a8`, `dac0dfe`

### Sprint 17 — Robustecimiento + QA exhaustivo (25-26 mayo)

- Fix bugs críticos de sincronización offline
- ErrorBoundary global + endpoint debug
- Sistema de captura de errores en mobile
- Mutex global para SQLite
- Logger remoto activo

**Commits:** `7001b7e`, `9525ee1`, `890eb83`, `b65188a`, `f967fb1`, `b1d2fc9`, `837519b`, `8cd4a3e`, `b515004`, `44cd5eb`, `a1c976f`, `7483184`, `6d2a044`

### Sprint 18 — Arquitectura in-memory + redactor PII (26 mayo)

- Instrumentos viven en memoria desde bundle JSON (no SQLite)
- Migración V4: drop tablas obsoletas
- Redactor de PII en logs del interceptor axios
- Fin del "database is locked"

**Commits:** `2f6811f`, `e8b1ef6`, `9feddf8`, `478b305`, `31d3477`, `7429777`, `d5295db`, `e820e32`, `d289a7c`

### Sprint 21 — Preguntas PERSONA por miembro + calendario + wizard (26 mayo)

- Modelo `RespuestaEncuesta.miembro` FK + validación HOGAR/PERSONA
- SQLite mobile V5 + cola con `miembro_id`
- Motor: capítulo agrupa HOGAR + bloques por miembro
- Calendario nativo en preguntas FECHA
- Headers con nombre real del miembro
- Wizard 1-a-la-vez con botones Anterior/Siguiente

**Commits:** `1be5470`, `c9248da`, `82e8318`, `fb75ca2`, `e847990`, `be8755e`, `eab3075`

## Documentación generada

- `docs/sprints/sprint-07.md` a `sprint-11.md` (5 archivos)
- `docs/api-endpoints.md` actualizado
- `docs/estado-actual.md` (mapa completo del proyecto)
- `docs/qa-perfiles-sprint20.md` (reporte QA automático)
- `docs/correo-brando.md` (instrucciones para frontend)

## Soporte y mantenimiento

A lo largo del mes se atendieron y corrigieron:
- 3 bugs de sincronización offline (Sprint 17)
- 1 bug crítico de SQLite NPE (Sprint 17)
- 1 bug `Instrumento.perfil` que rompía GET hogares (Sprint 16)
- 1 bug 34 preguntas LISTA sin opciones (Sprint 16)
- 1 bug código instrumento confuso (Sprint 20)
- 16 preguntas COMBO_DINAMICO sin renderizar (Sprint 20-B)
- 1 bug fecha como input manual (Sprint 21-D)

## Archivos relevantes (referencias al repo)

- `srni-backend/` — backend Django completo
- `srni-mobile/` — app React Native + Expo SDK 54
- `srni-frontend/` — panel web React + Vite + Tailwind
- `docs/sprints/` — bitácora detallada
- `docs/estado-actual.md` — snapshot del proyecto

## Pendientes (a complementar Javier)

- Capturas finales del flujo cosido para anexar al informe
- Resumen de horas semanal (si supervisor lo solicita)
