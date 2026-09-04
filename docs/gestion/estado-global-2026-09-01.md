# Estado global del proyecto — 1 de septiembre de 2026

> **Para qué sirve este documento.** Es la foto de dónde está cada frente y qué lo
> desbloquea al **1 de septiembre**. Se escribió tras correr la batería completa de pruebas y
> revisar la documentación del repositorio.

> ⚠️ **Foto con fecha: no leer sus plazos como vigentes.** Al 4 de septiembre hay cuatro
> cosas que ya no son como aquí se cuentan:
>
> - **Las fechas de capacitación cambiaron dos veces.** Ya no son el 1, el 3 y el 8: son
>   **jueves 10, martes 15 y viernes 18 de septiembre**, según indicó el ingeniero Alejandro
>   Fernández. La Sesión 1 no se dictó el 1 de septiembre.
> - **El Manual de Uso v1.2 ya está publicado** (numeral 6 de «lo urgente») y con los cuatro
>   hallazgos de prioridad alta atendidos. Se descubrió además que no estaba publicado en
>   ninguna parte, y se corrigió.
> - **La cadena del FTP empeoró.** Aquí se cuentan 16 días; medido el 4 de septiembre son
>   **20 noches consecutivas** sin cargar, con la última carga buena el 14 de agosto.
> - **El pre-test bajó de 15 preguntas a 10** (cinco minutos), a solicitud de la jornada.
>
> El resto —pruebas, pendientes por frente, riesgos— sigue vigente.

---

## 1. Pruebas — ejecutadas hoy

| Componente | Suites | Pruebas | Resultado | Duración |
|---|---:|---:|---|---:|
| **Backend** (Django 5.2) | 60 archivos | **1.037** | ✅ pasan · 2 xfail · 0 fallos | 104 s |
| **App móvil** (Expo/RN) | 12 | **148** | ✅ pasan · 0 fallos | 8 s |
| **Panel web** (React) | 3 archivos | — | ⚠️ no ejecutable en esta máquina | — |
| **Total verificado** | | **1.185** | **0 fallos** | |

El panel web no tiene dependencias instaladas localmente (`node_modules` vacío): sus tres
archivos de prueba no se pudieron correr desde aquí. Es el frente de Brandon y se verifica en
su entorno. **No es un fallo: es una comprobación no realizada**, y así debe reportarse.

---

## 2. Lo urgente — con reloj

| # | Qué | De quién depende | Estado |
|---|---|---|---|
| 1 | **Suspender la eliminación diaria** de archivos del FTP | Operación | 🔴 Cada día que pasa se borra la captura de ese día |
| 2 | **Restablecer `F:\Encuestas`** en el servidor de Modelo | Administrador de ese servidor | 🔴 El proceso lleva 16 días fallando |
| 3 | ~~Correo del tablero GAVE~~ | — | ✅ **Enviado el 1-sep** |
| 4 | ~~Correo de la pregunta campesinado~~ | — | ✅ **Enviado el 1-sep** |
| 5 | ~~Correo gerencial del caso 14512~~ | — | ✅ **Enviado el 1-sep** — quedan a la espera las dos instrucciones que pide |
| 6 | **Manual de Uso v1.2** | Nosotros | 🟠 4 hallazgos de prioridad alta, antes de la Sesión 2 |
| 7 | **Canal de soporte interno** | Subdirección | 🟠 Bloquea el manual *y* la pieza gráfica 7 |
| 8 | **Verificación de dispositivos** de los 30 enlaces | Operación / nosotros | 🟠 72 h antes de cada sesión |

**Los cuatro correos se enviaron el 1 de septiembre** (los tres anteriores más la solicitud a
QA por los seis hallazgos sin descripción). Con eso, lo urgente que queda ya no depende de
redactar nada: depende de que respondan.

**Medido el 1-sep, antes de enviarlos:** el proceso de carga del FTP seguía fallando todas
las noches —incluida la del 31 de agosto— en un segundo, y `DATA_JSON` del 65 llevaba
**catorce días sin recibir un solo archivo**. La cadena acumula **16 días caída**.

---

## 3. Estado por frente

### 3.1 Aplicación móvil — SICAV Móvil

**Donde está.** Versión **1.2.3** desplegada, con la versión visible en la pantalla de
ingreso. 148 pruebas en verde. Los siete hallazgos del informe de calidad APK están cerrados.

