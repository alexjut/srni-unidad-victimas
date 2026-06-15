# Correo 2 — Para Brando: credenciales + lo nuevo en el panel

**Para:** Brando
**De:** Javier
**Asunto:** Tu acceso al ambiente + lo que creamos en el panel

---

Hola Brando,

Te dejo tu acceso al ambiente desplegado y te cuento lo nuevo que quedó en el front.

## Tu acceso
- **URL:** https://prod-caracterizacion.ngrok.app
- **Usuario:** `BRANDO`  (mayúsculas; también acepta minúscula)
- **Contraseña:** `Brando2026*`
- **Rol:** Coordinador / Líder (buscar RNI, caracterizar, ver reportes)

## Lo que creamos en el panel (front)
Por la urgencia de la presentación, dejé una **página base del módulo de
Administración de usuarios** en el panel (es tu área, así que **mejorala con tu estilo —
no la rehagas desde cero**):

- Nueva ruta **`/usuarios`** + ítem **“Usuarios”** en el menú (visible **solo para admin**,
  vía `puede_administrar`).
- `src/pages/Usuarios.tsx`: **tabla** de usuarios + **crear/editar**, **resetear contraseña**
  y **activar/desactivar**.
- `src/api/usuarios.ts`: cliente del API CRUD (`/api/usuarios/`).
- Ajuste en `authStore` (el perfil ahora incluye `puede_administrar` / `puede_ver_reportes`).

Todo está en `main` (Azure + GitHub) → hacé `git pull` para traerlo.

## Datos para que el panel no se vea vacío
El ambiente ya trae paramétricas, instrumentos, 10 víctimas de prueba y los usuarios.
Las pantallas que dependen de caracterizaciones (Hogares, Encuestas, Reportes, Dashboard)
hoy salen vacías; **estoy generando datos de ejemplo** para poblarlas de cara a la
presentación. Decime qué pantallas son las clave y las dejo con datos.

Cualquier campo o endpoint extra que necesites, me escribís.

Saludos,
Javier
