# Veredicto de calidad de datos — Oracle legacy de producción

**Esquema:** `RNIENTREVISTA` en `30.0.1.9/ENTREVISTARN` (Oracle 19c Enterprise Edition 19.0.0.0.0)
**Fecha de medición:** 2026-07-28 (entre 10:42 y 11:20, hora del servidor)
**Autor:** agente de base de datos SICAV/SRNI
**Alcance:** calidad e integridad de los datos de caracterización, para corregir **después** de terminar la migración.

> 🔒 **AUDITORÍA DE SOLO LECTURA. NINGÚN DATO FUE MODIFICADO.**
> Todas las sentencias ejecutadas fueron `SELECT` sobre el diccionario de datos y sobre tablas de negocio.
> No se ejecutó ningún `INSERT`/`UPDATE`/`DELETE`/`DDL`, no se crearon objetos ni tablas temporales, y no se
> programó ningún job. El harness de consulta bloquea por expresión regular cualquier verbo que no sea de lectura.
>
> 🔒 **SIN PII.** No se extrajo ni se imprimió ningún nombre, documento, teléfono o dirección. Todas las cifras
> son agregados (`COUNT`, `SUM`, `MIN`/`MAX`, longitudes y formas). Cuando fue necesario caracterizar un valor
> (p. ej. documentos duplicados) se midió únicamente su **longitud** y si era **numérico o no**, nunca su contenido.

**Nota sobre las cifras:** la base está viva y recibe escrituras durante la auditoría. Entre la primera y la última
consulta `GIC_PERSONA` pasó de 7.757.407 a 7.757.438 filas (+31) y `GIC_HOGAR` de 1.102.858 a 1.102.878 (+20).
Las cifras de este documento son fotografías del momento de cada consulta; las diferencias de decenas entre
hallazgos son ese movimiento, no un error de medición.

---

## 1. Veredicto

Esta base **no está corrupta a nivel estructural: está sucia a nivel semántico y desatendida a nivel operativo.**
La integridad referencial de la caracterización es buena donde hay claves foráneas — 0 miembros sin hogar,
0 respuestas con hogar inexistente, 0 respuestas apuntando a un id de catálogo que no existe — y los huérfanos
reales son residuos de tres cifras sobre millones de filas (270 miembros sin persona, 211 respuestas con persona
inexistente, 4 filas territoriales sin hogar en ninguna de las dos tablas de hogar). El problema no es ese.

El problema es que **el modelo no defiende lo que importa**: `GIC_PERSONA` (7,76 M de filas) no tiene clave
primaria ni índice único, y el resultado medido es que 2.016.957 filas (26,0 %) comparten par
(tipo de documento, número de documento) con otra fila, con una llave que se repite hasta 5.437 veces. En la misma
línea, 142.352 personas (1,84 %) tienen una fecha de nacimiento imposible — el rango real va del año 0001 al 9999 —
y 1.126.613 (14,5 %) no tienen tipo de documento. Nada de esto es un accidente de migración: es la ausencia de
restricciones durante diez años de operación.

En lo operativo hay señales de abandono que **no dependen del dato sino del cuidado del sistema**: 53 objetos PL/SQL
inválidos (4,1 % de los no-Java), cuatro jobs que llevan entre 1.472 y 1.718 fallos consecutivos y siguen
habilitados y ejecutándose hoy, y estadísticas del optimizador congeladas el **2024-05-16** — dos años y dos meses —
con un desvío del 14 % en la tabla más grande del esquema.

**Lo tranquilizador para la migración:** ninguno de los objetos inválidos está en la ruta de escritura de la
caracterización. El paquete `GIC_N_CARACTERIZACION` (cuerpo y especificación) está `VALID`, ningún objeto válido
depende de uno inválido, y todo lo roto son reportes, microdatos y procedimientos de análisis con nombres como
`PRUEBAPRUEBA`, `PKG_REP_CARAC_COPIA` o `SP_MICRODATO_HOGAR_2015_2016`. **La migración puede seguir adelante.**

---

## 2. Tabla de hallazgos

Ordenada por severidad. 🔴 corrompe datos · 🟠 degrada · 🟡 higiene.

