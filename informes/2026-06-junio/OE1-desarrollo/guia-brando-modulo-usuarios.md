# Para Brando — API del módulo "Administración de usuarios" (panel web)

**De:** Javier
**Asunto:** Backend listo para que armes la tabla + formulario de usuarios en el panel

Hola Brando,

Dejé listo el **API CRUD de usuarios** para que construyas el módulo de administración
en el panel web. Es **solo panel web** (NO va en la APK). Solo lo ven los **administradores**
(perfil con `puede_administrar`); a los demás el backend les responde **403**.

> Base URL: misma del panel (mismo origen). Todos requieren `Authorization: Bearer <access>`.

## Endpoints

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/api/usuarios/` | Lista paginada (PageNumber, igual que hogares/auditoría) |
| POST | `/api/usuarios/` | Crea usuario (con contraseña) |
| GET | `/api/usuarios/{id}/` | Detalle |
| PATCH | `/api/usuarios/{id}/` | Edita (nombre, email, perfil, activo, es_admin) |
| DELETE | `/api/usuarios/{id}/` | **Desactiva** (no borra físico) |
| POST | `/api/usuarios/{id}/reset_password/` | Body `{"password": "..."}` (mín. 8) |
| POST | `/api/usuarios/{id}/activar/` | Reactiva |
| POST | `/api/usuarios/{id}/desactivar/` | Desactiva |
| GET | `/api/usuarios/perfiles/` | Perfiles para el `<select>` |

**Filtros (query params):** `search` (código/nombre/email), `activo=true|false`,
`perfil__codigo=ADMINISTRADOR`, `ordering=codigo_usuario|-created_at`, `page`, `page_size`.

## Shape de un usuario (GET lista/detalle)
```json
{
  "id": "ab45b402-...",
  "codigo_usuario": "ALEXJUT",
  "nombre_completo": "Javier Alexander Aguilar Castro",
  "email": "ingaguilarsistemas@gmail.com",
  "perfil": 2,
  "perfil_codigo": "ADMINISTRADOR",
  "perfil_nombre": "Administrador",
  "activo": true,
  "es_admin": true,
  "fecha_ultimo_login": "2026-06-15T08:38:01-05:00",
  "created_at": "2026-06-15T..."
}
```

## Crear usuario (POST)
```json
{
  "codigo_usuario": "ENC010",
  "nombre_completo": "Nuevo Encuestador",
  "email": "enc010@srni.dev",
  "perfil": 1,
  "activo": true,
  "es_admin": false,
  "password": "ClaveSegura123"
}
```
> El `codigo_usuario` se normaliza a mayúsculas automáticamente. `perfil` es el `id` que
> traés de `/api/usuarios/perfiles/`.

## Perfiles disponibles (GET /perfiles/)
`ADMINISTRADOR`, `COORDINADOR` (Líder), `SUPERVISOR`, `ENCUESTADOR` — cada uno con sus
banderas (`puede_buscar_rni`, `puede_caracterizar`, `puede_ver_reportes`, `puede_administrar`).

## Sugerencia de UI
- Tabla con: código, nombre, perfil (badge), estado (activo/inactivo), acciones.
- Botón "Nuevo usuario" → formulario (código, nombre, email, perfil select, password).
- Acciones por fila: editar, resetear contraseña, activar/desactivar.
- Mostrar el módulo solo si el usuario logueado tiene `puede_administrar` (o `es_admin`).

Cualquier campo extra que necesites en la respuesta, me decís y lo agrego.
Probado: HTTP 200 en lista/perfiles con admin; 403 con encuestador.

Saludos,
Javier
