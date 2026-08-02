# Oracle legacy → SICAV — Estado y siguiente paso

> **Traspaso de sesión.** Qué hicimos, dónde está todo, qué falta y **con qué empezar
> la próxima vez** (incluye el prompt listo para pegar). Fecha de corte: 2026-07-16.
> **Worktree:** `feat/oracle-legacy-writer` en `D:\desarrollo\uv-oracle-writer`.
> Todo lo hecho fue **solo lectura** contra Oracle (local + prod), excepto un único
> `DROP` autorizado de una master table huérfana. La escritura real a Oracle **NO
> está activada** (todo en DRY-RUN).

---

## 0-ter. Actualización 2026-08-01 — **EL PADRÓN REAL ESTÁ CARGADO** (leer esto primero)

Ya no estamos leyendo el padrón: **está en nuestra base**.

| | |
|---|---|
| Personas en el padrón | **5.927.713** víctimas **incluidas** (`ESTADO_RUV = 1`) |
| Fuente | `GIC_PERSONA` ⨝ `M_CARACT_TABLA_RA_PER@DBL_VIVANTO` |
| Duración de la carga | 19 h (sobrevivió a dos caídas de VPN) |
| Regla de 2 años | **1.940.213 vencidas** · 1.392.101 al día |
| Descartadas | 0 |

**Antes de tocar nada, leer:**
[`../oracle-legacy-padron/hallazgos_identidad_padron.md`](../oracle-legacy-padron/hallazgos_identidad_padron.md)
— 11 hallazgos sobre cómo está partida la identidad entre las tres bases, y las
**5 preguntas para OTI**. Y [`../ciclo_completo_tablas.md`](../ciclo_completo_tablas.md)
— el recorrido entero de un dato y qué se rompe en cada etapa.

### Lo que se decidió, y lo que costó

**No se usó `MI_PERSONAS`**, que era el origen pedido. Tres mediciones lo impidieron:
su `PER_ID` no se alcanza desde `GIC_PERSONA.PER_IDMODELOINT` (**0 de 20.000**); el
puente `DEP_RUV_PERSONAS_MI` mezcla RUPD/RUV/SIV y el `CONS_PERONA` del corte cruza
con **dos fuentes a la vez**; y el cruce por documento devuelve **1.159 millones de
filas a partir de 20.000 documentos** porque hay 1,2 M de documentos de un solo
carácter. Cualquiera de esos caminos asigna datos de **otra persona**, en silencio.

**El precio:** **1.884.872 víctimas incluidas (24 %)** no tienen identidad en la .9 y
**quedan fuera del padrón**. La APK debe permitir alta manual — no es un caso raro,
es una de cada cuatro.

### Cuatro defectos que estaban escondidos y ya no

1. **Producción respondía con el MOCK.** `settings.VICTIMA_REPOSITORY` no existía en
   ningún settings → `getattr(..., "MOCK")`. Las búsquedas devolvían ENC001 y
   documentos 999… El sistema *funcionaba*, solo que contra otra base.
2. **La precarga pedía el padrón entero.** `/api/victimas/precarga/` llamaba a
   `listar_todas()` sin tope: con el mock eran 11 personas, con el padrón real
   5.926.004 → el login de la APK quedaba colgado sin dar error.
3. **`MEDIA_ROOT` solo estaba en development** → `generar_padron` abortaba en el
   servidor.
4. **`CELERY_TASK_TIME_LIMIT = 600`** habría matado la recarga mensual a los 10 min, y
   el `visibility_timeout` de Redis (1 h) habría lanzado **dos cargas simultáneas**
   contra Oracle.

Los cuatro con test de regresión.

### Para que se mantenga solo

`cz_beat` + `cz_celery_padron` desplegados, con tres tareas — **apagadas por defecto**,
porque encenderlas escribe en producción:

| Tarea | Cuándo | Interruptor |
|---|---|---|
| `recargar_padron` (padrón → fechas → SQLite) | 1.º sábado del mes, 20:00 | `PADRON_RECARGA_HABILITADA` |
| `refrescar_fechas_padron` (fechas → SQLite) | diaria, 03:30 (~15 min) | idem |
| `reintentar_sincronizaciones_pendientes` | cada 15 min | `SYNC_REINTENTO_HABILITADO` |

Para encenderlas: editar el `.env` del servidor y `docker compose up -d cz_beat`.

### Lección operativa (costó cuatro intentos)

**La VPN a 30.0.1.109 se cae seguido.** Los comandos largos por SSH mueren con cada
corte. Lo que funciona: subir un script y lanzarlo con `setsid nohup` **del lado del
servidor**, y consultar el log aparte. Así sobrevivió la carga de 19 h. Los cortes a
mitad de un `docker compose up` dejan contenedores huérfanos con nombre hasheado
(`41812ae7da25_cz_backend`) que bloquean el siguiente `up`: hay que `docker rm -f`
esos, **nunca `cz_postgres`**.

### Qué falta

1. ~~Terminar `generar_padron`~~ ✅ **TERMINÓ el 2-ago 04:45 UTC** (11 h en total).
   `padron-20260802044544-9bf121f2.sqlite3`. Paso 3: 2.535.941 fechas aplicadas
   sobre 3.332.338 leídas en 36.619 s; 796.373 fuera del padrón; 24 fechas
   imposibles. Padrón: 5.926.004 · con fecha 2.535.941 · al día 1.058.971.
   **El archivo existe, pero NO está listo para campo — tres hallazgos; al 2-ago
   queda 1a cerrado y 1b/1c abiertos, ambos esperando decisión:**

   🔴 **1a. El manifiesto declara 997.279 filas que no están.** ✅ **ARREGLADO Y
   DESPLEGADO (2-ago, `4b88856`).** `generar_padron` ahora declara el `count(*)`
   del archivo y agrega `registros_leidos` y `colisiones_documento`, con aviso en
   stdout. El manifiesto **ya servido** se corrigió en caliente sin regenerar las
   11 h (mismo `checksum` y `version` → la APK no re-descarga): el endpoint
   `/padron/version/` responde `total_registros 4.928.725`, `registros_leidos
   5.926.004`, `colisiones_documento 997.279`. *Sigue abierta la **decisión
   funcional**: qué hacer con los duplicados dentro del archivo offline (ver más
   abajo, y ojo que el camino ONLINE ya quedó resuelto con el 409).* El texto
   original del hallazgo, para contexto:
   `padron-latest.json` decía 5.926.004 registros; el SQLite tiene **4.928.725**. La
   causa es `INSERT OR REPLACE INTO padron` con `doc_hash TEXT PRIMARY KEY`: cuando
   dos víctimas comparten documento, la segunda pisa a la primera **sin avisar**. El
   número cuadra exacto con la BD (5.926.004 − 4.928.725 pares distintos = 997.279).

   | Repeticiones del documento | Documentos | Personas |
   |---|---:|---:|
   | 2 (probable duplicado real) | 617.770 | 1.235.540 |
   | 3–10 | 149.633 | 509.521 |
   | 11–100 | 678 | 10.756 |
   | **>100 (comodín, uno con 4.297)** | **15** | **9.558** |

   Los pares son probablemente la misma persona (H9) y quedarse con una se defiende.
   Los 693 con >10 repeticiones son el documento basura de H5: ahí son personas
   **distintas** y la búsqueda devuelve una al azar — el riesgo de "datos de otra
   persona, en silencio". *Arreglo inmediato y sin decisión: que el conteo del
   manifiesto salga del `count(*)` del archivo, no del contador del bucle, y que se
   informe cuántas colisiones hubo. Lo que sí es **decisión funcional**: qué hacer
   con los duplicados (la caracterizada más recientemente / excluirlas / marcarlas
   para alta manual).*

   🟠 **1b. Pesa 878 MB, no los ~150 MB de la arquitectura offline** (5,9×). Es el
   punto que decide si "descargar el padrón entero al dispositivo" se sostiene con el
   padrón real. Dónde está el peso: `doc_hash` **301 MB** (SHA-256 en hex de 64
   caracteres; en binario truncado a 16 bytes serían ~75 MB), `nombre` 123 MB,
   `cons_persona` 32 MB, el resto índice y overhead.

   🟠 **1c. Los nombres van en claro.** `nombre TEXT NOT NULL`: 5,9 M nombres reales
   de víctimas sin cifrar en un archivo que se descarga a móviles. El cifrado estaba
   anotado como Fase 1, pero hasta el 1-ago el contenido era el mock de 11 personas.

   🟠 **1d. Los duplicados DENTRO del archivo offline siguen sin decidirse.** El
   online ya está resuelto (409 con candidatos, punto 2). Pero el SQLite tiene una
   sola fila por `doc_hash`, así que **offline** una búsqueda sobre esos 768.096
   documentos devuelve **una** de las personas y no dice que había otra — que es
   justo el silencio que el 409 elimina online. Las salidas posibles: (a) permitir
   varias filas por documento (PK compuesta o `rowid`) y que la APK muestre
   candidatos, como online — es lo coherente, y **aumenta** el tamaño ya
   problemático de 1b; (b) marcar el documento como ambiguo con una bandera y sin
   los datos de nadie, forzando la consulta online o el alta manual; (c) excluirlos
   del archivo. **Decide Javier** (ver [`../gestion/decisiones_negocio_pendientes.md`](../gestion/decisiones_negocio_pendientes.md)).

