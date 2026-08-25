# Copiar-pegar al formato del supervisor — Informe Agosto 2026

> Este documento concentra las **2 secciones que pide el formato del supervisor**
> (Actividad desarrollada en este periodo + Evidencia que soporta esta actividad)
> para cada una de las 9 obligaciones. Listo para copiar y pegar directo en el
> formato oficial UARIV al cierre del mes.
>
> **Período:** 1 → 25 de agosto de 2026. *Actualizado: 25-ago-2026.*
>
> Todas las cifras están medidas contra el repositorio y las pruebas, no
> estimadas. Cuando algo está construido pero falta verificarlo en dispositivo o
> en producción, se dice explícitamente.

---

## Obligación 1 — Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Se atendieron **tres informes de aseguramiento de calidad (QA)** de la Unidad y se
corrigieron sus hallazgos. Del informe de la aplicación móvil (IGED-QA-C003 v2, 19
puntos evaluados), varios hallazgos resultaron tener una causa distinta de la
reportada, lo que exigió investigar en vez de parchar: el error "intermitente" al
conformar hogar (APK-002) no era intermitente ni de red, sino que el propio
servidor rechazaba el dato que él mismo enviaba —documentos repetidos daban error
500 y campos vacíos daban error 400—; y la barra de progreso en 0 % de sesiones
"Completadas" (APK-005) no era un defecto visual, sino que el cálculo dividía por
todas las preguntas obligatorias sin descontar las que las reglas del formulario
mantienen ocultas. Del informe del panel web (IGED-QA-C002 v2), el hallazgo
crítico (H-024) —una búsqueda que fallaba de forma intermitente— resultó ser una
consulta que recorría los 12 millones de registros del universo sin índice
(medido: 5,8 segundos), y se corrigió para que use el índice (2 milisegundos).
También se corrigió el listado de encuestas que mostraba "undefined" y "Página 1
de NaN" (H-010, H-011) y la fila que aparecía duplicada al buscar (H-025).

### Evidencia que soporta esta actividad

- Informes de QA: `docs/Informe_Seguimiento_Regresion_APK_v2.pdf` y
  `docs/Informe_Seguimiento_Regresion_WEB_v2.pdf`.
- Estado de cada hallazgo: `docs/pruebas/estado_hallazgos_qa_apk.md` y
  `docs/pruebas/plan_qa_v2_y_pendientes.md`.
- Commits en `main` (GitHub + Azure DevOps): `2397754` (APK-002, tres causas
  raíz), `3dfcd61`+`3fe431f`+`ff861c5` (APK-005), `cebefe9` (H-024, medición
  5,8 s → 2 ms), `d949ec2` (H-010/H-011/H-025), `e20085a` (H-027).
- Verificación técnica: **973 pruebas de backend y 140 de móvil en verde**,
  corridas el 25-ago; los arreglos se comprobaron por mutación (revertir el
  arreglo hace fallar la prueba).
- Detalle en `OE1-desarrollo/README.md`.

---

## Obligación 2 — Realizar la captura, el procesamiento, la transformación y la gestión de calidad de datos de las fuentes recibidas por la entidad

### Actividad desarrollada en este periodo

Se trabajó la calidad de los datos de identidad del padrón. Se clasificaron los
**768.096 documentos repetidos** del padrón, midiendo que el **92 % son la misma
persona** cargada más de una vez por el sistema de origen (no dos personas
distintas con el mismo número); con esa clasificación, el sistema deja de pedir
confirmación en el 100 % de esos casos y solo la pide en el ~7 % que de verdad lo
amerita. Sobre esa base, la búsqueda de autorizaciones dejó de mostrar una misma
persona repetida en pantalla (hallazgo H-025), colapsando los registros que son
la misma persona con el mismo criterio que la búsqueda de víctimas. También se
consolidó el estado **NO_VERIFICADO** para quien no aparece en el padrón
descargado —distinto de "no está en el registro de víctimas"—, para no negarle a
nadie su condición sin haberla comprobado.

### Evidencia que soporta esta actividad

- `docs/oracle-legacy-padron/decision_documentos_duplicados.md` (768.096
  repetidos, 92 % misma persona).
- Comando de clasificación: `apps/victimas/management/commands/clasificar_colisiones.py`.
- Colapso por identidad en autorizaciones: commit `d949ec2`.
- Estado NO_VERIFICADO: `docs/ciclo_completo_tablas.md` §6; migraciones
  `victimas/0008`, `victimas/0009`, `hogares/0007`.
- Detalle en `OE2-datos/README.md`.

---

## Obligación 3 — Procesar, implementar y documentar medidas de seguridad para proteger integridad, confiabilidad y confidencialidad de los datos

### Actividad desarrollada en este periodo

