# Escribir en el legacy: qué exige GIC_PERSONA / GIC_HOGAR y qué falta

**2 de agosto de 2026.** Análisis del Oracle de producción (esquema `RNIENTREVISTA`)
para llenar el legacy desde SICAV y que los reportes existentes sigan funcionando.

Salió de leer el **volcado real** —1.000.516 caracteres de PL/SQL, 72 triggers, 57
jobs, 384 constraints, 100 dependencias— que está en
[`volcado/`](volcado/). Cada afirmación cita archivo y línea; lo que no se pudo
verificar está marcado como tal.

> **Lo que hay que leer primero:** llenar GIC_PERSONA y GIC_HOGAR **no** hace
> aparecer nada en los reportes. Los reportes no leen esas dos tablas: leen
> `GIC_N_RESPUESTASENCUESTA_C`, que **solo se llena al CERRAR la encuesta**, y el
> cierre solo funciona si antes se escribieron capítulos. Ese es el hallazgo que
> cambia el plan.

---

# PLAN — Llenar GIC_PERSONA / GIC_HOGAR desde SICAV y que los reportes salgan

Para: Javier · Fecha: 2026-08-02 (para ejecutar el 3-ago)
Base del repo: `D:\desarrollo\unidad-victima`
Volcado citado: `D:\desarrollo\unidad-victima\docs\oracle-legacy\volcado\`

**Titular, sin rodeos:** llenar GIC_PERSONA y GIC_HOGAR **no hace aparecer nada en los reportes**. Los reportes no leen esas dos tablas como fuente: leen `GIC_N_RESPUESTASENCUESTA_C`, y esa tabla **solo se llena en el momento en que la encuesta se CIERRA**, y el cierre solo funciona si antes se escribieron capítulos en `GIC_N_CAPITULOS_TER`. Hoy SICAV no hace ninguna de esas dos cosas. Mañana se puede escribir bien el primer hogar real y dejar el camino listo; **mañana no salen reportes**, y encender `ORACLE_SYNC_AUTOMATICA` mañana corrompería datos vivos de la UARIV. Abajo está el porqué, con el código a la vista, y qué sí se puede hacer mañana.

---

## 1. EL FLUJO DEL LEGACY, EXPLICADO

### Por qué "hacían tantos procedimientos"

Porque en el legacy **un hogar no es una tabla, son ocho**, y **no existe transacción**. Cada procedure hace su propio `COMMIT` interno (`src_GIC_CATEGORIZACION.sql:226, 262, 300, 347`) y termina en un `WHEN OTHERS` que solo escribe en `SP_GEN_LOG_ERROR` y **no relanza** (`:234-241, :265-267, :307-309, :359-361`). Es decir: el aplicativo viejo era el que orquestaba; la base nunca supo qué era "un hogar completo". Por eso hay un procedure por cada cosa que hay que dejar escrita, y por eso hay jobs nocturnos que recogen lo que quedó a medias.

La lista de las ocho tablas que componen "un hogar" está probada por el propio rollback del legacy, `src_GIC_PROC_BORRAR_HOGARES.sql:17-27`: `gic_n_validadoresxpersona`, `GIC_N_RESPUESTASENCUESTA`, `GIC_N_RESPUESTASENCUESTA_C`, `GIC_MIEMBROS_HOGAR`, `GIC_N_CAPITULOS_TER`, `GIC_N_PREGUNTASDERIVADAS`, `GIC_ARCHIVOCOLILLA`, `GIC_HOGAR`. (Ojo: **no borra GIC_PERSONA** — porque una persona puede estar en varios hogares.)

### La cadena, paso a paso

**En vivo, mientras el encuestador trabaja:**

1. **Abrir el hogar** — `GIC_CATEGORIZACION.GIC_INSERT_HOGAR1(USUA_CREACION, ID_USUARIO, ID_PERFIL_USUARIO, ID_TIPO_CARACTERIZACION, MARCADOR OUT)` (`src_GIC_CATEGORIZACION.sql:44-51`, cuerpo `:313-361`). Inserta en `GIC_HOGAR` con `ESTADO='ACTIVA'` quemado en duro (`:346`). El `HOG_CODIGO` lo arma como `ID_USUARIO || '-' || 5 caracteres aleatorios` (`FN_GET_GENERAR_CODIGO_ENCUESTA`, `src_GIC_N_CARACTERIZACION.sql:1454-1483`), con un `WHILE` que reintenta si colisiona. El trigger `TS_GIC_HOGAR` (BEFORE INSERT, `triggers.tsv:35`) pisa el `HOG_ID` con la secuencia — por eso el procedure inserta literalmente `VALUES(0, ...)`.
   **La trampa:** solo crea el hogar si ese `ID_USUARIO` **no tiene ningún hogar en ACTIVA** (`:342-352`). Si ya lo tiene, no crea nada y devuelve en `MARCADOR` el código del hogar viejo. Y cuando **sí** crea, devuelve `MARCADOR='1'`, no el código. Semántica invertida.

2. **Alta de cada persona** — `GIC_INSERT_PERSONAS(...18 argumentos..., VALSECUENCIA OUT)` (`src_GIC_CATEGORIZACION.sql:15-23`, cuerpo `:183-241`). Inserta en `GIC_PERSONA` con `VALUES(0,...)` de 25 valores posicionales, **sin lista de columnas** (`:221-224`); el trigger `TS_GIC_PERSONA_GIC_SEC_PERSONA` (`triggers.tsv:57`) asigna el `PER_IDPERSONA` desde `GIC_SEC_PERSONA`, y el procedure lo recupera con `SELECT gic_sec_persona.currval` (`:228`) — **de la misma sesión**. Escribe los nombres/documento dos veces: en `PER_*` y en las columnas espejo `R_*` (que son las que ve la ficha del encuestador). Aplica `UPPER` a todo.
   **Única validación que hace:** si ese documento ya está en un hogar ACTIVA con la persona creada en las últimas 24 h, hace `RAISE v_duplicado` **antes** del INSERT (`:205-219`), lo traga (`:235-236`) y devuelve `VALSECUENCIA` NULL en silencio. Nombre, documento y fecha de nacimiento **no los valida nadie** — ni el procedure ni la tabla (`constraints.tsv:287-289`: en GIC_PERSONA solo `PER_IDPERSONA`, `USU_USUARIOCREACION` y `USU_FECHACREACION` son NOT NULL).

3. **Vincular persona↔hogar** — `GIC_INSERT_MIEMBRO_HOGAR(IDHOGAR, ID_PERSONA, USUARIO, ID_USUARIO, ENCUESTADA)` (`:26-33`, cuerpo `:245-267`). Es el único idempotente por diseño: un `IF COUNT(*)=0` por el par (hogar, persona) antes del INSERT (`:257-263`). No tiene triggers. La FK `GIC_REL_HOGAR_TO_MIEMBRO` (`constraints.tsv:194`) obliga a que el hogar exista primero — es la única FK que nos defiende en toda la cadena.

4. **Validadores de la persona** — aquí está la mitad del valor que se pierde si no se replica:
   - `GIC_INSERT_VALIDADOR_HOGAR(IDPERSONA, CODHOGAR, VALIDADOR, VALIDADOR_TIPOPERSONA, VALIDADOR_TIPOPERFIL, IDINSTRUMENTO)` (`src_GIC_CATEGORIZACION.sql:469-571`): escribe en `GIC_N_VALIDADORESXPERSONA` el validador **1 = INCLUIDO / NO INCLUIDO** (estado RUV, `:476-482`), el **5001=AUTORIZADO / 5002=TUTOR / 5003=CUIDADOR PERMANENTE / 5004=MIEMBRO HOGAR** (`:484-495`) y el 5005 con el perfil; además actualiza `GIC_N_RUTA_CARACTERIZACION` (`:562-566`).
   - `GIC_INSERT_VALIDADOR_PARENT(...)` (`:575-591`): validador **20=JEFE / 21=NO JEFE**.
   - `GIC_INSERT_VALIDADOR_HECHO_AUX(IDPERSONA, CODHOGAR, ID_HECHO, IDINSTRUMENTO, FECHA_HECHO)` (`:770-815`): homologa el hecho 1..14 a los validadores **101..114** y guarda la fecha; al final llama `GIC_INSERT_VALIDADOR_ARES` (`:818`, cuerpo `:1138-1170`), que crea el validador 506 si hay desplazamiento forzado.

   De esa tabla salen `ESTADO_RUV` y `HECHO_VICTIMIZANTE_1..14` de los reportes y de la constancia (`src_GIC_N_CARACTERIZACION.sql:3905-3919`, `src_GIC_N_CARGA_REPORTE_PLANO.sql:62-68`). **Ningún PL/SQL del volcado llama a estos tres procedures**: el llamador era la aplicación. Si SICAV no los llama, nadie los llama.

5. **Territorio de atención** — cascada de 4 procedures sobre `GIC_N_RELACION_DT_PUNTO` (una fila por hogar, PK `hogarcodigo+idpersona`). Solo el primero hace INSERT; los otros tres son `UPDATE ... WHERE hogarcodigo = X` sin condición (`src_GIC_N_CARACTERIZACION.sql:3373, 3418, 3473, 3522`).

6. **Cada respuesta** — `SP_SET_RESPUESTAS_DE_ENCUESTA(...)` (`src_GIC_N_CARACTERIZACION.sql:282-371`) escribe en `GIC_N_RESPUESTASENCUESTA` (la **tabla de trabajo**), con el id puesto por el trigger `TS_GIC_RESP_N_ENCU_SECUENCIA`. Y arrastra efectos colaterales: inserta en `GIC_N_VALIDADORESXPERSONA` (`:339-350`), llama `SP_INS_ETNIA_ARES` (`:352`), `SP_CAMBIAR_ESTADOGUARDADO` (`:355-358`) y `SP_SET_PREGUNTAS_DERIVADAS` (`:360-364`).
   **Detalle peligroso:** `SP_INS_ETNIA_ARES` arranca con dos `DELETE` sobre `GIC_N_VALIDADORESXPERSONA` filtrados **solo por HOG_CODIGO** (`:3676-3684`). Escribir una sola respuesta en un HOG_CODIGO ajeno **borra los validadores de ese hogar ajeno**.

7. **Marcar al encuestado** — `GIC_ACTUALIZA_ENCUESTADO(pIdPersona, pCodigo)` (`src_GIC_CATEGORIZACION.sql:928-940`): `UPDATE GIC_MIEMBROS_HOGAR SET PER_ENCUESTADA='SI'` para **una** persona.

8. **Cerrar cada capítulo** — `SP_FINALIZARCAPITULO(pcodHogar, pidTema, pusuario)` (`src_GIC_N_CARACTERIZACION.sql:1532-1546`): DELETE+INSERT sobre `GIC_N_CAPITULOS_TER`. Idempotente por (hogar, tema).

9. **Cerrar la encuesta** — `SP_ACTUALIZAR_ESTADO_ENCUESTA(HOGCODIGO, USUARIO, TIPO_APLAZAMIENTO)` con `'4'` = CERRADA (`:1575-1632`). **Este es el paso que hace existir el dato para los reportes:** pone `ESTADO='CERRADA'`, `FECHA_ESTADO`, `USU_USUARIOESTADO`, hace `INSERT INTO GIC_N_RESPUESTASENCUESTA_C SELECT * FROM GIC_N_RESPUESTASENCUESTA` y **borra la de trabajo** (`:1596-1597`), y borra `gic_variable_sesion` del usuario dueño del hogar (`:1598`).
   **Y solo hace todo eso si `totalCT > 3` en `GIC_N_CAPITULOS_TER`; si no, cae en un `ELSE NULL` literal (`:1586-1589`, `:1630-1631`) y devuelve éxito sin hacer nada.**
   No confundir con `CERRAR_ENCUESTA` (`:3581-3596`), que solo hace `UPDATE ESTADO='CERRADA'` y devuelve 1: deja el hogar marcado como cerrado con **cero** respuestas consolidadas. Es el peor estado posible y es el que hoy figura declarado en nuestro `models.py:28`.

**De noche, sin que nadie mire** (`jobs.tsv`, los 12 activos de 57):

| Hora | Job | Qué hace |
|---|---|---|
| 20:15 | `JOB_IMP_65_FT_IMPORT_JSON` | Importa el JSON del FTP de la APK vieja |
| 20:45 | `JOB_SP_ADD_ENCUESTAS_MOVIL` | Staging `GIC_ENCUESTA_MOVIL` |
| 22:30 | `JOB_SP_INSERT_ENCUESTAS_MOVIL` | **Escribe GIC_HOGAR + GIC_PERSONA + GIC_MIEMBROS_HOGAR** (`dependencias.tsv:33,65,96`) |
| 22:35 | `GIC_REPORTEULTIMOANIO` | DROP+CREATE de `gic_reporte_hogar_2021` — **congelado en 2021** (`src_GIC_PROC_REPORTE_HOGAR2021.sql:13-18`) |
| 23:30 | `JOB_SP_MIGRAR_ENCUESTAS_A_65` | Toca las tres tablas |
| 01:30 | `JOB_SP_MIGRAR_ENCUESTAS_A_HISTORICO` | Mueve/copia hacia `GIC_HOGAR_HISTORICO` |
| 02:00 / 02:30 | `PKG_ACTUALIZAR_TAB_REP` / `PKG_TABLAS_HOGPERXANIO` | Reconstruyen las tablas de reporte (procedimientos `REP2015..REP2021`) |

**El código de esos cinco últimos NO está en el volcado.** `SP_ADD_ENCUESTAS_MOVIL` y `SP_INSERT_ENCUESTAS_MOVIL` fueron recompilados el 22 y 23 de julio de 2026 (`objetos.tsv:4051, 4056`) — alguien más sigue tocando el legacy.

Y el job que resolvía `PER_IDMODELOINT` (la llave con el RUV/Vivanto) y llenaba `GIC_HECHOS_EVENTOS_PERSONA`, `GIC_ACT_TIPO_RECONOCIMIENTO`, **está DISABLED** (`jobs.tsv:62`), y filtra exactamente `WHERE P.PER_IDMODELOINT=0` (`jobs.tsv:12`).

**Al final: los reportes.** `GIC_SP_MICR_HOGAR` / `GIC_SP_MICR_PERSONA` leen `GIC_N_RESPUESTASENCUESTA_C` pivoteada contra `GIC_REPORTE_HOGARXRESPUESTA` (`src_GIC_SP_MICR_HOGAR.sql:29-45`), y `PKG_REPORTE_CARACTERIZACION` (lo que consulta el web) filtra `ESTADO='CERRADA'` en 45 sitios. Cuatro objetos de esa cadena están **INVALID en producción hoy**: `GIC_N_REPORTES` body (2026-05-28), `PKG_REPORTE_CARACTERIZACION` body (2025-11-13), `GIC_SP_MICR_HOGAR` y `GIC_SP_MICR_PERSONA` (`objetos.tsv:3933, 3945, 4012, 4014`). **Estaban rotos antes de nosotros** — hay que dejarlo por escrito para no cargar con ese muerto.

---

## 2. QUÉ TIENE QUE ESCRIBIR SICAV, EXACTAMENTE

**Orden obligatorio** (impuesto por la FK del miembro y por el encadenamiento de OUTs). Todo con **binds por nombre** — el orden de argumentos del legacy no es intuitivo (`USUARIO` va en posición 7 y `USU_FCREACION` en 8 de `GIC_INSERT_PERSONAS`).

| # | Paso | Procedure | ¿Está hoy? |
|---|---|---|---|
| 1 | HOGAR | `GIC_CATEGORIZACION.GIC_INSERT_HOGAR1` | ✅ |
| 2 | PERSONA (×N) | `GIC_CATEGORIZACION.GIC_INSERT_PERSONAS` | ✅ |
| 3 | MIEMBRO (×N) | `GIC_CATEGORIZACION.GIC_INSERT_MIEMBRO_HOGAR` | ✅ |
| 4 | VALIDADORES (×N) | `GIC_INSERT_VALIDADOR_HOGAR` + `GIC_INSERT_VALIDADOR_PARENT` | ❌ **falta** |
| 5 | HECHOS (×N×hechos) | `GIC_INSERT_VALIDADOR_HECHO_AUX` | ❌ **falta** |
| 6 | ENCUESTADO (×1) | `GIC_ACTUALIZA_ENCUESTADO` | ❌ **falta** |
| 7 | TERRITORIO | cascada de 4 `GIC_SP_*` | ✅ |
| 8 | RESPUESTAS (×N) | `SP_SET_RESPUESTAS_DE_ENCUESTA` | ✅ (solo 1ª sesión) |
| 9 | CAPÍTULOS (×temas) | `SP_FINALIZARCAPITULO` | ❌ **falta** |
| 10 | CIERRE | `SP_ACTUALIZAR_ESTADO_ENCUESTA(..., '4')` | ❌ **falta** |

### Campos: qué es obligatorio de verdad

**GIC_HOGAR** — casi todo lo pone el procedure (`HOG_CODIGO`, `HOG_CODIGOENCUESTA`, `USU_FECHACREACION`, `FECHA_ESTADO`, `ESTADO='ACTIVA'`, `src_GIC_CATEGORIZACION.sql:346`). Nosotros solo mandamos 4 valores:
- `USUA_CREACION` → `USU_USUARIOCREACION`. **NOT NULL** y en Oracle la cadena vacía **es** NULL. Debe existir como fila en `GIC_USUARIO`: `SP_REPORTE_MIEMBROSXCODIGO` hace `INNER JOIN GIC_USUARIO US ON US.USU_USUARIO = T.USU_USUARIOCREACION` (`src_GIC_N_CARACTERIZACION.sql:2451`) — si no existe, el hogar desaparece de "mis encuestas".
- `ID_USUARIO` → `USU_IDUSUARIO`. Debe existir en `GIC_USUARIO` o `T5` (encuestador) del reporte sale NULL (`src_GIC_N_REPORTES.sql:412-419`). **Debe ser el mismo usuario que `USUA_CREACION`.**
- `ID_PERFIL_USUARIO` → dominio de hecho **{1190, 1230}**: el legacy filtra `ID_PERFIL_USUARIO IN (1230,1190)` en `FN_UPDATE_HOGAR_SAAH` (`src_GIC_CATEGORIZACION.sql:1230, 1250, 1254, 1262`) y en `SP_REPORTE_XHOGAR` (`src_GIC_N_CARACTERIZACION.sql:6078, 6188`).
- `ID_TIPO_CARACTERIZACION` → `TPOCRN_ID`, **la única FK real** de las tres tablas (`constraints.tsv:140`).

`ESTADO` acepta solo 6 literales: `ACTIVA`, `APLAZADA`, `ANULADA`, `CERRADA`, `HOGAR_NO_RESPONDE`, `MANUAL` (`src_PKG_REPORTE_CARACTERIZACION.sql:1137`). **No hay CHECK**: un valor inventado no falla, simplemente desaparece de todos los conteos.

**GIC_PERSONA** — solo 3 de 25 columnas son NOT NULL y **ninguna es de identidad**. Todo lo demás es responsabilidad nuestra:
- `PNOMBRE`, `PAPELLIDO`, `NDOCU` — **obligatorios por decisión nuestra, no de Oracle.** En MAYÚSCULAS (el procedure aplica `UPPER`). Se copian automáticamente a las columnas espejo `R_*`. Son la llave de identidad de las 9 columnas de identidad de `GIC_REPORTE_PERSONA` y del cruce con Vivanto.
- `USUARIO` + `USU_FCREACION` — NOT NULL. La fecha debe ir en **hora local naive** (Oracle DATE no guarda zona; hoy mandamos UTC aware = +5h).
- `ESTADO` → `PER_ESTADO`. Dominio **`INCLUIDO` / `NO INCLUIDO`** (`src_GIC_CATEGORIZACION.sql:628, 963`). **No** `ACTIVA`.
- `IDPERMI` → `PER_IDMODELOINT`. Mandar **`0`**, no NULL (el DEFAULT 0 no aplica porque el INSERT es posicional, y el job de cruce busca `=0`).
- `TDOC`, `RELAC`, `FNACIMIENTO` — se pueden dejar, pero rompen joins en silencio si van mal (no hay FK).
- `T_VICTIMA`, `ID_DECLAR`, `ID_PERS_FUENTE`, `ID_SINIESTRO` → NULL está bien, coherente con el 99,99% del histórico.
- `FUENTEE='SICAV'` → `PER_FUENTE`. Es nuestra marca de origen y sirve para aislar y revertir.

**GIC_MIEMBROS_HOGAR** — 7 columnas, sin triggers, todo lo que quede es lo que mandemos. `ENCUESTADA` debe ser el literal **`'SI'`** (no `'S'`) y **solo para el jefe/encuestado**, no para todos. `IDPERSONA_ENCUMO` la escribe el procedure siempre NULL: no hay nada que mapear.

**Lo que NO se puede mandar nunca:** `PER_IDPERSONA` ni `HOG_ID` propios — los triggers BEFORE INSERT los pisan con la secuencia. La trazabilidad SICAV↔Oracle vive en nuestro ledger, no en la clave.

---

## 3. QUÉ NOS FALTA HOY

### BLOQUEANTE — sin esto se corrompe algo o el reporte sale mal

| # | Falta | Esfuerzo | Archivo |
|---|---|---|---|
| B1 | **Guarda: si `MARCADOR != '1'`, abortar el hogar.** Hoy `verificacion.py:28-39` acepta el código ajeno como bueno y `escritor.py:200-204` lo marca VERIFICADO. Es la puerta por la que se fusionan hogares — y una sola respuesta escrita en un hogar ajeno borra sus validadores vía `SP_INS_ETNIA_ARES` (`src_GIC_N_CARACTERIZACION.sql:3676-3684`). Daño irreversible a datos reales de la UARIV. | horas | `...\oracle\escritor.py`, `...\oracle\verificacion.py` |
| B2 | **Cerrar el hogar del piloto `999999-2W832`** antes de escribir cualquier cosa. Está en ACTIVA en producción desde el 28-jul (`plan_escalon_2.md:210`). Mientras siga ACTIVA, el próximo hogar que escribamos cae DENTRO de él. | minutos | operación en prod |
| B3 | **`_cod_usuario` devuelve cadena vacía** cuando no hay usuario (`mapeo.py:696-697` + `escritor.py:304` con `Hogar.creado_por` nullable). `USU_USUARIOCREACION` es NOT NULL → `ORA-01400` → tragado por el `WHEN OTHERS` → la persona no se escribe pero el paso puede darse por bueno. | minutos | `...\oracle\mapeo.py:696` |
| B4 | **`PER_ESTADO='ACTIVA'`** fuera de dominio. Debe ser `INCLUIDO`/`NO INCLUIDO`. Hoy `GIC_OBTENER_PERSONAS` nunca devolverá una persona nuestra. | minutos | `...\oracle\escritor.py:38`, `mapeo.py:803` |
| B5 | **`PER_ENCUESTADA='S'`** para todos, cuando el legacy compara `='SI'` y marca a uno solo. `JEFE_HOGAR` sale 'NO' para todos. | minutos | `...\oracle\mapeo.py:817` + declarar `GIC_ACTUALIZA_ENCUESTADO` |
| B6 | **`IDPERMI=NULL`** en vez de `0` → la persona nunca cruza con el RUV. | minutos | `...\oracle\mapeo.py:187-196` |
| B7 | **`Z2` (Lugar de la Encuesta) tiene `id_preg=null` en territorial v7 y v8.** En Oracle es `PRE_IDPREGUNTA=1` / `RES_IDRESPUESTA=1`, y ya está bien mapeada en buenaventura, san_andres, urbano_etnico, rural_etnico y telefonico. Sin esa fila, el hogar **no aparece en ningún reporte por departamento/municipio** ni en la búsqueda por documento (`src_PKG_REPORTE_CARACTERIZACION.sql:1051, 1064, 1131, 1143, 1212-1215`). Es el perfil del grueso de la captura. | minutos | `...\formulario\fixtures\perfil_territorial_v8.json` (+ v7, asistencia) y regenerar bundle |
| B8 | **Ninguna pregunta ABIERTA se puede escribir.** `resolver_res_idrespuesta` solo sabe LISTA, BOOLEAN y las geográficas; para TEXTO/NUMERICO/FECHA lanza excepción (`mapeo.py:405-430`). Medido: 55 preguntas abiertas con `id_preg` válido en territorial v8, 48 con respuesta contenedora única. **Hoy ningún hogar territorial completo se puede escribir**: aborta en el primer campo abierto (A5 documento → RES 101, T6 supervisor → RES 15, Z8 dirección, Z9A/B teléfonos, Z10 correo). El piloto no lo vio porque llevaba 3 respuestas. | horas | `...\oracle\mapeo.py:405-422` |
| B9 | **`try/except` por paso en `procesar_hogar`** (`escritor.py:298-358`). Hoy la excepción sube, el paso no deja fila, el hogar queda a medias en Oracle, `/estado/` dice COMPLETO y la barrida no lo recoge. Un fallo se lee como éxito. | horas | `...\oracle\escritor.py:298-358`, `...\views.py:99-110` |
| B10 | **Solo se escriben las respuestas de la PRIMERA sesión** (`escritor.py:313-317, 350`). El límite de una fila es de `GIC_N_RELACION_DT_PUNTO` (territorio), **no** de las respuestas: `SP_SET_RESPUESTAS_DE_ENCUESTA` recibe `pins_IdInstrumento` como parámetro. Es pérdida silenciosa de datos. | horas | `...\oracle\escritor.py:298-358` |
| B11 | **Paso VALIDADORES** (`GIC_INSERT_VALIDADOR_HOGAR` + `_PARENT`) — sin él no hay `ESTADO_RUV`, ni tipo de persona, ni jefe reconocible, ni marcas étnicas. El dato ya existe en `MiembroHogar.estado_inclusion` y `.tipo_persona` (`apps/hogares/models.py:327-339`, ya con los códigos 5001-5004). | días | `procedimientos.py`, `mapeo.py`, `escritor.py`, `models.py`, `verificacion.py` |
| B12 | **Paso HECHOS** (`GIC_INSERT_VALIDADOR_HECHO_AUX`) — sin él, cero hechos victimizantes en reportes y constancia. | días | idem |
| B13 | **Paso CAPÍTULOS** (`SP_FINALIZARCAPITULO`) — precondición dura del cierre. **El `TEM_IDTEMA` no hay que pedírselo a nadie**: ya está en `respuestas_oracle.json` y lo carga `catalogos.py:209-217`, solo que nadie lo lee. Se deriva de las respuestas ya escritas. | horas | `mapeo.py`, `procedimientos.py`, `escritor.py` |
| B14 | **Paso CIERRE** con `SP_ACTUALIZAR_ESTADO_ENCUESTA(hog, usuario, '4')`. Es lo único que hace que el dato exista para los reportes. **Nunca `CERRAR_ENCUESTA`.** | días | `procedimientos.py`, `escritor.py`, `verificacion.py` |
| B15 | **Un `USU_IDUSUARIO` por encuestador**, dado de alta en `GIC_USUARIO`, y `USUA_CREACION`/`ID_USUARIO` de la misma fila. Hoy son dos identidades distintas (`mapeo.py:703-704, 815-816`). Con uno compartido: fusión de hogares, cierre que borra `gic_variable_sesion` de todos, y todo el reporte de productividad atribuido a un solo usuario. | días | `catalogos.py`, `mapeo.py`, `settings/base.py:364-365` + comando de alta |
| B16 | **Respaldo verificado de las 8 tablas antes de cada lote.** Marcado como pendiente en `movimientos_en_la_bd.md §6`; el piloto del 28-jul se hizo sin él. Sin respaldo no hay vuelta atrás: COMMIT interno, sin flashback documentado, y `GIC_N_VALIDADORESXPERSONA` no tiene columna de fecha ni de usuario para reconstruir por diferencia. | horas | `infra/` + runbook |
| B17 | **Comando de reversión ejecutable.** Hoy solo existe la frase "un DELETE acotado". Las tres alternativas son trampas: `GIC_PROC_BORRAR_HOGARES` no borra `GIC_PERSONA` (deja huérfanas permanentes en una tabla sin PK) y en un hogar fusionado borra el hogar real. | días | nuevo `...\management\commands\revertir_hogar_oracle.py` |
| B18 | **Ventana horaria: escribir, verificar y revertir el mismo día antes de las 23:00.** A las 23:30 y 01:30 corren `A_65` y `A_HISTORICO`, cuyo código no tenemos. Si el hogar pasó a histórico, borrarlo de `GIC_HOGAR` ya no lo elimina. | minutos | runbook + `settings/base.py:449-460` |
| B19 | **Pedir/volcar 5 fuentes:** `SP_INSERT_ENCUESTAS_MOVIL`, `SP_ADD_ENCUESTAS_MOVIL`, `SP_MIGRAR_ENCUESTAS_A_65`, `SP_MIGRAR_ENCUESTAS_A_HISTORICO`, `PKG_ACTUALIZAR_TAB_REP`/`PKG_TABLAS_HOGPERXANIO`. Más los **cuerpos de los 5 triggers** (`TS_GIC_PERSONA_GIC_SEC_PERSONA`, `TSU_GIC_PERSONA_GIC_SEC_PERS_0`, `TS_GIC_HOGAR`, `TSU_GIC_HOGAR`, `TS_GIC_RESP_N_ENCU_SECUENCIA`) y `SP_GEN_LOG_ERROR` con su tabla destino. La base es nuestra: se extraen con `DBMS_METADATA` / `ALL_TRIGGERS.TRIGGER_BODY`. | horas | `docs\oracle-legacy\volcado\` |

### DESEABLE — no corrompe, pero deja el dato cojo

| Falta | Esfuerzo | Archivo |
|---|---|---|
| Whitelist de procedures en `invocar()` (prohibir `GIC_SP_INGRESOPERSONA`, `GIC_PROC_BORRAR_HOGARES`, `CERRAR_ENCUESTA`, `GIC_N_ACTUALIZAR_REPUES_C`, `SP_CARGA_REPORTE_HOGAR`) + test | minutos | `...\oracle\procedimientos.py:197-208` |
| Serializar por `USU_IDUSUARIO` (`bloqueo_exclusivo`, ya existe en `srni/bloqueos.py`) o cola `sync` en concurrency 1 | horas | `escritor.py` / `settings/base.py:383` |
| `verificar_respuesta` compare `RXP_TEXTORESPUESTA` (hoy solo cuenta la fila; el bug del DANE con cero pasaba) | minutos | `...\oracle\verificacion.py:100-111` |
| `verificar_persona` por **identidad** (documento + nombre + `R_*`), no por existencia del id | horas | `...\oracle\verificacion.py:54-62` |
| `VALSECUENCIA` NULL = rechazo por duplicado 24h → resolver con `GIC_VERIFICA_PERSONAS` + `GIC_IDPERSONA` | horas | `procedimientos.py`, `escritor.py:209-228` |
| `_partes_nombre` reparte mal con 2 o 3 tokens (`mapeo.py:686-693`): 'JUAN PEREZ' → apellido='JUAN'. Afecta al **24% que va por alta manual** | horas | `mapeo.py` o 4 campos separados en `MiembroHogar` |
| Zona horaria en `USU_FCREACION` (hoy UTC aware, +5h) | minutos | `mapeo.py:796` |
| `_id_oracle` descarta el `PER_IDPERSONA` si viene float (`escritor.py:130-140` + `procedimientos.py:237-238`) → ledger con NULL → persona irrecuperable | minutos | `escritor.py` |
| Preflight de contrato (last_ddl_time, VALID, nº y orden de columnas 11/25/7) | horas | nuevo `verificar_contrato_oracle.py` |
| Snapshot de `COUNT(*)` de las 8 tablas antes/después de cada corrida | horas | `verificacion.py`, `escritor.py` |
| Ledger append-only (`update_or_create` hoy pisa el intento anterior, `escritor.py:147-160`) | horas | `models.py`, `escritor.py` |
| Docstring falso de `resolver_pbandera` ("upsert idempotente" — no lo es) | minutos | `mapeo.py:208-215` |
| `PER_TIPODOC`: hoy mandamos el id numérico; el histórico tiene texto | horas | `catalogos.py`, tras medir en prod |
| Parentesco del jefe cableado a `1` en vez de resolverlo con `GIC_OBTENER_JEFEHOGAR` | minutos | `catalogos.py`, `mapeo.py:180-182` |
| `SP_INSERTA_ARCHIVO` → `GIC_ARCHIVOCOLILLA` (si no, `T4`=sin soporte en todos nuestros hogares) | horas | decisión de negocio |
| Leer `SP_GEN_LOG_ERROR` tras cada paso FALLIDO (hoy no sabemos *por qué* falló) | horas | `verificacion.py` |
| Cortacircuitos y tope diario en la barrida (hoy 50 cada 15 min = 4.800/día, sin freno) | horas | `tasks.py`, `settings/base.py` |

---

## 4. EL PLAN DE MAÑANA (3-ago), POR HORAS

**Regla de oro del día: nada se escribe en producción después de las 20:00.** A las 20:15 arranca la cadena nocturna y a las 23:30/01:30 los dos jobs de migración cuyo código no tenemos.

### 08:00 – 09:00 · Volcar lo que falta (sin escribir nada)
Solo lectura sobre `30.0.1.9/ENTREVISTARN`, con `setsid nohup` del lado del servidor (la VPN se cae):
- `ALL_TRIGGERS.TRIGGER_BODY` de los 5 triggers de B19 → `docs\oracle-legacy\volcado\triggers_body.sql`
- `DBMS_METADATA.GET_DDL` de `SP_INSERT_ENCUESTAS_MOVIL`, `SP_ADD_ENCUESTAS_MOVIL`, `SP_MIGRAR_ENCUESTAS_A_65`, `SP_MIGRAR_ENCUESTAS_A_HISTORICO`, `SP_GEN_LOG_ERROR`, `PKG_ACTUALIZAR_TAB_REP`, `PKG_TABLAS_HOGPERXANIO`
- `USER_CONS_COLUMNS` de las 3 tablas (confirmar que la PK de GIC_HOGAR es `HOG_CODIGO` — hoy es inferencia)
- `USER_TAB_COLUMNS`: `DATA_LENGTH` vs `CHAR_LENGTH` (¿los nombres son de 40 o de 80 caracteres?)
- `SELECT hog_codigo, estado, usu_fechacreacion FROM gic_hogar WHERE usu_idusuario = 999999`
- `SELECT usu_usuario, usu_idusuario, id_perfil FROM gic_usuario WHERE ...` para B15
- distribución real de `PER_TIPODOC` en los últimos 3 años

**Criterio de corte:** si `SP_MIGRAR_ENCUESTAS_A_HISTORICO` resulta que **mueve** (INSERT+DELETE) hogares en ACTIVA, se para todo y se replantea. Si solo copia por estado CERRADA, seguimos.

### 09:00 – 11:00 · Los arreglos de minutos (todos con test, sin tocar Oracle)
B3, B4, B5, B6, B7, más la whitelist de procedures, la zona horaria y `_id_oracle`. Son cambios de una línea cada uno pero son los que hacen que el dato sirva. Test que falle si:
- se invoca un procedure fuera de la whitelist
- `PER_ESTADO` no está en `{INCLUIDO, NO INCLUIDO}`
- `GIC_HOGAR.ESTADO` no está en los 6 literales
- se llama a persona sin primer nombre, primer apellido o documento
- `_cod_usuario` devuelve vacío

### 11:00 – 13:00 · Las dos guardas que evitan el desastre
- **B1**: `paso_hogar` → si `marcador != '1'` ⇒ FALLIDO y **abortar el hogar entero**. Y `verificar_hogar` exige que el `HOG_CODIGO` resuelto sea nuevo (`USU_FECHACREACION >= T0` de la corrida) y que no esté ya asignado a otro `Hogar` en el ledger.
- **Territorio**: `SELECT COUNT(*) FROM gic_n_relacion_dt_punto WHERE hogarcodigo = :h` antes de la cascada; si ya hay fila y no la creó esta corrida ⇒ FALLIDO. Es el único paso que hace UPDATE sobre filas ajenas, y `GIC_PROC_BORRAR_HOGARES` ni siquiera limpia esa tabla.
- **B9**: `try/except` por paso registrando FALLIDO con motivo.

### 13:00 – 15:00 · B8, el que desbloquea el instrumento completo
Generalizar el atajo de "respuesta contenedora única" de las geográficas a **cualquier** pregunta cuyo único `RES_RESPUESTA` sea vacío. Verificar contra `respuestas_oracle.json` que las 48 medidas quedan resueltas, y listar explícitamente las 7 que no. Test que recorra el perfil territorial v8 completo en DRY-RUN estricto **sin lanzar ni una excepción**.

### 15:00 – 16:00 · Respaldo (B16) — no negociable
`expdp` o CTAS de las 8 tablas del hogar en el servidor. Evidencia (nombre de archivo, hora, conteos) adjunta al lote. **Si esto no está, el día termina aquí y no se escribe nada en producción.**

### 16:00 – 17:00 · Cerrar el piloto (B2) — **PUNTO DE NO RETORNO**
`SP_ACTUALIZAR_ESTADO_ENCUESTA('999999-2W832', <usuario>, '4')`.
Antes: `SELECT COUNT(*) FROM gic_n_capitulos_ter WHERE hog_codigo='999999-2W832'` — si es ≤ 3, el procedure **no hace nada y devuelve éxito**. En ese caso hay dos opciones: escribir capítulos con `SP_FINALIZARCAPITULO` (B13 mínimo), o dejarlo en `ANULADA` (`'1'`), que los microdatos ya excluyen (`src_GIC_SP_MICR_HOGAR.sql:32-35`).
Después: verificar por SELECT `ESTADO='CERRADA'` y que `COUNT(*) FROM gic_hogar WHERE usu_idusuario=999999 AND estado='ACTIVA'` = **0**.

**Esto es el punto de no retorno del día**: es la primera escritura con COMMIT interno. A partir de aquí ya no hay rollback de transacción, solo el respaldo y el DELETE acotado.

### 17:00 – 19:00 · UN hogar real, a mano
```
python manage.py escribir_a_oracle --hogar <codigo> --destino produccion --confirmar
```
- Un hogar **del padrón real** (miembros con FK a `Victima`), no el demo sintético. El arreglo de identidad de hoy solo tiene tests unitarios; nunca ha entrado una fila con nombre y documento reales en `GIC_PERSONA`.
- Antes: DRY-RUN completo y leer los bloques PL/SQL uno por uno.
- Antes: `COUNT(*)` de las 8 tablas.
- Después: `COUNT(*)` de las 8 tablas y comparar el diff contra lo que dice el ledger. Y `SELECT` de identidad: `PER_PRIMERNOMBRE`, `PER_NUMERODOC`, `R_PRIMERNOMBRE`, `R_NUMERODOC` no nulos y coincidentes.
- **Un solo hogar.** Nada de lote.

### 19:00 – 20:00 · Cierre del día
Anotar en `docs\oracle-legacy\movimientos_en_la_bd.md` qué se escribió, con qué `HOG_CODIGO` y `PER_IDPERSONA`. Confirmar que `ORACLE_SYNC_AUTOMATICA` sigue en `False` y `SYNC_REINTENTO_HABILITADO` en `False`. **Parar.**

### 4-ago, después de las 03:00 · La prueba que responde la pregunta grande
Verificar que el hogar escrito ayer **sigue** en `GIC_HOGAR`, que **no** apareció en `GIC_HOGAR_HISTORICO`, y que sus personas siguen en `GIC_PERSONA`. Eso responde empíricamente qué hacen `A_65` y `A_HISTORICO` con lo nuestro, sin necesidad de leer su código.

### Lo que NO se hace mañana
- ❌ No se enciende `ORACLE_SYNC_AUTOMATICA`.
- ❌ No se enciende la barrida (arrastraría de golpe todo lo capturado, 4.800 hogares/día, sin cortacircuitos).
- ❌ No se escribe un segundo hogar hasta que el paso CIERRE exista (B14): mientras no cerremos, el segundo hogar cae dentro del primero.
- ❌ No se toca `GIC_N_REPORTES`, `PKG_REPORTE_CARACTERIZACION`, `GIC_SP_MICR_*` ni ningún job.

---

## 5. CÓMO BLINDARLO

**Que no se dupliquen personas.** `GIC_PERSONA` no tiene PK ni UNIQUE (`constraints.tsv:287-289`): la base **no puede** impedirlo. La única barrera es el ledger `RegistroEscrituraOracle`, con clave única `(hogar, paso, origen_id, destino_entorno)` en PostgreSQL (`models.py:112-115`). Reglas duras:
1. Prohibido cualquier script de carga que no pase por `EscritorOracle`.
2. El ledger no se borra ni se restaura de un backup viejo sin conciliar antes contra Oracle.
3. Arreglar `_id_oracle` (float→int) o el `PER_IDPERSONA` se guarda NULL y la persona queda irrecuperable.
4. Ledger append-only: hoy `update_or_create` pisa el intento anterior; sin historial no hay auditoría, hay estado.

**Que no se fusionen hogares.** Tres cerrojos independientes:
1. `MARCADOR != '1'` ⇒ FALLIDO y abortar (B1). Sin excepciones.
2. `verificar_hogar` exige que el `HOG_CODIGO` sea **nuevo** (fecha de creación ≥ T0 de la corrida) y que no esté ya en el ledger apuntando a otro `Hogar`.
3. Bloqueo exclusivo por `USU_IDUSUARIO` alrededor de `procesar_hogar`, o cola `sync` en concurrency 1. `srni/bloqueos.bloqueo_exclusivo` ya existe y es fail-closed; hoy solo protege la barrida.

**Que se pueda reintentar.** El ledger da reanudación por paso. Pero hay dos trampas conocidas:
- `verificar_hogar` tiene `'ACTIVA'` quemado (`verificacion.py:34-39`): en cuanto exista el paso CIERRE, cualquier re-run dará FALLIDO en el paso HOGAR. Hay que aceptar los estados de cierre.
- `GIC_INSERT_PERSONAS` rechaza en silencio el mismo documento dentro de 24h: un reintento el mismo día **siempre** choca. Tratar `VALSECUENCIA` NULL como "rechazo por duplicado" y resolver el id real con `GIC_VERIFICA_PERSONAS` + `GIC_IDPERSONA` (`src_GIC_CATEGORIZACION.sql:395-421`).

**Que no se pueda llamar a lo prohibido.** Hoy el freno es que "no los declaramos" en `procedimientos.py` — una omisión, no una barrera. Constante `PROHIBIDOS` + `assert` en `invocar()` + test: `GIC_SP_INGRESOPERSONA` (recupera el id con `MAX()` sobre 7,76M filas y no llena las `R_*`), `GIC_PROC_BORRAR_HOGARES` (borra 8 tablas sin validar estado), `CERRAR_ENCUESTA` (marca CERRADA sin mover nada a `_C`), `GIC_N_ACTUALIZAR_REPUES_C` (todo comentado salvo un `create table pruebaasd`), `SP_CARGA_REPORTE_HOGAR` (arranca con `DELETE GIC_REPORTE_HOGAR`).

**Si algo sale mal.** No hay rollback: cada procedure hizo `COMMIT`. El procedimiento es:
1. **Parar la escritura** inmediatamente (`ORACLE_SYNC_AUTOMATICA=False`, matar el worker `sync`).
2. **Leer `SP_GEN_LOG_ERROR`** — es la única traza de lo que los procedures se tragaron. Hoy ni sabemos en qué tabla escribe (candidatos: `LOG_ERRORES_ENCUESTA`, `GIC_LOG_APLICATIVO`). Por eso está en el volcado de las 08:00.
3. **Comparar el snapshot de conteos** antes/después. Es lo único que detecta un borrado colateral de validadores o un UPDATE territorial sobre un hogar ajeno — las dos verificaciones actuales miran solo la fila que esperábamos crear.
4. **Revertir con `revertir_hogar_oracle.py`** (por escribir): dry-run por defecto, solo `HOG_CODIGO` presentes en el ledger con `destino_entorno='produccion'`, borra personas **solo por los `destino_per_idpersona` del ledger** (nunca por documento ni por nombre), verifica `USU_IDUSUARIO=999999` y `PER_FUENTE='SICAV'` antes de cada DELETE, y aborta si el conteo no coincide.
5. **Antes de las 23:00.** Después, `A_65` y `A_HISTORICO` pueden haber copiado o movido el hogar y borrarlo de `GIC_HOGAR` ya no lo elimina del sistema.
6. **Alternativa suave:** dejar el hogar en `ESTADO='ANULADA'` (`SP_ELIMINAR_ENCUESTA`, `src_GIC_N_CARACTERIZACION.sql:1698-1706`). Los microdatos ya excluyen ese estado. Neutraliza sin borrar.

**Congelar el DDL.** Los INSERT del legacy son **posicionales sin lista de columnas** (25/7/11 valores). Un `ALTER TABLE` en cualquiera de las tres invalida el package y toda la escritura empieza a fallar **en silencio**. Durante la migración no se toca el DDL de `GIC_PERSONA`, `GIC_HOGAR` ni `GIC_MIEMBROS_HOGAR`. Y como el legacy se sigue tocando (dos recompilaciones el 22 y 23 de julio), un preflight de 30 líneas que compare `last_ddl_time` y el número de columnas contra una línea base versionada convierte un fallo masivo silencioso en un abort ruidoso.

---

## 6. LO QUE NO SE PUEDE GARANTIZAR — Y LO QUE TE TOCA DECIDIR A TI

### No se puede garantizar hoy

1. **Que lo que escribamos sobreviva la noche.** `SP_MIGRAR_ENCUESTAS_A_HISTORICO` y `SP_MIGRAR_ENCUESTAS_A_65` corren cada noche sobre nuestras tablas y **su código no está en el volcado**. Existe `GIC_HOGAR_HISTORICO` con la estructura idéntica más `ROWID_HIS` — patrón clásico de mover filas. No es verificable con este volcado si copian o mueven. La prueba del 4-ago lo responde empíricamente.

2. **Que los reportes muestren lo de SICAV, aunque todo lo demás salga perfecto.** El job diario `GIC_REPORTEULTIMOANIO` (22:35, corriendo desde hace 5 años) recrea `gic_reporte_hogar_2021` filtrando `BETWEEN '01/01/2021' AND '31/12/2021'`, y `PKG_REPORTE_CARACTERIZACION` no tiene rama para 2026 (`src_PKG_REPORTE_CARACTERIZACION.sql:288-299`). Un hogar de 2026 **no puede** entrar ahí. Es deuda del legacy, no nuestra, pero sin resolverla la promesa "los reportes siguen funcionando" es falsa.

3. **Que la cadena de reportes funcione.** `GIC_N_REPORTES` body (INVALID desde 2026-05-28), `PKG_REPORTE_CARACTERIZACION` body (INVALID desde 2025-11-13), `GIC_SP_MICR_HOGAR` y `GIC_SP_MICR_PERSONA` (INVALID). En Oracle un objeto INVALID se recompila al primer uso, pero si falla, el reporte cae. Hay que verificar que recompilan **antes** de que entre el primer dato de SICAV, para no confundir un reporte roto de antes con un daño nuestro.

4. **Que se migre todo lo capturado.** 27 preguntas con `id_preg=null` en telefónico/rural_étnico (vivienda: paredes, piso, techo, agua, saneamiento; salud: régimen, H13) **no se migran**. En territorial v8 son 114. Es pérdida de alcance decidida, no un bug — pero tienes que saber qué capítulos no van a llegar a los reportes de la UARIV.

5. **Que la fecha de la encuesta sea la real.** `SP_SET_RESPUESTAS_DE_ENCUESTA` **no acepta fecha**: `USU_FECHACREACION` es `SYSDATE` del momento del sync. Si sincronizamos en lote días después, "fecha inicio" y "fecha fin" de la encuesta en los microdatos serán casi idénticas y del día del sync.

6. **Que se pueda revertir sin el ledger.** `GIC_PERSONA` se aísla por `PER_FUENTE='SICAV'` y hogar/miembro por `USU_IDUSUARIO`. Pero `GIC_N_VALIDADORESXPERSONA` y `GIC_N_RELACION_DT_PUNTO` **no tienen columna de usuario ni de fecha**: solo se identifican por `HOG_CODIGO`. Si la BD de SICAV se restaura de un respaldo anterior, no sabemos si podríamos revertir.

### Decisiones que son tuyas (nadie más las va a tomar)

| # | Decisión | Por qué no puede esperar |
|---|---|---|
| D1 | **¿Un `USU_IDUSUARIO` por encuestador, o seguimos con el usuario de servicio 999999?** | Con uno compartido: fusión de hogares, cierre que borra `gic_variable_sesion` de operaciones en curso del aplicativo web vivo, y todos los reportes de productividad atribuidos al mismo usuario. Es la causa raíz más barata de eliminar de toda la lista. **Recomendación: uno por encuestador, dados de alta en `GIC_USUARIO`.** |
| D2 | **`ID_PERFIL_USUARIO`: ¿1190 o 1230?** | Con cualquier otro valor el hogar es invisible para el reporte de grupo familiar y no se le puede cambiar el estado por la vía SAAH. No hay FK que avise. |
| D3 | **`PER_IDMODELOINT`: ¿mandamos 0 y reactivamos `GIC_ACT_TIPO_RECONOCIMIENTO`, lo portamos a Django, o lo resolvemos al insertar?** | Es la llave que amarra la persona con el RUV/Vivanto y con `GIC_HECHOS_EVENTOS_PERSONA`. Sin ella la persona existe pero no cruza con nada. El job está DISABLED y tal como está recorre 7,76M de filas. **Recomendación: mandar 0 ahora, portarlo a Django después — no reencender el job.** |
| D4 | **¿Nuestros hogares salen "sin soporte" (`T4=2`) y "no terminados" (`T1=2`)?** | `T4` exige fila en `GIC_ARCHIVOCOLILLA`; `T1` exige ≥20 capítulos en `GIC_N_CAPITULOS_TER`. Se puede asumir explícitamente, o implementar `SP_INSERTA_ARCHIVO` y los 20 capítulos. |
| D5 | **¿Escalamos a OTI el `GIC_PROC_REPORTE_HOGAR2026`?** | Sin esa rama, nada de lo capturado en 2026 llega al reporte que consume el front. Es deuda del legacy pero nos la van a cobrar a nosotros. |
| D6 | **`PER_TIPODOC`: ¿id numérico o texto?** | El histórico tiene texto ('Cedula de Ciudadania'), nosotros mandamos '1'. La columna se muestra cruda al usuario en la constancia. Si mandamos números añadimos una sexta convención a una columna que ya tiene cinco. |
| D7 | **¿Se adjunta constancia firmada y soportes desde SICAV?** | `SP_INSERTA_SOPORTES` / `SP_INSERTA_CONSTA_FIRMADA_SAAH` no tienen equivalente en SICAV hoy. Hay que decidirlo **antes** de apagar el legacy, no después. |
| D8 | **El árbol genealógico (`GIC_INSERT_ARBOLGENEALOGICO`)** — ningún objeto del volcado lo consume, pero es forma que dejaba la app vieja y tu objetivo declarado es que la forma sea idéntica. | Barato de decidir: si nadie lo lee, no lo hacemos y queda documentado. |

---

## RESUMEN EN CUATRO FRASES

1. Llenar `GIC_PERSONA` y `GIC_HOGAR` es el 30% del trabajo: el otro 70% son los **validadores**, los **capítulos** y el **cierre**, y sin cierre los reportes no ven absolutamente nada.
2. Mañana se puede: volcar lo que falta, arreglar los 8 defectos de minutos, poner las dos guardas anti-fusión, desbloquear las preguntas abiertas, respaldar, cerrar el piloto y escribir **un** hogar real completo.
3. Mañana **no** se puede: encender la sincronización automática. Con el hogar del piloto en ACTIVA y sin paso de cierre, el segundo hogar entra dentro del primero y su primera respuesta **borra los validadores de un hogar real de la UARIV**, en silencio, sin forma de saber qué se borró.
4. Lo que hay que decidir hoy, antes de mañana: **D1 (un usuario por encuestador)** y **D2 (perfil 1190 o 1230)**. Sin esos dos, ni siquiera el hogar de prueba queda bien escrito.