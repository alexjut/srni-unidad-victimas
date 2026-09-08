# Presentaciones gerenciales de bases de datos — 7 de septiembre de 2026

Dos presentaciones independientes, pensadas para exponerse la misma sesión y en
este orden:

| Archivo | Qué es | Diapositivas |
|---|---|---|
| `pdf/Base-de-datos-SICAV-produccion.pdf` | **La base de datos nuestra, tal como está hoy en producción**: dónde vive, qué guarda, cómo protege el dato personal, cómo circula hasta el Oracle de la entidad y qué está abierto. | 14 |
| `pdf/Base-de-datos-sistema-anterior.pdf` | **Cómo funciona la base de datos del sistema anterior**: las dos bases dentro del teléfono, la cadena de seis eslabones hasta el tablero gerencial, y por qué lleva tres semanas detenida. | 13 |

Los `.html` de la raíz son las mismas presentaciones navegables (flechas, barra
espaciadora, `#9` salta a la diapositiva 9). Los PDF son A4 apaisado, una
diapositiva por página, para repartir o proyectar sin navegador.

## Por qué dos y en este orden

La primera responde «qué tenemos» y la segunda «de dónde venimos y qué sigue
funcionando mientras tanto». Puestas al revés, la segunda parece un reproche al
sistema viejo; en este orden, explica por qué la nueva está construida como
está, y deja el cierre en las decisiones pendientes, que es lo accionable.

Las dos cierran con una tabla de decisiones —tres y cinco— y **ninguna de ellas
es de desarrollo**: son instrucciones o constancias que dependen de la
Subdirección, de Operación o de Infraestructura.

## De dónde salen las cifras

Todo está medido; nada estimado. Con su fecha de medición, que también aparece
al pie de la última diapositiva de cada presentación:

| Cifra | Origen | Medido |
|---|---|---|
| 5.926.004 padrón · 12.009.492 universo | `docs/gestion/estado-global-2026-09-01.md` | 1-sep |
| 106 capítulos · 1.959 preguntas · 6.021 opciones · 1.043 reglas | recuento sobre las nueve parametrizaciones vigentes | 1-sep |
| 7 hogares · 4 sesiones · 1.161 usuarios | producción y `docs/operacion/usuarios_y_perfiles.md` | 11-ago |
| Volumen por tabla · 5,8 GB de índices sin uso | `docs/infraestructura/analisis_capacidad_disco.md` | 5-ago |
| 33,68 GB del volumen de la base | `docs/infraestructura/runbook_traslado_bd_a_datos.md` | 11-ago |
| Servidor, contenedores, tareas programadas | `docs/arquitectura/arquitectura-produccion-2026-08-31.html` | 27-ago |
| Piloto de escritura a Oracle (11/11 verificados) | `docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md` | 28-jul |
| 785 MB · 9,4 M personas · estructura del APK v4.1 | `docs/arquitectura/ANALISIS_APK.md` y `docs/base-datos/apk-original.md` | 9-abr |
| Los 8 defectos del procedimiento · 43 M filas | `docs/analisis-bd-oracle-real.md`, lectura del PL/SQL de producción | — |
| 20 noches · 21.337 archivos · tablero con 9 días de desfase | `docs/gestion/correo_seguimiento_14512_y_gave_2026-09-04.md` | 4-sep |

> **Advertencia que va escrita en ambas presentaciones:** no fue posible
> revalidar en vivo el 7 de septiembre porque la VPN no estaba disponible. Las
> cifras son las últimas medidas, con su fecha a la vista. Antes de usarlas como
> línea base formal conviene revalidarlas con conexión.

## Regenerar

Desde la carpeta del entregable, con Google Chrome instalado:

```bash
python fuente/armar.py       # HTML autónomo desde el cuerpo + el estilo común
python fuente/verificar.py   # comprueba que ninguna diapositiva se desborde del 16:9

CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
D="D:/desarrollo/unidad-victima/entregables/2026-09-07-bases-de-datos"
for f in "Base-de-datos-SICAV-produccion" "Base-de-datos-sistema-anterior"; do
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --virtual-time-budget=25000 --print-to-pdf="$D/pdf/$f.pdf" "file:///$D/$f.html"
done
```

`--virtual-time-budget` es necesario: sin él Chrome imprime antes de que la
página termine de componerse.

**Editar el contenido se hace en `fuente/cuerpo_*.html`**, no en el HTML de la
raíz —que se sobrescribe—. La numeración de pie se calcula sola: cada
diapositiva lleva `<span data-num></span>` y `armar.py` la resuelve, así que
insertar una lámina no obliga a renumerar las demás.

`verificar.py` existe porque una diapositiva que se desborda **no avisa**: el
marco recorta el contenido y el PDF sale con el texto cortado. Conviene correrlo
después de cada edición y antes de imprimir.

## Estilo

`fuente/estilo-sicav.css` es el sistema de la presentación de avance del 28 de
agosto, con tres añadidos para estas: la cadena de eslabones, los bloques de
capas y una variante compacta de la tabla. Se copió en lugar de compartirse para
que ajustar la densidad de estas láminas no altere las ya entregadas.
