# Manual Funcional — App Móvil de Caracterización (SICAV / SRNI)

**Versión del manual:** 1.0
**Fecha:** 2026-07-03
**Dirigido a:** Equipo funcional / de pruebas de la UARIV
**Aplicación:** SICAV Móvil — Sistema de Caracterización a Víctimas (Android)
**Alcance:** describe, pantalla por pantalla, qué hace la app, qué ve y toca el usuario, qué mensajes muestra, qué es obligatorio y cómo se comporta con y sin conexión. Incluye checklists de prueba, catálogo de mensajes y pendientes conocidos.

> **Cómo usar este manual.** Si es su primera vez, lea las secciones 1–4 (conceptos y arranque). Para probar un flujo puntual, salte a la sección 6 (recorrido pantalla por pantalla) usando el índice. Para ejecutar pruebas formales, use la sección 9 (checklists). Todo lo que va **"entre comillas y en negrita"** es texto literal que verá en la app.

---

## Índice

1. ¿Qué es esta aplicación?
2. Glosario de conceptos clave (léalo primero)
3. Requisitos, credenciales e instalación de la APK de prueba
4. Reglas de negocio que todo probador debe conocer
5. El flujo completo de una caracterización (mapa general)
6. Recorrido pantalla por pantalla (detallado)
7. Comportamiento sin conexión (modo offline) — matriz
8. Catálogo de mensajes y estados
9. Checklists de prueba funcional
10. Pendientes conocidos (NO reportar como bugs nuevos)
11. Solución de problemas
12. Anexo — comportamiento de carga y red (importante para esta versión)

---

## 1. ¿Qué es esta aplicación?

Es la herramienta móvil con la que un **encuestador** de la UARIV **caracteriza** a las víctimas en campo: busca a la persona en el registro nacional, **conforma su hogar** (arma la lista de integrantes) y le aplica uno o varios **instrumentos** de caracterización (encuestas por capítulos). Está diseñada para funcionar **con y sin internet**, porque el trabajo de campo tiene señal intermitente.

Objetivo de la prueba funcional: verificar que cada flujo se comporta como se describe aquí, que los mensajes son claros, que lo capturado sin señal **no se pierde** y que la app nunca deja al encuestador bloqueado.

---

## 2. Glosario de conceptos clave (léalo primero)

Entender estos términos evita confusiones al probar:

| Término | Qué significa en la app |
|---|---|
| **RNI / RUV** | El registro nacional de víctimas contra el que se consulta a la persona. La app dice si está **INCLUIDO**, **NO INCLUIDO**, **EN PROCESO** o **EXCLUIDO**. |
| **Autorizado / Titular** | La víctima **titular** que autoriza y sobre la que gira la entrevista. Es **el primer integrante** del hogar y lleva la estrella **★ AUTORIZADO**. Solo hay uno por hogar. |
| **Hogar** | La unidad familiar que se caracteriza. Se compone del autorizado + los demás integrantes. |
| **Integrante / Miembro** | Cada persona del hogar. Puede tener rol **Miembro**, **Tutor** (de un menor) o **Cuidador permanente** (de un adulto dependiente). |
| **Instrumento / Perfil** | El tipo de encuesta (Territorial, Telefónico, Urbano étnico, Rural étnico, etc.). Cada uno tiene una **versión** y un número de **capítulos**. |
| **Caracterización / Sesión** | Una aplicación concreta de un instrumento a un hogar. Un hogar puede tener **varias** caracterizaciones (una por instrumento). Estados: **INICIADA**, **EN PROGRESO**, **COMPLETADA**, **SUSPENDIDA**. |
| **Capítulo** | Cada bloque de preguntas del instrumento. Puede ser **por hogar** (se responde una vez) o **por persona** (se repite por cada integrante). |
| **Pregunta por persona** | Pregunta que se responde **por cada integrante** del hogar (p. ej. datos básicos). |
| **Skip-logic (lógica de saltos)** | Preguntas que **aparecen, desaparecen o se vuelven obligatorias** según respuestas anteriores. Es comportamiento **esperado**, no un error. |
| **Padrón (precarga)** | La lista de víctimas/jornada que la app **descarga tras el login** para poder **buscar sin internet**. |
| **Cola de sincronización** | La "bandeja de salida": todo lo creado sin señal (víctimas, hogares, integrantes, respuestas) se **encola** y sube solo al recuperar conexión. |
| **En línea / sin conexión** | La app decide **sola** según la señal; el probador no cambia nada manualmente. El estado se refresca ~cada 60 segundos, así que puede haber un pequeño desfase. |

---

## 3. Requisitos, credenciales e instalación de la APK de prueba

