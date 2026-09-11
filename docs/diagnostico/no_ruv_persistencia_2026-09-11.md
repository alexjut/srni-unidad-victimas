# «Los datos no permanecen almacenados» — qué es cierto y qué no

**Fecha:** 11 de septiembre de 2026
**Origen:** correo del equipo de caracterización del 11-sep-2026, segundo punto
**Para qué sirve este documento:** sostener con archivo y línea la respuesta del
§2 del correo `docs/gestion/correo_retiro_control_vigencia_2026-09-11.md`. Sin él,
ese numeral es palabra contra palabra.

---

## El reporte, textual

> «al registrar la información requerida y avanzar a otros capítulos del
> instrumento, los datos previamente diligenciados no permanecen almacenados, lo
> que obliga al usuario a ingresarlos nuevamente»
>
> «agradecemos validar la posibilidad de implementar un mecanismo de
> almacenamiento permanente de la información desde su primer registro»

No trae documento, fecha, usuario ni versión. Eso importa: los tres defectos que
sí existen se corrigen distinto, y sin el caso no se sabe cuál se vio.

---

## Lo que el reporte afirma y no es cierto

**El mecanismo de almacenamiento permanente desde el primer registro ya existe.**
No hay que implementarlo.

Las respuestas de la entrevista se escriben en SQLite del teléfono a medida que
se capturan, no al cerrar. La escritura es un *upsert* por
`(borrador, pregunta, miembro)`:

- `srni-mobile/src/db/borradoresDao.ts:89` — `upsertRespuesta`, con
  `ON CONFLICT(borrador_id, pregunta_id, miembro_id) DO UPDATE`.
- `srni-mobile/src/db/borradoresDao.ts:115` — `remapMiembro`, que reapunta las
  respuestas capturadas sin señal al identificador real del integrante cuando el
  servidor lo crea. Existe precisamente para que nada se pierda en ese salto.
- `srni-mobile/src/db/borradoresDao.ts:74` — `listarBorradores` y su comentario:
  dos filtros anteriores escondían entrevistas ya capturadas y los dos se
  retiraron por eso mismo.

Por eso la frase «no permanecen almacenados», dicha en general, describe una
herramienta distinta de la que tenemos. **Lo que hay son tres defectos concretos
en el camino de quien no está en el RUV**, y ninguno de los tres es que la base
del teléfono no guarde.

---

## Defecto A — el registro manual viajaba solo en memoria

**Qué pasaba.** Al dar de alta a una persona que no está en el padrón, sus datos
se guardaban en un almacén de Zustand que **no persiste en disco**:

- `srni-mobile/src/stores/caracterizacionStore.ts:8` — el propio archivo lo dice:
  «NO persiste en disco — solo en memoria de la sesión activa».
- `srni-mobile/app/(main)/busqueda.tsx:999-1007` — `registrarAltaManual` en el
  camino **con** conexión llama a `registrarDesdeFuente` y hace
  `setVictimaFuente` / `setVictimaLocalId`. **No escribe en
  `victimasOfflineDao`**; solo el camino sin conexión lo hace
  (`busqueda.tsx:959`).
- `srni-mobile/app/(main)/busqueda.tsx:680-695` — al volver a la pantalla de
  búsqueda, un `useFocusEffect` llama `limpiar()` y borra el almacén a propósito,
  para dejarla lista para la siguiente persona.

**Consecuencia.** Registrada la persona con conexión, si el flujo se interrumpía
—volver a la búsqueda, reabrir la aplicación— el prellenado del formulario ya no
tenía de dónde leer. El respaldo previsto en
`srni-mobile/app/(main)/formulario/[temaId].tsx:530` lee de `victimasOfflineDao`
por identificador local, y para un alta manual **con** conexión esa fila no
existe. Resultado: había que reescribir nombre, apellidos y documento.

**Estado: corregido hoy.** Desde el 11-sep-2026 el servidor entrega los cuatro
campos del nombre y el documento de **cada** integrante, y el formulario los
precarga desde ahí, que es una fuente que no se pierde:

- `srni-backend/apps/hogares/tests/test_miembro_datos_personales.py` — fija el
  contrato.
- `srni-mobile/app/(main)/formulario/[temaId].tsx:187` —
  `construirPrefillMiembroBasico` siembra `NOMBRE_1/2`, `APELLIDO_1/2`, `A5`,
  `A3`, `A6`, `B9`, `B10`, `A8`.
- `srni-mobile/app/(main)/formulario/[temaId].tsx:236` — `partirNombre` prefiere
  los campos separados del servidor; partir el nombre completo quedó como
  respaldo.

Entró en la **versión 1.2.4** (commits `0c753e4` y `229f64b`, ambos del
11-sep-2026; el primero a las 12:27).

---