2. ~~Probar login + búsqueda con un documento real~~ ✅ **HECHO (2-ago), y encontró
   un 500 en producción.** Login `200`; búsqueda con un documento real del padrón:
   **500**. `BuscarVictimaView` hacía `.get()` sobre `numero_documento_hash` y el
   documento estaba repetido — le pasa a **768.096 documentos** de 4.928.725
   (~15,6 % de las búsquedas posibles). Salió en el **primer** intento, sin
   buscarlo. Tres arreglos en `4b88856`, ya desplegados y verificados contra prod:

   | Camino | Antes | Ahora |
   |---|---|---|
   | `/api/victimas/buscar/` (frontend web) | **500** | **409** + `candidatos` + `ambiguo:true` + "CONFIRME cuál corresponde"; auditado con `coincidencias` |
   | `/api/victimas/consultar-fuente/` (APK) | avisaba "Hay 2 registros… CONFIRME" con `candidatos: 0` | manda los candidatos: el aviso ya se puede cumplir |
   | manifiesto del padrón | `total_registros` del contador del bucle | `count(*)` real + `registros_leidos` + `colisiones_documento` |

   La **APK nunca estuvo afectada** por el 500: usa `/consultar-fuente/`, que va por
   el repositorio (que sí manejaba los duplicados). El 500 lo veía el frontend web.
   ⏳ Queda **para Brando**: manejar el `409` en `srni-frontend` — hoy caería en el
   handler de error genérico. El body trae `detail`, `ambiguo` y `candidatos[]`.
   6 tests nuevos en `apps/victimas/tests/test_documento_duplicado.py`;
   suite **558 pass / 1 xfail**.

2-bis. ~~🚀 **DESPLEGAR**~~ ✅ **DESPLEGADO (2-ago).** Migraciones aplicadas:
   `hogares/0007`, `victimas/0008`, `victimas/0009`. La de datos **no tocó nada**:
   en prod hay 0 filas con `fuente_origen='NO_INCLUIDA'`/`'OFFLINE'` (las 5.926.004
   víctimas son padrón puro, todavía no hay altas manuales en producción).
   ⚠️ **Trampa del deploy, para la próxima:** al recrear `cz_backend` cambia su IP y
   `cz_nginx` se queda con la vieja cacheada → **502 en todo `/api/`** aunque
   gunicorn esté sano. Se arregla con `docker restart cz_nginx`. Verificar siempre
   con `curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/` **después**
   de recrear.
3. ~~Decidir la **etiqueta del alta manual**~~ ✅ **DECIDIDO Y APLICADO (1-ago).**
   Estado nuevo **`NO_VERIFICADO`** = *"no está en el padrón descargado"*, que no es
   *"no está en el RUV"*. Toca `Victima.ESTADO_RUV`, `MiembroHogar.ESTADO_INCLUSION`,
   la APK (payload, colores y textos) y tres migraciones —`victimas/0008`,
   `victimas/0009` (datos), `hogares/0007`—. De paso salieron tres defectos: la APK
   mandaba `fuente_origen='NO_INCLUIDA'`, que **no existe** en el modelo y entraba
   porque el serializer era un `CharField` suelto; el default del serializer era
   `NO_INCLUIDO`; y el padrón offline degradaba a `NO_INCLUIDO` todo lo que no viniera
   marcado `INCLUIDO`. 10 tests nuevos; suite 549 pass / 1 xfail.
   **Detalle en [`../ciclo_completo_tablas.md`](../ciclo_completo_tablas.md) §6.**
   ⏳ Queda **para Brando**: la clave `NO_VERIFICADO` en `ESTADO_RUV_BADGE` del
   frontend web (no rompe, solo no pinta el badge).
   🚀 **Al desplegar:** correr las migraciones — hay una de datos que reetiqueta las
   altas manuales ya grabadas.
4. Encender las tareas programadas cuando se quiera.
   Estado verificado el **2-ago**: siguen **apagadas** — no hay ninguna variable
   `PADRON_*` ni `SYNC_*` en el `.env` de prod, y los defaults son `False`.
   💡 **Recomendación: no encenderlas todavía.** `refrescar_fechas_padron` corre a
   diario y **regenera el SQLite**; hoy eso produciría cada noche un archivo de
   878 MB con los nombres en claro (1b y 1c abajo). Encenderlas después de decidir
   tamaño y cifrado, no antes.
   ⚠️ **Antes de encenderlas hacía falta un arreglo, ya hecho (1-ago).** El
   `UPDATE` de `cargar_fechas_caracterizacion` era **incondicional**: cruzaba por
   `cons_persona` y reescribía la fila aunque el valor ya fuera ese. Como
   `refrescar_fechas_padron` corre **a diario a las 03:30**, cada noche habría
   reescrito 3,3 M filas para dejarlas idénticas.
   No es una ineficiencia de manual: `victimas_victima` tiene **24 índices** y el
   UPDATE toca `habilitado_para_caracterizacion`, que está indexada — eso descarta
   el *HOT update*, así que cada fila cuesta **25 escrituras**. Medido en la corrida
   real: **8 h y seguía**, con 61 GB de WAL cada tres horas. La estimación del
   docstring (~12 min) estaba mal por un factor de 40, y ya está corregida con el
   número real.
   Ahora el cruce se materializa en una temporal (que no genera WAL), se marca ahí
   qué cambia de verdad, y el UPDATE va **por PK** solo sobre esas filas. El
   informe pasa a dar dos cifras: las que cruzan y las que se escribieron.
   SQL validado contra el PostgreSQL del servidor con tablas temporales y
   `ROLLBACK` (los tests corren en SQLite y **no** cubren ese camino — es la misma
   trampa de `9a35c18`, el `COPY` de psycopg2).
5. Las 5 preguntas para OTI — **borrador listo (1-ago)**:
   [`../gestion/correo_oti_identidad_padron.md`](../gestion/correo_oti_identidad_padron.md).
   Falta que Javier lo revise y lo mande. Ninguna de las cinco bloquea el despliegue;
   la 1 y la 3 son las que recuperarían al 24 % que quedó fuera del padrón.
6. `xfail` abierto: los capítulos D/E/F/G de ASISTENCIA ya no están cerrados a los
   incluidos en RUV (defecto funcional vivo; reponerlo exige regenerar bundle y
   validar en dispositivo).

---

## 0-bis. Actualización 2026-07-28 — **ESCALÓN 2 LOGRADO**

El corte de este documento (16-jul) quedó viejo. Estado real al 28-jul:

- ✅ **Escalón 1** (24-jul): primera escritura real end-to-end contra la réplica local.
- ✅ **Escalón 2** (28-jul): la **ruta geográfica** verificada. `11/11 VERIFICADO`,
  idempotente, y la respuesta geográfica **la resuelve Oracle**: `'5001' → Medellin /
  Antioquia`, con el mismo join que usan sus reportes.
- ✅ **El bloqueante del "entorno de Pruebas de OTI" se disolvió**: se probó que la ruta
  de escritura no lee `AP_GEOGRAFIA` (las 18 referencias están en `SP_CONSTANCIA_GAVE`,
  que no tiene llamadores; el cierre transitivo de la escritura son 17 subprogramas y
  ninguno usa dblink).
- 🐞 **Defecto real encontrado y corregido**: las preguntas de departamento/municipio
  guardaban el DANE **con** cero a la izquierda (`'05001'`) y Oracle espera `'5001'`
  (`GIC_MUNICIPIO.ID_MUNI_DEPTO`, medido: **28.151/28.151 = 100 %**). Rompía en silencio
  en 8 departamentos.
- 🔒 **Riesgo crítico corregido**: `--destino local` podía resolver a producción si la
  sesión tenía `ORACLE_LEGACY_HOST` exportado. Ahora aborta, y el comando imprime el DSN.
- 📋 **3a.11 con dato**: volcados los **266 puntos de atención** reales.
- **Tests: 134/134** en `apps/sincronizacion`. **Escrituras en producción: 0.**

> **Detalle completo en [`plan_escalon_2.md`](plan_escalon_2.md).** Lo de abajo es
> historia previa; donde contradiga a esta sección, manda esta sección.

---

