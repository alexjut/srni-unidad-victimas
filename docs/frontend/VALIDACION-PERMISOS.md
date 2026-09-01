# Validacion de permisos — SRNI Panel Web

> Matriz de validación de permisos por rol. **Sin diligenciar** — las columnas
> «Resultado real» siguen vacías y los cuatro usuarios en `PENDIENTE`.
> Última revisión del documento: **2026-09-01**.
> Frontend: http://localhost:5173 | Backend: http://localhost:8001
> En producción: https://caracterizacion.unidadvictimas.gov.co

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
| 7 | Hogares carga en solo lectura | Ir a `/hogares` | Carga la tabla; no debe permitir crear ni editar | |
| 8 | Encuestas carga en solo lectura | Ir a `/encuestas` | Carga la tabla; no debe permitir crear ni editar | |
| 9 | Reportes carga | Ir a `/reportes` | Carga con datos | |

> ✅ **CORREGIDO (verificado el 2026-09-01).** El 403 que este documento reportaba para el
> Supervisor en Hogares, Encuestas y Reportes **ya no ocurre**. El backend dejó de exigir
> `puede_caracterizar` para lectura: existe la clase `PuedeConsultarOperacion`
> (`apps/autenticacion/permissions.py`), que permite **lectura** a los roles de campo,
> supervisión y administración, y reserva la **escritura** a quien puede caracterizar.
> Está aplicada en `hogares/views.py`, `encuestas/views.py` y `reportes/views.py`.
>
> Lo que esta validación debe comprobar ahora es lo contrario de antes: que el Supervisor
> **sí ve** esas tres pantallas y que **no puede escribir** en ellas.

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
