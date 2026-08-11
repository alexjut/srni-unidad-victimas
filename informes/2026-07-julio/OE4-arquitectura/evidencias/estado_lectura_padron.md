# Lectura del padrón real — estado y camino

> **Fecha:** 2026-07-28 · **Estado: NO IMPLEMENTADO.** La APK sigue buscando contra el
> mock. Este documento existe para que el siguiente que lo retome no empiece por donde
> empezamos nosotros — que resultó ser un callejón.

---

> ## ⚠️ CORRECCIÓN — 2026-08-11
>
> **Dos afirmaciones de este documento son FALSAS.** Se dejan tal cual abajo
> porque es un informe entregado y su historia no se reescribe, pero **no deben
> usarse**:
>
> | Lo que dice el documento | Lo verificado el 11-ago contra producción |
> |---|---|
> | «ni esa tabla ni ese dblink existen» | **`INH_REPORTE_GAVE` SÍ EXISTE: 1.832 filas** |
> | «`CONSULTAMODELO110` no está entre los dblinks» | **SÍ está**, y es alcanzable |
>
> La consulta que lo demuestra, desde `RNIENTREVISTA@30.0.1.9/ENTREVISTARN`:
>
> ```sql
> SELECT COUNT(*) FROM rnientrevista.inh_reporte_gave@consultamodelo110;  -- 1.832
> ```
>
> `CONSULTAMODELO110` y `DBL_RNIENTREVISTA` van ambos a la base **MODELO**. Ojo con
> `OPEN_LINKS=4`: cada dblink abre su propia conexión o sale `ORA-02020`.
>
> **Por qué importa:** el documento se escribió para evitar que alguien perdiera
> tiempo en un callejón, y acabó creando otro — mandando a descartar una tabla que
> sí está. Se desmintió el 4-ago y la corrección no había llegado hasta acá.
>
> **Esto no cambia la conclusión de fondo del documento.** El padrón operativo se
> resolvió por otra vía —`GIC_PERSONA` + el universo del RUV, cargados el 1 y el
> 6-ago— y hoy está en producción con 5.926.005 y 12.009.492 filas. Lo que cambia
> es que `INH_REPORTE_GAVE` vuelve a ser una fuente que se puede mirar, no una que
> se dio por inexistente.

---

## El callejón: la referencia que teníamos era falsa

El proyecto arrastraba una nota de referencia que situaba el padrón en
`RNIENTREVISTA.INH_REPORTE_GAVE@CONSULTAMODELO110`, con una lista de columnas
(`HOG_CODIGO`, `PER_IDPERSONA`, `PNOMBRE_1`, `P1541..P1655`…).

**Verificado contra producción el 28-jul: ni esa tabla ni ese dblink existen.**

- Objetos `INH_*` en el esquema: **25**, todas de *reportes de entrevistas*
  (`INH_REP_RESPUESTAENCUESTA`, `INH_MIEMBROS_SAAH`, `INH_RESPUESTAS_HOGAR_RURAL`…).
  Ninguna es un padrón de personas.
- Lo único con "GAVE" en el nombre de todo el esquema es el procedure
  `SP_CONSTANCIA_GAVE`.
- `CONSULTAMODELO110` no está entre los dblinks.

La nota se corrigió. **No usar aquella estructura de columnas para nada.**

## Lo que sí hay — medido

Dblinks desde `RNIENTREVISTA@30.0.1.9/ENTREVISTARN`:

| dblink | Host | Estado |
|---|---|---|
| **`DBL_VIVANTO`** | VIVANTO | ✅ **ALCANZABLE** — el camino probable al RUV |
| `CONSULTAATENCION` | ATENCION | ✅ alcanzable |
| `DBL_RNIENTREVISTA` | MODELO | el que usa `SP_CONSTANCIA_GAVE` para `AP_GEOGRAFIA` |
| `CONSULTACARACT` | RNI | ❌ `ORA-01017` credenciales inválidas |
| `DB_PRE` | fuentes | ❌ `ORA-01017` |

