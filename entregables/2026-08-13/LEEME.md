# Presentación de avance quincenal — 13 de agosto de 2026

Diapositivas para presentar el avance del proyecto **PRY-0662064 · SICAV Móvil**
del periodo **29-jul → 13-ago-2026**.

## Contenido

| Archivo | Qué es |
|---|---|
| `pptx/presentacion_avance_quincenal.pptx` | **La presentación editable en PowerPoint.** 15 diapositivas en 16:9. Es la que se usa para exponer. |
| `pdf/presentacion_avance_quincenal.pdf` | Las 15 diapositivas en A4 apaisado, una por página. Para repartir o proyectar sin PowerPoint. |
| `fuente/presentacion_avance_quincenal.html` | La misma presentación como página web navegable (flechas, barra espaciadora; `#9` salta a la diapositiva 9). |
| `fuente/generar_pptx.py` | El generador del .pptx. |

Se versiona la fuente (HTML y script), no los binarios: se regeneran (ver abajo).

## Las 15 diapositivas

```
01  Portada
02  La quincena en cifras
03  ── Sección: Avances
04  Datos reales en producción
05  Operación sin conexión
06  Puente con el sistema heredado
07  Infraestructura y continuidad
08  ── Sección: Dificultades y soluciones
09  El tamaño en el celular      → filtro de existencia de 21,7 MB
10  El tamaño en el servidor     → poda de índices, lotes, traslado
11  El tiempo de las cargas      → COPY y lotes; la lección del EXPLAIN
12  El dato que no era de esa persona → cruce por documento
13  Verificación
14  Lo que sigue y de qué depende
15  Cierre y equipo
```

La estructura sigue lo pedido: **avances / dificultades / soluciones**. Las
dificultades y su solución van en la misma diapositiva, a dos columnas, para que
el auditorio no tenga que recordar el problema tres diapositivas después.

## Cifras que se citan

Medidas contra producción entre el 1 y el 13 de agosto de 2026, no estimadas:

| | |
|---|---:|
| Padrón operativo | 5.926.005 |
| Universo del RUV | 12.009.492 |
| Personas únicas cubiertas | 12.677.172 |
| Víctimas sin caracterización previa | 8.123.873 |
| Encuestadoras cargadas | 1.158 |
| Pruebas automáticas en verde | 977 (862 backend + 115 móvil) |
| Cédulas del territorio verificadas | 68 de 68 |
| Padrón descargable | 896 MB → 319 MB |
| Espacio para la base de datos | 16 GB → 207 GB |
| Cobertura del cruce por documento | 86,1 % |
| Cambios versionados en el periodo | 114 |

## Regenerar

**El .pptx** — se edita `fuente/generar_pptx.py` y se corre:

```bash
python -m pip install python-pptx      # solo la primera vez
python fuente/generar_pptx.py
```

Ojo: si el .pptx está abierto en PowerPoint, el script falla con
`PermissionError`. Cerrar esa pestaña y repetir.

Para retoques puntuales conviene editar directamente en PowerPoint; el script es
para rehacer la presentación entera o cambiar cifras de raíz.

**El PDF** — tras editar el HTML de `fuente/`:

```bash
chrome --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="pdf/presentacion_avance_quincenal.pdf" \
  "fuente/presentacion_avance_quincenal.html"
```

En este equipo: `C:\Program Files\Google\Chrome\Application\chrome.exe`.

## Relación con el entregable anterior

`entregables/2026-08-11/` tiene los tres documentos gerenciales en prosa (resumen
ejecutivo, avance técnico, riesgos y decisiones). **Esta presentación no los
reemplaza**: es la versión para proyectar del mismo contenido, extendida con lo
del 12-ago —cierre de la migración 0021, el cruce del `FLAG_EN_RUV` contra el
universo y el respaldo físico semanal.

El defecto de datos heredado va **incluido** (diapositiva 12), igual que en los
documentos del 11-ago y por la misma razón: invalida temporalmente los reportes
con enfoque diferencial, y presentar el avance sin mencionarlo dejaría a la
supervisión sin un dato que necesita para decidir.
