# Bitacora de Desarrollo — Panel Web (srni-frontend)

**Desarrollador:** Brandon
**Rama:** `frontend`
**Inicio:** 2026-05-27

---

## Dia 1 — 2026-05-27 | Setup del ambiente local

### Actividades realizadas

1. **Configuracion del repositorio**
   - Clone el repo y verifique los remotes (origin + azure)
   - Cambie a la rama `frontend` (`git checkout frontend`)
   - Verifique la estructura actual de `srni-frontend/`

2. **Levantamiento del frontend**
   - `pnpm install` — dependencias instaladas sin errores
   - `pnpm run dev` — Vite corriendo en `http://localhost:5173`
   - Stack confirmado: React 18 + Vite 5 + Tailwind CSS 3 + Zustand 4 + TypeScript

3. **Levantamiento del backend (para pruebas locales)**
   - Instale Python 3.13 (la 3.14 no es compatible con `psycopg-binary==3.2.3`)
   - Cree `.venv` con `py -3.13 -m venv .venv`
   - `pip install -r requirements.txt` + `pip install drf-spectacular` (faltaba)
   - Configure `.env` con clave Fernet para cifrado de campos PII
   - `python manage.py migrate` — todas las migraciones OK (SQLite dev)
   - `python manage.py crear_usuario_prueba` — usuario ENCUESTADOR001 creado

4. **Carga de datos de prueba**
   - Parametricas: 8 tipos documento, 33 departamentos, 33 municipios, 21 DTs, 37 puntos atencion
   - 8 instrumentos cargados (ASISTENCIA, TERRITORIAL, BUENAVENTURA, SAN_ANDRES, URBANO_ETNICO, RURAL_ETNICO, TELEFONICO, VICTIMAS_EXTERIOR)
   - Datos ficticios: 12 victimas, 6 hogares, 15 sesiones, 1032 respuestas

5. **Verificacion end-to-end**
   - Login con ENCUESTADOR001 / SrniTest2026! — OK
   - Dashboard muestra metricas reales del API
   - Endpoints de reportes, hogares y encuestas responden 200

### Estado actual de srni-frontend/

| Componente | Archivo | Estado |
|-----------|---------|--------|
| Login | `src/pages/Login.tsx` | Funcional |
| Dashboard | `src/pages/Dashboard.tsx` | Funcional — muestra metricas |
| Hogares | `src/pages/Hogares.tsx` | Tabla paginada (sin vista detalle) |
| Encuestas | `src/pages/Encuestas.tsx` | Tabla paginada (sin vista detalle) |
| Reportes | `src/pages/Reportes.tsx` | Tarjetas resumen + tabla + CSV |
| Layout | `src/components/MainLayout.tsx` | Sidebar GOV.CO basico |
| Auth Store | `src/stores/authStore.ts` | Zustand con tokens en sessionStorage |
| API Client | `src/api/client.ts` | Axios con interceptor JWT + auto-refresh |

### Problemas encontrados y resueltos

| Problema | Solucion |
|----------|----------|
| Python 3.14 no compatible con `psycopg-binary==3.2.3` | Instale Python 3.13 en paralelo |
| `drf-spectacular` no estaba en `requirements.txt` | `pip install drf-spectacular` manualmente |
| `FIELD_ENCRYPTION_KEY` vacia en `.env` | Genere clave Fernet para desarrollo |
| Dashboard mostraba ceros | Cargue datos de prueba locales |

### Nota para Javier
- No modifique ningun archivo del backend ni del mobile
- Los datos de prueba estan solo en mi `db.sqlite3` local
- El `.env` tiene valores de desarrollo, no de produccion

---

## Plan de trabajo — Proximos pasos

Basado en el plan de 7 fases definido para el frontend:

### Fase 1 — Componentes base e infraestructura UI — COMPLETADA 2026-05-31
- [x] ~~Instalar dependencias: sonner, date-fns~~ (react-hook-form y zod pendientes para Fase 6)
- [x] ~~13 componentes UI: Button, Input, Select, Table, Modal, Card, Alert, Breadcrumb, Badge, Spinner, EmptyState, Pagination, PageHeader~~
- [x] ~~MainLayout: sidebar independiente, header desktop, indicador activo mejorado, drawer mobile~~
- [x] ~~Refactor 6 paginas: Dashboard, Hogares, Encuestas, Reportes, HogarDetalle, SesionDetalle~~
- [x] ~~Fix perfil usuario al refrescar pagina~~ (RequireAuth carga perfil automaticamente)
- [x] ~~Manejo global de errores: Error boundary, toasts en errores API, pagina 404~~