## 0. Actualización 2026-07-22 — el catálogo COMPLETO ya está en el Oracle local

**Se cerró el bloqueo #1 (catálogo truncado).** En vez de reexportar por el cliente SQL,
se trajo el catálogo entero desde prod al Oracle **local**:

- **Método (cero footprint en prod):** `SELECT` directo de las 8 tablas de **catálogo**
  (sin PII) desde `30.0.1.9/ENTREVISTARN` (solo lectura) e `INSERT` en el Oracle local.
  No se creó `.dmp`, ni job, ni archivo en el server. Script reproducible:
  `srni-backend/scripts/cargar_catalogo_local.py` (lee `infra/oracle-local/.env.prod`,
  gitignored). **No** se trajo `GIC_N_RESPUESTASENCUESTA` (respuestas reales = sensible).
- **Cargado (9.316 filas, todas de definición):** `GIC_N_PREGUNTAS` 1108,
  `GIC_N_RESPUESTAS` 3686, `GIC_N_INSTRUMENTOXPREG` 903, `GIC_N_INSTRUMENTOXRESP` 3533,
  `GIC_INSTRUMENTO` 1, `GIC_TEMA` 69, `GIC_TIPOCARACTERIZACION` 2, `GIC_TIPODOC` 14.
- **`respuestas_oracle.json` REGENERADO → `cobertura: COMPLETO`** (antes: truncado a 200):
  **902 preguntas / 3069 respuestas / 43 huérfanas**. Export crudo versionado en
  `docs/oracle-legacy/query_a_v2_completo.tsv`. Comando:
  `generar_catalogo_respuestas ../docs/oracle-legacy/query_a_v2_completo.tsv --fecha 2026-07-22`
  (en Windows, con `PYTHONUTF8=1` o la consola revienta al imprimir `⇒`).
- **Confirmado con dato completo (no muestra):**
  - **Parentesco (preg 28):** 6 escribibles (`79,80,81,84,906,912`) = las 6 del manual =
    las 6 de SICAV; 7 huérfanas. **Falsa alarma cerrada, ahora con catálogo completo.**
    ⇒ el correo que escala esto como "defecto activo" hay que **corregirlo**, no ejecutarlo.
  - **Cédula (preg 30):** los 4 ids `93/3852/3853/3854` son **todos escribibles** →
    sigue siendo pregunta de negocio para Oscar (3a.13).
- **Nueva lista de curación:** las **43 huérfanas** completas ya salen en el reporte del
  comando. El default es "opciones retiradas" (como parentesco), pero **revisar contra el
  manual** algunas que llaman la atención: **preg 221/222 (hechos victimizantes:** Acto
  terrorista, Minas Antipersonal, Vinculación de NNA, Delitos contra libertad/integridad
  sexual**)** y las SI/NO de preg 1532-1535 — cotejar antes de concluir nada.
- ⚠️ **Se volvió a usar la clave de RNIENTREVISTA (solo lectura).** Sigue **pendiente de
  rotar** (3a.5) — coordinar con OTI. `.env.prod` es local y gitignored.
- **Reproducir todo:** `docker start srni-oracle-local` → `scripts/cargar_catalogo_local.py`
  → `generar_catalogo_respuestas ...`. Sin commitear (a revisión de Javier).

**Avance 2026-07-22 (cont.) — curación cruzada + crosswalk verificado:**
- Se cruzó SICAV ↔ catálogo completo: **0 pérdidas silenciosas reales**; 148 trivial /
  16 sustantiva / 12 mapeo-dudoso / 2 a Oscar (agente experto, contra el manual).
- **Crosswalk verificado** `apps/sincronizacion/oracle/crosswalk_opciones.json` (164
  mapeos SICAV→`res_idrespuesta`). **164/164 verificados: existen y son escribibles**.
  Clasificación: **104 CROSSWALK_SOLO** (dato puro, no toca instrumento — p.ej. `"Otro"`
  →`"Otro,¿cuál?"` es prompt de sub-campo) · **54 FIXTURE_REVISAR** (wording caso a caso)
  · **6 FIXTURE_FIX_TYPO** (typos claros de SICAV: `recolecion`, `ota`, `Combares`,
  `exploración`→`explotación`, `turiísticos`).
- **Hallazgo estructural:** `PR3_re` (Ayuda Humanitaria) está mapeado a `id_preg=92`
  (=rehabilitación) — id_preg mal. Revisar antes de escribir ese perfil.
- Propuesta y detalle: `docs/gestion/curacion_crosswalk_propuesta.md`. Normalizador
  reforzado (§2). Tests: **96/96**.

**Avance 2026-07-22 (cont. 2) — ejecutado:**
1. ✅ **Crosswalk WIREADO** en `resolver_res_idrespuesta` (consulta `crosswalk_opciones.json`
   como autoridad curada antes de fallar, verifica escribibilidad, sin fuzzy). Tests: **100/100**.
2. ✅ **Batch de fixture APLICADO** (en `main`, sin commitear): **21 correcciones** (6 typos +
   15 wording) → **79 ediciones en fixtures + 63 en bundles**, en 7 `perfil_*.json` + 6 bundles.
   Diff mínimo (88 líneas, verificado que es solo `etiqueta`), **fixture↔bundle 0 mismatches**.
   Detalle: `docs/gestion/batch_fixture_correcciones.md`. NO se bumpeó versión (correcciones
   cosméticas, in-place; el APK las toma en el próximo build).

**Avance 2026-07-23 — crosswalk reconciliado:**
- `main` mergeado al worktree (merge `1dd5928`): el worktree ya tiene el instrumento corregido.
- **Crosswalk reconciliado** (`crosswalk_opciones.json`): **164 → 148** mapeos. Se quitaron
  **16 entradas redundantes** (el label corregido ya == Oracle ⇒ el resolver cruza DIRECTO,
  p.ej. `Combates o bombardeos`, `Ninguno`, `Usufructo`) y se **re-clavaron 3** al label nuevo
  (`Rural disperso (vereda)`, pre 1164/1452/1461, que sigue ≠ Oracle `Parte rural disperso…`).
  `_meta.reconciliado` lo documenta. Test del typo reemplazado por uno del caso que sobrevive.
  **100 tests verdes.**

**Siguiente:**
1. **A Oscar:** familia NS/NR (M-series), pre1435 `del jefe`→`del responsable`, pre1503 mismatch,
   PR3_re id_preg, "Autodiligenciada"/"Cara a cara" (pre 2), Cédula 3854.
3. **`cargar_perfil --reemplazar`** de los 7 perfiles editados en el server (en el próximo deploy;
   el fixture es la fuente, la BD se regenera). ¿Bump de versión? Solo si se quiere que el sync
   empuje a dispositivos ya desplegados; para cosmético no hace falta.
4. 🔒 Rotar clave RNIENTREVISTA + borrar `.env.prod`. Commitear (main = instrumento; worktree = migración) cuando Javier revise.

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

- **Commiteado y pusheado** en `feat/oracle-legacy-writer` (ambos remotes, `origin` + `azure`):
  - `b504d79` — Etapa A + ResolverCatalogos (17 archivos).
  - `38e4bf0` — incrementos 6+7: cascada territorial cableada + `resolver_territorio`
    real (+ fix del diagnóstico de `t_victima`, redacción de `PRXP_TEXTORESPUESTA`).
  - `e57a99d` — `cargar_hogar_demo_oracle`, el escenario del Escalón 1.
  - `88cad0a` — este documento.
- **Todo en DRY-RUN.** La ruta `--confirmar` aborta a propósito hasta resolver los pendientes de negocio.
- **Tests:** 90/90 en `apps/sincronizacion`. La suite completa trae 7 fallos en
  `apps/formulario/tests/test_cargar_diccionario.py` que son **preexistentes**
  (verificado contra HEAD limpio), ajenos a este trabajo.
- Máquina de estados ejecuta ya los **cinco pasos**: HOGAR → PERSONA → MIEMBRO →
  TERRITORIO → RESPUESTA. Corrida real sobre un hogar: **10 pasos, todos DRY_RUN**.
  - **TERRITORIO resuelve ids REALES** contra el crosswalk (DT CENTRAL/TOLIMA/
    JORNADAS/ALVARADO → `id_dt=7, id_depto=30, id_pt=13, id_ma=32`). Único paso que
    sale **sin ningún pendiente**.
  - **RESPUESTA: el cruce ya resuelve a ids reales de Oracle.** `2/2` respuestas del
    demo limpias (`res=8` Zona/Cabecera, `res=69` Sexo/Mujer), con escribibilidad
    confirmada, y **`RXP_TIPOPREGUNTA` cableado** (`GE` para la de hogar, `IN` para la
    de persona). Ya **no** quedan `‹PEND:RES_IDRESPUESTA›`, `‹PEND:ESCRIBIBLE›` ni
    `‹PEND:RXP_TIPOPREGUNTA›`. Siguen marcados solo `PBANDERA` y `PPER_IDPREGUNTAPADRE`
    (+ `PPER_IDPERSONA` en las de nivel hogar), nunca inventados.
  - ⚠️ **El catálogo de respuestas cargado es PARCIAL** (temas 1-2): el export volvió
    truncado a 200 filas. El código lo sabe y lo declara — ver §3b-bis-C.2.
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