| Pendiente | Naturaleza | Prioridad |
|---|---|---|
| **APK-004** — quitar un integrante funciona; **corregirlo no** | Desarrollo | Media |
| **Padrón offline real** — el dispositivo conoce 5.000 personas, no 5,9 M: nunca descarga el archivo completo | Desarrollo · Fase B | **Alta** |
| **Cifrado del padrón local (Fase 1)** — hoy usa un hash no criptográfico y reversible, sin sal | Desarrollo · seguridad | **Alta** |
| Botón de adjuntar soporte de la excepción, aún presente en campo | Desarrollo · build nuevo | Media |

> El punto del padrón offline es el más importante del frente móvil: la operación sin conexión
> es la razón de ser de la aplicación, y hoy opera contra una fracción del padrón.

### 3.2 Panel de Control — web

**Donde está.** Los cinco hallazgos del informe de calidad WEB cerrados (H-010, H-011, H-024,
H-025, H-027). La búsqueda de autorizaciones pasó de 5,8 s a 2 ms. Trabajo de Brandon
integrado. Autorización de excepciones operativa, incluida la de quien está en el RUV y no en
el padrón.

| Pendiente | Naturaleza |
|---|---|
| ~~Matriz de validación de permisos sin diligenciar~~ | ✅ **Resuelto 1-sep** — automatizada: 61 comprobaciones sobre los 5 perfiles reales |
| **Seis hallazgos de QA v1 sin descripción** (H-003, H-005, H-006, H-015, H-016, H-018) | 🟠 Escalado por escrito el 1-sep; si no hay respuesta en una semana se cierran como superados por el v2 |
| Cobertura de pruebas del panel: 3 archivos para 5.921 líneas (el control de acceso ya está cubierto desde el backend) | Desarrollo · Brandon |
| Dependencias no instaladas para correr sus pruebas fuera del entorno de Brandon | Entorno |
| **Cuántas cuentas con permiso de autorizar** — medido: **3 cuentas para 1.157 encuestadores**. Ficha de decisión en `decisiones_negocio_pendientes.md` §6 | **Definición de operación** |
| `H-022` (admin de Django mezcla idiomas) · usuario `QATEST01` sin eliminar · responsive sin revisar | Menores |

> **Verificado el 1-sep:** el «bug conocido» del 403 para el Supervisor **ya no existe**
> —`PuedeConsultarOperacion` da lectura a supervisión y reserva la escritura a campo—, y
> `backfill_porcentaje` resultó ser un **no-op**: producción tiene 4 sesiones y ninguna
> cambiaría. Ambos estaban documentados como pendientes y no lo eran.

> **El dato que enmarca todo el frente web:** producción tiene **7 hogares y 4 sesiones**.
> El panel está construido y es correcto, pero **no se ha ejercitado con datos reales**
> porque ninguna encuestadora ha entrado todavía. El riesgo no es lo que muestra: es que
> nada se ha probado a volumen.

### 3.3 Backend y datos

**Donde está.** 976 pruebas en verde. Padrón real cargado (**5.926.004** personas) y universo
del RUV (**12.009.492**). Ya no opera con datos ficticios. El piloto de escritura hacia Oracle
por los procedures oficiales se verificó en producción el 28 de julio.

| Pendiente | Naturaleza | Prioridad |
|---|---|---|
| **Escritura automática a Oracle: apagada** — encenderla es decisión operativa explícita | Decisión | Media |
| Join roto de caracterización: género, etnia, discapacidad y estado RUV del padrón provienen de otra persona | Dato · **corrección de fondo** | **Alta** |
| Tres tareas programadas, todas apagadas por defecto | Decisión | Baja |

### 3.4 Instrumento de caracterización

**Donde está.** Nueve parametrizaciones vigentes: 106 capítulos, **1.959 preguntas**, 1.043
reglas de flujo y 6.021 opciones. Territorial V8 reconstruido contra el manual y desplegado.

| Pendiente | Naturaleza |
|---|---|
| **Replicar los flujos reconstruidos** de Territorial a Asistencia y a los demás perfiles | Desarrollo |
| Preguntas y sub-campos que el manual declara y el instrumento no tiene (D7, estrato, semanas de embarazo, primas) | Desarrollo |
| Tres preguntas huérfanas en el perfil Telefónico, en producción | Limpieza |
| **646 opciones sin código de correspondencia con VIVANTO** — incluidos los perfiles Rural Étnico y Víctimas en el Exterior al 0 % | **Bloquea la migración de esos perfiles** |
| **Pregunta de autorreconocimiento campesino** | Esperando insumos de la Dirección de Registro |