| # | Sev | Hallazgo | Evidencia (cifra medida) | Impacto | Acción propuesta | Esfuerzo |
|---|-----|----------|--------------------------|---------|------------------|----------|
| 1 | 🔴 | Personas duplicadas por documento | 864.789 llaves (tipodoc, numdoc) repetidas → **2.016.957 filas (26,0 % de 7.757.438)**; 18 llaves repiten >100 veces (11.735 filas); máximo 5.437 | Una misma víctima cuenta varias veces; los reportes por persona sobreestiman | Deduplicar por lotes con criterio de negocio; luego índice único | Alto |
| 2 | 🔴 | `GIC_PERSONA` sin PK ni unique | 0 constraints `P`/`U` en la tabla; solo **56 PK en 331 tablas** del esquema | Nada impide seguir insertando duplicados: el hallazgo 1 se reproduce cada día | Crear PK en `PER_IDPERSONA` y único en (tipodoc, numdoc) tras deduplicar | Alto |
| 3 | 🔴 | Fechas de nacimiento imposibles | **140.962 anteriores a 1900** + **1.390 futuras** = 142.352 (1,84 %); rango real `0001-01-01` … `9999-10-20`; 148.491 implican edad >110 | Cálculo de edad erróneo → mal enrutamiento de rutas etarias (NNA, adulto mayor) | `CHECK` de rango + corrección dirigida de las 6.079 que sí están caracterizadas | Medio |
| 4 | 🟠 | Trazabilidad de autoría rota | **1.077.712 hogares (97,7 %)** con `USU_USUARIOCREACION` que no existe en `GIC_USUARIO`; 9.424 cadenas distintas vs 8.172 usuarios; `USU_IDUSUARIO` no cruza en 1.099.482 (99,7 %) | No se puede auditar quién capturó una encuesta | Reconstruir histórico de usuarios o declarar el campo como texto libre no auditable | Medio |
| 5 | 🟠 | Cuatro jobs fallando de forma crónica | `JOB_PKG_ACTUALIZAR_TAB_REP` **1.718 fallos**, `JOB_PS_ANDAGUEDA` 1.718, `JOB_PKG_TABLAS_HOGXPERS` 1.706, `GIC_REPORTEULTIMOANIO` 1.472 — todos `SCHEDULED`/`ENABLED`, último arranque 2026-07-28 | Tablas de reporte desactualizadas en silencio; ruido que oculta fallos nuevos | Diagnosticar o deshabilitar; hoy fallan sin que nadie lo note | Bajo |
| 6 | 🟠 | 53 objetos PL/SQL inválidos | 41 `PROCEDURE` + 10 `PACKAGE BODY` + 2 `VIEW` = **4,1 % de 1.284** objetos no-Java; causa dominante `ORA-00942` (tabla o vista no existe). Además 811 `JAVA CLASS` inválidas | Reportes y microdatos caídos. **Ninguno en la ruta de escritura** | Recompilar lo recuperable; borrar lo muerto (`PRUEBAPRUEBA`, `*_COPIA`, `*_PRUEBA`) | Medio |
| 7 | 🟠 | Estadísticas del optimizador congeladas | Última recolección **2024-05-16** en 6 de 7 tablas core; `STALE_STATS=YES` en las 7; `_C` declara 426.963.675 filas vs **498.828.649** reales (−14,4 %); `GIC_PERSONA` 6.430.300 vs 7.757.438 (−17,1 %) | Planes de ejecución subóptimos en toda la base | `DBMS_STATS.GATHER_SCHEMA_STATS` en ventana de baja carga | Bajo |
| 8 | 🟠 | Fecha de creación centinela año 1900 | **503.317 personas (6,49 %)** con `USU_FECHACREACION` en 1900; 17 en año **0026**; 7 en 1969; 6 hogares en año 0026; `_C` tiene `MIN = 0026-04-25` | Series temporales y cohortes de captura contaminadas | Marcar 1900 como "desconocido" explícito; investigar el origen del año 0026 | Medio |
| 9 | 🟠 | Mitad de los hogares sin territorio | **555.975 de 1.102.858 hogares (50,4 %)** sin fila en `GIC_N_RELACION_DT_PUNTO` | No se puede atribuir esos hogares a una DT / punto de atención | Verificar si es esperable en hogares antiguos antes de intentar reconstruir | Medio |
| 10 | 🟠 | Sobre-indexación masiva de `_C` | **13 índices = 180,6 GB** sobre una tabla de **36,3 GB** (5,0×); 7 de ellos encabezan por `HOG_CODIGO`. `_C` + índices = 216,9 GB de los **500,3 GB** del esquema (43,4 %) | Costo de almacenamiento y penalización en cada escritura | Analizar uso real y consolidar los redundantes | Medio |
| 11 | 🟡 | Territorio incompleto (bug histórico) | **599 filas de 1.119.775 (0,053 %)** con algún id en NULL: `IDMUNATEN` 597, `IDPUNTOATEN` 392, `IDDEPTOATEN` 183, `IDDT` **0**. Además 44 filas con combinación inexistente en `GIC_N_DT_PUNTOS_ATENCION` | Menor de lo temido: el bug existe pero está acotado a 6 de cada 10.000 filas | Completar las 599 desde el punto de atención; `NOT NULL` a futuro | Bajo |
| 12 | 🟡 | Documentos implausibles | **1.126.613 (14,5 %) sin tipo de documento**; 11.952 sin número (0,15 %); 8.535 con ≤4 caracteres (0,11 %); 7.570 no numéricos (0,10 %) | Cruces contra RUV/registraduría fallan en silencio | Validación de formato por tipo de documento en captura | Medio |
| 13 | 🟡 | Catálogo con opciones no escribibles | **205 preguntas sin instrumento (188 marcadas activas)**; **153 respuestas sin instrumento (116 activas)**; 17 preguntas sin ninguna respuesta; 3 respuestas huérfanas de pregunta | Opciones visibles en el catálogo que nunca se pueden guardar | Depurar el catálogo o vincular al instrumento correcto | Bajo |
| 14 | 🟡 | Textos duplicados en el catálogo | **123 grupos de texto de pregunta idéntico → 344 preguntas**; solo **2 preguntas** (ids 30 y 89) con texto de opción duplicado | Ambigüedad al reportar; menor de lo esperado en opciones | Consolidar ids duplicados con mapa de equivalencias | Medio |
| 15 | 🟡 | Huérfanos residuales | 270 miembros sin persona (0,0080 %); 211 respuestas con `PER_IDPERSONA` inexistente (0,0055 %); 543 respuestas con `HOG_CODIGO` NULL (0,014 %); 4 filas territoriales sin hogar; 3.833 hogares sin miembros (0,35 %) | Marginal, pero rompe joins estrictos | Limpieza puntual; añadir FK que hoy faltan | Bajo |
| 16 | 🟡 | Duplicados menores | 26 pares (hogar, persona) repetidos en `GIC_MIEMBROS_HOGAR` → 54 filas; 21 tripletas (hogar, persona, respuesta) repetidas → 44 filas. **0 hogares con código duplicado**, **0 PK duplicada** en respuestas | Casi nulo | Limpieza puntual + único compuesto | Bajo |
| 17 | 🟡 | FK deshabilitada sin validar | `GIC_ARBOLGENEALOGICO.GIC_REL_PARENGENTOARBGEN` en `DISABLED` / `NOT VALIDATED` — única entre 66 FK `R`; además 2 PK en `DISABLED` | Parentesco genealógico sin garantía referencial | Validar y rehabilitar si el dato lo permite | Bajo |

---

## 3. Detalle por hallazgo

Todas las consultas son reproducibles tal cual. Ninguna modifica datos.

### 3.1 Objetos INVALID en producción — y si tocan la ruta de escritura

**Conteo por tipo.**

```sql
SELECT object_type, COUNT(*) FROM all_objects
WHERE owner='RNIENTREVISTA' AND status<>'VALID'
GROUP BY object_type ORDER BY 2 DESC;
```

| Tipo | Inválidos | Total del tipo | % |
|---|---|---|---|
| `JAVA CLASS` | 811 | 1.647 | 49,2 % |
| `PROCEDURE` | 41 | 128 | 32,0 % |
| `PACKAGE BODY` | 10 | 29 | 34,5 % |
| `VIEW` | 2 | 5 | 40,0 % |

Excluyendo Java: **53 inválidos sobre 1.284 objetos no-Java = 4,13 %**.

```sql
SELECT
 (SELECT COUNT(*) FROM all_objects WHERE owner='RNIENTREVISTA'
   AND object_type NOT LIKE 'JAVA%' AND object_type NOT IN ('LOB')) total_no_java,
 (SELECT COUNT(*) FROM all_objects WHERE owner='RNIENTREVISTA'
   AND status<>'VALID' AND object_type NOT LIKE 'JAVA%') invalid_no_java
FROM dual;
-- → 1284 | 53
```

**Nota comparativa:** el enunciado reportaba 67 objetos inválidos en la réplica local. En producción son **53**
(sin contar Java) o **864** contándolas. Son universos distintos: la réplica local no tiene las clases Java.

**¿Alguno está en la ruta de escritura?** No.

```sql
SELECT object_name, object_type, status, TO_CHAR(last_ddl_time,'YYYY-MM-DD') ult_ddl
FROM all_objects WHERE owner='RNIENTREVISTA'
  AND object_name IN ('GIC_N_CARACTERIZACION','GIC_ENCUESTA_MOVIL');
-- → GIC_N_CARACTERIZACION  PACKAGE BODY  VALID  2026-03-03
-- → GIC_N_CARACTERIZACION  PACKAGE       VALID  2024-02-11
-- → GIC_ENCUESTA_MOVIL     TABLE         VALID  2021-11-13
```

Los procedimientos de escritura (`GIC_INSERT_HOGAR`, `GIC_INSERT_PERSONAS`, `GIC_SP_GUARDAMUNATEN`,
`GIC_SP_OBTDT`, …) no son objetos de primer nivel: son **80 subprogramas dentro del paquete
`GIC_N_CARACTERIZACION`**, que está `VALID`. Verificado con:

```sql
SELECT COUNT(*) FROM all_procedures
WHERE owner='RNIENTREVISTA' AND object_name='GIC_N_CARACTERIZACION';
-- → 80
```

**Ningún objeto válido depende de uno inválido** (el grafo de dependencias está limpio):

```sql
SELECT d.name, d.type, d.referenced_name
FROM all_dependencies d
JOIN all_objects o ON o.owner=d.referenced_owner AND o.object_name=d.referenced_name
                   AND o.object_type=d.referenced_type AND o.status<>'VALID'
WHERE d.owner='RNIENTREVISTA' AND d.referenced_owner='RNIENTREVISTA'
  AND d.referenced_type IN ('PACKAGE','PACKAGE BODY','PROCEDURE','FUNCTION','VIEW');
-- → 0 filas
```

**Qué está roto, exactamente.** Los 53 inválidos son reportería y microdatos. Los paquetes:
`GIC_EJECUTOR_EN_CRUCE`, `GIC_N_REPORTES`, `GIC_UNIVERSO`, `PKG_ANDRES_PRE_TIPO3`, `PKG_INSERT`,
`PKG_REPORTE_CARACTERIZACION`, `PKG_REPORTE_ENCUESTADORMOVIL`, `PKG_REP_CARAC_COPIA`,
`PKG_TL_APP_RECONOCIMIENTO`, `PKG_WS_UTILITARIO_RNI`. Las 2 vistas: `VIEW_REP_HOGAR_SAAH`,
`VIEW_REP_PERSONA_SAAH`. Entre los 41 procedimientos hay 13 variantes de `SP_MICRODATO_HOGAR_*`,
5 de `CURSOR_HOGARES*` y objetos claramente descartables (`PRUEBAPRUEBA`, `PROBAR_DIR`,
`GIC_HOG_ENCUE_PRUEBA`, `GIC_SP_MICR_HOGAR_PRUEBA`).