Al otro lado de `DBL_VIVANTO` hay tres esquemas con pinta de servir:

- **`MODELOINTEGRADO`** — `MI_ESTADOPERSONAS`, `MI_ESTADOVICTIMA`, `MI_TIPODOCUMENTO`,
  `MI_PERSONAS_CONTACTO`, `MI_PERSONAS_FUENTES`, `MI_PERSONAS_SOPORTES`.
  ⚠️ Ojo: buena parte de este esquema son tablas `DMRS_*`, que son **metadatos de Oracle
  Data Modeler**, no datos. No confundir el modelo con el padrón.
- **`RNIPAQUETES`** — `PRY_PERSONAS`, `GIC_REP_PERSONA_*` (con fecha en el nombre: son
  cortes históricos), `M_REP_AHE_PERSONAS`.
- **`ADMINUSUARIOS`** — `TM_PERSONA`, `TM_IDPERSONA_NUEVOS`.

## Lo que el contrato exige (y por qué no se puede improvisar)

`apps/victimas/repository/base.py` ya define la interfaz completa, y no pide solo un
nombre y un documento. `VictimaResumen` exige:

| Campo | Dificultad |
|---|---|
| identificación, nombres, fecha nac., género | mecánico |
| **`estado_ruv`** (INCLUIDO / NO_INCLUIDO / EN_PROCESO / EXCLUIDO) | semántica de negocio |
| **`habilitado_para_caracterizacion`** | regla de negocio, no una columna |
| `pertenencia_etnica`, `pueblo_indigena` | catálogo a homologar |
| `discapacidad`, `tipo_discapacidad` | catálogo a homologar |
| **`hechos_victimizantes`** (lista, con fecha y municipio) | otra tabla, otra relación |
| `municipio_residencia_codigo` (DIVIPOLA) | ojo: aquí también aplica lo del cero a la izquierda |

Improvisar el mapeo de `estado_ruv` o de `habilitado_para_caracterizacion` sería peor que
no tenerlo: el encuestador decide **a quién caracteriza** con ese dato.

---

## 🔑 Hallazgo del 29-jul: el RUV NO se consulta por tabla, se consulta por servicio

Se recorrió `DBL_VIVANTO` entero buscando el padrón. **No está.** Lo que hay:

**1. El Modelo Integrado está diseñado pero VACÍO.** `MODELOINTEGRADO.MI_PERSONAS`
tiene exactamente la estructura que pide nuestro contrato —`PER_TIPODOC`,
`PER_DOCUMENTO`, nombres, `PER_FECHANACIMIENTO`, `PER_SEXO`, **`PER_ETNIA`,
`PER_PUEBLO`, `PER_RESGUARDO`, `PER_CONSEJO_COMUNITARIO`, `PER_DISCAPACIDAD`,
`PER_DISC_DESCRI`**— y está **a 0 filas**. Igual `MI_HECHOSVICTIM` y
`MI_CARACTERIZACION`. Verificado con `COUNT(*)` real, no con la estadística del
optimizador (que además está congelada desde 2024-05-16).

De todas las `MI_*` solo tienen datos los **catálogos** (`MI_DIVIPOLA` 1.123,
`MI_TIPODOCUMENTO` 18, `MI_DEPARTAMENTO` 33…) y **`MI_UBICACION_ULTIMA`, con
7.767.010 filas** — que es del mismo orden que las 7.757.438 personas de
`GIC_PERSONA`. O sea: el modelo existe, alguien pobló la ubicación, y el resto
nunca se llenó.

**2. Las tablas grandes de VIVANTO son auditoría y cortes, no padrón:**

