# Frontend — App Móvil SRNI

**Tecnología:** React Native + Expo SDK 54  
**Enrutamiento:** Expo Router (file-based routing)  
**Estado:** En desarrollo activo  
**Última actualización:** 2026-05-21

---

## Qué ES el frontend actual

El frontend del SRNI es la **app móvil React Native**, no una SPA Angular.
La ARQUITECTURA.md menciona Angular 17 como plan a futuro (Fase 2 — web).
Lo que existe y funciona hoy es `srni-mobile/`.

No existe aún:
- Frontend web Angular
- PWA offline-first
- Dashboard web de supervisores

---

## Pantallas implementadas

```
srni-mobile/app/
├── _layout.tsx                          ← Root layout + PaperProvider + auth guard
├── index.tsx                            ← Redirect según sesión
├── (auth)/
│   ├── _layout.tsx
│   └── login.tsx                        ✅ Login JWT con UI GOV.CO
└── (main)/
    ├── _layout.tsx                      ✅ Bottom tabs (Dashboard, Búsqueda, Hogares, Caracterizar)
    ├── index.tsx                        ✅ Dashboard con resumen del encuestador
    ├── busqueda.tsx                     ✅ Búsqueda RNI (server-side, sin PII en cliente)
    ├── hogares/
    │   ├── index.tsx                    ✅ Lista de hogares asignados
    │   ├── nuevo.tsx                    ✅ Crear nuevo hogar
    │   └── [hogarId].tsx               ✅ Detalle/edición de hogar
    ├── caracterizar/
    │   └── index.tsx                    ✅ Flujo instrumento → hogar → crear sesión
    ├── formulario/
    │   ├── index.tsx                    ✅ Lista de capítulos del instrumento
    │   ├── [temaId].tsx                ✅ Motor preguntas + skip logic + carga previa + bulk sync (S8)
    │   ├── consentimiento-ia.tsx       ✅ Consentimiento para asistente IA
    │   ├── grabacion-entrevista.tsx    ✅ Modo Gemini — grabación batch por capítulo (S7)
    │   └── revision-ia.tsx            ✅ Revisión y confirmación de sugerencias IA (S7)
    ├── encuestas/
    │   ├── index.tsx                    ✅ Lista de sesiones de encuesta
    │   └── [sesionId].tsx              ✅ Detalle de sesión + nombre dinámico instrumento (S8)
    ├── sync-status.tsx                 ✅ Estado de la cola de sincronización (S9)
    └── reportes.tsx                    ✅ Reportes de producción con métricas y export CSV (S10)
```

---

## Flujo de caracterización

### Modo Manual (implementado)

```
Tab Caracterizar
  → Seleccionar instrumento (perfil: TERRITORIAL, BUENAVENTURA, etc.)
  → Seleccionar hogar (o crear uno desde Tab Hogares)
  → Crear sesión en servidor
  → Formulario: lista de capítulos
  → Por cada capítulo: responder preguntas con skip logic offline
  → Cola de sincronización → servidor cuando haya conexión
```

### Modo Asistido Gemini (implementado Sprint 7)

```
Tab Caracterizar → Seleccionar instrumento → Seleccionar hogar → Crear sesión
  → Formulario: selector "Manual / Asistido por IA"
  → Grabar entrevista del capítulo completo (grabacion-entrevista.tsx)
  → POST /api/ia/procesar-entrevista/ → Gemini extrae respuestas
  → Revisar y confirmar sugerencias (revision-ia.tsx)
  → Guardar respuestas confirmadas
```

Degrada silenciosamente a modo manual cuando no hay conexión.

---

## Stack técnico

| Componente | Tecnología |
|-----------|-----------|
| Framework | React Native + Expo SDK 54 |
| Routing | Expo Router (file-based) |
| UI | React Native Paper (estilo GOV.CO) |
| Estado global | Zustand (`authStore`, `syncStore`, `iaStore`, `caracterizacionStore`) |
| HTTP | Axios + interceptores JWT |
| Almacenamiento local | expo-sqlite (schema offline, Migration V3) |
| IA asistente | Proxy Gemini vía backend Django |

---

## SQLite local — Schema V3 (Sprint 9)

