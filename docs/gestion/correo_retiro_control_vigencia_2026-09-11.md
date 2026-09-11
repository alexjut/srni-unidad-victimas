# Correo — Respuesta al retiro del control de vigencia

**Estado:** borrador listo para revisar y enviar
**Para:** María Elena Silva Fandiño — Subdirectora encargada, Red Nacional de Información
**CC:** Alexandra María López Sevillano (Dirección técnica) · Oscar Manosalva (Supervisión SRNI) · Jorge Cardona (Calidad) · Nixon Alonso Duarte Acosta (Seguridad de la información) · Brandon Niño (Panel de Control)
**Asunto:** Retiro del bloqueo por ficha vigente — cómo lo vamos a implementar y qué quedará registrado
**Adjunto sugerido:** `plan_registro_silencioso_vigencia.md`
**Fecha:** 11 de septiembre de 2026

> **Por qué está escrito así.** La decisión ya está tomada y el correo **no la
> discute**: la acata y dice cómo se ejecuta. Deja constancia técnica de la
> objeción —una sola vez, sin insistir— porque esa constancia es la que protege
> al equipo si dentro de un año alguien pregunta por qué se hizo, y porque quien
> ejecuta un cambio tiene el deber de advertir sus consecuencias aunque no le
> corresponda decidirlo.
>
> **Lo que no dice, a propósito:** no menciona «auditoría silenciosa» ni sugiere
> que se guarde algo a espaldas de nadie. Lo que se guarda se dice de frente, en
> el numeral 3. Un registro que hay que ocultar es un registro que no se puede
> usar después, que es justamente para lo que lo queremos.

---

Doctora María Elena, buen día.

Recibimos la indicación que usted impartió en la reunión con los funcionales de
caracterización: **el bloqueo por ficha vigente se retira**, de modo que
cualquier persona del padrón pueda caracterizarse en el momento en que la
operación lo requiera, sin autorización previa.

**La instrucción queda acatada.** Abajo está cómo la vamos a ejecutar, qué
dejamos de exigir, qué seguimos registrando y en qué fechas, más una advertencia
técnica que tengo el deber de dejar por escrito.

## 1. Lo que se retira

| | Hoy | Desde el cambio |
|---|---|---|
| Persona caracterizada hace menos de dos años | El sistema **no deja continuar** | Se caracteriza normalmente |
| Autorización previa de coordinación | Obligatoria | **Se elimina** |
| Radicado y soporte documental | Obligatorios | **Se eliminan** |
| Perfil con permiso especial | Necesario | **Ya no interviene** |
| Espera del encuestador en campo | De horas a días | **Ninguna** |

El encuestador deja de encontrarse con la pared y no tiene que hacer nada
distinto de lo que hace hoy. Ese era el punto de la solicitud y queda resuelto
por completo.

## 2. Lo que esto significa en cifras

Medido sobre producción el 11 de septiembre:

| | |
|---|---|
| Padrón | 5.926.196 personas |
| Con caracterización registrada | 2.536.018 |
| **Con ficha vigente hoy** (menos de dos años) | **973.964** |
| De esas, bloqueadas hoy por el sistema | 973.963 |

Es decir: **973.964 personas quedan disponibles para recaracterización desde el
día en que el cambio entre.** Vale decir también que el control hoy opera
correctamente —bloquea 973.963 de 973.964—, de modo que no se está retirando algo
que estuviera fallando.

## 3. Lo que sí vamos a seguir registrando, y por qué

La solicitud es que el sistema **no detenga** al encuestador. Eso lo cumplimos
por completo. Lo que no hay razón para perder es el **dato**, porque no le cuesta
un segundo a nadie en campo: **lo escribe el sistema solo, al cerrar la
encuesta**, sin pantallas, sin permisos y sin pedirle nada a nadie.

Por cada caracterización hecha sobre una persona que aún tenía ficha vigente
quedará:

- quién la hizo y cuándo;
- sobre qué persona;
- la ruta de entrevista que el funcionario eligió;
- la fecha de la caracterización anterior y cuántos días le faltaban por vencer;
- la entrevista y el hogar concretos.

**Para qué sirve.** El día que la Contraloría, control interno o la propia
Subdirección pregunten cuántas recaracterizaciones se hicieron sobre fichas
vigentes, quién las hizo y en qué territorial, la respuesta va a existir. Sin
este registro, esa pregunta no tiene respuesta posible y la entidad queda sin
cómo explicar un millón de fichas reescritas.

Quiero ser explícito en un punto: **esto no es una autorización disfrazada.** No
hay nadie que apruebe, no hay nada que esperar y el encuestador no se entera de
que se está escribiendo. Es un libro de registro, no una puerta.

## 4. La advertencia técnica, por una sola vez

Tengo el deber de dejarla por escrito, y con esto queda dicha.

**Lo que se pierde no es el poder de recaracterizar: es el porqué.** El control
actual nunca impidió recaracterizar; exigía decir con qué soporte. Retirado,
dos caracterizaciones de la misma persona con veinte días de diferencia quedan
indistinguibles entre sí, y el sistema podrá decir quién y cuándo, pero **nunca
por qué**. La ruta que elige el encuestador es lo más cercano que tendremos, y es
una lista de opciones, no una explicación.

