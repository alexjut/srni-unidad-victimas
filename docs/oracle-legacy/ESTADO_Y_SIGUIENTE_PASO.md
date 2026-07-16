# Oracle legacy → SICAV — Estado y siguiente paso

> **Traspaso de sesión.** Qué hicimos, dónde está todo, qué falta y **con qué empezar
> la próxima vez** (incluye el prompt listo para pegar). Fecha de corte: 2026-07-16.
> **Worktree:** `feat/oracle-legacy-writer` en `D:\desarrollo\uv-oracle-writer`.
> Todo lo hecho fue **solo lectura** contra Oracle (local + prod), excepto un único
> `DROP` autorizado de una master table huérfana. La escritura real a Oracle **NO
> está activada** (todo en DRY-RUN).

---

## 1. Qué hicimos (fases completadas)

| Fase | Resultado | Artefacto |
|---|---|---|
| **Infra Oracle local** | Contenedor Docker `gvenzl/oracle-free` (`FREEPDB1`), esquema `RNIENTREVISTA` importado con estructura real (333 tablas/78 triggers/68 secuencias). Export lo generamos nosotros (no OTI). | `infra/oracle-local/`, `docs/oracle-legacy/oracle-local-setup.md` |
| **Validación de paridad** | Lógica portada: **24/24** tests Django. Estructura: **12/12** invariantes resuelven contra el esquema real. | `paridad_logica_portada.md` |
| **Housekeeping prod** | `DROP` de master table huérfana `SYS_EXPORT_SCHEMA_01`; secreto de prod borrado. (Falta: rotar clave RNIENTREVISTA — lo hace Javier.) | — |
| **Etapa A — capa de escritura (DRY-RUN)** | Strangler-fig etapa A: escribir vía **procedures oficiales**. Ledger reanudable + máquina de estados + verificación por SELECT + redacción PII. Comando `escribir_a_oracle` (DRY-RUN; `--confirmar` bloqueado). | `apps/sincronizacion/` · commit **`b504d79`** |
| **ResolverCatalogos** | Traduce SICAV→Oracle con **valores reales de prod**: tipo_doc (CC→1…), parentesco (8), tipo_caracterización=HOGAR(2). Nunca inventa. | `oracle/catalogos.py`, `catalogos_oracle.json` |
| **Auditoría de diseño legacy** | 10 hallazgos + 4 nuevos, cada uno con decisión (replicar/mejorar/descartar) y evidencia. | `auditoria_diseno_legacy.md` |
| **Veredicto a1 vs a2** | **a1 (procedures granulares) confirmado.** a2 (ingesta móvil) descartada: no puebla territorio (reintroduce el bug). | `auditoria_diseno_legacy.md` §Veredicto |

**Decisiones de arquitectura cerradas:** strangler-fig (a1 ahora, escritura directa Django = Etapa B después) · ruta = procedures granulares · no arrastrar Java-en-BD, tablas-sombra, packages muertos, reportes congelados.

---

## 2. Estado actual del código

- **Commiteado y pusheado** en `feat/oracle-legacy-writer`: `b504d79` (Etapa A + ResolverCatalogos, 17 archivos), en ambos remotes (`origin` + `azure`).
- **SIN COMMITEAR (pendiente de revisión de Javier):** incrementos 6+7 — cascada
  territorial cableada + `resolver_territorio` real. 5 archivos tocados + 1 test nuevo.
- **Todo en DRY-RUN.** La ruta `--confirmar` aborta a propósito hasta resolver los pendientes de negocio.
- Máquina de estados ejecuta ya los **cinco pasos**: HOGAR → PERSONA → MIEMBRO →
  TERRITORIO → RESPUESTA. Corrida real sobre un hogar: **10 pasos, todos DRY_RUN**.
  - **TERRITORIO resuelve ids REALES** contra el crosswalk (DT CENTRAL/TOLIMA/
    JORNADAS/ALVARADO → `id_dt=7, id_depto=30, id_pt=13, id_ma=32`).
  - **RESPUESTA tiene la fontanería completa pero sus ids están PENDIENTES** de
    dato/negocio (ver 3a.6-3a.9): salen como marcadores `‹PEND:...›`, nunca inventados.
- Docs de análisis en `docs/oracle-legacy/` están **gitignored** por convención del equipo (menos `oracle-local-setup.md` y este archivo, que son traspaso/arquitectura sin datos de prod).

