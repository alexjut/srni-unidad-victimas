# El control de vigencia retirado — qué se construyó y cómo se enciende

**Pedido el 11-sep-2026** por el equipo de caracterización, tras la reunión con la
Subdirectora encargada: **se retira el bloqueo por ficha vigente**. Cualquier
persona del padrón puede caracterizarse cuando el encuestador lo necesite, sin
pedirle permiso a nadie.

**Estado al 11-sep-2026: construido, probado y apagado.** Falta encenderlo.

> **El interruptor nace apagado a propósito.** La regla de los dos años la define
> el Manual de Usuario §5.1.1, que es documento misional. Retirarla es una
> decisión del proceso, no de la ingeniería, y encenderla deja huella con fecha y
> responsable en el servidor. Mientras nadie lo mueva, producción sigue como está.
> El correo que lo pide por escrito está en
> `docs/gestion/correo_retiro_control_vigencia_2026-09-11.md`.

---

## 1. Cómo se enciende

Una variable de entorno en el `.env` del servidor, y recrear los contenedores:

```bash
VIGENCIA_BLOQUEO_ACTIVO=False
```

No hace falta reconstruir la imagen, ni desplegar, ni tocar la APK. Volver atrás
es poner `True` —o borrar la línea— y recrear otra vez.

**Ni la APK ni el panel necesitan versión nueva para que el interruptor surta
efecto.** Está resuelto del lado del servidor a propósito: la precarga de la
jornada entrega el campo que la APK usa **sin señal** para decidir si deja
continuar, así que moverlo alcanza para que el cambio llegue al territorio en las
aplicaciones ya instaladas.

---

## 2. Qué cambia para el encuestador

**Nada distinto de lo que hace hoy.** Simplemente deja de encontrarse con la
pared.

| | Con el control activo | Con el control retirado |
|---|---|---|
| ¿Se puede caracterizar a cualquiera? | No | **Sí, siempre** |
| ¿Hace falta autorización previa? | Sí | **No** |
| ¿Hace falta radicado y soporte? | Sí | **No** |
| ¿Hace falta un perfil especial? | Sí | **No** |
| ¿El encuestador elige la ruta? | Sí | Sí, igual que hoy |
| ¿Funciona sin señal? | Sí | **Sí** |
| ¿Queda registro de quién recaracterizó y sobre qué? | Sí, como autorización | **Sí, como registro automático** |

**Lo que NO se abre.** Retirar la vigencia no es abrir todo. Quien está excluida
del RUV sigue bloqueada: eso es una decisión jurídica sobre la condición de
víctima, no un control de frescura del dato, y ninguna ruta de excepción la
habilitaba tampoco. Tampoco se levanta el caso del dato roto —marcada como no
habilitada y sin fecha que lo explique—, porque eso hay que seguir viéndolo.

---

## 3. El libro de registro

Una fila por cada caracterización hecha sobre una persona que todavía tenía ficha
vigente. La escribe el sistema al cerrar la encuesta, sin intervención de nadie:
sin pantalla, sin permiso y sin pedirle nada a quien está en campo.

Modelo `encuestas.RecaracterizacionVigente`.

| Dato | Para qué sirve el día que pregunten |
|---|---|
| Quién la hizo | Es la única forma de responder «¿quién?» |
| Cuándo | Ídem para «¿cuándo?» |
| Sobre quién | La persona, por su ficha |
| Ruta elegida | Es lo que el funcionario sí escoge, y el motivo más cercano que tendremos |
| Fecha de la caracterización anterior | Distingue «la recaracterizaron a los 22 meses» de «a los 3 días» |
| Cuántos días le faltaban para vencer | El mismo dato, ya calculado, para poder ordenar por gravedad |
| Sesión y hogar | Permite ir del registro a la entrevista concreta |

Con eso se responde, sin pedirle nada a nadie: **cuántas recaracterizaciones se
hicieron sobre ficha vigente, quién las hizo, en qué territorial y con cuánta
anticipación.** Es exactamente el informe que va a pedir control interno el día
que lo pida, y hoy no lo tendríamos.

### Por qué una tabla nueva y no la que ya existe

