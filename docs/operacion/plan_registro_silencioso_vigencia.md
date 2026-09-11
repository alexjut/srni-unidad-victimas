# La autorización que ya no autoriza — plan del registro silencioso

**Decidido el 11-sep-2026** por la Subdirectora encargada en reunión con los
funcionales de caracterización: **se retira el bloqueo por ficha vigente**.
Cualquier persona del padrón puede caracterizarse cuando el encuestador lo
necesite, sin pedirle permiso a nadie.

Este documento es cómo lo vamos a hacer sin perder la información.

---

## 1. La diferencia entre lo que se quita y lo que se conserva

Lo que molesta de la regla no es que registre: es que **detiene**. El encuestador
llega donde la persona, no puede continuar, y tiene que volver a la oficina a
pedir una autorización que puede tardar días. Eso es lo que se quita.

Lo que no hay razón para quitar es el **dato**: que esa caracterización se hizo
sobre una ficha que seguía vigente, quién la hizo, cuándo y por qué ruta. Ese
dato no le cuesta un segundo a nadie en campo, porque **el sistema lo escribe
solo**.

| | Hoy | Desde el cambio |
|---|---|---|
| ¿Se puede caracterizar a cualquiera? | No | **Sí, siempre** |
| ¿Hace falta autorización previa? | Sí | **No** |
| ¿Hace falta radicado y soporte? | Sí | **No** |
| ¿Hace falta un perfil especial? | Sí | **No** |
| ¿El encuestador elige la ruta? | Sí | Sí, igual que hoy |
| ¿Queda registro de quién recaracterizó y sobre qué? | Sí, como autorización | **Sí, como registro automático** |

**Nadie tiene que hacer nada distinto a lo que hace hoy.** Simplemente deja de
encontrarse con la pared.

---

## 2. Qué se guarda, y por qué esas cosas

Una fila por cada caracterización hecha sobre una persona que todavía tenía ficha
vigente. Se escribe al cerrar la encuesta, sin intervención de nadie:

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

---

## 3. Por qué una tabla nueva y no la que ya existe

`ExcepcionVigencia` es un **permiso otorgado**: tiene quién lo autorizó, el
radicado del soporte y el motivo escrito por una persona. El registro nuevo no
tiene ninguna de las tres cosas, porque ya no hay autorizante ni soporte.

Meter las dos cosas en la misma tabla dejaría una mitad de las filas con el
sentido contrario a la otra, y dentro de un año nadie sabría cuáles
correspondieron a un fallo judicial verificado y cuáles a una recaracterización
de rutina. Las filas que ya existen son la evidencia del régimen anterior y hay
que poder seguir distinguiéndolas.

Modelo nuevo: `RecaracterizacionVigente`, en el mismo módulo.

---

## 4. Qué pasa con lo que ya está construido

Nada se borra. Se deja **inerte**, que es distinto:

| Pieza | Qué se hace |
|---|---|
| Tabla `ExcepcionVigencia` | Se conserva. Solo lectura. Deja de crear filas |
| API `/api/habilitaciones/` | Sigue respondiendo consultas. Deja de aceptar autorizaciones nuevas |
| Pantalla de autorizaciones | Pasa a ser consulta del histórico |
| Permiso `puede_autorizar_excepciones` | Se conserva en el modelo, sin uso |

**Por qué no se borra:** si el área funcional repone la regla dentro de seis
meses —y estas decisiones se reponen—, reponerla cuesta cambiar un interruptor.
Borrarlo todo hoy convierte esa vuelta atrás en volver a construirlo.

El interruptor es uno solo: una opción de configuración que consulta
`describir_elegibilidad`, que es el único lugar donde hoy se decide si alguien
puede o no caracterizarse. Fuera de ahí, ningún módulo cambia de comportamiento.

---

## 5. El hogar: se actualiza el que ya existe — DECIDIDO

**Decisión de Javier, 11-sep-2026: no se crea un hogar nuevo. Se actualiza el
hogar que esa persona ya tiene.**

Es la opción correcta: **el hogar es la familia, no la entrevista.** Crear uno
cada vez que se recaracteriza multiplicaría los hogares de la misma familia y
volvería incontable cuántas familias hay, que es una de las cifras que el sistema
tiene que poder dar.

Cada caracterización es una **sesión** dentro de ese hogar, y cada sesión tiene su
propio autor y su propia fecha. La historia no se pisa: se acumula.

### Por qué esto no es «no hacer nada»

