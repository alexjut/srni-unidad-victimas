# SRNI — Panel Web de Supervisión

> **Rama de trabajo:** `feature/sprint12-panel-web`
> **Stack:** React 18 + TypeScript + Vite + TailwindCSS
> **Backend:** Django REST Framework (`http://localhost:8001`)
> **Repositorio oficial:** Azure DevOps (ver enlace en CLAUDE.md raíz)

---

## 🚀 Inicio rápido

```bash
# 1. Instalar dependencias
cd srni-frontend
npm install

# 2. Copiar el archivo de variables de entorno
cp .env.example .env.local
# → Editar VITE_API_URL con la IP del servidor

# 3. Arrancar en modo desarrollo
npm run dev
# Abre http://localhost:5173
```

---

## 🔑 Autenticación JWT

El panel usa JWT idéntico al de la app móvil.

| Campo         | Valor                    |
|---------------|--------------------------|
| Endpoint login | `POST /api/auth/token/`  |
| Access token  | Expira en **15 minutos** |
| Refresh token | Expira en **8 horas**    |
| Almacenamiento | `sessionStorage` (NUNCA localStorage) |

```ts
// Ejemplo: obtener token
const resp = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/token/`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ codigo_usuario: 'ALEXJUT', password: 'alexjut1030' }),
});
const { access, refresh } = await resp.json();
sessionStorage.setItem('access_token', access);
sessionStorage.setItem('refresh_token', refresh);
```

---

## 📡 API REST — Endpoints principales

> Base URL: `VITE_API_URL` (ej. `http://10.63.31.132:8001`)
> Todas las llamadas llevan el header: `Authorization: Bearer <access_token>`

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/token/` | Login → devuelve access + refresh |
| POST | `/api/auth/token/refresh/` | Renovar access token |
| GET  | `/api/auth/perfil/` | Datos del usuario autenticado |

### Reportes del encuestador
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/reportes/encuestador/` | Resumen: sesiones, hogares, víctimas |
| GET | `/api/reportes/encuestador/detalle/?page=1` | Listado paginado de sesiones |
| GET | `/api/reportes/encuestador/exportar/?formato=csv` | Descarga CSV |

### Hogares
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/hogares/` | Lista de hogares (paginada) |
| GET | `/api/hogares/{id}/` | Detalle + miembros |

### Encuestas / Sesiones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/encuestas/` | Lista de sesiones (paginada) |
| GET | `/api/encuestas/{id}/` | Detalle de sesión |
| GET | `/api/encuestas/{id}/respuestas/` | Respuestas guardadas |

### Formulario / Instrumentos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/formulario/instrumentos/` | Lista de instrumentos |
| GET | `/api/formulario/instrumentos/{id}/temas/` | Capítulos del instrumento |

---

## 👥 Perfiles de usuario

El campo `perfil.nombre` define lo que ve cada usuario:

| Perfil | Descripción |
|--------|-------------|
| `ASISTENCIA` | Encuestador general |
| `TERRITORIAL` | Enfoque territorial |
| `BUENAVENTURA` | Pacífico — Buenaventura |
| `SAN_ANDRES` | Insular — San Andrés |
| `URBANO_ETNICO` | Comunidades urbanas étnicas |
| `RURAL_ETNICO` | Comunidades rurales étnicas |
| `SUPERVISOR` | Ve todos los encuestadores |
| `ADMIN` | Acceso completo |

---

## 🎨 Identidad visual

El panel sigue la **Guía de Diseño GOV.CO** (gobierno colombiano).

| Token | Color |
|-------|-------|
| Azul primario | `#1565C0` |
| Azul oscuro | `#003A80` |
| Amarillo GOV.CO | `#F5BF04` |
| Verde éxito | `#2E7D32` |
| Rojo error | `#C62828` |
| Naranja alerta | `#E65100` |
| Fondo | `#F5F5F5` |
| Superficie | `#FFFFFF` |

Fuentes recomendadas: **Montserrat** (títulos) y **Work Sans** (cuerpo) — disponibles en Google Fonts.

---

## 📁 Estructura sugerida del proyecto

```
srni-frontend/
├── public/
│   └── logo-unidad-victimas.png
├── src/
│   ├── api/
│   │   ├── client.ts          ← axios con interceptor JWT (auto-refresh 401)
│   │   ├── auth.ts
│   │   ├── reportes.ts
│   │   ├── hogares.ts
│   │   └── encuestas.ts
│   ├── components/
│   │   ├── GovLayout.tsx      ← sidebar + topbar GOV.CO
│   │   ├── GovCard.tsx
│   │   ├── GovTable.tsx       ← tabla paginada
│   │   └── GovBadge.tsx       ← chips de estado
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Hogares.tsx
│   │   ├── Encuestas.tsx
│   │   └── Reportes.tsx
│   ├── stores/
│   │   └── authStore.ts       ← Zustand (mismo patrón que el móvil)
│   ├── types/
│   │   └── index.ts           ← copiar y adaptar de srni-mobile/src/types/
│   └── main.tsx
├── .env.example
├── index.html
├── tailwind.config.ts
├── vite.config.ts
└── package.json
```

---

## 🔒 Reglas de seguridad obligatorias

1. **Tokens SIEMPRE en `sessionStorage`** — nunca en `localStorage` ni cookies sin `HttpOnly`
2. **`sessionStorage.clear()` al hacer logout** — limpia tokens Y datos cacheados
3. **Interceptor Axios** que añade `Authorization: Bearer` en cada request
4. **Refresh automático** al recibir 401 — renovar con `/api/auth/token/refresh/` y reintentar
5. **Nunca cachear datos RNI** (datos de víctimas) en IndexedDB ni localStorage
6. El instrumento (capítulos/preguntas) SÍ puede cachearse en memoria de la sesión
7. Cumplimiento **Ley 1581/2012** — Habeas Data Colombia

---

## 🧪 Usuario de prueba

| Campo | Valor |
|-------|-------|
| Código usuario | `ALEXJUT` |
| Contraseña | `alexjut1030` |
| Perfil | Supervisor / Admin |
| Víctima de prueba | CC 1030547250 — JAVIER ALEXANDER AGUILAR CASTRO |

---

## 📋 Alcance Sprint 12 — Panel Web

### Pantallas a desarrollar

- [ ] **Login** — formulario con logo Unidad + franja GOV.CO amarilla
- [ ] **Dashboard** — métricas generales (hogares, sesiones, encuestadores activos)
- [ ] **Mis reportes** — resumen del encuestador + exportar CSV
- [ ] **Lista de hogares** — tabla paginada con filtros (estado, municipio, fecha)
- [ ] **Detalle de hogar** — miembros del hogar + sesiones asociadas
- [ ] **Lista de sesiones** — tabla con estado, progreso y acciones
- [ ] **Detalle de sesión** — respuestas por capítulo (solo lectura)

### NO incluir en este sprint

- Panel de administración de usuarios (lo hace Django Admin)
- Edición de respuestas (solo lectura en el panel web)
- Mapas georreferenciados (Sprint futuro)

---

## 📞 Contacto

| Rol | Nombre | Email |
|-----|--------|-------|
| Líder técnico / Backend | Javier Aguilar Castro | ingaguilarsistemas@gmail.com |
| Supervisor UARIV | Oscar Andrés Manosalva García | — |

> **Cualquier duda sobre la API**: consultar primero este README,
> luego `docs/api-endpoints.md` en la raíz del repositorio,
> y finalmente contactar al líder técnico.
