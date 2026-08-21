# Presentación de avance — 21 de agosto de 2026

Diapositivas para presentar el avance del proyecto **PRY-0662064 · SICAV Móvil**
del periodo **14-ago → 21-ago-2026**: la semana del informe de calidad
**IGED-QA-C003**.

## Contenido

| Archivo | Qué es |
|---|---|
| `pptx/presentacion_avance_14-21-ago.pptx` | **La presentación editable en PowerPoint.** 15 diapositivas en 16:9. Es la que se usa para exponer. |
| `pdf/presentacion_avance_14-21-ago.pdf` | Las 15 diapositivas en A4 apaisado, una por página. Para repartir o proyectar sin PowerPoint. |
| `fuente/presentacion_avance_14-21-ago.html` | La misma presentación como página web navegable (flechas, barra espaciadora; `#9` salta a la diapositiva 9). |
| `fuente/generar_pptx.py` | El generador del .pptx. |

Se versiona la fuente (HTML y script), no los binarios: se regeneran (ver abajo).

## Las 15 diapositivas

```
01  Portada
02  El periodo en cifras
03  ── Sección 01: Avances
04  Quién autoriza una excepción     → dejó de decidirlo quien está en el barrio
05  El trabajo sin conexión          → las tres pantallas que quedaron mudas
06  El informe de calidad            → los siete defectos, uno por uno
07  Lo que quedó corriendo           → servidor, panel y aplicación 1.2.2
08  ── Sección 02: Dificultades y soluciones
09  APK-001 · La foto que nadie en campo podía tener
10  APK-002 · El error «intermitente» que no era intermitente
11  APK-003 · El trabajo que desaparecía sin señal
12  APK-005 · El número que mentía
13  Verificación
14  Lo que sigue y la decisión que necesitamos
15  Cierre y equipo
```

La estructura sigue lo pedido: **avance / problema / solución**. Las dificultades
y su solución van en la misma diapositiva, a dos columnas, para que el auditorio
no tenga que recordar el problema tres diapositivas después.

**Se presenta como equipo.** Ningún defecto se atribuye a una persona: los
hallazgos son del sistema y el trabajo es del equipo. Los nombres aparecen una
sola vez, en la diapositiva de cierre y por área de responsabilidad.

## La diapositiva que hay que preparar

La **14** lleva la única pregunta que el equipo necesita responder de la
supervisión, y no es técnica:

> El rediseño del APK-001 movió la autorización de excepciones al nivel central.
> Hoy en producción hay **un coordinador, un supervisor y un administrador** con
> ese permiso, para **1.158 encuestadoras**. Si no se define cuántas cuentas se
> habilitan y quiénes son, el flujo nuevo se traba el primer día de operación.

Conviene llevar una propuesta de número, no solo el problema.

## Cifras que se citan

Medidas contra el repositorio y el servidor entre el 14 y el 21 de agosto de
2026, no estimadas. Las de pruebas se obtuvieron corriendo las tres suites en un
*worktree* en el punto de partida (`e64646c`) y otra vez hoy:

| | |
|---|---:|
| Commits del periodo | 26 |
| Archivos tocados | 52 (+4.977 / −374) |
| Pruebas del servidor | 883 → **944** |
| Pruebas de la aplicación | 115 → **140** |
| Pruebas del panel web | 9 → **14** |
| **Total en verde** | 1.007 → **1.098** (+91) |
| Funciones de prueba nuevas | 72 |
| Hallazgos de calidad atendidos | 13 de 13 |
| Defectos corregidos | 19 (7 del informe + 12 del equipo) |
| Versiones de la aplicación publicadas | 3 (1.2.0, 1.2.1, 1.2.2) |
| Lote máximo de autorización | 200 documentos |

### Tres cifras que se corrigieron antes de entrar

Se dejan anotadas porque son fáciles de repetir mal:

- **No es «901 → 944» en el servidor, es «883 → 944».** El 901 sale del mensaje
  de un commit que ya está *dentro* del periodo, así que incluía pruebas escritas
  esta misma semana.
- **El «N+1 de 79 consultas» nunca estuvo en producción.** Lo introdujo el primer
  borrador de un arreglo y se quitó en el mismo commit. Presentarlo como un
  defecto de campo habría sido falso; la diapositiva 13 lo cuenta como lo que
  fue: una prueba que atajó el problema antes de que saliera del equipo.
- **Ninguna prueba automática toca las pantallas.** Las 140 de la aplicación
  cubren la lógica (servicios, base local, sincronización), no la interfaz.
  «1.098 pruebas en verde» y «las pantallas funcionan» son dos afirmaciones
  distintas, y la 13 lo dice.

## Lo que no hay, y por qué

**Cero cifras de operación.** Ninguna encuestadora ha entrado nunca al sistema —
así fue como se descubrió que el endpoint del APK-001 llevaba tiempo respondiendo
error 500 sin que nadie lo notara. Si la supervisión pregunta cuántas entrevistas
se capturaron esta semana, la respuesta es ninguna, y la diapositiva 14 lo
enmarca: el proyecto está en estabilización previa al arranque.

**El informe IGED-QA-C003 no está en el repositorio.** De APK-008 a APK-013 solo
se tiene la etiqueta de una línea; por eso la diapositiva 06 los menciona en
bloque como «cumplidos según el propio informe» en vez de enumerarlos.

## Regenerar

**El .pptx:**

```bash
python -m pip install python-pptx          # solo la primera vez
python fuente/generar_pptx.py
```

Ojo: si el .pptx está abierto en PowerPoint, el script falla con
`PermissionError`. Cerrar esa pestaña y repetir.

Para retoques puntuales conviene editar directamente en PowerPoint; el script es
para rehacer la presentación entera o cambiar cifras de raíz.

**El PDF** — tras editar el HTML de `fuente/`:

```bash
chrome --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="pdf/presentacion_avance_14-21-ago.pdf" \
  "fuente/presentacion_avance_14-21-ago.html"
```

El detalle de cada hallazgo, con su porqué, está en
[`docs/pruebas/estado_hallazgos_qa_apk.md`](../../docs/pruebas/estado_hallazgos_qa_apk.md).
