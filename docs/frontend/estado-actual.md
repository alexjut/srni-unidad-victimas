# Frontend Web — Panel SRNI

**Tecnologia:** React 18.3 + TypeScript 5.4 + Vite 5 + TailwindCSS 3.4
**Carpeta:** `srni-frontend/`
**Estado:** 18 paginas funcionales — Fases 1-8 + Usuarios completadas — Build produccion validado — Code splitting aplicado
**Ultima actualizacion:** 2026-06-16

---

## Que ES el panel web

Aplicacion web de supervision y consulta para la Unidad para las Victimas (UARIV).
Lectura del trabajo del encuestador, metricas por usuario, busqueda de victimas y exportacion de reportes.

**NO sustituye la app movil** — la captura de campo sigue siendo movil offline-first.
El panel web es una capa de visualizacion para supervisores, coordinadores y operadores territoriales.

---

## Stack tecnico

| Componente | Tecnologia | Version |
|------------|-----------|---------|
| Framework | React | 18.3 |
| Lenguaje | TypeScript | 5.4 |
| Build / dev server | Vite | 5.3 |
| Routing | React Router | 6.23 |
| Estado global | Zustand | 4.5 |
| HTTP | Axios | 1.7 |
| Estilos | TailwindCSS | 3.4 |
| Iconos | Lucide-react | 0.395 |
| Graficas | Recharts | - |
| Mapas | react-simple-maps | - |
| Excel | ExcelJS | - |
| Formularios | react-hook-form + zod | - |
| Toasts | Sonner | 2.0 |
| Fechas | date-fns | 4.3 |
| Testing | Vitest + Testing Library | - |

---

## Estructura de archivos

```
srni-frontend/src/
├── api/
│   ├── client.ts          Axios + JWT interceptors (auto-refresh, cola, timeout)
│   ├── auth.ts            login, refresh, perfil, logout, cambiar-password
│   ├── hogares.ts         listar (paginado + filtros), detalle
│   ├── encuestas.ts       listar (paginado + filtro estado), detalle con respuestas
│   ├── reportes.ts        resumen, detalle paginado (todas las paginas para export), exportar CSV (legacy)
│   ├── victimas.ts        buscar (POST hash SHA-256), detalle, registrar
│   ├── supervision.ts     resumen supervisor, series temporales
│   ├── formulario.ts      instrumentos, capitulo detalle con preguntas
│   ├── parametricas.ts    departamentos, municipios, DTs, puntos, tipos doc, veredas, comunidades negras, resguardos indigenas
│   ├── auditoria.ts       logs de acceso con filtros
│   └── usuarios.ts        CRUD usuarios + perfiles + activar/desactivar + reset password
├── components/
│   ├── MainLayout.tsx     Sidebar desktop + drawer mobile + header con dropdown usuario + bottom sheet mobile
│   ├── Sidebar.tsx        Logo institucional (LogoHorizontalNegativo.svg) + 10 nav items (Usuarios adminOnly)
│   ├── ErrorBoundary.tsx  Captura errores React
│   └── ui/                14 componentes reutilizables
│       ├── Button.tsx     4 variantes, 3 tamanos, loading, icon, shadow-soft, press effect
│       ├── Dropdown.tsx   Dropdown custom Apple-style (desktop) + select nativo (mobile)
│       ├── Input.tsx      forwardRef, label, error, icono con peer-focus
│       ├── Select.tsx     forwardRef, label, error, opciones tipadas
│       ├── Table.tsx      Generico <T>, skeleton escalonado, fade-in filas, paginacion
│       ├── Modal.tsx      Backdrop blur, scale-in, focus trap, bloqueo scroll
│       ├── Card.tsx       Tarjeta metrica con hover lift
│       ├── Alert.tsx      4 variantes con borde lateral de acento
│       ├── Breadcrumb.tsx Navegacion jerarquica con aria-label
│       ├── Badge.tsx      5 variantes con borde sutil
│       ├── Spinner.tsx    3 tamanos, role="status"
│       ├── EmptyState.tsx Icono + titulo + descripcion
│       ├── Pagination.tsx Botones ghost, hover azul
│       └── PageHeader.tsx Titulo + subtitulo + acciones
├── stores/
│   └── authStore.ts       Zustand: tokens en sessionStorage, usuario, logout
├── pages/
│   ├── Login.tsx          Logo institucional (LogoHorizontalColor.svg) + formulario glass
│   ├── Dashboard.tsx      4 Cards metricas + accesos rapidos
│   ├── Hogares.tsx        Tabla paginada + filtros (busqueda + estado)
│   ├── HogarDetalle.tsx   Breadcrumb + InfoCards + miembros + sesiones
│   ├── Encuestas.tsx      Tabla paginada + filtro estado + barra progreso
│   ├── SesionDetalle.tsx  InfoCards + progreso + respuestas + link hogar
│   ├── Reportes.tsx       6 tarjetas resumen + tabla + exportar Excel (.xlsx) con modal de filtros (fecha/estado/instrumento)
│   ├── Victimas.tsx       Busqueda por documento + resultado + recientes
│   ├── VictimaDetalle.tsx Datos PII + hechos victimizantes + metadata
│   ├── Supervision.tsx    LineChart + BarChart + tabla encuestadores + filtros
│   ├── Instrumentos.tsx   Cards expandibles + lazy-load preguntas
│   ├── Parametricas.tsx   Mapa Colombia + 8 tabs con filtros
│   ├── Auditoria.tsx      Logs inmutables + filtros accion/resultado/fecha
│   ├── CambiarPassword.tsx Formulario con react-hook-form + zod
│   ├── Usuarios.tsx       Tabla usuarios + filtros perfil/estado + modales crear/editar/reset (solo puede_administrar)
│   └── NotFound.tsx       Pagina 404
├── test/
│   └── setup.ts           Setup vitest con jest-dom
├── App.tsx                15 rutas + RequireAuth + catch-all 404
├── main.tsx               Entry: BrowserRouter + ErrorBoundary + Toaster
└── index.css              Base global: transiciones Apple, scrollbar, focus ring, page-content
```

