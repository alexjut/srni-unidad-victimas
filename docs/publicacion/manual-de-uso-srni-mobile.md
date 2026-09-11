# Manual de Uso — SICAV Móvil (App de caracterización)

**Versión del manual:** 1.3
**Fecha:** 2026-09-11
**Dirigido a:** Encuestadores de caracterización UARIV
**Aplicación:** SICAV Móvil — Android **1.2.5**

> **Qué cambió frente a la versión 1.2.** **Se retiró el control de vigencia.** Una
> persona ya caracterizada se puede volver a caracterizar cuando la operación lo
> necesite: la aplicación lo avisa pero **no lo detiene**, y desaparece el trámite de
> autorización con radicado y soporte. Además se explica cómo **retirar del hogar** a
> quien ya no pertenece a él. Si su manual dice 1.2 o menos, está desactualizado.

---

## 1. Requisitos previos

- Teléfono Android 8 o superior.
- **Código de usuario y contraseña** asignados por el administrador del SRNI.
  La app no permite auto-registro.
- Conexión a internet para iniciar sesión y sincronizar. **La entrevista puede
  realizarse sin conexión** (ver sección 9).
- La **versión instalada** debe ser la **1.2.5** o superior. Se lee en la propia
  pantalla de ingreso, bajo el formulario. Si ve una versión anterior, descargue de
  nuevo la aplicación desde el enlace institucional antes de salir a campo.

## 2. Inicio de sesión

1. Abra la app. Verá la pantalla de ingreso con la franja institucional GOV.CO.
2. Digite su **código de usuario** y su **contraseña** (el ícono de ojo
   muestra/oculta la contraseña).
3. Toque **Ingresar**.
4. Si su teléfono tiene huella o rostro configurado, marque **Activar ingreso
   con huella o rostro** al iniciar sesión. En los siguientes ingresos aparecerá
   el botón **Huella digital** para entrar sin digitar la contraseña. La
   biometría se valida solo en su teléfono.

> **¿Olvidó su contraseña?** No existe recuperación desde la app: contacte al
> administrador del sistema. El cambio de contraseña se realiza por el panel
> web del SRNI.

> **Confirme la versión antes de salir a campo.** En la parte inferior de la pantalla
> de ingreso aparece la versión instalada. Cuando reporte una incidencia, incluya ese
> número: sin él no se puede saber si el problema ya está corregido.

## 3. Pantalla de inicio

Tras ingresar verá **"Hola, {su nombre}"** con:

- **Indicador de sincronización** (esquina superior): `✓ Al día`,
  `N pendiente(s)` (toque para sincronizar), `Sin conexión` o `N error(es)`.
- **Crear hogar y entrevista** — acceso directo al flujo completo.
- **Acciones:** Búsqueda RNI · Hogares · Caracterizaciones.
- **Sistema:** Mis reportes · Estado de sincronización.
- **Cerrar sesión** (al final).

Las opciones visibles dependen de los permisos de su perfil.

## 4. Flujo completo de una caracterización

```
Búsqueda RNI → Conformar hogar → Elegir instrumento →
Ubicación de atención → Responder capítulos → Finalizar sesión
```

### Paso 1 — Buscar a la persona (Búsqueda RNI)

1. Entre a **Búsqueda RNI** (o a "Crear hogar y entrevista").
2. Seleccione el **tipo de documento** (CC, TI, RC, CE, PA) y digite el
   **número de documento**.
3. Elija la **ruta de entrevista**: General, Acciones constitucionales,
   Modificación de núcleo o Especial.
4. Toque **Consultar RNI**. Resultados posibles:
   - **Persona habilitada (tarjeta verde):** verá nombre, estado RUV,
     pertenencia étnica, discapacidad y municipio. Toque **Conformar hogar**.
     Si la persona ya tiene hogar registrado, la app le ofrece **Ver hogar
     registrado** para continuar con sus caracterizaciones.
   - **No habilitada (tarjeta naranja):** la persona existe pero no puede ser
     caracterizada; la tarjeta indica el motivo y muestra su nombre. Hoy los
     motivos son dos: que esté **excluida del RUV** —ninguna ruta la habilita— o
     que el número de documento sea un valor de relleno que no identifica a
     nadie. **Tener una caracterización vigente ya no es uno de ellos.**
   - **No encontrada (tarjeta gris):** toque **Registrar y caracterizar**.
     Se abre el formulario **Alta manual**: diligencie nombres, apellidos,
     fecha de nacimiento y género, y toque **Agregar víctima**.

