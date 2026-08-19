# Hallazgos de QA de la APK — documento vivo

Informe de origen: **IGED-QA-C003**, *Revisión de regresión — aplicación móvil
SICAV (APK) SRNI*, agosto 2026.

Este es el **único** documento de estado de esos hallazgos. Continúa a
`estado_hallazgos_qa_2026-08-14.md` (misma historia, ahora sin fecha en el
nombre porque se sigue actualizando) y absorbe el checklist
`docs/QA/checklist-qa-apk-agosto-2026.md` que Brando armó el 18-ago: tener dos
listas del mismo informe garantizaba que una quedara mintiendo.

Regla del documento: lo que dice «resuelto» está **verificado contra el código**
y con pruebas. Lo que dice «pendiente» no se ha tocado, y se dice por qué.

**Última actualización:** 19-ago-2026.

---

## Estado

| # | Hallazgo | Estado | Quién |
|---|---|---|---|
| APK-001 | Ruta de excepción no avanzaba al instrumento | ✅ Resuelto (de otra forma) · ⬜ falta E2E en dispositivo | Javier |
| APK-002 | «No se pudo registrar» al conformar hogar | ✅ Resuelto | Javier |
| APK-003 | Modo offline no funcionaba | ✅ Resuelto (hogares, encuestas, detalle) · ⚠️ falta comunicar el alcance | Brando + Javier |
| APK-004 | No se podía editar ni eliminar integrante | ✅ Quitar (API + app) · ⬜ corregir en la app | Javier |
| APK-005 | Sesión «Completada» con barra en 0 % | ⚠️ Abierto: la causa es `recalcular_porcentaje` sin skip-logic (§6) | Javier |
| APK-006 | Barras de progreso desbordan la tarjeta | ✅ Resuelto | Brando |
| APK-007 | No mostraba el nombre en «No habilitado» | ✅ Resuelto · ⬜ falta verlo en dispositivo | Javier |
| APK-008 … 013 | Autenticación, alerta de vigencia, exactitud RNI, captura Ruta General, validación de campos, diseño del mecanismo de excepción | ✅ Cumplidos según el propio informe | — |
| — | Regla de recaracterización: ¿libre o por excepción? | ⚠️ Definida; falta llevarla al manual | Javier |

Todo lo de la APK necesita un **build nuevo** para llegar a campo. La versión en
curso es la 1.2.x.

---

## 1. APK-001 — la ruta de excepción bloqueaba la recaracterización

**Resuelto, pero no como se propuso.** No se arregló el botón: se cambió el
flujo, porque el problema de fondo era otro. El botón pedía una **foto del
soporte** y el encuestador no tiene ese documento — el fallo o la tutela llegan
por canal institucional al nivel central.

Ahora la excepción la autoriza coordinación desde el panel (**Autorizaciones**),
y el celular solo la consume: la ve en la búsqueda o en la precarga de la
jornada, y se consume al finalizar la encuesta.

> **Dato incómodo:** ese endpoint **nunca funcionó**, ni antes del cambio.
> Escribía la auditoría con `LogAcceso.objects.create(..., ip=...)` y ese campo
> se llama `ip_origen`, así que toda llamada moría en 500 antes de responder. QA
> reportó un bloqueo real cuya causa no era la que parecía.

**Del lado del servidor no queda nada pendiente.** El checklist del 18-ago pedía
que «`POST /api/victimas/buscar/` refleje la habilitación»; ese endpoint no es el
que usa la APK —usa `POST /api/victimas/consultar-fuente/`— y la habilitación ya
se evalúa ahí, en `apps/victimas/repository/base.py:399`
(`evaluar_elegibilidad` → `_buscar_habilitacion`), con pruebas en
`apps/encuestas/tests/test_habilitaciones.py`.

**Falta:** correr el flujo completo en un teléfono real — buscar con vigencia,
autorizar desde el panel, tocar «Ya la autorizaron», conformar hogar y crear la
sesión.

## 2. APK-002 — error «intermitente» al conformar hogar

**Resuelto.** El error no era intermitente: lo era el mensaje. La app le mostraba
al encuestador el JSON crudo del servidor con un `JSON.stringify(detalle)`
guardado detrás de un `typeof detalle === 'object'`. Y como en JavaScript
`typeof null` también es `'object'`, una respuesta con cuerpo vacío le mostraba
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