`ExcepcionVigencia` es un **permiso otorgado**: tiene quién lo autorizó, el
radicado del soporte y el motivo escrito por una persona. El registro nuevo no
tiene ninguna de las tres cosas, porque ya no hay autorizante ni soporte.

Meter las dos cosas en la misma tabla dejaría una mitad de las filas con el
sentido contrario a la otra, y dentro de un año nadie sabría cuáles
correspondieron a un fallo judicial verificado y cuáles a una recaracterización de
rutina. Las filas que ya existen son la evidencia del régimen anterior y hay que
poder seguir distinguiéndolas.

### El orden importa, y es frágil

Al cerrar la encuesta pasan dos cosas en este orden:

1. se escribe el registro — lee la fecha **anterior**;
2. se marca a las personas como caracterizadas — la **sobreescribe**.

Invertirlas es el cambio más natural del mundo, porque el registro «parece» que va
después. Si alguien lo hace, el libro se sigue llenando, nada falla, y todas las
filas dicen que faltaban cero días por vencer: el registro existiría y no serviría
para nada. Lo cuida
`apps/encuestas/tests/test_recaracterizacion_vigente.py::test_el_registro_guarda_la_fecha_anterior_no_la_de_hoy`.

---

## 4. El hogar: se actualiza el que ya existe

**No se crea un hogar nuevo. Se actualiza el que esa persona ya tiene.**

El hogar es la familia, no la entrevista. Crear uno cada vez que se recaracteriza
multiplicaría los hogares de la misma familia y volvería incontable cuántas
familias hay, que es una de las cifras que el sistema tiene que poder dar.

Cada caracterización es una **sesión** dentro de ese hogar, con su propio autor y
su propia fecha. La historia no se pisa: se acumula.

### Por qué esto no era «no hacer nada»

Había una segunda regla, independiente de la vigencia, que de no atenderse
quedaba siendo el nuevo obstáculo: **una persona solo puede tener un hogar
activo**. Si el hogar lo creó otro encuestador, el sistema respondía *«esta víctima
ya tiene un hogar activo registrado por otro encuestador. Solicita su reasignación
al supervisor»* y ahí se acababa el camino: **no hay pantalla de reasignación en
ninguna parte**.

Retirar la vigencia sin arreglar esto habría sustituido un bloqueo que se entendía
y tenía salida por otro que no se entiende y no la tiene. La queja habría vuelto en
una semana, con razón.

### Qué se cambió, en concreto

1. **Al conformar, el hogar existente se devuelve siempre**, sea de quien sea. Se
   acabó el 409.
2. **La propiedad NO se reasigna.** `creado_por` sigue siendo del primero:
   quitárselo le borraría de «mis encuestas» un trabajo que sí hizo. El hogar
   simplemente deja de tener dueño exclusivo.
3. **La autoría vive en la sesión.** Cada caracterización queda a nombre de quien
   la hizo, que es donde siempre debió estar.
4. **La visibilidad se amplía lo justo.** El encuestador puede abrir por
   identificador el hogar sobre el que está trabajando, y ve en su listado los que
   creó **más** aquellos donde tiene una sesión —si no, no podría volver a su
   propia entrevista a corregir nada—. **El listado completo no se abre**: son 2,5
   millones de fichas con datos personales de víctimas, y ver un hogar por estar
   trabajándolo no es lo mismo que poder navegarlos todos.

---

## 5. Lo que hay que vigilar

Dos encuestadores pueden terminar caracterizando el mismo hogar el mismo día sin
enterarse, y antes el bloqueo lo impedía de rebote. Ya no. El registro del §3 lo va
a mostrar —dos sesiones del mismo hogar, misma semana, autores distintos—, pero
mostrarlo es todo lo que va a hacer.

---

## 6. Qué quedó hecho