### 3.5 Cadena legacy y Oracle

**Donde está.** Tres causas raíz identificadas la semana pasada, todas con evidencia
reproducible y documentadas.

| Pendiente | De quién depende |
|---|---|
| **`F:\Encuestas`** en el servidor de Modelo | Administrador de ese servidor |
| **Eliminación diaria de archivos del FTP** | Operación |
| **Reprocesar el respaldo represado** — la ventana se cierra hacia el 12 de octubre | Nosotros, tras lo anterior |
| **Programar `PRC_REP_GAVE`** — el reporte del tablero se reconstruye a mano | Autorización de la Subdirección |
| **Monitoreo con alerta** sobre los procesos de la cadena | Nosotros |
| 912 archivos sin procesar y 2.237 fallidos, sin revisar | Nosotros |
| 12 defectos de la base legacy registrados para después de la migración | Diferido |

### 3.6 Infraestructura

**Donde está.** Servidor `30.0.1.109`, dominio institucional operativo vía WAF. Arquitectura
documentada el 31 de agosto.

| Pendiente | Naturaleza | Prioridad |
|---|---|---|
| **Respaldos sin confirmar** — se solicitaron en junio y no hay constancia de que operen | **Gestión con Infraestructura** | 🔴 **Alta** |
| Servidor compartido, no dedicado: presión de disco y de capacidad | Contexto permanente | Media |
| Revalidar la ficha de arquitectura en vivo | Nosotros, con VPN | Baja |

> **El punto de los respaldos es el riesgo abierto más grande del proyecto.** Hay 5,9 millones
> de personas y 12 millones de registros de universo en una base de la que no consta que se
> respalde. No es un pendiente técnico: es una gestión que lleva abierta desde junio.

### 3.7 Capacitación

**Donde está.** Plan formal y ocho anexos listos y commiteados. Sesión 1 **hoy**.

| Pendiente | Cuándo |
|---|---|
| Manual de Uso v1.2 con los 4 hallazgos de prioridad alta | Antes de la Sesión 2 (jueves 3) |
| Canal de soporte interno definido | Bloquea el manual y la pieza 7 |
| Listado nominal del equipo de la Subdirección | Sesión 1 |
| Verificación de dispositivos y credenciales | 72 h antes de cada sesión |
| Las siete piezas gráficas | Especificadas, en producción |

---

## 4. Lo que propongo hacer primero

1. **Enviar los tres correos hoy.** Dos ya pasaron su plazo. Están escritos; no enviarlos es
   el único costo evitable de toda esta lista.
2. **Escalar los respaldos.** Es el riesgo mayor y el más antiguo. Basta con retomar la
   solicitud de junio y pedir constancia.
3. **Manual v1.2 antes del jueves.** Si la Sesión 2 recibe el manual actual, treinta enlaces
   se llevan un material que no coincide con lo que ven en pantalla.
4. **Padrón offline (Fase B).** Es el pendiente técnico de mayor impacto: la aplicación existe
   para trabajar sin señal y hoy lo hace contra el 0,08 % del padrón.
5. **Join roto de caracterización.** Mientras no se corrija, cuatro atributos del padrón
   describen a otra persona.

---

## 5. Documentación — estado

Actualizada hoy:

- `docs/gestion/implementacion_capacitacion_despliegue.md` — cinco pendientes marcados como
  resueltos: identidad de marca, repositorio de víctimas (ya no es MOCK), plan de capacitación
  formal, calendario y participantes, y publicación TLS con dominio institucional.
- `docs/arquitectura/arquitectura-produccion-2026-08-31.html` — línea base de la arquitectura,
  con la identificación del servidor y el contraste contra la solicitud de junio.
- Este documento.

Sigue vigente y es la referencia técnica del frente Oracle:
`docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md` (su §3 conserva el backlog de decisiones de
negocio de la migración, varias de ellas aún abiertas).

**Entregables de la semana:** `entregables/2026-08-27-caso-14512/`,
`entregables/2026-08-27-capacitacion/`, `entregables/2026-08-28/` (presentación semanal) y
`entregables/2026-08-31-arquitectura/`.