Los documentos concretos del informe (Rubiela Díaz Triana, Sara Nicol Salazar
Preciado) caen en el 409 de «hogar de otro encuestador»: eso ahora se lee.

## 3. APK-003 — trabajo sin conexión

**Resuelto en las tres pantallas que QA reportó.** Brando lo cerró el 18-ago:

- **Hogares** (`app/(main)/hogares/index.tsx`) — sin red ya no se saltaba los
  hogares que sí estaban en el teléfono; ahora los pinta desde SQLite. Y el
  `EmptyState` de «Sin hogares» se suprime cuando el servidor falló: ese cartel
  con su botón «Nuevo hogar» era una **invitación a duplicar** un hogar que ya
  existía.
- **Encuestas** (`app/(main)/encuestas/index.tsx`) — si el API falla, lee los
  borradores locales y resuelve el nombre del instrumento desde el bundle, con
  banner de «sin conexión».
- **Detalle de sesión** (`app/(main)/encuestas/[sesionId].tsx`) — busca el
  borrador por `sesion_id`, muestra sus respuestas guardadas y deja continuar el
  formulario. Sirve porque pasa `instrumentoId`, que es lo único con lo que
  `formulario/index` puede resolver el perfil sin red.

Tres correcciones sobre ese trabajo, el 19-ago (ver §8).

**Falta la definición formal**, que es justo lo que pide QA. Hoy la app opera sin
señal con: padrón local, filtro del universo del RUV (12,68 M de personas en
21,7 MB), hogares y sesiones persistidos en SQLite con cola de sincronización, y
las excepciones de vigencia. **Sí es un requisito soportado.** Falta comunicarlo
por escrito y con sus límites — el principal: una habilitación otorgada después
de que arrancó la jornada no llega hasta la sincronización siguiente. La búsqueda
RNI sin red seguirá sin funcionar, y eso es correcto: depende del servicio
central.

## 4. Regla de negocio de recaracterización

**Definida el 14-ago:** por **excepción**, nunca libre. Tres rutas la permiten
(Manual §5.1.1), la autoriza coordinación con radicado y motivo, y es de un solo
uso. Está documentada en
[`excepcion_vigencia_desde_el_front.md`](../operacion/excepcion_vigencia_desde_el_front.md).

**Falta llevarla al manual de usuario**, que es lo que QA pide expresamente.

## 5. APK-004 — editar y eliminar integrantes

**Quitar: resuelto, API y app.** No existía en ninguna de las dos — quien se
equivocaba al capturar quedaba con el error adentro del hogar para siempre.

```
DELETE /api/hogares/{id}/miembros/{miembro_id}/    quitar
PATCH  /api/hogares/{id}/miembros/{miembro_id}/    corregir
```

En la app cada integrante tiene su botón de quitar
(`hogares/conformar.tsx:207`), con confirmación que incluye el nombre. Tres
guardas, cada una con su motivo:

- **Al autorizado no se le toca** — es el titular; quitarlo deja el hogar sin
  dueño. Para eso está «cambiar autorizado».
- **No se quita de un hogar ya caracterizado** — ese integrante forma parte de
  algo ya reportado. Eso es una novedad hacia el legado, no una corrección de
  captura. Con la encuesta *abierta* sí se puede: es cuando el encuestador se da
  cuenta del error.
- **No se quita lo que aún no sincronizó** — su alta sigue en la cola y borrarlo
  solo de la pantalla lo haría reaparecer al sincronizar.

Quitar **borra la fila** a propósito: atiende «esta persona nunca debió estar».
«Ya no vive en el hogar» es otra cosa y sigue sin resolverse.

**Editar en la app: pendiente, y no depende del backend.** `PATCH` está listo y
probado, y el cliente móvil ya expone `hogaresApi.editarMiembro()`
(`src/api/hogares.ts:67`). Lo único que falta es la pantalla de corrección: al
tocar un integrante, abrir el modal con sus datos precargados. El checklist del
18-ago lo daba como bloqueado por el backend; no lo está.

## 6. APK-005 / APK-006 — progreso y barras

**Resuelto.** Eran dos síntomas del mismo descuido: el valor del progreso se le
pasaba crudo a la barra.

- El valor se acota con `Math.max(0, Math.min(1, …))`. Sin eso, un porcentaje
  mayor que 100 dibujaba una barra **más ancha que su tarjeta**, que es el
  APK-006. Ese clamp queda.
