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

### Fase 3 — Busqueda de victimas — COMPLETADA 2026-05-31
- [x] ~~Pagina Victimas (`/victimas`) — formulario busqueda + resultado~~
- [x] ~~VictimaDetalle (`/victimas/:id`) — datos PII + hogares + sesiones~~

### Fase 4 — Panel de supervision — COMPLETADA 2026-05-31
- [x] ~~Dashboard de Supervision (`/supervision`) — metricas por encuestador~~
- [x] ~~Graficas de produccion (series temporales)~~

### Fase 5 — Instrumentos y parametricas — COMPLETADA 2026-05-31
- [x] ~~Pagina Instrumentos (`/instrumentos`) — arbol capitulos/preguntas~~
- [x] ~~Pagina Parametricas (`/parametricas`) — cascada depto > municipio > vereda~~

### Fase 6 — Auditoria y seguridad — COMPLETADA 2026-06-02
- [x] ~~Pagina Auditoria (`/auditoria`) — logs inmutables (adaptada a endpoint real de Javier)~~
- [x] ~~Cambiar contrasena (`/perfil/cambiar-password`) — react-hook-form + zod~~
- [x] ~~Logout real: POST `/api/auth/logout/` con blacklist de refresh token~~

### Fase 7 — Pulido y calidad — EN PROGRESO
- [x] ~~Accesibilidad parcial (skip-to-content, aria-labels, roles, htmlFor)~~
- [x] ~~Testing setup (Vitest + happy-dom + 9 tests)~~
- [x] ~~Correccion tsconfig: eliminar baseUrl deprecado~~
- [x] ~~UI filtros: Supervision y Auditoria con layout responsive correcto~~
- [ ] Responsive design completo (pendiente revision pagina por pagina)
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

### Proximo paso: completar Fase 6 (CambiarPassword + Logout real)

---

## Dia 6 — 2026-05-31 | Fase 6 parcial — Auditoria

### Actividades realizadas

1. **Pagina de Auditoria** (`src/pages/Auditoria.tsx`)
   - Tabla paginada con columnas: fecha, usuario, accion, recurso, resultado, IP, detalle
   - Filtros: accion (dropdown con acciones reales del backend), rango de fechas
   - Badges por tipo de accion (BUSQUEDA_RNI, VER_VICTIMA, LOGIN, etc.) y resultado (EXITO, ERROR, DENEGADO)
   - Nota de inmutabilidad visible
   - Boton limpiar filtros (rojo con icono papelera)

2. **API de Auditoria** (`src/api/auditoria.ts`)
   - Tipos basados en el modelo real `auditoria_logacceso` del backend
   - Campos: `codigo_usuario`, `accion`, `recurso`, `recurso_id`, `ip_origen`, `user_agent`, `resultado`, `detalle`, `timestamp`

3. **Hallazgo: endpoint no implementado en backend**
   - El modelo `auditoria_logacceso` existe y tiene 10 registros reales
   - Pero `serializers.py`, `views.py` y `urls.py` de la app auditoria estan vacios
   - La pagina muestra warning amigable y esta lista para funcionar cuando se implemente
   - **Accion requerida de Javier:** implementar `GET /api/auditoria/logs/` (solo lectura, paginado, con filtros)

### Archivos creados

