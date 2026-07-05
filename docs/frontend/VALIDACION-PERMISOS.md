# Validacion de permisos — SRNI Panel Web

> Archivo personal. No commitear.
> Fecha de los cambios validados: 2026-07-02
> Frontend: http://localhost:5173 | Backend: http://localhost:8001

## Como usar este archivo

1. Abre el frontend con `pnpm dev` y el backend corriendo
2. Entra con cada usuario en orden
3. Rellena la columna "Resultado real" con: `OK`, `FALLA — [lo que viste]`
4. Cuando termines un usuario, cambia su estado de `PENDIENTE` a `OK` o `FALLA`
5. Cuando me traigas los resultados, con eso lo arreglamos

> Si quieres dejar evidencia visual: toma screenshot y nombralo
> `prueba-[usuario]-[numero].png` (ej: `prueba-ENC001-5.png`)

---

## Estado general

| Usuario    | Rol           | Estado    | Fecha | Notas |
|------------|---------------|-----------|-------|-------|
| ENC001     | Encuestador   | PENDIENTE |       |       |
| SUPERVISOR | Supervisor    | PENDIENTE |       |       |
| BRANDO     | Coordinador   | PENDIENTE |       |       |
| ALEXJUT    | Administrador | PENDIENTE |       |       |

---

## ENC001 — Encuestador `[ PENDIENTE ]`

**Credenciales:** `ENC001` / `SrniTest2026!`

| # | Que validar | Como hacerlo | Esperado | Resultado real |
|---|-------------|--------------|----------|----------------|
| 1 | Supervision NO aparece en sidebar | Iniciar sesion, revisar menu lateral | Item "Supervision" no visible | |
| 2 | Auditoria NO aparece en sidebar | Revisar menu lateral | Item "Auditoria" no visible | |
| 3 | Usuarios NO aparece en sidebar | Revisar menu lateral | Item "Usuarios" no visible | |
| 4 | /supervision bloqueada | Entrar a `http://localhost:5173/supervision` | Pantalla "Acceso restringido" | |
| 5 | /auditoria bloqueada | Entrar a `http://localhost:5173/auditoria` | Pantalla "Acceso restringido" | |
| 6 | /usuarios bloqueada | Entrar a `http://localhost:5173/usuarios` | Pantalla "Acceso restringido" | |
| 7 | Dashboard carga | Ir a `/dashboard` | Carga con datos | |
| 8 | Victimas carga | Ir a `/victimas` | Carga con buscador | |
| 9 | Hogares carga | Ir a `/hogares` | Carga tabla | |
| 10 | Encuestas carga | Ir a `/encuestas` | Carga tabla | |
| 11 | Reportes carga | Ir a `/reportes` | Carga con datos | |

---

## SUPERVISOR `[ PENDIENTE ]`

**Credenciales:** `SUPERVISOR` / `Supervisor2026*`

| # | Que validar | Como hacerlo | Esperado | Resultado real |
|---|-------------|--------------|----------|----------------|
| 1 | Supervision SI aparece en sidebar | Iniciar sesion, revisar menu lateral | Item "Supervision" visible | |
| 2 | Auditoria NO aparece en sidebar | Revisar menu lateral | Item "Auditoria" no visible | |
| 3 | Usuarios NO aparece en sidebar | Revisar menu lateral | Item "Usuarios" no visible | |
| 4 | /supervision carga | Ir a `/supervision` | Carga con datos de encuestadores | |
| 5 | /auditoria bloqueada | Entrar a `http://localhost:5173/auditoria` | Pantalla "Acceso restringido" | |
| 6 | /usuarios bloqueada | Entrar a `http://localhost:5173/usuarios` | Pantalla "Acceso restringido" | |
| 7 | Hogares — ver que pasa | Ir a `/hogares` | Carga tabla (o error 403 del backend — bug conocido) | |
| 8 | Encuestas — ver que pasa | Ir a `/encuestas` | Carga tabla (o error 403 del backend — bug conocido) | |

> BUG CONOCIDO: el backend devuelve 403 en Hogares, Encuestas, Victimas detalle y Reportes
> para el Supervisor porque usa el flag `puede_caracterizar` que el Supervisor no tiene.
> El frontend muestra la pagina pero las llamadas API fallan. Esto es pendiente con Javier.
> Anotar en resultado si aparece error o tabla vacia.

---

## BRANDO — Coordinador `[ PENDIENTE ]`

**Credenciales:** `BRANDO` / `Brando2026*`

| # | Que validar | Como hacerlo | Esperado | Resultado real |
|---|-------------|--------------|----------|----------------|
| 1 | Supervision SI aparece en sidebar | Iniciar sesion, revisar menu lateral | Item "Supervision" visible | |
| 2 | Auditoria SI aparece en sidebar | Revisar menu lateral | Item "Auditoria" visible | |
| 3 | Usuarios NO aparece en sidebar | Revisar menu lateral | Item "Usuarios" no visible | |
| 4 | /supervision carga | Ir a `/supervision` | Carga con datos de encuestadores | |
| 5 | /auditoria carga | Ir a `/auditoria` | Carga tabla de logs | |
| 6 | /usuarios bloqueada | Entrar a `http://localhost:5173/usuarios` | Pantalla "Acceso restringido" | |
| 7 | Dashboard carga | Ir a `/dashboard` | Carga con datos | |
| 8 | Victimas carga | Ir a `/victimas` | Carga con buscador | |
| 9 | Hogares carga | Ir a `/hogares` | Carga tabla | |
| 10 | Encuestas carga | Ir a `/encuestas` | Carga tabla | |
| 11 | Reportes carga | Ir a `/reportes` | Carga con datos | |

---

## ALEXJUT — Administrador `[ PENDIENTE ]`

**Credenciales:** `ALEXJUT` / `alexjut1030`

| # | Que validar | Como hacerlo | Esperado | Resultado real |
|---|-------------|--------------|----------|----------------|
| 1 | Supervision SI aparece en sidebar | Iniciar sesion, revisar menu lateral | Item "Supervision" visible | |
| 2 | Auditoria SI aparece en sidebar | Revisar menu lateral | Item "Auditoria" visible | |
| 3 | Usuarios SI aparece en sidebar | Revisar menu lateral | Item "Usuarios" visible | |
| 4 | /supervision carga | Ir a `/supervision` | Carga con datos de encuestadores | |
| 5 | /auditoria carga | Ir a `/auditoria` | Carga tabla de logs | |
| 6 | /usuarios carga | Ir a `/usuarios` | Carga tabla de usuarios | |
| 7 | Dashboard carga | Ir a `/dashboard` | Carga con datos | |
| 8 | Victimas carga | Ir a `/victimas` | Carga con buscador | |
| 9 | Hogares carga | Ir a `/hogares` | Carga tabla | |
| 10 | Encuestas carga | Ir a `/encuestas` | Carga tabla | |
| 11 | Reportes carga | Ir a `/reportes` | Carga con datos | |