**El daño no se revierte.** Reponer la regla más adelante es cambiar un
interruptor, pero para entonces habrá caracterizaciones duplicadas sin criterio
para decidir cuál es la vigente. Ese problema exacto lo tiene hoy el sistema
anterior y es una de las razones por las que se está reemplazando.

**El control también protegía al encuestador.** Evitaba que dos funcionarios
capturaran el mismo hogar sin saberlo, con el segundo sobrescribiendo el trabajo
del primero.

Dicho eso: **la regla es del Manual de Usuario, numeral 5.1.1, y es una
definición misional, no técnica.** Quien la define es quien puede retirarla, y
esa no es la ingeniería. Procedemos.

## 5. El hogar de la persona se actualiza, no se duplica

Hay una segunda regla, independiente de la vigencia, que de no atenderse quedaría
siendo el nuevo obstáculo: **una persona solo puede tener un hogar activo**. Si
retiráramos la vigencia sin más, el encuestador ya no vería «ficha vigente»,
avanzaría, y al conformar el hogar se encontraría con *«esta víctima ya tiene un
hogar activo registrado por otro encuestador»*. Habríamos cambiado un bloqueo que
se entendía por otro que no.

**Queda resuelto así: la caracterización nueva actualiza el hogar que la persona
ya tiene.** No se crea uno nuevo ni se archiva el anterior.

El criterio es que **el hogar es la familia, no la entrevista**. Cada
caracterización se guarda como una entrevista más dentro de ese hogar, con su
propia fecha y a nombre de quien la hizo. Así:

- la historia de la familia no se pisa: se acumula, y se puede ver la evolución
  entre una caracterización y la siguiente;
- el sistema conserva la capacidad de decir **cuántas familias** hay, que se
  perdería si cada recaracterización estrenara hogar;
- el encuestador que está en campo puede continuar aunque el hogar lo haya creado
  un compañero, sin pedir reasignación a nadie.

## 6. Lo que vamos a vigilar y conviene que usted sepa

Con el bloqueo retirado, **dos encuestadores pueden caracterizar el mismo hogar
el mismo día sin enterarse.** Antes la regla de vigencia lo impedía de rebote; ya
no lo hará.

El registro del numeral 3 lo va a mostrar con precisión —dos entrevistas del
mismo hogar, la misma semana, autores distintos—, pero mostrarlo es todo lo que
puede hacer. Corregirlo es trabajo de supervisión, y por eso la consulta de
seguimiento que mencionamos abajo importa más de lo que parece: **un registro que
nadie revisa equivale a no tenerlo.**

## 7. Fechas propuestas

| Cuándo | Qué |
|---|---|
| **Hasta el 29 de septiembre** | **No se toca nada.** Las tres jornadas se dictan con el sistema como está |
| Semana del 30 de septiembre | Entra el cambio: sin bloqueo, con registro automático |
| En paralelo | Verificación de que el sistema anterior acepte la segunda escritura |
| Antes de la siguiente capacitación | Ajuste del Manual de Uso y del material |

**Por qué no antes del 29.** El material de las tres jornadas está construido
sobre este flujo: un caso de estudio completo, una sección propia del Manual de
Uso y **2 de las 10 preguntas** del cuestionario de evaluación. Cambiarlo antes
del 15 deja el material enseñando algo que ya no existe; cambiarlo entre jornadas
deja a un grupo capacitado en un procedimiento y a los otros dos en el contrario.

Si la operación necesita el cambio antes de esa fecha, lo hacemos; solo
necesitaríamos saberlo con cuarenta y ocho horas para rehacer el material.

## 8. Lo que necesitamos de usted

1. **Confirmación de las fechas del numeral 7**, o la instrucción de adelantarlas.
2. **Visto bueno al criterio del numeral 5** — la caracterización nueva actualiza
   el hogar existente. Si la operación esperaba un hogar nuevo por cada
   caracterización, es el momento de decirlo: cambia el diseño.
3. **Constancia escrita de la decisión** —este correo respondido basta— para
   dejarla en el expediente del proyecto junto con el numeral 5.1.1 del manual.

Quedo atento y a disposición para explicarlo en el espacio que usted disponga.

Cordialmente,

**Javier Alexander Aguilar Castro**
Referente de caracterización — arquitectura y desarrollo
Subdirección Red Nacional de Información · Unidad para las Víctimas

---

## Anexo para uso interno — no enviar

**Qué implementar.** Está en `docs/operacion/plan_registro_silencioso_vigencia.md`.
Resumen: un interruptor en `describir_elegibilidad`, un modelo nuevo
`RecaracterizacionVigente` escrito al cerrar la encuesta, y la salida del hogar
del numeral 5.

**Por qué el correo no dice «auditoría silenciosa».** Porque por escrito, ante la
Subdirectora, eso se lee como guardar algo a espaldas de la operación. El
registro se declara de frente en el numeral 3: es automático, no lo ve el
encuestador, y existe para poder responder preguntas de control. Dicho así es
defendible en cualquier mesa; dicho como «silenciosa» no lo es, y encima le quita
fuerza a lo único que estamos conservando.

**Por qué la objeción va una sola vez y en pasado.** La decisión está tomada por
quien podía tomarla. Repetir la advertencia en tres numerales distintos convierte
un correo de ejecución en uno de resistencia, y lo que se busca es exactamente lo
contrario: que quede constancia de que se advirtió **y** de que se ejecutó sin
fricción.
