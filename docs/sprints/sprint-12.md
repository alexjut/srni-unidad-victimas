# Sprint 12 — Panel Web + Modelo de Autorizado/Miembro v2

**Branch:** `feature/sprint12-panel-web`
**Estado:** ✅ Completo
**Inicio:** 2026-05-22
**Cierre:** 2026-05-25

---

## Objetivos del sprint

1. Refactorizar el modelo `Hogar` y `MiembroHogar` al concepto de **Autorizado** (titular de la entrevista) — eliminar la noción de "jefe de hogar" del scaffolding del hogar (se captura dentro de la entrevista).
2. Construir el **scaffold completo del panel web** (`srni-frontend/`) en React 18 + Vite + TypeScript + Tailwind, alineado a la paleta GOV.CO y a las reglas de seguridad JWT del proyecto.
3. Implementar la pantalla móvil **"Conformar Hogar"** que crea el hogar automáticamente con el autorizado y permite agregar integrantes con rol (Miembro / Tutor / Cuidador permanente) y estado de inclusión (Incluido / No incluido en RUV).
4. Agregar la víctima de prueba del contratista (CC 1030547250) al repositorio mock para validar el flujo end-to-end.

---

## Entregables

### A) Backend — modelo de hogar v2

| Cambio | Detalle |
|--------|---------|
| `Hogar.jefe_hogar` → `Hogar.autorizado` | FK a `Victima` con `related_name='hogares_como_autorizado'`. Ahora representa la víctima titular que autoriza y realiza la entrevista. |
| `MiembroHogar.rol` | Nuevo campo con choices `MIEMBRO` / `TUTOR` / `CUIDADOR_PERMANENTE`. |
| `MiembroHogar.es_autorizado` | Boolean. `UniqueConstraint`: solo un `es_autorizado=True` por hogar. |
| `MiembroHogar.estado_inclusion` | Choices `INCLUIDO` / `NO_INCLUIDO` — refleja si la persona está en el RUV. |
| `MiembroHogar.save()` | Sincroniza automáticamente `incluido_ruv` y `tipo_persona` (taxonomía Oracle) según `estado_inclusion`. |
| `PARENTESCO` choices | Se eliminó la opción `JEFE` — el jefe de hogar se captura dentro del módulo de entrevista, no en el modelo. |
| `HogarViewSet.perform_create` | Auto-inserta el autorizado como primer `MiembroHogar` con `rol='MIEMBRO'`, `es_autorizado=True`, `estado_inclusion='INCLUIDO'`. |
| Action `cambiar_jefe` → `cambiar_autorizado` | Lógica actualizada con la nueva semántica. |
| Migración 0003 | `RenameField` + nuevos campos + constraints. **BD vacía, sin data migration.** |
| Tests `tests/test_hogares.py` | 15/15 pasan: auto-inserción del autorizado, `UniqueConstraint`, sincronización de tipos Oracle. |

### B) Frontend Web — `srni-frontend/` (scaffold completo)

| Carpeta / archivo | Contenido |
|-------------------|-----------|
| `package.json` | React 18.3 · React Router 6 · Zustand 4.5 · Axios · Tailwind 3.4 · Vite 5 · Lucide-react · TypeScript 5.4 |
| `vite.config.ts` | Alias `@/` → `src/`, puerto dev 5173, proxy opcional a backend |
| `tailwind.config.ts` | Paleta GOV.CO institucional (`gov-azul`, `gov-azulOscuro`, `gov-amarillo`, `gov-verde`, `gov-rojo`, `gov-naranja`), fuentes Montserrat (display) + Work Sans (body) |
| `src/api/client.ts` | Axios con interceptor JWT: auto-refresh en 401 + **cola de espera** para peticiones en paralelo durante el refresh |
| `src/api/auth.ts` · `hogares.ts` · `encuestas.ts` · `reportes.ts` | Módulos tipados con interfaces TypeScript |
| `src/stores/authStore.ts` | Zustand con `accessToken` / `refreshToken` / `usuario`. **Tokens en `sessionStorage` (nunca localStorage).** `logout()` ejecuta `sessionStorage.clear()`. |
| `src/components/MainLayout.tsx` | Sidebar + topbar GOV.CO con navegación a Dashboard / Hogares / Encuestas / Reportes |
| `src/pages/Login.tsx` | Login con franja amarilla GOV.CO + logo Unidad + credenciales JWT |
| `src/pages/Dashboard.tsx` | 4 métricas (sesiones finalizadas / en proceso, hogares, víctimas) con tarjetas de color |
| `src/pages/Hogares.tsx` | Listado paginado con filtros básicos |
| `src/pages/Encuestas.tsx` | Listado de sesiones de encuesta |
| `src/pages/Reportes.tsx` | Resumen del encuestador + descarga CSV |
| `README.md` | Guía de arranque, alcance del sprint, paleta GOV.CO, usuario de prueba |
| `.env.example` | Plantilla con `VITE_API_URL` |