6. ~~**`PINS_IDINSTRUMENTO`**~~ ✅ **RESUELTO** (Query B): `GIC_INSTRUMENTO` tiene una
   sola fila (1=`CARACTERIZACION`). Oracle no separa por instrumento como SICAV: no
   había crosswalk que resolver. Es la constante `INS_IDINSTRUMENTO_CARACTERIZACION`.
7. ~~**`PRES_IDRESPUESTA`**~~ ✅ **RESUELTO** — y la hipótesis era **falsa**:
   `id_resp_vivanto` **NO** es `RES_IDRESPUESTA` (refutado 0/14: Mujer es 4599 en SICAV
   y 69 en Oracle). El puente bueno es `Pregunta.id_preg == PRE_IDPREGUNTA` (14/14) +
   opción por texto normalizado dentro de la pregunta. Hay test de regresión para que
   no vuelva a colarse: escribir 4599 no habría dado error, simplemente no habría escrito.
8. **`PPER_IDPERSONA` de preguntas de nivel HOGAR** — en SICAV llegan con
   `miembro=NULL` y el procedure exige un NUMBER. La cascada territorial usa el
   literal `'1'` como "persona del hogar"; extrapolarlo sería suponer. ¿Qué manda
   ahí la app vieja?
9. **`PBANDERA`** — con valor 1 dispara `SP_BORRADORESPUESTAS`, que **BORRA** las
   respuestas previas del hogar/instrumento; con 0 solo inserta. Qué corresponde en
   una migración es decisión de negocio, y el lado destructivo no se asume.
10. ~~**`RXP_TIPOPREGUNTA`**~~ ✅ **RESUELTO CON DATO (2026-07-16) — y sin negocio.**
    `SELECT DISTINCT RXP_TIPOPREGUNTA` en prod → **`{GE, IN}`**: mismo dominio que
    `PRE_TIPOPREGUNTA`. No era el tipo de widget, era el **nivel** (GE=hogar,
    IN=persona). ⇒ No hay crosswalk: se **copia** el valor que Oracle ya tiene para esa
    pregunta. Cableado; el DRY-RUN ya no marca `‹PEND:RXP_TIPOPREGUNTA›`.
    ⚠️ Falta el control fila-a-fila (§3b-bis-E.4): el `DISTINCT` prueba el dominio,
    no que la app vieja escriba el `PRE_TIPOPREGUNTA` de SU pregunta. Barato y pendiente.
12. ~~**10 respuestas que Oracle ofrece pero no sabe guardar** (7 parentescos)~~
    ❌ **NO EXISTE — falsa alarma mía, cerrada por el manual antes de escalarla.**
    Las 10 huérfanas son opciones que el manual **no declara** y que SICAV **no ofrece**
    (10/10): filas muertas del catálogo de Oracle, no un agujero funcional. El manual
    (11-MU pág. 56) lista 6 opciones de parentesco y son exactamente las 6 escribibles.
    Ver §3b-bis-E.3 — **no llevar a Oscar.**
13. 🆕 **`Cédula de ciudadanía / Contraseña` con 4 ids escribibles** (pregunta 30).
    **El único de los dos "hallazgos" del 2026-07-16 que sobrevivió.** El manual declara
    la opción una vez ⇒ sobran ids, pero no dice cuál surrogate es el vigente (no es
    dato del manual). Pregunta concreta + consulta de apoyo en §3b-bis-E.1.

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

### 3b-bis-A. RESULTADOS de las consultas (2026-07-16) — dos veredictos

Javier corrió las consultas. Lo que cambió:

**❌ REFUTADA — `id_resp_vivanto` NO es `RES_IDRESPUESTA`.** Cero de 14 coinciden:
Mujer es 4599 en SICAV y **69** en Oracle; Indígena 4565 vs **112**; Heterosexual
4602 vs **2351**; Cabecera municipal 4572 vs **8**. Haberla asumido habría escrito
ids ajenos —y como el procedure traga el `NO_DATA_FOUND`, sin error visible—.
Hay test de regresión (`test_no_usa_id_resp_vivanto`).

**✅ CONFIRMADO — el puente ya existía: `Pregunta.id_preg` == `PRE_IDPREGUNTA`.**
14/14 ids del volcado existen en SICAV y, comparando el texto de la pregunta, **52 de
59 coinciden** (39 idénticos tras normalizar + 13 compatibles). Ej.: `id_preg=5` →
'ZONA DE RESIDENCIA' en ambos lados; `id_preg=35` (Z4) → la de autorreconocimiento
étnico. ⇒ Las preguntas **no** se cruzan por texto: se cruzan por id. Solo las
**opciones** se cruzan por texto, y acotadas a su pregunta (2-14 candidatas).

**Query B — hay UN solo instrumento:** `GIC_INSTRUMENTO` = 1 fila, `1 =
'CARACTERIZACION'` (activo desde 2013-10-18). Oracle no modela el cuestionario por
instrumento como SICAV (que tiene 8): todo cuelga de ese id. ⇒ `INS_IDINSTRUMENTO`
deja de ser pendiente y pasa a **constante**. El `= 1` del WHERE nunca fue circular.

**Query C1 — dominio `'SI'`/`'NO'`**: la suposición original era correcta.

**Query C2 — 153 respuestas huérfanas** (sin fila en `GIC_N_INSTRUMENTOXRESP`): el
riesgo de NO_DATA_FOUND es real y medido. ⚠️ **Tenemos el CONTEO pero no la LISTA**,
así que todavía no se pueden excluir: ver 3b-bis-C.

**Query C3 — 0 y 0**: no hay preguntas ni respuestas en varios instrumentos ⇒ el
riesgo de TOO_MANY_ROWS por esa causa no existe (coherente con haber un instrumento).

### 3b-bis-B. Lo que YA quedó implementado (sin commitear, a revisión)

- `respuestas_oracle.json` — catálogo del volcado, **regenerado desde la Query A v2**
  (62 preguntas / 200 respuestas), ahora con `escribible` por fila y `pre_tipopregunta`.
  Export crudo versionado en `docs/oracle-legacy/query_a_v2_parcial_temas_1_2.tsv`.
- `resolver_ins_idinstrumento` → constante 1.
- `resolver_res_idrespuesta` → `id_preg`→`PRE_IDPREGUNTA`, luego opción por texto
  normalizado **dentro de esa pregunta**; error claro y accionable si no cruza.
- Escenario demo alineado al catálogo real (`DEMO_SEXO` id_preg=24 → 69;
  `DEMO_ZONA` id_preg=5 → 8), y el comando **verifica el cruce** y aborta si se rompe.
- 90/90 tests en `apps/sincronizacion`.

**Estado del DRY-RUN de `LISTO-96001` (2026-07-16, corrida limpia de 10 pasos):**

| | |
|---|---|
| Respuestas que resuelven **limpio** | **2/2** — `res=8` (Zona/Cabecera), `res=69` (Sexo/Mujer) |
| Respuestas pendientes de curaduría | **0** |
| `‹PEND:RES_IDRESPUESTA›` / `‹PEND:ESCRIBIBLE›` | **0** — desaparecieron los dos |
| Paso TERRITORIO | **LIMPIO** (único paso sin ningún pendiente) |

Los `‹PEND›` que siguen en el paso RESPUESTA **no son del resolver**: son
`RXP_TIPOPREGUNTA`, `PBANDERA`, `PPER_IDPREGUNTAPADRE` y `PPER_IDPERSONA(nivel_hogar)`
— los bloqueantes de negocio 3a.6-3a.11, intactos.

### 3b-bis-C. Lo que FALTA para cerrar RESPUESTA

1. ~~La LISTA de las 153 huérfanas~~ ✅ **RESUELTO** por la columna `ESCRIBIBLE` de la
   Query A v2. De las filas exportadas ya se **sabe** (no se supone) qué se puede
   escribir: 10 huérfanas identificadas. `escribibilidad_verificada: true`.
