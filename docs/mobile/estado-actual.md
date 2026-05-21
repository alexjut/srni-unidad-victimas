# Frontend — App Móvil SRNI

**Tecnología:** React Native + Expo SDK 54  
**Enrutamiento:** Expo Router (file-based routing)  
**Estado:** En desarrollo activo  
**Última actualización:** 2026-05-06

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
    │   ├── [temaId].tsx                ✅ Motor de preguntas + skip logic offline
    │   ├── consentimiento-ia.tsx       ✅ Consentimiento para asistente IA
    │   ├── grabacion-entrevista.tsx    ❌ Pendiente (modo Gemini)
    │   └── revision-ia.tsx            ❌ Pendiente (modo Gemini)
    └── encuestas/
        ├── index.tsx                    ✅ Lista de sesiones de encuesta
        └── [sesionId].tsx              ✅ Detalle de sesión + navegación al formulario
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

### Modo Asistido Gemini (pendiente Sprint 7)

```
Tab Caracterizar → Seleccionar instrumento → Seleccionar hogar → Crear sesión
  → Formulario: selector "Manual / Asistido por IA"
  → Grabar entrevista del capítulo completo (grabacion-entrevista.tsx)
  → POST /api/ia/procesar-entrevista/ → Gemini extrae respuestas
  → Revisar y confirmar sugerencias (revision-ia.tsx)
  → Guardar respuestas confirmadas
```

---

## Stack técnico

| Componente | Tecnología |
|-----------|-----------|
| Framework | React Native + Expo SDK 54 |
| Routing | Expo Router (file-based) |
| UI | React Native Paper (estilo GOV.CO) |
| Estado global | Zustand (`authStore`, `syncStore`, `iaStore`) |
| HTTP | Axios + interceptores JWT |
| Almacenamiento local | expo-sqlite (schema offline, Migration V2) |
| IA asistente | Proxy Gemini vía backend Django |

---

## SQLite local — Schema V2 (Sprint 7)

Las tablas fueron recreadas con TEXT PKs (UUID) para alinear con los IDs del servidor.

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

-- Cola de sincronización
cola_sincronizacion -- operaciones pendientes con reintentos
```

**Tipos de operaciones en la cola:**
- `CREAR_HOGAR` — hogar creado offline
- `CREAR_SESION` — sesión creada offline
- `RESPONDER_PREGUNTA` — respuesta individual
- `FINALIZAR_SESION` — cierre de sesión

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

- Tokens JWT en memoria (Zustand) — nunca en AsyncStorage persistente
- Logout limpia Zustand + expo-sqlite
- Búsqueda RNI solo server-side, el cliente recibe resúmenes paginados
- Sin datos PII almacenados localmente en SQLite
- Interceptor Axios que añade `Authorization: Bearer` en cada request
- `allowBackup: false` en configuración de la app

---

## Pendientes de la app móvil

| Pendiente | Sprint | Prioridad |
|-----------|--------|-----------|
| Modo Gemini: grabación + revisión batch | Sprint 7 | Alta |
| Opciones en preguntas LISTA/RADIO de instrumentos V7 | Sprint 7 | Alta |
| Pantalla finalizar sesión desde formulario | Sprint 7 | Media |
| Pantalla de perfil del encuestador | Sprint 7 | Baja |
| Push notifications para asignaciones | Sprint 8 | Baja |
| Firma digital al cerrar encuesta | Sprint 8 | Media |

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