La causa dominante es `ORA-00942: table or view does not exist` — referencian tablas que ya no existen:

```sql
SELECT name, type, COUNT(*) errores FROM all_errors
WHERE owner='RNIENTREVISTA' GROUP BY name, type ORDER BY 3 DESC FETCH FIRST 5 ROWS ONLY;
-- → PRO_TEM_UPDATE_TAPC (PROCEDURE) 20 · PKG_REP_CARAC_COPIA 20
--   GIC_N_REPORTES 20 · PKG_REPORTE_CARACTERIZACION 20 · CURSOR_ENTREVISTA_SAAH 17
```

### 3.2 Jobs fallando en silencio

```sql
SELECT job_name, state, enabled, failure_count, TO_CHAR(last_start_date,'YYYY-MM-DD') ult_inicio
FROM all_scheduler_jobs WHERE owner='RNIENTREVISTA'
ORDER BY failure_count DESC NULLS LAST FETCH FIRST 8 ROWS ONLY;
```

| Job | Estado | Habilitado | Fallos | Último arranque |
|---|---|---|---|---|
| `JOB_PKG_ACTUALIZAR_TAB_REP` | SCHEDULED | TRUE | **1.718** | 2026-07-28 |
| `JOB_PS_ANDAGUEDA` | SCHEDULED | TRUE | **1.718** | 2026-07-28 |
| `JOB_PKG_TABLAS_HOGXPERS` | SCHEDULED | TRUE | **1.706** | 2026-07-28 |
| `GIC_REPORTEULTIMOANIO` | SCHEDULED | TRUE | **1.472** | 2026-07-27 |
| `GIC_REPORTE_DT_` | DISABLED | FALSE | 306 | 2022-09-14 |
| `JOB_PROCESAMIENTO_NECESIDADES` | SCHEDULED | TRUE | 56 | 2026-07-01 |
| `JOB_SP_ADD_ENCUESTAS_MOVIL` | SCHEDULED | TRUE | 14 | 2026-07-27 |
| `JOB_SP_MIGRAR_ENCUESTAS_A_HISTORICO` | SCHEDULED | TRUE | 9 | 2026-07-28 |

El esquema tiene 57 jobs. Los cuatro primeros siguen habilitados y arrancando hoy con más de 1.400 fallos
acumulados cada uno.

### 3.3 Integridad referencial

**Restricciones existentes.** El esquema tiene 66 FK (`R`) de las cuales 65 están `ENABLED`/`VALIDATED`, y solo
56 PK para 331 tablas.

```sql
SELECT constraint_type, status, COUNT(*) FROM all_constraints
WHERE owner='RNIENTREVISTA' AND constraint_type IN ('P','R','U','C')
GROUP BY constraint_type, status ORDER BY 1,2;
-- → C ENABLED 3383 · P DISABLED 2 · P ENABLED 56 · R DISABLED 1 · R ENABLED 65 · U ENABLED 11
```

La única FK deshabilitada es `GIC_ARBOLGENEALOGICO.GIC_REL_PARENGENTOARBGEN` (`DISABLED` / `NOT VALIDATED`).

**Tablas grandes sin PK** (>100.000 filas, top 5):

```sql
SELECT t.table_name, t.num_rows FROM all_tables t
WHERE t.owner='RNIENTREVISTA'
  AND NOT EXISTS (SELECT 1 FROM all_constraints c
                  WHERE c.owner=t.owner AND c.table_name=t.table_name AND c.constraint_type='P')
  AND t.num_rows > 100000 ORDER BY t.num_rows DESC FETCH FIRST 5 ROWS ONLY;
-- → GIC_N_RESPUESTASENCUESTA_C 426.963.675 · GIC_ACTUALIZAR_RESPUESTA 178.741.474
--   GIC_N_VALIDADORESXPERSONA_HIS 58.077.800 · GIC_REPORTE_TEMATICA 51.437.500
--   GIC_ENCUESTA_MOVIL 43.856.806
```

`GIC_PERSONA` aparece en la misma lista (6.430.300 según estadísticas): **no tiene clave primaria**.

**Huérfanos medidos.**

| Verificación | Resultado | Base | % |
|---|---|---|---|
| Miembros sin hogar | **0** | 3.377.039 | 0 % |
| Miembros sin persona | **270** | 3.377.039 | 0,0080 % |
| Respuestas con `HOG_CODIGO` inexistente | **0** | 3.843.797 | 0 % |
| Respuestas con `HOG_CODIGO` NULL | **543** | 3.843.797 | 0,0141 % |
| Respuestas con `PER_IDPERSONA` inexistente | **211** | 3.843.797 | 0,0055 % |
| Respuestas con `RES_IDRESPUESTA` fuera del catálogo | **0** | 3.843.797 | 0 % |
| Hogares sin ningún miembro | **3.833** | 1.102.858 | 0,348 % |

```sql
SELECT COUNT(*) FROM GIC_MIEMBROS_HOGAR m
WHERE NOT EXISTS (SELECT 1 FROM GIC_HOGAR h WHERE h.HOG_CODIGO=m.HOG_CODIGO);          -- 0

SELECT COUNT(*) FROM GIC_MIEMBROS_HOGAR m
WHERE NOT EXISTS (SELECT 1 FROM GIC_PERSONA p WHERE p.PER_IDPERSONA=m.PER_IDPERSONA);  -- 270

SELECT COUNT(*) total, SUM(CASE WHEN r.PER_IDPERSONA IS NULL THEN 1 ELSE 0 END) per_null
FROM GIC_N_RESPUESTASENCUESTA r
WHERE r.PER_IDPERSONA IS NULL
   OR NOT EXISTS (SELECT 1 FROM GIC_PERSONA p WHERE p.PER_IDPERSONA=r.PER_IDPERSONA);  -- 211 | 0

SELECT COUNT(*) FROM GIC_N_RESPUESTASENCUESTA r WHERE r.HOG_CODIGO IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM GIC_HOGAR h WHERE h.HOG_CODIGO=r.HOG_CODIGO);          -- 0

SELECT COUNT(*) FROM GIC_HOGAR h
WHERE NOT EXISTS (SELECT 1 FROM GIC_MIEMBROS_HOGAR m WHERE m.HOG_CODIGO=h.HOG_CODIGO); -- 3833
```

Los 0 de hogar se explican por la FK `RESNTOHOGA` y `GIC_REL_HOGAR_TO_MIEMBRO`, ambas `ENABLED`/`VALIDATED`.
Los 211 y los 270 existen porque **no hay FK hacia `GIC_PERSONA`** — no puede haberla: `GIC_PERSONA` no tiene PK.

### 3.4 El falso positivo del territorio: 51 % de huérfanos que no lo son

Esta es la corrección más importante del informe. La primera medición dio:

```sql
SELECT COUNT(*) FROM GIC_N_RELACION_DT_PUNTO r
WHERE NOT EXISTS (SELECT 1 FROM GIC_HOGAR h WHERE h.HOG_CODIGO=r.HOGARCODIGO);
-- → 572.885  (51,2 % de 1.119.775)
```

Descartado que fuera un problema de formato — `TRIM` y `UPPER` no recuperan **ni una sola** fila:

```sql
SELECT COUNT(*) FROM GIC_N_RELACION_DT_PUNTO r
WHERE NOT EXISTS (SELECT 1 FROM GIC_HOGAR h WHERE h.HOG_CODIGO=r.HOGARCODIGO)
  AND EXISTS (SELECT 1 FROM GIC_HOGAR h WHERE UPPER(TRIM(h.HOG_CODIGO))=UPPER(TRIM(r.HOGARCODIGO)));
-- → 0
```

La explicación real es que existe `GIC_HOGAR_HISTORICO` con **2.505.938 códigos distintos**, y los supuestos
huérfanos están ahí:

```sql
SELECT COUNT(*) FROM GIC_N_RELACION_DT_PUNTO r
WHERE NOT EXISTS (SELECT 1 FROM GIC_HOGAR h WHERE h.HOG_CODIGO=r.HOGARCODIGO)
  AND EXISTS (SELECT 1 FROM GIC_HOGAR_HISTORICO x WHERE x.HOG_CODIGO=r.HOGARCODIGO);
-- → 572.881  (99,9993 % de los 572.885)

SELECT COUNT(*) FROM GIC_N_RELACION_DT_PUNTO r
WHERE NOT EXISTS (SELECT 1 FROM GIC_HOGAR h WHERE h.HOG_CODIGO=r.HOGARCODIGO)
  AND NOT EXISTS (SELECT 1 FROM GIC_HOGAR_HISTORICO x WHERE x.HOG_CODIGO=r.HOGARCODIGO);
-- → 4
```

**Solo 4 filas territoriales están realmente colgando.** Las otras 572.881 apuntan a hogares archivados.
Esto no es corrupción, pero sí es **deuda de modelo**: `GIC_N_RELACION_DT_PUNTO` no tiene FK y su universo de
referencia está partido en dos tablas sin ninguna declaración que lo diga. Cualquier consulta que haga
`JOIN GIC_HOGAR` pierde la mitad de las filas sin avisar.

### 3.5 Territorio incompleto — el bug histórico, cuantificado

```sql
SELECT COUNT(*) total,
 SUM(CASE WHEN IDDT        IS NULL THEN 1 ELSE 0 END) iddt_null,
 SUM(CASE WHEN IDDEPTOATEN IS NULL THEN 1 ELSE 0 END) depto_null,
 SUM(CASE WHEN IDPUNTOATEN IS NULL THEN 1 ELSE 0 END) punto_null,
 SUM(CASE WHEN IDMUNATEN   IS NULL THEN 1 ELSE 0 END) mun_null,
 SUM(CASE WHEN IDDT IS NULL OR IDDEPTOATEN IS NULL
            OR IDPUNTOATEN IS NULL OR IDMUNATEN IS NULL THEN 1 ELSE 0 END) alguno_null,
 SUM(CASE WHEN IDDT IS NULL AND IDDEPTOATEN IS NULL
            AND IDPUNTOATEN IS NULL AND IDMUNATEN IS NULL THEN 1 ELSE 0 END) todos_null
FROM GIC_N_RELACION_DT_PUNTO;
```

| Total | `IDDT` NULL | `IDDEPTOATEN` NULL | `IDPUNTOATEN` NULL | `IDMUNATEN` NULL | Alguno NULL | Todos NULL |
|---|---|---|---|---|---|---|
| 1.119.775 | **0** | 183 | 392 | 597 | **599 (0,053 %)** | **0** |

El patrón es una cascada: cuando falla, falla de derecha a izquierda (el municipio es lo que más falta, la DT
nunca falta). Ninguna fila está completamente vacía. **El bug histórico es real pero mínimo: 6 filas por cada
10.000.** Repetido con `TRIM` para descartar cadenas de solo espacios: mismo resultado, 599.

Combinaciones territoriales que no existen en el catálogo de puntos:

```sql
SELECT COUNT(*) FROM GIC_N_RELACION_DT_PUNTO r
WHERE r.IDDT IS NOT NULL AND r.IDDEPTOATEN IS NOT NULL
  AND r.IDPUNTOATEN IS NOT NULL AND r.IDMUNATEN IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM GIC_N_DT_PUNTOS_ATENCION p
        WHERE p.IDDT=r.IDDT AND p.IDDEPARTAMENTO=r.IDDEPTOATEN
          AND p.IDPUNTOATENCION=r.IDPUNTOATEN AND p.IDMUNICIPIO=r.IDMUNATEN);
-- → 44

SELECT COUNT(*) FROM GIC_N_RELACION_DT_PUNTO r WHERE r.IDPUNTOATEN IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM GIC_N_DT_PUNTOS_ATENCION p WHERE p.IDPUNTOATENCION=r.IDPUNTOATEN);
-- → 0
```

**44 filas** tienen una cuádrupla que no existe en el catálogo, pero **ningún punto de atención es inventado**:
el id de punto siempre existe, lo que no cuadra es su combinación con departamento o municipio.

**Hogares sin territorio:**

```sql
SELECT COUNT(*) FROM GIC_HOGAR h
WHERE NOT EXISTS (SELECT 1 FROM GIC_N_RELACION_DT_PUNTO r WHERE r.HOGARCODIGO=h.HOG_CODIGO);
-- → 555.975  (50,4 % de 1.102.858)
```

Todos los hogares son del mismo tipo de caracterización, así que no se explica por perfil:

```sql
SELECT h.TPOCRN_ID, COUNT(*) n,
  SUM(CASE WHEN EXISTS (SELECT 1 FROM GIC_N_RELACION_DT_PUNTO d
                        WHERE d.HOGARCODIGO=h.HOG_CODIGO) THEN 1 ELSE 0 END) con_territorio
FROM GIC_HOGAR h GROUP BY h.TPOCRN_ID;
-- → TPOCRN_ID=2 | 1.102.878 | 546.901   (única fila: todo el universo es tipo 2)
```

> **Sospecha, no dato:** la hipótesis más probable es que la captura de DT/punto se incorporó al flujo
> después de que ya existieran cientos de miles de hogares, y nunca se retropobló. No pude confirmarlo
> porque `GIC_N_RELACION_DT_PUNTO` no tiene columna de fecha de creación.

### 3.6 Duplicados

**Hogares — limpio.**

```sql
SELECT COUNT(*) codigos_duplicados FROM (
  SELECT HOG_CODIGO FROM GIC_HOGAR GROUP BY HOG_CODIGO HAVING COUNT(*)>1);
-- → 0
```

**Respuestas — limpio en PK, residual en la tripleta de negocio.**

```sql
SELECT COUNT(*) FROM (SELECT RXP_IDRESPUESTAXPERSONA FROM GIC_N_RESPUESTASENCUESTA
  GROUP BY RXP_IDRESPUESTAXPERSONA HAVING COUNT(*)>1);
-- → 0

SELECT COUNT(*) llaves, SUM(c) filas, MAX(c) max_rep FROM (
 SELECT HOG_CODIGO, PER_IDPERSONA, RES_IDRESPUESTA, COUNT(*) c
 FROM GIC_N_RESPUESTASENCUESTA
 GROUP BY HOG_CODIGO, PER_IDPERSONA, RES_IDRESPUESTA HAVING COUNT(*)>1);
-- → 21 llaves | 44 filas | máximo 4 repeticiones
```

**Miembros de hogar — residual.**

```sql
SELECT COUNT(*) llaves, SUM(c) filas FROM (
 SELECT HOG_CODIGO, PER_IDPERSONA, COUNT(*) c FROM GIC_MIEMBROS_HOGAR
 GROUP BY HOG_CODIGO, PER_IDPERSONA HAVING COUNT(*)>1);
-- → 26 llaves | 54 filas
```

**Personas — el hallazgo grave.**

```sql
SELECT COUNT(*) llaves_dup, SUM(c) filas_implicadas, MAX(c) max_repeticiones FROM (
  SELECT PER_TIPODOC, PER_NUMERODOC, COUNT(*) c FROM GIC_PERSONA
  WHERE PER_NUMERODOC IS NOT NULL
  GROUP BY PER_TIPODOC, PER_NUMERODOC HAVING COUNT(*)>1);
-- → 864.789 llaves | 2.016.957 filas | 5.437 repeticiones máximo
```