### Fase 2 — Vistas de detalle — COMPLETADA 2026-05-29
- [x] ~~HogarDetalle (`/hogares/:id`) — datos + miembros + sesiones~~
- [x] ~~SesionDetalle (`/encuestas/:id`) — info + respuestas + link a hogar~~
- [x] ~~Filtros y busqueda en tablas existentes (Hogares: busqueda + estado, Encuestas: estado)~~
- [x] ~~Filas clickeables + boton "Ver detalle" en Hogares y Encuestas~~

### Fase 3 — Busqueda de victimas
- [ ] Pagina Victimas (`/victimas`) — formulario busqueda + resultado
- [ ] VictimaDetalle (`/victimas/:id`) — datos PII + hogares + sesiones

### Fase 4 — Panel de supervision
- [ ] Dashboard de Supervision (`/supervision`) — metricas por encuestador
- [ ] Graficas de produccion (series temporales)

### Fase 5 — Instrumentos y parametricas
- [ ] Pagina Instrumentos (`/instrumentos`) — arbol capitulos/preguntas
- [ ] Pagina Parametricas (`/parametricas`) — cascada depto > municipio > vereda

### Fase 6 — Auditoria y seguridad
- [ ] Pagina Auditoria (`/auditoria`) — logs inmutables
- [ ] Cambiar contrasena (`/perfil/cambiar-password`)

### Fase 7 — Pulido y calidad
- [ ] Responsive design
- [ ] Accesibilidad (WCAG AA)
- [ ] Testing (Vitest + Playwright)
- [ ] Build de produccion

---

## Dia 2 — 2026-05-27 | Responsive y fix perfil usuario

### Actividades realizadas

1. **MainLayout responsive (sidebar → drawer mobile)**
   - Desktop (>=1024px): sidebar fijo a la izquierda, sin cambios
   - Mobile/tablet (<1024px): sidebar oculto, topbar azul con hamburguesa, drawer deslizable con overlay
   - Drawer se cierra al navegar o tocar el overlay
   - Se extrajo `SidebarContent` como componente interno para no duplicar codigo

2. **Dashboard responsive**
   - Cards: 1 columna en mobile, 2 en tablet, 4 en desktop (antes era 2 en mobile, quedaban apretadas)
   - Header: boton "Actualizar" debajo del saludo en mobile, en linea en desktop
   - Padding y tipografia ajustados por breakpoint

3. **Fix: perfil de usuario no se cargaba al refrescar pagina**
   - Problema: `usuario` en Zustand se perdia al refrescar (solo tokens se restauran de sessionStorage)
   - Dashboard mostraba "Hola, — " en vez del nombre real
   - Solucion: `RequireAuth` ahora llama a `GET /api/auth/perfil/` cuando hay tokens pero no hay usuario
   - Muestra spinner mientras carga, hace logout si el token expiro

