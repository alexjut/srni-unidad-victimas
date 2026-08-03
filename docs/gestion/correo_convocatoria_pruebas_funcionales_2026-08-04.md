# Correo — estado de SICAV y convocatoria a sesión de pruebas funcionales (martes 4-ago)

> **Borrador para revisión de Javier. No enviado.**
> Dos objetivos en un solo correo: dejar por escrito **qué está operativo hoy** y
> **convocar la sesión de pruebas** de mañana martes, con funcionales y técnica en
> la misma sala.
>
> Criterio de redacción: no se listan números de documento en el cuerpo. El padrón
> son **5,9 M de víctimas reales, no datos de prueba**; los documentos de cada caso
> se sacan de la base en el momento, como indica el guion adjunto.

---

**Para:** Oscar [supervisión funcional UARIV] · **Edwin Ruiz** [PMO] · [equipo funcional — caracterización]
**CC:** [OTI — responsable técnico] · Brando [frontend web]
**Asunto:** SICAV — estado a la fecha, convocatoria a pruebas funcionales (martes 4 de agosto) y una consulta sobre hechos victimizantes (PRY-0662064)

---

Estimados,

En el marco del **PRY-0662064** les comparto el estado de **SICAV** —el reemplazo de
la aplicación de caracterización— y les propongo una **sesión de pruebas funcionales
para mañana martes 4 de agosto**, con el equipo funcional y el equipo técnico en la
misma sesión.

## 1. Qué está operativo hoy

Todo lo siguiente está **desplegado y verificado en producción**:

| | |
|---|---|
| **Aplicación web** | `https://caracterizacion.unidadvictimas.gov.co` |
| **Aplicación móvil (Android)** | descargable desde `/descargar/` del mismo dominio |
| **Padrón de víctimas** | **5.926.004** víctimas incluidas, cargadas desde el RUV |
| **Padrón fuera de línea** | **5.001.402** registros en el dispositivo, para operar sin señal |
| **Instrumentos de captura** | los 8 perfiles cargados y sincronizados entre servidor y móvil |
| **Pruebas automatizadas** | 683 en el servidor · 88 en el móvil |

En concreto, hoy la aplicación permite: **buscar a la víctima por documento** (con o
sin señal), **conformar el hogar** con sus integrantes, **aplicar el instrumento
completo** con sus saltos y validaciones, y **dar de alta manualmente** a quien no
aparezca en el padrón.

Ese último punto no es un caso raro y conviene tenerlo presente: **1.884.872 víctimas
incluidas (24 %)** no pudieron incorporarse al padrón porque su identidad no está
resuelta en la fuente. Es una de cada cuatro, y por eso el alta manual en campo es
parte del flujo normal, no una excepción.

## 2. Lo que se resolvió recientemente y conviene que vean funcionando

**Documentos compartidos por más de una persona.** En el padrón hay **768.096**
documentos que aparecen en más de un registro. Al analizarlos encontramos que el
**92 % es la misma persona duplicada en el sistema de origen**, y solo un **6,8 %**
son personas realmente distintas que comparten el número. También hay valores de
relleno —un mismo "documento" con miles de nombres detrás—, que no identifican a
nadie.

El sistema ahora **distingue los tres casos**: cuando es una sola persona la muestra
sin molestar al encuestador; cuando son personas distintas **le pide confirmar cuál
es**, mostrándole los candidatos; y cuando el documento es de relleno **no muestra a
nadie** y obliga al alta manual. Es lo que hace que el aviso, cuando aparece, se lea
en vez de ignorarse.

**Es justamente lo que queremos que validen ustedes**, porque la decisión de fondo
—cuándo interrumpir al encuestador y cuándo no— es funcional, no técnica.

## 3. Lo que está construido pero **apagado a propósito**

La ruta que registra las caracterizaciones de SICAV **en la base actual
(RNIENTREVISTA)** está terminada: los diez pasos que exige el sistema, incluidos los
que llenan el estado en el RUV y los hechos victimizantes en los reportes.

**No está activa.** Opera en modo simulación, con cuatro interruptores en apagado, y
a la fecha lleva **cero escrituras en producción**. Se encenderá cuando esté
respaldada la reversión y ustedes den el visto bueno, no antes. Lo menciono para que
conste que la sesión de mañana **no toca la base actual**.

## 4. Una consulta puntual — Edwin, esta es para ti

**¿De dónde deben salir los hechos victimizantes de cada persona?**

Es lo único que hoy impide que los reportes salgan completos, y no lo podemos
resolver por nuestra cuenta.

El detalle: los reportes de caracterización traen catorce columnas de hechos
victimizantes por persona (desplazamiento forzado, amenaza, homicidio, etc.). La
parte que nos toca ya está construida y probada: sabemos escribirlos y el sistema
los registra correctamente. **Lo que no tenemos es el dato de entrada.**

Cuando cargamos el padrón trajimos, por cada víctima, su identidad, pertenencia
étnica, sexo, discapacidad y estado en el RUV. **Los hechos victimizantes no venían
en esa información**, y no encontramos por dónde pedirlos.

Las tres salidas posibles, como las vemos:

1. **Traerlos de la misma fuente que el padrón.** Es el camino que recomendamos: ya
   funcionó para 5,9 millones de personas y el cruce está probado. Solo nos falta
   saber **qué tabla o servicio los tiene** y que nos den una muestra para verificar
   que corresponden a la persona correcta.
