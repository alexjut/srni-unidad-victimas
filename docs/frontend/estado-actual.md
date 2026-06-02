# Frontend Web — Panel SRNI

**Tecnologia:** React 18.3 + TypeScript 5.4 + Vite 5 + TailwindCSS 3.4
**Carpeta:** `srni-frontend/`
**Estado:** 17 paginas funcionales — Fases 1-6 completadas, Fase 7 en progreso
**Ultima actualizacion:** 2026-06-02

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
│   ├── reportes.ts        resumen, detalle paginado, exportar CSV
│   ├── victimas.ts        buscar (POST hash SHA-256), detalle, registrar
│   ├── supervision.ts     resumen supervisor, series temporales
│   ├── formulario.ts      instrumentos, capitulo detalle con preguntas
│   ├── parametricas.ts    departamentos, municipios, DTs, puntos, tipos doc
│   └── auditoria.ts       logs de acceso con filtros
├── components/
│   ├── MainLayout.tsx     Sidebar desktop + drawer mobile + header con dropdown usuario + bottom sheet mobile
│   ├── Sidebar.tsx        Logo GOV.CO + 9 nav items
│   ├── ErrorBoundary.tsx  Captura errores React
│   └── ui/                13 componentes reutilizables
│       ├── Button.tsx     4 variantes, 3 tamanos, loading, icon, shadow-soft, press effect
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
│   ├── Login.tsx          Split layout: branding GOV.CO + formulario
│   ├── Dashboard.tsx      4 Cards metricas + accesos rapidos
│   ├── Hogares.tsx        Tabla paginada + filtros (busqueda + estado)
│   ├── HogarDetalle.tsx   Breadcrumb + InfoCards + miembros + sesiones
│   ├── Encuestas.tsx      Tabla paginada + filtro estado + barra progreso
│   ├── SesionDetalle.tsx  InfoCards + progreso + respuestas + link hogar
│   ├── Reportes.tsx       5 tarjetas resumen + tabla + exportar CSV
│   ├── Victimas.tsx       Busqueda por documento + resultado + recientes
│   ├── VictimaDetalle.tsx Datos PII + hechos victimizantes + metadata
│   ├── Supervision.tsx    LineChart + BarChart + tabla encuestadores + filtros
│   ├── Instrumentos.tsx   Cards expandibles + lazy-load preguntas
│   ├── Parametricas.tsx   Mapa Colombia + 5 tabs con filtros
│   ├── Auditoria.tsx      Logs inmutables + filtros accion/resultado/fecha
│   ├── CambiarPassword.tsx Formulario con react-hook-form + zod
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
| Parametricas | `parametricas.ts` | `/api/parametricas/departamentos/` · `/municipios/` · `/direcciones-territoriales/` · `/puntos-atencion/` · `/tipos-documento/` |
| Auditoria | `auditoria.ts` | `/api/auditoria/logs/` |

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

Fuentes: **Montserrat** (display) + **Work Sans** (body)

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
| **Total** | **9** | happy-dom |

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
- **Diseno Apple-style:** sombras multi-capa, animaciones suaves, transiciones globales, scrollbar minimalista. Mantiene identidad GOV.CO.