Sobre 7.757.438 personas: **26,0 % de las filas comparten documento con otra.** Distribución:

```sql
SELECT CASE WHEN c=2 THEN '2' WHEN c=3 THEN '3' WHEN c<=5 THEN '4-5'
            WHEN c<=10 THEN '6-10' WHEN c<=100 THEN '11-100' ELSE '>100' END rango,
       COUNT(*) llaves, SUM(c) filas
FROM (SELECT PER_TIPODOC, PER_NUMERODOC, COUNT(*) c FROM GIC_PERSONA
      WHERE PER_NUMERODOC IS NOT NULL
      GROUP BY PER_TIPODOC, PER_NUMERODOC HAVING COUNT(*)>1)
GROUP BY ... ORDER BY 3 DESC;
```

| Repeticiones | Llaves | Filas |
|---|---|---|
| 2 | 689.356 | 1.378.712 |
| 3 | 124.988 | 374.964 |
| 4–5 | 40.382 | 171.624 |
| 6–10 | 8.904 | 62.086 |
| 11–100 | 1.141 | 17.836 |
| **>100** | **18** | **11.735** |

Las 18 llaves con más de 100 repeticiones son casi con certeza valores centinela, no personas: al medir su
**forma** (sin exponer el valor) aparecen 34 llaves de 2 dígitos que acumulan 5.928 filas y 10 llaves de 1 dígito
que acumulan 1.666 filas.

Restringido a personas que **sí están caracterizadas** (son miembro de algún hogar), el problema no desaparece:

```sql
SELECT COUNT(*) llaves_dup, SUM(c) filas FROM (
 SELECT p.PER_TIPODOC, p.PER_NUMERODOC, COUNT(*) c FROM GIC_PERSONA p
 WHERE p.PER_NUMERODOC IS NOT NULL
   AND EXISTS (SELECT 1 FROM GIC_MIEMBROS_HOGAR m WHERE m.PER_IDPERSONA=p.PER_IDPERSONA)
 GROUP BY p.PER_TIPODOC, p.PER_NUMERODOC HAVING COUNT(*)>1);
-- → 281.056 llaves | 602.857 filas
```

### 3.7 Fechas imposibles

**Nacimiento:**

```sql
SELECT COUNT(*) total,
 SUM(CASE WHEN PER_FECHANACIMIENTO > SYSDATE THEN 1 ELSE 0 END) futura,
 SUM(CASE WHEN PER_FECHANACIMIENTO < DATE '1900-01-01' THEN 1 ELSE 0 END) antes_1900,
 SUM(CASE WHEN MONTHS_BETWEEN(SYSDATE,PER_FECHANACIMIENTO)/12 > 110 THEN 1 ELSE 0 END) mas_110,
 TO_CHAR(MIN(PER_FECHANACIMIENTO),'YYYY-MM-DD') f_min,
 TO_CHAR(MAX(PER_FECHANACIMIENTO),'YYYY-MM-DD') f_max
FROM GIC_PERSONA;
```

| Total | Futura | Antes de 1900 | Edad >110 | Mínima | Máxima |
|---|---|---|---|---|---|
| 7.757.438 | **1.390** | **140.962** | **148.491** | `0001-01-01` | `9999-10-20` |

Solo **1** persona tiene la fecha de nacimiento en NULL: el sistema prefiere una fecha basura a un nulo honesto.
De las imposibles, **6.079 corresponden a personas efectivamente caracterizadas**:

```sql
SELECT COUNT(*) FROM GIC_PERSONA p
WHERE (p.PER_FECHANACIMIENTO > SYSDATE OR p.PER_FECHANACIMIENTO < DATE '1900-01-01')
  AND EXISTS (SELECT 1 FROM GIC_MIEMBROS_HOGAR m WHERE m.PER_IDPERSONA=p.PER_IDPERSONA);
-- → 6.079
```

**Creación:**

```sql
SELECT TO_CHAR(USU_FECHACREACION,'YYYY') anio, COUNT(*) n FROM GIC_PERSONA
WHERE USU_FECHACREACION < DATE '2000-01-01'
GROUP BY TO_CHAR(USU_FECHACREACION,'YYYY') ORDER BY 2 DESC;
-- → 1900: 503.317 · 0026: 17 · 1969: 7
```

**503.317 personas (6,49 %) con fecha de creación en 1900** — un centinela clásico de "sin dato".
Los 17 registros del año **0026** y los 6 hogares equivalentes son casi seguramente `2026` mal tecleado o mal
parseado; la misma anomalía asoma en `_C`, cuyo `MIN(USU_FECHACREACION)` es `0026-04-25`.

Fuera de eso, la auditoría básica está sana — **0 usuarios de creación vacíos y 0 fechas nulas** en las cuatro
tablas centrales:

| Tabla | Filas | `USU_USUARIOCREACION` vacío | Fecha NULL | Fecha futura | Antes de 2010 |
|---|---|---|---|---|---|
| `GIC_HOGAR` | 1.102.875 | 0 | 0 | 0 | 6 |
| `GIC_PERSONA` | 7.757.438 | 0 | 0 | 0 | 503.342 |
| `GIC_MIEMBROS_HOGAR` | 3.377.039 | 0 | 0 | 0 | 0 |
| `GIC_N_RESPUESTASENCUESTA` | 3.843.797 | 0 | 0 | 0 | 0 |

En `GIC_N_RESPUESTASENCUESTA` tampoco hay `RES_IDRESPUESTA` ni `INS_IDINSTRUMENTO` nulos (0 y 0).

### 3.8 Trazabilidad de autoría

```sql
SELECT COUNT(*) filas, COUNT(DISTINCT h.USU_USUARIOCREACION) usuarios_distintos
FROM GIC_HOGAR h
WHERE NOT EXISTS (SELECT 1 FROM GIC_USUARIO u
                  WHERE UPPER(TRIM(u.USU_USUARIO))=UPPER(TRIM(h.USU_USUARIOCREACION)));
-- → 1.077.712 filas | 9.424 usuarios distintos
```

Sobre 1.102.878 hogares: **97,7 % no se puede atribuir a un usuario registrado**. `GIC_USUARIO` tiene
8.172 usuarios con 8.172 logins distintos, pero en `GIC_HOGAR` aparecen 9.424 cadenas creadoras que no cruzan.

Descartado que el campo guarde otra cosa (documento, id o correo):

```sql
SELECT COUNT(*) FROM GIC_HOGAR h WHERE EXISTS (SELECT 1 FROM GIC_USUARIO u
  WHERE TO_CHAR(u.USU_DOCUMENTO)=TRIM(h.USU_USUARIOCREACION));            -- 0
SELECT COUNT(*) FROM GIC_HOGAR h WHERE EXISTS (SELECT 1 FROM GIC_USUARIO u
  WHERE TO_CHAR(u.USU_IDUSUARIO)=TRIM(h.USU_USUARIOCREACION));            -- 0
SELECT COUNT(*) FROM GIC_HOGAR h WHERE EXISTS (SELECT 1 FROM GIC_USUARIO u
  WHERE UPPER(TRIM(u.USU_CORREOELECTRONICO))=UPPER(TRIM(h.USU_USUARIOCREACION))); -- 0
```

El campo es siempre alfanumérico (1.102.878 de 1.102.878; ni una cadena de solo dígitos, ni un correo), o sea
que **sí es un login** — simplemente ya no existe en la tabla de usuarios. La columna numérica tampoco salva:

```sql
SELECT COUNT(*) FROM GIC_HOGAR h
WHERE NOT EXISTS (SELECT 1 FROM GIC_USUARIO u WHERE u.USU_IDUSUARIO=h.USU_IDUSUARIO);
-- → 1.099.482  (99,7 %)
```

