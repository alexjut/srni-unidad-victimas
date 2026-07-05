# Credenciales de prueba — SRNI Panel Web

> Archivo personal. No commitear.
> Backend local: http://localhost:8001 | Frontend: http://localhost:5173

---

## Usuarios por rol

| Rol            | Usuario      | Contrasena        |
|----------------|--------------|-------------------|
| Encuestador    | `ENC001`     | `SrniTest2026!`   |
| Supervisor     | `SUPERVISOR` | `Supervisor2026*` |
| Coordinador    | `BRANDO`     | `Brando2026*`     |
| Administrador  | `ALEXJUT`    | `alexjut1030`     |

Usuarios encuestadores adicionales: `ENC002`, `ENC003`, `ENC004`, `ENC005` (misma contrasena que ENC001).

---

## Flags del modelo Perfil (backend)

Estos son los flags reales definidos en `apps/autenticacion/models.py` y asignados
por `crear_usuarios_demo` en `apps/autenticacion/management/commands/crear_usuarios_demo.py`.

| Flag                | Encuestador | Supervisor | Coordinador | Administrador |
|---------------------|:-----------:|:----------:|:-----------:|:-------------:|
| `puede_buscar_rni`  | SI          | SI         | SI          | SI            |
| `puede_caracterizar`| SI          | NO         | SI          | SI            |
| `puede_ver_reportes`| NO          | SI         | SI          | SI            |
| `puede_administrar` | NO          | NO         | NO          | SI            |

---

## Permission classes del backend y que flag usan

| Permission class      | Flag requerido        | Archivo                              |
|-----------------------|-----------------------|--------------------------------------|
| `PuedeBuscarRNI`      | `puede_buscar_rni`    | `apps/autenticacion/permissions.py`  |
| `PuedeCaracterizar`   | `puede_caracterizar`  | `apps/autenticacion/permissions.py`  |
| `PuedeVerReportes`    | `puede_ver_reportes`  | `apps/autenticacion/permissions.py`  |
| `PuedeAdministrar`    | `puede_administrar`   | `apps/autenticacion/permissions.py`  |
| `_PuedeVerAuditoria`  | `administrar` OR `ver_reportes` | `apps/auditoria/views.py` |

---

## Tabla de permisos por modulo — estado actual del backend

Esta tabla refleja lo que el backend REALMENTE aplica segun las permission classes de cada view.

| Modulo / Funcion             | Encuestador | Supervisor | Coordinador | Administrador | Permission class usada             |
|------------------------------|:-----------:|:----------:|:-----------:|:-------------:|------------------------------------|
| Inicio (Dashboard)           | SI          | SI         | SI          | SI            | `IsAuthenticated`                  |
| Buscar victimas (RNI)        | SI          | SI         | SI          | SI            | `PuedeBuscarRNI`                   |
| Ver detalle de victima       | SI          | **NO**     | SI          | SI            | `PuedeCaracterizar`                |
| Ver lista de hogares         | SI          | **NO**     | SI          | SI            | `PuedeCaracterizar`                |
| Ver detalle de hogar         | SI          | **NO**     | SI          | SI            | `PuedeCaracterizar`                |
| Ver lista de encuestas       | SI          | **NO**     | SI          | SI            | `PuedeCaracterizar`                |
| Ver detalle de encuesta      | SI          | **NO**     | SI          | SI            | `PuedeCaracterizar`                |
| Ver reportes propios         | SI          | **NO**     | SI          | SI            | `PuedeCaracterizar`                |
| Ver panel de supervision     | NO          | SI         | SI          | SI            | `PuedeVerReportes`                 |
| Ver instrumentos             | SI          | SI         | SI          | SI            | `IsAuthenticated`                  |
| Ver parametricas             | SI          | SI         | SI          | SI            | `IsAuthenticated`                  |
| Ver logs de auditoria        | NO          | **SI**     | SI          | SI            | `administrar OR ver_reportes`      |
| Administrar usuarios         | NO          | NO         | NO          | SI            | `PuedeAdministrar`                 |
| Cambiar propia contrasena    | SI          | SI         | SI          | SI            | `IsAuthenticated`                  |