**Stack confirmado:**

```
React 18.3 + TypeScript 5.4 + Vite 5
TailwindCSS 3.4 con paleta GOV.CO
React Router 6 (rutas protegidas con <RequireAuth>)
Zustand 4.5 (mismo patrón que la app móvil)
Axios + interceptor JWT con auto-refresh
Lucide-react para iconos
```

### C) Mobile — pantalla "Conformar Hogar"

| Archivo | Detalle |
|---------|---------|
| `app/(main)/hogares/conformar.tsx` (842 líneas) | NUEVA pantalla — flujo completo desde el autorizado |

**Flujo:**

```
Búsqueda RNI → Víctima habilitada → Tab "Caracterizar"
   ↓
ConformarHogar (esta pantalla):
   1. Al montar: POST /api/hogares/  → crea el hogar (autorizado = primer MiembroHogar automático)
   2. Muestra ruta de entrevista (General / Acc. Constitucionales / Mod. Núcleo / Especial)
   3. Lista de integrantes (comienza con el autorizado marcado con ★)
   4. Form para agregar integrantes:
      - Tipo doc (CC/TI/RC/CE/PA) — selector modal
      - Número documento
      - Primer/segundo nombre, primer/segundo apellido
      - Fecha de nacimiento
      - Parentesco (Cónyuge / Hijo / Yerno / Nieto / Padre / Hermano / Otro pariente / No pariente) — selector
      - Género (M / F / NB / ND) — selector
      - Rol (Miembro / Tutor / Cuidador permanente) — selector
   5. Botón "Iniciar Entrevista" → POST /api/encuestas/ → navega al formulario
```

### D) Mobile — ajustes complementarios

| Archivo | Cambio |
|---------|--------|
| `app/(auth)/login.tsx` (550 líneas) | Refactor completo: gradiente azul, regiones decorativas, biometría prominente, **fix icono** `mountain` → `image-filter-hdr` (warning MaterialCommunityIcons) |
| `app/(main)/hogares/[hogarId].tsx` | Badge **★ AUTORIZADO**, chips INCLUIDO/NO_INCLUIDO, selector de ROL al agregar miembro, botón "Crear entrevista" solo activo si el autorizado existe |
| `app/(main)/hogares/nuevo.tsx` | Etiqueta "Autorizado / Titular" en vez de "Jefe de hogar"; envía campo `autorizado` |
| `app/(main)/_layout.tsx` · `busqueda.tsx` · `index.tsx` | Ajustes menores de navegación y safe area |
| `src/api/hogares.ts` (mobile) | `CrearHogarPayload` usa `autorizado`; `AgregarMiembroPayload` usa `rol` + `estado_inclusion` |
| `src/types/index.ts` | Tipos `RolMiembro`, `EstadoInclusion`; `Parentesco` sin `JEFE`; `MiembroHogarResumen` con `rol` / `es_autorizado` / `estado_inclusion` |
| `assets/regiones/*.png` | 5 imágenes nuevas: amazonia, andina, caribe, insular, orinoca — para fondo del login |

### E) Backend — víctima de prueba

| Archivo | Cambio |
|---------|--------|
| `apps/victimas/repository/mock.py` | Agregado **Caso 11**: CC **1030547250** JAVIER ALEXANDER AGUILAR CASTRO (1990-01-01, M) — estado RUV `INCLUIDO`, `habilitado=True`, hecho HV01 en Bogotá D.C. — para que el contratista pueda hacer login y validar el flujo completo en pantalla con su propia cédula. |

---

## Decisiones técnicas

### 1. Autorizado vs Jefe de hogar

> El "jefe de hogar" es un concepto que se decide **dentro de la entrevista**, no al crear el hogar. Antes del Sprint 12 el modelo asumía que el jefe del hogar era quien creaba el registro — eso es incorrecto. Ahora:
> - **Autorizado** (modelo): la víctima titular que autoriza la entrevista. Es siempre un miembro del hogar con `es_autorizado=True`.
> - **Jefe de hogar** (entrevista): se identifica en el módulo de jefatura del instrumento. Puede ser cualquier integrante.

`UniqueConstraint` garantiza que solo haya un `es_autorizado=True` por hogar. La migración 0003 está aplicada sobre BD vacía.

### 2. Rol del miembro — semántica funcional

Los tres roles cubren los casos legales más frecuentes:

| Rol | Cuándo aplica |
|-----|---------------|
| `MIEMBRO` | Caso normal — integrante regular del hogar |
| `TUTOR` | Adulto responsable legal de un menor sin padres presentes |
| `CUIDADOR_PERMANENTE` | Persona a cargo de un adulto en condición de dependencia |

Esto NO sustituye `parentesco` (que es la relación familiar). Un miembro puede ser, por ejemplo, `parentesco='HIJO_A'` + `rol='MIEMBRO'`, o `parentesco='NO_PARIENTE'` + `rol='CUIDADOR_PERMANENTE'`.

### 3. Sincronización Oracle (tipo_persona / incluido_ruv)

