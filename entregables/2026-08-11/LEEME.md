# Entregable gerencial — 11 de agosto de 2026

Documentos para presentar el estado del proyecto **PRY-0662064 · SICAV Móvil**.

## Contenido

| Archivo | Págs. | Para qué sirve |
|---|:--:|---|
| `pdf/01_resumen_ejecutivo.pdf` | 2 | **El principal.** Estado en una página, cifras clave, qué significa en terreno, el riesgo identificado y próximos pasos. Si solo se entrega uno, es este. |
| `pdf/02_avance_tecnico.pdf` | 3 | El detalle de lo construido: datos en producción, operación sin conexión, aplicación móvil, infraestructura y verificación. Para quien pregunte “¿qué hay debajo?”. |
| `pdf/03_riesgos_y_decisiones.pdf` | 2 | Riesgos con su nivel y manejo, y **las dos decisiones que requieren definición de la supervisión**. Útil para pedir definiciones en reunión. |

`fuente/` contiene los originales en HTML. Para modificar un documento se edita el
HTML y se regenera (ver abajo) — así el formato se mantiene idéntico.

## Cifras que se citan

Todas están medidas contra producción el 11-ago-2026, no estimadas:

| | |
|---|---:|
| Padrón operativo | 5.926.005 |
| Universo del RUV | 12.009.492 |
| Personas únicas cubiertas | 12.677.172 |
| Víctimas sin caracterización previa | 8.123.873 |
| Encuestadoras cargadas | 1.158 |
| Pruebas automáticas en verde | 972 |
| Cédulas del territorio verificadas | 68 de 68 |

## Qué NO incluye

- **No hay corte formal de monitoreo de agosto.** El último es a 30-jun
  (`monitoreo/corte_2026-06-30/`, 16 documentos). Estos tres cubren el avance
  posterior, pero no siguen la estructura de línea base y soportes numerados.
- **No reemplazan la documentación técnica.** Los 89 documentos de `docs/` siguen
  siendo la referencia; estos son su lectura gerencial.

## Regenerar los PDF

Tras editar un HTML de `fuente/`:

```bash
chrome --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="pdf/NOMBRE.pdf" "fuente/NOMBRE.html"
```

En este equipo: `C:\Program Files\Google\Chrome\Application\chrome.exe`.

## Nota sobre el contenido

Los tres documentos **incluyen el defecto de datos encontrado**, en vez de omitirlo.
Es una decisión deliberada: el hallazgo invalida temporalmente los reportes con
enfoque diferencial, y presentar el avance sin mencionarlo dejaría a la supervisión
sin un dato que necesita para decidir. Va acompañado de su alcance verificado —qué
sí y qué no está afectado— y de las medidas ya aplicadas.
