# Sprint 10 — Reportes de Producción

**Branch:** `feature/sprint10-reportes-produccion`  
**Estado:** ✅ Completo  
**Inicio:** 2026-05-14  
**Cierre:** 2026-05-16

---

## Objetivos del sprint

1. Backend: endpoints de producción por encuestador (resumen, detalle paginado, export CSV)
2. Mobile: pantalla de reportes con métricas, progreso por instrumento y export
3. Selector de período (semana / mes / todo)

---

## Tareas completadas

| Tarea | Archivos clave | Notas |
|-------|---------------|-------|
| App Django `reportes` con URLs | `apps/reportes/` | `urls.py`, `views.py`, `serializers.py` |
| Endpoint resumen de producción | `GET /api/reportes/produccion/` | Totales, por estado, por instrumento |
| Endpoint detalle paginado | `GET /api/reportes/produccion/detalle/` | 20/pág, filtro por estado |
| Export CSV streaming | `GET /api/reportes/produccion/export/` | `StreamingHttpResponse` — sin carga en memoria |
| URL registrada en `srni/urls.py` | `srni/urls.py` | `path('api/reportes/', ...)` |
| API client móvil | `src/api/reportes.ts` | `resumen()`, `detalle()`, `exportUrl()` |
| Pantalla `reportes.tsx` | `app/(main)/reportes.tsx` | Métricas, progress bars, sesiones recientes |

---

## Decisiones técnicas

### Scoping por encuestador (Row-level security)

Todos los endpoints filtran por el usuario autenticado:

```python
def _sesiones_periodo(encuestador, desde, hasta):
    qs = SesionEncuesta.objects.filter(encuestador=encuestador)
    if desde:
        qs = qs.filter(fecha_inicio__date__gte=desde)
    if hasta:
        qs = qs.filter(fecha_inicio__date__lte=hasta)
    return qs
```

Un encuestador solo puede ver sus propias sesiones. No existe endpoint de "todas las sesiones" para el rol encuestador.

### Export CSV streaming — sin carga en memoria

Para evitar timeouts en exports grandes (encuestadores con miles de sesiones):

```python
class _Echo:
    def write(self, value):
        return value

def produccion_export_csv(request):
    writer = csv.writer(_Echo())
    rows = (writer.writerow(row) for row in _generar_filas(sesiones))
    response = StreamingHttpResponse(rows, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte.csv"'
    return response
```

### Estructura del resumen

```json
{
  "total": 42,
  "completadas": 28,
  "en_progreso": 10,
  "sin_iniciar": 4,
  "hogares_caracterizados": 31,
  "respuestas_total": 4820,
  "promedio_completado": 78.3,
  "por_instrumento": [
    { "instrumento": "TERRITORIAL V7", "total": 18, "completadas": 14 }
  ],
  "sesiones_recientes": [...]
}
```

### Pantalla móvil — período y export

```ts
// reportes.tsx
const exportUrl = reportesApi.exportUrl({ desde, hasta });
await Linking.openURL(exportUrl); // abre el CSV en el navegador del dispositivo
```

El período se calcula localmente:

| Opción | `desde` |
|--------|---------|
| semana | `new Date(now - 7 * 86400000)` |
| mes | `new Date(now - 30 * 86400000)` |
| todo | `undefined` |

---

## Archivos creados / modificados

| Archivo | Cambio |
|---------|--------|
| `srni-backend/apps/reportes/__init__.py` | NUEVO |
| `srni-backend/apps/reportes/apps.py` | NUEVO |
| `srni-backend/apps/reportes/serializers.py` | NUEVO — `ResumenInstrumentoSerializer`, `ProduccionEncuestadorSerializer` |
| `srni-backend/apps/reportes/views.py` | NUEVO — 3 funciones: resumen, detalle, export |
| `srni-backend/apps/reportes/urls.py` | NUEVO |
| `srni-backend/srni/urls.py` | Registra `api/reportes/` |
| `srni-mobile/src/api/reportes.ts` | NUEVO |
| `srni-mobile/app/(main)/reportes.tsx` | NUEVO — pantalla completa con métricas |

---

## Endpoints nuevos

| Método | URL | Descripción |
|--------|-----|-------------|
| `GET` | `/api/reportes/produccion/` | Resumen del encuestador autenticado |
| `GET` | `/api/reportes/produccion/detalle/` | Sesiones paginadas (`?page=1&estado=completada`) |
| `GET` | `/api/reportes/produccion/export/` | Descarga CSV streaming (`?desde=&hasta=`) |

---

## Tareas → Sprint 11

| Tarea | Prioridad |
|-------|-----------|
| Throttling DRF: login, búsqueda RNI, IA | Alta |
| Reemplazar `eval()` en skip logic con evaluador AST | Alta |
| `max_length` en serializers de respuestas | Alta |
| DATABASES producción con SSL y python-decouple | Alta |
| Nginx: HTTPS, TLS, CSP, rate limiting por zona | Alta |
| Auditoría CORS, RLS, variables de entorno | Media |