| Tabla | Filas | Qué es |
|---|---:|---|
| `AUDITORIAVIVANTOPROD.WS_AUDITORIA` | 378.870.362 | auditoría de web services |
| `AUDITORIAVIVANTOPROD.AU_CONSULTA_INDIVIDUAL_RUV` | 375.533.381 | **auditoría de consultas al RUV** |
| `AUDITORIAVIVANTOPROD.AU_CONSULTA_WEB_SERVICES` | 103.258.515 | idem, con `ID_APLICACION` |
| `RNIPAQUETES.M_CARACT_TABLA_RA_PER*` | ~10 M | cortes de caracterización |
| `RNIPAQUETES.CARACT_EVENTOS_VICTIMIZANTES*` | ~10 M | **hechos victimizantes** (útil aparte) |

`AU_CONSULTA_INDIVIDUAL_RUV` solo tiene `USUARIO`, `TIPO`, `CRITERIO1/2`, `IP`: es el
registro de **quién consultó qué**. 375 millones de consultas individuales al RUV, y
ninguna tabla de RUV que consultar.

**Y no existe ninguna tabla con "PADRON" o "RUV" en el nombre con datos**, en ningún
esquema alcanzable.

### Qué significa

**El padrón del RUV se sirve por un servicio (web service), no por una tabla.** Nuestro
`DBL_VIVANTO` llega a la auditoría, a los reportes y a los catálogos — no al registro.

⇒ **`OracleVictimaRepository` probablemente no debe ser un repositorio Oracle.** El
contrato `VictimaRepository` está bien y no cambia (por eso se diseñó como interfaz),
pero su implementación sería un **cliente HTTP del servicio de consulta del RUV**, y
convendría que se llamara `RuvServiceVictimaRepository` o similar.

### Lo que hace falta pedir (no se puede deducir)

1. **Endpoint del servicio de consulta individual del RUV** y su contrato (WSDL/OpenAPI).
2. **Credenciales / `ID_APLICACION`** para SICAV — la auditoría muestra que cada
   aplicación consumidora tiene el suyo.
3. Confirmar si ese servicio devuelve etnia, discapacidad y hechos victimizantes, o si
   los hechos hay que sacarlos aparte de `CARACT_EVENTOS_VICTIMIZANTES`.

**Esto ya no es trabajo de descubrimiento técnico: es una gestión.** Sin el endpoint y
las credenciales no hay nada que implementar, y ninguna cantidad de exploración de la
base lo va a resolver.

---

## Medición del 29-jul: los cortes NO sirven como fuente del padrón

Se evaluaron los candidatos con volumen. Ninguno alcanza:

| Corte | Filas | Veredicto |
|---|---:|---|
| `RNIPAQUETES.M_CARACT_TABLA_RA_PER` | 9.961.503 | ❌ **no tiene documento ni nombres**. Sus llaves son `CONS_PERONA` *(sic)* e `ID_PERSONA_CARACT`, ids internos. Trae `ESTADO_RUV`, `PERT_ETNICA`, `DISCAP`, `F_NACIMIENTO`, `GENERO_HOM` — buenos atributos, pero **no se puede buscar por cédula** |
| `RNIPAQUETES.CARACT_EVENTOS_VICTIMIZANTES` | — | ❌ **bloque corrupto** (ORA-01578, ver adenda del veredicto). Las hermanas `_1`, `1`, `2` sí se leen (~10 M) |
| `RNIPAQUETES.PRY_PERSONAS` | **2** | ❌ estructura ideal —documento, tipo, nombres, fecha nac., género, etnia, discapacidad, DANE— pero **está vacía**: es una tabla de proyecto |
| `ADMINUSUARIOS.TM_PERSONA` | 64.500 | ❌ son **usuarios** del sistema, no víctimas |

**El dato que falta es siempre el mismo: el documento.** Los cortes traen atributos de
la persona indexados por id interno; el número de documento no viaja en ellos.