4. **Restriccion de zona de trabajo documentada**
   - Se agrego aviso en PLAN-FRONTEND-PUBLICO.md, SETUP-BRANDON.md e INFORME-ANALISIS-PROYECTO.md
   - Solo se trabaja en `srni-frontend/`, no se toca backend, mobile ni infra

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/components/MainLayout.tsx` | Sidebar responsive: fijo en desktop, drawer en mobile |
| `src/pages/Dashboard.tsx` | Grid responsive + header responsive |
| `src/App.tsx` | RequireAuth carga perfil al refrescar pagina |

---

## Dia 3 — 2026-05-29 | Fase 1 (bloques A+B) + Fase 2 completa

### Actividades realizadas

1. **Dependencias instaladas**
   - `sonner` (v2.0.7) — toasts globales
   - `date-fns` (v4.3.0) — formateo de fechas

2. **Fase 1 — Componentes base e infraestructura**
   - `ErrorBoundary.tsx` — captura errores React, UI amigable + detalle en DEV
   - `NotFound.tsx` — pagina 404 con icono y boton volver
   - `Spinner.tsx` — 3 tamaños (sm/md/lg), role="status" a11y
   - `Badge.tsx` — 5 variantes (verde, azul, rojo, gris, naranja), tipo exportado
   - `EmptyState.tsx` — icono + titulo + descripcion, aplicado en Hogares, Encuestas y Reportes
   - `Pagination.tsx` — anterior/siguiente, se oculta si ≤1 pagina, reemplaza paginacion duplicada
   - `PageHeader.tsx` — titulo + subtitulo + acciones, responsive
   - Toasts automaticos en interceptor Axios (sin conexion, 500, 403)
   - Toaster Sonner agregado en main.tsx

3. **Fase 2 — Vistas de detalle**
   - `HogarDetalle.tsx` — 4 InfoCards + datos hogar + tabla miembros + tabla sesiones clickeables
   - `SesionDetalle.tsx` — 4 InfoCards + barra progreso + info sesion + tabla respuestas + link a hogar
   - Rutas `/hogares/:id` y `/encuestas/:id` agregadas a App.tsx

4. **Fase 2 — Tablas interactivas y filtros**
   - Hogares: filas clickeables, boton "Ver detalle", filtro por estado, busqueda por codigo
   - Encuestas: filas clickeables, boton "Ver detalle", filtro por estado
   - EmptyState adaptativo (mensajes distintos con/sin filtros activos)
   - Boton "Limpiar" cuando hay filtros activos

5. **Tipos API actualizados con campos reales del backend**
   - `hogares.ts`: HogarResumen, MiembroResumen, SesionAnidada, HogarDetalle (campos verificados contra serializers)
   - `encuestas.ts`: SesionResumen, RespuestaEncuesta, SesionDetalle
   - `codigo_hogar` marcado como opcional (pendiente que Javier lo agregue al serializer)

6. **Datos de prueba variados en SQLite**
   - Hogares: 3 ACTIVO, 2 BORRADOR, 1 ARCHIVADO (antes todos ACTIVO)
   - Sesiones ya tenian variacion: 6 COMPLETADA, 4 EN_PROGRESO, 2 INICIADA, 3 SUSPENDIDA

### Archivos creados

| Archivo | Descripcion |
|---------|-------------|
| `src/components/ErrorBoundary.tsx` | Error boundary React |
| `src/components/ui/Spinner.tsx` | Spinner con 3 tamaños |
| `src/components/ui/Badge.tsx` | Badge con 5 variantes |
| `src/components/ui/EmptyState.tsx` | Estado vacio reutilizable |
| `src/components/ui/Pagination.tsx` | Paginacion reutilizable |
| `src/components/ui/PageHeader.tsx` | Header de pagina reutilizable |
| `src/pages/NotFound.tsx` | Pagina 404 |
| `src/pages/HogarDetalle.tsx` | Detalle de hogar |
| `src/pages/SesionDetalle.tsx` | Detalle de sesion de encuesta |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/main.tsx` | Agrego ErrorBoundary + Toaster Sonner |
| `src/App.tsx` | Rutas /hogares/:id y /encuestas/:id, catch-all → NotFound |
| `src/api/client.ts` | Toasts automaticos en interceptor (sin conexion, 500, 403) |
| `src/api/hogares.ts` | Tipos actualizados con campos reales, param busqueda |
| `src/api/encuestas.ts` | SesionDetalle + RespuestaEncuesta, detalle con respuestas |
| `src/pages/Hogares.tsx` | Filtros, busqueda, filas clickeables, boton ver detalle |
| `src/pages/Encuestas.tsx` | Filtro estado, filas clickeables, boton ver detalle |
| `src/pages/Reportes.tsx` | Badge + EmptyState + Pagination + PageHeader aplicados |

### Nota para Javier
- `codigo_hogar` no esta en HogarListSerializer ni HogarDetalleSerializer. Se usa `id.slice(0,8)` como fallback. Pendiente agregarlo.
- No se modifico ningun archivo .py del backend. Solo se leyo/escribio la BD SQLite para variar datos de prueba.

---

## Dia 4 — 2026-05-31 | Fase 1 completada — componentes UI + refactor + layout

### Actividades realizadas

