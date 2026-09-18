# Mensaje para Brando — jerarquía de equipos en el panel

*(Para copiar y pegar. El plan completo está en `docs/planes/jerarquia-equipos.md`.)*

---

Brando, buen día.

Nos pidieron poder **organizar la operación por equipos** en el panel:

- El **supervisor** ve y arma su grupo de **encuestadores**.
- El **coordinador** ve a los **supervisores de su área** y puede entrar a cada equipo.

Hasta ayer eso no se podía: «supervisor» era apenas un nombre de perfil y ninguna
relación decía a quién supervisa. **Ya lo dejé en el servidor y está en producción**,
así que puedes empezar cuando quieras.

## Ya está en producción (lo puedes usar hoy)

El servidor ya tiene el concepto de **Equipo**: un supervisor, un área y sus
encuestadores, con fecha de entrada y de salida para que quede historia.

| Servicio | Qué hace |
|---|---|
| `GET /api/equipos/` | Lista recortada por quien pregunta: el coordinador ve todos, el supervisor solo el suyo. Acepta `?direccion_territorial=` |
| `GET /api/equipos/{id}/` | El equipo con su lista de `encuestadores` |
| `GET /api/equipos/mio/` | El equipo del supervisor conectado (404 si no tiene) |
| `POST /api/equipos/` | Crear: `{nombre, supervisor, direccion_territorial?}` |
| `POST /api/equipos/{id}/miembros/` | Asignar **varios**: `{"usuarios": ["uuid", "uuid"]}`. Devuelve el equipo con su gente |
| `DELETE /api/equipos/{id}/miembros/{usuario_id}/` | Sacar a uno |
| `GET /api/equipos/sin-equipo/` | Encuestadores a los que falta asignar. Acepta `?busqueda=` |

Cada equipo trae `total_encuestadores`, `supervisor_codigo`, `supervisor_nombre` y
`direccion_territorial_nombre`, para que la tabla no tenga que resolver nada aparte.

Tres reglas que el servidor ya sostiene, para que no las repitas en el panel:

1. **Un encuestador pertenece a un solo equipo.** Si lo asignas a otro, el servidor
   cierra la pertenencia anterior solo; no hace falta quitarlo primero.
2. **Nadie se supervisa a sí mismo** y el equipo lo encabeza un supervisor, un
   coordinador o un administrador. Si mandas un encuestador como supervisor, responde
   400 con el mensaje en el campo `supervisor`.
3. **Borrar un equipo lo desactiva**, no lo elimina: la historia se conserva.

## Lo que te pediría en el panel

**1. Usuarios** — agregar columna **Equipo** y filtro por equipo; en el modal de editar,
un selector de equipo. Es lo más rápido y ya deja usable la asignación.

**2. «Mi equipo»** (pantalla nueva, para el supervisor) — la lista de sus encuestadores
y un buscador para agregar: selección múltiple y un botón «Agregar al equipo». Que se
pueda quitar a alguien con confirmación. Esta es la que más piden.

**3. «Equipos»** (pantalla nueva, para el coordinador) — tarjetas o tabla con los equipos
de su área: supervisor, cuántos encuestadores tiene y su producción; al entrar, la gente
del equipo.

**4. Supervisión** — agrupar la tabla actual por supervisor o por área, con totales por
grupo y detalle al abrir. Hoy es una tabla plana de todos los encuestadores del país.

**Orden sugerido:** 1 → 2 → 4 → 3. Con el 1 y el 2 ya se puede usar en campo.

## Un detalle que cambia lo que ve la gente

Hoy quien tiene permiso de reportes **ve todo el país**. Con esto, la idea es que el
supervisor vea solo su equipo y el coordinador solo su área (el administrador sigue
viendo todo). Cuando lo aplique en el servidor, las pantallas de reportes y supervisión
van a traer menos datos para esos perfiles: no es un error, es el alcance nuevo. Te aviso
antes de encenderlo para que no te tome por sorpresa.

## Lo que todavía no está definido

Estoy preguntando al área funcional: si «área» es la Dirección Territorial o hay otra
división, quién arma los equipos (el coordinador, el supervisor o los dos) y si el
supervisor debe ver los datos personales de las caracterizaciones de su equipo o solo la
producción. Lo último puede cambiar qué mostramos en la pantalla del equipo, así que
conviene dejar esa vista fácil de recortar.

Cualquier cosa me dices y lo ajustamos.
