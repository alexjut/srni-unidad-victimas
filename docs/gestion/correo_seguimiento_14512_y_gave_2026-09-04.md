# Correo de seguimiento — Caso 14512 y tablero del GAVE

**Estado:** listo para enviar
**Para:** Maria Elena Silva Fandiño — Subdirectora (E), Subdirección Red Nacional de Información
**CC:** Jorge Cardona (Calidad) · Daniel Puín · Fabio Mesa · Dora Vivas · Natalia Grisales
**Asunto:** Seguimiento — Caso 14512 (20 noches sin carga) y tablero GAVE (sin reconstruir desde el 27 de agosto)
**Fecha:** 4 de septiembre de 2026
**Antecede a:** `correo_gerencial_caso_14512.md` (28-ago) y `correo_tablero_gave_panama.md` (27-ago), ambos enviados el 1 de septiembre

---

Respetada Subdirectora, buenos días.

Escribo para dar seguimiento a los dos asuntos que le remití el 1 de septiembre. **Las cifras
de este correo se midieron hoy**, no se copiaron de los informes anteriores, y en los dos
casos se han deteriorado.

## 1. Caso 14512 — la carga sigue detenida, y ya van veinte noches

El proceso que sube al sistema las encuestas capturadas sin conexión **no ha vuelto a
funcionar**. Medido esta mañana sobre el registro de ejecuciones:

| | |
|---|---|
| Última carga exitosa | **14 de agosto** |
| Noches consecutivas fallando | **20** — incluida la de anoche |
| Duración de cada intento fallido | **1 segundo** — el mismo error de acceso a la carpeta |

Cuando le escribí eran doce noches. Hoy son veinte. El error no cambió y la causa tampoco:
**la carpeta de trabajo sigue sin acceso.**

Las dos decisiones que solicité siguen pendientes y son las mismas:

1. **Suspender la eliminación diaria de archivos.** Cada día que la operación borra lo que
   copió el día anterior, se pierde trabajo de campo que nunca alcanzó a entrar. No requiere
   ningún cambio técnico: es una instrucción.
2. **Restablecer el acceso a la carpeta** en el servidor de Modelo. Media hora de trabajo
   para quien administre ese servidor.

**La ventana de recuperación no se detiene.** Para las encuestas de mediados de julio el
plazo vence alrededor del 12 de octubre. Cada semana que pasa, un tramo de lo represado deja
de ser recuperable por la vía normal.

## 2. Tablero del GAVE — volvió a quedarse atrás, como estaba previsto

En el informe del 27 de agosto le expliqué que el tablero se alimenta de una tabla de reporte
que **no se actualiza sola**, y que la reconstruimos manualmente ese día a las 8:54 a. m.
También advertí que, sin programar la ejecución, el desfase volvería a aparecer.

Ocurrió. Verificado hoy:

| | |
|---|---|
| Última reconstrucción del reporte | **27 de agosto, 8:54 a. m.** — la que hicimos nosotros |
| Corte de la información que muestra hoy | **26 de agosto** (2.141 registros, las mismas cifras de aquel día) |
| Trabajo programado que lo ejecute | **Sigue sin existir** |

Es decir: **el tablero lleva nueve días mostrando un corte viejo**, y volverá a pasar cada vez
que nadie ejecute el procedimiento a mano. La reconstrucción del 27 de agosto no fue una
solución: fue un parche de un día.

Aprovecho para dejar constancia de que el procedimiento fue intervenido el 16 de agosto por
los ingenieros **Daniel Puín y Fabio Mesa**, cuyo trabajo forma parte de la solución
técnica. Lo que falta no es técnico: es **la autorización para programar la ejecución
automática**, que solicité en el numeral 4 de aquel informe y que sigue sin respuesta.

También sigue abierta la pregunta de **quién administra el refresco del conjunto de datos en
Power BI**. Sin ese dato, aunque programemos la reconstrucción en la base, el tablero puede
seguir mostrando información vieja por el otro extremo de la cadena.

## 3. Lo que necesito de usted

| # | Decisión | De quién depende | Lleva esperando |
|---|---|---|---|
| 1 | Suspender la eliminación diaria de archivos del FTP | Operación | 20 noches |
| 2 | Restablecer el acceso a la carpeta de trabajo | Administrador del servidor de Modelo | 20 noches |
| 3 | Autorizar la programación automática del reporte del GAVE | Su instrucción | 9 días |
| 4 | Confirmar quién administra el refresco en Power BI | Su instrucción | 9 días |

Los cuatro puntos son de baja complejidad técnica. Ninguno depende de desarrollo nuevo, y
los cuatro llevan escalados por escrito desde el 1 de septiembre.

Quedo atento a su instrucción. Si prefiere, puedo presentar los cuatro puntos en una reunión
corta con las áreas responsables.

Cordialmente,

**Javier Alexander Aguilar Castro**
Arquitectura y desarrollo — Sistema de Caracterización de Víctimas (SICAV / SRNI)

---

## Notas para el remitente (no enviar)

**Por qué este correo une los dos asuntos.** El 27 de agosto recomendé lo contrario:
separarlos para no diluir la urgencia. Esa razón ya no aplica. Ahora los dos están en el
mismo estado —escalados, sin respuesta, y deteriorándose— y ante la misma persona. Un
seguimiento único con cuatro decisiones numeradas es más difícil de archivar que dos correos
que repiten lo ya dicho.

**Lo que este correo no afirma.** Sigue sin decir cuántas encuestas se han perdido, por la
misma razón que el anterior: no se ha contado, y el registro de las eliminaciones no existe.
Veinte noches sin carga no es lo mismo que veinte noches de pérdida, y no conviene confundirlos.

**Tampoco dice que nadie haya hecho nada.** El trabajo de Daniel y Fabio sobre el
procedimiento del GAVE es real y está reconocido en el numeral 2. Lo que falta es una
autorización, no esfuerzo técnico.

**Cómo se midió, por si preguntan.** Consultas de solo lectura del 4 de septiembre:

| Afirmación | Cómo se verifica |
|---|---|
| Última carga exitosa el 14 de agosto y 20 noches fallando | `ALL_SCHEDULER_JOB_RUN_DETAILS@DBL_RNIENTREVISTA` para `JOB_PCD_FN_FTP_PC_IJ`, últimos 30 días: 30 corridas, 10 correctas hasta el 14-ago y 20 fallidas seguidas con `ORA-29283` |
| El reporte del GAVE no se reconstruye desde el 27 de agosto | `JOB_REPORTE_GAVE` tiene una sola corrida registrada: 2026-08-27 08:54 |
| El tablero muestra el corte del 26 de agosto | `SELECT COUNT(*), MAX(fecha_creacion) FROM rnientrevista.inh_reporte_gave@consultamodelo110` → 2.141 filas, máximo 2026-08-26 17:26 |
| Sigue sin job programado | `SELECT * FROM all_scheduler_jobs@consultamodelo110 WHERE UPPER(job_name) LIKE '%GAVE%'` → sin filas |

**Cuidado al reenviar el correo del 28 de agosto.** Su cifra central —«doce días
fallando»— quedó vieja. Si se reenvía tal cual, la Subdirectora recibe un número menor al
real y el asunto pierde urgencia en vez de ganarla. Por eso este seguimiento es un correo
nuevo y no un reenvío.
