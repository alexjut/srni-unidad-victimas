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
| APK-005 | Sesión «Completada» con barra en 0 % | ✅ Resuelto | Brando (app) + Javier (API) |
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

- El backend ya recalcula al cerrar (`encuestas/views.py:279`,
  `recalcular_porcentaje()`), pero la app igual fuerza **100 % cuando el estado
  es `COMPLETADA`** — una sesión completada está completa por definición, y así
  no depende de que el número haya viajado bien.
- El valor se acota con `Math.max(0, Math.min(1, …))`. Sin eso, un porcentaje
  mayor que 100 dibujaba una barra **más ancha que su tarjeta**, que es el
  APK-006.
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

Tres cosas que quedaron mal en el arreglo del APK-003 y se corrigieron al
integrarlo:

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

---

## Qué falta, en orden

| | Tarea | Quién | Depende de |
|---|---|---|---|
| 1 | Probar APK-001 E2E en dispositivo (buscar → autorizar en el panel → «Ya la autorizaron» → conformar → sesión) | Brando | build nuevo |
| 2 | Verificar APK-003, APK-006 y APK-007 en dispositivo, en modo avión | Brando | build nuevo |
| 3 | Pantalla de corrección de integrante (APK-004) | Brando | nada — la API está lista |
| 4 | Documentar el alcance del modo offline y sus límites | Javier | nada |
| 5 | Llevar la regla de recaracterización al manual de usuario | Javier | nada |
