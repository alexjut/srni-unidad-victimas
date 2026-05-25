# Sprint 14 — Flujo móvil cosido (sin botones sueltos)

**Branch:** `feature/sprint14-mobile-flujo-cosido`
**Estado:** ✅ Completo
**Inicio:** 2026-05-25
**Cierre:** 2026-05-25

---

## Motivación

Después del Sprint 12, el flujo móvil tenía **3 puntos sueltos** entre "conformar hogar" y "iniciar caracterización":

1. **`conformar.tsx`** creaba la sesión y saltaba directo al formulario — el usuario nunca veía un listado de caracterizaciones del hogar.
2. **`[hogarId].tsx`** (detalle) tenía DOS botones que hacían cosas parecidas:
   - "Crear entrevista" → `caracterizar/index`
   - "Ver sesiones de este hogar" → `encuestas?hogar=X` (mezclado con sesiones de otros hogares)
3. **`caracterizar/index.tsx`** tras crear la sesión saltaba directo al formulario sin pasar por el hub.

Resultado: no había un "lugar único" para ver todas las caracterizaciones de un hogar, y los botones se sentían sueltos.

---

## Objetivos del sprint

1. Crear el **hub de caracterizaciones por hogar** — una pantalla única que liste todas las caracterizaciones del hogar y permita crear nuevas.
2. Cosido del flujo: cada pantalla apunta al hub, no a destinos paralelos.
3. Eliminar la duplicación de botones en el detalle del hogar.

---

## Entregables

### Pantalla nueva — `app/(main)/hogares/[hogarId]/caracterizaciones.tsx`

Hub que el usuario ve tras conformar el hogar (o desde el detalle):

- **Resumen del hogar** (tarjeta): código corto, municipio, # integrantes, autorizado marcado con estrella.
- **Listado de caracterizaciones** (sesiones del hogar) con:
  - Nombre del instrumento + versión
  - Fecha de inicio
  - Chip de estado con color (INICIADA / EN_PROGRESO / COMPLETADA / SUSPENDIDA)
  - Barra de progreso con `%` completado
  - Encuestador asignado
  - Tap → navega al detalle de la sesión (`encuestas/[sesionId]`)
- **Empty state** cuando no hay caracterizaciones todavía.
- **Botón sticky inferior** "+ Nueva caracterización" → `caracterizar/index?hogarId=X`.
- **Pull to refresh** para recargar al volver de crear una sesión.
- **`useFocusEffect`** recarga automáticamente al volver de la creación.

Consume el endpoint `GET /api/hogares/{id}/` que desde el Sprint 13 incluye el array `sesiones[]` anidado — sin segundo round-trip.

### Reestructura de carpetas

Movido `app/(main)/hogares/[hogarId].tsx` → `app/(main)/hogares/[hogarId]/index.tsx` para permitir subrutas hermanas como `caracterizaciones.tsx`. Esto es el patrón estándar de Expo Router.

`_layout.tsx` ajustado:
```diff
- <Tabs.Screen name="hogares/[hogarId]" ... />
+ <Tabs.Screen name="hogares/[hogarId]/index" ... />
+ <Tabs.Screen name="hogares/[hogarId]/caracterizaciones" ... />
```

### `conformar.tsx` — ya no crea sesión directa

| Antes | Después |
|-------|---------|
| Botón **"Iniciar Entrevista"** | Botón **"Continuar a caracterizaciones"** |
| Llamaba a `encuestasApi.crear()` | Solo navega al hub |
| Iba directo al formulario `encuestas/[sesionId]` | Va al listado `hogares/[hogarId]/caracterizaciones` |
| Requería `instrumentoId` para habilitarse | Solo requiere que el hogar esté creado |

El instrumento ahora se elige en `caracterizar/index.tsx`, que es donde realmente debe estar esa decisión.

### `[hogarId]/index.tsx` — un solo botón unificado

| Antes | Después |
|-------|---------|
| "Crear entrevista" + "Ver sesiones de este hogar" (2 botones) | **"Ver caracterizaciones (N)"** (1 solo) |
| Iban a destinos distintos (`caracterizar` vs `encuestas?hogar=X`) | Va al hub `hogares/[hogarId]/caracterizaciones` |
| Sección titulada "Entrevista de caracterización" | "Caracterizaciones del hogar" |

Texto de ayuda contextual:
- Si no hay autorizado: "Primero confirma el autorizado del hogar…"
- Si `total_sesiones === 0`: "Aún no se ha iniciado ninguna caracterización…"
- Si hay sesiones: "Revisa el progreso, abre una existente o crea una nueva."

### `caracterizar/index.tsx` — vuelve al hub tras crear

| Antes | Después |
|-------|---------|
| Tras `encuestasApi.crear()` → `router.replace(encuestas/[sesionId])` | Tras crear → `router.replace(hogares/[hogarId]/caracterizaciones)` |
| Usuario llegaba directo al formulario | Usuario vuelve al hub y ve la nueva caracterización en la lista |