Se abordó el manejo de contraseñas de las cuentas de encuestador. El sistema
legado guarda las claves con un algoritmo antiguo (SHA-512 con una sal escondida
en la aplicación, imposible de recalcular y débil frente a ataques). Como ninguna
de las **1.158 encuestadoras** ha ingresado nunca al sistema nuevo, no hay nada
que preservar del esquema viejo; se construyó un comando que asigna las claves
nuevas guardándolas con **Argon2id**, el estándar actual de la industria. El
comando lee las claves desde un archivo, las valida, es reproducible sin efectos
duplicados y no deja las claves en texto plano. Adicionalmente, al revisar el
trabajo sin conexión se detectó y corrigió un defecto de protección de datos: un
envío fallido en la cola de sincronización impedía que, al cerrar sesión, se
borraran del teléfono los datos personales capturados.

### Evidencia que soporta esta actividad

- Comando: `srni-backend/apps/autenticacion/management/commands/cargar_claves.py`
  (commit `10bc0b9`), con **9 pruebas** en `test_cargar_claves.py`.
- Corrección del borrado de datos personales al cerrar sesión sin cola vacía:
  commit `2812ffc` (documentado en `docs/pruebas/estado_hallazgos_qa_apk.md` §8).
- La PII sigue cifrada en reposo y la búsqueda es por hash del documento (medida
  de julio, vigente).
- Detalle en `OE3-seguridad/README.md`.

---

## Obligación 4 — Realizar el diseño e implementación de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Se completó y verificó el flujo de **excepción de vigencia de punta a punta**: la
regla de recaracterizar solo cada dos años se mantiene, pero la autorización de
la excepción (por fallo, tutela o auto) dejó de pedirse en campo —donde el
encuestador no tiene el documento de soporte— y pasó a autorizarla la
coordinación desde el panel web; el celular solo consume esa autorización. Al
trazar el flujo completo se encontró y corrigió el último eslabón que faltaba:
con señal, autorizar no desbloqueaba la aplicación, y ahora sí lo hace **sin
necesidad de una versión nueva** (la que ya está en campo funciona). También se
habilitó **autorizar a quien está en el registro de víctimas pero aún no tiene
ficha en el padrón operativo**, creándole la ficha en el momento de autorizar. En
la aplicación móvil se consolidó la operación sin conexión (búsqueda contra un
filtro que reconoce a los 12,68 millones de personas del universo en 22,7 MB) y
la cola de sincronización que sube el trabajo cuando vuelve la señal.

### Evidencia que soporta esta actividad

- Excepción de vigencia extremo a extremo: commits `2ecf39c`, `63ee8ba` (mover la
  autorización al panel, 14-ago) y `c23c781` (desbloqueo en línea, 25-ago), con
  **prueba de punta a punta** `tests/test_e2e_excepcion_vigencia.py`.
- Autorizar a quien solo está en el universo: commits `f1a2522`, `0e0399a`;
  verificado contra producción (respuesta correcta, origen UNIVERSO).
- Trabajo sin conexión y sincronización: `docs/` y commits `d34fa01` (filtro
  Bloom), `ddc1c77`, `2812ffc`, `421ce61`; documento técnico de la capacidad en
  `entregables/2026-08-21-offline-sync-ia/`.
- Detalle en `OE4-arquitectura/README.md`.

---

## Obligación 5 — Estructurar, diseñar y documentar las bases de datos requeridas

### Actividad desarrollada en este periodo

Quedaron cargados y en operación los dos conjuntos de datos que sostienen la
búsqueda: el **padrón operativo (5.936.769 víctimas incluidas)** y el **universo
del registro de víctimas (~12,5 millones)**, este último como fuente de
existencia —antes, quien nunca había sido entrevistado era invisible para el
sistema aunque estuviera en el registro—. Se blindó el cruce entre ambos: se midió
que los identificadores internos de los dos sistemas no coinciden (de 243.610
pares con el mismo documento, cero coinciden por identificador), por lo que el
enlace se hace siempre por el número de documento y nunca por el identificador
interno. La escritura de las caracterizaciones nuevas hacia la base de la entidad
(Oracle) se hace exclusivamente por los procedimientos oficiales, verificando
cada escritura con una consulta posterior.

### Evidencia que soporta esta actividad

- `docs/arquitectura/adr-padron-universo-victimas.md` (decisión aprobada 5-ago,
  cifras del universo: 12.496.965 filas del corte).
- `docs/oracle-legacy-padron/hallazgos_identidad_padron.md` (5.936.769 incluidas;
  1.884.872 —24,1 %— sin identidad en el servidor de la entidad).
- Cruce por documento: `docs/ciclo_completo_tablas.md`; comando
  `cargar_universo_victimas.py`.