---

## API consumida

| Modulo | Archivo | Endpoints |
|--------|---------|-----------|
| Auth | `auth.ts` | `/api/auth/token/` · `/token/refresh/` · `/perfil/` · `/logout/` · `/cambiar-password/` |
| Hogares | `hogares.ts` | `/api/hogares/` · `/api/hogares/{id}/` |
| Encuestas | `encuestas.ts` | `/api/encuestas/` · `/api/encuestas/{id}/` |
| Reportes | `reportes.ts` | `/api/reportes/encuestador/` · `/detalle/` · `/exportar/` |
| Victimas | `victimas.ts` | `/api/victimas/buscar/` · `/api/victimas/{id}/` |
| Supervision | `supervision.ts` | `/api/reportes/supervisor/` · `/dashboard/series/` |
| Formulario | `formulario.ts` | `/api/formulario/instrumentos/` · `/capitulos/{id}/` |
| Parametricas | `parametricas.ts` | `/api/parametricas/departamentos/` · `/municipios/` · `/direcciones-territoriales/` · `/puntos-atencion/` · `/tipos-documento/` · `/veredas/` · `/comunidades-negras/` · `/resguardos-indigenas/` |
| Auditoria | `auditoria.ts` | `/api/auditoria/logs/` |
| Usuarios | `usuarios.ts` | `/api/usuarios/` · `/{id}/activar/` · `/{id}/desactivar/` · `/{id}/reset_password/` · `/perfiles/` |

Todos consumen `apiClient` (`src/api/client.ts`) con interceptor JWT + auto-refresh 401.

---

## Sistema de diseno

### Paleta GOV.CO (tailwind.config.ts)

| Token | Color | Uso |
|-------|-------|-----|
| `gov-azul` | `#1565C0` | Primario, botones, links |
| `gov-azulOscuro` | `#003A80` | Sidebar, login, header mobile |
| `gov-azulTenue` | `#E3F2FD` | Hover, fondos sutiles |
| `gov-amarillo` | `#F5BF04` | Franja GOV.CO |
| `gov-verde` | `#2E7D32` | Exito, badge finalizada |
| `gov-rojo` | `#C62828` | Error, badge cancelada |
| `gov-naranja` | `#E65100` | Advertencia, en proceso |
| `gov-grisTenue` | `#F5F5F5` | Fondo general |
| `gov-borde` | `#E0E0E0` | Bordes, divisores |

