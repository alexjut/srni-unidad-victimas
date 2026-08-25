# Plan — informe de QA v2, el bloqueo de autorizaciones y lo que falta

> **Qué es esto.** El plan de trabajo que sale de tres cosas que llegaron juntas
> el 21-ago-2026: el informe **IGED-QA-C003 versión 2** de Jorge, el bloqueo de
> la pantalla de Autorizaciones reportado en vivo, y un aviso del DBA sobre una
> tabla y un índice creados en el Oracle de la UARIV.
>
> **Esto es análisis y plan, no ejecución.** Nada de lo que está acá se ha
> arreglado todavía. Lo que sí está hecho es el diagnóstico, y varias causas
> están **reproducidas**, no supuestas.
>
> Última verificación contra código y producción: **21-ago-2026**.

---

## Actualización — 25-ago-2026 (qué se cerró desde el plan)

El plan de arriba es del 21-ago. Desde entonces se ejecutó una tanda. Estado real
al 25-ago, verificado contra el código y las pruebas (backend **976** passed,
móvil **148** passed):

| # del plan | Qué era | Estado 25-ago |
|---|---|---|
| 0 / 1 | Autorizar a quien está solo en el universo + respaldo por número sin tipo | ✅ **Hecho** — materialización al autorizar (`_materializar_del_universo`) y búsqueda por `numero_documento_hash_sin_tipo`. Verificado contra producción. |
| 2 | Upsert de `registrar-desde-fuente` (500 duplicado / 400 tipo vacío / género-estado) | ✅ **Hecho** — `_resolver_colision`, tipo vacío por hash, homologación. (APK-002 backend) |
| 3 | Test de regresión del upsert | ✅ **Hecho** |
| 4 | Abrir la app sin red borra la sesión | ✅ **Hecho** — `cargarPerfil` distingue 401/403 de sin-red/5xx; perfil cacheado en keychain; 6 tests, verificado por mutación. |
| 5 | `obtenerToken()` en la precarga (el filtro del universo nunca bajaba) | ✅ **Hecho** — lee de SecureStore; 2 tests, verificado por mutación. |
| 6 | `interpretarError` en los catch de `busqueda.tsx` | ✅ **Hecho** — búsqueda, conformar hogar y alta manual muestran el mensaje del servidor + código HTTP; el detalle va al reporte. |
| 12 | Comando de backfill de `porcentaje_completado` | ✅ **Hecho** — `manage.py backfill_porcentaje` (por lotes, idempotente, `--dry-run`); 3 tests. **Falta CORRERLO en producción** antes del próximo reporte. |
| H-024/H-010/H-011/H-025/H-027 | Hallazgos WEB v2 | ✅ **Hecho** y con el frontend de Brando ya integrado a `main`. |

**Lo que sigue abierto** (del plan): #7 corregir `MOVIL_VERSION` en prod (dice
1.0.0), #8 aviso de versión en el login, #9 medir APK-019 en el servidor, #10
reporte de errores real en prod, #11 curar obligatorias de Asistencia, #13
pantalla de editar integrante, #16 `deploy-apk.sh` escribe la versión. Y **todo
lo de la APK necesita build nuevo + reprueba en dispositivo**.