| Pieza | Dónde | Estado |
|---|---|---|
| Interruptor | `settings.VIGENCIA['BLOQUEO_ACTIVO']` | ✅ Apagado por defecto |
| Veredicto | `victimas/repository/base.py` — motivo `ELEGIBLE_SIN_CONTROL_VIGENCIA` | ✅ |
| Búsqueda en línea | `django_orm.buscar_por_documento` — el resumen refleja el veredicto | ✅ |
| Búsqueda sin señal | precarga: `habilitada` refleja el retiro | ✅ Sirve en APK ya instaladas |
| Universo del RUV | `_resumen_de_universo` | ✅ |
| Mock | `repository/mock.py` | ✅ Mismo árbol, para que desarrollo y capacitación se comporten igual |
| Registro | `encuestas.RecaracterizacionVigente` + migración 0010 | ✅ |
| Escritura al cerrar | `encuestas/views.py::_registrar_recaracterizaciones` | ✅ Antes de marcar las fechas |
| Salida del hogar | `hogares/views.py` — se acabó el 409 | ✅ |
| Pruebas | 12 + 9 + 10 + 5 casos nuevos; 932 en total | ✅ Verde |

### Piezas del régimen anterior — se dejan inertes, no se borran

| Pieza | Qué se hace |
|---|---|
| Tabla `ExcepcionVigencia` | Se conserva. Deja de crear filas cuando el control está retirado |
| API `/api/habilitaciones/` | Sigue respondiendo consultas del histórico |
| Pantalla de autorizaciones | Pasa a ser consulta del histórico |
| Permiso `puede_autorizar_excepciones` | Se conserva en el modelo, sin uso |

**Por qué no se borra:** si el área funcional repone la regla dentro de seis meses
—y estas decisiones se reponen—, reponerla cuesta mover una variable. Borrarlo todo
hoy convierte esa vuelta atrás en volver a construirlo.

---

## 7. Lo que sigue

| | Qué | Cuándo |
|---|---|---|
| 1 | **Encender el interruptor en producción** y verificar en la APK | Antes del 15 |
| 2 | Consulta de recaracterizaciones para el informe de control | Después de encender |
| 3 | Prueba de la escritura al Oracle del sistema anterior con la segunda caracterización del mismo hogar | En paralelo |
| 4 | Ajuste del Manual de Uso y del material de capacitación | Antes de la siguiente jornada |

### Sobre el punto 3, que es el único con trabajo de verdad detrás

**El Oracle del sistema anterior tiene su propia regla de vigencia.** Que SICAV
deje de bloquear no significa que el destino acepte la segunda escritura: los
procedimientos `GIC_*` pueden rechazarla o —peor— aceptarla en silencio y no
escribir nada, comportamiento que ya está documentado.

Hay que probarlo contra producción con un caso real. Conviene recordar que la
escritura automática al Oracle está **apagada** por su propio interruptor
(`ORACLE_SYNC_AUTOMATICA`, también `False` por defecto), así que hoy cerrar una
encuesta no escribe allá de todos modos.

### Sobre el punto 4

El material de las tres jornadas —un caso de estudio completo, una sección del
Manual de Uso y 2 de las 10 preguntas del cuestionario— está construido sobre el
flujo de autorización. Si el interruptor se enciende antes del 15, ese material
queda enseñando un procedimiento que ya no existe. Hay dos salidas y las dos son
válidas; lo que no se puede es no elegir:

- **encender después del 29** y dictar las tres jornadas con lo que hay;
- **encender antes del 15** y rehacer esas tres piezas del material, que son
  medio día de trabajo.

---

## 8. Lo que este plan no resuelve, y conviene decirlo

**Sin autorización no hay motivo escrito.** La ruta que elige el encuestador es lo
más cercano que vamos a tener, y es una lista de opciones, no una explicación. El
día que alguien pregunte *por qué* se recaracterizó a una persona a los tres días,
el sistema va a poder decir quién y cuándo, pero no por qué. Es una consecuencia
aceptada de la decisión, no un defecto del diseño.

**El registro no impide nada.** Es un libro, no una puerta. Si la operación empieza
a recaracterizar masivamente, el sistema lo va a anotar con precisión y no va a
hacer nada al respecto. Que alguien mire ese libro es una decisión de supervisión,
y por eso el punto 2 del §7 —la consulta— importa más de lo que parece: **un
registro que nadie consulta es lo mismo que no tenerlo.**
