# Mensaje para Brando — jerarquía de equipos en el panel

*(Para copiar y pegar. El plan completo está en `docs/planes/jerarquia-equipos.md`.)*

---

Brando, buen día.

Nos pidieron poder **organizar la operación por equipos** en el panel:

- El **supervisor** ve y arma su grupo de **encuestadores**.
- El **coordinador** ve a los **supervisores de su área** y puede entrar a cada equipo.

Hoy eso no se puede porque «supervisor» es apenas un nombre de perfil: no existe ninguna
relación que diga a quién supervisa. Eso lo pongo yo en el servidor.

## Lo que yo entrego primero

Voy a crear el concepto de **Equipo** (un supervisor, un área y sus encuestadores, con
fecha de entrada y salida para que quede historia) y estos servicios:

| Servicio | Para qué |
|---|---|
| `GET /api/equipos/` | Lista de equipos. El coordinador ve los de su área; el supervisor, el suyo |
| `GET /api/equipos/mio/` | El equipo del supervisor que está conectado |
| `POST /api/equipos/` | Crear equipo (nombre, supervisor, área) |
| `POST /api/equipos/{id}/miembros/` | Agregar **varios** encuestadores de una vez |
| `DELETE /api/equipos/{id}/miembros/{usuario}` | Sacar a uno del equipo |
| `GET /api/usuarios/?equipo=&sin_equipo=1` | Buscar encuestadores para asignar |

Te aviso apenas estén y te paso el contrato exacto con ejemplos de respuesta. Calculo
2 a 3 días.

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