1. **8 componentes UI nuevos** (`src/components/ui/`)
   - `Button.tsx` — 4 variantes (primary/secondary/danger/ghost), 3 tamaños, loading spinner, icono
   - `Input.tsx` — forwardRef, label integrado, error, icono izquierdo. Listo para react-hook-form
   - `Select.tsx` — forwardRef, label, error, opciones tipadas con placeholder
   - `Table.tsx` — generico `<T>`, columnas declarativas, skeleton, empty state, paginacion, filas clickeables
   - `Modal.tsx` — overlay, cierre con Escape/click fuera, focus trap, bloqueo scroll body, slot acciones
   - `Card.tsx` — tarjeta metrica reutilizable (icono + valor + label)
   - `Alert.tsx` — 4 variantes (error/exito/info/warning) con icono automatico por variante
   - `Breadcrumb.tsx` — navegacion jerarquica con links y aria-label

2. **Refactor de 6 paginas existentes para usar componentes UI**
   - Dashboard: `MetricCard` inline → `Card`, error div → `Alert`, boton → `Button`
   - Hogares: tabla manual (~60 lineas) → `Table` con columnas declarativas, error → `Alert`, botones → `Button`
   - Encuestas: misma reduccion con `Table`, error → `Alert`, botones → `Button`
   - Reportes: error → `Alert`, boton exportar → `Button` con loading
   - HogarDetalle: error → `Alert`, botones → `Button`, agregado `Breadcrumb`
   - SesionDetalle: error → `Alert`, botones → `Button`, agregado `Breadcrumb`

3. **Layout mejorado**
   - Header fijo en desktop: barra blanca con seccion actual + nombre usuario + perfil + avatar con inicial
   - Indicador activo en sidebar: cambiado de `bg-white/15` a `bg-gov-azul shadow-sm` (mucho mas visible)
   - Sidebar extraido a componente independiente (`src/components/Sidebar.tsx`)
   - MainLayout simplificado: de ~177 lineas a ~100

### Archivos creados

