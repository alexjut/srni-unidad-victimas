# Fix — Timeout en refresh de token (carga infinita al abrir hogar)

**Fecha:** 2026-07-03
**Rama:** `fix/timeout-refresh-token-precarga`
**Base:** `main` (ver nota de rama abajo)
**Estado:** implementado y probado localmente. **NO desplegado.** Va a Pruebas primero (gate: reconciliación UUID + checklist APK).
**Diagnóstico origen:** `docs/diagnostico/precarga-hogar-colgada.md`

---

## Qué se arregló

El síntoma reportado ("al abrir un hogar/caracterización la carga nunca termina, sin error") tiene como causa raíz que una petición de red podía **quedar colgada sin resolver ni rechazar**, dejando el spinner (`ActivityIndicator`) eterno. El punto exacto: el **refresh de token se hacía con `axios.post` crudo sin `timeout`**, así que ante un 401 + refresh colgado (red parcial / túnel ngrok lento) la promesa nunca settleaba y las pantallas gated en `cargando` no liberaban nunca.

### Cambio 1 — `src/api/client.ts`: timeout en el refresh
- Se agrega `timeout: 15000` al `axios.post('/api/auth/refresh/')`.
- Efecto: un refresh colgado ahora **aborta con `ECONNABORTED`** → cae al `catch` existente → `rejectQueue()` (ya presente) libera las peticiones concurrentes encoladas → cada pantalla resuelve su `catch`/`finally`. El spinner infinito se convierte en un error manejable (y el guard puede redirigir a login).
- No hay riesgo de loop: la petición original ya marca `_retry = true` antes del refresh.

### Cambio 1b — `src/api/client.ts`: loguear el fallo del refresh
- Antes, un timeout/fallo del refresh **pasaba desapercibido**: el 401 se excluye del `errorReporter` y el `catch` del refresh solo rechazaba en silencio — ocultando justamente los timeouts que colgaban la app.
- Ahora el `catch` del refresh reporta un `warn` con `code`/`status` (sin PII, nunca el token). Responde al punto 4 del encargo.

### Cambio 2 — `app/(main)/formulario/[temaId].tsx`: `try/finally` en la carga
- El `useEffect` de carga (captura por persona, la pantalla que lista integrantes) no tenía `finally`; el `.catch` solo cubría rechazos.
- Se envuelve el cuerpo en `try { … } catch { warn } finally { setCargando(false) }`, de modo que el spinner **siempre** se libera. Blindaje adicional al Cambio 1.

### Cambio 3 — `src/services/miembrosHogar.ts`: **sin cambio de código** (solo test)
- Confirmado: `cargarMiembrosHogar` va a red por `hogaresApi.detalle` → `apiClient.get` (que ya tiene `timeout: 15000`). Con el Cambio 1, un cuelgue por 401→refresh ahora **rechaza** y la función cae a su fallback de SQLite/caché en el `catch`, en vez de dejar la lista de integrantes vacía indefinidamente.
- Se agrega un **test de regresión** que simula el rechazo por timeout (`ECONNABORTED`) y verifica que cae al fallback de caché.

### Cambio 4 — Watchdog de UI (~20 s): **NO incluido** (pendiente documentado)
- El Cambio 1 ya convierte el cuelgue en error manejable, así que el watchdog es defensa en profundidad, no bloqueante. Se deja pendiente para no ampliar el alcance ni el riesgo de este PR. Recomendado como mejora posterior en las pantallas gated por red (detalle de hogar, hub, captura).

---

## Pruebas

- **Typecheck:** `tsc --noEmit` limpio.
- **Suite completa:** `jest` → **79 tests, 7 suites, todo verde** (incluye el nuevo test de timeout de `cargarMiembrosHogar` y los de sincronización).

### Nota sobre el test del interceptor (transparencia — punto 2 del encargo)
Se intentó un test de integración directo del interceptor de `client.ts` (simular refresh colgado y verificar `rejectQueue`). **No es ejecutable en este entorno de jest:** importar el `apiClient`/axios real crashea con `TypeError: Cannot cancel a stream that already has a reader` (bug del adapter `fetch` de axios v1 + polyfill de streams de `jest-expo`, en tiempo de import). Por eso **todas las demás suites mockean `../api/client`**. El comportamiento del fix queda cubierto por:
- El test downstream de `cargarMiembrosHogar` (rechazo por timeout → fallback), que es exactamente el efecto observable del fix.
- Typecheck de la firma del `axios.post` con `timeout`.
- Revisión manual del camino `catch → rejectQueue → reject`.

Para un test de integración real del interceptor haría falta tocar la config global de jest (mapear/parchear el adapter fetch de axios), lo que excede el alcance de bajo riesgo de este fix.

---

## Notas para revisión

**Rama base = `main`, no `develop`.** Al preparar la rama se detectó que **`develop` está 165 commits atrás de `main`** y ni siquiera contiene los archivos que este fix toca (p. ej. `src/services/miembrosHogar.ts` no existe en `develop`). El APK de producción/preview se construye desde el estado de `main`, así que basar el fix en `develop` habría arreglado una versión obsoleta que no corresponde al APK del reporte. Se basó en `main`. **Conviene alinear `develop` con `main` en el flujo de integración** (decisión de flujo, fuera de este fix).

**Trabajo previo commiteado aparte.** Los fixes de la sesión anterior (nombre de integrante en `[hogarId]/index.tsx` + sincronización de `AGREGAR_MIEMBRO` en una pasada, 18 tests) se commitearon por separado en `main` (`fix(hogares): …`), no mezclados con este PR.

**Esto es una MITIGACIÓN, no la solución definitiva del cuelgue.** Convierte el spinner infinito en un error manejable y evita que la lista de integrantes quede vacía para siempre. Pero **mientras el backend de pruebas siga detrás del túnel ngrok** (`EXPO_PUBLIC_API_URL=https://prod-caracterizacion.ngrok.app`), la lentitud y los cortes seguirán ocurriendo — ahora degradando a error/offline en vez de colgar. La estabilización real del entorno (mover a `caracterizacion.unidadvictimas.gov.co`, ya provisionado internamente) es tarea de infraestructura/OTI, aparte de este fix.

**No se tocó** `sincronizacion.ts`, `colaDao.ts`, `eas.json` ni las URLs de perfiles. **No se hizo push ni despliegue.**

---

## Archivos

| Archivo | Cambio |
|---|---|
| `srni-mobile/src/api/client.ts` | `timeout: 15000` en refresh + log del fallo de refresh |
| `srni-mobile/app/(main)/formulario/[temaId].tsx` | `try/finally` en el `useEffect` de carga |
| `srni-mobile/src/services/__tests__/miembrosHogar.test.ts` | test de regresión (timeout → fallback caché) |