**Correr en producción, pendiente:** `backfill_porcentaje` (#12) — avisar a Brando
que el número del panel va a moverse de golpe.

---

## 0. Lo urgente — no se puede autorizar a quien está solo en el universo

Se intentó autorizar una excepción para el documento `1115724047` desde el panel
y la pantalla respondió *«Sin coincidencia en el padrón»*. **No es un error de la
pantalla: es un límite de diseño que hasta hoy no se había visto.**

Consultado contra producción:

| Dónde se buscó | Resultado |
|---|---:|
| `Victima` por CC + número (lo que usa Autorizaciones) | **0** |
| `Victima` por número solo | **0** |
| `PersonaUniverso` por CC + número | **1** |

La persona **existe en el universo del RUV** (12.009.492 filas) pero **no en el
padrón operativo** (5.926.009). Es el 24 % que ya estaba documentado en
[`project_padron_cargado`](../../docs/arquitectura/adr-padron-universo-victimas.md).

Y hay un segundo muro detrás: `ExcepcionVigencia.victima` es una
**`ForeignKey` a `victimas.Victima` con `on_delete=PROTECT`**
(`apps/encuestas/models.py:435`). Aunque la pantalla la encontrara en el
universo, **no habría fila a la cual colgar la habilitación**.

### Dos defectos distintos, uno detrás del otro

**A. Autorizaciones no busca en el universo.** El endpoint arma
`doc_hash(tipo, documento)` y filtra solo `Victima`
(`apps/encuestas/habilitaciones.py:419-422`). Para las ~6 M de personas que están
en el RUV pero no en el padrón, la respuesta siempre va a ser «sin coincidencia».

**B. Autorizaciones tampoco tiene el respaldo por número sin tipo.** La búsqueda
de la APK sí lo tiene, y con un motivo escrito en el propio código:

> *1.126.615 víctimas (14,5 % del padrón) están cargadas SIN tipo de documento, y
> su hash de identidad se calculó con el tipo vacío. Sin este respaldo, buscarlas
> por «CC + número» respondía «no se encontró ninguna víctima con ese documento»
> —literalmente falso—.*
> — `apps/victimas/views.py`, `BuscarVictimaView`

Ese respaldo **no está** en `habilitaciones.py`. O sea que, aparte del caso de
hoy, hay **más de un millón de personas que sí están en el padrón y que la
pantalla de Autorizaciones tampoco puede encontrar.** Ese defecto no se
manifestó hoy —esta persona no está en `Victima` de ninguna forma— pero se va a
manifestar en cuanto se autorice a alguien cargado sin tipo.

### Qué habría que decidir

Autorizar a alguien que no está en el padrón implica **crearle la fila de
`Victima` primero**, que es exactamente lo que hace el alta manual en la APK.
Las opciones, en orden de menor a mayor alcance:

1. **Materializar desde el universo al autorizar.** Si el documento aparece en
   `PersonaUniverso`, la pantalla ofrece «registrar y autorizar»: crea la
   `Victima` con `estado_ruv='NO_VERIFICADO'` y `fuente_origen` del universo, y
   sobre esa fila cuelga la habilitación. Es coherente con lo ya decidido para
   el alta manual el 1-ago.
2. **Solo agregar el respaldo por número sin tipo** (defecto B). Resuelve 1,1 M
   de casos, no el de hoy. Es una hora de trabajo y no tiene contraindicación.
3. **No hacer nada y documentar el límite.** Habría que decirle a coordinación
   que a quien no esté en el padrón no se le puede autorizar excepción — y eso
   deja sin ruta a una parte grande de la población.

**Mi recomendación: 2 ya (es barato y no discute), y 1 como decisión de negocio.**
La pregunta de fondo para la supervisión es: *¿la excepción de vigencia aplica a
alguien de quien no tenemos caracterización previa registrada?* Porque si no está
en el padrón, tampoco hay ficha vigente que saltar — y quizá el camino correcto
no sea autorizar sino el alta manual, que ya funciona.

---

## 1. Qué versión probó QA — y por qué no vale la pena discutirlo

El rótulo **«1.2.0» cubre cuatro binarios distintos**. Recorriendo `app.json`
commit por commit:

| commit | fecha y hora | dice |
|---|---|---|
| `e5085eb` | 14-ago 12:20 | 1.2.0 |
| `ce429d3` | 14-ago 15:18 | 1.2.0 |
| `fdcd8bf` | 19-ago 10:50 | 1.2.0 |
| `9a88a0e` | 19-ago 13:34 | 1.2.0 |
| `ddc1c77` | 19-ago 18:16 | **1.2.1** |
| `c064fd2` | 19-ago 20:18 | **1.2.2** |

Del texto del informe se puede acotar la ventana pero no cerrarla: probaron algo
posterior al 14-ago 15:18 (porque dan APK-007 por corregido), y **no** la ventana
del 19-ago entre las 10:50 y las 18:16 (porque en esa la app forzaba 100 % y
ellos ven 0 %).

**No hay que decirles que probaron una versión vieja.** No se puede afirmar, y
sobre todo **no cambia nada**: los cinco hallazgos abiertos salen igual en la
1.2.2. Decirlo costaría credibilidad para nada.

Lo que sí es culpa nuestra y hay que reconocer: **la APK no muestra su versión en
ninguna pantalla**, y el endpoint `GET /api/movil/version/` responde hoy en
producción `{"version":"1.0.0","version_code":1}` mientras la app va en 1.2.2.
Nadie actualiza esa variable al publicar. La recomendación 6 de Jorge tiene toda
la razón, y ellos mismos perdieron una ronda entera por esto.

---

## 2. Diagnóstico de cada hallazgo abierto

### APK-002 · Conformar hogar falla · CRÍTICO · **causa raíz reproducida**

No es intermitente ni es de red. Son **tres defectos distintos** en
`POST /api/victimas/registrar-desde-fuente/`, reproducidos corriendo el caso
contra una base de prueba:

| Caso | Resultado |
|---|---|
| Persona con 1 sola fila en el padrón | `200` ✅ |
| **Documento duplicado** | **`500`** — `MultipleObjectsReturned` |
| **Sin tipo de documento** | **`400`** — «Este campo no puede estar en blanco» |
| **Sin género** | **`400`** — «"" no es una elección válida» |
| **Sin estado RUV** | **`400`** |
| Alta manual | `201` ✅ |

1. **El 500.** `apps/victimas/views.py:462` hace un `.get()` por hash + tipo y
   solo atrapa `DoesNotExist`. No hay restricción de unicidad sobre ese par
   —el padrón tiene duplicados **a propósito**— y hay **768.096 documentos
   repetidos** (15,6 %) que involucran a **1.765.375 personas**. La búsqueda ya
   resuelve esto con `ColisionDocumento`; el registro no.
2. **El 400 por tipo vacío** es exactamente el caso que QA aprobó como
   **APK-015** (el aviso de «coincide por número pero el tipo no es CC»). O sea:
   **la app puede encontrar a esa persona pero no puede registrarla.**
3. **Los 400 por género y estado RUV vacíos** son el mismo patrón que el propio
   repositorio ya documenta: *«el backend producía un payload que su serializer
   rechazaba con 400. En campo eso se leía como "Revisa la conexión"»*.

**Por qué el alta manual sí funciona** — y esto responde la pista de oro de QA:
el botón del alta manual llama a `conformarHogarAltaManual()`
(`busqueda.tsx:955`), que **solo hace `router.push`**: no habla con el servidor.
Y su payload se arma a mano en la pantalla. No funciona mejor: **esquiva los tres
defectos por construcción.**

**Y el arreglo del 14-ago se aplicó a la pantalla equivocada.** El texto que QA
fotografía vive en `busqueda.tsx:893` y `:1007`, dentro de un `catch` con texto
fijo. `interpretarError` solo se importa en `hogares/conformar.tsx` — la pantalla
siguiente, a la que con gente del padrón nunca se llega.

### APK-003 · Modo offline · CRÍTICO · **no se puede cerrar todavía**

QA no lo reprobó, y **no hay que pedirles que lo hagan aún**. Aparecieron dos
defectos que lo bloquean, ninguno reportado:

1. **Abrir la app sin red borra la sesión.** `authStore.ts:158-173`:
   `cargarPerfil()` llama a `authApi.me()` y su `catch` **no distingue un 401 de
   un error de red** — borra los dos tokens y deja `usuario = null`. Se invoca en
   cada arranque en frío. Mientras la app viva en memoria el offline anda; si el
   sistema la mata o la encuestadora la cierra en campo, **no vuelve a entrar
   hasta recuperar señal, y encima perdió el token.**
2. **El filtro del universo nunca se ha descargado en ningún teléfono.**
   `obtenerToken()` en `precarga.ts` lee el token de `defaults.headers.common` en
   vez de SecureStore, y falla en silencio. Toda la arquitectura offline de
   12,68 M está apagada y no se había notado.

Con APK-002 vivo, mandar a QA a probar el offline sería peor que no probar: la
prueba sale verde en pantalla y la jornada entera queda atascada en la cola.

### APK-004 · Editar/eliminar integrante · MEDIO

QA revisó exactamente donde dijo. El botón de **quitar** sí estaba en la build,
pero **solo en la pantalla de conformar**, no en el detalle del hogar. Y la
pantalla de **editar no existe** — el backend (`PATCH`) y el cliente móvil
(`hogaresApi.editarMiembro`) están listos desde el 14-ago, falta la interfaz.

Jorge pregunta en su recomendación 4 si esto estaba en el levantamiento inicial.
**Es una buena pregunta y hay que responderla**: si editar no estaba, se cierra
como fuera de alcance. Quitar desde el detalle del hogar sí hay que hacerlo,
porque la app ya lo promete por escrito.

### APK-005 · Sesión «Completada» en 0 % · MEDIO · **el arreglo no alcanza**

Dos cosas, y las dos hay que hacerlas:

1. **Una sesión ya COMPLETADA nunca se recalcula.** `porcentaje_completado` solo
   se escribe en `responder`, `responder_bulk` y `finalizar`, y los tres cortan
   si el estado es COMPLETADA. El arreglo del 19-ago **aplica solo hacia
   adelante**: la sesión que QA fotografió va a seguir en 0 % para siempre.
   Hace falta un comando de backfill.
2. **El instrumento de Asistencia humanitaria no tiene preguntas obligatorias.**
   Con denominador cero el porcentaje es 0 por definición, y ninguna sesión de
   ese instrumento va a llegar nunca a 100 %, con arreglo o sin él. Hay que
   curarlo contra el manual 14-MU.

### APK-019 · Falla intermitente al consultar el RNI · MEDIO

**Hay tres hipótesis y cero mediciones.** Lo que sí está confirmado es que
**estamos ciegos por diseño**, y esa es la razón por la que este hallazgo lleva
dos rondas sin acotarse:

- `errorReporter.ts:18` — `const BASE_URL = __DEV__ ? ... : null`. **En la APK de
  producción, todo `reportarError` es un no-op.**
- `LogAcceso.registrar` en `ConsultarFuenteView` corre **después** de la consulta
  exitosa: un fallo no deja fila.
- gunicorn arranca **sin `--access-logfile`**.
- Y el `catch` de la búsqueda (`busqueda.tsx:845`) es **pelado, sin variable de
  error**: cualquier fallo —400, 429, 500, 502, timeout— muestra el mismo texto.

**Antes de tocar nada hay que medir**, en el servidor:

```bash
docker logs --since 72h cz_nginx | grep 'consultar-fuente' | awk '{print $9}' | sort | uniq -c
docker logs --since 72h cz_backend | grep -iE 'Traceback|WORKER TIMEOUT|CRITICAL'
```

Un 499 con `request_time ≈ 15` es el cliente cortando; 500/502 es el backend. El
contraste que cierra el caso: cantidad de POST a `consultar-fuente/` en nginx
contra filas de `LogAcceso` con `accion='CONSULTA_FUENTE_EXTERNA'` en la misma
ventana — **la diferencia son exactamente las consultas que fallaron.**

---

## 3. El plan, en orden de riesgo para la operación

| # | Qué | Por qué va acá | Quién | Tamaño |
|---|---|---|---|---|
| 1 | **Respaldo por número sin tipo en Autorizaciones** | 1,1 M de personas que están en el padrón hoy no se pueden autorizar. Una hora, sin contraindicación. | Backend | 1 h |
| 2 | **Arreglar el upsert de `registrar-desde-fuente`**: veredicto de `ColisionDocumento` en vez de `.get()`; aceptar tipo vacío por el hash sin tipo; homologar género y estado RUV vacíos | Es el bloqueo real de campo (APK-002). Sin esto no hay operación, ni con red ni sin ella. | Backend | 1 día |
| 3 | **Test de regresión del upsert** — hoy `test_documento_duplicado.py` cubre `buscar/` y `consultar-fuente/` pero **no** `registrar-desde-fuente/`; por eso pasó | Sin esto el arreglo se cae en el próximo cambio del padrón | Backend | 2 h |
| 4 | **Que abrir la app sin red no borre la sesión** — distinguir 401 de fallo de red, y persistir el perfil | Hoy, cerrar la app en modo avión deja a la encuestadora **afuera del sistema en pleno campo**. Es pérdida de jornada. | Móvil | 4 h |
| 5 | **Arreglar `obtenerToken()` en la precarga** | El filtro del universo nunca se ha descargado. Toda la arquitectura offline está apagada. | Móvil | 1 h |
| 6 | **Usar `interpretarError` en los tres `catch` de `busqueda.tsx`** y mostrar el código HTTP | Convierte cada foto de QA en un diagnóstico. Sin esto, arreglar APK-019 es a ciegas. | Móvil | 3 h |
| 7 | **Corregir `MOVIL_VERSION` en el `.env` de prod** (hoy dice 1.0.0) y **poner la versión en el pie del login** | Sin esto la próxima ronda de QA se vuelve a perder. La corrección del `.env` se hace hoy, sin desplegar nada. | Infra + móvil | 3 h |
| 8 | **Aviso de versión nueva en el login**, con enlace de descarga | Lo pidió Jorge (rec. 6) y lo pidió el equipo. **Va después del 7**: hoy el aviso diría «está al día» cuando va tres versiones atrás. | Móvil | 4 h |
| 9 | **Medir APK-019 en el servidor** con los comandos de §2 | Barato, no rompe nada, y decide entre tres hipótesis. Hoy no hay datos. | Backend | 2 h |
| 10 | **Reporte de errores real en producción** y registrar también los fallos en `LogAcceso` | Es la razón por la que APK-002 y APK-019 llevan dos rondas sin acotarse | Backend + móvil | 1 día |
| 11 | **Curar las obligatorias de Asistencia** contra el manual 14-MU y recargar | Cierra APK-005 de verdad | Backend + negocio | 1-2 días |
| 12 | **Comando de backfill** de `porcentaje_completado`, por lotes, con `setsid nohup` del lado del servidor | Debe correr **antes** de que salga cualquier reporte de avance a la UARIV. Avisarle a Brando: el número va a cambiar de golpe en el panel. | Backend | 4 h |
| 13 | **Pantalla de editar/quitar integrante en el detalle del hogar** | Cierra APK-004 y cumple lo que la app ya promete | Móvil | 1 día |
| 14 | **Corregir `estado_hallazgos_qa_apk.md`**, que hoy marca APK-002 y APK-003 como resueltos | El documento vivo está mintiendo sobre los dos críticos | Documentación | 1 h |
| 15 | **Guion de prueba de APK-003 para QA** | Se manda **después** de 2, 4 y 5. Antes, le haríamos firmar un «cumplido» sobre trabajo que nunca sale del teléfono. | QA + móvil | 4 h |
| 16 | **Que publicar deje de depender de la memoria**: `deploy-apk.sh` escribe `MOVIL_VERSION` en el `.env` del servidor | Cierra el ciclo del aviso de versión | Infra | 4 h |

---

## 4. Lo que hay que decidir, y no es técnico

1. **¿La excepción de vigencia aplica a quien no está en el padrón?** Es la
   pregunta que destapó el bloqueo de hoy. Si no está en el padrón no hay ficha
   vigente que saltar — quizá el camino correcto sea el alta manual y no la
   autorización. **Bloquea el punto 0.**
2. **¿Qué preguntas de Asistencia humanitaria son obligatorias?** Cuatro de los
   ocho instrumentos no tienen ninguna. **Bloquea el punto 11.**
3. **¿Qué mostrar cuando el instrumento no tiene obligatorias?** Hoy sale `0 %`,
   que es falso y confunde.
4. **¿Se corre el backfill antes o después del próximo reporte a la UARIV?** Los
   promedios del panel van a cambiar de golpe.
5. **¿Editar integrante estaba en el levantamiento inicial?** Lo pregunta Jorge.
   Si no, se cierra como fuera de alcance y se ahorra un día.
6. **Cuántas cuentas con permiso de autorizar excepciones.** Hoy hay **una
   coordinación, una supervisión y una administración** para 1.158
   encuestadoras. Sigue abierto desde la semana pasada.

---

## 5. Lo que NO haría

- **No responder «probaron una versión vieja».** No se sostiene y no cambia nada.
- **No tocar timeouts ni gunicorn todavía.** El desajuste entre los 15 s del
  cliente y los 120 s del servidor es real y hay que alinearlo, pero **no explica
  APK-002** —ese fallo es determinista por dato— y para APK-019 no hay una sola
  medición. Primero el punto 9.
- **No cerrar APK-004 como «malentendido de QA».** Revisaron donde dijeron.
- **No pedirle a QA que reprobara el offline ahora.** Con APK-002 vivo saldría
  verde en pantalla y la jornada quedaría atascada en la cola.
- **No mandar el aviso de versión antes de arreglar el `.env`.** Diría «está al
  día» cuando no lo está.

---

## 6. Fuera de este plan — la tabla y el índice en MODELO

El DBA de la UARIV creó una tabla y un índice en el esquema **`MODELO`**. Lo
hicieron ellos, por su cuenta.

**Decisión (21-ago): no entra en este plan.** Se revisa cuando arranque el
trabajo de mejora de la base de datos. Queda anotado en el registro de defectos
del legacy — [`defectos_bd_legacy.md`](../oracle-legacy/defectos_bd_legacy.md) —
que es donde vive lo que se ataca post-migración.

Lo que habrá que pedirles cuando se retome: nombre de la tabla y del índice, el
DDL, sobre qué columnas va, para qué lo crearon y desde cuándo existe. Importa
porque `MODELO` es de donde sale el padrón y un índice nuevo puede cambiar el
plan de ejecución de las consultas de carga que ya afinamos.