- El arreglo original también forzaba **100 % cuando el estado era
  `COMPLETADA`**. Eso se retiró el 19-ago: tapaba el síntoma y encima mentía.
  El backend **no exige completitud para cerrar** (`finalizar` guarda el
  porcentaje real junto a `COMPLETADA`) y la app tampoco bloquea el cierre, así
  que una entrevista interrumpida a mitad —la víctima se retiró— se mostraba al
  100 %. El panel web nunca aplicó ese override: la misma sesión se veía
  distinta según quién la mirara.
- **El APK-005 sigue abierto por el lado del backend**, y ahora se ve. La causa
  de fondo es `SesionEncuesta.recalcular_porcentaje`
  (`apps/encuestas/models.py:120-152`): divide por **todas** las obligatorias
  del instrumento **sin evaluar skip-logic**, así que cuenta como faltantes
  preguntas que la regla ocultó. Por eso una sesión legítimamente terminada se
  guarda en 55 %, o en 0 % si respondió pocas. El móvil ya lo calcula bien con
  `calcularProgresoOffline` (obligatorias *visibles*); falta llevar ese criterio
  al servidor.
- Se reemplazó el `ProgressBar` de react-native-paper por
  `src/components/AnimatedProgressBar.tsx`, con `overflow: 'hidden'` en el track.
  La animación usa `Animated` nativo con `useNativeDriver: false`, que es
  obligatorio al animar `width`.

## 7. APK-007 — nombre en los resultados con ficha vigente

**Resuelto.** La tarjeta de persona habilitada mostraba el nombre; la de «no
habilitado» no. Es donde más falta hace: la persona está enfrente y el
encuestador tiene que confirmar que el bloqueo es de ella y no de un homónimo
antes de mandarla a coordinación.

**Falta** verlo en un dispositivo.

## 8. Correcciones sobre el trabajo offline (19-ago)

Al integrar el APK-003 se corrigieron **doce** defectos del propio arreglo, en
tres pasadas. La primera salió de leer el diff (3); la segunda, de una revisión
adversarial de cinco frentes sobre el rango completo (5); la tercera y la cuarta
buscaron regresiones introducidas por los arreglos mismos, y **las dos
encontraron algo** (2 y 2). Cada hallazgo pasó por dos verificadores
independientes con ángulos distintos; ninguno pudo refutarse.

Que cada pasada encontrara menos —5, 2, 2— y que las dos últimas encontraran
defectos *de los arreglos* dice algo que conviene anotar: en este flujo, un
arreglo que se ve obvio en su propio archivo se rompe tres saltos más abajo. La
cadena captura → SQLite → cola → servidor tiene demasiados estados como para
razonarla de a un archivo por vez.

Vale la pena decir por qué son todos la misma familia de error: el trabajo
offline se construyó **mostrando** lo que hay en SQLite, pero las condiciones
que deciden qué mostrar y qué borrar se escribieron pensando en el camino con
red. Cada vez que una de esas condiciones se equivocó, lo que desapareció fue
trabajo ya capturado — y lo que sigue después de que una encuestadora cree que
perdió una entrevista es volver a levantarla con la víctima enfrente.

### Lo que se vio leyendo el diff

1. **La tarjeta le mentía a la encuestadora.** Al empezar a mostrar los hogares
   sin red se los pintaba a todos con la tarjeta de «pendiente», que tiene
   **«Pendiente sync» escrito fijo**. Un hogar ya sincronizado (`id_servidor`
   presente, `estado_sync = 'enviado'`) le decía que su trabajo no había subido.
   Eso es peor que el defecto original: antes no lo veía, ahora lo veía mal.
   Ahora la etiqueta sale del dato: *Guardado* / *Pendiente sync* /
   *Error de envío*.
2. **El mismo hogar tenía dos códigos.** La tarjeta local mostraba y navegaba con
   `id_local`; con red, ese mismo hogar aparece con el id del servidor. Ahora
   manda `id_servidor` apenas existe, que es el que también ve el panel web.
3. **Tocar un borrador no lo continuaba.** Llevaba a `/(main)/caracterizar`, que
   es el *selector de instrumento*: la encuestadora tocaba su trabajo a medias y
   la app le pedía volver a elegir todo desde cero. Ahora va al formulario con
   `borradorId`, que es el hilo del flujo offline.

### Lo que encontró la revisión adversarial