Las tablas usan TEXT PKs (UUID) alineados con IDs del servidor. Migration V3 agrega columna `retry_after` a la cola.

```sql
-- Tablas principales
instrumentos      -- meta del instrumento descargado
capitulos         -- capítulos del instrumento (UUID PK)
preguntas         -- preguntas (UUID PK, codigo_externo)
opciones          -- opciones de respuesta por pregunta
reglas_skip_logic -- reglas HABILITAR/DESHABILITAR/OBLIGAR/FINALIZAR

-- Offline-first
hogares_offline   -- hogares creados sin conexión
borradores        -- sesiones pendientes de sincronizar
borradores_resp   -- respuestas en borrador por sesión

-- Cola de sincronización (V3)
cola_sincronizacion -- operaciones con backoff exponencial (retry_after)
```

**Tipos de operaciones en la cola:**
- `CREAR_HOGAR` — hogar creado offline
- `CREAR_SESION` — sesión creada offline
- `RESPONDER_PREGUNTA` — respuesta individual
- `RESPONDER_BULK` — N respuestas de un capítulo en un ítem (Sprint 8/9)
- `FINALIZAR_SESION` — cierre de sesión

**Backoff exponencial:** intento 1 → espera 30s · intento 2 → espera 120s · intento 3 → estado `error` definitivo.

---

## Skip logic offline

El motor evalúa las reglas localmente en `src/services/skipLogic.ts` sin llamadas al servidor. Semántica:

- **HABILITAR**: pregunta oculta por defecto, visible solo si la condición se cumple
- **DESHABILITAR**: pregunta visible por defecto, oculta si la condición se cumple
- **OBLIGAR**: hace la pregunta obligatoria cuando la condición se cumple
- **FINALIZAR**: cierra el capítulo cuando la condición se cumple

Las reglas se descargan junto con el instrumento en `GET /api/formulario/instrumento/{perfil_codigo}/`.

---

## Seguridad implementada

- Tokens JWT en `expo-secure-store` (keychain del SO) — nunca en AsyncStorage
- Auto-login biométrico (huella/Face ID) con `expo-local-authentication`
- Logout limpia Zustand + expo-sqlite + expo-secure-store
- Búsqueda RNI solo server-side, el cliente recibe resúmenes paginados
- Sin datos PII almacenados localmente en SQLite
- Interceptor Axios que añade `Authorization: Bearer` en cada request
- Refresh automático de token al recibir 401
- `allowBackup: false` en configuración de la app (Android)

---

## Estado actual — todo implementado (Sprint 11)

| Funcionalidad | Sprint | Estado |
|--------------|--------|--------|
| Login JWT + biometría + UI GOV.CO | S5/S7 | ✅ |
| Búsqueda RNI server-side | S3 | ✅ |
| Gestión de hogares y miembros | S3 | ✅ |
| Flujo de caracterización (instrumento → hogar → sesión) | S7 | ✅ |
| Motor de formulario con skip logic offline | S4/S8 | ✅ |
| Carga de respuestas previas al abrir capítulo | S8 | ✅ |
| Bulk sync al guardar capítulo | S8 | ✅ |
| Modo Gemini: grabación + revisión batch | S7 | ✅ |
| Cola robusta con backoff exponencial | S9 | ✅ |
| Path offline al guardar capítulo | S9 | ✅ |
| Pantalla sync-status con estado de la cola | S9 | ✅ |
| Reportes de producción con métricas y export CSV | S10 | ✅ |

## Pendientes (backlog Fase 2)

| Pendiente | Prioridad |
|-----------|-----------|
| Push notifications para asignaciones nuevas | Baja |
| Firma digital del encuestador al cerrar sesión | Media |
| Dashboard web de supervisores (Angular — Fase 2) | Alta |
| Panel de gestión (Django Admin extendido) | Media |

---

## Cómo levantar el frontend

```powershell
cd srni-mobile
npm install
npx expo start --port 8082
# Usar tunnel para celular físico:
# .\tunnel.bat  (en terminal separada)
```

Puerto: `8082` (ngrok: `https://srniapk.ngrok.app`)

Para conectar al backend en desarrollo ver `docs/ARRANQUE-DEV.md`.
