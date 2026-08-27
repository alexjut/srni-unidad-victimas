# Plan de Capacitación — SICAV Móvil (APK) y Panel de Control

Plan de capacitación para el equipo de la **Subdirección Red Nacional de
Información** y los **enlaces de las direcciones territoriales**, sobre las dos
herramientas del sistema de caracterización: la aplicación móvil **SICAV Móvil**
y el **Panel de Control** web.

## Contenido

| Archivo | Qué es |
|---|---|
| `pdf/plan_capacitacion.pdf` | **El plan, listo para enviar/imprimir.** A4, 5 páginas. |
| `pdf/anexos_capacitacion.pdf` | **Los anexos del plan.** A4, 18 páginas. |
| `fuente/plan_capacitacion.html` | La fuente del plan (se versiona esta, no el PDF; se regenera). |
| `fuente/anexos_capacitacion.html` | La fuente de los anexos. |

## Anexos (8 instrumentos)

Todo el contenido está anclado al sistema real: instrumento territorial **V8**
(14 capítulos, 363 preguntas, 276 reglas de salto) y **SICAV Móvil 1.2.3**.

| | Anexo | Cuándo se usa |
|---|---|---|
| A | Pre-test y post-test — 15 preguntas, mismo cuestionario en los dos momentos, con clave y escala | 8:00 a.m. y 11:50 a.m. |
| B | Banco de 32 preguntas por capítulo + tabla de referencia Hogar/Persona | Bloque A y refuerzo |
| C | Tres casos de estudio: hogar offline · ficha vigente (APK + panel) · alta manual e incidencia | Práctica guiada |
| D | Plantilla de documentación de la experiencia (6 secciones) | Cierre de cada sesión |
| E | Revisión del Manual de Usuario — 9 hallazgos verificados | Antes de la Sesión 1 |
| F | Encuesta de calidad (10 ítems Likert) + 4 preguntas abiertas | 11:50 a.m. |
| G | Especificación de las 7 piezas gráficas | Antes de convocar |
| H | Verificación de dispositivos y credenciales — formato con los 30 participantes | 72 horas antes |

## Estructura del plan

- **3 sesiones**, jornada de la mañana (8:00 a.m. – 12:00 m.), dictadas por
  **Jorge** (calidad), **Javier Aguilar** (APK) y **Brandon** (panel).
  - **Sesión 1 · martes 1 de septiembre** — Equipo de la Subdirección Red Nacional de Información.
  - **Sesión 2 · jueves 3 de septiembre** — Enlaces territoriales, Grupo A (Caribe, Antioquia y
    Nororiente): **16 participantes**.
  - **Sesión 3 · martes 8 de septiembre** — Enlaces territoriales, Grupo B (Centro, Suroccidente y
    Orinoquía): **14 participantes**.
- **Temario** en dos bloques por sesión: **Bloque A — APK** (instalación,
  búsqueda, excepción de vigencia, hogar, instrumento, offline, sincronización) y
  **Bloque B — Panel de Control** (acceso, autorizaciones, hogares/encuestas,
  reportes, auditoría).
- Agenda horaria, metodología, requisitos y los dos rosters completos con correo.

## Pendiente de confirmar

- **Listado nominal** de asistentes de la Sesión 1 (equipo SRNI) — para replicarles el
  formato del Anexo H.
- **Canal de soporte interno UARIV.** Bloquea dos cosas a la vez: la publicación del
  Manual de Uso (sigue con `[COMPLETAR]`) y la impresión de la pieza gráfica 7.
- **Actualización del Manual de Uso a v1.2** antes del 1 de septiembre, con los cuatro
  hallazgos de prioridad alta del Anexo E.
- **Verificación de dispositivos** de los 30 enlaces (Anexo H), 72 horas antes de cada sesión.

## Regenerar el PDF

Desde la carpeta del entregable, con Google Chrome instalado:

```bash
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
BASE="file:///D:/desarrollo/unidad-victima/entregables/2026-08-27-capacitacion/fuente"

"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=30000 --print-to-pdf="pdf/plan_capacitacion.pdf" \
  "$BASE/plan_capacitacion.html"

"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=30000 --print-to-pdf="pdf/anexos_capacitacion.pdf" \
  "$BASE/anexos_capacitacion.html"
```

> `--virtual-time-budget` es necesario: sin él Chrome imprime antes de que carguen las
> tipografías (Nunito Sans) y el PDF sale con fuentes de respaldo.
