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
| A | Pre-test y post-test — 15 preguntas, mismo cuestionario en los dos momentos, con clave y escala. **Se responde en línea** (`/descargar/prueba.html?t=pre` y `?t=post`); el anexo es la copia de control | 8:00 a.m. y 11:40 a.m. |
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
  - **Sesión 1 · martes 8 de septiembre** — Equipo de la Subdirección Red Nacional de Información.
  - **Sesión 2 · martes 15 de septiembre** — Enlaces territoriales, Grupo A (Caribe, Antioquia y
    Nororiente): **16 participantes**.
  - **Sesión 3 · martes 22 de septiembre** — Enlaces territoriales, Grupo B (Centro, Suroccidente y
    Orinoquía): **14 participantes**.
- **Temario** en dos bloques por sesión: **Bloque A — APK** (instalación,
  búsqueda, excepción de vigencia, hogar, instrumento, offline, sincronización) y
  **Bloque B — Panel de Control** (acceso, autorizaciones, hogares/encuestas,
  reportes, auditoría).
- Agenda horaria, metodología, requisitos y los dos rosters completos con correo.

## Pendiente de confirmar

- **Correos institucionales** de Brandon, Karen, Jorge Cardona y la supervisión. Sus
  cuentas en el sistema tienen direcciones de desarrollo (`@srni.dev`, `@srni.local`), y el
  cuestionario de la jornada identifica a cada persona por su correo institucional.
- **Canal de soporte interno UARIV.** El Manual de Uso v1.2 ya está publicado, pero el dato
  del canal sigue con `[COMPLETAR]` dentro del manual y bloquea la impresión de la pieza
  gráfica 7.
- **Convocatoria** con el enlace del pre-test
  (`caracterizacion.unidadvictimas.gov.co/descargar/prueba.html?t=pre`), que debe salir con
  al menos 72 horas de anticipación a cada sesión.
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