- Escritura a Oracle por procedimientos `GIC_*` con verificación posterior:
  `docs/ciclo_completo_tablas.md` §3.
- Detalle en `OE5-bd/README.md`.

---

## Obligación 6 — Diseñar, documentar y mantener los modelos de datos

### Actividad desarrollada en este periodo

Se unificó el **motor de reglas del formulario (skip-logic)** en un solo lugar
del sistema, de modo que la aplicación móvil, el tablero del celular y el servidor
decidan exactamente igual qué preguntas se muestran y cuáles son obligatorias para
una misma persona. Antes cada parte tenía su propia copia y habían empezado a
divergir. Sobre esa base se corrigió el cálculo del porcentaje de avance de una
entrevista, que ahora cuenta solo las preguntas obligatorias **visibles**
—evaluando las reglas con los datos reales de cada integrante (edad, sexo,
pertenencia étnica, condición en el registro)— y no las que quedan ocultas y nadie
puede responder.

### Evidencia que soporta esta actividad

- Motor unificado: `srni-backend/apps/formulario/skiplogic.py`.
- Cálculo del porcentaje por obligatorias visibles con contexto: commits
  `3dfcd61`, `3fe431f`, `ff861c5`; **35 pruebas de backend + 6 de móvil**,
  verificadas por mutación.
- Detalle en `OE6-modelos/README.md`.

---

## Obligación 7 — Participar en las reuniones y actividades de coordinación con la supervisión

### Actividad desarrollada en este periodo

Se sostuvo la coordinación con la supervisión y con el equipo. Se recibieron y
procesaron los tres informes de calidad, se acordó el criterio de respuesta y se
priorizaron las correcciones por riesgo operativo. Se tomaron —por delegación de
la supervisión— las decisiones de negocio pendientes que el trabajo iba
requiriendo, entre ellas el rediseño de quién autoriza la excepción de vigencia
(coordinación en el nivel central, no el encuestador en campo) y el criterio para
registrar a quien no está en el padrón descargado. Quedaron señaladas las
decisiones que todavía requieren definición de la Unidad.

### Evidencia que soporta esta actividad

- Decisiones de negocio: `docs/gestion/decisiones_negocio_pendientes.md`.
- Contrato del flujo de excepción para el panel:
  `docs/operacion/excepcion_vigencia_desde_el_front.md`.
- Presentaciones de avance para la supervisión (ver Obligación 8).
- Detalle en `OE7-reuniones/README.md`.

---

## Obligación 8 — Elaborar y cargar mensualmente los informes y documentos requeridos

### Actividad desarrollada en este periodo

Se produjeron los documentos de avance del período: dos presentaciones de avance
para la supervisión (corte 13-ago y corte 21-ago), un documento técnico sobre las
capacidades de operación sin conexión, sincronización e inteligencia artificial,
y el plan de respuesta a los informes de QA. Este informe mensual consolida el
trabajo de agosto con evidencia física por cada obligación, en la misma
estructura de julio.

### Evidencia que soporta esta actividad

- Presentaciones: `entregables/2026-08-13/` y `entregables/2026-08-21/` (fuentes
  versionadas; el .pptx y el .pdf se regeneran).
- Documento de capacidades: `entregables/2026-08-21-offline-sync-ia/`.
- Plan de QA: `docs/pruebas/plan_qa_v2_y_pendientes.md`.
- Evidencia del mes: `OE8-informes/evidencias/` (commits, autores, líneas).
- Detalle en `OE8-informes/README.md`.

---

## Obligación 9 — Las demás actividades asignadas relacionadas con el objeto del contrato

### Actividad desarrollada en este periodo

Se analizó el formato en que el sistema legado almacena las contraseñas para
decidir cómo migrar las credenciales de las encuestadoras (obligación 3), y se
construyó la herramienta correspondiente. Se documentó y dejó trazada, como
prueba automatizada reproducible, la verificación de punta a punta del flujo de
excepción de vigencia. Se dejó registrado, para el trabajo futuro de mejora de la
base de datos, el aviso de la Unidad sobre una tabla e índice creados en el
esquema del universo (fuera del alcance de este mes, anotado para no perderlo).

### Evidencia que soporta esta actividad

- Prueba de punta a punta: `srni-backend/tests/test_e2e_excepcion_vigencia.py`.
- Análisis del formato de claves legado y decisión: `OE3-seguridad/README.md`.
- Registro del pendiente de base de datos: `OE5-bd/README.md`.
- Detalle en `OE9-adicionales/README.md`.

---

*Repositorios: Azure DevOps (oficial UARIV) y GitHub (respaldo). Corte del
informe: 25 de agosto de 2026, commit `c23c781`.*