> La búsqueda requiere conexión a internet.

#### Si la persona ya fue caracterizada

Una caracterización se considera **vigente** durante dos años. Es un criterio de la
entidad para no repetir el esfuerzo de campo.

**Desde septiembre de 2026 eso no lo detiene.** Si la persona ya fue caracterizada, la
aplicación se lo dice —con la fecha de la caracterización anterior— y **usted continúa
normalmente**. No hay autorización que pedir, ni radicado que conseguir, ni soporte que
adjuntar, ni nadie a quien esperar.

**Qué sí debe hacer.** Léale el aviso a la persona y confirme con ella que tiene sentido
volver a caracterizarla. El sistema no va a preguntárselo, así que ese criterio queda en
sus manos.

**Qué NO debe hacer.** No use el **Alta manual** para una persona que sí está en el
padrón, ni el documento de otra persona. El alta manual es solo para quien no aparece:
usarla de otro modo crea una ficha duplicada que después hay que depurar a mano.

> **Queda registrado, y no tiene que hacer nada para eso.** Cuando cierra una
> caracterización hecha sobre una ficha que aún estaba vigente, el sistema anota solo la
> fecha, quién la hizo y con cuánta anticipación. No hay pantalla que llenar y usted no
> interviene. Sirve para que la entidad pueda explicar, si alguien lo pregunta, por qué
> una caracterización se actualizó antes de los dos años.

> **Funciona sin señal.** Esto vale igual en campo y sin conexión. Lo único que conviene
> es **iniciar sesión con señal antes de salir**, porque es ahí cuando el teléfono
> descarga la información actualizada del padrón.

### Paso 2 — Conformar el hogar

1. La persona buscada queda registrada automáticamente como **★ AUTORIZADO**
   (primer integrante del hogar).
2. Para cada integrante adicional diligencie: tipo y número de documento,
   nombres y apellidos, fecha de nacimiento y **rol** (miembro, tutor o cuidador
   permanente). El **parentesco** y el **género** ya no se piden aquí: se
   registran durante la entrevista, en el Capítulo B (Datos básicos). Si elige
   **tutor** o **cuidador permanente**, la app le exigirá **adjuntar la
   constancia** que acredita ese rol antes de continuar. Toque **Agregar al
   hogar** y repita.
3. Al terminar, toque **Continuar a caracterizaciones**.

> Regla del sistema: una persona pertenece a **un solo** hogar. Si ya tenía uno
> registrado, la aplicación le muestra **ese mismo hogar con su familia**, incluso
> si lo conformó otro encuestador. Es correcto y no hay que pedir nada: el hogar es
> de la familia, no de quien lo creó, y cada caracterización queda a nombre de
> quien la hizo.

#### Cuando la familia ya no es la misma

Al actualizar la caracterización de una familia que ya estaba registrada, lo normal
es que algo haya cambiado: nació un niño, alguien murió, alguien se fue de la casa.

- **Alguien nuevo:** tóquelo con **Agregar al hogar**, como cualquier integrante.
- **Los que ya estaban:** aparecen solos en la lista. **No los capture de nuevo**;
  si lo hace, la persona queda dos veces en el hogar y hay que depurarlo a mano
  después.
- **Alguien que ya no pertenece al hogar:** entre al hogar y use **Retirar del
  hogar** en esa persona. Le va a pedir dos cosas:

  1. **El motivo** — falleció, cambió de residencia, ya no convive, u otro.
  2. **La fecha del hecho**, que **no es la de hoy**. Si la señora falleció en
     marzo y usted se está enterando en septiembre, la fecha es la de marzo.
     Pregúntesela a la familia.

> **Retirar no es borrar, y esa diferencia importa.** La persona sigue registrada:
> lo que queda anotado es que desde esa fecha ya no pertenece al hogar. Así la
> caracterización anterior —donde la persona sí estaba— **sigue siendo válida**, y
> la nueva no le pregunta por alguien que ya no está.

> Si se equivoca de fila, **Deshacer retiro** lo devuelve al hogar.

> Al integrante **★ AUTORIZADO** no se le puede retirar: es el titular del hogar.
> Si es él quien dejó de pertenecer, primero hay que cambiar el autorizado.