---

## Tabla de permisos deseada (manual de usuario)

Esta es la tabla que se quiere publicar en el manual. Difiere del estado actual en los puntos marcados.

| Modulo / Funcion             | Encuestador | Supervisor | Coordinador | Administrador |
|------------------------------|:-----------:|:----------:|:-----------:|:-------------:|
| Inicio (Dashboard)           | SI          | SI         | SI          | SI            |
| Buscar victimas (RNI)        | SI          | SI         | SI          | SI            |
| Ver detalle de victima       | SI          | SI         | SI          | SI            |
| Ver lista de hogares         | SI          | SI         | SI          | SI            |
| Ver detalle de hogar         | SI          | SI         | SI          | SI            |
| Ver lista de encuestas       | SI          | SI         | SI          | SI            |
| Ver detalle de encuesta      | SI          | SI         | SI          | SI            |
| Ver reportes propios         | SI          | SI         | SI          | SI            |
| Ver panel de supervision     | NO          | SI         | SI          | SI            |
| Ver instrumentos             | SI          | SI         | SI          | SI            |
| Ver parametricas             | SI          | SI         | SI          | SI            |
| Ver logs de auditoria        | NO          | NO         | SI          | SI            |
| Administrar usuarios         | NO          | NO         | NO          | SI            |
| Cambiar propia contrasena    | SI          | SI         | SI          | SI            |

---

## Inconsistencias detectadas (backend vs manual)

Encontradas el 2026-07-02 comparando `crear_usuarios_demo.py` + views del backend vs tabla del manual.

| Modulo                 | Rol        | Manual dice | Backend da | Motivo                                                         |
|------------------------|------------|-------------|------------|----------------------------------------------------------------|
| Ver detalle de victima | Supervisor | SI          | 403        | View usa `PuedeCaracterizar`; Supervisor tiene `caracterizar=False` |
| Ver lista de hogares   | Supervisor | SI          | 403        | View usa `PuedeCaracterizar`; Supervisor tiene `caracterizar=False` |
| Ver detalle de hogar   | Supervisor | SI          | 403        | View usa `PuedeCaracterizar`; Supervisor tiene `caracterizar=False` |
| Ver lista de encuestas | Supervisor | SI          | 403        | View usa `PuedeCaracterizar`; Supervisor tiene `caracterizar=False` |
| Ver detalle de encuesta| Supervisor | SI          | 403        | View usa `PuedeCaracterizar`; Supervisor tiene `caracterizar=False` |
| Ver reportes propios   | Supervisor | SI          | 403        | Endpoint `/produccion/` usa `PuedeCaracterizar`                |
| Ver logs de auditoria  | Supervisor | NO          | 200 OK     | Guard es `administrar OR ver_reportes`; Supervisor tiene `ver_reportes=True` |

### Raiz del problema

El flag `puede_caracterizar` se usa para TODAS las operaciones de hogares/encuestas/victimas,
sin distinguir entre lectura (que el supervisor si deberia hacer) y escritura (que no deberia).

---

## Opciones para corregir — pendiente decision con Javier

**Opcion A — Rapida:** Activar `puede_caracterizar=True` en el perfil SUPERVISOR.
- El supervisor podria tecnicamente crear encuestas, pero en el flujo real no lo hara.
- Cambio minimo: solo una linea en `crear_usuarios_demo.py`.
- Resuelve 6 de las 7 inconsistencias.

**Opcion B — Correcta:** Agregar flag `puede_ver_datos` al modelo `Perfil`.
- Los endpoints de lectura usarian `PuedeVerDatos`.
- Los de escritura seguirian con `PuedeCaracterizar`.
- Supervisor tendria `ver_datos=True, caracterizar=False`.
- Requiere migracion de BD + nuevas permission classes + actualizar todas las views.

