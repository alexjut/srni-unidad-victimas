# Correo a Oscar — DIFICULTAD URGENTE: el servidor no tiene disco para la migración

> Borrador para revisión de Javier. **Es un escalamiento**, no una consulta técnica:
> el espacio del servidor bloquea la carga del universo de víctimas y, con ella, la
> migración. Va a Oscar como supervisor, para que lo lleve a OTI / infraestructura.
>
> Todos los números están medidos el 5-ago-2026 sobre el servidor en producción, con
> la carga corriendo. Evidencia completa:
> [`docs/infraestructura/analisis_capacidad_disco.md`](../infraestructura/analisis_capacidad_disco.md).

---

**Para:** Oscar Andrés Manosalva García — Supervisión SRNI
**CC:** [PMO — Rommey Edwin Ruiz Rivera] · [OTI — infraestructura]
**Asunto:** 🔴 URGENTE — El servidor de SICAV se queda sin disco: la migración del universo de víctimas no cabe (PRY-0662064)

Oscar, buen día.

Escalo una **dificultad urgente de infraestructura**. No es un problema de desarrollo:
el código está listo y probado, y la carga del universo de víctimas **está corriendo en
este momento**. El problema es que **el servidor no tiene disco suficiente para
sostenerla**, y sin resolverlo la migración no se puede completar ni operar mes a mes.

---

## 1. La situación, en una línea

El servidor tiene **61 GB de disco y hoy quedan 18 GB libres (71 % ocupado)**. Solo el
universo de víctimas que estamos cargando ocupa entre **13 y 19 GB**, y el paso
siguiente —enlazar ese universo con el padrón— necesita **8 GB más de los que hay**.

## 2. Qué se está cargando y por qué es necesario

Dos cédulas reportadas desde el territorio se podían caracterizar en Vivanto y en SICAV
"no existían". La causa: el padrón de SICAV se construía desde el registro de *quién ya
fue caracterizado*, así que **una víctima que nunca pasó por una entrevista era
invisible**. La solución es cargar el **universo completo de víctimas: 12.496.965
personas**, que es la fuente correcta.

Esa carga arrancó y va por el 38 %. Es lo que le devuelve a SICAV la capacidad de
responder "esta persona sí es víctima" sobre el universo real y no sobre un subconjunto.

## 3. Lo que se midió (no es estimación)

| | |
|---|---|
| Disco del servidor | **61 GB** · 43 usados · **18 libres** |
| Base de datos hoy | 23 GB — de los cuales el padrón operativo son 15 GB |
| Universo, ya cargado a medias | 7 GB (4,5 de 12 millones de personas) |
| Universo completo, proyectado | **13 a 19 GB** según se optimice |
| Espacio que pide el paso de enlace | **8 GB** que no existen |
| **Copias de seguridad de la base** | **NINGUNA** — no hay ni tarea programada ni respaldo, y no cabría |

Esa última fila es la que más me preocupa y la traigo aparte: **hoy la base con
5.926.004 víctimas no tiene respaldo**, y no se puede crear uno porque no hay espacio
donde escribirlo. Tampoco se le puede hacer mantenimiento: reorganizar la tabla más
grande exige 15 GB libres para reescribirla, y no los hay.

Y hay un riesgo que va más allá de nuestro proyecto: **ese disco es compartido** con
otros servicios de la entidad (`sidi`, `catálogo SI`, el servicio de autenticación y el
proxy). Si la base se queda sin espacio, **el motor de datos se detiene para todos**,
no solo para SICAV.

## 4. Lo que ya hicimos por nuestra cuenta

Antes de escalar, exprimimos lo que estaba en nuestras manos:

- **Corregimos un proceso** que iba a pedir 19 GB de golpe; ahora pide 88 MB.
- **Detectamos 5,8 GB en índices que no se usan** (medido: cero usos) y los vamos a
  eliminar.
- **Instalamos un vigilante** que detiene la carga si el disco baja de 4 GB, para que
  el servidor no se caiga mientras se resuelve esto.
- Identificamos ~5 GB recuperables en imágenes y registros viejos.

Con todo eso **la carga actual termina**. Lo que no se sostiene es la **operación**: el
universo se actualiza **cada mes**, y cada actualización vuelve a pedir el mismo
espacio.

