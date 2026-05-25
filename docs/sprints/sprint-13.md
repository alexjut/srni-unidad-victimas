# Sprint 13 — Backend Habilitador para Panel Web

**Branch:** `feature/sprint13-backend-habilitador`
**Estado:** ✅ Completo
**Inicio:** 2026-05-25
**Cierre:** 2026-05-25

---

## Contexto

El Sprint 12 cerró con el scaffold del panel web (`srni-frontend/`) en su lugar. A partir de este sprint **la división de trabajo es clara**:

| Persona | Área | Rama |
|---------|------|------|
| Javier (Claude) | Backend, BD, APK móvil, infra, docs | `feature/sprint<N>-<tema>` |
| Brando | Panel web (`srni-frontend/`) | Rama propia (no fusionada todavía) |

Este Sprint 13 es **backend habilitador**: dejo el backend listo con todo lo que el panel web va a necesitar — endpoints, filtros, paginación, serializers enriquecidos — para que Brando los encuentre listos cuando avance con sus pantallas.

NO se tocó nada de `srni-frontend/`.

---

## Objetivos del sprint

1. Ampliar `HogarDetalleSerializer` con `sesiones` anidadas (evitar segundo round-trip desde el panel).
2. Implementar `HogarFilterSet` y `SesionEncuestaFilterSet` con `django-filter` — filtros server-side comunes.
3. Crear endpoint **vista supervisor** con métricas comparativas por encuestador.
4. Crear endpoint **dashboard/series** con serie temporal y distribución por instrumento.
5. Migrar listado de sesiones a **paginación cursor** (más estable bajo carga concurrente).
6. Actualizar `docs/backend/api-endpoints.md` como contrato claro para Brando.

---

## Entregables

### A1 · Detalle de hogar enriquecido

`HogarDetalleSerializer` ahora incluye:
- `sesiones`: lista anidada con `SesionEncuestaListSerializer` (instrumento, encuestador, porcentaje, fechas).
- `encuestador_nombre`: nombre completo de `creado_por`.

`HogarViewSet.get_queryset()` añade `prefetch_related('sesiones__instrumento__perfil', 'sesiones__encuestador')` para evitar N+1.

### A2 · `HogarFilterSet`

Archivo nuevo: `apps/hogares/filters.py`

Filtros server-side disponibles en `GET /api/hogares/`:

| Param | Lookup |
|-------|--------|
| `estado` | exact |
| `municipio` | exact (UUID) |
| `tipo_vivienda` | exact |
| `creado_por` | exact (UUID — encuestador) |
| `created_at_after` | `date__gte` |
| `created_at_before` | `date__lte` |
| `busqueda` | `icontains` en `codigo_hogar` OR `observaciones` |

Tests nuevos: 6 casos en `tests/test_hogares.py::TestHogarFilterSet`.

### A3 · `SesionEncuestaFilterSet`

Archivo nuevo: `apps/encuestas/filters.py`

Filtros server-side en `GET /api/encuestas/`:

| Param | Lookup |
|-------|--------|
| `estado` | exact |
| `instrumento` | exact (UUID) |
| `ruta_entrevista` | exact |
| `encuestador` | exact (UUID) |
| `hogar` | exact (UUID) |
| `fecha_inicio_after` | `date__gte` |
| `fecha_inicio_before` | `date__lte` |
| `porcentaje_min` | `>=` |
| `porcentaje_max` | `<=` |

### A4 · `GET /api/reportes/supervisor/`

Vista cross-encuestador con métricas agregadas en el período. Una fila por encuestador. Totales globales del equipo. Permiso `PuedeVerReportes` (perfil `puede_ver_reportes=True`).

Ver `docs/backend/api-endpoints.md` para el contrato JSON completo.

### A5 · `GET /api/reportes/dashboard/series/`

Series temporales para los gráficos del dashboard:

- **Serie diaria** del período (default últimos 30 días) con `sesiones_iniciadas` y `sesiones_completadas` por día. **Incluye días sin actividad con ceros** — el frontend no tiene que rellenar huecos.
- **Distribución por instrumento** — cuenta de sesiones agrupadas por `instrumento__codigo`.

Scope automático:
- `puede_administrar=True` → ve todo el equipo
- `puede_ver_reportes=True` solo → ve sus propias sesiones

### A6 · Paginación cursor

Archivo nuevo: `srni/pagination.py` con `CursorTimePagination` (basada en `-created_at`).

Aplicada a `SesionEncuestaViewSet`. El cliente recibe `next` / `previous` opacos y no necesita calcular offsets. Más estable que `PageNumberPagination` para listas que crecen rápido.

Listados pequeños (hogares, instrumentos) siguen con `PageNumberPagination` por simplicidad.

### A7 · Documentación de endpoints

`docs/backend/api-endpoints.md` actualizado con:
- Nueva sección **Reportes — Supervisor y Dashboard (Sprint 13)** con request/response examples
- Sección **Hogares** ampliada con filtros y respuesta JSON completa del detalle
- Sección **Encuestas** ampliada con filtros y nota de paginación cursor
- Corrección del JSON de "Crear hogar" — usa `autorizado` (no `jefe_hogar`)

---

## Decisiones técnicas

### 1. Sesiones anidadas en lugar de endpoint separado