| Archivo | Descripcion |
|---------|-------------|
| `src/api/auditoria.ts` | API auditoria: tipos + endpoint logs con filtros |
| `src/pages/Auditoria.tsx` | Vista de logs inmutables con tabla, filtros y paginacion |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/App.tsx` | Ruta `/auditoria` |
| `src/components/Sidebar.tsx` | Item "Auditoria" con icono Shield |

### Estado del frontend actualizado

| Tipo | Cantidad |
|------|----------|
| Paginas | 16 (14 funcionales + Login + NotFound) |
| API clients | 10 |
| Componentes UI | 13 |
| Componentes layout | 3 |
| Rutas | 14 + catch-all 404 |
| Nav items sidebar | 9 |

### Pendiente para continuar

- Fase 7 (restante): Responsive completo pagina por pagina + build produccion

---

## Dia 7 — 2026-06-02 | Fase 6 completada + Fase 7 parcial (a11y, testing, UI fixes)

### Actividades realizadas

1. **Fase 6 completada — Auditoria adaptada + CambiarPassword + Logout real**
   - Adaptacion de `src/api/auditoria.ts` al endpoint real de Javier: tipos actualizados (`accion_display`, `resultado_display`, `usuario_nombre`), 15 acciones, filtros resultado/codigo_usuario/search/ordering/page_size
   - `src/pages/Auditoria.tsx` — badges por accion y resultado, filtro resultado (dropdown), renderizado JSON detalle, columnas responsive
   - `src/api/auth.ts` — endpoints `logout` (POST con refresh token) y `cambiarPassword`
   - `src/pages/CambiarPassword.tsx` — formulario con react-hook-form + zod v4: validacion password_actual, password_nueva (min 8 + mayuscula + numero), confirmar (must match). Breadcrumb, Alert exito, manejo errores API
   - `src/components/MainLayout.tsx` — logout real (fire-and-forget POST antes de limpiar session) + skip-to-content link + `role="main"`
   - `src/components/Sidebar.tsx` — enlace "Cambiar contrasena" con icono KeyRound + `aria-label` en nav
   - `src/App.tsx` — ruta `/perfil/cambiar-password`
   - `src/api/hogares.ts` — `codigo_hogar` cambiado de opcional a requerido (Javier lo agrego al serializer)
   - `src/pages/Hogares.tsx` y `src/pages/HogarDetalle.tsx` — fallback `??` cambiado a `||` para codigo_hogar

2. **Fase 7 parcial — Accesibilidad**
   - `src/components/MainLayout.tsx` — skip-to-content (`sr-only focus:not-sr-only`), `<main id="main-content" role="main">`
   - `src/pages/Login.tsx` — `htmlFor`/`id` en inputs usuario y password, `aria-label` en boton toggle password
   - `src/pages/Parametricas.tsx` — `role="tablist"`, `role="tab"`, `aria-selected` en tabs
   - `src/components/Sidebar.tsx` — `aria-label="Menu principal"` en nav

3. **Fase 7 parcial — Testing**
   - Dependencias: `vitest@^2`, `@testing-library/react@14`, `@testing-library/user-event@14`, `@testing-library/jest-dom@6`, `happy-dom@20`
   - `vite.config.ts` — configuracion test (globals, happy-dom, setupFiles, css:false)
   - `src/test/setup.ts` — import jest-dom matchers para vitest
   - `src/vite-env.d.ts` — referencia tipos Vite (fix `import.meta.env`)
   - `src/components/ui/Button.test.tsx` — 5 tests (render, click, loading, disabled, variant danger)
   - `src/stores/authStore.test.ts` — 4 tests (init, setTokens, setUsuario, logout)
   - 9 tests pasando

4. **Correccion tsconfig.json**
   - Eliminado `baseUrl: "."` (deprecado en TS 5.9, causa error en TS 7.0)
   - `paths` cambiado de `"src/*"` a `"./src/*"` (funciona sin baseUrl)
   - Build limpio sin warnings de deprecacion

5. **UI/UX filtros — Supervision y Auditoria**
   - `src/pages/Supervision.tsx` — filtros en card dedicada con grid responsive (1/2/4 cols), botones Filtrar + Actualizar alineados a misma altura que inputs (`h-[38px]`), cards totales grid 1/2/4 cols
   - `src/pages/Auditoria.tsx` — filtros con layout flex (grid de inputs `flex-1` + botones compactos al lado), componente Button reutilizado (antes eran botones manuales), responsive mobile con botones full-width
   - `src/components/ui/Table.tsx` — skeleton rows respetan className de columna (para hidden responsive)

### Archivos creados

| Archivo | Descripcion |
|---------|-------------|
| `src/pages/CambiarPassword.tsx` | Formulario cambio contrasena con validacion zod |
| `src/test/setup.ts` | Setup vitest con jest-dom matchers |
| `src/vite-env.d.ts` | Referencia tipos Vite |
| `src/components/ui/Button.test.tsx` | 5 tests del componente Button |
| `src/stores/authStore.test.ts` | 4 tests del auth store |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `package.json` | +react-hook-form, +zod, +@hookform/resolvers, +vitest, +testing-library, +happy-dom |
| `pnpm-lock.yaml` | Lockfile actualizado |
| `tsconfig.json` | Eliminado baseUrl deprecado, paths relativo |
| `vite.config.ts` | Configuracion test vitest |
| `src/api/auth.ts` | Endpoints logout + cambiarPassword |
| `src/api/auditoria.ts` | Tipos adaptados a endpoint real, filtros nuevos |
| `src/api/hogares.ts` | codigo_hogar requerido |
| `src/App.tsx` | Ruta /perfil/cambiar-password |
| `src/components/MainLayout.tsx` | Logout real + skip-to-content + role main |
| `src/components/Sidebar.tsx` | Link cambiar contrasena + aria-label nav |
| `src/components/ui/Table.tsx` | Skeleton respeta className columna |
| `src/pages/Auditoria.tsx` | Adaptada a endpoint real + filtros flex layout |
| `src/pages/Supervision.tsx` | Filtros en card + grid responsive cards |
| `src/pages/Login.tsx` | htmlFor + aria-labels |
| `src/pages/Parametricas.tsx` | Tabs con roles ARIA |
| `src/pages/Hogares.tsx` | Fallback codigo_hogar |
| `src/pages/HogarDetalle.tsx` | Fallback codigo_hogar |

### Estado del frontend actualizado

| Tipo | Cantidad |
|------|----------|
| Paginas | 17 (15 funcionales + Login + NotFound) |
| API clients | 10 |
| Componentes UI | 13 |
| Componentes layout | 3 |
| Rutas | 15 + catch-all 404 |
| Nav items sidebar | 9 + link cambiar contrasena |
| Tests | 9 (5 Button + 4 authStore) |

### Nota para Javier
- Endpoint `GET /api/auditoria/logs/` ya implementado y conectado. Frontend funcional.
- `codigo_hogar` ya es requerido en el frontend (gracias por agregarlo al serializer).
- `POST /api/auth/logout/` y `POST /api/auth/cambiar-password/` conectados.

---

## Registro de cambios por dia

| Fecha | Que hice | Archivos tocados |
|-------|----------|-----------------|
| 2026-05-27 | Setup completo del ambiente local | Ninguno del repo (solo config local) |
| 2026-05-27 | Responsive layout + dashboard + fix perfil usuario | MainLayout.tsx, Dashboard.tsx, App.tsx |
| 2026-05-29 | Fase 1 (componentes UI + errores) + Fase 2 (detalle + filtros) | 9 archivos creados, 8 modificados |
| 2026-05-31 | Fase 1 completada: 8 componentes UI + refactor 6 paginas + layout mejorado | 9 archivos creados, 7 modificados |
| 2026-05-31 | Fases 3-5: victimas + supervision + instrumentos + parametricas con mapa | 10 archivos creados, 2 modificados |
| 2026-05-31 | Fase 6 parcial: auditoria (pagina lista, endpoint pendiente en backend) | 2 archivos creados, 2 modificados |
| 2026-06-02 | Fase 6 completada + Fase 7 parcial (a11y, testing, UI filtros) | 5 archivos creados, 17 modificados |

---

## Dia 8 — 2026-06-02 | Mejoras UI/UX globales — diseño Apple-style

### Actividades realizadas

1. **Layout: info usuario movida del Sidebar al Header**
   - Sidebar simplificado: solo logo GOV.CO + 9 nav items (sin info usuario, sin logout, sin cambiar contrasena)
   - Header desktop: dropdown con avatar + nombre + perfil + chevron animado. Al hacer clic abre menu con "Cambiar contrasena" y "Cerrar sesion"
   - Header mobile: avatar circular abre bottom sheet (panel desde abajo) con info usuario + acciones + boton cancelar
   - Bottom sheet con animacion slide-up, overlay, handle visual, touch targets grandes (py-3.5)

2. **Sistema de diseño global — Nivel 1 (base)**
   - `tailwind.config.ts`: sombras Apple multi-capa (shadow-soft, soft-md, soft-lg, soft-xl), 5 animaciones (fade-in, fade-in-up, scale-in, slide-down, slide-up), easing Apple + spring
   - `src/index.css`: font smoothing (antialiased), transiciones globales en elementos interactivos (200ms cubic-bezier Apple), focus ring azul suave con offset, scrollbar minimalista (6px), selection color institucional, clase page-content con fade-in-up
   - Botones: rounded-lg, shadow-soft, efecto press active:scale[0.97], disabled sin scale
   - Inputs: rounded-lg, hover border-gray-400, focus ring gov-azul/30
   - Cards: rounded-2xl, shadow-soft, border-gov-borde/60, nueva clase card-hover con lift
   - Badges: padding horizontal ampliado (px-2.5)

3. **Componentes UI mejorados — Nivel 2**
   - `Button.tsx`: shadow-soft en primary/danger, hover shadow-soft-md, active scale 0.97
   - `Card.tsx`: hover lift (-translate-y-0.5 + shadow-soft-md), icono rounded-2xl con shadow-soft
   - `Modal.tsx`: backdrop blur, animate scale-in, shadow-soft-xl, boton cerrar circular con hover bg-gray-100
   - `Table.tsx`: filas con animate-fade-in escalonado (delay 30ms por fila), skeletons con delay 50ms, bordes sutiles (/60 y /40), hover en todas las filas
   - `Alert.tsx`: borde lateral de color de acento (4px izquierda), rounded-xl, animate fade-in
   - `EmptyState.tsx`: contenedor 64px rounded-2xl, mas espaciado (py-16)
   - `Pagination.tsx`: botones ghost sin borde, hover azul tenue, numero pagina en bold
   - `Badge.tsx`: borde sutil semitransparente por variante
   - `Input.tsx`: icono cambia a azul en focus (peer-focus), input con clase peer
   - `PageHeader.tsx`: tracking-tight en titulo

4. **Transicion de paginas**
   - MainLayout: wrapper `<div key={location.pathname} className="page-content">` alrededor de Outlet
   - Cada cambio de ruta dispara animacion fade-in-up (sube 8px + opacidad 0.35s)

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `tailwind.config.ts` | Sombras soft, keyframes, animaciones, easing Apple/spring |
| `src/index.css` | Base global: font smoothing, transiciones, focus ring, scrollbar, selection, page-content |
| `src/components/Sidebar.tsx` | Simplificado: solo logo + nav (sin info usuario, sin logout) |
| `src/components/MainLayout.tsx` | Dropdown desktop + bottom sheet mobile + page-content wrapper |
| `src/components/ui/Button.tsx` | Shadow-soft, active scale, rounded-lg |
| `src/components/ui/Card.tsx` | Hover lift, icono rounded-2xl |
| `src/components/ui/Modal.tsx` | Backdrop blur, scale-in, shadow-soft-xl |
| `src/components/ui/Table.tsx` | Fade-in escalonado, bordes sutiles |
| `src/components/ui/Alert.tsx` | Borde lateral acento, rounded-xl |
| `src/components/ui/EmptyState.tsx` | Contenedor grande, mas espaciado |
| `src/components/ui/Pagination.tsx` | Botones ghost, hover azul |
| `src/components/ui/Badge.tsx` | Borde sutil semitransparente |
| `src/components/ui/Input.tsx` | Icono peer-focus azul |
| `src/components/ui/PageHeader.tsx` | Tracking-tight |

### Proximo paso: Nivel 3 — revision UI pagina por pagina

---

## Dia 9 — 2026-06-02 | Fase 7 completada — Nivel 3 UI + fixes API

### Actividades realizadas

1. **Nivel 3 — Revision UI pagina por pagina (15 paginas)**
   - Batch global aplicado en todas las paginas: `transition-all`, `divide-gov-borde/40`, `shadow-soft`, skeletons `bg-gray-200`
   - **Alta prioridad** — Parametricas: 4 botones rojos hardcodeados → `Button variant="danger"`, shadow-soft en mapa, bordes sutiles en banners, `divide-gov-borde/40`
   - **Alta prioridad** — Victimas: `animate-fade-in-up` al resultado, `rounded-xl`/`rounded-2xl` en cards, `hover:shadow-soft-md` en recientes
   - **Alta prioridad** — HogarDetalle: animaciones escalonadas en 4 secciones (0/50/100/150ms)
   - **Alta prioridad** — SesionDetalle: animaciones escalonadas, `shadow-soft` en progress card
   - **Media** — Instrumentos: `rounded-2xl` en icon background, option badges mas sutiles, `animate-fade-in` al expandir
   - **Media** — Supervision: `shadow-soft` en filtros y chart cards, progress bar `h-1.5`, boton limpiar filtros
   - **Media** — Reportes: animaciones en cards y tabla
   - **Media** — VictimaDetalle: animaciones escalonadas en 4 secciones
   - **Media** — Encuestas: `Select` component, barra progreso `h-1.5` + `transition-all`, filtros en card
   - **Media** — Auditoria: `shadow-soft` en filtros, action badges `rounded-md`
   - **Media** — Dashboard: animaciones en grid metricas y card accesos rapidos
   - **Media** — Login: `Alert` component, `animate-scale-in` en form card, `transition-all` en toggle password
   - **Baja** — CambiarPassword: `shadow-soft animate-fade-in-up` en card, toggle ojo en los 3 campos
   - **Baja** — Hogares: `Select` component, filtros en card con shadow
   - **Baja** — NotFound: `rounded-2xl`, `animate-fade-in`, `hover:scale-105` en boton

2. **Fix API Reportes — campos desalineados con el backend**
   - `src/api/reportes.ts`: interfaz `ResumenEncuestador` completamente reescrita con campos reales del backend (`sesiones_completadas`, `hogares_caracterizados`, `respuestas_total`, `periodo_desde/hasta`)
   - `DetalleSesion` actualizada (`instrumento_nombre`, `estado_display`, `respuestas_total`)
   - Funcion `desdeDefault()`: rango de 3 meses por defecto (evita quedarse sin datos al filtrar por mes actual)
   - `src/pages/Reportes.tsx`: columnas tabla actualizadas a campos reales, 6 cards de resumen
   - `src/pages/Dashboard.tsx`: campos de metricas corregidos

3. **Extras durante la sesion**
   - `Supervision.tsx`: boton "Limpiar" que limpia filtros fecha y recarga sin parametros
   - `CambiarPassword.tsx`: toggle ver/ocultar contrasena en los 3 campos (estado independiente por campo)
   - Diagnostico datos de prueba: sesiones de mayo no aparecian en reportes por filtro de mes. Resuelto con rango ampliado en el cliente API

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/api/reportes.ts` | Interfaz y campos alineados con backend real, rango 3 meses por defecto |
| `src/pages/Dashboard.tsx` | Campos corregidos + animaciones |
| `src/pages/Reportes.tsx` | Columnas tabla + cards corregidas + animaciones |
| `src/pages/Login.tsx` | Alert component + animate-scale-in + transition-all toggle |
| `src/pages/Hogares.tsx` | Select component + filtros en card |
| `src/pages/HogarDetalle.tsx` | Animaciones escalonadas |
| `src/pages/Encuestas.tsx` | Select component + barra progreso refinada |
| `src/pages/SesionDetalle.tsx` | Animaciones escalonadas + shadow-soft |
| `src/pages/Victimas.tsx` | Animacion resultado + cards refinadas |
| `src/pages/VictimaDetalle.tsx` | Animaciones escalonadas |
| `src/pages/Supervision.tsx` | Shadow-soft + boton limpiar filtros |
| `src/pages/Reportes.tsx` | Animaciones + fix campos |
| `src/pages/Instrumentos.tsx` | rounded-2xl + option badges + animate-fade-in |
| `src/pages/Parametricas.tsx` | Button danger + shadow-soft + bordes sutiles |
| `src/pages/Auditoria.tsx` | Shadow-soft + action badges rounded-md |
| `src/pages/CambiarPassword.tsx` | Shadow-soft + animacion + toggle ojo x3 |
| `src/pages/NotFound.tsx` | rounded-2xl + animate-fade-in + hover boton |