`MiembroHogar.save()` mapea automáticamente `estado_inclusion` a los campos Oracle que entiende el repositorio antiguo:

```python
def save(self, *args, **kwargs):
    if self.estado_inclusion == 'INCLUIDO':
        self.incluido_ruv = True
        self.tipo_persona = '5003'   # Víctima registrada
    else:
        self.incluido_ruv = False
        self.tipo_persona = '5004'   # Otro miembro
    super().save(*args, **kwargs)
```

Esto preserva compatibilidad con consultas Oracle del histórico sin que el frontend tenga que conocer la taxonomía interna.

### 4. Panel web — interceptor JWT con cola de espera

Cuando varias peticiones reciben 401 simultáneamente (caso típico al abrir el dashboard), solo la primera dispara el refresh — las demás se encolan y reintentan automáticamente con el nuevo token:

```ts
// srni-frontend/src/api/client.ts
let refrescando = false;
let colaEspera: Array<(token: string) => void> = [];

apiClient.interceptors.response.use(res => res, async (error) => {
  if (error.response?.status === 401 && !original._retry) {
    if (refrescando) {
      return new Promise(resolve => {
        colaEspera.push(newToken => {
          original.headers['Authorization'] = `Bearer ${newToken}`;
          resolve(apiClient(original));
        });
      });
    }
    // ... refresca y libera la cola
  }
});
```

Evita N llamadas concurrentes a `/auth/token/refresh/` y previene el efecto "thundering herd".

### 5. Seguridad del panel web — sessionStorage estricto

| Regla | Implementación |
|-------|---------------|
| Tokens en `sessionStorage`, nunca `localStorage` | `authStore.ts` |
| Logout limpia todo | `sessionStorage.clear()` en `logout()` |
| Bearer automático | Interceptor request en `client.ts` |
| Refresh transparente al 401 | Interceptor response en `client.ts` |
| Falla de refresh → logout + redirect | `window.location.href = '/login'` |

Cumple las mismas reglas que aplican al móvil (`expo-secure-store` allá, `sessionStorage` aquí).

---

## Archivos creados / modificados

### Nuevos archivos
```
srni-frontend/                                          ← NUEVO directorio completo
├── package.json · vite.config.ts · tailwind.config.ts
├── tsconfig.json · tsconfig.node.json · postcss.config.js
├── index.html · .env.example · README.md
└── src/
    ├── main.tsx · App.tsx · index.css
    ├── api/      (client, auth, hogares, encuestas, reportes)
    ├── components/MainLayout.tsx
    ├── pages/    (Login, Dashboard, Hogares, Encuestas, Reportes)
    └── stores/authStore.ts

srni-backend/apps/hogares/migrations/0003_autorizado_rol_es_autorizado_estado_inclusion.py
srni-mobile/app/(main)/hogares/conformar.tsx                ← 842 líneas
srni-mobile/assets/regiones/{amazonia,andina,caribe,insular,orinoca}.png
```

### Archivos modificados
```
srni-backend/apps/hogares/models.py · serializers.py · views.py · admin.py
srni-backend/apps/victimas/repository/mock.py             (+14 líneas — caso 11)
srni-backend/tests/test_hogares.py                        (15/15 ✅)
srni-mobile/app/(auth)/login.tsx                          (refactor, +266 líneas)
srni-mobile/app/(main)/hogares/[hogarId].tsx              (badge AUTORIZADO + ROL)
srni-mobile/app/(main)/hogares/nuevo.tsx
srni-mobile/app/(main)/_layout.tsx · busqueda.tsx · index.tsx
srni-mobile/src/api/hogares.ts · src/types/index.ts
```

---

## Cómo arrancar el panel web

```powershell
cd srni-frontend
npm install
cp .env.example .env.local      # editar VITE_API_URL
npm run dev                     # http://localhost:5173
```

### Usuario de prueba
| Campo | Valor |
|-------|-------|
| Código | `ALEXJUT` |
| Password | `alexjut1030` |
| Víctima de prueba (mock) | CC 1030547250 — JAVIER ALEXANDER AGUILAR CASTRO |

---

## Pendientes (backlog Sprint 13 — Panel Web v2)

| Pendiente | Prioridad |
|-----------|-----------|
| Detalle de hogar con miembros + sesiones asociadas (panel web) | Alta |
| Detalle de sesión con respuestas por capítulo (panel web, solo lectura) | Alta |
| Filtros server-side: por municipio, estado, fecha, encuestador | Alta |
| Paginación con cursor (no offset) en listados grandes | Media |
| Gráficos en el dashboard (sesiones por día, distribución por perfil) | Media |
| Export CSV / Excel desde el panel | Media |
| Vista de supervisor — métricas por encuestador | Alta |
| Auditoría de accesos (LogAcceso) visible en panel | Media |

> Sprint 13 confirmado con el supervisor: enfoque en **completar las pantallas operativas del panel web** sobre el scaffold del Sprint 12.