2. **El catálogo completo — SIGUE PENDIENTE, es lo único que bloquea.** El export v2
   volvió a llegar **truncado en exactamente 200 filas** (201 con cabecera): ese número
   redondo es la firma del cliente SQL cortando, no el final del instrumento. Cubre
   temas 1-2 (62 preguntas, hasta la 1158 / `IXP_ORDEN` 41) de un cuestionario que en
   SICAV tiene **290 preguntas con `id_preg`**.
   → **Reexportar a archivo** (`SPOOL` en SQL*Plus, o "export to file" en el cliente),
   no a la rejilla de resultados. El SQL de 3b-bis-D no lleva límite: el corte es del
   cliente.
   → El código ya convive con esto sin mentir: `_meta.completo: false`, y una pregunta
   ausente produce *"no está en el volcado — y eso NO quiere decir que no exista en
   Oracle"*, nunca *"no existe"*. Cuando llegue el export completo, `completo` pasa a
   `true` y el mensaje cambia solo.
3. **Curaduría manual** (no se resuelven con código, ver 3b-bis-E).

### 3b-bis-D. Query A v2 — catálogo + escribibilidad en una sola pasada

**Estado: CORRIDA el 2026-07-16, pero el export llegó truncado a 200 filas ⇒ hay que
REEXPORTARLA A ARCHIVO.** Lo que trajo funcionó (resultado crudo en
`docs/oracle-legacy/query_a_v2_parcial_temas_1_2.tsv`, cargado en el catálogo): la
columna `ESCRIBIBLE` cerró el pendiente de las huérfanas y `PRE_TIPOPREGUNTA` destapó
el hallazgo GE/IN de 3b-bis-E.4. Solo falta que no la corte el cliente.

> **El SQL no lleva `LIMIT` ni `ROWNUM`: el corte es del cliente.** Exportar **a
> archivo** (`SPOOL` en SQL*Plus, o "export to file" / "fetch all rows" en el cliente
> gráfico), no a la rejilla de resultados. Señal de que volvió a pasar: el archivo
> tiene exactamente 200 filas de datos y termina en la pregunta 1158.

`ESCRIBIBLE` marca lo que la Query C2 solo contaba, y `PRE_TIPOPREGUNTA` es candidato
a resolver `RXP_TIPOPREGUNTA` (3a.10).
**Sin `WHERE INS_IDINSTRUMENTO` ni límite de filas** (solo hay un instrumento).

```sql
SELECT
  ip.INS_IDINSTRUMENTO,
  ip.TEM_IDTEMA,
  ip.IXP_ORDEN,
  ip.PRE_TIPOPREGUNTA,
  pr.PRE_IDPREGUNTA,
  pr.PRE_PREGUNTA,
  re.RES_IDRESPUESTA,
  re.RES_RESPUESTA,
  re.RES_ACTIVA,
  CASE WHEN EXISTS (SELECT 1 FROM GIC_N_INSTRUMENTOXRESP ir
                    WHERE ir.RES_IDRESPUESTA = re.RES_IDRESPUESTA)
       THEN 'SI' ELSE 'NO' END AS ESCRIBIBLE
FROM GIC_N_INSTRUMENTOXPREG ip
JOIN GIC_N_PREGUNTAS pr ON pr.PRE_IDPREGUNTA = ip.PRE_IDPREGUNTA
JOIN GIC_N_RESPUESTAS re ON re.PRE_IDPREGUNTA = pr.PRE_IDPREGUNTA
WHERE re.RES_ACTIVA = 'SI'
ORDER BY ip.TEM_IDTEMA, ip.IXP_ORDEN, re.RES_IDRESPUESTA;
```

Con el resultado (ya hecho para la parte que llegó): se regenera `respuestas_oracle.json`
con `escribibilidad_verificada: true` + `escribible` por fila, y el DRY-RUN muestra
`pres_idrespuesta` limpio. Reproducible con el conversor
`scratchpad/tsv_a_catalogo_v2.py` (apuntarlo al TSV nuevo y volver a correr).

### 3b-bis-E. Casos de curaduría — **la autoridad es el MANUAL OFICIAL**

> 📌 **Regla del proyecto:** lo funcional (qué preguntas hay, qué opciones, con qué
> texto) lo decide el **manual oficial**, no el criterio de nadie: `11-MU` para
> Territorial y Étnicos, `14-MU` para Asistencia (`docs/perfiles/`, gitignored).
> A Oscar solo lo que el manual no cubra. Antes de marcar algo "pendiente de
> negocio", **mirar el manual primero**.

1. **`Cédula de ciudadanía / Contraseña` con 4 ids** (`93, 3852, 3853, 3854`) en la
   pregunta 30 — **sigue siendo decisión de negocio. Mi predicción falló.**

   > ⚠️ **Aquí decía que el filtro de escribibilidad iba a disolverlo solo.** La
   > hipótesis era que `3852-3854` serían huérfanas y que al descartarlas quedaría
   > `93`. La Query A v2 la **refutó**: los **4 ids están marcados `ESCRIBIBLE=SI`**.
   > El filtro no desempata nada aquí. Se deja escrito porque la teoría era mía y el
   > dato dijo que no; el test `test_el_filtro_de_escribibilidad_disuelve_la_falsa_
   > ambiguedad` se borró (fingía con `monkeypatch` unas huérfanas que no existen) y
   > lo sustituye `test_los_4_ids_de_cedula_son_todos_escribibles`, que fija el dato real.

   Dónde queda, aplicando la escalera:
   - **Peldaño 2 (escribibilidad):** no resuelve — los 4 son escribibles.
   - **Peldaño 3 (manual):** el 11-MU (B6) declara la opción **una sola vez**, y su
     lista de 11 opciones calza exacto con `93-96` + `3799-3805`. ⇒ Confirma que
     **sobran ids**… pero el manual habla de opciones funcionales, no de surrogates:
     **no dice cuál de los 4 es el vigente**. No puede: ese dato no es del manual.
   - **Peldaño 4 (Oscar):** ⇒ **aquí queda.** Es la pregunta exacta a llevarle:
     *"Oracle repite 'Cédula de ciudadanía / Contraseña' con 4 ids escribibles en la
     pregunta 30 y el manual declara la opción una sola vez. ¿Cuál id usamos?"*

   **USO REAL MEDIDO EN PROD (2026-07-16)** — y el resultado **no** es el que esperaba:

   | RES_IDRESPUESTA | usos | lectura |
   |---:|---:|---|
   | **93** | **29.338** | el mayoritario |
   | **3854** | **8.620** | ⚠️ **volumen real — NO es ruido** |
   | 3852 | 19 | ruido (error de captura / duplicado de catálogo) |
   | 3853 | 15 | ruido |

   **Esto es lo que impide resolverlo por código, y es la razón de que siga abierto.**
   Con 3852/3853 no hay discusión: 19 y 15 usos contra 29.338 es ruido. Pero **3854
   tiene 8.620 usos: hay algo real detrás.** Un id con ese volumen no es un duplicado
   accidental — responde a *algo* (¿un período distinto? ¿otro canal de captura?
   ¿una migración pasada? ¿un perfil concreto?). Elegir 93 "porque es el mayoritario"
   sería exactamente la suposición que este proyecto no se permite: si 3854 significa
   algo, mandar 93 en su lugar escribiría mal 8.620 casos… en silencio.

   ⇒ **Pendiente de negocio (3a.13). La pregunta exacta para Oscar:**
   > *"En la pregunta 30 (tipo de documento), Oracle tiene 4 ids escribibles con el
   > texto 'Cédula de ciudadanía / Contraseña' y el manual declara la opción una sola
   > vez. El uso real es 93 → 29.338, **3854 → 8.620**, 3852 → 19, 3853 → 15. Los dos
   > pequeños son claramente ruido. **¿Qué representa el 3854, que tiene volumen
   > significativo — un período distinto, otro canal de captura, una migración
   > anterior?** ¿Cuál debe usar SICAV al escribir?"*

   El resolver **NO** lo resuelve: sigue fallando con las 4 candidatas a la vista.
   Es lo correcto hasta que Oscar diga qué es 3854.

   *(SQL usado, verificado contra el esquema real — la columna de fecha es
   `USU_FECHACREACION`, no `RXP_FECHACREACION`, que fue mi primera suposición y no
   existe:)*

   ```sql
   SELECT RES_IDRESPUESTA, COUNT(*) AS USOS,
          MIN(USU_FECHACREACION) AS PRIMERO, MAX(USU_FECHACREACION) AS ULTIMO
   FROM GIC_N_RESPUESTASENCUESTA
   WHERE RES_IDRESPUESTA IN (93, 3852, 3853, 3854)
   GROUP BY RES_IDRESPUESTA ORDER BY USOS DESC;
   ```

   **Pista barata para la reunión:** las columnas `PRIMERO`/`ULTIMO` de esa misma
   consulta probablemente ya expliquen el 3854 (si sus fechas no se solapan con las de
   93, es un período/migración; si se solapan, es un canal paralelo). Mirar eso antes
   de la reunión puede convertir la pregunta en una confirmación.

