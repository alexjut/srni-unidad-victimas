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

### Fase 1 — Componentes base e infraestructura UI
- [ ] Instalar dependencias: react-hot-toast, @tanstack/react-table, react-hook-form + zod, date-fns
- [ ] Crear componentes UI reutilizables: Button, Input, Select, Table, Modal, Badge, Card, Spinner, EmptyState, Breadcrumb
- [ ] Mejorar MainLayout: sidebar colapsable, breadcrumbs, indicador de usuario/rol, responsive
- [ ] Manejo global de errores: Error boundary, toasts en errores API, pagina 404

### Fase 2 — Vistas de detalle
- [ ] HogarDetalle (`/hogares/:hogarId`) — datos + miembros + sesiones
- [ ] SesionDetalle (`/encuestas/:sesionId`) — info + respuestas por capitulo
- [ ] Filtros y busqueda en tablas existentes (Hogares, Encuestas)

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

## Registro de cambios por dia

| Fecha | Que hice | Archivos tocados |
|-------|----------|-----------------|
| 2026-05-27 | Setup completo del ambiente local | Ninguno del repo (solo config local) |

---

*Documento de seguimiento para el ingeniero lider (Javier Alexander Aguilar)*
