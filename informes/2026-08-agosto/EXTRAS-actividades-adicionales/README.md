# EXTRAS — Actividades adicionales por fuera del cronograma

> Trabajo ejecutado durante **Agosto 2026** que **no estaba listado** en las 9
> obligaciones específicas (OE1-OE9) del cronograma del contrato 2226-2026, pero que
> se realizó como apoyo al objeto del contrato.

## Actividad desarrollada en este periodo

### 1. Consolidación de tres rondas de aseguramiento de calidad en un mes

El cronograma no preveía **tres informes de QA** en un mismo período. Atenderlos
—móvil v1, móvil v2 (IGED-QA-C003) y web v2 (IGED-QA-C002)— implicó no solo corregir,
sino **reinvestigar hallazgos mal atribuidos**: lo reportado como "intermitente" o
"visual" resultó ser, en varios casos, un rechazo del propio servidor (APK-002), un
cálculo sobre el modelo equivocado (APK-005) o una consulta sin índice sobre 12
millones de filas (H-024). Ese trabajo de causa raíz, más costoso que un parche, es
lo que evita que los mismos defectos vuelvan en la siguiente ronda.

### 2. Seguimiento de la escritura hacia la base en operación

Tras el piloto de fin de julio (primera caracterización de SICAV registrada en la
base real de la entidad), en agosto se mantuvo **bajo seguimiento** la ruta de
escritura por procedimientos oficiales `GIC_*`, con verificación por consulta
posterior y con la escritura automática continua **apagada por defecto** de forma
deliberada, a la espera de la autorización de la Unidad para encenderla. Se cuidó de
**no tocar la base durante la migración**, dejando el registro de defectos del legado
para atender después.

### 3. Materialización de fichas desde el universo

No estaba en el cronograma que el panel tuviera que **crear una ficha en el momento
de autorizar** a una persona que solo existe en el universo del registro (12,5 M) y
no en el padrón operativo (5,9 M). Fue necesario construirlo para que la coordinación
pudiera autorizar recaracterizaciones de personas nunca antes entrevistadas, y quedó
verificado contra producción.

## Evidencia que soporta esta actividad

- Estado de los tres informes de QA: `docs/pruebas/estado_hallazgos_qa_apk.md`,
  `docs/pruebas/plan_qa_v2_y_pendientes.md`.
- Escritura a Oracle por procedimientos `GIC_*`: `docs/ciclo_completo_tablas.md`.
- Materialización desde el universo: commits `f1a2522`, `0e0399a`, `cebefe9`
  (detalle en [`../OE4-arquitectura/README.md`](../OE4-arquitectura/README.md)).

## Pendiente / siguiente paso

- Cerrar los hallazgos de QA con build nueva y reprueba en dispositivo.
- Decidir con la Unidad el encendido de la escritura automática a Oracle.
