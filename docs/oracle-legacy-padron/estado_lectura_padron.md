# Lectura del padrón real — estado y camino

> **Fecha:** 2026-07-28 · **Estado: NO IMPLEMENTADO.** La APK sigue buscando contra el
> mock. Este documento existe para que el siguiente que lo retome no empiece por donde
> empezamos nosotros — que resultó ser un callejón.

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