Se podría haber expuesto `GET /api/hogares/{id}/sesiones/` como action aparte. Pero el panel web va a mostrar **siempre** el detalle del hogar con sus sesiones — separarlos generaría dos llamadas en cada apertura de pantalla. Con `prefetch_related` la diferencia de costo en backend es marginal y el frontend queda con un código mucho más simple.

### 2. `CursorPagination` solo en listados volátiles

`PageNumberPagination` es adecuado cuando el conjunto cambia poco y el usuario rara vez pagina más allá de la página 5 (ej. listado de hogares creados por un encuestador). En cambio, `SesionEncuesta` puede crecer 50–100 filas por día por encuestador; durante una sesión de revisión del panel, ordenar y paginar con offsets sobre filas que cambian produce duplicados o saltos.

Cursor estable basado en `-created_at` evita esto sin sacrificar performance.

### 3. Permiso `PuedeVerReportes` para supervisor

El supervisor no necesariamente es admin. Hay perfiles intermedios que ven reportes pero no editan paramétricas. Por eso los endpoints de S13 usan `PuedeVerReportes` (perfil `puede_ver_reportes=True`), no `PuedeAdministrar`. Un admin tiene ambos permisos por separado.

### 4. La serie diaria rellena días sin actividad

El backend devuelve un punto por cada día del rango (incluso con ceros) en lugar de solo los días con datos. Esto:
- Simplifica el código del gráfico (no `forEach` con relleno de huecos)
- Evita que el chart muestre líneas discontinuas
- Es barato — máximo 31 puntos para el período por defecto

### 5. Sin modelo `Perfil` en `apps.formulario`

El código existente usa `instrumento.perfil.codigo` con `hasattr` defensivo, pero el modelo `Instrumento` solo tiene `codigo`/`nombre`/`version` — no hay una relación `perfil`. Los endpoints S13 usan `instrumento.codigo` directamente (sin pasar por un `Perfil` que no existe). Esto evita devoluciones `None` falsas.

---

## Archivos creados / modificados

### Nuevos archivos
```
srni-backend/apps/hogares/filters.py         ← HogarFilterSet
srni-backend/apps/encuestas/filters.py       ← SesionEncuestaFilterSet
srni-backend/srni/pagination.py              ← CursorTimePagination
docs/sprints/sprint-13.md                    ← este documento
```

### Archivos modificados
```
srni-backend/apps/hogares/serializers.py     (+sesiones anidadas, +encuestador_nombre)
srni-backend/apps/hogares/views.py           (filterset_class + prefetch sesiones)
srni-backend/apps/encuestas/views.py         (filterset_class + CursorTimePagination)
srni-backend/apps/reportes/views.py          (+supervisor_reporte, +dashboard_series)
srni-backend/apps/reportes/serializers.py    (+4 serializers S13)
srni-backend/apps/reportes/urls.py           (+2 rutas)
srni-backend/tests/test_hogares.py           (+6 tests filtros)
docs/backend/api-endpoints.md                (S13 ampliado)
```

---

## Tests

```
tests/test_hogares.py        21 passed  (15 existentes + 6 nuevos del FilterSet)
tests/test_victimas.py       17 passed
tests/test_parametricas.py    4 passed
─────────────────────────────────────────
TOTAL                        42 passed  ✅
```

`python manage.py check` → `System check identified no issues (0 silenced).`

### Tests pre-existentes con imports obsoletos (NO bloqueante)

`tests/test_encuestas.py`, `tests/test_formulario.py`, `tests/test_ia.py` importan `Perfil` e `InstrumentoVersion` desde `apps.formulario.models`, pero el modelo real es `Instrumento` (sin `Perfil`/`InstrumentoVersion`). Este bug es **anterior al Sprint 13** y fue registrado como backlog para arreglar.

---

## Pendientes para Brando (lo que ya tiene listo del backend)

Brando, cuando llegues a estas pantallas, encontrarás el backend ya servido:

| Pantalla del panel | Endpoint backend listo |
|--------------------|------------------------|
| Detalle de hogar | `GET /api/hogares/{id}/` — incluye `miembros` y `sesiones` anidados |
| Listado de hogares con filtros | `GET /api/hogares/?estado=&municipio=&...` |
| Detalle de sesión | `GET /api/encuestas/{id}/` (existente) + `GET /api/encuestas/{id}/respuestas/` |
| Listado de sesiones con filtros | `GET /api/encuestas/?estado=&instrumento=&...` con cursor |
| Vista Supervisor | `GET /api/reportes/supervisor/` |
| Gráficos del dashboard | `GET /api/reportes/dashboard/series/` |

Cualquier campo adicional que falte, lo agrego cuando pidas. El contrato JSON está en `docs/backend/api-endpoints.md`.

---

## Backlog próximo sprint

| Tema | Prioridad |
|------|-----------|
| Arreglar tests pre-existentes con imports obsoletos | Media |
| Reemplazar mock víctimas con OracleVictimaRepository real (INH_REPORTE_GAVE) | Alta |
| Firma digital del encuestador al cerrar sesión (mobile) | Media |
| Push notifications de asignaciones (mobile) | Baja |
| Pruebas de carga con Locust | Media |
| Auditoría externa de pen-test (preparación) | Alta (antes de pre-producción) |
