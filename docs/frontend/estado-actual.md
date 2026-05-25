# Frontend Web — Panel SRNI

**Tecnología:** React 18.3 + TypeScript 5.4 + Vite 5 + TailwindCSS 3.4
**Carpeta:** `srni-frontend/`
**Estado:** Scaffold operativo (Sprint 12) — pantallas pendientes en Sprint 13
**Última actualización:** 2026-05-25

---

## Qué ES el panel web

Aplicación web de supervisión y consulta para la Unidad para las Víctimas (UARIV).
Lectura del trabajo del encuestador, métricas por usuario y exportación de reportes.

**NO sustituye la app móvil** — la captura de campo sigue siendo móvil offline-first.
El panel web es una capa de visualización para supervisores, coordinadores y operadores territoriales.

---

## Stack técnico

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Framework | React | 18.3 |
| Lenguaje | TypeScript | 5.4 |
| Build / dev server | Vite | 5.3 |
| Routing | React Router | 6.23 |
| Estado global | Zustand | 4.5 |
| HTTP | Axios | 1.7 |
| Estilos | TailwindCSS | 3.4 |
| Iconos | Lucide-react | 0.395 |

---

## Pantallas implementadas (Sprint 12)

```
srni-frontend/src/
├── main.tsx               ← entry point con BrowserRouter
├── App.tsx                ← rutas con <RequireAuth>
├── components/
│   └── MainLayout.tsx     ✅ Sidebar + topbar GOV.CO
├── pages/
│   ├── Login.tsx          ✅ Login JWT con franja GOV.CO
│   ├── Dashboard.tsx      ✅ 4 métricas + accesos rápidos
│   ├── Hogares.tsx        ✅ Listado paginado
│   ├── Encuestas.tsx      ✅ Listado de sesiones
│   └── Reportes.tsx       ✅ Resumen del encuestador + export CSV
└── stores/
    └── authStore.ts       ✅ Zustand con sessionStorage
```

---

## API consumida

| Módulo | Archivo | Endpoints |
|--------|---------|-----------|
| Auth | `src/api/auth.ts` | `/api/auth/token/` · `/api/auth/token/refresh/` · `/api/auth/perfil/` |
| Hogares | `src/api/hogares.ts` | `/api/hogares/` · `/api/hogares/{id}/` |
| Encuestas | `src/api/encuestas.ts` | `/api/encuestas/` · `/api/encuestas/{id}/` · `/api/encuestas/{id}/respuestas/` |
| Reportes | `src/api/reportes.ts` | `/api/reportes/encuestador/` · `/detalle/` · `/exportar/` |

Todos consumen `apiClient` (`src/api/client.ts`) con interceptor JWT + auto-refresh 401.

---

## Seguridad

| Regla | Cómo se aplica |
|-------|---------------|
| Tokens en `sessionStorage` — nunca `localStorage` | `authStore.ts` lee/escribe directamente |
| `sessionStorage.clear()` al logout | método `logout()` en el store |
| Bearer automático en cada request | interceptor request en `client.ts` |
| Refresh transparente al 401 | interceptor response con cola de espera |
| Refresh fallido → logout + redirect a `/login` | `window.location.href = '/login'` |
| Sin caché de datos RNI en disco | nunca `localStorage` ni IndexedDB para datos de víctimas |
| Cumplimiento Ley 1581 / Habeas Data | datos PII permanecen server-side |

---

## Paleta GOV.CO

| Token Tailwind | Color | Uso |
|---------------|-------|-----|
| `gov-azul` | `#1565C0` | Primario, botones principales |
| `gov-azulOscuro` | `#003A80` | Headers, navegación |
| `gov-amarillo` | `#F5BF04` | Franja GOV.CO, énfasis |
| `gov-verde` | `#2E7D32` | Estados de éxito (sesión finalizada) |
| `gov-rojo` | `#C62828` | Errores, alertas críticas |
| `gov-naranja` | `#E65100` | En proceso, alerta media |
| `bg-fondo` | `#F5F5F5` | Fondo general |
| Superficie | `#FFFFFF` | Tarjetas |

Fuentes: **Montserrat** (display) + **Work Sans** (body) — vía Google Fonts.

---

## Cómo levantar el panel web

```powershell
cd srni-frontend
npm install
Copy-Item .env.example .env.local
# Editar .env.local → VITE_API_URL=http://localhost:8001
npm run dev
# http://localhost:5173
```

### Conexión al backend

Por defecto el panel apunta a `VITE_API_URL` definida en `.env.local`.
Para desarrollo en LAN o ngrok, ajustar al endpoint correspondiente.

---

## Backlog Sprint 13 — Panel Web v2

| Funcionalidad | Prioridad |
|---------------|-----------|
| Detalle de hogar (miembros + sesiones asociadas) | Alta |
| Detalle de sesión (respuestas por capítulo, solo lectura) | Alta |
| Filtros server-side: municipio, estado, fecha, encuestador | Alta |
| Paginación con cursor en listados grandes | Media |
| Gráficos del dashboard (sesiones por día, distribución por perfil) | Media |
| Export CSV / Excel desde panel | Media |
| Vista supervisor: métricas por encuestador | Alta |
| Auditoría de accesos (LogAcceso) visible | Media |
| Mapas georreferenciados de hogares | Baja (Sprint futuro) |

---

## Decisiones tomadas

- **No PWA / sin service worker:** el panel se usa siempre con conexión. Offline-first sigue siendo responsabilidad exclusiva de la app móvil.
- **Sin Material UI / sin Ant Design:** Tailwind + componentes propios mantienen control fino del diseño GOV.CO y el bundle bajo.
- **Sin Redux:** Zustand replica el patrón que ya usa la app móvil — minimiza disonancia cognitiva entre proyectos.
- **Sin SSR / sin Next.js:** SPA pura con Vite. El backend Django ya sirve la API; no se necesita SSR para un panel interno.
- **Lectura solamente:** el panel no edita respuestas de la encuesta. Captura sigue siendo móvil. Esto reduce drásticamente la superficie de validación y el riesgo de inconsistencia.
