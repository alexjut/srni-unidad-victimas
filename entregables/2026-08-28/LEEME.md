# Presentación de avance — 28 de agosto de 2026

Diapositivas para presentar el avance del proyecto **PRY-0662064 · SICAV Móvil**
del periodo **21-ago → 28-ago-2026**: la semana en que llegaron tres
reclamaciones por correo y las tres resultaron tener una causa distinta de la
que se les atribuía.

## Contenido

| Archivo | Qué es |
|---|---|
| `pptx/presentacion_avance_21-28-ago.pptx` | **La presentación editable en PowerPoint.** 15 diapositivas en 16:9. Es la que se usa para exponer. |
| `pdf/presentacion_avance_21-28-ago.pdf` | Las 15 diapositivas en A4 apaisado, una por página. Para repartir o proyectar sin PowerPoint. |
| `fuente/presentacion_avance_21-28-ago.html` | La misma presentación como página web navegable (flechas, barra espaciadora; `#9` salta a la diapositiva 9). |
| `fuente/generar_pptx.py` | El generador del .pptx. |

Se versiona la fuente (HTML y script), no los binarios: se regeneran (ver abajo).

## Las 15 diapositivas

```
01  Portada
02  El periodo en cifras
03  ── Sección 01: Avances
04  Los informes de calidad v2       → los doce hallazgos, cerrados
05  El plan de capacitación          → completo, con sus ocho anexos
06  Lo que quedó corriendo           → APK 1.2.3, panel, autorizaciones
07  ── Sección 02: Dificultades y soluciones
08  Caso 14512 · El proceso no estaba apagado: estaba en el otro servidor
09  Caso 14512 · Cada día se borra la captura de ese día
10  Segundo informe · La medición era correcta; la causa, no
11  Tablero GAVE · La información sí estaba
12  La pregunta que llegó con un día de plazo
13  Verificación
14  Lo que sigue y las decisiones que necesitamos
15  Cierre y equipo
```

La estructura sigue lo pedido: **avance / problema / solución**. Las dificultades
y su solución van en la misma diapositiva, a dos columnas, para que el auditorio
no tenga que recordar el problema tres diapositivas después.

## De dónde salen las cifras

Todo lo que se afirma en las diapositivas se midió, no se estimó:

| Cifra | Origen |
|---|---|
| 12 / 12 hallazgos cerrados | `docs/pruebas/respuesta_qa_v2.md` — 7 APK + 5 del panel |
| 25 cambios versionados | `git log` del periodo |
| 51 hogares de la jornada de Panamá | `INH_REPORTE_GAVE`, consultado por dblink |
| 88 archivos / 31 perdidos / 11 vs 77 | validación del segundo informe externo |
| 1.959 preguntas · 1.043 reglas | recuento sobre las nueve parametrizaciones vigentes |
| 19 días-persona | estimación desglosada por actividad, no un total lanzado |
| Ventanas de 120 y 90 días | código vigente en producción, leído el 27-ago |

Los tres informes que sustentan la sección 02 están en el repositorio:
`entregables/2026-08-27-caso-14512/`, `docs/gestion/correo_tablero_gave_panama.md`
y `docs/gestion/correo_inclusion_pregunta_campesinado.md`.

## Regenerar

Desde la carpeta del entregable, con Google Chrome instalado:

```bash
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
BASE="file:///D:/desarrollo/unidad-victima/entregables/2026-08-28/fuente"

"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=25000 \
  --print-to-pdf="pdf/presentacion_avance_21-28-ago.pdf" \
  "$BASE/presentacion_avance_21-28-ago.html"

python fuente/generar_pptx.py
```

> `--virtual-time-budget` es necesario: sin él Chrome imprime antes de que la
> página termine de componerse.
