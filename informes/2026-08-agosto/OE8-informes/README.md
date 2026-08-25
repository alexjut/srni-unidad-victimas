# OE8 — Carga mensual de documentos

> **Obligación contractual:** *Cargar mensualmente en la ruta dispuesta por la Subdirección todos los documentos que den cuenta de la gestión realizada en el contrato.*

## Actividad desarrollada en este periodo

Se produjeron los documentos de avance del período y se consolidó este informe
mensual con evidencia física por cada obligación, en la misma estructura de julio:

- **Dos presentaciones de avance** para la supervisión (corte 13-ago y corte
  21-ago).
- **Documento técnico** sobre las capacidades de operación sin conexión,
  sincronización e inteligencia artificial de la aplicación móvil.
- **Plan de respuesta a los informes de QA**, con el estado hallazgo por hallazgo.
- **Este informe mensual** (carpeta `informes/2026-08-agosto/`), con el documento de
  copiar-pegar al formato del supervisor y una carpeta por obligación.

## Cifras del mes (medidas)

| | | Comando / fuente |
|---|---:|---|
| Commits de agosto | **142** | `git log --since=2026-08-01 --until=2026-08-26` |
| — Javier / — Brando | 131 / 11 | `git log --pretty=%an \| sort \| uniq -c` |
| Líneas | **+44.081 / −868** (287 archivos) | `git diff --shortstat 686d0ad..HEAD` |
| Pruebas backend | **973 passed, 1 xfailed** | `pytest -q` (25-ago) |
| Pruebas móvil | **140 passed** | `npm test` |

## Evidencia que soporta esta actividad

- Presentaciones: `entregables/2026-08-13/` y `entregables/2026-08-21/`.
- Documento de capacidades: `entregables/2026-08-21-offline-sync-ia/`.
- Plan de QA: `docs/pruebas/plan_qa_v2_y_pendientes.md`.
- Este informe: `informes/2026-08-agosto/`.

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/) — **evidencia transversal de todo el mes**:

| Archivo | Qué prueba |
|---|---|
| `commits-agosto.txt` | Histórico completo de commits del mes (fecha, autor, mensaje) |
| `commits-por-autor.txt` | Reparto de commits por autor (131 Javier / 11 Brando) |
| `lineas-cambiadas.txt` | Volumen del mes: archivos tocados y líneas +/− |

## Pendiente / siguiente paso

- Cargar este informe en la ruta dispuesta por la Subdirección al cierre del mes.
- Regenerar los `.pdf`/`.pptx` de las presentaciones desde sus fuentes versionadas si
  la supervisión los pide en ese formato.
