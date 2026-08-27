# Respuesta — Actualización del tablero Power BI del GAVE (jornada Panamá)

**Estado:** listo para enviar
**Para:** Maria Elena Silva Fandiño — Subdirectora (E), Subdirección Red Nacional de Información
**Asunto:** RE: Actualización tablero GAVE — información cargada, causa raíz identificada y medida correctiva
**Fecha:** 27 de agosto de 2026

> Todas las cifras se midieron hoy contra la base de producción. El anexo indica cómo
> verificar cada una.

---

Respetada Subdirectora, buenas tardes.

En atención a su solicitud sobre el tablero del GAVE, presento el resultado de la revisión
técnica, la causa raíz identificada y la medida correctiva aplicada.

## 1. La información de la jornada de Panamá está cargada

**La información nunca se perdió ni se capturó fuera de tiempo.** Los registros de la
jornada del 14 al 16 de julio están en la tabla que alimenta el tablero, y **fueron cerrados
el mismo día de su captura**:

| Fecha | Hogares | Registros | Encuestadores | Cierre |
|---|---:|---:|---:|---|
| 14 de julio | 1 | 3 | 1 | mismo día, 11:10 |
| 15 de julio | 28 | 56 | 4 | mismo día, entre 09:12 y 19:16 |
| 16 de julio | 22 | 37 | 6 | mismo día, entre 09:18 y 18:07 |
| **Total** | **51** | **96** | | |

No hubo demora entre la captura y el cierre: cada caracterización quedó cerrada minutos
después de levantarse, el mismo día. La información estuvo disponible en la base desde la
jornada misma.

## 2. Qué sí falló: la reconstrucción del reporte

El tablero no consulta directamente las tablas de caracterización. Se alimenta de una tabla
de reporte, `INH_REPORTE_GAVE`, que **no se actualiza sola**: la construye un procedimiento
(`PRC_REP_GAVE`) que borra y rehace la tabla completa cada vez que se ejecuta.

**Ese procedimiento no tiene ningún trabajo programado que lo ejecute.** Se verificó hoy: no
existe job alguno asociado al reporte GAVE en el servidor. Su ejecución es manual.

Esa es la causa raíz: **un paso manual, sin automatización, sin responsable asignado y sin
documentación**. Mientras nadie lo ejecutara, la tabla de reporte —y por lo tanto el
tablero— seguía mostrando el último corte, aunque la información de campo estuviera
completa en la base desde julio.

No se automatizó en su momento porque no se contaba con documentación del proceso: no había
registro de qué procedimiento construía el reporte, con qué periodicidad debía ejecutarse ni
quién era su responsable. Establecerlo requirió un trabajo de reconstrucción sobre el código
del sistema heredado.

## 3. Qué se hizo

Identificado el mecanismo, **el reporte fue reconstruido hoy 27 de agosto a las 8:54 a. m.**
La tabla quedó con 2.141 registros y con información hasta el 26 de agosto, incluida la
jornada de Panamá. El procedimiento fue además intervenido el 16 de agosto por los ingenieros
Daniel y Fabio como parte de la solución.

**Con esto la fuente del tablero queda actualizada dentro del plazo del 31 de agosto que
usted señala.**

Si al consultar el tablero la información aún no se refleja, el punto pendiente ya no está en
la base de datos sino en el **refresco del conjunto de datos en Power BI**, que depende de la
programación del servicio y de las credenciales del origen. Agradezco confirmar quién
administra ese refresco para cerrar el ciclo completo.

## 4. Medida para que no vuelva a ocurrir

La reconstrucción manual seguirá produciendo el mismo desfase cada vez que nadie la ejecute.
Se proponen tres acciones:

| # | Acción | Responsable |
|---|---|---|
| 1 | **Programar la ejecución automática** de `PRC_REP_GAVE` con periodicidad definida (se sugiere diaria, en la ventana nocturna) | Equipo técnico, previa autorización |
| 2 | **Definir y programar el refresco del conjunto de datos** en Power BI, alineado con la ejecución anterior | Administrador del tablero |
| 3 | **Monitoreo con alerta**: verificación diaria de que el reporte se reconstruyó, con aviso cuando no ocurra | Equipo técnico |

