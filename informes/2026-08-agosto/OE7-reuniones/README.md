# OE7 — Reuniones y coordinación con supervisor

> **Obligación contractual:** *Asistir a las reuniones programadas para tratar temas relacionados con el desarrollo del objeto del contrato y las demás que sean requeridas por el supervisor.*

## Actividad desarrollada en este periodo

Se sostuvo la coordinación con la supervisión y con el equipo de trabajo a lo largo
del mes:

- **Atención a los informes de calidad.** Se recibieron los **tres informes de QA**
  del período (móvil v1, móvil v2 y web v2), se acordó el criterio de respuesta y se
  **priorizaron las correcciones por riesgo operativo**, empezando por el hallazgo
  crítico del panel (H-024) y por el que rompía la conformación de hogar en campo
  (APK-002).
- **Decisiones de negocio delegadas.** La supervisión delegó en el contratista las
  decisiones de negocio que el trabajo iba requiriendo. En agosto se resolvieron,
  entre otras: **quién autoriza la excepción de vigencia** (la coordinación en el
  nivel central desde el panel, no el encuestador en campo) y el **criterio para
  registrar a quien no está en el padrón descargado** (mostrarlo y crearle la ficha
  al autorizar, con estado *INCLUIDO*). Quedaron señaladas las decisiones que aún
  requieren definición de la Unidad.
- **Coordinación con el frontend.** Se acordó con Brando el reparto de tareas del
  panel web (badge de estado *Sin verificar*, indicador de carga, y presentación de
  las filas de origen UNIVERSO), dejándolas listadas para su ejecución.

## Evidencia que soporta esta actividad

- Registro de decisiones de negocio: `docs/gestion/decisiones_negocio_pendientes.md`.
- Contrato del flujo de excepción para el panel (acuerdo con frontend):
  `docs/operacion/excepcion_vigencia_desde_el_front.md`.
- Plan de respuesta a QA acordado: `docs/pruebas/plan_qa_v2_y_pendientes.md`.
- Presentaciones de avance para la supervisión (ver OE8).

## Evidencia física recolectada

La evidencia de coordinación queda soportada por los documentos de gestión y las
presentaciones de avance referidos arriba y en [`OE8-informes/`](../OE8-informes/README.md).

## Pendiente / siguiente paso

- Llevar a la Unidad las decisiones que exceden la delegación (excepción para quien
  no está en el padrón; encendido de la escritura automática a Oracle).
- Reunión de seguimiento PETI (PRY-0662064) según cronograma.