4. **El borrador de ayer se partía en dos.**
   `findBorradorOfflinePorHogarInstrumento` filtraba por `sesion_id IS NULL`
   «para no colisionar con el camino online». Pero apenas la cola crea la sesión,
   `marcarSincronizado` le pone el `sesion_id` al borrador: desde ese momento la
   consulta ya no lo encontraba. Volver a entrar por ese hogar sin red creaba un
   borrador **en blanco** —todos los capítulos en 0/N— y al sincronizar quedaban
   dos filas con el mismo `sesion_id`; como `findBySesionId` usa `getFirstAsync`,
   devolvía una cualquiera y **media entrevista dejaba de verse**. El WHERE ahora
   busca el borrador vivo de ese hogar e instrumento, vinculado o no.
   *Es el más grave de los ocho: es el único que esconde respuestas ya guardadas.*
5. **La lista de hogares borraba copias locales de SQLite.** La reconciliación
   trataba la respuesta del servidor como censo: si una fila ya sincronizada no
   venía en ella, ejecutaba `eliminarPorIdLocal` — un DELETE definitivo. Pero esa
   respuesta nunca fue un censo: es **una página de 20** (`PAGE_SIZE=20`, sin
   seguir `next`) y encima filtrada por `?estado=`. Con 21 hogares, o tocando el
   segmento «Activo» con un hogar en BORRADOR, la copia local se borraba sola —
   justo la fila que hace posible la tarjeta offline. Se retiró la purga entera:
   quien limpia es `purgarSincronizados()`, que solo corre con la cola vacía.
6. **Los borradores solo se veían cuando el servidor fallaba.** La lectura de
   SQLite estaba dentro de `if (!servidorOk)`. Un borrador que aún no subió no
   está —por definición— en la respuesta del servidor, así que con señal la
   entrevista capturada esa mañana no aparecía por ningún lado, sin mensaje; y si
   su ítem de cola había quedado en `error`, era invisible de forma permanente.
   Ahora se leen siempre y el dedupe por `sesion_id`, que era código muerto, pasa
   a hacer su trabajo.
7. **La misma mentira del punto 1, en encuestas.** La tarjeta de borrador tenía
   «Pendiente sync» escrito fijo, también para lo ya subido. Ahora sale de
   `sesion_id`: *Guardado* / *Pendiente sync*.
8. **`listarBorradores` escondía lo que tenía sesión creada pero no subida.**
   Excluía `estado != 'SINCRONIZADO'`, y ese estado **no** significa «ya subió
   todo»: lo escribe `marcarSincronizado` cuando la cola logra crear la sesión,
   con las respuestas todavía pendientes. Ahora excluye `COMPLETADO`, que sí es
   el cierre real.

### Lo que encontró la segunda pasada, sobre los arreglos mismos

Una segunda revisión adversarial —esta vez buscando **regresiones que los
arreglos acabaran de introducir**— encontró que el punto 8 estaba mal resuelto,
y era grave:

9. **`COMPLETADO` significaba dos cosas y yo elegí la equivocada.** El punto 8
   cambió el filtro a `estado != 'COMPLETADO'` dando por hecho que ese estado
   quería decir «el servidor confirmó el cierre». No: `encolarFinalizar`
   (`formulario/index.tsx:486`) lo escribía **en la rama offline**, apenas se
   encolaba el FINALIZAR y antes de que nada saliera del teléfono. O sea que la
   encuestadora finalizaba una entrevista en modo avión, la app le decía «quedó
   cerrada en el dispositivo», entraba a Encuestas y leía **«Sin sesiones»**. Y
   si volvía a entrar por ese hogar,
   `findBorradorOfflinePorHogarInstrumento` —que ahora también excluye
   COMPLETADO— tampoco la encontraba: formulario en blanco y un segundo
   CREAR_SESION en cola. La idempotencia del backend no protege ahí, porque
   `create()` excluye las sesiones ya COMPLETADAS.

   Se arregló separando el hecho en dos, que es lo que siempre fueron:
   **`CERRADO_LOCAL`** (la encuestadora cerró, sigue en cola) y **`COMPLETADO`**
   (el servidor confirmó). Los dos WHERE quedan correctos tal como estaban, y
   `purgarSincronizados` sigue borrando solo lo realmente cerrado. Va con
   **migración de esquema (v13)** que reclasifica las filas que ya quedaron mal
   en los teléfonos de campo: se reconocen porque su FINALIZAR_SESION sigue en
   la cola.

