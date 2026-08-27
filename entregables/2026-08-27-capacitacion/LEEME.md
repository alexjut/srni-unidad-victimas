# Plan de Capacitación — SICAV Móvil (APK) y Panel de Control

Plan de capacitación para el equipo de la **Subdirección Red Nacional de
Información** y los **enlaces de las direcciones territoriales**, sobre las dos
herramientas del sistema de caracterización: la aplicación móvil **SICAV Móvil**
y el **Panel de Control** web.

## Contenido

| Archivo | Qué es |
|---|---|
| `pdf/plan_capacitacion.pdf` | **El plan, listo para enviar/imprimir.** A4, 5 páginas. |
| `fuente/plan_capacitacion.html` | La fuente del plan (se versiona esta, no el PDF; se regenera). |

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

- **Mes y fechas exactas** de los días 1, 3 y 8 (con la Subdirección).
- **Listado nominal** de asistentes de la Sesión 1 (equipo SRNI).

## Regenerar el PDF

Desde la carpeta del entregable, con Google Chrome instalado:

```bash
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="pdf/plan_capacitacion.pdf" \
  "file:///D:/desarrollo/unidad-victima/entregables/2026-08-27-capacitacion/fuente/plan_capacitacion.html"
```