## Defecto B — el integrante no titular entraba con el primer nombre y nada más

**Qué pasaba.** El servidor entregaba el nombre solo como una cadena concatenada
y no entregaba el documento, así que la aplicación partía la cadena y se quedaba
con el primer pedazo. El titular salía completo; los demás integrantes, con el
primer nombre solo.

Está documentado en la cabecera de
`srni-backend/apps/hogares/tests/test_miembro_datos_personales.py`, que lo fecha
como **reportado en campo el 11-sep-2026**.

**Estado: corregido hoy**, en el mismo cambio del defecto A.

No es específico de quien no está en el RUV, pero se cruza con él: una persona de
alta manual suele venir con su hogar entero de alta manual.

---

## Defecto C — el hecho victimizante queda vacío y bloqueado

**Este es el único específico de quien NO está en el RUV, y sigue abierto.**

**Qué pasa.** El hecho victimizante (`H_V`) y su fecha de ocurrencia (`Ocur_HV`)
se muestran siempre en modo solo lectura, porque normalmente vienen del RUV y
volver a capturarlos introduciría inconsistencias. La condición **no mira si hay
dato**:

- `srni-mobile/app/(main)/formulario/[temaId].tsx:299` —
  `PREGUNTAS_RUV_READONLY = new Set(['H_V', 'Ocur_HV'])`.
- `srni-mobile/app/(main)/formulario/[temaId].tsx:1221` y `:1240` —
  `soloLectura={PREGUNTAS_RUV_READONLY.has(p.codigo_externo) || …}`, sin
  excepción.

En un alta manual, `hechos_victimizantes` sale vacío
(`srni-mobile/app/(main)/busqueda.tsx:993`), así que no hay nada que precargar.

**Consecuencia, medida sobre los instrumentos v8:**

| Instrumento | `H_V` / `Ocur_HV` | Efecto en una persona no incluida en el RUV |
|---|---|---|
| Territorial | `es_precargada = true` | No se muestran. Sin efecto |
| **Asistencia humanitaria** | `es_precargada = false` | **Se muestran vacíos y no se pueden escribir** |

En Territorial las preguntas precargadas se filtran de la lista visible
(`formulario/[temaId].tsx:693`), así que no hay problema. En Asistencia
humanitaria sí: el encuestador ve dos campos vacíos que no puede llenar.

No son obligatorias, de modo que **no impiden cerrar la entrevista** ni afectan
el porcentaje de avance. Es un dato que se pierde, no un bloqueo.

**Corrección propuesta.** Que el modo solo lectura dependa de que exista valor
precargado del RUV, no del código de la pregunta: si no hay dato del RUV, el
campo se habilita. Es un cambio de una condición.

---

## Defecto D — encontrado de paso, no reportado por ellos

**El alta manual hecha sin señal es invisible para una segunda búsqueda.**

`buscarOffline` consulta el padrón precargado y el filtro del universo, y **nunca
lee `victimasOfflineDao`**:

- `srni-mobile/app/(main)/busqueda.tsx:712-786` — `buscarOffline` usa
  `precargaDao.buscarCandidatosEnPadron` y `filtroUniverso.estaEnUniverso`.
- `victimasOfflineDao` aparece en esa pantalla **solo para escribir**
  (`busqueda.tsx:959`).

**Consecuencia.** Persona registrada a mano sin señal. Si se busca otra vez el
mismo documento, la aplicación responde de nuevo «no está en el padrón» y ofrece
darla de alta otra vez. El encuestador reescribe todo y se encola un **segundo**
registro de la misma persona.

Esto sí encaja literalmente con «obliga al usuario a ingresarlos nuevamente», y
además genera duplicados al sincronizar. **Es el candidato más probable de lo que
vieron si las pruebas se hicieron sin conexión.**

**Corrección propuesta.** Que `buscarOffline` consulte `victimasOfflineDao` antes
de declarar «no está en el padrón», y que al encontrarla ofrezca continuar en vez
de registrar.

---

## Resumen

| | Defecto | Específico de no RUV | Estado |
|---|---|---|---|
| A | Registro manual solo en memoria | Sí | Corregido en 1.2.4 |
| B | Integrante no titular sin apellidos ni documento | No, pero se cruza | Corregido en 1.2.4 |
| C | Hecho victimizante vacío y bloqueado | **Sí** | Abierto — una condición |
| D | Alta manual sin señal invisible a la segunda búsqueda | **Sí** | Abierto — no lo reportaron |

**Lo que hay que pedirles, y por qué no es una excusa.** Documento, fecha y hora,
usuario y versión visible en la pantalla de ingreso. A y B ya están corregidos, C
y D no, y las correcciones de C y D son distintas entre sí. Sin el caso, se
corrige a ciegas y se vuelve a discutir el mismo punto en dos semanas.