**Opcion C — Para auditoria:** Cambiar guard de auditoria a solo `puede_administrar`.
- Supervisor dejaria de ver logs (queda como dice el manual).
- Cambio de 1 linea en `apps/auditoria/views.py`.
- Se puede aplicar independientemente de A o B.

---

## Flujo de prueba de permisos

1. `ENC001` — Supervision NO aparece en sidebar, `/supervision` redirige al dashboard
2. `SUPERVISOR` — Supervision SI, Usuarios NO. Hogares/Encuestas dan 403 (bug conocido)
3. `BRANDO` — Supervision SI, Usuarios NO, todo lo demas SI
4. `ALEXJUT` — Todo SI, acceso al panel `/admin/` de Django

---

---

## Logica de visibilidad en el frontend (para implementar)

### Datos disponibles en el store

El endpoint `GET /api/auth/perfil/` devuelve el objeto `usuario` que queda
guardado en `authStore`. El frontend tiene acceso a estos flags via:

```ts
const usuario = useAuthStore((s) => s.usuario);

usuario.perfil.puede_buscar_rni      // boolean
usuario.perfil.puede_caracterizar    // boolean
usuario.perfil.puede_ver_reportes    // boolean | undefined
usuario.perfil.puede_administrar     // boolean | undefined
usuario.perfil.codigo                // string — ej: "ENCUESTADOR", "SUPERVISOR", "COORDINADOR", "ADMINISTRADOR"
```

El helper existente en `App.tsx` para aplicar guards es `RequirePermission`:

```tsx
// Muestra <Forbidden /> si el usuario no tiene el permiso
<RequirePermission permiso="puede_ver_reportes">
  <SupervisionPage />
</RequirePermission>
```

Solo acepta `puede_ver_reportes` o `puede_administrar` por ahora.
Habra que extenderlo para `puede_caracterizar` y `puede_buscar_rni` cuando se necesite.

---

### Sidebar — logica de visibilidad por item

Archivo: `src/components/Sidebar.tsx` — array `NAV_ITEMS`.
Cada item puede tener flags opcionales que filtran la visibilidad.
El filtro actual usa `adminOnly` y `supervisorOnly`.

| Item sidebar     | Ruta            | Condicion para mostrar                        | Estado actual         |
|------------------|-----------------|-----------------------------------------------|-----------------------|
| Inicio           | `/dashboard`    | siempre (solo `IsAuthenticated`)              | implementado          |
| Victimas         | `/victimas`     | siempre                                       | implementado          |
| Hogares          | `/hogares`      | siempre                                       | implementado          |
| Encuestas        | `/encuestas`    | siempre                                       | implementado          |
| Reportes         | `/reportes`     | siempre                                       | implementado          |
| Supervision      | `/supervision`  | `puede_ver_reportes === true`                 | implementado (flag `supervisorOnly`) |
| Instrumentos     | `/instrumentos` | siempre                                       | implementado          |
| Parametricas     | `/parametricas` | siempre                                       | implementado          |
| Auditoria        | `/auditoria`    | `perfil.codigo` en `['COORDINADOR','ADMINISTRADOR']` | **PENDIENTE** — hoy visible para todos |
| Usuarios         | `/usuarios`     | `puede_administrar === true`                  | implementado (flag `adminOnly`) |

> Nota sobre Auditoria: los flags actuales no distinguen Coordinador de Supervisor
> (ambos tienen `ver_reportes=True`). Por eso hay que usar `perfil.codigo` hasta
> que Javier agregue un flag dedicado. Ver seccion "Inconsistencias detectadas".

Cambio pendiente en `NAV_ITEMS`:
```ts
// Reemplazar la linea de auditoria de:
{ to: '/auditoria', icon: Shield, label: 'Auditoria' }

// Por:
{ to: '/auditoria', icon: Shield, label: 'Auditoria', coordinadorOnly: true }

// Y en el filtro agregar:
const puedeVerAuditoria = ['COORDINADOR', 'ADMINISTRADOR'].includes(usuario?.perfil?.codigo ?? '');
if ('coordinadorOnly' in i && i.coordinadorOnly && !puedeVerAuditoria) return false;
```