### Paso 3 — Elegir el instrumento

1. Seleccione el instrumento de caracterización (Territorial, Telefónico,
   Urbano étnico, Rural étnico, etc.). Cada tarjeta muestra versión y número
   de capítulos.
2. Si entró desde un hogar, toque **Iniciar caracterización**. Si no, la app
   le pedirá **seleccionar el hogar** en el paso 2 del asistente.

### Paso 4 — Ubicación de atención

Registre dónde se realiza la entrevista, en cascada:

1. **Dirección Territorial** (si es "No presencial", solo pedirá el punto).
2. **Departamento** y **Municipio** de atención.
3. **Punto de atención**.

Toque **Continuar al formulario**. Si está sin conexión puede tocar
**Omitir por ahora** y completar la ubicación después.

### Paso 5 — Responder los capítulos

La pantalla de capítulos muestra el progreso global y el estado de cada
capítulo (Sin iniciar / Faltan N / Completado). Antes de empezar, elija el
**modo de trabajo**:

- **Manual:** responde cada pregunta directamente.
- **Asistido por IA:** transcribe la entrevista oral y la IA sugiere
  respuestas (ver sección 5).

En modo manual, dentro de un capítulo:

- Las preguntas se responden según su tipo (texto, número, fecha, lista,
  selección múltiple). Algunas preguntas aparecen o se ocultan según
  respuestas anteriores — es el comportamiento esperado del formulario.
- Las preguntas de nivel **persona** se repiten por cada integrante del hogar,
  agrupadas en una sección por integrante dentro del capítulo.
- **Las respuestas se guardan automáticamente** en el teléfono mientras
  escribe. Al salir con **Guardar y volver**, se envían al servidor (o quedan
  en cola si no hay señal).

### Paso 6 — Finalizar la sesión

1. Cuando los capítulos obligatorios estén completos, toque **Finalizar
   caracterización** en la pantalla de capítulos.
2. Agregue observaciones (opcional) y confirme. La sesión queda **COMPLETADA**
   y no podrá modificarse.
3. Si necesita anular una entrevista, use **Anular entrevista** (pide doble
   confirmación y es definitivo).

## 5. Asistente de voz con IA (opcional)

1. En la pantalla de capítulos, toque **Asistido por IA**.
2. La primera vez verá la pantalla de **Consentimiento — Asistente IA**: léala
   y marque la casilla de aceptación; luego toque **Activar asistente de voz**.
   Puntos clave: **nunca se almacena audio**, solo el texto transcrito viaja al
   servidor, la clave de la IA vive en el servidor y la IA solo **sugiere** —
   usted decide.
3. Al abrir un capítulo en este modo verá el área **Transcripción de la
   entrevista**: escriba o pegue allí el texto de la entrevista y toque
   **Procesar con IA**.
4. En la pantalla de **Revisión IA** verá cada sugerencia con su nivel de
   confianza (alta/media/baja) y el razonamiento. Para cada una puede
   **Aceptar**, **Editar** o **Ignorar**.
5. Toque **Confirmar y cerrar** para guardar solo las respuestas aceptadas.

## 6. Hogares

- **Hogares** lista sus unidades familiares con filtros (Todos / Borrador /
  Activo). Toque un hogar para ver su detalle y sus caracterizaciones.
- Los hogares creados sin conexión aparecen con la marca **"Pendiente sync"**
  hasta que se sincronicen.
- El botón **+ Nuevo hogar** permite crear un hogar directamente.

## 7. Encuestas (sesiones)

**Caracterizaciones** lista sus sesiones con estado (Iniciada, En curso,
Completada) y porcentaje de avance. Toque una sesión en curso para continuar
exactamente donde quedó.

## 8. Mis reportes

Muestra su producción por período (semana / mes / todo): sesiones completadas
y en progreso, hogares caracterizados, respuestas registradas, promedio de
avance y desglose por instrumento. Puede **Exportar CSV**.

## 9. Trabajo sin conexión (modo offline)

La app está diseñada para campo con señal intermitente:

- **Qué funciona sin señal:** responder capítulos de una sesión ya iniciada,
  crear hogares (quedan "Pendiente sync") y revisar datos locales.