| Archivo | Descripcion |
|---------|-------------|
| `src/components/ui/Button.tsx` | Boton reutilizable con variantes, tamaños, loading |
| `src/components/ui/Input.tsx` | Input con label, error, icono |
| `src/components/ui/Select.tsx` | Dropdown con label, error, opciones |
| `src/components/ui/Table.tsx` | Tabla generica con skeleton, empty state, paginacion |
| `src/components/ui/Modal.tsx` | Dialog reutilizable |
| `src/components/ui/Card.tsx` | Tarjeta metrica |
| `src/components/ui/Alert.tsx` | Alerta con 4 variantes |
| `src/components/ui/Breadcrumb.tsx` | Navegacion jerarquica |
| `src/components/Sidebar.tsx` | Sidebar independiente (extraido de MainLayout) |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/components/MainLayout.tsx` | Header desktop, sidebar independiente, simplificado |
| `src/pages/Dashboard.tsx` | Usa Card, Button, Alert |
| `src/pages/Hogares.tsx` | Usa Table, Button, Alert |
| `src/pages/Encuestas.tsx` | Usa Table, Button, Alert |
| `src/pages/Reportes.tsx` | Usa Button, Alert |
| `src/pages/HogarDetalle.tsx` | Usa Button, Alert, Breadcrumb |
| `src/pages/SesionDetalle.tsx` | Usa Button, Alert, Breadcrumb |

### Estado de la Fase 1

**COMPLETADA.** Todos los componentes UI del plan estan creados (13 total). Las 6 paginas existentes fueron refactorizadas para usarlos. El layout tiene header desktop y sidebar con indicador activo mejorado.

### Proximo paso: Fase 6 — Auditoria y seguridad

---

## Dia 5 — 2026-05-31 | Fases 3, 4 y 5 completadas

### Actividades realizadas

1. **Fase 3 — Busqueda de victimas**
   - `src/api/victimas.ts` — buscar (POST con hash SHA-256), detalle, registrar desde fuente, tipos documento
   - `src/pages/Victimas.tsx` — formulario busqueda + resultado enriquecido con DatoCards (genero, etnia, municipio, fecha) + hogar activo con contadores + 3 info cards en estado inicial + busquedas recientes en sessionStorage (max 5)
   - `src/pages/VictimaDetalle.tsx` — breadcrumb + datos PII + info complementaria + hechos victimizantes + metadata + manejo 403
   - Rutas `/victimas` y `/victimas/:id` en App.tsx, item "Victimas" en Sidebar

2. **Fase 4 — Panel de supervision**
   - Instalado `recharts` para graficas
   - `src/api/supervision.ts` — resumen supervisor + series temporales
   - `src/pages/Supervision.tsx` — 4 Cards totales + LineChart (actividad diaria) + BarChart horizontal (por instrumento) + tabla encuestadores con barras de progreso + filtros fecha (desde/hasta)
   - Ruta `/supervision` en App.tsx, item "Supervision" en Sidebar

3. **Fase 5 — Instrumentos y parametricas**
   - `src/api/formulario.ts` — instrumentos, capitulo detalle con preguntas y opciones
   - `src/pages/Instrumentos.tsx` — cards expandibles por instrumento, capitulos con carga lazy de preguntas, badges tipo/nivel, indicador obligatoria, preview de opciones (max 6)
   - Instalado `react-simple-maps` + `@types/react-simple-maps`
   - `src/api/parametricas.ts` — departamentos, municipios (paginado + todos), DTs, puntos atencion, tipos documento
   - `src/pages/Parametricas.tsx` — 5 tabs con tabs sticky:
     - Departamentos: mapa interactivo de Colombia (react-simple-maps) + tabla sincronizada + banner de seleccion + boton limpiar
     - Municipios: carga todos via `/municipios/todos/`, filtro local por departamento + badge filtro activo
     - Dir. Territoriales: busqueda por texto (nombre o codigo)
     - Puntos atencion: carga todos al inicio, filtro opcional por DT
     - Tipos documento: tabla con badges activo/inactivo
   - GeoJSON `colombia.json` movido de `src/` a `public/geo/` (1.7MB fuera del bundle)
   - Botones limpiar con icono papelera y estilo rojo, contenedor max-w-7xl
   - Rutas `/instrumentos` y `/parametricas` en App.tsx, items en Sidebar

4. **Correcciones durante desarrollo**
   - Supervision 403: activar `puede_ver_reportes=1` en perfil ENCUESTADOR (SQLite)
   - Victimas: descifrar documentos de prueba con Fernet para poder buscar
   - recharts: warning bundle >500KB (normal, optimizar en Fase 7)

### Archivos creados

| Archivo | Descripcion |
|---------|-------------|
| `src/api/victimas.ts` | API victimas: buscar, detalle, registrar, tipos documento |
| `src/api/supervision.ts` | API supervision: resumen supervisor, series temporales |
| `src/api/formulario.ts` | API formulario: instrumentos, capitulo detalle |
| `src/api/parametricas.ts` | API parametricas: deptos, municipios, DTs, puntos, tipos doc |
| `src/pages/Victimas.tsx` | Busqueda de victimas con resultado enriquecido |
| `src/pages/VictimaDetalle.tsx` | Detalle completo de victima |
| `src/pages/Supervision.tsx` | Panel de supervision con graficas recharts |
| `src/pages/Instrumentos.tsx` | Instrumentos con arbol capitulos/preguntas |
| `src/pages/Parametricas.tsx` | Parametricas con mapa Colombia + 5 tabs |
| `public/geo/colombia.json` | GeoJSON departamentos (movido desde src/) |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/App.tsx` | 6 rutas nuevas (victimas, victimas/:id, supervision, instrumentos, parametricas) |
| `src/components/Sidebar.tsx` | 3 items nuevos (Victimas, Supervision, Instrumentos, Parametricas) |

### Estado del frontend

| Tipo | Cantidad |
|------|----------|
| Paginas | 15 (13 funcionales + Login + NotFound) |
| API clients | 9 |
| Componentes UI | 13 |
| Componentes layout | 3 |
| Rutas | 13 + catch-all 404 |
| Nav items sidebar | 8 |

### Proximo paso: Fase 6 — Auditoria y seguridad

---

## Registro de cambios por dia

| Fecha | Que hice | Archivos tocados |
|-------|----------|-----------------|
| 2026-05-27 | Setup completo del ambiente local | Ninguno del repo (solo config local) |
| 2026-05-27 | Responsive layout + dashboard + fix perfil usuario | MainLayout.tsx, Dashboard.tsx, App.tsx |
| 2026-05-29 | Fase 1 (componentes UI + errores) + Fase 2 (detalle + filtros) | 9 archivos creados, 8 modificados |
| 2026-05-31 | Fase 1 completada: 8 componentes UI + refactor 6 paginas + layout mejorado | 9 archivos creados, 7 modificados |
| 2026-05-31 | Fases 3-5: victimas + supervision + instrumentos + parametricas con mapa | 10 archivos creados, 2 modificados |

---

*Documento de seguimiento para el ingeniero lider (Javier Alexander Aguilar)*
