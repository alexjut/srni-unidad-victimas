# EXTRAS — Actividades adicionales por fuera del cronograma

> Trabajo ejecutado durante **Julio 2026** que **no estaba listado** en las 9 obligaciones
> específicas (OE1-OE9) del cronograma del contrato 2226-2026, pero que se realizó
> como apoyo al objeto del contrato.

## Actividad desarrollada en este periodo

Dos frentes que no estaban en el cronograma y que resultaron ser lo más
significativo del mes.

### 1. Ruta de escritura hacia la base actual (RNIENTREVISTA)

El cronograma preveía construir SICAV, no conectarlo con el sistema en operación.
Durante julio se construyó y validó esa ruta, en tres escalones:

- **Escalón 1** — primera escritura completa de una caracterización usando los
  **procedimientos oficiales `GIC_*`** (nunca `INSERT` directo a tablas), validada
  de extremo a extremo contra una réplica local.
- **Escalón 2** — ruta geográfica verificada y guarda de destino, para que sea
  imposible escribir en la base equivocada por descuido.
- **Piloto en producción (28 de julio)** — primera caracterización de SICAV
  registrada en la base real de la entidad, identificable y verificada por consulta
  posterior.

El trabajo incluyó auditar la calidad de la base de destino, con un registro de
defectos encontrados para atender **después** de la migración: durante la migración
no se toca la base.

### 2. Carga del padrón real de víctimas

Se pasó de un padrón de prueba (11 casos ficticios) a **5.926.004 víctimas reales**
cargadas desde la fuente de la entidad, con la homologación de cada campo medida
contra los datos —no supuesta— y con la clasificación de los 768.096 documentos
compartidos por más de una persona.

El rendimiento de la carga se trabajó como problema propio: de una primera versión
estimada en **42 horas** se llegó a **~25 minutos**, y la aplicación de fechas de
caracterización pasó de 25 horas a minutos al reemplazar la escritura fila a fila
por una carga masiva.

## Evidencia que soporta esta actividad

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `implementacion_capacitacion_despliegue.md` | Plan y ejecución de implementación, capacitación y despliegue |
| `cierre-julio-2026.md` | Cierre del mes con el detalle de lo ejecutado y su estado |

*(La evidencia técnica de estos dos frentes está repartida en `OE2-datos/` —calidad
del padrón— y `OE4-arquitectura/` —planes de los escalones y movimientos en la base
de la entidad—.)*

## Pendiente / siguiente paso

- Respaldo de las tablas del legado y comando de reversión, previos al piloto
  general de escritura.
