# Jerarquía de equipos: coordinador → supervisores → encuestadores

**Pedido (18-sep-2026).** Poder organizar y ver la operación por equipos: el
**coordinador** ve a los **supervisores por área**, cada **supervisor** ve a los
**encuestadores de su grupo**, y se puede **asignar** quién supervisa a quién —ya sea
que el supervisor escoja a sus encuestadores o que el coordinador arme los grupos.

---

## 1. De qué partimos

| Pieza | Estado hoy | Archivo |
|---|---|---|
| Perfiles | ADMINISTRADOR, COORDINADOR, SUPERVISOR, DOCUMENTADOR, ENCUESTADOR, con 5 banderas de permiso | `apps/autenticacion/models.py:7` |
| Usuario | código, nombre, correo, perfil, activo. **Sin territorio, sin jefe, sin equipo** | `apps/autenticacion/models.py:63` |
| Territorio | Dirección Territorial, Departamento, Municipio, Punto de Atención | `apps/parametricas/models.py:108` |
| Territorio del trabajo | La DT se captura **en cada sesión**, no en el usuario | `apps/encuestas/models.py:74` |
| Visibilidad | Binaria: o ves **lo tuyo**, o ves **todo el país** | `apps/encuestas/views.py:125` |
| Reporte de supervisión | Lista todos los encuestadores del país, sin agrupar | `apps/reportes/views.py:309` |
| Panel | Páginas `Usuarios` y `Supervision` (tabla plana) | `srni-frontend/src/pages/` |

**El hueco de fondo:** hoy «supervisor» es solo un nombre de perfil. No existe
ninguna relación que diga *a quién* supervisa. Por eso un supervisor no puede ver a
los suyos: el sistema solo sabe distinguir entre «mis propias entrevistas» y «todas».

---

## 2. La decisión de diseño

Hay dos formas de modelarlo:

**(a) Un campo `supervisor` en el usuario.** Rápido: una línea en el modelo. Pero no
guarda historia (quién supervisaba antes), no soporta que un encuestador rote entre
jornadas y no deja registrar el área del equipo.

**(b) Un `Equipo`** con supervisor, dirección territorial, nombre y miembros. Permite
historia, reasignación, equipos por área y que el coordinador vea el árbol completo.

**Recomiendo (b)**, con una salvedad práctica: el equipo se crea igual de rápido, y
lo que evita es tener que rehacer el modelo en dos meses cuando pidan «el histórico
de qué supervisor tenía a esta encuestadora en agosto».

Dos reglas que conviene fijar desde el principio:

1. **Un encuestador pertenece a un solo equipo activo a la vez.** Si no, los reportes
   cuentan doble y nadie sabe quién responde por esa persona.
2. **El territorio del equipo es del equipo, no del usuario.** La DT de cada sesión
   sigue siendo la de la atención (donde se atendió a la familia). Son cosas distintas
   y mezclarlas daña los reportes de producción.

---

## 3. Qué hay que construir

### Servidor (me corresponde)

| # | Trabajo | Detalle |
|---|---|---|
| 1 | Modelo `Equipo` | nombre, `supervisor` (FK Usuario), `direccion_territorial` (FK), `activo`; y `MiembroEquipo` (equipo, usuario, desde, hasta) para la historia |
| 2 | Validaciones | el supervisor debe tener perfil SUPERVISOR o COORDINADOR; nadie se supervisa a sí mismo; un encuestador con un solo equipo activo |
| 3 | Alcance de visibilidad | tercer nivel entre «lo mío» y «todo»: **lo de mi equipo**. Un helper único que devuelva los usuarios visibles, usado por encuestas, hogares, víctimas, sincronización y reportes |
| 4 | Endpoints | `GET /api/equipos/` (el coordinador ve los de su área, el supervisor el suyo), `POST /api/equipos/`, `POST /api/equipos/{id}/miembros/` (asignar varios de una), `DELETE .../miembros/{usuario}` |
| 5 | «Mi equipo» | `GET /api/equipos/mio/` para el supervisor y `GET /api/equipos/?dt=` para el coordinador |
| 6 | Usuarios | exponer y filtrar por `equipo` y `direccion_territorial` en `/api/usuarios/` |
| 7 | Reportes | que `supervisor_reporte` y las series acepten `?equipo=` y `?direccion_territorial=`, y que el supervisor pueda ver la producción de los suyos (hoy solo el administrador puede mirar a otro) |
| 8 | Auditoría | registrar asignación y desasignación: quién movió a quién y cuándo |
| 9 | Admin | administración de equipos en el admin, para arreglar a mano sin tocar la base |

**Decisión que hay que tomar antes de empezar el 3:** hoy `puede_ver_reportes`
significa «ve todo el país». Si el supervisor pasa a ver solo lo suyo, eso **cambia
lo que hoy ve** quien tenga ese perfil. Propongo: el supervisor ve su equipo, el
coordinador ve su área, y el administrador sigue viendo todo.

### Panel web (le corresponde a Brando)

| # | Pantalla | Qué hace |
|---|---|---|
| A | **Usuarios** | columna y filtro por equipo; en el modal, selector de equipo (y de DT) |
| B | **Mi equipo** (supervisor) | lista de sus encuestadores, con buscador y selección múltiple para **agregar o quitar** |
| C | **Equipos** (coordinador) | los equipos de su área con su supervisor y cuántos encuestadores tiene cada uno; entrar a un equipo muestra su gente |
| D | **Supervisión** | agrupar la tabla por supervisor o por área, con totales por grupo y detalle al abrir |

---

## 4. Orden propuesto

1. **Servidor primero**: modelo, endpoints y alcance de visibilidad (2 a 3 días).
   Mientras no exista `/api/equipos/`, el panel no tiene contra qué trabajar.
2. **Panel en paralelo desde el día 2**: Brando puede arrancar por la pantalla de
   **Mi equipo** con el contrato de la API acordado, y seguir con Equipos y el
   agrupado de Supervisión.
3. **Reportes por equipo al final**, cuando ya haya equipos cargados con gente real.

**Fuera de alcance por ahora** (conviene decirlo para que no se cuele): mover la
jerarquía al teléfono. La app de campo no necesita saber de equipos; esto es
organización y seguimiento, que viven en el panel.

---

## 5. Lo que hay que preguntar al área funcional

1. **¿El área es la Dirección Territorial** o hay otra división (grupos, ejes,
   macroterritorios)? El modelo se ancla a lo que respondan.
2. **¿Quién arma los equipos?** ¿El coordinador asigna, el supervisor escoge, o los
   dos? Lo más operativo es que los dos puedan, con el coordinador por encima.
3. **¿Un encuestador puede estar en dos equipos?** Recomiendo que no (ver §2).
4. **¿El supervisor debe ver los datos personales** de las caracterizaciones de su
   equipo, o solo la producción (cuántas, en qué estado, cuándo)? Esto es protección
   de datos, no una preferencia de pantalla.