2. **Los textos de opción divergen entre SICAV y Oracle** — no es cosa de acentos, y
   por eso no se aplica *fuzzy matching* (elegiría mal en silencio):

   | SICAV | Oracle |
   |---|---|
   | `Palenquero(a)` | `Palenquero (a)` |
   | `Rural disperso (vereda)` | `Parte rural disperso (vereda, campo)` |
   | `Negro(a), afrocolombiano(a)` | `Negro(a), afrocolombiano(a) o afrodescendiente` |

   Con territorio tuvimos suerte (21/21 DT idénticas). Aquí hace falta un crosswalk
   curado opción-a-opción **contra el texto del manual**, que es el que dice cuál es
   la redacción oficial y, por tanto, si las dos variantes son la misma opción. El
   resolver ya falla listando las candidatas reales de la pregunta, así que la
   curaduría se hace con los datos a la vista.

3. **🆕 Las 10 huérfanas del volcado: NO son un defecto — falsa alarma, cerrada por el
   manual.** ⚠️ **Esto estuvo a punto de escalarse a Oscar como "defecto activo de
   producción con prioridad". Habría sido un error.** Se deja documentado el episodio
   completo porque el mecanismo de la falsa alarma es instructivo.

   **Lo que parecía:** 10 respuestas sin fila en `GIC_N_INSTRUMENTOXRESP` ⇒ el
   procedure las traga con `NO_DATA_FOUND` y no escribe nada sin avisar. **7 de las 13
   opciones de parentesco (pregunta 28)** entre ellas: `Nieto(a)`, `Yerno o nuera`,
   `Abuelo(a)`, `Suegro(a)`, `Tío(a)`, `Sobrino(a)`, `Otros no parientes`. Leído así,
   un hogar extenso no podría registrar el parentesco de sus miembros — grave, y en un
   censo de víctimas los hogares extensos son lo normal.

   **Lo que dice el manual** (11-MU pág. 56, *"El parentesco … frente al jefe del hogar
   es:"*): lista **exactamente 6 opciones** — Jefe(a), Cónyuge o Compañera(o),
   Hijo(a)-Hijastro(a), Padre o madre-Padrastro o madrastra, Hermano(a)-Hermanastro(a),
   **Otro pariente del jefe**. Las 7 "huérfanas" **no están en el manual**: son
   categorías que se absorbieron en *"otro pariente del jefe"*.

   **Los tres lados coinciden:**

   | | opciones de la pregunta 28 |
   |---|---|
   | Manual 11-MU (pág. 56) | **6** |
   | SICAV (`formulario.OpcionRespuesta`) | **6** — las mismas |
   | Oracle **escribibles** | **6** — las mismas (`79, 80, 81, 84, 906, 912`) |
   | Oracle huérfanas | 7 — las que el manual no declara |

   Verificado además **10/10: SICAV no ofrece NINGUNA de las 10 huérfanas** (tampoco
   `No sabe/no informa`, `En trámite` ni `Porque nació así`).
   ⇒ **No hay defecto, ni pérdida de datos, ni nada que escalar.** La escribibilidad de
   Oracle **implementa el manual**: es el mecanismo con que retira opciones que dejaron
   de ser oficiales, igual que los 3 ids de más de Cédula. Filas muertas de catálogo.

   **Dato que descarta la otra hipótesis:** la pregunta 1435 (*"…frente a la persona
   responsable del hogar"*, 6 opciones, todas escribibles) **no es la sustituta** de la
   28 — el manual (B24) dice que *"solo se habilita para el perfil Buenaventura"*.

   **Lo que sí queda, y es útil:** el guard sigue fallando ruidosamente, pero ahora
   apunta a donde toca. Si algún día SICAV manda una huérfana, el hallazgo no es sobre
   Oracle: es que **el instrumento de SICAV se desvió del manual**. El filtro es, de
   hecho, un **detector de deriva SICAV↔manual** gratis.

   **La lección del episodio** (por eso se conserva escrito): tenía el mecanismo bien
   —el `NO_DATA_FOUND` tragado es real y está verificado en el PL/SQL— y aun así la
   conclusión era falsa, porque nunca comprobé si alguien llega a mandar esas opciones.
   *Un fallo silencioso en una ruta que nadie recorre no es un fallo.* La regla del
   proyecto (**mirar el manual ANTES de escalar**) es justo lo que lo atajó.
   ⚠️ Con el export completo saldrán las otras ~143 huérfanas: **el default es que
   sean lo mismo** (opciones retiradas). Antes de alarmarse por ninguna, cotejarla
   contra el manual y contra lo que SICAV ofrece.

4. **🆕 `PRE_TIPOPREGUNTA` es el NIVEL, no el tipo — pista fuerte para 3a.10.**
   Vale `GE`/`IN`. Pese al nombre no es el widget (radio/texto): cruzando las 62
   preguntas del volcado contra `Pregunta.nivel` de SICAV —que se llenó aparte,
   leyendo el manual— concuerdan **61 de 63**:

   | Oracle | SICAV | n |
   |---|---|---|
   | `GE` | HOGAR | 18 |
   | `IN` | PERSONA | 43 |
   | `IN` | HOGAR | **2** ← |

   Y **las 2 excepciones refuerzan la lectura en vez de romperla: en las dos, Oracle
   tiene razón y el que está mal es SICAV.** Consultado el manual (regla del proyecto):
   - **Pregunta 8 — Celular.** 11-MU pág. 45, **A11**, textual: *"Campo abierto.
     Numérico. **Se habilita para cada una de las personas del hogar.**"* ⇒ es PERSONA.
     Oracle dice `IN` ✅. SICAV lo tiene en HOGAR ❌ — **defecto de SICAV**.
   - **Pregunta 35 — Autorreconocimiento étnico.** El manual (A4, pág. 42) **no
     declara el nivel de forma literal** en esa página; lo que hay es el pendiente
     funcional ya registrado del 24-jun ("pertenencia étnica **por persona**") y el
     propio texto de A4, dirigido a un individuo. ⇒ **Corrobora a Oracle (`IN`), pero
     con evidencia más floja que A11**: no lo doy por cerrado igual que el celular.

   **Por qué NO se cableó todavía:** falta probar que `RXP_TIPOPREGUNTA` (el bind del
   procedure) comparta dominio con `PRE_TIPOPREGUNTA`. Los nombres se parecen y sería
   el origen natural del dato — pero *"se parece"* no es evidencia, y ya nos mordió
   una vez (`id_resp_vivanto` también se parecía). **Un renglón lo cierra:**

   ```sql
   SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA ORDER BY 1;
   ```

   Si sale `{GE, IN}`, el pendiente **3a.10 se resuelve sin crosswalk y sin negocio**:
   se copia el valor que el propio Oracle ya tiene para esa pregunta, y el DRY-RUN
   pierde el `‹PEND:RXP_TIPOPREGUNTA(RADIO)›` (ese `RADIO` de ahora es el widget de
   SICAV: dominio equivocado, no lo mandes así).

   **Control que lo prueba de verdad** (que salga `{GE, IN}` es necesario pero no
   suficiente: hay que ver que el valor escrito coincida con el nivel de SU pregunta).
   Si la diagonal `GE/GE` + `IN/IN` concentra casi todo, está probado; si está
   repartido, la corazonada era falsa y no se cablea:

   ```sql
   SELECT re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA, COUNT(*) AS N
   FROM GIC_N_RESPUESTASENCUESTA re
   JOIN GIC_N_RESPUESTAS rs ON rs.RES_IDRESPUESTA = re.RES_IDRESPUESTA
   JOIN GIC_N_INSTRUMENTOXPREG ip ON ip.PRE_IDPREGUNTA = rs.PRE_IDPREGUNTA
   GROUP BY re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA ORDER BY N DESC;
   ```

   *(Los 3 SQL de esta sección parsean contra el esquema real — validados en el Oracle
   local, que tiene la estructura de prod.)*

   **Regalo aparte:** esto detectó **2 defectos en el instrumento de SICAV** (preguntas
   8 y 35 con `nivel` equivocado). No es de esta migración — va a la lista del
   instrumento territorial.

### 3b-bis. Contexto original — desbloquear RESPUESTA con datos reales de Oracle

Es **el** incremento técnico que queda, y no arranca sin dato: hoy el paso RESPUESTA
escribe `‹PEND:...›` en `PRES_IDRESPUESTA`, `PINS_IDINSTRUMENTO` y
`PRXP_TIPOPREGUNTA` porque SICAV no tiene los ids de Oracle (3a.6, 3a.7, 3a.10).
El plan es el mismo que funcionó con territorio: traer el catálogo real y **cruzar
por nombre/significado, nunca por id** (los ids de Oracle son surrogate).

#### Paso 1 — Javier corre estos SELECT contra prod (solo lectura, sin PII) y pega el resultado

**Query A — catálogo de respuestas del instrumento** (la consulta base):

```sql
-- Catálogo de respuestas del instrumento, con texto de pregunta para
-- poder cruzar por nombre/significado (igual que se hizo con territorio)
SELECT
  ip.INS_IDINSTRUMENTO,
  ip.TEM_IDTEMA,
  pr.PRE_IDPREGUNTA,
  pr.PRE_PREGUNTA,
  re.RES_IDRESPUESTA,
  re.RES_RESPUESTA,
  re.RES_ACTIVA
FROM GIC_N_INSTRUMENTOXPREG ip
JOIN GIC_N_PREGUNTAS pr ON pr.PRE_IDPREGUNTA = ip.PRE_IDPREGUNTA
JOIN GIC_N_RESPUESTAS re ON re.PRE_IDPREGUNTA = pr.PRE_IDPREGUNTA
WHERE ip.INS_IDINSTRUMENTO = 1  -- ajustar al instrumento real (ver Query B)
  AND re.RES_ACTIVA = 'SI'
ORDER BY ip.TEM_IDTEMA, ip.IXP_ORDEN, re.RES_IDRESPUESTA;
```

> ✅ **Verificada contra el esquema real** (Oracle local, `user_tab_columns`,
> 2026-07-16): las 3 tablas y las 7 columnas existen con esos nombres exactos.
> La consulta corre tal cual.
>
> ⚠️ Dos ajustes que conviene hacer **antes** de correrla:
> - **`INS_IDINSTRUMENTO = 1` es circular**: ese id es justo lo que buscamos (3a.6).
>   Correr primero la Query B para elegirlo. Ojo: el catálogo se llama
>   **`GIC_INSTRUMENTO`**, sin el `_N` (`GIC_N_INSTRUMENTO` NO existe).
> - **`RES_ACTIVA = 'SI'` es una suposición sobre el dominio.** La columna es
>   `NVARCHAR2(4)` y **no tiene CHECK** que la acote (verificado), así que podría ser
>   `'S'`/`'N'` y el filtro devolvería 0 filas — pareciendo "catálogo vacío" en vez de
>   "filtro mal". Sacar el filtro en la primera corrida, o mirar el
>   `SELECT DISTINCT RES_ACTIVA FROM GIC_N_RESPUESTAS;` de la Query C.

**Query B — instrumentos disponibles** (rompe la circularidad y da el cruce por nombre
contra `formulario.Instrumento` de SICAV):

```sql
SELECT INS_IDINSTRUMENTO, INS_NOMBREINSTRUMENTO, INS_ACTIVO,
       INS_FECHAINICIO, INS_FECHAFIN
FROM GIC_INSTRUMENTO
ORDER BY INS_IDINSTRUMENTO;
```

**Query C — chequeos de los dos fallos SILENCIOSOS del procedure** (esto es lo que
decide qué respuestas son escribibles de verdad — ver la explicación abajo):

```sql
-- C1. Dominio real de las banderas (¿'SI'/'NO'? ¿'S'/'N'?)
SELECT DISTINCT RES_ACTIVA FROM GIC_N_RESPUESTAS;

-- C2. NO_DATA_FOUND: respuestas SIN fila en GIC_N_INSTRUMENTOXRESP.
--     El procedure hace SELECT ... INTO sobre esa tabla ⇒ si no hay fila,
--     no escribe NADA y no avisa.
SELECT COUNT(*) AS respuestas_sin_instrumentoxresp
FROM GIC_N_RESPUESTAS re
WHERE NOT EXISTS (SELECT 1 FROM GIC_N_INSTRUMENTOXRESP ir
                  WHERE ir.RES_IDRESPUESTA = re.RES_IDRESPUESTA);

-- C3. TOO_MANY_ROWS: preguntas que viven en MÁS DE UN instrumento, y
--     respuestas registradas para más de un instrumento. Ambos rompen los
--     SELECT ... INTO del procedure, también en silencio.
SELECT COUNT(*) AS preguntas_en_varios_instrumentos FROM (
  SELECT PRE_IDPREGUNTA FROM GIC_N_INSTRUMENTOXPREG
  GROUP BY PRE_IDPREGUNTA HAVING COUNT(DISTINCT INS_IDINSTRUMENTO) > 1);

SELECT COUNT(*) AS respuestas_en_varios_instrumentos FROM (
  SELECT RES_IDRESPUESTA FROM GIC_N_INSTRUMENTOXRESP
  GROUP BY RES_IDRESPUESTA HAVING COUNT(DISTINCT INS_IDINSTRUMENTO) > 1);
```

**Opcional pero útil — Query D:** `GIC_N_INSTRUMENTOXPREG.TEM_IDTEMA` referencia
**`GIC_TEMA`** (singular; `GIC_TEMAS` en plural es otra cosa, metadata de cruces de
reporte). El "tema" es el equivalente del **Capítulo** de SICAV, así que traer su
nombre permite cruzar también ese nivel:

```sql
SELECT TEM_IDTEMA, TEM_NOMBRETEMA, TEM_ACTIVO, TEM_ORDEN
FROM GIC_TEMA ORDER BY TEM_ORDEN;
```

`GIC_N_INSTRUMENTOXRESP` además trae `RES_ORDENRESPUESTA`, `RES_OBLIGATORIO` y
**`RES_FINALIZA`** — que es exactamente el `OpcionRespuesta.finaliza_capitulo` de
SICAV (el viejo RESFINALIZA del APK). Sirve como verificación cruzada del mapeo.

#### Por qué las Query C importan (los dos fallos silenciosos)

`SP_SET_RESPUESTAS_DE_ENCUESTA` abre con **dos `SELECT ... INTO` sin filtrar por
instrumento** (body líneas 23-29):

```sql
SELECT PR.IXP_ORDEN INTO pOrden FROM GIC_N_INSTRUMENTOXPREG PR
JOIN GIC_N_RESPUESTAS RE ON RE.PRE_IDPREGUNTA = PR.PRE_IDPREGUNTA
WHERE RE.RES_IDRESPUESTA = pres_IdRespuesta;          -- sin AND INS_IDINSTRUMENTO

SELECT COALESCE(VAL_IDVALIDADOR,0), VAL_IDVALIDADOR_DEF INTO pValidador, textVal
FROM GIC_N_INSTRUMENTOXRESP WHERE RES_IDRESPUESTA = pres_IdRespuesta;
```

Como el `EXCEPTION WHEN OTHERS` del procedure se traga todo, hay dos formas de que la
escritura **no ocurra y nadie se entere**:
- **NO_DATA_FOUND** — la respuesta no tiene fila en `GIC_N_INSTRUMENTOXRESP` (C2).
- **TOO_MANY_ROWS** — la pregunta está en más de un instrumento, o la respuesta está
  registrada para varios: el `SELECT INTO` recibe 2+ filas y revienta (C3).

⇒ **No todo `RES_IDRESPUESTA` es escribible.** Si C2/C3 dan > 0, el resolver tendrá
que excluir esos casos explícitamente en vez de confiar en que el procedure avise.
Mejor descubrirlo en el SELECT que con el hogar a medio escribir.

#### Paso 2 — Con el resultado pegado, yo hago (sigue en DRY-RUN, sin commitear)

1. **Resolver de respuestas** en `ResolverCatalogos`: cruce **por texto** de
   pregunta/respuesta contra `formulario.Pregunta` / `formulario.OpcionRespuesta`,
   con la misma normalización que territorio (mayúsculas, acentos, espacios) y el
   mismo criterio: si no hay match, **error claro**, nunca un id inventado.
   Se aprovechará para **contrastar la hipótesis `id_resp_vivanto == RES_IDRESPUESTA`**
   (3a.7): si el cruce por texto coincide con el `id_resp_vivanto` que ya trae SICAV,
   queda confirmada; si no, gana el texto y lo reportamos.
2. **Cablear** ese resolver en `paso_respuesta` de `escritor.py`, quitando los
   `‹PEND:›` que hoy tapan `PRES_IDRESPUESTA` / `PINS_IDINSTRUMENTO` /
   `PRXP_TIPOPREGUNTA`.
3. **Tests** del resolver (incluidos los casos de C2/C3 si aparecen) + re-correr
   `escribir_a_oracle --hogar LISTO-96001` en DRY-RUN con los **10 pasos y sin ningún
   `‹PEND:RESPUESTA...›`**.
4. **Ajustar `cargar_hogar_demo_oracle`** si hace falta: hoy siembra el primer
   `Instrumento` activo de SICAV y dos preguntas demo (`DEMO_SEXO`, `DEMO_ZONA`) con
   `id_resp_vivanto` 4599/4572. Si el instrumento real de Oracle no las tiene, el
   escenario debe sembrar preguntas que **sí** existan en el catálogo, o el Escalón 1
   no probaría nada.

**Lo que seguirá pendiente aunque llegue este SELECT** (no lo desbloquea): `PBANDERA`
(3a.9), `PPER_IDPERSONA` de nivel hogar (3a.8), usuario/perfil de servicio (3a.1) y
`T_VICTIMA` (3a.2). Sin esos cuatro, `--confirmar` sigue bloqueado aunque RESPUESTA
resuelva sus ids.
- 13. **Territorio con varias sesiones** — `GIC_N_RELACION_DT_PUNTO` admite **una sola
  fila por hogar** (PK `hogarcodigo`+`idpersona='1'`). El escritor toma la PRIMERA
  sesión. Si un hogar puede tener sesiones con territorios distintos, Oracle solo
  guarda uno: confirmar si ese caso existe.

### 3c. Después (no ahora)
- Escalón 1 del rollout: 1 hogar contra Oracle **local** con `--confirmar` (requiere ResolverCatalogos completo + tu aprobación).
- Etapa B (escritura directa Django) — fase separada, cuando se retire la app vieja.

---

## 3d. 🌅 MAÑANA (17-jul) — lista corta, en orden

**1. El re-export completo** (lo único que bloquea de verdad). Con `SPOOL`, no la
grilla. Al llegar:
```
python manage.py generar_catalogo_respuestas <tsv> --fecha 2026-07-17
```
Si el comando NO avisa de truncado y dice `cobertura: COMPLETO`, está bien.

**2. Tres consultas de un renglón, ya validadas contra el esquema real.** Las dos
primeras pueden **cerrar pendientes de negocio sin reunión**:

```sql
-- (a) 3a.8: ¿qué PER_IDPERSONA usa Oracle en las respuestas de nivel HOGAR?
--     Ahora que sabemos que GE = hogar, esto se MIDE en vez de preguntarse.
--     Si sale un valor convencional (p.ej. siempre la persona 1 del hogar), 3a.8 cae.
SELECT PER_IDPERSONA, COUNT(*) AS N FROM GIC_N_RESPUESTASENCUESTA
WHERE RXP_TIPOPREGUNTA = 'GE' GROUP BY PER_IDPERSONA
ORDER BY N DESC FETCH FIRST 10 ROWS ONLY;

-- (b) 3a.9 (PBANDERA): ¿Oracle guarda UNA respuesta por hogar+pregunta, o varias?
--     Si es siempre 1, la app vieja borra antes de insertar (PBANDERA=1) y lo sabemos
--     sin arriesgar el lado destructivo. Si hay N>1, acumula (PBANDERA=0).
SELECT N_POR_PREGUNTA, COUNT(*) AS HOGARES FROM (
  SELECT re.HOG_CODIGO, rs.PRE_IDPREGUNTA, COUNT(*) AS N_POR_PREGUNTA
  FROM GIC_N_RESPUESTASENCUESTA re
  JOIN GIC_N_RESPUESTAS rs ON rs.RES_IDRESPUESTA = re.RES_IDRESPUESTA
  GROUP BY re.HOG_CODIGO, rs.PRE_IDPREGUNTA)
GROUP BY N_POR_PREGUNTA ORDER BY N_POR_PREGUNTA;

-- (c) Control pendiente de RXP_TIPOPREGUNTA (§3b-bis-E.4): el DISTINCT probó el
--     dominio, esto prueba la correspondencia fila a fila. Si la diagonal GE/GE + IN/IN
--     no concentra casi todo, hay que descablearlo.
SELECT re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA, COUNT(*) AS N
FROM GIC_N_RESPUESTASENCUESTA re
JOIN GIC_N_RESPUESTAS rs ON rs.RES_IDRESPUESTA = re.RES_IDRESPUESTA
JOIN GIC_N_INSTRUMENTOXPREG ip ON ip.PRE_IDPREGUNTA = rs.PRE_IDPREGUNTA
GROUP BY re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA ORDER BY N DESC;
```

**3. Para la reunión con Oscar** — solo lo que el manual no puede responder:
- **3a.13 Cédula:** *¿qué representa el id 3854 (8.620 usos)?* Llevar los 4 números.
  Truco: las fechas `PRIMERO`/`ULTIMO` de la consulta de §3b-bis-E.1 puede que ya lo
  expliquen solas ⇒ mirarlas antes y convertir la pregunta en una confirmación.
- **3a.5 rotar la clave de RNIENTREVISTA** (con OTI). Es el pendiente más viejo.
- **3a.11 catálogo oficial de puntos de atención** (7 Centros Regionales de SICAV no
  existen en Oracle).
- 3a.2 (mapeo P8) y 3a.3 (PE/NES).

**4. Commitear** lo de julio cuando lo revises (hoy quedó todo sin commitear a
propósito).

**Lo que NO hay que hacer mañana:** escalar lo de las 7 opciones de parentesco. Es
falsa alarma cerrada (§3b-bis-E.3).

---

## 4. Con qué EMPEZAR la próxima sesión (recomendación)

**El resolver de respuestas ya está y funciona** (2/2 del demo a ids reales). Lo que
queda no lo desbloquea el código:

1. **Reexportar la Query A v2 SIN que la corte el cliente** (§3b-bis-D). Es lo más
   barato y lo que más destraba: da el catálogo de los ~228 preguntas que faltan, la
   lista completa de huérfanas (van 10 de 153) y el resto de casos de curaduría.
   **A archivo, no a la rejilla.** Luego:
   `python manage.py generar_catalogo_respuestas <tsv> --fecha <YYYY-MM-DD>` y listo.
2. **Dos consultas de un renglón que pueden cerrar pendientes enteros** (solo lectura):
   - `SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA;` → si sale
     `{GE, IN}`, **3a.10 se resuelve sin negocio** (§3b-bis-E.4).
   - El conteo de usos de los 4 ids de Cédula (§3b-bis-E.1) → convierte la pregunta a
     Oscar en un dato, no en una opinión.
   Ojo: la clave de RNIENTREVISTA **está pendiente de rotar** (3a.5); coordinar.
3. **Con Oscar** (lo que el manual no cubre): 3a.8 (`PPER_IDPERSONA` nivel hogar),
   3a.9 (`PBANDERA`), 3a.11 (puntos de atención), 3a.12 (las 7 opciones de parentesco
   que Oracle no sabe guardar) y 3a.13 (cuál id de Cédula).
4. Con eso, el escalón 1 contra el Oracle **local** sale solo.

---

## 5. Qué DECIR la próxima sesión (prompt listo para pegar)

**Si ya reexportaste la Query A v2 completa** (el camino previsto):

> Retomamos la migración Oracle legacy → SICAV, worktree `feat/oracle-legacy-writer`.
> Lee `docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md`; el estado está en **§3b-bis-B/C**.
> Sigue todo en **DRY-RUN, solo lectura**.
>
> Ya tengo el export completo de la Query A v2 (sin truncar) en `<ruta del TSV>`.
> Regenera el catálogo con `generar_catalogo_respuestas`, comprueba que `completo`
> quede en `true`, y dime: (a) cuántas de las 153 huérfanas aparecen y en qué
> preguntas — sobre todo si hay más agujeros como el de parentesco (§3b-bis-E.3);
> (b) cuántas opciones de SICAV **no cruzan por texto** con Oracle, que es la lista
> de curaduría real contra el manual; (c) si sigue habiendo textos duplicados con
> varios ids escribibles además del de Cédula.
> Tests + re-correr `escribir_a_oracle --hogar LISTO-96001` en DRY-RUN.
> Lo que no cruce, pendiente: **nada de fuzzy matching**, y ante duda funcional manda
> el **manual** (11-MU/14-MU) antes que escalar a Oscar. No commitees hasta que revise.

**Si además corriste el `SELECT DISTINCT RXP_TIPOPREGUNTA`**, añade:

> Y el `SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA` dio: `<...>`.
> Si es `{GE, IN}`, cablea `RXP_TIPOPREGUNTA` desde el `pre_tipopregunta` del catálogo
> (§3b-bis-E.4) y quita ese pendiente.

**Si todavía no hay export**, lo que queda son los bloqueantes de §3a. Ver §4.

---

## 6. Punteros rápidos

- Código Etapa A: `srni-backend/apps/sincronizacion/` (models, oracle/, management/, tests/).
- Crosswalk catálogos: `apps/sincronizacion/oracle/catalogos.py` + `catalogos_oracle.json`.
- Catálogo de respuestas: `apps/sincronizacion/oracle/respuestas_oracle.json` (**generado,
  no se edita a mano**) ← `docs/oracle-legacy/query_a_v2_parcial_temas_1_2.tsv`
  vía `python manage.py generar_catalogo_respuestas <tsv> --fecha <YYYY-MM-DD>`.
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