### 2.1 Lo que se aprendió del PL/SQL real (relevante para revisar)

- **La cascada territorial son 4 procedures y el ORDEN es obligatorio.** Solo el
  primero (`GIC_SP_OBDEPTOPORDT`) hace `INSERT` de la fila en
  `GIC_N_RELACION_DT_PUNTO`; los otros tres son `UPDATE ... WHERE hogarcodigo=X`.
  Un UPDATE sin fila **no es error** en Oracle: fuera de orden, el paso "pasaría"
  sin dejar territorio.
- **⚠️ Trampa de nombres confirmada:** `GIC_SP_OBTPUNTOATECION` recibe un parámetro
  formal llamado `Id_DT`, pero su cuerpo hace `SET iddeptoaten = Id_dt` y filtra
  `T.IDDEPARTAMENTO = pId_DT` (body 3140 y 3162). **Espera el id de DEPARTAMENTO,
  no el de la DT.** Pasarle la DT rompe el join de los reportes
  (`RL.IDDEPTOATEN = PA.IDDEPARTAMENTO`) — la forma exacta del bug histórico.
  Hay test de regresión para esto.
- **Son CUATRO ids, no tres.** El stub anterior devolvía `id_dt/id_pt/id_ma` y se
  comía `IDDEPTOATEN`, que es columna propia. Faltando una, el territorio queda
  incompleto.
- **El cruce debe ser por la FILA COMPLETA, no columna a columna.** Los nombres
  sueltos no son únicos: 68 municipios repiten nombre (BUENAVISTA tiene 4 ids) y
  `JORNADAS DE ATENCION Y/O FERIAS DE SERVICIO` existe con 39 ids (uno por DT).
  La tupla (dt, depto, punto, municipio) sí es única: **1370/1370, 0 ambiguas**.
- **`SP_SET_RESPUESTAS_DE_ENCUESTA` falla en silencio con ids desconocidos:** abre
  con `SELECT ... INTO` sobre `RES_IDRESPUESTA` y su `WHEN OTHERS` se traga el
  `NO_DATA_FOUND` ⇒ retorna sin excepción y sin escribir. Por eso los ids no se
  adivinan y la verificación por SELECT es obligatoria.

---

## 3. Qué falta (pendientes)

### 3a. Bloqueantes de NEGOCIO (los resuelve Javier con Oscar/UARIV — no los decido yo)
1. **Usuario/perfil de servicio SICAV en Oracle** → poner valor en `settings.ORACLE_LEGACY['USUARIO_SERVICIO_ID' / 'PERFIL_SERVICIO_ID']`.
2. **Mapeo P8** (campos vivos de `GIC_INSERT_PERSONAS`): `ID_SINIESTRO`→hecho/siniestro (`HechoVictima`), `ID_DECLAR`→declaración/FUD, `T_VICTIMA`→tipo de víctima.
3. **Tipo de documento PE (PEP) y NES** — sin equivalente en `GIC_TIPODOC`: ¿mapear a Otro(13)/Indocumentado(14) o pedir alta de catálogo?
4. **SISBEN** (N3): ¿SICAV usa el cruce `TEMP_SISBEN`?
5. **Rotar clave RNIENTREVISTA** (se usó para lectura/export).

**Nuevos, detectados al cablear RESPUESTA (bloquean ese paso por completo):**