Sin la acción 1, cualquier corte futuro vuelve a depender de que alguien recuerde ejecutarlo
manualmente. Es una intervención de baja complejidad y requiere únicamente la autorización
para programar el trabajo en el servidor.

## 5. Nota sobre un frente distinto

En paralelo se adelanta una auditoría técnica más amplia sobre la cadena de carga de las
encuestas capturadas **sin conexión** (caso 14512), en la que se identificó hoy la causa raíz
de una interrupción distinta. **Ese hallazgo no afecta a la jornada de Panamá**: los 51
hogares se capturaron y cerraron en línea el mismo día, sin pasar por esa ruta. Se menciona
para evitar que ambos asuntos se confundan. El informe correspondiente se remite por
separado.

Quedo atento a su confirmación sobre la autorización de la acción 1 y sobre el responsable
del refresco en Power BI.

Cordialmente,

**Javier Alexander Aguilar Castro**
Arquitectura y desarrollo — Sistema de Caracterización de Víctimas (SICAV / SRNI)
Contrato 2226-2026

---

## Anexo para uso interno — verificación de las cifras

Consultas de solo lectura, ejecutadas el 27 de agosto de 2026 desde
`RNIENTREVISTA@30.0.1.9/ENTREVISTARN` hacia el servidor MODELO por el dblink
`CONSULTAMODELO110`.

| Afirmación | Cómo se verifica |
|---|---|
| 51 hogares y 96 registros del 14 al 16 de julio | `SELECT TO_CHAR(fecha_creacion,'YYYY-MM-DD'), COUNT(*), COUNT(DISTINCT hog_codigo) FROM rnientrevista.inh_reporte_gave@consultamodelo110 WHERE fecha_creacion >= DATE '2026-07-14' AND fecha_creacion < DATE '2026-07-17' GROUP BY 1` |
| Cierre el mismo día de la captura | Comparar `fecha_creacion` y `fecha_cierre` en esas mismas filas |
| Encuestadores de la jornada | `USUARIO_CREACION`: SMOLIVARESH, JCREYESV, DLVIVASL, NMCASTIBLANCOG, LVORTIZB, APMARQUEZA, NAMUÑOZAG |
| 2.141 registros, hasta el 26 de agosto | `SELECT COUNT(*), MAX(fecha_creacion), MAX(fecha_cierre) FROM rnientrevista.inh_reporte_gave@consultamodelo110` |
| Reconstrucción del reporte hoy 8:54 a. m. | `LAST_DDL_TIME` de la tabla `INH_REPORTE_GAVE` en `ALL_OBJECTS` — se actualiza al borrarse la tabla, que es lo que hace el procedimiento |
| Intervención del procedimiento el 16 de agosto | `LAST_DDL_TIME` de `PRC_REP_GAVE` = 2026-08-16 17:59 |
| **No existe job programado** | `SELECT * FROM all_scheduler_jobs@consultamodelo110 WHERE UPPER(job_name) LIKE '%GAVE%' OR UPPER(job_action) LIKE '%GAVE%'` → sin filas |
| El procedimiento reconstruye la tabla completa | `ALL_SOURCE` de `PRC_REP_GAVE`: contiene el subprograma `ProBorra_tbl`, que vacía la tabla antes de repoblarla |

**Precisión importante.** La afirmación del numeral 5 —que Panamá no pasó por la ruta
offline— se sustenta en que las 96 filas tienen `fecha_cierre` el mismo día de la
`fecha_creacion`, con diferencias de minutos. La ruta sin conexión, por diseño, introduce un
desfase de al menos un día entre captura y llegada a la base. **No debe presentarse el caso
14512 como causa de este asunto.**

**Punto abierto para la mesa técnica.** El perfil de Víctimas en el Exterior —bajo el cual
opera el GAVE— tiene hoy 362 opciones de respuesta sin identificador de correspondencia con
VIVANTO (`id_resp_vivanto`), es decir, sin ruta de migración definida hacia los sistemas
masivos de la entidad. No afecta al tablero, que se alimenta de la tabla de reporte, pero es
relevante para cualquier cruce posterior con RUV o VIVANTO.