- **Dispositivo:** Android 8 o superior. (iOS/iPhone está aplazado en esta fase; probar solo en Android.)
- **Credenciales:** un **código de usuario** y una **contraseña** asignados por el administrador del SRNI. La app **no** permite auto-registro ni recuperación de contraseña desde el móvil (eso se hace por el panel web).
- **Instalación de la APK de prueba:**
  1. Abrir en el celular la página de descarga: **`https://prod-caracterizacion.ngrok.app/descargar/`** (allí hay un **QR** y el enlace directo).
  2. Descargar `app.apk` e instalarla (Android pedirá permitir "instalar apps de orígenes desconocidos"; es normal para una APK de prueba).
  3. Abrir la app "SICAV Móvil".
- **Conexión:** para iniciar sesión y sincronizar se necesita internet. La captura de una entrevista ya iniciada funciona sin señal.

> **Nota de entorno:** en pruebas, la app se conecta al backend a través de un **túnel (ngrok)** que puede estar lento o caerse por momentos. Si nota lentitud, revise la sección 12: la app ya **no** se queda "cargando" para siempre; degrada a error o a modo sin conexión.

---

## 4. Reglas de negocio que todo probador debe conocer

1. **Un autorizado = un hogar activo.** Una misma persona solo puede ser autorizada de **un** hogar no archivado a la vez. Si intenta crear un segundo hogar para la misma persona, la app le **devuelve el hogar ya existente** (no crea duplicado). Si el hogar activo lo creó **otro** encuestador, la app lo bloquea con un mensaje para pedir reasignación al supervisor.
2. **El autorizado se agrega solo.** Al conformar el hogar, la persona buscada queda automáticamente como **★ AUTORIZADO** (primer integrante). No hay que agregarla a mano.
3. **Parentesco y género NO se piden al conformar.** Se capturan **dentro de la entrevista**, en el Capítulo B "Datos básicos". Al agregar un integrante solo se pide documento, nombres, apellidos, fecha de nacimiento y rol.
4. **Tutor/Cuidador exigen constancia.** Si el rol de un integrante es **Tutor** o **Cuidador permanente**, la app exige adjuntar una **constancia** para poder continuar (ver pendiente conocido en la sección 10).
5. **1 hogar → N caracterizaciones.** Para probar varios instrumentos con la misma persona **NO** se crean varios hogares: se crea **un** hogar y se le agregan **varias** caracterizaciones (una por instrumento).
6. **Nada se pierde sin señal.** Todo lo capturado offline se **encola** y sube solo al reconectar. El probador debe verificar siempre que la cola quede en **"Todo al día"**.
7. **Se permite guardar incompleto.** Un capítulo se puede guardar con obligatorias sin responder (la app avisa y deja "Guardar igual"). Esto es intencional.

---

## 5. El flujo completo de una caracterización (mapa general)

```
Login
  → Inicio (dashboard)
    → Búsqueda RNI  (buscar por documento)
      → Conformar hogar  (agregar integrantes)
        → Hub de caracterizaciones del hogar
          → Caracterizar: elegir instrumento  (→ elegir hogar si no venía)
            → Ubicación de atención  (DT / Depto / Municipio / Punto)  [solo online]
              → Lista de capítulos
                → Capturar cada capítulo (manual o asistido por IA)
                  → Finalizar caracterización
```

**Ruta corta alterna:** desde **Inicio → "Crear hogar y entrevista"** se entra directo a la Búsqueda y se recorre todo el flujo.

---

## 6. Recorrido pantalla por pantalla (detallado)

### 6.1 Inicio de sesión

**Propósito:** entrar con las credenciales institucionales.

- Fondo con **fotos de regiones de Colombia** que rotan solas cada ~5 s (Caribe, Andes, Amazonia, Orinoquía, Insular), con etiqueta de región. No se pueden pasar a mano.
- Franja amarilla **"GOV.CO"**, logo Unidad para las Víctimas, y tarjeta **"Bienvenido/a"** / **"Ingresa tus credenciales institucionales"**.
- Campos: **"Código de usuario"** (se escribe en MAYÚSCULAS solo), **"Contraseña"** (con ojito para mostrar/ocultar).
- Casillas: **"Recordar mi código de usuario"** (marcada por defecto; guarda solo el código, nunca la contraseña) y **"Activar ingreso con huella o rostro"** (solo aparece si el celular tiene biometría configurada).
- Botón **"Ingresar"**: **deshabilitado** mientras código o contraseña estén vacíos. Al validar muestra un girador.
- **Huella:** si ya inició sesión antes con biometría activada, aparece el separador **"o ingresa con"** y el botón **"Huella digital"**.
- **Error:** credenciales inválidas o sin conexión → texto **rojo** bajo las casillas (mensaje del servidor). Se limpia al reintentar.
- **Tras entrar:** en segundo plano (sin barra visible) la app **descarga el padrón** para trabajar offline. Si esa descarga falla, el login **no** falla.

