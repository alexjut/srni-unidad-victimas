# Respuesta — Inclusión pregunta de autorreconocimiento campesino

**Estado:** listo para enviar
**Para:** Maria Elena Silva Fandiño — Subdirectora (E), Subdirección Red Nacional de Información
**CC:** Alejandro Fernández, Alexandra López, Natalia Grisales, Fabián Agudelo, Jorge Bernal, Dora Vivas
**Asunto:** RE: Inclusión pregunta Caracterización — estado técnico, insumos faltantes y estimación de esfuerzo
**Fecha:** 27 de agosto de 2026

> Todas las cifras del correo se midieron hoy contra los nueve archivos de parametrización
> vigentes del instrumento. El anexo indica cómo verificar cada una.

---

Respetada Subdirectora, buenas tardes.

En atención a su solicitud de retroalimentación sobre el requerimiento de la Dirección de
Registro y Gestión de la Información, presento el estado técnico del asunto, los insumos
que hacen falta y una estimación de esfuerzo.

## 1. Por qué no se ha ejecutado

**A la fecha no se ha recibido el documento oficial que soporta la solicitud.** Lo recibido
es el enunciado de una pregunta en el cuerpo de un correo, remitido hoy a las 3:34 p. m.,
con solicitud de respuesta para mañana antes del mediodía.

La herramienta de entrevista de caracterización no se parametriza a partir de un enunciado.
Se genera a partir de tres artefactos controlados **por cada uno de los ocho perfiles**:

- el **diccionario de datos**, que define la variable, su tipo y su dominio de respuesta;
- el archivo de **flujos de preguntas**, que define su posición y las reglas que la gobiernan;
- el **manual de usuario (MU)**, que es el documento oficial del instrumento.

Esos tres documentos son la fuente formal contra la cual se construye y se valida el
instrumento, y son también los que deben indicar **exactamente dónde va la pregunta en cada
perfil**. Ninguno ha sido actualizado ni entregado con la pregunta solicitada.

**La razón por la cual el requerimiento no se ha ejecutado no es de capacidad técnica: es
que el insumo que lo hace ejecutable no ha sido entregado.** Sin él no hay especificación
que parametrizar, y lo que llegara a parametrizarse no podría validarse contra ningún
documento oficial.

El requerimiento tampoco ingresó por la mesa de servicios (Aranda), por lo que no existe
caso asociado, ni especificación técnica formal, ni priorización frente al resto del plan de
trabajo. En los repositorios técnicos del proyecto no obra registro de la solicitud previa a
la que el correo hace referencia.

## 2. Sobre qué se está pidiendo intervenir

La solicitud pide la inclusión «en todas las versiones de la herramienta». Eso es, hoy, lo
siguiente:

| Perfil | Versión | Capítulos | Preguntas | Reglas de salto | Opciones |
|---|---|---:|---:|---:|---:|
| Buenaventura | V7 | 16 | 380 | 199 | 1.053 |
| Territorial | V8 | 14 | 363 | 276 | 939 |
| San Andrés | V7 | 15 | 334 | 199 | 938 |
| Territorial | V7 | 14 | 319 | 238 | 945 |
| Urbano Étnico | V1 | 10 | 176 | 74 | 523 |
| Víctimas en el Exterior | V1 | 8 | 110 | 0 | 362 |
| Rural Étnico | V1 | 14 | 106 | 11 | 651 |
| Asistencia | V8 | 8 | 105 | 43 | 228 |
| Telefónico | V8 | 7 | 66 | 3 | 382 |
| **Total** | | **106** | **1.959** | **1.043** | **6.021** |

No se trata de agregar una pregunta a un formulario. Se trata de intervenir **nueve
parametrizaciones en producción**, con 1.043 reglas de flujo activas, de las cuales **212
tienen su origen en el capítulo donde se pide insertar la pregunta**.

## 3. Lo que la solicitud no define, y sin lo cual no puede implementarse

**3.1 La ubicación indicada no corresponde a la estructura del instrumento.** Se pide
insertar la pregunta «en el Módulo de Información General, como la Pregunta 2, inmediatamente
después de la pregunta de autorreconocimiento étnico». En la parametrización vigente no
existe un módulo con esa denominación —el capítulo equivalente es **A. Identificación**— y
«la Pregunta 2» no ubica una posición única: la pregunta de autorreconocimiento étnico ocupa
**cinco posiciones distintas** según el perfil.