2. **Preguntarlos en campo.** No sirve como equivalente: el instrumento pregunta por
   hechos *declarados en los últimos seis meses*, que no es lo mismo que los hechos
   por los cuales la persona está incluida en el RUV. Registrar uno como si fuera el
   otro sería un dato falso.
3. **Dejar esas columnas vacías** y decirlo por escrito, para que nadie las lea como
   "esta persona no sufrió ningún hecho".

**Lo que te pediría concretamente:** que nos indiques a quién preguntarle o qué
fuente consultar. Con eso lo resolvemos nosotros; no necesitamos accesos nuevos. Si
te sirve, lo conversamos en la misma sesión de mañana.

## 5. Propuesta de sesión — martes 4 de agosto

Necesitamos a **las dos partes juntas**: lo funcional para decidir si el
comportamiento es el correcto, y lo técnico para resolver en el momento lo que
aparezca, sin una segunda vuelta.

**Horario propuesto:** 9:00 a 11:00 a. m.
**Alternativa:** 2:00 a 4:00 p. m. — me acomodo a la que les sirva.
**Modalidad:** presencial o virtual, como prefieran.

**Agenda (2 horas):**

| | |
|---|---|
| 15 min | Demostración del flujo completo: ingreso, búsqueda, hogar, instrumento, envío |
| 45 min | **Pruebas guiadas** sobre los cuatro caminos de identidad, con guion por escrito |
| 30 min | Captura de un hogar completo de principio a fin, en dispositivo |
| 20 min | **Hechos victimizantes** (punto 4) y qué se espera ver en los reportes |
| 10 min | Compromisos y fechas |

**Para aprovechar la sesión les pediría:**

- **Funcionales:** vengan con los casos que en la operación real dan problema. Lo que
  necesitamos validar no es que la aplicación no se caiga, sino que **decida como
  ustedes decidirían en campo**.
- **Técnica:** un momento para revisar juntos el registro en RNIENTREVISTA y confirmar
  que la forma del dato es la que esperan sus reportes.
- **Dispositivos:** Android, con la aplicación **descargada del dominio el mismo día**.
  Una versión anterior no sirve para estas pruebas: el almacenamiento local cambió y
  se comportaría como antes, dando por buenas cosas que ya no lo son.

Adjunto el **guion de pruebas**, que para cada caso dice qué se hace, qué debe pasar
y **qué sería un fallo**. Esa última columna es la que importa: varios de estos
comportamientos son creíbles cuando están mal, y por eso hay que mirar el dato
concreto.

⚠️ Una advertencia de manejo: las pruebas se hacen sobre el **padrón real**, con datos
personales de víctimas. No son datos de prueba. Los documentos de cada caso se
obtienen en el momento y **no circulan por correo**.

Quedo atento a la confirmación de horario.

Cordialmente,

**Javier Aguilar** — Desarrollo y arquitectura, SICAV / SRNI (PRY-0662064)

---

### Notas para Javier (no enviar)

**Antes de mandarlo, completar:**
- Los destinatarios reales (funcionales de caracterización, contacto de OTI).
- **Edwin va en "Para", no en copia**, porque el punto 4 es una pregunta dirigida a
  él y en copia se lee como información. Si preferís no mezclar la convocatoria con
  la consulta, el punto 4 sale limpio como correo aparte: está escrito para poder
  cortarse entero sin tocar el resto.
- Confirmar si Brando entra a la sesión o solo va en copia — el panel web tiene dos
  pendientes suyos (manejar el `409` de documento ambiguo y el badge `NO_VERIFICADO`),
  y si en la sesión se prueba el camino web, esos dos se van a ver.
- El adjunto: `docs/pruebas/guion_pruebas_funcionales_identidad.md`. Está fechado
  "para la sesión del 3-ago" — cambiarle la fecha al 4 antes de enviarlo.

**Cifras usadas, por si preguntan (todas verificadas):**
- 5.926.004 víctimas incluidas cargadas · padrón fuera de línea 5.001.402 filas.
- 768.096 documentos repetidos: 92,0 % misma persona · 6,8 % personas distintas ·
  1,3 % variante de nombre · 89 documentos de relleno.
- 1.884.872 incluidas (24 %) sin identidad resoluble → alta manual.
- 683 tests backend (1 xfail conocido) · 88 APK.
- **Instrumentos: cuidado con el matiz.** Los 8 están cargados y sincronizados, pero
  Telefónico arrastra 3 preguntas huérfanas (7/8 al 100 %). Por eso el correo dice
  "cargados y sincronizados" y no "al 100 %". Si en la sesión se prueba Telefónico,
  mejor decirlo antes que lo encuentren ellos.
- Escrituras en RNIENTREVISTA a la fecha: **0**. Los cuatro interruptores en `False`,
  comprobado en el despliegue de hoy.

**Lo que deliberadamente NO se dice en el correo:**
- Los defectos internos encontrados y corregidos. No aportan a la convocatoria y
  ocupan el lugar de lo que sí hay que decidir. Si preguntan, están documentados.
- Los cuatro objetos INVALID de la cadena de reportes del legacy —vienen rotos desde
  2025, son anteriores a nosotros—. Conviene mencionarlo **de viva voz** en la sesión
  con la parte técnica, para que no se lea como daño nuestro cuando se enciendan los
  reportes, pero por escrito en una convocatoria suena a reproche.

**El punto que de verdad hay que sacar de la reunión:** la decisión sobre el origen de
los hechos victimizantes (punto 5a de `decisiones_negocio_pendientes.md`). Es lo único
que hoy bloquea que los reportes salgan completos, y no lo podemos resolver nosotros.