**Qué verificar:** botón deshabilitado con campos vacíos; error visible con credenciales malas; que tras entrar se llegue al Inicio.

---

### 6.2 Inicio (Dashboard)

**Propósito:** panel principal, punto de partida.

- Encabezado azul **"Hola, [primer nombre]"** + perfil. A la derecha, **chip de sincronización**: **"Sincronizando…"** / **"N pendiente(s)"** / **"Sin conexión"** / **"N error(es)"** / **"✓ Al día"**. Tocarlo **fuerza una sincronización**.
- **Banner de estado de campo** (clave para offline):
  - Verde **"Conectado"** — "Datos al día · se sincroniza en línea".
  - Naranja **"Sin conexión · listo para campo"** — "N víctimas precargadas · puedes trabajar offline".
  - Rojo **"Sin conexión · sin datos"** — "Conéctate para descargar la jornada antes de salir a campo".
- Tarjeta destacada **"Crear hogar y entrevista"** (solo si el perfil puede caracterizar).
- Sección **"ACCIONES"**: **"Búsqueda RNI"**, **"Hogares"**, **"Caracterizaciones"** (según permisos).
- Sección **"SISTEMA"**: **"Mis reportes"**, **"Estado de sincronización"** (el subtítulo muestra pendientes/errores).
- Al final, botón rojo **"Cerrar sesión"**.

**Qué verificar:** que el chip y el banner reflejen el estado real de red; que "Crear hogar y entrevista" lleve a la Búsqueda.

---

### 6.3 Navegación (barra inferior)

Toda la zona autenticada tiene **4 pestañas fijas abajo**: **"Inicio"**, **"Buscar"**, **"Hogares"**, **"Encuestas"**. La pestaña activa se ve azul. Las demás pantallas (detalle de hogar, caracterizar, formulario, IA, sync, reportes) se abren desde botones dentro del flujo, no desde la barra. Si el usuario deja de ser válido, la app **redirige al login** sola.

---

### 6.4 Búsqueda RNI

**Propósito:** buscar a la persona por documento e iniciar el flujo.

- Encabezado **"ENTREVISTA DE CARACTERIZACIÓN"** / "Conformación del hogar".
- Sin conexión, chip naranja: **"Sin conexión — se buscará en los datos offline y se sincronizará al recuperar señal"**.
- Campos:
  - **"Tipo de documento"** (hoja inferior): **CC**, **TI**, **RC**, **CE**, **PA** (por defecto CC).
  - **"Número de documento"** (solo números, con **X** para borrar).
  - **"Ruta"** (menú): **General** (defecto), **Acc. Constitucionales**, **Mod. Núcleo Familiar**, **Ruta Especial**.
  - Botón **"Consultar RNI"** (deshabilitado si el número está vacío; al consultar dice **"Consultando…"**).
- **Resultados:**
  - **Verde — "Persona habilitada para caracterización":** nombre, chip RUV (**INCLUIDO/NO INCLUIDO/EXCLUIDO/EN PROCESO**), chips de discapacidad/etnia si aplican, municipio, N hechos victimizantes.
    - Si ya tiene hogar activo → botón naranja **"Ver hogar registrado (N caracterización/es)"**.
    - Si no tiene hogar → botón azul **"Conformar hogar"** (dice **"Registrando…"** al procesar).
  - **Naranja — "No habilitado para caracterización":** motivo + estado RUV. Sin acciones.
  - **Gris — "No encontrado en el RUV":** botón **"Agregar como víctima no incluida"** → formulario **"Víctima No Incluida"**: **"Primer nombre *"**, "Segundo nombre", **"Primer apellido *"**, "Segundo apellido", **"Fecha de nacimiento *"** (calendario, sin futuro), **Género** (Masc./Fem./NB/N/D). Botón **"Agregar víctima"** deshabilitado hasta tener nombre, apellido y fecha válida. Tras agregar, la tarjeta pasa a **"Registrada como Víctima No Incluida"** con botón **"Conformar hogar"**.
- **Errores:** **"Sin conexión y la persona no está en los datos offline. Conéctese e intente de nuevo."** / **"Error al consultar el RNI. Verifique la conexión."** / **"No se pudo registrar. Revisa la conexión e intenta de nuevo."**
- **Online/offline:** en línea consulta **al servidor**; si la red se cae en ese momento, **cae al padrón offline** automáticamente. Sin conexión busca directo en el padrón (documento enmascarado, p. ej. **"••••1234"**; puede indicar **"Persona YA CARACTERIZADA (datos offline)"**). Conformar sin señal guarda y encola.

**Qué verificar:** los tres tipos de resultado; el registro de "no incluida"; el fallback a offline al cortar la red durante la consulta.