| Perfil | Pregunta de autorreconocimiento étnico | Nivel de captura | Posición |
|---|---|---|---:|
| Territorial V7 y V8 | A4 | **Persona** | 4 |
| Buenaventura V7 | A4 | **Persona** | 29 |
| San Andrés V7 | A4 | **Persona** | 29 |
| Urbano Étnico V1 | A4 | **Persona** | 29 |
| Rural Étnico V1 | A4 | **Hogar** | 4 |
| Telefónico V8 | A5 | **Hogar** | 5 |
| Asistencia V8 | 1 | **Hogar** | 25 |
| Víctimas en el Exterior V1 | A16 | **Hogar** | 16 |

**3.2 No se define el nivel de captura.** Como muestra la tabla, el autorreconocimiento
étnico se captura **por persona en cinco perfiles y por hogar en cuatro**. Se requiere
definición expresa sobre si el autorreconocimiento campesino se pregunta a cada integrante
del hogar o una sola vez por hogar. Metodológicamente el autorreconocimiento es individual;
replicar la ubicación del étnico sin decidirlo produciría un dato con dos naturalezas
distintas según el perfil, **no comparable entre sí ni agregable** —lo contrario de lo que
persigue una variable estadística.

**3.3 No se define el dominio de respuesta.** La solicitud aporta el enunciado pero no las
opciones de respuesta ni su codificación. Sin el conjunto cerrado de opciones la pregunta no
es parametrizable.

**3.4 Falta la codificación en VIVANTO, que emite la Dirección solicitante.** Cada opción de
respuesta lleva un identificador de correspondencia con VIVANTO (`id_resp_vivanto`) sin el
cual la respuesta se captura en el dispositivo pero **no puede migrarse a los sistemas de
información de la entidad**. Hoy **4.416 de las 5.062 opciones catalogadas (87,2 %)** cuentan
con ese identificador. Ese código no puede asignarlo el equipo técnico del proyecto: lo
emite quien administra el RUV y VIVANTO, es decir **la propia Dirección de Registro y Gestión
de la Información**. Es exactamente la armonización que invoca el considerando 6 del
requerimiento, y es una condición **previa** a la parametrización, no posterior.

**3.5 No se define el alcance.** «Todas las versiones» comprende los ocho perfiles,
incluidos Telefónico, Asistencia y Víctimas en el Exterior, cuya pertinencia frente a una
pregunta de autorreconocimiento campesino debe valorarse expresamente. Comprende además las
versiones V7 que continúan en operación.

**3.6 No se definen las reglas de flujo asociadas.** Debe establecerse si la nueva pregunta
habilita preguntas dependientes, si queda condicionada por la respuesta étnica, y qué ocurre
con las 212 reglas cuyo origen está en el capítulo de identificación.

**3.7 No se define el tratamiento de lo ya capturado.** Debe establecerse qué ocurre con las
caracterizaciones cerradas bajo la versión vigente y con las sesiones en curso al momento
del despliegue.

## 4. Estimación de esfuerzo

Con los insumos completos en mano, y sin contar el tiempo que tome producirlos, la
intervención se estima así. El cómputo es de **días-persona de trabajo técnico
especializado**:

| Actividad | Días-persona |
|---|---:|
| Especificación técnica por perfil a partir del diccionario y los flujos | 2 |
| Parametrización de los nueve archivos, catálogo de opciones e identificadores | 4 |
| Revisión y ajuste de las reglas de flujo afectadas | 3 |
| Correspondencia con VIVANTO y con las tablas de migración | 2 |
| Pruebas de regresión sobre los ocho perfiles | 4 |
| Nueva versión del instrumento, compilación y publicación de la aplicación | 2 |
| Actualización del manual de usuario y del material de capacitación | 2 |
| **Total** | **19 días-persona** |

Equivale a **entre tres y cuatro semanas calendario** para un profesional dedicado, o cerca
de dos semanas con dos personas en paralelo, siempre **a partir de la entrega de los
insumos**. No es una estimación conservadora: es el costo de intervenir 1.959 preguntas y
1.043 reglas en producción sin degradar la información ya capturada.

