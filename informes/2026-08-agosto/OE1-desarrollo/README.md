# OE1 — Desarrollo, mantenimiento, documentación y soporte

> **Obligación contractual:** *Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante agosto se atendieron **tres informes de aseguramiento de calidad (QA)** de
la Unidad y se corrigieron sus hallazgos. Lo característico del mes fue que varios
defectos **no eran lo que el informe reportaba**, y corregirlos exigió encontrar la
causa real en lugar de tapar el síntoma.

**Informe de la aplicación móvil (IGED-QA-C003 v2).**

- **APK-002 — "error intermitente al conformar hogar".** No era intermitente ni de
  red. El propio servidor rechazaba lo que él mismo enviaba: al registrar una
  persona desde el RUV, un documento repetido producía error 500 y un documento sin
  tipo producía error 400. Se corrigieron **tres causas raíz**: se dejó de asumir
  un único registro por documento (se colapsan los que son la misma persona; si son
  personas distintas se responde 409, no 500), se aceptó el tipo de documento vacío
  con búsqueda por hash del número, y se normalizaron género y estado en el RUV.
- **APK-005 — "barra de progreso en 0 % en sesiones Completadas".** No era un
  defecto visual: el cálculo dividía por **todas** las preguntas obligatorias, sin
  descontar las que las reglas del formulario mantienen ocultas para esa persona.
  Se corrigió para contar solo las obligatorias **visibles** (ver OE6).
- Se cerró además el borrado de datos personales al cerrar sesión cuando la cola de
  sincronización tenía un envío fallido (ver OE3).

**Informe del panel web (IGED-QA-C002 v2).**

- **H-024 (crítico) — búsqueda que fallaba "de forma intermitente".** Era una
  consulta que recorría los **12 millones** de registros del universo sin índice
  (medido en producción: **5,8 s**); se corrigió para usar el índice existente
  (**~2 ms**) y para no traer la misma persona repetida.
- **H-010 / H-011 — "undefined" y "Página 1 de NaN"** en el listado de encuestas:
  el panel esperaba paginación por número de página y el backend entregaba otra; se
  unificó a paginación por número de página.
- **H-025** — una misma persona aparecía repetida al buscar en autorizaciones: se
  colapsó por identidad con el mismo criterio de la búsqueda de víctimas.
- **H-027** — ajuste de consistencia asociado al mismo listado.

## Evidencia que soporta esta actividad

- Informes de QA: `docs/Informe_Seguimiento_Regresion_APK_v2.pdf`,
  `docs/Informe_Seguimiento_Regresion_WEB_v2.pdf`.
- Estado hallazgo por hallazgo: `docs/pruebas/estado_hallazgos_qa_apk.md`,
  `docs/pruebas/plan_qa_v2_y_pendientes.md`.
- Commits en `main` (GitHub + Azure DevOps): `2397754` (APK-002),
  `3dfcd61`+`3fe431f`+`ff861c5` (APK-005), `cebefe9` (H-024), `d949ec2`
  (H-010/H-011/H-025), `e20085a` (H-027).
- Verificación: **973 pruebas de backend** en verde (+1 xfail) y **140 de móvil**,
  corridas el 25-ago; cada arreglo se comprobó **por mutación** (revertir el arreglo
  hace fallar la prueba).

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `suite-backend-agosto.txt` | Salida real de la suite completa de backend (pytest) |
| `commits-qa-agosto.txt` | Commits de respuesta a los informes de QA, del histórico del repositorio |

## Pendiente / siguiente paso

- **Build nueva del APK y reprueba de QA en dispositivo** para dar por cerrados los
  hallazgos de la aplicación móvil (hoy corregidos en código con pruebas).
- Recalcular (backfill) el porcentaje de las sesiones ya guardadas antes del próximo
  reporte.
- Alinear el endpoint de versión (responde 1.0.0 en producción; la app va en 1.2.2).
