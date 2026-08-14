# Hallazgos de QA — estado al 14-ago-2026

Respuesta punto por punto al listado de QA. Lo que dice «resuelto» está
verificado contra el código y con pruebas; lo que dice «pendiente» no se ha
tocado, y se dice cuál es la razón.

| # | Hallazgo | Estado |
|---|---|---|
| 1 | APK-001 — botón «Continuar» en ruta de excepción | ✅ Resuelto (de otra forma) |
| 2 | APK-002 — error intermitente al conformar hogar | ✅ Resuelto |
| 3 | APK-003 — definir si offline es requisito soportado | ⚠️ Construido; falta comunicarlo |
| 4 | Regla de recaracterización: libre vs. excepción | ⚠️ Definida; falta el manual |
| 5 | APK-004 — editar y eliminar integrantes | ✅ Eliminar · ⬜ editar en la app |
| 6 | APK-005/006 — progreso de sesiones y barras | ⬜ Pendiente |
| 7 | APK-007 — nombre en resultados con ficha vigente | ✅ Resuelto |

Todo lo de la APK necesita el **build v1.2.0** para llegar a campo.

---

## 1. APK-001 — la ruta de excepción bloqueaba la recaracterización

**Resuelto, pero no como se propuso.** No se arregló el botón: se cambió el
flujo, porque el problema de fondo era otro. El botón pedía una **foto del
soporte** y el encuestador no tiene ese documento — el fallo o la tutela llegan
por canal institucional al nivel central.

Ahora la excepción la autoriza coordinación desde el panel
(**Autorizaciones**), y el celular solo la consume: la ve en la búsqueda o en la
precarga de la jornada, y se consume al finalizar la encuesta.

> **Dato incómodo:** ese endpoint **nunca funcionó**, ni antes del cambio.
> Escribía la auditoría con `LogAcceso.objects.create(..., ip=...)` y ese campo
> se llama `ip_origen`, así que toda llamada moría en 500 antes de responder. QA
> reportó un bloqueo real cuya causa no era la que parecía.

## 2. APK-002 — error intermitente al conformar hogar

**Resuelto.** El error no era intermitente: lo era el mensaje. La app hacía

```js
if (typeof detalle === 'object') setErrorHogar(JSON.stringify(detalle));
```

y le mostraba al encuestador el JSON crudo del servidor. Y como en JavaScript
`typeof null === 'object'`, una respuesta con cuerpo vacío le mostraba
literalmente la palabra **«null»**.

El mismo intento fallaba distinto según hubiera red, la víctima tuviera un hogar
de otro encuestador (409) o el cuerpo viniera vacío — y las tres cosas se veían
igual de opacas. De ahí la sensación de intermitencia.

Ahora hay un intérprete de errores (`src/utils/errores.ts`, 6 pruebas) que
distingue los tres casos que exigen acciones distintas:

- **Sin red** → «Su trabajo no se pierde: vuelva a intentarlo cuando tenga señal».
- **El servidor respondió** → su texto tal cual, que ya viene redactado para
  campo.
- **Cualquier otra cosa** → mensaje claro **más el código HTTP**, y el detalle
  técnico va al reporte de errores, no a la pantalla. Eso es lo que le faltaba a
  soporte para diagnosticar sin pedir capturas.

## 3. APK-003 — trabajo sin conexión

**Está construido; lo que falta es la definición formal**, que es justo lo que
pide QA. Hoy la app opera sin señal con: padrón local, filtro del universo del
RUV (12,68 M de personas en 21,7 MB), hogares y sesiones persistidos en SQLite
con cola de sincronización, y desde hoy también las excepciones de vigencia.

**Sí es un requisito soportado.** Falta comunicarlo por escrito y con sus
límites — el principal: una habilitación otorgada después de que arrancó la
jornada no llega hasta la sincronización siguiente.

## 4. Regla de negocio de recaracterización

**Definida el 14-ago:** por **excepción**, nunca libre. Tres rutas la permiten
(Manual §5.1.1), la autoriza coordinación con radicado y motivo, y es de un solo
uso. Está documentada en
[`excepcion_vigencia_desde_el_front.md`](../operacion/excepcion_vigencia_desde_el_front.md).

**Falta llevarla al manual de usuario**, que es lo que QA pide expresamente.

## 5. APK-004 — editar y eliminar integrantes

**Eliminar: resuelto.** No existía ni en la API ni en la app — quien se
equivocaba al capturar quedaba con el error adentro del hogar para siempre.

```
DELETE /api/hogares/{id}/miembros/{miembro_id}/    quitar
PATCH  /api/hogares/{id}/miembros/{miembro_id}/    corregir
```

En la app, cada integrante tiene ahora su botón de quitar, con confirmación que
incluye el nombre. Tres guardas, cada una con su motivo:

- **Al autorizado no se le toca** — es el titular; quitarlo deja el hogar sin
  dueño. Para eso está «cambiar autorizado».
- **No se quita de un hogar ya caracterizado** — ese integrante forma parte de
  algo ya reportado. Eso es una novedad hacia el legado, no una corrección de
  captura. Con la encuesta *abierta* sí se puede: es cuando el encuestador se da
  cuenta del error.
- **No se quita lo que aún no sincronizó** — su alta sigue en la cola y
  borrarlo solo de la pantalla lo haría reaparecer al sincronizar.

Quitar **borra la fila** a propósito: atiende «esta persona nunca debió estar».
«Ya no vive en el hogar» es otra cosa y sigue sin resolverse.

**Editar en la app: pendiente.** La API ya lo soporta y está probada, pero la
pantalla de corrección no está hecha. Se dice para que no se dé por cerrado.

## 6. APK-005 / APK-006 — progreso y barras

**Pendiente. No se ha revisado.** Se prefiere no dar un estado sin verificarlo.

## 7. APK-007 — nombre en los resultados con ficha vigente

**Resuelto.** La tarjeta de persona habilitada mostraba el nombre; la de «no
habilitado» no. Es donde más falta hace: la persona está enfrente y el
encuestador tiene que confirmar que el bloqueo es de ella y no de un homónimo
antes de mandarla a coordinación.