**Un elemento adicional de oportunidad.** La capacitación a los treinta enlaces
territoriales está programada para el **1, 3 y 8 de septiembre**. Una modificación del
instrumento en ese lapso invalidaría el material ya elaborado y obligaría a recapacitar. Se
recomienda ejecutar el cambio **después** de esas jornadas.

## 5. Lo que se requiere para atender el requerimiento

| # | Insumo | Responsable |
|---|---|---|
| 1 | **Documento oficial** de la solicitud, con la especificación de la variable | Dirección de Registro y Gestión de la Información |
| 2 | Diccionario de datos actualizado por perfil: variable, tipo, dominio y codificación | Dirección de Registro / Subdirección RNI |
| 3 | Archivo de flujos de preguntas actualizado, con posición exacta y reglas | Dirección de Registro / Subdirección RNI |
| 4 | Manual de usuario (MU) actualizado del perfil correspondiente | Subdirección RNI |
| 5 | Identificadores de correspondencia en VIVANTO/RUV para cada opción | Dirección de Registro y Gestión de la Información |
| 6 | Definición del nivel de captura (persona u hogar) y del alcance por perfil | Dirección de Registro / Subdirección RNI |
| 7 | Caso formal en la mesa de servicios (Aranda) | Solicitante |

**El tiempo de atención comienza a contar desde la recepción de estos insumos**, no desde la
fecha del correo.

## 6. Consideración final

El equipo comparte plenamente el fundamento normativo del requerimiento y no tiene reparo
alguno frente a la inclusión de la pregunta. La observación es exclusivamente de orden
técnico y de calidad del dato.

Una variable incorporada sin diccionario, sin flujo, sin manual y sin correspondencia en
VIVANTO produce información que **no se puede validar, no se puede migrar y no se puede
reportar**. Sería incorporar la pregunta y no obtener el dato —justamente lo contrario de lo
que exigen el Acto Legislativo 001 de 2023 y el artículo 9 de la Ley 2421 de 2024 al ordenar
la producción de información estadística específica sobre la población campesina.

Quedo atento a coordinar una mesa técnica con la Dirección de Registro y Gestión de la
Información para precisar los siete insumos y acordar el cronograma.

Cordialmente,

**Javier Alexander Aguilar Castro**
Arquitectura y desarrollo — Sistema de Caracterización de Víctimas (SICAV / SRNI)
Contrato 2226-2026

---

## Anexo para uso interno — verificación de las cifras

| Afirmación | Cómo se verifica |
|---|---|
| Nueve parametrizaciones vigentes | `srni-backend/apps/formulario/fixtures/perfil_*.json` |
| 106 capítulos · 1.959 preguntas · 1.043 reglas · 6.021 opciones | Recuento sobre `capitulos`, `preguntas`, `reglas_skip_logic` y `opciones` en los nueve archivos |
| Posición y nivel de la pregunta étnica | `codigo_externo` = `Z4` / `Z4_tel` / `Z4_re` / `A16_vex`; campos `nivel` y `orden` |
| 212 reglas con origen en el capítulo A/Z | Filtro sobre `reglas_skip_logic[].origen` |
| 5.062 opciones catalogadas · 4.416 con `id_resp_vivanto` (87,2 %) | Recuento sobre `opciones[].id_resp_vivanto`; 646 sin identificador |
| Artefactos de gobierno del instrumento | `docs/perfiles/<Perfil>/Diccionario_de_datos_*.xlsx`, `Flujos_preguntas_*.xlsx`, y los manuales `11-MU` y `14-MU` |
| Sin registro de solicitud previa | Búsqueda de «campesin» en el repositorio: aparece solo como **opción de respuesta** de preguntas existentes —«Zonas de reserva campesina» en tipo de territorio, «Campesina» en tipo de organización—. No existe ninguna pregunta de autorreconocimiento campesino. |

**Nota.** Los perfiles Rural Étnico y Víctimas en el Exterior tienen 0 % de cobertura de
`id_resp_vivanto` (53 y 362 opciones). No es un defecto introducido por este requerimiento,
pero conviene tenerlo presente en la mesa técnica: son perfiles que hoy capturan información
sin ruta de migración definida.

**Advertencia de uso.** La estimación de la sección 4 es de esfuerzo técnico y no incluye el
tiempo de producción de los insumos por parte del solicitante, ni tiempos de aprobación
institucional. Si la Subdirección requiere un cronograma con fechas, se elabora al recibir
los insumos.
