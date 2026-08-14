# Manual de Uso — SRNI Encuestador (App Móvil)

**Versión:** 1.0
**Fecha:** 2026-06-10
**Dirigido a:** Encuestadores de caracterización UARIV
**Aplicación:** SRNI Encuestador — Android / iOS

---

## 1. Requisitos previos

- Teléfono Android 8+ o iPhone (iOS 15+).
- **Código de usuario y contraseña** asignados por el administrador del SRNI.
  La app no permite auto-registro.
- Conexión a internet para iniciar sesión y sincronizar. **La entrevista puede
  realizarse sin conexión** (ver sección 9).

## 2. Inicio de sesión

1. Abra la app. Verá la pantalla de ingreso con la franja institucional GOV.CO.
2. Digite su **código de usuario** y su **contraseña** (el ícono de ojo
   muestra/oculta la contraseña).
3. Toque **Ingresar**.
4. Si su teléfono tiene huella o reconocimiento facial configurado, en los
   siguientes ingresos aparecerá el botón **Huella digital** para entrar sin
   digitar la contraseña. La biometría se valida solo en su teléfono.

> **¿Olvidó su contraseña?** No existe recuperación desde la app: contacte al
> administrador del sistema. El cambio de contraseña se realiza por el panel
> web del SRNI.

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
     caracterizada; se muestra el motivo. No hay acciones disponibles.
   - **No encontrada (tarjeta gris):** puede registrarla con **Agregar como
     víctima no incluida** — diligencie nombres, apellidos, fecha de
     nacimiento y género, y toque **Agregar víctima**.

> La búsqueda requiere conexión a internet.

### Paso 2 — Conformar el hogar

1. La persona buscada queda registrada automáticamente como **★ AUTORIZADO**
   (primer integrante del hogar).
2. Para cada integrante adicional diligencie: tipo y número de documento,
   nombres y apellidos, fecha de nacimiento, **parentesco** (cónyuge, hijo/a,
   etc.), **género** y **rol** (miembro, tutor o cuidador permanente). Toque
   **Agregar al hogar** y repita.
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
  selección múltiple). Algunas preguntas aparecen u se ocultan según
  respuestas anteriores — es el comportamiento esperado del formulario.
- Las preguntas de nivel **persona** se repiten por cada integrante del hogar;
  use las pestañas de miembros para cambiar de persona.
- **Las respuestas se guardan automáticamente** en el teléfono mientras
  escribe. Al salir con **Guardar capítulo**, se envían al servidor (o quedan
  en cola si no hay señal).

### Paso 6 — Finalizar la sesión

1. Cuando los capítulos obligatorios estén completos, toque **Finalizar
   sesión** en la pantalla de capítulos.
2. Agregue observaciones (opcional) y confirme. La sesión queda **COMPLETADA**
   y no podrá modificarse.
3. Si necesita anular una entrevista, use **Anular entrevista** (pide doble
   confirmación y es definitivo).

## 5. Asistente de voz con IA (opcional)

1. En la pantalla de capítulos, toque **Asistido por IA**.
2. La primera vez verá la pantalla de **Consentimiento**: léala y marque la
   casilla de aceptación. Puntos clave: el audio se transcribe en el teléfono
   y **nunca se guarda ni se envía**; solo el texto va al servidor; la IA solo
   **sugiere** y usted decide.
3. Al abrir un capítulo en este modo, use el botón de **micrófono**: toque
   para grabar la conversación del capítulo y toque de nuevo para detener.
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
| Botón "Consultar RNI" deshabilitado | Sin conexión | La búsqueda RNI requiere internet |
| Elementos con "error" en la cola | Reintentos agotados | Toque **Reintentar errores**; si persiste, reporte el detalle del error al soporte |
| La app pide ingresar de nuevo | Sesión expirada | Ingrese normalmente; su trabajo local no se pierde |
| No aparece el botón de huella | Biometría no configurada en el teléfono o primer ingreso | Ingrese una vez con contraseña; configure huella/Face ID en el sistema |
| Un capítulo muestra "Faltan N" tras responder | Preguntas obligatorias por **cada miembro** del hogar | Revise las pestañas de cada integrante |

**Soporte técnico:** `[COMPLETAR — canal de soporte interno UARIV]`