---

### 6.5 Conformar hogar

**Propósito:** crea el hogar automáticamente y permite agregar integrantes.

- **Al entrar** crea el hogar solo: **"Registrando hogar…"** (online) o **"Guardando hogar offline…"**. Sin autorizado: error **"No hay autorizado seleccionado. Vuelve a buscar la víctima."**
- Encabezado **"Conformar Hogar"** / "N integrante(s)"; miga "Búsqueda › Conformar hogar". Sin señal: chip **"Sin conexión — hogar e integrantes se guardan localmente…"**.
- **"Ruta de entrevista"** (selector).
- **"Integrantes del hogar (N)"**: el autorizado va primero con **"★ AUTORIZADO"**.
- **"Agregar integrante"**: **"Tipo Documento"** + **"Número de Documento"**, **"Primer Nombre *"**, "Segundo Nombre", **"Primer Apellido *"**, "Segundo Apellido", **"Fecha de nacimiento"** (sin futuro).
  - Nota azul: **"El parentesco y el género se registran en el Capítulo B (Datos básicos) durante la entrevista."**
  - **"Rol en el hogar"**: **"Miembro del hogar"** (defecto), **"Tutor — responsable legal de menor"**, **"Cuidador permanente — adulto dependiente"**.
  - **Constancia obligatoria** (Tutor/Cuidador): recuadro verde **"Constancia obligatoria"** + botón **"Adjuntar constancia"**. (Ver pendiente en sección 10: hoy registra un marcador, no adjunta archivo real.)
  - Botón **"Agregar al hogar"** (dice **"Agregando…"**).
- **Validaciones:** **"Requerido"** en nombre/apellido faltantes; **"Adjunte la constancia del rol seleccionado"**; **"Formato: AAAA-MM-DD"**; alerta **"Error al agregar…"** si falla.
- **"Continuar a caracterizaciones (N integrante/s)"**: deshabilitado si hay Tutor/Cuidador a medio capturar sin constancia (texto rojo **"Adjunte la constancia del Tutor/Cuidador o cambie su rol antes de continuar."**). Enlace **"Cancelar y volver"**.
- **Destino:** online → hub de caracterizaciones; offline → flujo caracterizar directo (salta el hub).

**Qué verificar:** que el autorizado aparezca solo; agregar un integrante; la exigencia de constancia bloqueando "Continuar".

---

### 6.6 Detalle del hogar

**Propósito:** ver toda la información del hogar.

