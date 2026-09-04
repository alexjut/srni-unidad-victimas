# Presentación de avance — 4 de septiembre de 2026

Diapositivas para presentar el avance del proyecto **PRY-0662064 · SICAV Móvil**
del periodo **28-ago → 4-sep-2026**: la semana en que la capacitación dejó de ser
un acto que se dicta y pasó a ser algo que se mide, y en la que cuatro de las
cinco dificultades aparecieron al revisar nuestro propio trabajo.

## Contenido

| Archivo | Qué es |
|---|---|
| `pptx/presentacion_avance_28ago-4sep.pptx` | **La presentación editable en PowerPoint.** 15 diapositivas en 16:9. Es la que se usa para exponer. |
| `pdf/presentacion_avance_28ago-4sep.pdf` | Las 15 diapositivas, una por página. Para repartir o proyectar sin PowerPoint. |
| `fuente/presentacion_avance_28ago-4sep.html` | La misma presentación como página web navegable (flechas, barra espaciadora; `#9` salta a la diapositiva 9). |
| `fuente/generar_pptx.py` | El generador del `.pptx`. |

Se versiona la fuente (HTML y script), no los binarios: se regeneran (ver abajo).

## Las 15 diapositivas

```
01  Portada
02  El periodo en cifras
03  ── Sección 01: Avances
04  El pre-test y el post-test        → medir la jornada, no solo dictarla
05  La auditoría del estado real      → 1.185 pruebas, permisos automatizados
06  Lo que quedó publicado            → app, manual, pre-test y post-test
07  ── Sección 02: Dificultades y soluciones
08  El cuestionario no medía nada: bastaba marcar «todo B»
09  El manual existía y no estaba publicado en ninguna parte
10  La dirección de descarga dependía de quién preguntara
11  El proceso de carga: veinte noches seguidas sin operar
12  Seis correos del equipo son de desarrollo, y el test identifica por correo
13  Verificación
14  Lo que sigue: los tres martes y las dos urgencias que no son nuestras
15  Cierre y equipo
```

La estructura sigue lo pedido: **avance / dificultad / solución**. Cada dificultad
y su solución van en la misma diapositiva, a dos columnas, para que el auditorio no
tenga que recordar el problema tres diapositivas después.

## De dónde salen las cifras

Todo lo que se afirma se midió en el periodo. Nada es estimación:

| Cifra | Origen |
|---|---|
| 1.185 pruebas en verde (1.037 backend + 148 móvil) | Batería completa corrida el 1-sep · `docs/gestion/estado-global-2026-09-01.md` |
| 976 → 1.037 pruebas del backend | Las 61 comprobaciones nuevas de la matriz de permisos |
| 61 comprobaciones · 5 perfiles · 10 endpoints | `srni-backend/apps/autenticacion/tests/test_matriz_permisos.py` |
| 3 cuentas autorizadoras para 1.157 encuestadores | Medido en producción · `docs/gestion/decisiones_negocio_pendientes.md` §6 |
| 15 preguntas · clave 3 A / 4 B / 4 C / 4 D | `cargar_prueba_capacitacion.py`, y comparadas contra lo que sirve el servidor |
| 11 de 15 correctas eran B (versión anterior) | El defecto que corrigió el commit `956268c` |
| 14 cambios versionados | `git log` del periodo (29-ago → 4-sep) |
| Última carga exitosa del FTP: **14-ago** · 20 noches fallidas | `ALL_SCHEDULER_JOB_RUN_DETAILS`, consultado el **4-sep** |
| 4 direcciones publicadas | Verificadas contra el dominio institucional tras el despliegue del 3-sep |

> **La cifra del proceso de carga se volvió a medir el día de la presentación**, no se
> heredó del informe anterior. El informe del 27-ago hablaba de once días; hoy son
> veinte noches y la última carga buena sigue siendo la del 14 de agosto.

## Lo que esta presentación **no** afirma

- **No dice por qué se corrió el calendario** de la capacitación a los martes 8, 15 y 22.
  Presenta las fechas nuevas como confirmadas y nada más. Si la PMO pregunta el motivo,
  hay que agregarlo.
- **No reporta las pruebas del panel web.** No se pudieron correr desde nuestro entorno
  (`node_modules` vacío). Se declara como comprobación no realizada, no como fallo.

## Regenerar

Desde la carpeta del entregable, con Google Chrome instalado:

```bash
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
BASE="file:///D:/desarrollo/unidad-victima/entregables/2026-09-04/fuente"

"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=25000 \
  --print-to-pdf="pdf/presentacion_avance_28ago-4sep.pdf" \
  "$BASE/presentacion_avance_28ago-4sep.html"

python fuente/generar_pptx.py
```

> `--virtual-time-budget` es necesario: sin él Chrome imprime antes de que la
> página termine de componerse.
