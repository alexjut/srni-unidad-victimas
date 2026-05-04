# Documentación SRNI — Sistema de Caracterización de Víctimas

**Proyecto:** Sistema de Registro Nacional de Información (SRNI)
**Unidad para las Víctimas — UARIV | Contrato 2226-2026**
**Desarrollador:** Javier Alexander Aguilar Castro
**Última actualización:** 2026-05-04

---

## Documento de entrega

- [**Informe de Avance — Entrega Formal**](INFORME-ENTREGA.md) — Estado completo: sprints, métricas, pendientes

---

## Arquitectura y Diseño

- [Arquitectura del sistema](arquitectura/ARQUITECTURA.md) — Stack, componentes, flujo de datos
- [Análisis APK original](arquitectura/ANALISIS_APK.md) — Errores del sistema v4.1 que se corrigieron

---

## Guía de desarrollo

- [Arranque del entorno](ARRANQUE-DEV.md) — Levantar backend + mobile en local
- [Túnel ngrok](TUNEL-NGROK.md) — Configurar dominios permanentes para celular físico

---

## Base de Datos

- [Índice de BD](base-datos/README.md) — Comparativa APK vs nuevo sistema
- [Modelos Django](base-datos/MODELOS.md) — Esquema completo PostgreSQL + pgcrypto
- [APK original — SQLite](base-datos/apk-original.md) — `vivanto.db` y `dbencuestadormovil.db` con sus fallas
- [Backend — PostgreSQL](base-datos/backend-postgresql.md) — Sentencias CREATE TABLE del sistema actual
- [Mobile — SQLite offline](base-datos/mobile-sqlite.md) — Schema `srni_offline.db` con migraciones

---

## Frontend — App Móvil

- [Estado actual](mobile/estado-actual.md) — Pantallas implementadas, tecnología, pendientes
- [Navegación](mobile/navegacion.md) — Rutas Expo Router, flujos, auth guard

---

## Backend — Django REST Framework

- [API Endpoints](backend/api-endpoints.md) — Rutas, métodos, autenticación, ejemplos
- [Seguridad](backend/seguridad.md) — JWT, cifrado PII, auditoría, rate limiting, normativa

---

## Instrumentos de Caracterización

- [Resumen de perfiles](instrumentos/perfiles-resumen.md) — Los 6 perfiles UARIV V7/V8, loaders, PKs
- [Perfil Territorial V7](instrumentos/perfil-territorial-v7.md) — 14 capítulos, ~248 preguntas
- [Perfil Buenaventura V7](instrumentos/perfil-buenaventura-v7.md) — 17 capítulos, ~300 preguntas
- [Perfil San Andrés / SAI V7](instrumentos/perfil-san-andres-v7.md) — 14 capítulos, ~290 preguntas

---

## Sprints

| Sprint | Descripción | Fechas | Estado |
|--------|-------------|--------|--------|
| [Sprint 01](sprints/sprint-01.md) | Fundamentos: JWT + modelos base + mobile scaffold | 2026-04-13 | ✅ |
| [Sprint 02](sprints/sprint-02.md) | Motor formularios + paramétricas + víctimas PII | 2026-04-13 | ✅ |
| [Sprint 03](sprints/sprint-03.md) | Hogares, encuestas y pantallas móviles | 2026-04-16 | ✅ |
| [Sprint 04](sprints/sprint-04.md) | Motor offline completo + sincronización automática | 2026-04-19 | ✅ |
| [Sprint 05](sprints/sprint-05.md) | Integración IA Gemini + UI GOV.CO institucional | 2026-04-19–21 | ✅ |
| [Sprint 06](sprints/sprint-06.md) | Diccionario V8 + loaders de 6 perfiles | 2026-04-21–28 | ✅ |

---

## Convenciones

- Cada sprint se documenta en `docs/sprints/sprint-XX.md` al cerrarse
- Los cambios al modelo se reflejan en `docs/base-datos/MODELOS.md` antes del commit
- Decisiones técnicas relevantes van en `docs/decisiones/` (Architecture Decision Records)
- `CLAUDE.md` es exclusivo del entorno local — nunca se sube al repositorio