- Errores con botón **"Ir a la lista de hogares"**: 404 **"Este hogar ya no existe en el servidor…"**, 403 **"No tienes permisos…"**, 401 **"Tu sesión expiró…"**, sin red **"Sin conexión con el servidor. Verifica tu red."**
- **"Datos de vivienda"**: Tipo, Ocupación, Estrato, Cuartos, Personas, Observaciones ("—" si vacío).
- **"Integrantes del hogar (N)"**: nombre (o **"Sin nombre registrado"**), badge **"AUTORIZADO"** si aplica, rol, chip **"Incluido"**/**"No incluido"**, fecha de nacimiento.
- **"Agregar del grupo familiar RUV"** (solo si es el hogar del flujo activo y hay parientes): botón **"Agregar"** por persona → alerta **"Rol en el hogar — ¿Cuál es el rol de [nombre]…"** (Miembro / Tutor / Cuidador / Cancelar). Luego el botón queda **"Agregado"**.
- **"Caracterizaciones del hogar"**: botón **"Ver caracterizaciones (N)"** (deshabilitado si el hogar no tiene autorizado).
- **Online/offline:** esta pantalla **requiere servidor**; sin señal muestra error de red.

---

### 6.7 Hub de caracterizaciones del hogar

**Propósito:** ver las caracterizaciones del hogar y crear nuevas.

- **Sin conexión:** wifi tachado + "Sin conexión con el servidor. Puedes continuar la caracterización sin conexión…" con botones **"Continuar sin conexión"** y **"Reintentar"**.
- Tarjeta resumen: código, municipio, "N integrante(s)", **"Autorizado:"**.
- **"Caracterizaciones del hogar (N)"**: una tarjeta por sesión con nombre del instrumento, chip de estado (**INICIADA** naranja / **EN PROGRESO** azul / **COMPLETADA** verde / **SUSPENDIDA** rojo), barra de progreso y encuestador. Se toca para abrir el detalle de la sesión.
- **Vacío:** **"Sin caracterizaciones todavía"**.
- Botón fijo abajo **"+ Nueva caracterización"** (deshabilitado si el hogar no tiene autorizado).

---

### 6.8 Caracterizar — elegir instrumento y hogar

**Propósito:** iniciar una nueva caracterización (paso 1 instrumento, paso 2 hogar).

- Indicador de pasos **`1 → 2`** con etiqueta **"Instrumento → Hogar"**.
- **Paso 1 — "¿Qué tipo de caracterización vas a realizar?"**: tarjetas por instrumento (nombre + **"versión · N capítulos"**). Selección única. Botón final **"Seleccionar hogar"** (o **"Iniciar caracterización"** si ya venía con hogar).
  - La lista **funciona sin internet** (viene en el bundle). Vacío: **"Sin instrumentos"** / "No hay instrumentos vigentes disponibles…".
- **Paso 2 — "¿A qué hogar vas a caracterizar?"**: tarjetas de hogar (**"Municipio · N miembro(s)"**). Al tocar uno se inicia la sesión con overlay **"Iniciando sesión…"**. Vacío: **"Sin hogares registrados"** + botón **"Ir a Hogares"**.
- **Online:** crea la sesión y va a **Ubicación de atención**. **Offline:** salta a la lista de capítulos (la sesión se crea al reconectar). Si el instrumento no está en el bundle: alerta **"El perfil {CÓDIGO} no está disponible en el bundle local. Reinstala la app."**

---

### 6.9 Ubicación de atención (solo online)

**Propósito:** registrar DT / Departamento / Municipio / Punto antes del formulario.

- Cuatro selectores en **cascada**: **"1. Dirección Territorial"**, **"2. Departamento de atención"** (se habilita tras elegir DT), **"3. Municipio de atención"** (tras el departamento), **"4. Punto de atención"**.
- Cambiar la DT **borra** departamento/municipio/punto. **Caso no presencial:** desaparecen Departamento y Municipio; solo se exigen DT + Punto.
- Botón **"Continuar al formulario"** (deshabilitado hasta completar la cascada). Botón **"Omitir por ahora"** → confirmación **"Omitir ubicación"** (**"Cancelar"** / **"Omitir"**).
- **Requiere conexión** para cargar las listas. Sin red: banner rojo **"No se pudieron cargar las Direcciones Territoriales…"** → recomendación: **"Omitir por ahora"** y completar luego.

---

### 6.10 Lista de capítulos (Formulario)

**Propósito:** hub de la caracterización — progreso por capítulo y global; finalizar/anular.

- Encabezado **"CÓDIGO versión"** (ej. **"TERRITORIAL v3"**) / "Hogar … · N capítulos". Carga: **"Cargando instrumento…"**. Error: **"Sin instrumento"** + botón **"Reintentar descarga"**.
- **Selector de modo** (solo online): **"Manual"** vs **"Asistido por IA"** (esta última atenuada si falta el consentimiento). Luego banner **"Modo … activo"** con enlace **"Cambiar"**.
- **Progreso global:** **"X de N capítulos completados"** + barra + porcentaje (verde al 100%).
- **Tarjetas de capítulo:** número/reloj/check, nombre, chip **"Sin iniciar"** / **"Faltan N"** / **"Completo"**, **"[CÓDIGO] · Por persona"** o **"· Por hogar"**, barra + **"respondidas/obligatorias · %"**.
  - **Importante:** el progreso se recalcula al volver; el denominador son las **obligatorias visibles** (según skip-logic), así que el total puede cambiar.
- **"Finalizar caracterización"** (online y offline). Solo online: **"Anular entrevista"**.
- **Modal "Finalizar sesión":** progreso actual + **"Observaciones (opcional)"**. Online → **"Sesión finalizada"**; offline → **"Caracterización finalizada (offline)"** ("…se enviará al servidor automáticamente cuando recuperes conexión.").
- **Anular** (solo online, doble confirmación): **"¿Cerrar con anulación?"** → **"Última confirmación"** → **"Sesión anulada"**. (No hay estado "ANULADA" separado; queda COMPLETADA con la observación `[ANULADA POR ENCUESTADOR]`.)

---

### 6.11 Captura de un capítulo (el corazón — funciona offline)

**Propósito:** responder las preguntas visibles del capítulo.

- Encabezado con nombre del capítulo / "N pregunta(s)". Chips: **"Offline"** (wifi tachado) sin señal, **"IA"** si el asistente está activo. Carga: **"Cargando…"**.
- **Bloqueo por borrador:** si no se pudo preparar el borrador local, no deja capturar: **"No se pudo preparar el borrador de esta caracterización…"** + **"Volver a capítulos"**. (Este bloqueo es una protección: evita perder respuestas en silencio.)
- **Barra de progreso** del capítulo: **"X / Y obligatoria(s) respondida(s)"** (verde al 100%).
- **Preguntas por hogar** (un control) y **por persona** (**"Datos por persona (N miembros)"**, una fila por integrante; check verde al responder; **"No aplica · motivo"** si la skip-logic la excluye para ese integrante).
- **Tipos de pregunta:** Texto / Texto largo (**"Escribe la respuesta"**), Número (**"Escribe el número"**, filtra no-numéricos), Fecha (sin futuro), Opción única (radio), Sí/No, Opción múltiple (**"Selecciona todas las que apliquen (N seleccionadas)"**), Municipio (selector dinámico).
- **Automáticas / solo lectura:** edad (**B9**) y grupo etario (**B10**) se calculan de la fecha (**A6**); datos del RUV (hecho victimizante **H_V**, fecha **Ocur_HV**) salen como **"Dato del RUV"** con candado (o **"Sin dato registrado en el RUV"**).
- **Prellenado:** la app rellena sola lo ya conocido de cada integrante en celdas vacías, sin pisar lo capturado.
- **Skip-logic:** preguntas que aparecen/desaparecen/se vuelven obligatorias; se evalúa por integrante y entre capítulos.
- **Guardado:** **autoguardado** local (~½ s tras dejar de escribir). Botón **"Guardar y volver"** (**"Sincronizando…"** al enviar). Si faltan obligatorias: alerta **"Preguntas requeridas"** (**"Revisar"** / **"Guardar igual"**) — **se permite guardar incompleto**. Online envía en bloque; offline encola.
- **Voz inline** (IA activa, modo manual, preguntas por hogar): botón **"Dictar respuesta"** → **"Grabando… toca para detener"** → **"Enviando al asistente…"** → tarjeta **"Sugerencia del asistente IA"** con **"N% confianza"** y **"Aceptar"** / **"Rechazar"**. (En esta versión la transcripción de audio es un placeholder — ver sección 10.)

---

### 6.12 Modo IA — Consentimiento, Grabación, Revisión

**6.12.a Consentimiento IA** (`consentimiento-ia`): **"Aviso de uso del asistente de voz"** — el audio se transcribe en el dispositivo y **solo se envía el texto**; el audio **nunca se almacena**; la IA **solo sugiere**. Casilla obligatoria de aceptación; botón **"Activar asistente de voz"** (deshabilitado hasta marcarla). Error: **"No se pudo registrar el consentimiento. Intenta de nuevo."**

**6.12.b Grabación / transcripción** (`grabacion-entrevista`): campo **"Transcripción de la entrevista"** (**"…pegue aquí la transcripción completa…"**, contador **"N / 50 000 caracteres"**). Botones **"Modo manual"** y **"Procesar con IA"** → **"Analizando entrevista con IA…"**. **Requiere conexión.** (MVP: el encuestador **escribe/pega** la transcripción; no hay grabación de audio real aquí — ver sección 10.)

**6.12.c Revisión IA** (`revision-ia`): una tarjeta por pregunta con nivel de confianza **"Alta confianza"** (verde ≥80%), **"Confianza media"** (naranja 50–79%), **"Baja confianza"** (rojo <50%), el valor sugerido (editable con lápiz), el razonamiento (**"IA: …"**) y **"Aceptar"** / **"Ignorar"**. Botón **"Confirmar N y cerrar"** → **"Respuestas guardadas"**. Sin aceptar ninguna: alerta **"Sin respuestas"**.

---

### 6.13 Encuestas (sesiones)

**6.13.a Listado** (`encuestas/index`): filtro **"Todas" / "Iniciadas" / "En curso" / "Completadas"**. Tarjetas con instrumento, chip de estado, **"Hogar: …"**, barra + %, fechas. Deslizar para refrescar. Vacío: **"Sin sesiones"**. Error: **"No se pudo cargar las sesiones."** **Requiere servidor.**

**6.13.b Detalle** (`encuestas/[sesionId]`): chip de estado + fechas, **"Hogar"**, **"Instrumento"**, barra + %, **"N respuesta(s) guardada(s)"**. Si está activa: **"Continuar formulario…"** y **"Finalizar sesión"** (confirma progreso). Lista **"Respuestas guardadas (N)"** (`[código] pregunta → valor`). **Requiere conexión.**

---

### 6.14 Estado de sincronización

**Propósito:** ver la cola y forzar el envío.

- Tarjeta global: **"Sincronizando…"** / **"Hay elementos pendientes"** / **"Sin conexión a internet"** / **"Hay errores que requieren atención"** / **"Todo sincronizado"**, con **"N pendiente(s) · M error(es)"**.
- Botones: **"Sincronizar"** (deshabilitado si ya sincroniza o sin conexión), **"Reintentar errores"** (solo si hay errores), y **"Limpiar enviados"**.
- **"En cola (N)"**: cada ítem con tipo (**"Crear hogar"**, **"Crear sesión"**, **"Respuestas"**, **"Respuesta"**, **"Finalizar sesión"**), estado (**pendiente/enviando/enviado/error**), intentos, y en errores el último mensaje. Vacío: **"Cola vacía — todo al día"**.

**Qué verificar (prueba clave de offline):** crear cosas sin señal → ver que aparezcan en la cola → reconectar → ver que pasen a **enviado** y la cola quede vacía.

---

### 6.15 Mis reportes

**Propósito:** producción del encuestador. Período **"Esta semana" / "Este mes" / "Todo"**. Métricas **"Completadas"**, **"En progreso"**, **"Hogares"**, **"Respuestas"**; **"Promedio completado"**; **"Por instrumento"**; **"Sesiones recientes"** (chip **"Ver todas"**). Botón **"Exportar CSV"** (abre el navegador). **Requiere conexión.** Sin red: **"No se pudo cargar el reporte. Verifica tu conexión."** + **"Reintentar"**.

---

## 7. Comportamiento sin conexión (modo offline) — matriz

| Acción | ¿Funciona sin señal? | Cómo se comporta |
|---|---|---|
| Iniciar sesión (primera vez) | ❌ No | Requiere internet para validar. |
| Ingreso con huella | ⚠️ Depende | Re-autentica con el token guardado; puede requerir red. |
| Búsqueda de víctima | ✅ Sí (si hay padrón) | Busca en el **padrón precargado**; documento enmascarado. |
| Conformar hogar / agregar integrantes | ✅ Sí | Se guarda local y se **encola**. |
| Crear nuevo hogar (manual) | ✅ Sí | Se guarda local ("Pendiente sync"). |
| Elegir instrumento | ✅ Sí | La lista viene en el **bundle**. |
| Ubicación de atención | ❌ No | Necesita listas del servidor → usar **"Omitir por ahora"**. |
| Capturar capítulos | ✅ Sí | Autoguardado local + cola. **Es lo más importante que funcione offline.** |
| Finalizar caracterización | ✅ Sí | Se **encola** ("finalizada offline"). |
| Detalle de hogar / hub / detalle de sesión | ❌ No | Requieren servidor; muestran error de red (con opción de continuar offline en el hub). |
| Reportes | ❌ No | Requieren servidor. |
| Sincronizar la cola | ❌ No | El botón se deshabilita sin conexión. |

> **Regla de oro para el probador:** después de cualquier prueba offline, **reconecte** y confirme que la cola llega a **"Todo al día"**. Así se garantiza que nada quedó solo en el teléfono.

---

## 8. Catálogo de mensajes y estados

**Chip de sincronización (Inicio):** "Sincronizando…" · "N pendiente(s)" · "Sin conexión" · "N error(es)" · "✓ Al día".

**Banner de campo (Inicio):** "Conectado" (verde) · "Sin conexión · listo para campo" (naranja) · "Sin conexión · sin datos" (rojo).

**Estados de una caracterización/sesión:** INICIADA (naranja/azul) · EN PROGRESO (azul) · COMPLETADA (verde) · SUSPENDIDA (rojo/gris).

**Estados de un capítulo:** "Sin iniciar" · "Faltan N" · "Completo".

**Estados de un ítem en la cola:** pendiente · enviando · enviado · error.

**Estado RUV de una persona:** INCLUIDO · NO INCLUIDO · EN PROCESO · EXCLUIDO.

**Errores frecuentes (texto literal):**
- "Sin conexión y la persona no está en los datos offline. Conéctese e intente de nuevo."
- "Error al consultar el RNI. Verifique la conexión."
- "Este hogar ya no existe en el servidor. Vuelve a la lista de hogares." (404)
- "Tu sesión expiró. Vuelve a iniciar sesión." (401)
- "No se pudieron cargar las Direcciones Territoriales. Verifica tu conexión…"
- "No se pudo determinar el instrumento de esta sesión. Conéctate a internet…"
- "El perfil {CÓDIGO} no está disponible en el bundle local. Reinstala la app."

---

## 9. Checklists de prueba funcional

### 9.1 Flujo feliz (end-to-end, con conexión)
- [ ] Login con credenciales válidas → llega al Inicio.
- [ ] Banner de campo en verde "Conectado" (tras precarga).
- [ ] Búsqueda de una persona **habilitada** → tarjeta verde → "Conformar hogar".
- [ ] El autorizado aparece solo con **★ AUTORIZADO**.
- [ ] Agregar 1 integrante "Miembro" → aparece en la lista.
- [ ] "Continuar a caracterizaciones" → hub.
- [ ] "+ Nueva caracterización" → elegir instrumento → (elegir hogar) → Ubicación → "Continuar al formulario".
- [ ] Responder un capítulo por hogar y uno por persona → progreso sube.
- [ ] "Finalizar caracterización" → "Sesión finalizada".
- [ ] Chip de sincronización queda en "✓ Al día".

### 9.2 Registro de "no incluida"
- [ ] Buscar un documento inexistente → tarjeta gris → "Agregar como víctima no incluida".
- [ ] "Agregar víctima" deshabilitado sin nombre/apellido/fecha; se habilita al completarlos.
- [ ] Tras agregar → "Conformar hogar" disponible.

### 9.3 Reglas de negocio
- [ ] Intentar crear un 2.º hogar para la misma persona → la app devuelve el existente (no duplica).
- [ ] Rol "Tutor"/"Cuidador" → exige constancia; "Continuar" bloqueado hasta adjuntarla (marcador).
- [ ] Un mismo hogar con 2 caracterizaciones (2 instrumentos).

### 9.4 Offline (crítico)
- [ ] Con la app abierta, activar modo avión.
- [ ] Buscar una persona del padrón → aparece (documento enmascarado).
- [ ] Conformar hogar + agregar integrante offline.
- [ ] Capturar un capítulo completo offline (autoguardado).
- [ ] Ver en "Estado de sincronización" los ítems en cola.
- [ ] Reconectar → la cola pasa a "enviado" → "Todo al día".
- [ ] Verificar en web/servidor que el hogar, integrantes y respuestas llegaron.

### 9.5 Robustez de carga/red (ver sección 12)
- [ ] Con red lenta/inestable (ngrok), abrir un hogar: la pantalla **no** se queda "Cargando…" para siempre; a los ~15 s muestra error o funciona offline.
- [ ] Al expirar la sesión, la app pide login sin colgarse.

---

## 10. Pendientes conocidos (NO reportar como bugs nuevos)

Estos comportamientos **son esperados en esta versión** — no son defectos nuevos:

1. **Constancia sin adjunto real:** al elegir Tutor/Cuidador y tocar "Adjuntar constancia", la app muestra **"Constancia registrada (pendiente de archivo)"** y registra un **marcador** para no bloquear la entrevista. El selector de archivos real aún no está instalado.
2. **Transcripción IA manual:** en la pantalla de grabación, el encuestador **escribe o pega** la transcripción; aún no hay grabación de audio real por capítulo (MVP).
3. **Voz inline "Dictar respuesta":** la transcripción de ese botón es un placeholder en esta versión.
4. **"Anular" no crea estado separado:** la sesión anulada queda **COMPLETADA** con la observación `[ANULADA POR ENCUESTADOR]` (por auditoría), no en un estado "ANULADA".
5. **Desfase del indicador offline:** el estado de conexión se refresca ~cada 60 s; puede tardar un momento en reflejar que se perdió/recuperó la señal.

---

## 11. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| "Sin conexión" con señal aparente | El servidor/túnel no responde | Reintentar desde "Estado de sincronización"; probar datos/WiFi. |
| "Consultar RNI" no responde o tarda | Túnel ngrok lento | Esperar; si falla, la app cae a offline o muestra error (no se cuelga). |
| Ítems en "error" en la cola | Reintentos agotados | Tocar **"Reintentar errores"**; si persiste, reportar el mensaje de error. |
| La app pide login otra vez | Sesión expirada | Ingresar normal; el trabajo local no se pierde. |
| Un capítulo dice "Faltan N" tras responder | Obligatorias **por cada integrante** | Revisar la fila de cada persona en las preguntas por persona. |
| No aparece el botón de huella | Biometría no configurada o primer ingreso | Ingresar una vez con contraseña; configurar huella en el sistema. |
| Integrante sin nombre en el detalle | Nombre no capturado | Aparece "Sin nombre registrado"; capturar el nombre. |

**Soporte técnico:** `[COMPLETAR — canal de soporte interno UARIV]`

---

## 12. Anexo — comportamiento de carga y red (importante para esta versión)

En pruebas, el backend va por un **túnel (ngrok)** que puede estar lento o caerse. Antes, cuando una petición se colgaba por red parcial, algunas pantallas se quedaban en **"Cargando…"** de forma indefinida. **Eso ya se corrigió:**

- Toda petición tiene un límite de espera de ~**15 segundos**. Si la red falla, la pantalla **muestra un error** o **cae a modo sin conexión** — **no** se queda cargando para siempre.
- Al abrir un hogar/caracterización, si el "Cargando…" supera claramente los ~15 s sin resolver, es un caso a **reportar** (con hora, pantalla y estado del túnel), porque no debería ocurrir.
- La lentitud puntual **sí** puede pasar mientras el entorno de pruebas siga en ngrok; la estabilización definitiva depende de mover el backend al dominio institucional. Repórtela como **lentitud de entorno**, no como cuelgue de la app.

---

*Fin del manual. Para dudas sobre un comportamiento no descrito aquí, repórtelo con: pantalla, pasos exactos, qué esperaba, qué pasó, si había conexión y (si es posible) captura de pantalla.*