`M_CARACT_TABLA_RA_PER` sí es aprovechable **si aparece una tabla que ligue
`CONS_PERONA` ↔ documento**. Ese `CONS_PERONA` es, con toda probabilidad, el mismo
`cons_persona` que ya está en nuestro contrato (`VictimaResumen.cons_persona`) y en
`GIC_PERSONA`. Es la pista más concreta que queda.

---

## ✅ LA FUENTE EXISTE, y no hay que pedírsela a nadie (29-jul)

El puente que faltaba **cruza**: `M_CARACT_TABLA_RA_PER.CONS_PERONA` ↔
`GIC_PERSONA.PER_IDPERSONA`, **1.996 de 2.000 (99,8 %)** en una muestra. Rangos
compatibles (0–9.185.577 vs 1–10.529.669).

Es decir, el padrón se arma juntando dos tablas que **ya alcanzamos**:

| Aporta | Tabla | Dónde está |
|---|---|---|
| documento, tipo, nombres, fecha nac. | **`GIC_PERSONA`** (7.758.615) | **nuestro propio esquema `RNIENTREVISTA`** |
| `ESTADO_RUV`, `PERT_ETNICA`, `DISCAP`, `GENERO_HOM`, ciclo vital | `M_CARACT_TABLA_RA_PER` (9.961.503) | `RNIPAQUETES` vía `DBL_VIVANTO` |

**No hace falta el web service, ni el Parametrizador, ni credenciales nuevas** para
poblar el padrón. La solicitud de acceso pasa a ser opcional: serviría para verificar
un caso puntual en línea, no para la carga.

### Tres problemas de datos que la carga tiene que resolver

Medidos sobre el total de `GIC_PERSONA`, no sobre muestra:

| Problema | Magnitud | Qué implica |
|---|---:|---|
| **Sin tipo de documento** | **1.126.615 (14,5 %)** | nuestro hash de identidad incluye el tipo; esas personas quedarían con llave `\|numero` y **el encuestador que busque "CC + número" no las encontraría** |
| **Números de documento repetidos** | **1.552.622** | coherente con el 26 % de duplicados del veredicto. Hay que decidir cuál gana al cargar |
| **`PER_TIPODOC` es texto libre** | — | `"CC"`, `"Cedula de Ciudadanía / Contraseña"`, `"CÉDULA DE CIUDADANÍA"` y `"3854"` son la misma cosa escrita de cuatro formas; hashean distinto |
| Sin número de documento | 11.952 (0,2 %) | esas filas no se pueden indexar; se descartan o se marcan |

**Esto no invalida la decisión de hoy sobre el hash.** En *nuestra* tabla el tipo es una
FK limpia a `TipoDocumento`: siempre está y está normalizado. El desorden es de la
fuente, y le toca resolverlo al **proceso de carga**, que es donde corresponde:
homologar el texto libre a un código, y decidir qué hacer con el 14,5 % sin tipo antes
de calcular la llave. Cargar sin resolver eso deja un padrón donde 1,1 millón de
personas son inencontrables.

## Camino propuesto

1. **Descubrir la tabla operativa de personas** en `DBL_VIVANTO` (empezar por
   `MODELOINTEGRADO.MI_ESTADOPERSONAS` y `MI_ESTADOVICTIMA`, y mirar volumen y columnas).
2. **Medir**, no suponer: cuántas filas, qué valores toma el estado, cómo se relaciona
   con los hechos victimizantes. El mismo método que resolvió la geografía (28.157/28.157).
3. **Resolver las credenciales de `CONSULTACARACT`** si resulta ser la fuente buena — hoy
   da `ORA-01017`.
4. Recién entonces implementar `OracleVictimaRepository` contra el contrato existente,
   con `settings.VICTIMA_REPOSITORY='ORACLE'` como interruptor, y el mock intacto como
   fallback.

**Estimación honesta:** es una fase con su propio descubrimiento, comparable a lo que
costó el Escalón 2. No entra en una tarde.