- **Qué requiere señal:** iniciar sesión, búsqueda RNI, crear la sesión de
  encuesta, reportes y finalizar sesión (se encola si no hay red).
- Todo lo capturado sin señal entra a una **cola de sincronización** que se
  envía automáticamente al recuperar conexión, con reintentos automáticos.
- En **Estado de sincronización** puede ver cada elemento de la cola, forzar
  **Sincronizar**, **Reintentar errores** y **Limpiar enviados**.

> **Recomendación:** antes de salir a campo, inicie sesión y verifique el
> indicador `✓ Al día`. Al volver a zona con señal, abra la app y confirme que
> el indicador regrese a `✓ Al día` (así garantiza que no queda información
> solo en el teléfono).

## 10. Cierre de sesión y seguridad

- Use **Cerrar sesión** al terminar la jornada; esto elimina las credenciales
  del teléfono.
- La sesión expira automáticamente por seguridad; si la app le pide ingresar
  de nuevo, es el comportamiento normal.
- No comparta su usuario: **toda acción queda registrada en auditoría** a su
  nombre.
- Si pierde el teléfono, informe de inmediato al administrador para revocar el
  acceso. Los datos locales no contienen documentos ni nombres de víctimas en
  forma permanente y las credenciales están en el almacén seguro del sistema.

## 11. Solución de problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| "Sin conexión" permanente con señal | El servidor no es alcanzable | Verifique datos móviles/WiFi; reintente desde Estado de sincronización |
| Botón "Consultar RNI" deshabilitado | No ha digitado el número de documento | Escriba el número de documento; el botón se habilita automáticamente |
| Elementos con "error" en la cola | Reintentos agotados | Toque **Reintentar errores**; si persiste, reporte el detalle del error al soporte |
| La app pide ingresar de nuevo | Sesión expirada | Ingrese normalmente; su trabajo local no se pierde |
| No aparece el botón de huella | Biometría no activada, no configurada en el teléfono, o primer ingreso | Configure la huella/rostro en los ajustes del teléfono e ingrese una vez marcando "Activar ingreso con huella o rostro" |
| Un capítulo muestra "Faltan N" tras responder | Preguntas obligatorias por **cada miembro** del hogar | Revise la sección de cada integrante |
| **Falta una pregunta** que usted esperaba ver | Una regla del formulario la oculta porque no aplica según lo ya respondido | Es el comportamiento esperado. Revise las respuestas anteriores del capítulo antes de reportarlo |
| Dice que la persona **ya fue caracterizada** | Se caracterizó hace menos de dos años | No es un error y no la detiene: continúe. Ver «Si la persona ya fue caracterizada» en la sección 4 |
| Sigue apareciendo **"No habilitado — ficha vigente"** | El teléfono tiene información del padrón de días anteriores | **Cierre sesión y vuelva a ingresar con señal.** Ahí se actualiza el padrón que el teléfono usa sin conexión |
| No puedo **quitar** a un integrante ya reportado | Borrarlo cambiaría un dato ya entregado | Use **Retirar del hogar**: registra que la persona ya no pertenece, con el motivo y la fecha, y no altera la caracterización anterior |
| El hogar tiene integrantes que yo no capturé | Es el hogar que la familia ya tenía registrado | Es correcto. **No los capture de nuevo**: si alguno ya no vive ahí, retírelo |

## 12. Cómo reportar un problema

Un reporte sirve si permite reproducir lo que usted vio. Incluya:

1. **La versión de la aplicación** — la lee en la pantalla de ingreso.
2. **En qué pantalla** ocurrió y **qué hizo justo antes**.
3. **Qué esperaba** y **qué pasó**.
4. Si hay mensaje de error, el texto completo.

> **No incluya datos de la persona entrevistada** —documento, nombres, dirección— en el
> reporte. Basta con el código del hogar si lo tiene. La información de las víctimas está
> protegida por la **Ley 1581 de 2012** y no debe salir por canales de soporte.

**Soporte técnico:** `[COMPLETAR — canal de soporte interno UARIV]`

> ⚠️ **Este dato falta y bloquea la publicación del manual.** Debe definirlo la
> Subdirección Red Nacional de Información: a qué correo, teléfono o mesa de servicios
> reporta un encuestador en campo. Sin él, el manual no puede entregarse a los enlaces
> territoriales ni imprimirse la tarjeta de bolsillo.