6. **`PINS_IDINSTRUMENTO`** — SICAV **no guarda en ninguna parte** el id de
   instrumento de Oracle. `formulario.Instrumento` tiene su propio TODO al respecto
   ("confirmar lista oficial de instrumentos y códigos exactos con área funcional /
   tablas Oracle"). Hace falta la equivalencia instrumento SICAV → `INS_IDINSTRUMENTO`.
7. **`PRES_IDRESPUESTA`** — hipótesis razonable: `OpcionRespuesta.id_resp_vivanto`
   (ID_RESP del Diccionario V8, p.ej. 4599=Mujer) sería el `RES_IDRESPUESTA` de
   `GIC_N_RESPUESTAS`. **Sin verificar**: no tenemos volcado de esa tabla. En dry-run
   el marcador muestra el candidato (`‹PEND:RES_IDRESPUESTA(hip:4572)›`) para poder
   cotejarlo. **Basta un `SELECT` de `GIC_N_RESPUESTAS` para confirmar o descartar.**
8. **`PPER_IDPERSONA` de preguntas de nivel HOGAR** — en SICAV llegan con
   `miembro=NULL` y el procedure exige un NUMBER. La cascada territorial usa el
   literal `'1'` como "persona del hogar"; extrapolarlo sería suponer. ¿Qué manda
   ahí la app vieja?
9. **`PBANDERA`** — con valor 1 dispara `SP_BORRADORESPUESTAS`, que **BORRA** las
   respuestas previas del hogar/instrumento; con 0 solo inserta. Qué corresponde en
   una migración es decisión de negocio, y el lado destructivo no se asume.
10. **`RXP_TIPOPREGUNTA`** — VARCHAR2 libre, sin catálogo ni CHECK que lo acote. No
    hay dominio conocido al cual mapear los tipos SICAV (RADIO/LISTA/TEXTO…).

**Dato, no decisión — pero también bloquea:**

11. **El catálogo de puntos de atención de SICAV es un placeholder** y no cruza a
    Oracle. `cargar_puntos_atencion.py` lo dice en su propio docstring: carga 2
    puntos por DT (37 en total) hasta que UARIV entregue el oficial. Oracle tiene
    **266 puntos reales**. Medido: las **21/21 DT cruzan** y "JORNADAS…" cruza, pero
    de los 20 "Centro Regional X" **solo 13 existen en Oracle**; no existen Medellín,
    Cartagena, Bogotá, Barrancabermeja, Pasto, Mocoa ni Bucaramanga. "ATENCIÓN
    TELEFÓNICA" tampoco (Oracle usa "ESQUEMA NO PRESENCIAL BOGOTA D.C." y similares).
    ⇒ Con el catálogo actual, un hogar cuyo punto sea un Centro Regional de esos 7
    **falla al resolver** (con error claro, no con un id inventado). Hace falta el
    dataset oficial de UARIV o un crosswalk punto SICAV→Oracle.

### 3b. Incrementos TÉCNICOS
- ~~6. Cablear TERRITORIO + RESPUESTA~~ ✅ **hecho** (pendiente de tu revisión).
- ~~7. Resolver territorio desde el crosswalk~~ ✅ **hecho** (pendiente de tu revisión).
- ~~12. `MiembroHogar.tipo_victima` NO EXISTE y el `getattr(..., None)` lo enmascara~~
  ✅ **corregido**: ahora lanza `CampoOrigenFaltante` nombrando el campo, y en dry-run
  el marcador dice la causa real (`‹PEND:T_VICTIMA(MiembroHogar SIN campo
  tipo_victima)›` en vez del engañoso `‹PEND:TIPO_VICTIMA(None)›`). Ojo: **esto solo
  arregla el diagnóstico**. Siguen abiertos, encadenados: (a) el campo no existe en el
  modelo — ¿se añade o el dato sale de otro lado?; (b) aunque existiera, el mapeo de
  T_VICTIMA sigue pendiente (3a.2, P8, Oscar).
- 13. **Territorio con varias sesiones** — `GIC_N_RELACION_DT_PUNTO` admite **una sola
  fila por hogar** (PK `hogarcodigo`+`idpersona='1'`). El escritor toma la PRIMERA
  sesión. Si un hogar puede tener sesiones con territorios distintos, Oracle solo
  guarda uno: confirmar si ese caso existe.

### 3c. Después (no ahora)
- Escalón 1 del rollout: 1 hogar contra Oracle **local** con `--confirmar` (requiere ResolverCatalogos completo + tu aprobación).
- Etapa B (escritura directa Django) — fase separada, cuando se retire la app vieja.

---

## 4. Con qué EMPEZAR la próxima sesión (recomendación)

Los incrementos técnicos 6+7 ya están. **Lo que queda está bloqueado por dato/negocio,
no por código**, así que la recomendación cambia de "seguir picando" a "desbloquear":

1. **El desbloqueo más barato y de mayor impacto: un `SELECT` de solo lectura** a
   `GIC_N_RESPUESTAS` y `GIC_N_INSTRUMENTOXPREG` en prod (o el volcado de esas dos
   tablas). Confirma o descarta la hipótesis `id_resp_vivanto == RES_IDRESPUESTA`
   (3a.7) y da el `INS_IDINSTRUMENTO` (3a.6) — los dos bloqueantes duros de RESPUESTA.
   Ojo: la clave de RNIENTREVISTA **está pendiente de rotar** (3a.5); coordinar ambas.
2. **En paralelo, con Oscar:** 3a.8 (PPER_IDPERSONA de nivel hogar), 3a.9 (PBANDERA)
   y 3a.11 (catálogo oficial de puntos de atención).
3. Con eso resuelto, el siguiente incremento técnico sale solo: quitar los pendientes
   de `binds_respuesta` y hacer el escalón 1 contra el Oracle **local**.

---

## 5. Qué DECIR la próxima sesión (prompt listo para pegar)

**Si ya tienes el volcado / los datos de Oracle** (lo más probable y lo más útil):

> Retomamos la migración Oracle legacy → SICAV, worktree `feat/oracle-legacy-writer`.
> Lee `docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md` para el contexto completo.
> Sigue todo en **DRY-RUN, solo lectura** contra Oracle.
>
> Ya traigo esto de la sección 3a: [pega aquí lo que tengas — volcado de
> `GIC_N_RESPUESTAS` / `GIC_N_INSTRUMENTOXPREG`, el `INS_IDINSTRUMENTO` por
> instrumento, qué `PPER_IDPERSONA` va en preguntas de hogar, qué `PBANDERA`, el
> catálogo oficial de puntos de atención].
>
> Tarea: quitar los pendientes correspondientes de `binds_respuesta` /
> `ResolverCatalogos`, con tests, y dejar el DRY-RUN de un hogar mostrando el flujo
> completo **sin marcadores ‹PEND:›** en lo que ya esté resuelto. Lo que siga sin
> dato, sigue pendiente: no lo adivines. No commitees hasta que yo revise.

**Si todavía no hay datos**, no hay incremento técnico que valga la pena: lo que
queda son los bloqueantes 3a.6-3a.11. Ver §4.

---

## 6. Punteros rápidos

- Código Etapa A: `srni-backend/apps/sincronizacion/` (models, oracle/, management/, tests/).
- Crosswalk catálogos: `apps/sincronizacion/oracle/catalogos.py` + `catalogos_oracle.json`.
- Diseño Etapa A: `docs/oracle-legacy/diseno_etapa_a_escritura.md`.
- Auditoría + veredicto a1/a2: `docs/oracle-legacy/auditoria_diseno_legacy.md`.
- Ruta de escritura (análisis PL/SQL): `docs/oracle-legacy/ruta_escritura.md`.
- Correr DRY-RUN: `python manage.py escribir_a_oracle --hogar <cod> --settings=srni.settings.development`.
- Oracle local: `cd infra/oracle-local && docker compose --env-file .env up -d`.

### Escenario del Escalón 1 (reproducible)

`cargar_hogar_demo_oracle` deja un hogar con sesión, territorio que **cruza a ids
reales de Oracle** y respuestas de los dos niveles. Es command y no fixture JSON a
propósito: el cruce es por NOMBRE y un fixture tendría que fijar `Municipio` por PK
(no hay `natural_key()`), que es la fragilidad que ya advierte `dump/README.md`.

```bash
python manage.py loaddata dump/hogares_demo_10.json          # precondición
python manage.py cargar_departamentos_municipios --csv=data/municipios_dane.csv
python manage.py cargar_direcciones_territoriales
python manage.py cargar_hogar_demo_oracle                    # idempotente
python manage.py escribir_a_oracle --hogar LISTO-96001       # DRY-RUN, 10 pasos
```

Territorio sembrado: DT CENTRAL / Tolima / JORNADAS DE ATENCIÓN / ALVARADO →
`id_dt=7, id_depto=30, id_pt=13, id_ma=32` (el comando lo verifica y aborta si deja
de cruzar). El punto va **con tilde** a propósito, para ejercitar la normalización.

⚠️ **Trampa que el comando ya cubre:** los hogares del fixture vienen con
`creado_por=null` ⇒ `USUA_CREACION` viajaría como cadena vacía y **en Oracle '' ES
NULL**; como `GIC_HOGAR.USU_USUARIOCREACION` es NOT NULL, el INSERT fallaría y
`GIC_INSERT_HOGAR1` se tragaría el error con su WHEN OTHERS: no escribiría nada y no
avisaría. El comando asigna un encuestador si falta.
