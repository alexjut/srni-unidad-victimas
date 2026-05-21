# Sprint 8 — Motor de Formulario End-to-End

**Branch:** `feature/sprint8-motor-formulario`  
**Estado:** ✅ Completo  
**Inicio:** 2026-05-07  
**Cierre:** 2026-05-10

---

## Objetivos del sprint

1. Carga de respuestas previas al entrar a un capítulo (no empezar desde cero)
2. Validación de preguntas obligatorias antes de avanzar/finalizar
3. Sincronización bulk al guardar capítulo (`RESPONDER_BULK`)
4. Progreso real por capítulo calculado desde la BD
5. Corrección de nombre dinámico del instrumento en pantalla de sesión

---

## Tareas completadas

| Tarea | Archivos clave | Notas |
|-------|---------------|-------|
| Carga de respuestas previas en `[temaId].tsx` | `formulario/[temaId].tsx` | Lee `borradoresDao` al montar capítulo |
| Validación de obligatorias antes de guardar | `formulario/[temaId].tsx` | Muestra lista de preguntas sin responder |
| Bulk sync al guardar capítulo | `encuestasApi.responderBulk()` | Un POST en lugar de N POSTs individuales |
| `porcentaje_completado` real en backend | `encuestas/views.py` | Calcula `respuestas / preguntas_activas` |
| Fix: nombre dinámico del instrumento | `encuestas/[sesionId].tsx` | Elimina texto hardcodeado "PAARI" |

---

## Decisiones técnicas

### Bulk sync por capítulo

Antes del Sprint 8 cada respuesta se enviaba en un POST individual. Ahora al presionar "Guardar capítulo" se empaquetan todas las respuestas del capítulo en un solo `POST /api/encuestas/{id}/responder-bulk/`.

**Ventaja:** Reduce N round-trips a 1. Crítico en zonas con alta latencia (campo).

```ts
// guardarYVolver() en [temaId].tsx
const arr = Object.entries(respuestas)
  .map(([pregunta_id, valor]) => ({ pregunta_id, valor }))
  .filter(r => r.valor.trim() !== '');

await encuestasApi.responderBulk(sesionServerId, arr);
```

### Carga de respuestas previas (offline-first)

El DAO `borradoresDao` actúa como fuente de verdad local. Al entrar al capítulo se cargan primero los borradores locales; las respuestas del servidor se sincronizan en segundo plano.

```ts
const previas = await borradoresDao.obtenerRespuestasPorCapitulo(borradorId, capituloId);
setRespuestas(Object.fromEntries(previas.map(r => [r.pregunta_id, r.valor])));
```

### Fix nombre instrumento

`[sesionId].tsx` mostraba "PAARI" hardcodeado. Corregido a:

```tsx
label={`Continuar formulario${sesion.instrumento_nombre ? ` — ${sesion.instrumento_nombre}` : ''}`}
```

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `srni-mobile/app/(main)/formulario/[temaId].tsx` | Carga previa, validación, bulk sync |
| `srni-mobile/app/(main)/encuestas/[sesionId].tsx` | Nombre dinámico del instrumento |
| `srni-backend/apps/encuestas/views.py` | `porcentaje_completado` calculado en backend |

---

## Tareas → Sprint 9

| Tarea | Prioridad |
|-------|-----------|
| Cola robusta con reintento exponencial | Alta |
| Tipo `RESPONDER_BULK` en cola de sincronización | Alta |
| Polling de conectividad cada 60s | Alta |
| Path offline al guardar capítulo sin conexión | Alta |
| Pantalla sync-status | Media |