## 5. Cuánto disco se necesita

Proyección a 12 meses de operación. Los tres primeros conceptos están medidos; el de
las caracterizaciones es una proyección con supuestos explícitos, que anoto abajo.

| Concepto | GB |
|---|---:|
| Padrón operativo de víctimas (actual) | 15 |
| Universo de víctimas — dos cortes conviviendo mientras se valida el nuevo | 26 |
| Hechos victimizantes del RUV (19,9 millones de registros, aún sin cargar) | 8 |
| **Respuestas de caracterización — 12 meses con 1.150 encuestadores** | **176** |
| Copias de seguridad (retención de 7 días) | 100 |
| Espacio de mantenimiento (reorganizar la tabla mayor) | 30 |
| Sistema operativo, contenedores y servicios compartidos | 20 |
| **Subtotal** | **375** |
| Margen operativo (25 %) | 94 |
| **Total** | **~470 GB** |

> *Supuestos de la línea de caracterizaciones:* 1.150 encuestadores · 4 hogares por día ·
> 20 días al mes = 92.000 hogares/mes; ~400 respuestas por hogar (el instrumento
> territorial tiene 197 preguntas, varias por cada miembro del hogar) a ~400 bytes cada
> una ⇒ **~15 GB por mes**. Si la meta de campo es mayor, la cifra sube en proporción.

**Solicitud: ampliar el disco del servidor a 500 GB como mínimo, y a 1 TB si es
posible.**

- **500 GB** cubre los 12 meses proyectados con margen.
- **1 TB** cubre el ciclo de vida del sistema sin volver a pedir ampliación, y permite
  conservar el histórico de cortes mensuales en vez de borrarlos.

Pedir menos nos deja repitiendo esta misma solicitud en pocos meses, con la migración
detenida cada vez.

## 6. No hace falta un servidor nuevo — y verifiqué que no es un tema de configuración

Esto es importante para dimensionar el esfuerzo de OTI: **es una ampliación de disco,
no una migración de servidor ni una reinstalación.**

El servidor es una **máquina virtual sobre plataforma Microsoft**. Revisé si el espacio
faltante era solo un tema de configuración —el caso frecuente en que el disco es grande
pero el sistema de archivos quedó chico y basta con extenderlo— y **no es el caso**: el
disco físico asignado es de **64 GB** y la partición **ya los está usando por completo**.
No hay espacio oculto por recuperar; **falta disco de verdad**.

Las dos vías posibles, ambas estándar y de bajo impacto:

1. **Ampliar el disco actual** en la plataforma de virtualización y extender el sistema
   de archivos. Las herramientas necesarias ya están instaladas en el servidor.
2. **Agregar un disco de datos adicional** y mover ahí la base. Es la opción más limpia:
   separa los datos del sistema operativo y no toca la partición de arranque.

> ⚠️ **Una advertencia para que nadie se confunda al mirarlo:** el servidor muestra un
> segundo disco de 32 GB casi vacío, montado en `/mnt`. **Ese disco es temporal**: la
> plataforma lo borra cada vez que la máquina se apaga o se redimensiona. **No sirve
> para la base de datos** — usarlo significaría perder los datos en el primer
> mantenimiento.

## 7. Qué necesito de usted

1. **Escalar esta solicitud a OTI / infraestructura como urgente**, con el número
   concreto: **500 GB mínimo, 1 TB recomendado**.
2. **Una fecha estimada** de ampliación. Con ella organizo la carga mensual del universo;
   sin ella, cada corte nuevo es un riesgo de dejar el servidor sin espacio.
3. **Una decisión funcional** que sí le corresponde a la supervisión: **¿conservamos el
   corte del mes anterior mientras se valida el nuevo?** Es lo que el diseño previó, es
   la forma segura de validar, y son 13 GB adicionales. Si la respuesta es no, la
   validación del corte nuevo hay que hacerla antes de cargarlo y con otro método.

Quedo atento. Mientras tanto la carga sigue en curso y vigilada; si el disco llega al
límite, el sistema se detiene solo y sin dañar nada, pero **no podremos avanzar a la
etapa de enlace** hasta tener el espacio.

Cordialmente,

**Javier Alexander Aguilar Castro**
Contrato 2226-2026 — Sistema de Caracterización de Víctimas (SICAV / SRNI)