10. **El filtro de estado no se aplicaba a los borradores.** Los
    SegmentedButtons filtran en el servidor; como ahora los borradores se leen
    siempre, al tocar «Completadas» salían arriba las entrevistas a medias. El
    filtro dejaba de significar algo, y peor: invitaba a darlas por cerradas.
    Ahora se aplica también localmente.

La misma pasada revisó los otros cuatro cambios y **no encontró defecto** en
ellos.

### Y lo que encontró la tercera, sobre el arreglo de la segunda

11. **Volver a cerrar lo ya cerrado envenenaba la cola del teléfono.** Al hacer
    que el borrador `CERRADO_LOCAL` volviera a ser alcanzable (que es lo que
    corresponde: es trabajo suyo), quedó alcanzable también el botón
    **«Finalizar caracterización»** — `formulario/index.tsx` no leía el estado
    del borrador. Un segundo toque encolaba un segundo FINALIZAR_SESION, el
    servidor lo rechaza con **400 «La sesión ya está completada»**, y como los
    4xx no se reintentan ese ítem quedaba en `error` **para siempre**.

    Y eso no era cosmético. `contarPendientes()` cuenta los `error`, así que con
    un solo ítem atascado:
    - `purgarSincronizados()` no vuelve a correr nunca — el `.db` crece sin
      techo;
    - el logout **deja de borrar la PII capturada** de víctimas y hogares
      (`authStore.ts:143` solo limpia todo si la cola quedó vacía);
    - el indicador de sincronización queda en rojo permanente, así que ella no
      puede distinguir lo que de verdad falta subir — y lo esperable es que
      recapture.

    Un teléfono así no se recuperaba sin reinstalar. Se arregló en dos capas:
    - **`sincronizacion.ts`** — cerrar una sesión que ya estaba cerrada cuenta
      como éxito, no como error. Y no se decide leyendo el texto del mensaje: se
      le pregunta al servidor por el estado de la sesión. Cualquier otro 400
      sigue su camino. Esto solo ya destraba todas las rutas, incluida la
      carrera de recuperar señal con el FINALIZAR ya encolado.
    - **`formulario/index.tsx`** — sobre una entrevista ya cerrada la pantalla
      no ofrece el botón: muestra «Caracterización cerrada. Se enviará sola
      cuando haya conexión». Puede revisar sus respuestas, no re-encolar el
      cierre.

12. **La migración v13 dejaba afuera el ítem en vuelo.** Reclasificaba mirando
    `estado IN ('pendiente','error')`, pero un teléfono que se apagó con el
    FINALIZAR en curso deja la fila en `'enviando'`, y `resetearBloqueados()`
    corre *después* de la migración. Ahora los tres estados cuentan.

Sobre las pruebas: **9 de regresión** en
`src/db/__tests__/borradoresDao.test.ts` y **3** del cierre doble en
`sincronizacion.test.ts`. Todas comprobadas **por mutación**: revirtiendo los
arreglos a mano, fallan (4 y 1 respectivamente). Una prueba que no falla cuando
el defecto vuelve no es una prueba. Móvil: **133 tests**, `tsc` limpio.

### Un hilo suelto que quedó a la vista

`purgarSincronizados()` solo corre si la cola quedó **totalmente** vacía, y
`contarPendientes()` cuenta `estado IN ('pendiente','error')`. O sea que **un
solo ítem en `error` congela el mantenimiento del `.db` para toda la vida del
dispositivo**: nunca más se purga nada. Está fuera del alcance de este rango,
pero conviene mirarlo antes de que los teléfonos de campo lleven meses de uso.

---

## Qué falta, en orden

| | Tarea | Quién | Depende de |
|---|---|---|---|
| 1 | Probar APK-001 E2E en dispositivo (buscar → autorizar en el panel → «Ya la autorizaron» → conformar → sesión) | Brando | build nuevo |
| 2 | Verificar APK-003, APK-006 y APK-007 en dispositivo, en modo avión | Brando | build nuevo |
| 3 | Pantalla de corrección de integrante (APK-004) | Brando | nada — la API está lista |
| 4 | **APK-005 de fondo:** que `recalcular_porcentaje` evalúe skip-logic, como ya hace el móvil | Javier | nada |
| 5 | Documentar el alcance del modo offline y sus límites | Javier | nada |
| 6 | Llevar la regla de recaracterización al manual de usuario | Javier | nada |
| 7 | Que un ítem en `error` no congele `purgarSincronizados()` para siempre | Javier | nada |