Fuentes: **Nunito Sans** (display + body) — pesos 400/500/600/700/800

### Sombras Apple-style

| Clase | Uso |
|-------|-----|
| `shadow-soft` | Cards, botones primarios |
| `shadow-soft-md` | Hover cards, dropdowns |
| `shadow-soft-lg` | Modales, bottom sheets |
| `shadow-soft-xl` | Overlays principales |

### Animaciones

| Clase | Efecto |
|-------|--------|
| `animate-fade-in` | Opacidad 0→1 (0.3s) |
| `animate-fade-in-up` | Sube 8px + opacidad (0.35s) |
| `animate-scale-in` | Escala 0.96→1 + opacidad (0.25s) |
| `animate-slide-down` | Baja 4px + opacidad (0.2s) |
| `animate-slide-up` | Sube desde abajo (0.25s) |

### Clases CSS reutilizables (index.css)

| Clase | Descripcion |
|-------|-------------|
| `.btn-primary` | Boton azul GOV.CO con shadow-soft, press effect |
| `.btn-secondary` | Boton borde azul con hover tenue |
| `.input` | Input con hover border, focus ring suave |
| `.card` | Fondo blanco, rounded-2xl, shadow-soft |
| `.card-hover` | Card con hover lift (-translate-y-0.5) |
| `.page-content` | Fade-in-up al entrar a pagina |
| `.badge-verde/rojo/azul/gris` | Badges de estado |

---

## Seguridad

| Regla | Como se aplica |
|-------|---------------|
| Tokens en `sessionStorage` — nunca `localStorage` | `authStore.ts` lee/escribe directamente |
| `sessionStorage.clear()` al logout | metodo `logout()` en el store |
| Logout real: blacklist refresh token | POST `/api/auth/logout/` antes de limpiar session |
| Bearer automatico en cada request | interceptor request en `client.ts` |
| Refresh transparente al 401 | interceptor response con cola de espera |
| Refresh fallido → logout + redirect a `/login` | `window.location.href = '/login'` |
| Sin cache de datos RNI en disco | nunca `localStorage` ni IndexedDB para datos de victimas |
| Cumplimiento Ley 1581 / Habeas Data | datos PII permanecen server-side |

---

## Testing

| Suite | Tests | Herramienta |
|-------|-------|-------------|
| Button.test.tsx | 5 (render, click, loading, disabled, variant) | Vitest + Testing Library |
| authStore.test.ts | 4 (init, setTokens, setUsuario, logout) | Vitest |
| **Total** | **9** | jsdom |

**Nota:** componentes con hooks (useState/useEffect/useRef) no son testeables con la combinacion actual Node.js v24 + Vitest 2.x + pnpm (bug CJS interop). Componentes sin hooks y stores si funcionan. Fix: actualizar a Vitest 3.x.

---

## Como levantar el panel web

```powershell
cd srni-frontend
pnpm install
pnpm dev          # http://localhost:5173
pnpm build        # Build produccion (tsc + vite build)
pnpm preview      # Preview del build
pnpm test         # Ejecutar tests
```

### Conexion al backend

El proxy de Vite redirige `/api` a `http://localhost:8001` (configurado en `vite.config.ts`).

---

## Decisiones de arquitectura

