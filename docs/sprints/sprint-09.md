# Sprint 9 — Sincronización Masiva Robusta

**Branch:** `feature/sprint9-sincronizacion-masiva`  
**Estado:** ✅ Completo  
**Inicio:** 2026-05-11  
**Cierre:** 2026-05-13

---

## Objetivos del sprint

1. Cola de sincronización con reintentos y backoff exponencial
2. Tipo `RESPONDER_BULK` en la cola (N respuestas por capítulo en un ítem)
3. Detección reactiva de conectividad con polling cada 60 s
4. Path offline al guardar capítulo (encola en lugar de fallar)
5. Pantalla `sync-status` con estado de la cola en tiempo real

---

## Tareas completadas

| Tarea | Archivos clave | Notas |
|-------|---------------|-------|
| Migration V3 SQLite: columna `retry_after` | `db/schema.ts` | `SCHEMA_VERSION = 3` |
| Reescritura de `colaDao.ts` | `db/colaDao.ts` | Backoff, `RESPONDER_BULK`, `reintentarErrores()` |
| Reescritura de `sincronizacion.ts` | `services/sincronizacion.ts` | `procesarResponderBulk()`, inyección de `sesion_id` |
| Reescritura de `syncStore.ts` | `stores/syncStore.ts` | Polling 60s, detección vuelta-a-online |
| Path offline en `[temaId].tsx` | `formulario/[temaId].tsx` | Encola RESPONDER_BULK si sin conexión |
| Nueva pantalla `sync-status.tsx` | `app/(main)/sync-status.tsx` | Pull-to-refresh, reintentar errores, limpiar enviados |
| Rutas ocultas en `_layout.tsx` | `app/(main)/_layout.tsx` | `href: null` para sync-status y reportes |
| Dashboard: accesos rápidos a sync y reportes | `app/(main)/index.tsx` | Chip de estado + AccionRow |

---

## Decisiones técnicas

### Backoff exponencial en `colaDao.marcarError()`

| Intento | Espera | Estado final |
|---------|--------|-------------|
| 1 | +30 s | pendiente (retry_after) |
| 2 | +120 s | pendiente (retry_after) |
| 3+ | — | error definitivo |

```ts
// colaDao.ts
const esperas = [30, 120];
const segundos = esperas[item.intentos] ?? null;
if (segundos === null) {
  await db.runAsync(`UPDATE cola_sincronizacion SET estado='error' WHERE id=?`, [item.id]);
} else {
  const retryAfter = new Date(Date.now() + segundos * 1000).toISOString();
  await db.runAsync(
    `UPDATE cola_sincronizacion SET estado='pendiente', retry_after=? WHERE id=?`,
    [retryAfter, item.id]
  );
}
```

### Tipo `RESPONDER_BULK` en la cola

Agrupa todas las respuestas de un capítulo en un solo ítem de cola. Cuando el ítem se procesa, busca el `sesion_id` del servidor (puede que la sesión aún no haya sido creada en servidor).

```ts
// procesarResponderBulk() — sincronizacion.ts
if (!payload.sesion_id) throw new Error('sesion_id no disponible aún');
const respuestas = payload.respuestas.filter(r => r.valor?.trim());
await encuestasApi.responderBulk(payload.sesion_id, respuestas);
```

La función `procesarCrearSesion()` inyecta el `sesion_id` recibido del servidor en todos los ítems `RESPONDER_BULK`, `RESPONDER_PREGUNTA` y `FINALIZAR_SESION` del mismo borrador.

### Polling reactivo de conectividad

```ts
// syncStore.ts — inicializar()
pollingInterval = setInterval(() => get().checkConnectivity(), 60_000);

// checkConnectivity() detecta transición offline → online
if (eraOffline && ahora_online) get().triggerSync();
```

No se usa `NetInfo` (dependencia adicional); en su lugar se hace un HEAD request liviano para verificar conectividad real al servidor.

### Path offline en `[temaId].tsx`

```ts
if (estaOnline) {
  await encuestasApi.responderBulk(sesionServerId, arr);
} else {
  await colaDao.encolar('RESPONDER_BULK', bid, {
    sesion_id: sesionServerId,
    borrador_id: bid,
    respuestas: arr,
  });
}
```

---

## Schema SQLite — Migration V3

```sql
ALTER TABLE cola_sincronizacion ADD COLUMN retry_after TEXT;
-- NULL = disponible ahora; valor ISO 8601 = esperar hasta esa fecha/hora
```

Consulta que respeta `retry_after`:
```sql
SELECT * FROM cola_sincronizacion
WHERE estado = 'pendiente'
  AND (retry_after IS NULL OR retry_after <= datetime('now'))
ORDER BY created_at ASC
LIMIT 10;
```

---

## Archivos creados / modificados

| Archivo | Cambio |
|---------|--------|
| `srni-mobile/src/db/schema.ts` | Migration V3: columna `retry_after` |
| `srni-mobile/src/db/colaDao.ts` | Reescritura completa con backoff y `RESPONDER_BULK` |
| `srni-mobile/src/services/sincronizacion.ts` | `procesarResponderBulk()`, inyección `sesion_id` |
| `srni-mobile/src/stores/syncStore.ts` | Polling 60s, `reintentarErrores()` |
| `srni-mobile/app/(main)/formulario/[temaId].tsx` | Path offline para RESPONDER_BULK |
| `srni-mobile/app/(main)/sync-status.tsx` | NUEVO — pantalla de estado de la cola |
| `srni-mobile/app/(main)/_layout.tsx` | Rutas ocultas sync-status y reportes |
| `srni-mobile/app/(main)/index.tsx` | Accesos dashboard + SyncChip |

---

## Tareas → Sprint 10

| Tarea | Prioridad |
|-------|-----------|
| Endpoint resumen de producción por encuestador | Alta |
| Endpoint detalle paginado de sesiones | Alta |
| Export CSV streaming | Media |
| Pantalla móvil de reportes con métricas | Alta |
