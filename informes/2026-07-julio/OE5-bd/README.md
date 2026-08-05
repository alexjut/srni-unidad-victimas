# OE5 — Estructura de bases de datos

> **Obligación contractual:** *Crear, diseñar y documentar la estructura de bases de datos para garantizar la eficiencia, integridad y seguridad de los datos utilizados en los procedimientos de instrumentalización de la información y análisis tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Julio fue el mes en que la base de datos pasó de estructura vacía a **base
operativa con el padrón real**. Tres frentes:

**1. Estructura del padrón de víctimas.** Se diseñó y desplegó la tabla que
sostiene los **5.926.004 registros**, con las decisiones que exige operar a ese
volumen: PII cifrada en reposo, doble índice de búsqueda por hash (identidad y
respaldo), y tipo de documento **opcional** —porque el 14,5 % de la fuente no lo
trae, y hacerlo obligatorio habría dejado fuera a 1,1 millones de personas—.

**2. Estructura para la identidad ambigua.** Se creó el modelo que clasifica los
**768.096 documentos compartidos por más de un registro**, separando los que son la
misma persona duplicada en el origen de los que son personas realmente distintas.
Sin esa estructura, la aplicación tendría que recalcular la clasificación en cada
búsqueda —operación que exige descifrar millones de filas— o preguntarle siempre al
encuestador, que es justamente lo que enseña a ignorar el aviso.

**3. Réplica local de la base del legado.** Se levantó una réplica en contenedor
con la estructura real de `RNIENTREVISTA`, para validar la ruta de escritura sin
tocar producción. Es lo que permitió probar los procedimientos oficiales `GIC_*` de
extremo a extremo antes del piloto real.

Todos los cambios de estructura quedaron versionados como **migraciones
reproducibles**, no como scripts sueltos: la base se puede reconstruir desde cero.

## Evidencia que soporta esta actividad

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `estructura-y-volumen-base-produccion.txt` | Inventario real de tablas con columnas y filas, estructura completa de la tabla del padrón, sus índices, y las migraciones aplicadas con su fecha |
| `migraciones-del-proyecto.txt` | Listado de las migraciones versionadas del proyecto |
| `oracle-local-setup.md` | Documentación de la réplica local de la base del legado |

## Pendiente / siguiente paso

- Respaldo verificado de las tablas del legado antes del piloto general de
  escritura, y comando de reversión.