En respuestas el mismo problema afecta a **2.752.619 filas (71,6 %)** con 4.433 creadores distintos no registrados.

> **Sospecha, no dato:** lo más probable es que `GIC_USUARIO` se haya purgado de cuentas dadas de baja
> (tiene la columna `USU_DADODEBAJA`) sin conservar histórico. No pude confirmarlo porque no hay tabla
> `GIC_USUARIO_HIS` en el esquema.

### 3.9 Calidad de la identificación

```sql
SELECT COUNT(*) total,
 SUM(CASE WHEN PER_NUMERODOC IS NULL THEN 1 ELSE 0 END) doc_null,
 SUM(CASE WHEN PER_TIPODOC   IS NULL THEN 1 ELSE 0 END) tipodoc_null
FROM GIC_PERSONA;
-- → 7.757.422 | 11.952 | 1.126.613

SELECT COUNT(*) total,
 SUM(CASE WHEN LENGTH(PER_NUMERODOC) <= 4 THEN 1 ELSE 0 END) doc_muy_corto,
 SUM(CASE WHEN NOT REGEXP_LIKE(PER_NUMERODOC,'^[0-9]+$') THEN 1 ELSE 0 END) doc_no_numerico
FROM GIC_PERSONA WHERE PER_NUMERODOC IS NOT NULL;
-- → 7.745.489 | 8.535 | 7.570
```

| Problema | Filas | % de 7.757.422 |
|---|---|---|
| Sin tipo de documento | **1.126.613** | 14,52 % |
| Sin número de documento | 11.952 | 0,154 % |
| Número de ≤4 caracteres | 8.535 | 0,110 % |
| Número no numérico | 7.570 | 0,098 % |

El 14,5 % sin tipo de documento es lo relevante: un número sin tipo no identifica unívocamente a nadie, y es
precisamente lo que alimenta el hallazgo de duplicados.

### 3.10 Catálogo

```sql
SELECT (SELECT COUNT(*) FROM GIC_N_PREGUNTAS)        preguntas,   -- 1.108
       (SELECT COUNT(*) FROM GIC_N_RESPUESTAS)       respuestas,  -- 3.686
       (SELECT COUNT(*) FROM GIC_N_INSTRUMENTOXPREG) inst_preg,   --   903
       (SELECT COUNT(*) FROM GIC_N_INSTRUMENTOXRESP) inst_resp    -- 3.533
FROM dual;
```

**Elementos que no pertenecen a ningún instrumento** (no se pueden escribir), desglosados por bandera de activo:

```sql
SELECT p.PRE_ACTIVA, COUNT(*) FROM GIC_N_PREGUNTAS p
WHERE NOT EXISTS (SELECT 1 FROM GIC_N_INSTRUMENTOXPREG i WHERE i.PRE_IDPREGUNTA=p.PRE_IDPREGUNTA)
GROUP BY p.PRE_ACTIVA;
-- → SI: 188 · NO: 17    (total 205 de 1.108 = 18,5 %)

SELECT r.RES_ACTIVA, COUNT(*) FROM GIC_N_RESPUESTAS r
WHERE NOT EXISTS (SELECT 1 FROM GIC_N_INSTRUMENTOXRESP i WHERE i.RES_IDRESPUESTA=r.RES_IDRESPUESTA)
GROUP BY r.RES_ACTIVA;
-- → SI: 116 · NO: 37    (total 153 de 3.686 = 4,2 %)
```

**188 preguntas y 116 respuestas están marcadas `ACTIVA='SI'` pero no pertenecen a ningún instrumento.**
Esa contradicción — activa pero inescribible — es el hallazgo de catálogo más accionable.

**Huérfanos y textos duplicados:**

```sql
SELECT COUNT(*) FROM GIC_N_PREGUNTAS p WHERE NOT EXISTS
  (SELECT 1 FROM GIC_N_RESPUESTAS r WHERE r.PRE_IDPREGUNTA=p.PRE_IDPREGUNTA);   -- 17
SELECT COUNT(*) FROM GIC_N_RESPUESTAS r WHERE NOT EXISTS
  (SELECT 1 FROM GIC_N_PREGUNTAS p WHERE p.PRE_IDPREGUNTA=r.PRE_IDPREGUNTA);    -- 3

SELECT COUNT(*) preguntas_afectadas, SUM(opciones_dup) FROM (
 SELECT PRE_IDPREGUNTA, COUNT(*) opciones_dup FROM (
   SELECT PRE_IDPREGUNTA, UPPER(TRIM(RES_RESPUESTA)) txt, COUNT(*) c
   FROM GIC_N_RESPUESTAS WHERE TRIM(RES_RESPUESTA) IS NOT NULL
   GROUP BY PRE_IDPREGUNTA, UPPER(TRIM(RES_RESPUESTA)) HAVING COUNT(*)>1)
 GROUP BY PRE_IDPREGUNTA);
-- → 2 preguntas afectadas | 2 textos duplicados
```

**Solo 2 preguntas** de 1.108 tienen texto de opción duplicado: la **30** (el caso conocido de
'Cédula de ciudadanía / Contraseña', con 4 opciones bajo un mismo texto) y la **89** (2 opciones).
El problema del catálogo **no** es la duplicación de opciones: está prácticamente contenido a ese único caso.

En cambio, a nivel de enunciado de pregunta sí hay redundancia:

```sql
SELECT COUNT(*) grupos, SUM(c) preguntas FROM (
 SELECT UPPER(TRIM(PRE_PREGUNTA)) txt, COUNT(*) c FROM GIC_N_PREGUNTAS
 WHERE PRE_PREGUNTA IS NOT NULL GROUP BY UPPER(TRIM(PRE_PREGUNTA)) HAVING COUNT(*)>1);
-- → 123 grupos | 344 preguntas
```

**344 preguntas (31,0 % de 1.108) comparten enunciado literal con otra.** Es esperable en parte — la misma
pregunta aparece en varios capítulos o perfiles — pero obliga a desambiguar por id en cualquier reporte.

### 3.11 `GIC_N_RESPUESTASENCUESTA_C`: no es una gemela, es el archivo

Esta era una incógnita del enunciado. La respuesta es clara: **`_C` es el almacén histórico y es disjunta de la
tabla principal.** No es una copia ni una gemela.

| Métrica | `GIC_N_RESPUESTASENCUESTA` | `GIC_N_RESPUESTASENCUESTA_C` |
|---|---|---|
| Filas | 3.843.797 | **498.828.649** (130×) |
| Hogares distintos | **27.363** | ~2.012.416 (estadísticas de 2024-05-16) |
| Rango de `RXP_IDRESPUESTAXPERSONA` | 3.117.540 – 481.172.308 | 3.082 – **2.610.882.146.864.345** |
| Rango de `USU_FECHACREACION` | 2015-05-02 – hoy | **0026-04-25** – hoy |
| PK / constraints | `RESTONINS` (único) + FK a hogar | **ninguna** |
| Tamaño | — | 36,3 GB + 180,6 GB de índices |

**Prueba de disyunción** (muestras de 300, usando los índices por `HOG_CODIGO`):

```sql
-- Hogares con respuestas en la tabla principal: ¿están también en _C?
SELECT COUNT(*) muestra, SUM(CASE WHEN EXISTS (SELECT 1 FROM GIC_N_RESPUESTASENCUESTA_C c
       WHERE c.HOG_CODIGO=s.HOG_CODIGO) THEN 1 ELSE 0 END) tambien_en_C
FROM (SELECT DISTINCT HOG_CODIGO FROM GIC_N_RESPUESTASENCUESTA
      WHERE HOG_CODIGO IS NOT NULL FETCH FIRST 300 ROWS ONLY) s;
-- → 300 | 0      (ninguno)

-- Hogares MIGRADOAHISTORICO: ¿tienen sus respuestas en _C?
SELECT COUNT(*) muestra, SUM(CASE WHEN EXISTS (SELECT 1 FROM GIC_N_RESPUESTASENCUESTA_C c
       WHERE c.HOG_CODIGO=s.HOG_CODIGO) THEN 1 ELSE 0 END) con_respuestas_en_C
FROM (SELECT HOG_CODIGO FROM GIC_HOGAR WHERE ESTADO='MIGRADOAHISTORICO'
      FETCH FIRST 300 ROWS ONLY) s;
-- → 300 | 300    (todos)
```

