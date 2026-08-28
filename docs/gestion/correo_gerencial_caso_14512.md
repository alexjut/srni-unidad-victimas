# Correo gerencial — Caso 14512 · Carga de encuestas sin conexión

**Estado:** listo para enviar
**Para:** Maria Elena Silva Fandiño — Subdirectora (E), Subdirección Red Nacional de Información
**CC:** Jorge Cardona (Calidad) · Daniel Puín · Fabio Mesa · Dora Vivas · Natalia Grisales
**Asunto:** Caso 14512 — causa raíz identificada · dos decisiones que requieren su instrucción hoy
**Adjunto:** `Caso-14512-carga-offline.pdf` (18 páginas)
**Fecha:** 28 de agosto de 2026

---

Respetada Subdirectora, buenos días.

Le presento el resultado de la revisión técnica del caso 14512, sobre las encuestas
capturadas sin conexión que no estaban llegando al sistema. **La causa raíz está
identificada y documentada**, y hay dos decisiones que dependen de su instrucción.

## Qué encontramos

El proceso automático que sube al sistema las encuestas levantadas en campo **sí existe y
funcionaba con normalidad hasta el 14 de agosto**. Desde el 16 de agosto **falla todas las
noches**, en menos de cuatro segundos, porque perdió el acceso a la carpeta donde deja los
archivos. Esa carpeta dejó de estar disponible tras un reinicio de la base de datos.

El diagnóstico previo señalaba un proceso deshabilitado desde 2024 y la ausencia de un
responsable para una tarea manual. **No es eso.** Hay dos procesos con el mismo nombre en
dos servidores distintos: el que estaba apagado es una copia sin uso; el que opera de verdad
está encendido, corre todos los días a las 6:20 de la tarde, y es el que está fallando.

La consecuencia es que **no hace falta reactivar nada ni asignarle la tarea a nadie: hay que
restablecer el acceso a una carpeta.**

## Lo que exige decisión hoy

**1. Suspender la eliminación diaria de archivos.** Hoy la operación copia los archivos a la
carpeta de carga y **al día siguiente los elimina**. Como el proceso lleva doce días
fallando, cada día se está borrando trabajo de campo que nunca alcanzó a entrar al sistema.
No es una pérdida del pasado: **está ocurriendo ahora, y se detiene con una instrucción a la
operación.** No requiere ningún cambio técnico.

**2. Restablecer la carpeta de trabajo en el servidor de Modelo.** Es la reparación del
incidente y es de baja complejidad —del orden de media hora para quien administre ese
servidor—. No está dentro de nuestro alcance: requiere su gestión ante el área responsable.

## Lo que se puede recuperar, y hasta cuándo

Existe respaldo de los archivos, y el sistema acepta hoy información capturada hasta **120
días atrás**. Eso significa que **lo represado sí se puede recuperar**, con dos condiciones:
que primero se restablezca la carpeta, y que se haga pronto.

**La ventana se cierra sola.** Para las encuestas de mediados de julio el plazo vence
alrededor del **12 de octubre**. Cada semana que pasa, un tramo de lo acumulado deja de ser
recuperable por la vía normal.

Sobre el volumen: el canal sin conexión venía entregando unos pocos archivos por día, de
modo que no hablamos de una pérdida masiva. Pero cada archivo es una visita a campo —a menudo
en zonas de difícil acceso— que puede no repetirse.

## Lo que ya se hizo

- Se identificó la causa raíz con evidencia reproducible, mediante consultas de **solo
  lectura** sobre producción. No se modificó ningún dato, procedimiento ni proceso automático.
- Se documentó la cadena completa, sus puntos de falla y las medidas correctivas en el
  informe adjunto, que incluye las consultas para que cualquier tercero verifique el
  resultado sin depender de nuestra palabra.
- Se validó, en el mismo ejercicio, un segundo informe de calidad sobre la transferencia
  entre servidores: la medición era correcta, pero la causa señalada no se sostiene. El
  detalle está en el adjunto.

## Lo que proponemos a continuación

| # | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | Suspender la eliminación diaria de archivos | Operación | **Hoy** |
| 2 | Restablecer el acceso a la carpeta de trabajo | Administrador del servidor de Modelo | **Inmediato** |
| 3 | Verificar la corrida siguiente y confirmar el restablecimiento | Equipo técnico | Al día siguiente de (2) |
| 4 | Reprocesar el respaldo de lo represado | Equipo técnico | Antes de octubre |
| 5 | Monitoreo con alerta diaria sobre este proceso | Equipo técnico | Septiembre |

El punto 5 merece un comentario: **este proceso lleva doce días fallando y nadie se enteró**,
porque no existe ninguna alerta sobre él. La evidencia estuvo disponible desde la primera
noche. Una verificación diaria automática convierte doce días de pérdida en una hora, y es
una intervención menor.

Quedo atento a su instrucción sobre los puntos 1 y 2, que son los que hoy detienen la
pérdida.

Cordialmente,

**Javier Alexander Aguilar Castro**
Arquitectura y desarrollo — Sistema de Caracterización de Víctimas (SICAV / SRNI)
Contrato 2226-2026

---

## Notas para el remitente (no enviar)

**Por qué este correo no trae nombres técnicos.** El informe adjunto los tiene todos —el
nombre del proceso, el código de error, la ruta de la carpeta, el servidor—. El correo
deliberadamente no: quien decide los puntos 1 y 2 no necesita el detalle, necesita saber qué
instruir y con qué urgencia. Si en la respuesta piden precisión técnica, está en las páginas
1 a 6 del adjunto.

**Lo que este correo evita afirmar.** No dice cuántas encuestas se han perdido desde el 16 de
agosto, porque no se midió: eso exige contar los archivos que hay hoy en el FTP y los que se
eliminaron, y el registro de las eliminaciones no existe. Decir «se perdieron N» sin haberlo
contado es exactamente el tipo de afirmación que este informe corrige en otros.

**Si preguntan por responsabilidad.** El correo no atribuye culpa a nadie, y conviene
sostener eso. La eliminación diaria es una práctica establecida que funcionaba mientras el
proceso funcionaba; el reinicio de la base es una operación legítima. Lo que falló es que
**no había una alerta que uniera las dos cosas** — y eso es el punto 5, no una persona.

**Orden de envío sugerido.** Este correo va primero. Los otros dos que están listos —el del
tablero del GAVE y el de la pregunta del campesinado— pueden ir después, en correos
separados: son asuntos distintos y mezclarlos diluye la urgencia de los puntos 1 y 2.