- **No PWA / sin service worker:** el panel se usa siempre con conexion. Offline-first es responsabilidad de la app movil.
- **Sin Material UI / sin Ant Design:** Tailwind + componentes propios para control del diseno GOV.CO y bundle reducido.
- **Sin Redux:** Zustand replica el patron de la app movil.
- **Sin SSR / sin Next.js:** SPA pura con Vite. El backend Django ya sirve la API.
- **Lectura solamente:** el panel no edita respuestas. Captura sigue siendo movil.
- **Sistema de transiciones suaves:** sombras multi-capa (shadow-soft, soft-md, soft-lg, soft-xl), animaciones suaves (fade-in 0.3s, fade-in-up 0.35s, scale-in 0.25s, slide-down/slide-up 0.2-0.25s escalonadas), transiciones globales 200ms ease-apple, scrollbar 6px minimalista. Mantiene identidad GOV.CO + elegancia moderna sin perder funcionalidad.
- **Nivel 3 UI completo:** revision pagina por pagina — botones hardcodeados migrados a componentes, Select reutilizable en filtros, barras de progreso refinadas (h-1.5), toggle ver/ocultar contrasena en CambiarPassword, bordes y sombras consistentes en todo el sistema, componentes con press effect y hover lift.
- **Code splitting:** React.lazy() en 13 paginas + SuspensePage wrapper con Spinner. manualChunks en vite.config.ts: vendor-react (164KB), vendor-charts (377KB recharts), vendor-maps (102KB react-simple-maps). Bundle principal: 937KB → 116KB (gzip 38KB). Cada pagina en su propio chunk (1-17KB).
- **A11y Modal:** aria-labelledby apuntando al h3 del titulo (WCAG AA). Modal tiene role="dialog", aria-modal="true", tabIndex=-1, cierre con Escape, overlay aria-hidden.
- **Build produccion:** validado y limpio. Sin errores de tipos. Sin warnings. Optimizaciones: tree-shaking, minification, source maps en dev.
- **Excel client-side:** ExcelJS con dynamic import (code splitting, no carga en bundle inicial). Archivo .xlsx generado 100% en navegador — header GOV.CO azul (#1565C0) texto blanco bold, filas alternas blanco/azul tenue (#E3F2FD), bordes internos, fila 1 congelada, anchos ajustados. 2 hojas: "Detalle de Sesiones" (9 columnas) + "Resumen" (métricas período). Nombre: reporte-srni-YYYY-MM-DD.xlsx. El endpoint /exportar/ del backend sigue existiendo pero ya no se usa.
- **Modal de filtros para exportacion:** pills (no Dropdown) para evitar clipping en overflow-y-auto del Modal. **Período:** dos date pickers (desde/hasta) con validacion cruzada, preconfigurados últimos 90 días. **Estado:** pills "Todos", Completada, En progreso, Iniciada, Suspendida, Cancelada (filtro client-side). **Instrumento:** pills dinámicos desde `GET /api/formulario/instrumentos/` al montar, solo activos, ordenados A-Z. Fallback silencioso a instrumentos de tabla actual si llamada falla. Pills: seleccionado → bg-gov-azul text-white, no seleccionado → border gris hover azul.
- **Dropdown personalizado (vs Select):** Componente custom para filtros UI (no formularios react-hook-form). Desktop: panel flotante estilizado shadow-soft-md, rounded-xl, border-gov-borde/60, animate-slide-down, opcion seleccionada bg-gov-azulTenue text-gov-azul + icono Check, hover bg-gov-azulTenue/40. Mobile: <select> nativo del SO (mejor UX tactil). Cierre con clic fuera o Escape. Usado en: Victimas, Hogares, Encuestas, Auditoria, Parametricas.

---

## Fase 8 — Completada 2026-06-10

### Parametricas completas (8/8 catalogos del backend cubiertos)

Analisis cruzado backend vs frontend realizado el 2026-06-10. Se agregaron las 3 tabs faltantes:

| Tab | Endpoint | Columnas | Filtro |
|-----|----------|----------|--------|
| Veredas | `GET /api/parametricas/veredas/` | codigo DANE, nombre, municipio, estado | por municipio |
| Comunidades Negras | `GET /api/parametricas/comunidades-negras/` | codigo, nombre, municipio, estado | por municipio |
| Resguardos Indigenas | `GET /api/parametricas/resguardos-indigenas/` | codigo, nombre, pueblo, municipio, estado | por municipio |

Datos de prueba: 30 veredas, 20 comunidades negras, 25 resguardos indigenas (solo en db.sqlite3 local).

**No hace falta para el frontend (son exclusivos de mobile):** crear hogares, responder encuestas, IA Gemini, sync offline, skip logic.

---

## Sistema de Transiciones Suaves

### Sombras (definidas en `tailwind.config.ts`)

| Clase | Valor | Uso |
|-------|-------|-----|
| `shadow-soft` | multi-capa sutil | Cards, botones primarios, componentes base |
| `shadow-soft-md` | multi-capa media | Hover cards, dropdowns, elementos elevados |
| `shadow-soft-lg` | multi-capa fuerte | Modales, bottom sheets, overlays secundarios |
| `shadow-soft-xl` | multi-capa muy fuerte | Overlays principales, drawers |

### Animaciones (definidas en `tailwind.config.ts`)

| Clase | Duración | Easing | Efecto |
|-------|----------|--------|--------|
| `animate-fade-in` | 300ms | ease-apple | Opacidad 0→1 |
| `animate-fade-in-up` | 350ms | ease-spring | Sube 8px + opacidad |
| `animate-scale-in` | 250ms | ease-spring | Escala 0.96→1 + opacidad |
| `animate-slide-down` | 200ms | ease-out | Baja 4px + opacidad |
| `animate-slide-up` | 250ms | ease-out | Sube desde abajo |

### Easing personalizado (tailwind.config.ts)

```javascript
ease-apple: 'cubic-bezier(0.4, 0, 0.2, 1)',    // Material Design standard
ease-spring: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)', // Rebote sutil
```

### Implementación en componentes

- **Transiciones globales:** `transition-all duration-200` en interactivos (buttons, inputs, hovers)
- **Focus ring:** `focus:outline-none focus:ring-2 focus:ring-gov-azul/50` en inputs, buttons, dropdowns
- **Page transitions:** `animate-fade-in-up` al cambiar ruta (key en location.pathname)
- **Componentes con motion:**
  - Button: press effect con `active:scale-95`
  - Card: hover lift con `hover:-translate-y-0.5`
  - Modal: backdrop blur + scale-in animado
  - Table rows: fade-in escalonado con delay
  - Alert: borde lateral acento + animacion entrada

---

## Code Splitting Strategy

### Objetivo
Reducir bundle principal de 937KB a 116KB sin afectar la experiencia del usuario.

### Implementación

**1. React.lazy() — 13 páginas críticas**
```typescript
const HogarDetalle = React.lazy(() => import('@/pages/HogarDetalle'));
const Supervision = React.lazy(() => import('@/pages/Supervision'));
// ... 11 más
```
Solo Login y Dashboard se importan eager (critical path).

**2. SuspensePage wrapper**
```typescript
const SuspensePage = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<Spinner />}>{children}</Suspense>
);
```
Muestra spinner mientras carga el chunk.

**3. Manual chunks en vite.config.ts**
```javascript
manualChunks: {
  'vendor-react': ['react', 'react-dom', 'react-router-dom'],    // 164KB
  'vendor-charts': ['recharts'],                                  // 377KB
  'vendor-maps': ['react-simple-maps'],                           // 102KB
}
```

### Resultado

| Bundle | Tamaño | Gzip | Cuando carga |
|--------|--------|------|--------------|
| main.js | 116KB | 38KB | Inicial |
| vendor-react.js | 164KB | 55KB | Inicial |
| vendor-charts.js | 377KB | 90KB | Usuario navega a Supervision |
| vendor-maps.js | 102KB | 25KB | Usuario navega a Parametricas |
| Cada página | 1-17KB | <5KB | Usuario navega a esa página |

**ExcelJS:** dynamic import en Reportes.tsx — no afecta bundle inicial, carga cuando usuario abre modal exportación.

---

## Excel Export Architecture

### Pipeline

1. **Usuario abre modal filtros** (botón "Exportar Excel")
2. **Carga de instrumentos** — `useEffect` fetch `GET /api/formulario/instrumentos/` (una sola vez)
   - Fallback: instrumentos de tabla actual si falla
3. **Modal con 3 filtros:**
   - **Período:** date pickers desde/hasta (validación cruzada, últimos 90 días por defecto)
   - **Estado:** pills (Todos, Completada, En progreso, Iniciada, Suspendida, Cancelada)
   - **Instrumento:** pills dinámicos desde API
4. **Fetch datos completos** — `fetchTodoDetalle({ desde, hasta })` obtiene todas las páginas en paralelo
5. **Generación Excel** — `dynamic import('exceljs')` → crea 2 hojas
6. **Descarga** — `blob → URL.createObjectURL → <a download> → click → cleanup`

### Detalles técnicos

**Helper `fetchTodoDetalle`:**
```typescript
async function fetchTodoDetalle({ desde, hasta }) {
  const firstPage = await reportesApi.detalle({ page: 1, desde, hasta });
  const totalPages = firstPage.meta.total_pages;
  const promises = Array.from({ length: totalPages }, (_, i) =>
    reportesApi.detalle({ page: i + 1, desde, hasta })
  );
  const allResults = await Promise.all(promises);
  return allResults.flatMap(r => r.results);
}
```

**Estructura Excel:**

Hoja 1 — "Detalle de Sesiones":
- Header: bg-gov-azul #1565C0, texto blanco bold
- Columnas: ID Hogar, Instrumento, Perfil, Estado, % Completado, Respuestas, Fecha Inicio, Fecha Fin, Duración (min)
- Filas alternas: blanco / azul tenue #E3F2FD
- Bordes: internos, fila 1 congelada
- Anchos: ajustados por columna

Hoja 2 — "Resumen":
- Métricas período: sesiones completadas, en progreso, suspendidas, hogares, respuestas total, promedio completado
- Rango: desde/hasta de filtro
- Mismo estilo header + filas alternas

**Nombre archivo:** `reporte-srni-YYYY-MM-DD.xlsx`

---

## Testing Limitations

### Estado actual
- **9 tests:** 5 en Button.test.tsx + 4 en authStore.test.ts
- **Setup:** Vitest 2.1.9 + jsdom + jest-dom

### Limitación conocida
**Componentes React con hooks NO se pueden testear** en el stack actual.

**Componentes testeables:**
- Button.tsx (sin hooks) ✅
- Badge.tsx ✅
- EmptyState.tsx ✅
- Componentes puramente funcionales

**Componentes no testeables:**
- Todos con useState, useEffect, useRef ❌
- Páginas (todas usan hooks) ❌
- Componentes con context ❌

**Causa técnica:**
Node.js v24.15.0 + pnpm virtual store + Vitest 2.1.9 + React 18 (CJS interop issue). Vite crea un Proxy ESM para React que no comparte `ReactCurrentDispatcher` con react-dom → `Proxy.useState` → `TypeError: Cannot read properties of null (reading 'useState')`.

**Soluciones intentadas (sin éxito):**
- dedupe React en pnpm-lock.yaml
- server.deps.inline en vite.config.ts
- resolve.alias para React
- shamefully-hoist en .npmrc
- pool:threads en Vitest
- deps.optimizer.esbuild en Vite
- jsdom / happy-dom toggle

**Fix futuro:** Actualizar a Vitest 3.x (usa React ESM build) o migrar a React 19.

---

## Build & Deploy

### Desarrollo local

```bash
cd srni-frontend
pnpm install
pnpm dev          # http://localhost:5173
```

### Build producción

```bash
pnpm build        # Ejecuta: tsc + vite build
pnpm preview      # Preview del bundle (local)
```

**Output:** `dist/` contiene:
- `index.html` — entry point
- `assets/` — JS chunks, CSS, media
- `.js.map` — source maps (opcional para debug remoto)

### Validaciones pre-deploy

```bash
# Verificar tipos sin errores
pnpm build        # Si falla → fix tipos antes de desplegar

# Verificar bundle size
npx vite-bundle-visualizer    # Ver qué ocupa espacio

# Tests
pnpm test         # 9 tests deben pasar
```

### Variables de entorno

**Archivo: `.env.production`** (crear antes de desplegar)

```env
VITE_API_URL=https://api-produccion.example.com   # URL backend producción
# Note: vite.config.ts usa process.env.VITE_API_URL ?? 'http://localhost:8001'
```

### Proxy en producción (nginx, Apache, etc.)

El panel está en `/` y el backend en `/api/`. Configurar el servidor web para:
1. Servir `dist/index.html` en `/`
2. Proxy `/api/*` → backend real
3. SPA fallback: requests a rutas desconocidas → `index.html`

**Ejemplo nginx:**
```nginx
location / {
  try_files $uri $uri/ /index.html;
}

location /api {
  proxy_pass http://backend-server:8001;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

### Checklist pre-producción

- [ ] Archivo `.env.production` con URLs correctas
- [ ] `pnpm build` sin errores
- [ ] `pnpm test` — 9 tests pasan
- [ ] Probar login con usuario real en staging
- [ ] Revisar bundle size: main.js < 200KB
- [ ] Verificar CORS headers en backend
- [ ] Verificar SSL/TLS en endpoint `/api`
- [ ] Cache headers configurados (inmutable para assets, no-cache para index.html)
- [ ] Source maps deshabilitados en producción (no quitar .map, solo no servirlos)

---

## Archivos de configuración clave

| Archivo | Propósito |
|---------|-----------|
| `vite.config.ts` | Build, proxy, test setup, chunks |
| `tailwind.config.ts` | Paleta GOV.CO, sombras, animaciones, fuentes |
| `tsconfig.json` | Strict mode, target ES2020, moduleResolution bundler |
| `.env` | Variables locales (opcional, vite.config usa defaults) |
| `package.json` | `"type": "module"`, scripts, dependencias |

---

## Arquitectura de Componentes

### Componentes Layout

#### MainLayout.tsx

**Propósito:** Envoltorio de todas las páginas. Contiene sidebar/drawer + header + page content.

**Responsivo:**
- **Desktop (≥1024px):** Sidebar fijo izquierda (w-64), header con dropdown usuario
- **Mobile (<1024px):** Sidebar → Drawer deslizable (overlay), topbar azul con hamburguesa, bottom sheet usuario

**Características:**
- Drawer se cierra automáticamente al navegar o clic overlay
- Header desktop: usuario + icono + dropdown logout
- Bottom sheet mobile: info usuario + cambiar contraseña + logout
- Transición suave: `transition-all duration-200`

#### Sidebar.tsx

**Navegación:** 9 items (Inicio, Víctimas, Hogares, Encuestas, Reportes, Supervisión, Instrumentos, Paramétricas, Auditoría)

**Indicador activo:** `bg-white/15 text-white font-semibold` (ruta actual)

**Logo:** GOV.CO con franja amarilla + "SRNI" subtítulo en Work Sans

#### ErrorBoundary.tsx

**Propósito:** Captura errores React no controlados.
- DEV: Detalle error + stack trace
- PROD: Mensaje amigable + botón "Recargar página"

---

### Componentes UI Base (14)

| Componente | Props | Características |
|-----------|-------|-----------------|
| **Button** | variant (primary/secondary/danger/ghost), size (sm/md/lg), loading, disabled, icon | Shadow-soft, press effect active:scale-95, focus ring azul |
| **Dropdown** | label, value, onChange, options, disabled | Desktop: custom panel shadow-soft-md animate-slide-down. Mobile (<768px): <select> nativo |
| **Input** | label, error, icon, ...HTML attrs | ForwardRef, label tracking-wide, error text-gov-rojo, icono opcional peer-focus |
| **Select** | label, error, options, ...HTML attrs | ForwardRef, integración react-hook-form, estilo consistente Input |
| **Table** | columns, data, isLoading, isEmpty, pagination | Skeleton escalonado, filas hover, empty state, fade-in |
| **Modal** | isOpen, onClose, title, children, footer | Backdrop blur scale-in, aria-labelledby, focus trap, bloqueo scroll |
| **Card** | icon, title, value, subtitle | Rounded-2xl shadow-soft, hover -translate-y-0.5 (lift) |
| **Badge** | variant (verde/azul/rojo/naranja/gris) | 5 variantes estado con colores GOV.CO |
| **Alert** | variant (success/error/info/warning) | Borde izquierdo 4px acento, rounded-lg, icono opcional |
| **Spinner** | size (sm/md/lg) | role="status", colores gov-azul, animación indefinida |
| **EmptyState** | icon, title, description | Mensaje amigable datos vacíos |
| **Breadcrumb** | items | Navegación jerárquica, separador /, último item sin link |
| **Pagination** | currentPage, totalPages, onPageChange | Anterior/Siguiente, deshabilitados límites, "Página X de Y" |
| **PageHeader** | title, subtitle, actions | Header estándar páginas con layout flex |

---

### Patrón Dropdown vs Select

**Dropdown.tsx** — para filtros UI:
- Custom desktop (panel flotante shadow-soft-md, chevron rotatorio, opción con Check)
- <select> nativo en mobile (<768px)
- Cierre: clic fuera, Escape, selección

**Select.tsx** — para formularios:
- Integración react-hook-form + zod
- Error messages sincronizados
- Validación

**Usado en:**
- Dropdown: Victimas, Hogares, Encuestas, Auditoria, Parametricas (filtros)
- Select: Login, CambiarPassword (formularios)

---

### Componentes Especializados

#### Formularios (react-hook-form + zod)

**Login.tsx:**
- Validación: codigo_usuario (min 3), password (min 6)
- Schema zod + resolver

**CambiarPassword.tsx:**
- 3 campos: actual, nueva, confirmar
- Toggle ver/ocultar contraseña por campo (estado independiente)
- Validación: nueva ≠ actual, nueva == confirmar
- Envío: `POST /api/auth/cambiar-password/` (autenticado)

---

### Patrones de Diseño (4)

#### 1. Patrón Loading/Error/Data

Usado en TODAS las páginas con datos. Estados: loading → loading spinner, error → Alert, data → contenido, !data → EmptyState.

#### 2. Patrón Filtros + Tabla

Usado en: Hogares, Encuestas, Reportes, Auditoria, Parametricas.
- Banner filtro activo: bg-gov-azulTenue + botón "Limpiar"
- handleLimpiar() limpia todos los filtros + recarga sin parámetros

#### 3. Patrón Modal + Formulario

Modal con form, validación, estado enviando, toast success/error, recarga lista.

#### 4. Patrón Búsqueda + Recientes (sessionStorage)

Usado en: Victimas.
- sessionStorage cumple Ley 1581 Habeas Data (no persiste en disco)
- Recientes limpios al cerrar navegador
- Máximo 5 items

---

### API Clients (10)

**client.ts — Base HTTP:**
- Axios instance baseURL `/api` (proxy Vite)
- Interceptor request: `Authorization: Bearer <token>`
- Interceptor response: 401 → refresh automático → reintenta → si falla → logout
- Cola requests pausa mientras refresca token
- Timeout: 30 segundos

**Módulos:**
1. **auth.ts** — login, refresh, perfil, logout, cambiar-password
2. **hogares.ts** — listar (paginado + filtros), detalle
3. **encuestas.ts** — listar (paginado + filtro estado), detalle
4. **reportes.ts** — resumen, detalle paginado (con fetchTodoDetalle)
5. **victimas.ts** — buscar (POST SHA-256), detalle
6. **supervision.ts** — resumen supervisor, series temporales
7. **formulario.ts** — instrumentos, capitulos detalle
8. **parametricas.ts** — 8 catálogos (deptos, municipios, DTs, puntos, tipos doc, veredas, comunidades negras, resguardos indigenas)
9. **auditoria.ts** — logs con filtros (accion, resultado, fecha)

**Flujo autenticación:**
1. Usuario → Login → authApi.login(codigo, password)
2. Backend: { access, refresh }
3. authStore.setTokens() → sessionStorage
4. Redirect dashboard
5. RequireAuth carga perfil (`GET /api/auth/perfil/`)
6. Interceptor agrega Bearer token
7. Si 401 → refresh automático
8. Si refresh falla → logout + /login

---

### Responsividad

**Breakpoints Tailwind:**
- sm: 640px
- md: 768px
- lg: 1024px (Sidebar ≥ lg, <lg = drawer)
- xl: 1280px
- 2xl: 1536px

**Estrategia mobile-first:**
1. Sidebar → Drawer en <lg
2. Grids adaptativos (1 col mobile, 2 tablet, 4+ desktop)
3. Tablas scroll horizontal en mobile (<md)
4. Dropdowns → <select> nativo en <md
5. Bottom sheets info usuario en mobile

---

### Tipografía

| Fuente | Peso | Uso |
|--------|------|-----|
| **Montserrat** | 600, 700 | Títulos (h2, h3), display |
| **Work Sans** | 400, 500, 600 | Body, labels, botones |