**0 de 300 activos están en `_C`; 300 de 300 migrados sí lo están.** El mecanismo es un movimiento, no una copia,
y lo confirma el estado de los hogares y el job correspondiente:

```sql
SELECT NVL(ESTADO,'(null)') estado, COUNT(*) n FROM GIC_HOGAR GROUP BY ESTADO ORDER BY 2 DESC;
```

| Estado | Hogares | % |
|---|---|---|
| `MIGRADOAHISTORICO` | **1.037.554** | 94,08 % |
| `APLAZADA` | 38.069 | 3,45 % |
| `ANULADA` | 16.427 | 1,49 % |
| `ERROR` | **8.958** | 0,81 % |
| `ACTIVA` | 1.479 | 0,13 % |
| `CERRADA` | 230 | 0,02 % |
| `CERRADA_APP_MOVIL` | 106 | 0,01 % |
| `MANUAL` | 50 | — |
| `PRUEBA` | 4 | — |
| `MIGRADOHISTORICO` | **1** | — |

Dos detalles menores pero reales: hay **8.958 hogares en estado `ERROR`** (0,81 %) que nadie ha reprocesado, y
existe **1 hogar con el estado mal escrito** (`MIGRADOHISTORICO` sin la A), lo que confirma que el estado es
texto libre sin dominio declarado.

Coherentemente, **1.075.511 hogares (97,5 %) no tienen ninguna respuesta en la tabla principal** — están todas
en `_C`. Y todas las respuestas vivas pertenecen a un único instrumento (`INS_IDINSTRUMENTO = 1`, 3.843.794 filas).

**Consecuencia para la migración:** cualquier extracción histórica de respuestas debe leer `_C`, no la tabla
principal. La tabla principal solo contiene la ventana de trabajo activa (27.363 hogares).

### 3.12 Sobre-indexación de `_C`

```sql
SELECT
 (SELECT ROUND(SUM(bytes)/1024/1024/1024,1) FROM dba_segments
   WHERE owner='RNIENTREVISTA' AND segment_name='GIC_N_RESPUESTASENCUESTA_C') tabla_gb,
 (SELECT ROUND(SUM(s.bytes)/1024/1024/1024,1) FROM dba_segments s
   WHERE s.owner='RNIENTREVISTA' AND s.segment_name IN
     (SELECT index_name FROM all_indexes WHERE owner='RNIENTREVISTA'
      AND table_name='GIC_N_RESPUESTASENCUESTA_C')) indices_gb,
 (SELECT COUNT(*) FROM all_indexes WHERE owner='RNIENTREVISTA'
   AND table_name='GIC_N_RESPUESTASENCUESTA_C') n_indices
FROM dual;
-- → 36,3 GB tabla | 180,6 GB índices | 13 índices
```

**Los índices pesan 5,0× la tabla.** Siete de los trece encabezan por `HOG_CODIGO` y son prefijos unos de otros:

| Índice | GB | Columnas |
|---|---|---|
| `IDX$$_5D350001` | 25,1 | `HOG_CODIGO, USU_FECHACREACION` |
| `IDX_HOGAR_C3` | 21,7 | `HOG_CODIGO, PER_IDPERSONA, RES_IDRESPUESTA` |
| `IDX_HOGAR_C1` | 19,7 | `HOG_CODIGO, PER_IDPERSONA` |
| `IDX_HOGAR_C2` | 18,5 | `HOG_CODIGO, RES_IDRESPUESTA` |
| `IDX_HOGAR_C` | 16,5 | `HOG_CODIGO` |
| `IDX_HOGAR_C6` | 16,5 | `SYS_NC00012$` (columna virtual) |
| `IDX_HOGAR_C7` | 15,5 | `PER_IDPERSONA, RES_IDRESPUESTA, USU_FECHACREACION` |
| `RXP_IDRESPUESTAXPERSONA_IDX` | 10,9 | `RXP_IDRESPUESTAXPERSONA` |
| `IDX_TEXTO_RES` | 10,7 | `RES_IDRESPUESTA, RXP_TEXTORESPUESTA` |
| `IDX_HOGAR_C5` | 10,3 | `SYS_NC00011$` |
| `IDX_HOGAR_C4` | 8,1 | `RES_IDRESPUESTA` |
| `IDX_RESC_1` | 3,8 | `RXP_TEXTORESPUESTA` |
| `IDX$$_5D350002` | 3,3 | `SYS_NC00010$` |

`IDX_HOGAR_C` (16,5 GB) es prefijo exacto de `IDX_HOGAR_C1`, que a su vez lo es de `IDX_HOGAR_C3`:
al menos 36 GB son redundantes por construcción. El esquema completo ocupa **500,3 GB**, de los cuales
`_C` y sus índices son **216,9 GB (43,4 %)**.

### 3.13 Estadísticas del optimizador

```sql
SELECT table_name, num_rows, TO_CHAR(last_analyzed,'YYYY-MM-DD') analizada, stale_stats
FROM all_tab_statistics WHERE owner='RNIENTREVISTA' AND object_type='TABLE'
  AND table_name IN ('GIC_HOGAR','GIC_PERSONA','GIC_MIEMBROS_HOGAR','GIC_N_RELACION_DT_PUNTO',
   'GIC_N_RESPUESTASENCUESTA','GIC_N_RESPUESTASENCUESTA_C','GIC_HOGAR_HISTORICO');
```

| Tabla | `num_rows` (estadística) | Real medido | Desvío | Analizada | Stale |
|---|---|---|---|---|---|
| `GIC_N_RESPUESTASENCUESTA_C` | 426.963.675 | 498.828.649 | **−14,4 %** | 2024-05-16 | YES |
| `GIC_PERSONA` | 6.430.300 | 7.757.438 | **−17,1 %** | 2024-05-16 | YES |
| `GIC_MIEMBROS_HOGAR` | 1.924.920 | 3.377.039 | **−43,0 %** | 2024-05-16 | YES |
| `GIC_N_RESPUESTASENCUESTA` | 3.472.565 | 3.843.797 | −9,7 % | 2024-05-16 | YES |
| `GIC_HOGAR_HISTORICO` | 2.028.731 | 2.505.938 | −19,0 % | 2024-05-16 | YES |
| `GIC_N_RELACION_DT_PUNTO` | 925.205 | 1.119.775 | −17,4 % | 2024-05-16 | YES |
| `GIC_HOGAR` | 991.524 | 1.102.878 | −10,1 % | 2026-03-13 | YES |

`GIC_MIEMBROS_HOGAR` está subestimada en **43 %**. Con esa desviación el optimizador elige planes con datos de
hace más de dos años. Las estadísticas de columna de `_C` son de la misma fecha, lo que explica que su
`num_distinct` de `HOG_CODIGO` (2.012.416) sea aproximado y no exacto.

---

## 4. Lo que NO pude medir, y por qué

1. **Si los 2.016.957 documentos duplicados son personas realmente distintas.** Distinguir un duplicado genuino
   de dos personas homónimas requiere comparar nombres y fechas de nacimiento, es decir, leer PII. Fuera de
   alcance por la regla de no extracción. La cifra reportada es de **filas que comparten documento**, no de
   "personas duplicadas confirmadas". El sub-conteo restringido a miembros de hogar (602.857 filas) es la cota
   inferior más honesta.