Esto evita el "vuelvo atrás y pierdo dónde estaba" que tenía el flujo anterior.

### Tipos

`srni-mobile/src/types/index.ts`: `HogarDetalle` ahora declara `sesiones: SesionResumen[]` y `total_miembros: number`. El backend ya los devolvía desde el Sprint 13 — solo faltaba reflejarlo en el cliente TypeScript.

---

## Flujo cosido — diagrama

```
Búsqueda RNI (busqueda.tsx)
   ↓ víctima habilitada
hogares/conformar.tsx
   ↓ "Continuar a caracterizaciones"
hogares/[hogarId]/caracterizaciones.tsx        ← HUB nuevo
   ├─ Tap en una caracterización  → encuestas/[sesionId]/  (formulario)
   └─ "+ Nueva caracterización"  → caracterizar/index
                                       ↓ instrumento + ruta
                                    crea sesión
                                       ↓
                                    vuelve al HUB con la sesión nueva visible
```

Desde el detalle del hogar:
```
hogares/[hogarId]/index.tsx
   ↓ "Ver caracterizaciones (N)"
hogares/[hogarId]/caracterizaciones.tsx
```

---

## Decisiones técnicas

### 1. Por qué el hub y no la pantalla directa al formulario

El usuario reportó que el flujo "saltaba" al formulario sin darle oportunidad de revisar qué caracterizaciones tenía el hogar. Un hogar puede tener varias caracterizaciones (una por instrumento, o re-aplicación con instrumento actualizado). El hub:
- Da contexto: "para este hogar ya hay 2 caracterizaciones, una completa y otra al 40%".
- Permite reanudar la que está al 40% en lugar de crear una nueva por error.
- Centraliza el punto de entrada — ya no hay dos rutas paralelas.

### 2. Por qué `useFocusEffect` para recargar

Tras crear una caracterización, `router.replace` regresa al hub. Si solo usáramos `useEffect`, el componente no se re-monta, así que la nueva sesión no aparecería hasta refrescar. `useFocusEffect` corre cada vez que la pantalla vuelve a tener foco, así que la lista siempre está fresca.

### 3. Pull to refresh adicional

Por si la red estaba lenta al volver y la lista quedó desactualizada. Cero costo de UX porque es el patrón nativo de iOS/Android.

### 4. Subrutas con Expo Router

Expo Router file-based routing permite `app/(main)/hogares/[hogarId]/caracterizaciones.tsx` como hermana de `index.tsx` dentro del directorio `[hogarId]`. Esto requiere convertir el archivo `[hogarId].tsx` a la forma `[hogarId]/index.tsx` — la ruta efectiva sigue siendo `/(main)/hogares/[hogarId]` sin cambios para los `router.push` existentes.

### 5. No se tocó el backend

El endpoint `GET /api/hogares/{id}/` ya devuelve `sesiones[]` anidado desde el Sprint 13. No fue necesario añadir nada en el backend. Tampoco se tocó `srni-frontend/` (responsabilidad de Brando).

---

## Archivos creados / modificados

### Nuevos
```
srni-mobile/app/(main)/hogares/[hogarId]/caracterizaciones.tsx
docs/sprints/sprint-14.md
```

### Movidos / renombrados
```
srni-mobile/app/(main)/hogares/[hogarId].tsx
  → srni-mobile/app/(main)/hogares/[hogarId]/index.tsx
```

### Modificados
```
srni-mobile/app/(main)/_layout.tsx              (rutas hijas)
srni-mobile/app/(main)/hogares/conformar.tsx    ("Iniciar Entrevista" → hub)
srni-mobile/app/(main)/hogares/[hogarId]/index.tsx  (un solo botón)
srni-mobile/app/(main)/caracterizar/index.tsx   (vuelve al hub tras crear)
srni-mobile/src/types/index.ts                  (HogarDetalle.sesiones)
```

---

## Verificación

- `npx tsc --noEmit` sobre el mobile: los únicos errores en archivos tocados son **pre-existentes** (`@expo/vector-icons`, `color` shorthand, `skipLogic.test`). Mis cambios no introducen errores nuevos.
- Backend intacto — `python manage.py check` no aplica porque no se modificó nada.

---

## Pendientes para el próximo sprint

| Pendiente | Prioridad |
|-----------|-----------|
| Arreglar tests pre-existentes con imports obsoletos (`Perfil`, `InstrumentoVersion`) | Media |
| Migrar mock víctimas → `OracleVictimaRepository` real | Alta |
| Pre-seleccionar instrumento en `caracterizar/index` si viene del store | Baja (nice to have) |
| Firma digital del encuestador al cerrar sesión (mobile) | Media |
| Push notifications de asignaciones (mobile) | Baja |
| Pruebas de carga con Locust | Media |
