# OE5 — Estructura de bases de datos

> **Obligación contractual:** *Crear, diseñar y documentar la estructura de bases de datos para garantizar la eficiencia, integridad y seguridad de los datos utilizados en los procedimientos de instrumentalización de la información y análisis tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Quedaron cargados y en operación los **dos conjuntos de datos** que sostienen la
búsqueda de personas:

- **Padrón operativo — 5.936.769 víctimas incluidas.** Es el registro sobre el que
  se caracteriza.
- **Universo del registro de víctimas — ~12,5 millones de filas** (corte). Se
  incorporó como **fuente de existencia**: antes, quien nunca había sido
  entrevistado era invisible para el sistema aunque estuviera en el registro; ahora
  el panel lo reconoce y le puede materializar la ficha al autorizar (ver OE4).

**Integridad del cruce entre fuentes.** Se midió que los identificadores internos de
los dos sistemas **no coinciden**: de 243.610 pares con el mismo documento, **cero**
coinciden por identificador interno. Por eso el enlace se hace **siempre por número
de documento y nunca por el identificador interno** — de lo contrario se le
atribuirían a una persona los datos (género, etnia, discapacidad, estado en el RUV)
de otra. Esta guarda quedó documentada y aplicada en el código.

**Escritura hacia la base de la entidad (Oracle).** Las caracterizaciones nuevas se
escriben exclusivamente por los **procedimientos oficiales `GIC_*`** (nunca `INSERT`
directo a tablas), verificando cada escritura con una consulta posterior. Esa ruta,
cuyo piloto en producción se logró a fin de julio, se mantuvo bajo seguimiento; la
escritura automática continua sigue **apagada por defecto** de forma deliberada,
hasta que la Unidad autorice encenderla.

**Registro de un pendiente ajeno a este alcance.** La Unidad informó de una tabla y
un índice creados por ellos en el esquema del universo (Oracle). Se **anotó para
tenerlo en cuenta cuando se inicie la mejora de la base**, pero **no entra en este
mes** ni se tocó nada de eso.

## Evidencia que soporta esta actividad

- `docs/arquitectura/adr-padron-universo-victimas.md` — decisión aprobada 5-ago;
  universo 12.496.965 filas del corte.
- `docs/oracle-legacy-padron/hallazgos_identidad_padron.md` — 5.936.769 incluidas;
  1.884.872 (24,1 %) sin identidad en el servidor de la entidad; cruce por documento.
- `docs/ciclo_completo_tablas.md` — flujo de escritura a Oracle por procedimientos
  `GIC_*` con verificación posterior.
- Comando de carga del universo: `cargar_universo_victimas.py`.

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `commits-datos-agosto.txt` | Commits del mes sobre padrón, universo, identidad e integridad del cruce |

## Pendiente / siguiente paso

- Definir con la Unidad el encendido continuo de la escritura automática a Oracle.
- Incorporar la tabla e índice creados por la Unidad al análisis de la fase de mejora
  de la base de datos (fuera de este mes).