2. **El conteo exacto de hogares distintos en `_C`.** Un `COUNT(DISTINCT HOG_CODIGO)` sobre 498,8 M de filas es
   prohibitivo: un simple `MIN/MAX` sobre esa tabla tardó **224 segundos**. Usé el `num_distinct` del diccionario
   (2.012.416), que es de 2024-05-16 y por tanto está subestimado en el mismo orden que el resto de las
   estadísticas.
3. **Si `_C` contiene absolutamente todas las respuestas históricas.** Lo verifiqué por muestreo (300 hogares
   activos + 300 migrados, resultado limpio en ambas direcciones), no de forma exhaustiva. Una verificación
   total exigiría un anti-join completo entre 498 M y 2,5 M de filas.
4. **Validez semántica de las respuestas.** No verifiqué si las respuestas guardadas respetan la lógica de salto
   del instrumento (p. ej. respuestas de embarazo en personas de sexo masculino). Requiere cruzar el motor de
   reglas con los datos y es un proyecto en sí mismo.
5. **Si las 811 clases Java inválidas se usan.** Son dependencias de librerías (`gson`, `slf4j`) con errores
   `ORA-29521` de referencia no encontrada. Determinar si algún flujo vivo las invoca exige inspeccionar el
   código PL/SQL que las llama, no el diccionario.
6. **La causa raíz de los 1.718 fallos de los jobs.** `ALL_SCHEDULER_JOB_RUN_DETAILS` daría el error exacto,
   pero no lo consulté para no ampliar el alcance; el conteo de fallos ya sustenta el hallazgo.
7. **Contraste contra una fuente autoritativa.** No comparé personas ni hogares contra RUV, Registraduría o DANE.
   Todo lo medido es consistencia **interna** del esquema.
8. **`GIC_ACTUALIZAR_RESPUESTA` (178,7 M de filas) y `GIC_ENCUESTA_MOVIL` (43,9 M).** Tablas grandes sin PK que
   no perfilé por límite de tiempo; quedan como frente abierto.
9. **Fragmentación real de los índices de `_C`.** Medí tamaño de segmento, no espacio desperdiciado; eso
   requeriría `VALIDATE STRUCTURE`, que no es una operación de solo lectura pura.

---

## 5. Plan sugerido post-migración

En orden de prioridad. Ninguna acción es destructiva por sí misma; **todas requieren respaldo previo y ventana
acordada**, y las de limpieza masiva deben ejecutarse por lotes con verificación intermedia.

**Fase 1 — Contención (bajo esfuerzo, alto retorno, sin tocar datos)**

1. **Recolectar estadísticas** (`DBMS_STATS.GATHER_SCHEMA_STATS` sobre `RNIENTREVISTA`, ventana de baja carga).
   Es la acción con mejor relación beneficio/riesgo del plan: no altera un solo dato de negocio y corrige
   desviaciones de hasta 43 %.
2. **Auditar los 4 jobs con >1.400 fallos**: revisar `ALL_SCHEDULER_JOB_RUN_DETAILS`, y arreglarlos o
   deshabilitarlos. Hoy fallan a diario sin que nadie se entere.
3. **Recompilar los 53 objetos inválidos** (`UTL_RECOMP`) para separar lo recuperable de lo definitivamente
   muerto. Documentar cuáles referencian tablas inexistentes.

**Fase 2 — Higiene acotada (cientos de filas, riesgo bajo)**

4. Completar las **599 filas territoriales incompletas** desde `GIC_N_DT_PUNTOS_ATENCION` vía el punto de
   atención, y revisar las **44 combinaciones inexistentes**.
5. Depurar los huérfanos residuales: **270** miembros sin persona, **211** respuestas con persona inexistente,
   **543** respuestas sin hogar, **4** filas territoriales colgando, **26** duplicados persona-hogar,
   **21** respuestas repetidas. Total: menos de 1.100 filas.
6. Reprocesar o cerrar los **8.958 hogares en estado `ERROR`** y normalizar el hogar con `MIGRADOHISTORICO`.
7. Depurar el catálogo: resolver las **188 preguntas y 116 respuestas activas sin instrumento** (vincular o
   desactivar), los **17** sin respuestas y las **3** huérfanas.

**Fase 3 — Corrección de datos de negocio (requiere decisión de negocio)**

8. **Fechas de nacimiento imposibles**: empezar por las **6.079** de personas caracterizadas (las que afectan
   atención real), luego el resto de las 142.352. Definir con negocio qué se hace cuando no hay dato recuperable:
   NULL explícito, no un centinela nuevo.
9. **Fecha de creación 1900**: sustituir el centinela por NULL en las **503.317** filas, o documentar formalmente
   que 1900 significa "desconocido" para que los reportes lo excluyan.
10. **Tipo de documento ausente** (1.126.613 filas, 14,5 %): inferir desde el número y la edad donde sea posible;
    es prerrequisito del punto 11.

**Fase 4 — Deduplicación e imposición de restricciones (alto esfuerzo, alto riesgo, hacer al final)**

11. **Deduplicar personas.** Requiere criterio de negocio escrito antes de tocar nada: qué fila sobrevive, qué
    pasa con las respuestas de las descartadas, cómo se registra la fusión. Empezar por las **18 llaves con
    >100 repeticiones** (11.735 filas), que son casi seguro centinelas y no personas, y por las **281.056 llaves
    entre personas caracterizadas**. Ejecutar por lotes, reversible, con ledger de fusiones.
12. **Crear la PK de `GIC_PERSONA`** en `PER_IDPERSONA` y el índice único en (tipo, número de documento) una vez
    deduplicado. Sin esto, el punto 11 se deshace solo con el tiempo.
13. **Declarar las FK que faltan**: `GIC_MIEMBROS_HOGAR → GIC_PERSONA`, `GIC_N_RESPUESTASENCUESTA → GIC_PERSONA`,
    `GIC_N_RELACION_DT_PUNTO → GIC_HOGAR` (resolviendo antes la partición hogar/histórico). Validar y rehabilitar
    `GIC_REL_PARENGENTOARBGEN`.
14. **`CHECK` de rango** en `PER_FECHANACIMIENTO` (entre 1900 y `SYSDATE`) y dominio cerrado para
    `GIC_HOGAR.ESTADO`.

**Fase 5 — Optimización de almacenamiento (independiente, se puede hacer en paralelo)**

15. Analizar el uso real de los **13 índices de `_C`** (180,6 GB) con `V$OBJECT_USAGE` durante un ciclo completo
    de reportería, y consolidar los redundantes por prefijo. Hay al menos 36 GB recuperables sin perder ninguna
    ruta de acceso.

**Lo que NO recomiendo tocar:** el mecanismo de archivado hacia `_C` y `GIC_HOGAR_HISTORICO`. Es feo y no está
declarado en el modelo, pero funciona de forma consistente (verificado: 300/300 en ambas direcciones) y sostiene
el 43 % del volumen del esquema. Documentarlo vale más que rediseñarlo.

---

## 6. Resumen de cifras de referencia

| Objeto | Filas (medido 2026-07-28) |
|---|---|
| `GIC_PERSONA` | 7.757.438 |
| `GIC_N_RESPUESTASENCUESTA_C` | 498.828.649 |
| `GIC_N_RESPUESTASENCUESTA` | 3.843.797 |
| `GIC_MIEMBROS_HOGAR` | 3.377.039 |
| `GIC_HOGAR_HISTORICO` | 2.505.938 |
| `GIC_N_RELACION_DT_PUNTO` | 1.119.775 |
| `GIC_HOGAR` | 1.102.878 |
| `GIC_N_RESPUESTAS` (catálogo) | 3.686 |
| `GIC_N_PREGUNTAS` (catálogo) | 1.108 |
| `GIC_USUARIO` | 8.172 |
| **Tamaño total del esquema** | **500,3 GB** |