Hoy el sistema ya reutiliza el hogar existente… **solo si es del mismo
encuestador.** Si lo creó otro, responde *«esta víctima ya tiene un hogar activo
registrado por otro encuestador. Solicita su reasignación al supervisor»* y ahí
se acaba el camino: no hay pantalla de reasignación, y el encuestador que está
parado frente a la persona no puede seguir.

Retirar la vigencia sin arreglar esto sustituye un bloqueo que se entendía y
tenía salida por otro que no se entiende y no la tiene. **La queja volvería en
una semana, con razón.**

### Qué hay que cambiar, en concreto

**El hogar deja de ser propiedad de un encuestador y pasa a ser el registro de la
familia.** Eso es un cambio de concepto, y de él salen tres consecuencias:

1. **Al conformar, el hogar existente se devuelve siempre**, sea de quien sea. Se
   acaba el 409.
2. **No se reasigna la propiedad.** Quitarle el hogar al primer encuestador para
   dárselo al segundo le borraría de «mis encuestas» un trabajo que sí hizo. El
   hogar simplemente deja de tener dueño exclusivo.
3. **La autoría vive en la sesión, no en el hogar.** Cada caracterización queda a
   nombre de quien la hizo, que es donde siempre debió estar. El hogar conserva
   quién lo creó, como dato histórico.

La visibilidad se amplía en consecuencia: hoy el encuestador solo ve los hogares
que él creó. Pasa a ver también aquel sobre el que está caracterizando. **No se
abre el listado entero**: ver un hogar por estar trabajándolo no es lo mismo que
poder navegar los hogares de todo el país.

### Lo que hay que vigilar

Dos encuestadores pueden terminar caracterizando el mismo hogar el mismo día sin
enterarse, y antes el bloqueo lo impedía de rebote. Ya no. El registro del
numeral 2 lo va a mostrar —dos sesiones del mismo hogar, misma semana, autores
distintos—, pero mostrarlo es todo lo que va a hacer.

---

## 6. La otra casilla que hay que medir antes de prometer una fecha

**El Oracle del sistema anterior tiene su propia regla de vigencia.** Que SICAV
deje de bloquear no significa que el destino acepte la segunda escritura: los
procedimientos `GIC_*` pueden rechazarla, o peor, aceptarla en silencio y no
escribir nada —ese comportamiento ya está documentado—.

Hay que probarlo contra producción con un caso real antes de comprometer la
fecha. Es lo único de este plan con trabajo de verdad detrás, y es lo que puede
convertir «una línea» en varios días.

---

## 7. Fases

| Fase | Qué | Cuándo |
|---|---|---|
| **0** | **No se toca nada.** Las tres jornadas se dictan con el sistema como está | Hasta el 29 de septiembre |
| **1** | Interruptor de vigencia + registro silencioso + salida del hogar (§5) | Después del 15, con la decisión de §5 tomada |
| **2** | Prueba de la escritura al sistema anterior (§6) | En paralelo con la 1 |
| **3** | Consulta de recaracterizaciones para el informe | Después de la 1 |
| **4** | Ajuste del Manual de Uso, del Caso 2 del Anexo C y de las dos preguntas del cuestionario | Antes de la siguiente capacitación |

**Por qué la fase 0 existe.** El material de las tres jornadas —el caso de
estudio 2, una sección propia del manual y 2 de las 10 preguntas del
cuestionario— está construido sobre el flujo de autorización. Cambiarlo antes del
15 deja el material enseñando algo que ya no existe; cambiarlo a mitad de las
tres jornadas deja a un grupo capacitado en un procedimiento y a los otros dos en
el contrario. Se dictan las tres con lo que hay, y el cambio entra después.

---

## 8. Lo que este plan no resuelve, y conviene decirlo

**Sin autorización no hay motivo escrito.** La ruta que elige el encuestador es
lo más cercano que vamos a tener, y es una lista de opciones, no una explicación.
El día que alguien pregunte *por qué* se recaracterizó a una persona a los tres
días, el sistema va a poder decir quién y cuándo, pero no por qué. Es una
consecuencia aceptada de la decisión, no un defecto del diseño.

**El registro no impide nada.** Es un libro, no una puerta. Si la operación
empieza a recaracterizar masivamente, el sistema lo va a anotar con precisión y
no va a hacer nada al respecto. Que alguien mire ese libro es una decisión de
supervisión, no del sistema, y por eso la fase 3 —la consulta— importa más de lo
que parece: un registro que nadie consulta es lo mismo que no tenerlo.
