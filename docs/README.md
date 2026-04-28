# Documentación SRNI — Sistema de Caracterización de Víctimas

**Proyecto:** Sistema de Registro Nacional de Información (SRNI)  
**Unidad para las Víctimas — UARIV**  
**Desarrollador:** Javier Alexander Aguilar Castro  
**Última actualización:** 2026-04-28

---

## Índice

### Arquitectura y Diseño
- [Arquitectura del sistema](../ARQUITECTURA.md) — Stack, componentes, flujo de datos
- [Modelos de base de datos](../MODELOS.md) — Esquema PostgreSQL + pgcrypto
- [Análisis APK original](../ANALISIS_APK.md) — Errores del sistema v4.1 (referencia)

### Frontend — App Móvil
- [Estado actual](mobile/estado-actual.md) — Pantallas implementadas, tecnología, pendientes
- [Navegación](mobile/navegacion.md) — Estructura de rutas Expo Router

### Backend — Django REST Framework
- [API Endpoints](backend/api-endpoints.md) — Rutas, métodos, autenticación
- [Seguridad](backend/seguridad.md) — JWT, cifrado PII, auditoría

### Instrumentos de Caracterización
- [Resumen de perfiles](instrumentos/perfiles-resumen.md) — Los 6 perfiles UARIV V7/V8
- [Perfil Territorial V7](instrumentos/perfil-territorial-v7.md)
- [Perfil Buenaventura V7](instrumentos/perfil-buenaventura-v7.md)
- [Perfil San Andrés / SAI V7](instrumentos/perfil-san-andres-v7.md)

### Sprints
- [Sprint 01](sprints/sprint-01.md) — Autenticación JWT + modelos base
- [Sprint 02](sprints/sprint-02.md) — Motor de formularios dinámico
- [Sprint 03](sprints/sprint-03.md) — API REST + encuestas
- [Sprint 04](sprints/sprint-04.md) — App móvil UI GOV.CO
- [Sprint 05](sprints/sprint-05.md) — Integración IA Gemini + UI móvil
- [Sprint 06](sprints/sprint-06.md) — Diccionario V8 + loaders de perfiles ← en curso

---

## Convenciones de documentación

- Cada sprint se documenta en `docs/sprints/sprint-XX.md` al cerrarse
- Los cambios al modelo se reflejan en `MODELOS.md` antes del commit
- Las decisiones técnicas relevantes van en `docs/decisiones/` (Architecture Decision Records)
- Este README se actualiza cuando se agrega un documento nuevo

---

## Agente Documentador

El agente `/documentador` tiene acceso a esta carpeta para:
1. Actualizar el estado de sprints al cerrar cada uno
2. Mantener `perfiles-resumen.md` sincronizado con los loaders
3. Agregar entradas a `backend/api-endpoints.md` cuando se crea una nueva vista
4. Documentar decisiones técnicas en `docs/decisiones/`

Para invocar: `/documentador` desde Claude Code.