### Estado del frontend al cierre del dia

| Tipo | Cantidad |
|------|----------|
| Paginas | 17 (15 funcionales + Login + NotFound) |
| API clients | 10 |
| Componentes UI | 13 |
| Componentes layout | 3 (MainLayout, Sidebar, ErrorBoundary) |
| Rutas | 15 + catch-all 404 |
| Tests | 9 (5 Button + 4 authStore) |
| Fases completadas | 1 a 7 (Nivel 3 incluido) |

### Pendiente
- A11y: revision WCAG AA, roles ARIA en modales, navegacion teclado
- Testing: expandir cobertura de componentes principales

---

## Dia 10 — 2026-06-02 | Componente Dropdown personalizado

### Actividades realizadas

1. **Nuevo componente `Dropdown.tsx`** (`src/components/ui/`)
   - Reemplaza el `<select>` nativo en filtros de UI (no en formularios react-hook-form)
   - Trigger button estilizado igual que `.input` con chevron rotatorio
   - Panel flotante: `shadow-soft-md`, `rounded-xl`, `border-gov-borde/60`, `animate-slide-down`
   - Opcion seleccionada: `bg-gov-azulTenue text-gov-azul` + icono Check
   - Hover: `bg-gov-azulTenue/40 transition-all`
   - Cierre con clic fuera y tecla Escape
   - **Responsive:** desktop → dropdown custom, mobile → `<select>` nativo del OS
   - Panel con `min-w-full w-max` para adaptarse al texto mas largo sin cortar

2. **Aplicado en 5 paginas**
   - `Victimas.tsx` — selector tipo documento
   - `Hogares.tsx` — filtro estado hogar
   - `Encuestas.tsx` — filtro estado sesion
   - `Auditoria.tsx` — filtros accion y resultado (2 dropdowns)
   - `Parametricas.tsx` — filtros por departamento y por DT (2 dropdowns)

### Archivos creados

| Archivo | Descripcion |
|---------|-------------|
| `src/components/ui/Dropdown.tsx` | Dropdown personalizado Apple-style con fallback nativo en mobile |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/pages/Victimas.tsx` | Select nativo → Dropdown |
| `src/pages/Hogares.tsx` | Select component → Dropdown |
| `src/pages/Encuestas.tsx` | Select component → Dropdown |
| `src/pages/Auditoria.tsx` | 2 selects nativos → Dropdown |
| `src/pages/Parametricas.tsx` | 2 selects nativos → Dropdown (con conversion Number↔String) |

---

*Documento de seguimiento para el ingeniero lider (Javier Alexander Aguilar)*
