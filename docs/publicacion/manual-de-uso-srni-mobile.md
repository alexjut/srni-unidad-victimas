# Manual de Uso — SICAV Móvil (App de caracterización)

**Versión del manual:** 1.2
**Fecha:** 2026-09-01
**Dirigido a:** Encuestadores de caracterización UARIV
**Aplicación:** SICAV Móvil — Android **1.2.3**

> **Qué cambió frente a la versión 1.1.** Se documenta la **regla de vigencia de dos
> años** y la **excepción** que la levanta (secciones 2 y 4), se explica la **lógica de
> saltos** del formulario (sección 4, paso 5) y se indica cómo **confirmar la versión
> instalada**. Si su manual dice 1.1, está desactualizado.

---

## 1. Requisitos previos

- Teléfono Android 8 o superior.
- **Código de usuario y contraseña** asignados por el administrador del SRNI.
  La app no permite auto-registro.
- Conexión a internet para iniciar sesión y sincronizar. **La entrevista puede
  realizarse sin conexión** (ver sección 9).
- La **versión instalada** debe ser la **1.2.3** o superior. Se lee en la propia
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
     caracterizada en este momento; la tarjeta indica el motivo y muestra su
     nombre. El motivo más frecuente es la **ficha vigente** — ver más abajo,
     «La regla de los dos años».
   - **No encontrada (tarjeta gris):** toque **Registrar y caracterizar**.
     Se abre el formulario **Alta manual**: diligencie nombres, apellidos,
     fecha de nacimiento y género, y toque **Agregar víctima**.

> La búsqueda requiere conexión a internet.

#### La regla de los dos años, y cómo se levanta

Una persona **no puede volver a caracterizarse antes de dos años** desde su última
caracterización. Es una regla de la entidad, no una limitación técnica: evita duplicar
el esfuerzo de campo y mantener información redundante.

Cuando la persona tiene una caracterización vigente, la búsqueda la muestra en naranja
como **«No habilitado — ficha vigente»**.

**Qué NO debe hacer el encuestador.** No intente rodear el bloqueo, no use el documento
de otra persona y no use el **Alta manual** para saltarse el
control. La caracterización quedaría duplicada y con datos incorrectos.

**Qué SÍ debe hacer.** Existen casos legítimos en los que corresponde volver a
caracterizar aunque la ficha esté vigente: un fallo judicial, una tutela o un auto que
lo ordene. En esos casos:

1. **Reporte el caso a su coordinación**, indicando el documento de la persona y el
   motivo.
2. **La autorización la otorga coordinación desde el Panel de Control**, con el
   radicado del soporte y el motivo. El documento de respaldo (el fallo, la tutela, el
   auto) **no lo maneja el encuestador**: llega por canal institucional al nivel
   central. Usted no necesita tenerlo ni fotografiarlo.
3. Una vez autorizada, vuelva a buscar a la persona en la aplicación y toque
   **«Ya la autorizaron»**. La caracterización continúa con normalidad.

> **La autorización es de un solo uso** y se consume al finalizar esa encuesta. Si más
> adelante la misma persona requiere otra excepción, hay que solicitarla de nuevo.

> **Funciona sin señal.** Las autorizaciones otorgadas antes de salir viajan al teléfono
> en la precarga de la jornada, así que la excepción se puede usar en campo aunque no
> haya conexión.

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

> Regla del sistema: una persona solo puede ser autorizada de **un** hogar
> activo a la vez. Si intenta crear un segundo hogar para la misma persona, la
> app le mostrará el hogar ya existente.

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
| **"No habilitado — ficha vigente"** | La persona se caracterizó hace menos de dos años | Ver «La regla de los dos años» en la sección 4. Si hay orden judicial, la excepción la autoriza coordinación desde el panel |
| El botón **"Ya la autorizaron"** no aparece | La autorización aún no se ha registrado en el panel, o no bajó al teléfono | Confirme con coordinación que quedó registrada; con señal, vuelva a consultar |

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