---

### Rutas — guards en App.tsx

| Ruta                        | Guard actual                                    | Guard correcto (manual)                                    | Estado         |
|-----------------------------|-------------------------------------------------|------------------------------------------------------------|----------------|
| `/dashboard`                | `RequireAuth`                                   | `RequireAuth`                                              | ok             |
| `/victimas`                 | `RequireAuth`                                   | `RequireAuth`                                              | ok             |
| `/victimas/:id`             | `RequireAuth`                                   | `RequireAuth` (pendiente backend fix para Supervisor)      | ok             |
| `/hogares`                  | `RequireAuth`                                   | `RequireAuth` (pendiente backend fix para Supervisor)      | ok             |
| `/hogares/:id`              | `RequireAuth`                                   | `RequireAuth` (pendiente backend fix para Supervisor)      | ok             |
| `/encuestas`                | `RequireAuth`                                   | `RequireAuth` (pendiente backend fix para Supervisor)      | ok             |
| `/encuestas/:id`            | `RequireAuth`                                   | `RequireAuth` (pendiente backend fix para Supervisor)      | ok             |
| `/reportes`                 | `RequireAuth`                                   | `RequireAuth` (pendiente backend fix para Supervisor)      | ok             |
| `/supervision`              | `RequirePermission("puede_ver_reportes")`       | `RequirePermission("puede_ver_reportes")`                  | ok             |
| `/instrumentos`             | `RequireAuth`                                   | `RequireAuth`                                              | ok             |
| `/parametricas`             | `RequireAuth`                                   | `RequireAuth`                                              | ok             |
| `/auditoria`                | `RequireAuth` (sin guard real)                  | `RequirePermission` con `perfil.codigo` coordinador+admin  | **PENDIENTE**  |
| `/usuarios`                 | `RequirePermission("puede_administrar")`        | `RequirePermission("puede_administrar")`                   | ok             |
| `/perfil/cambiar-password`  | `RequireAuth`                                   | `RequireAuth`                                              | ok             |

Cambio pendiente en `App.tsx` para la ruta de auditoria:
```tsx
// Extender RequirePermission para aceptar una funcion de evaluacion:
function RequirePermission({ check, children }) {
  const usuario = useAuthStore((s) => s.usuario);
  if (usuario && !check(usuario)) return <Forbidden />;
  return <>{children}</>;
}

// Uso en la ruta:
<Route path="auditoria" element={
  <RequirePermission check={(u) =>
    ['COORDINADOR', 'ADMINISTRADOR'].includes(u.perfil?.codigo ?? '')
  }>
    <SuspensePage><AuditoriaPage /></SuspensePage>
  </RequirePermission>
} />
```

---

### Resumen de cambios pendientes en el frontend

| Archivo                      | Cambio                                                                 | Prioridad |
|------------------------------|------------------------------------------------------------------------|-----------|
| `src/components/Sidebar.tsx` | Agregar `coordinadorOnly` en Auditoria + logica de filtro por codigo  | Alta      |
| `src/App.tsx`                | Guard en ruta `/auditoria` usando `perfil.codigo`                     | Alta      |
| `src/App.tsx`                | Extender `RequirePermission` para aceptar funcion `check`             | Alta      |
| `src/stores/authStore.ts`    | Agregar `codigo` al tipo `perfil` en la interface `Usuario`           | Alta      |

Estos 4 cambios se pueden hacer en una sola sesion sin tocar el backend.
Los demas problemas (Supervisor + hogares/encuestas/reportes) requieren primero
que Javier aplique la Opcion A o B descrita en la seccion de inconsistencias.

---

## Como recrear los usuarios (si se reinicia la BD)

```bash
cd "D:\Dev\RNI VIVANTO\srni-backend"
python manage.py crear_usuarios_demo --settings=srni.settings.development
```
