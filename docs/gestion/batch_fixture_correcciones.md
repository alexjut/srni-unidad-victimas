# Batch de correcciones de etiqueta al FIXTURE (SICAV vs Manual)

**Estado:** PROPUESTA para revision. Este documento NO edita ningun fixture; describe el lote exacto a aplicar en UNA sola pasada.
**Fecha:** 2026-07-22
**Autoridad:** Manual oficial 11-MU (Territorial/Etnicos) y 14-MU (Asistencia). Ante duda, MANDA EL MANUAL.
**Insumos:** `crosswalk_opciones.json` (acciones `FIXTURE_FIX_TYPO`=6 y `FIXTURE_REVISAR`=54; se ignoran los 104 `CROSSWALK_SOLO`) + `curacion_crosswalk_propuesta.md`.
**Alcance:** SOLO edicion de la cadena `etiqueta`. No se agregan/quitan opciones ni se toca `valor`, `id_resp_vivanto` u `orden`.

---

## 1. Resumen

| | Cant. | Detalle |
|---|---:|---|
| **APLICAR** | **21** | 6 typos seguros (`FIXTURE_FIX_TYPO`) + 15 de wording/artefacto confirmados contra el manual (de `FIXTURE_REVISAR`). |
| **NO TOCAR** | **39** | Todas de `FIXTURE_REVISAR`: variantes lexicas, rewordings substantivos, typos de Oracle, targets truncados o mismatches. |
| Archivos afectados | **7** | Todos `perfil_*.json`. **0 cambios en `opciones_compartidas.json`.** |
| Ediciones de string | **~79** | Varias opciones viven **inline duplicadas** en varios perfiles (misma cadena en cada archivo listado). |

Hallazgo transversal: **ninguna** de las 21 correcciones vive en el catalogo compartido `opciones_compartidas.json`; todas son **opciones inline** dentro de `preguntas[].opciones[]`. Como la misma opcion esta duplicada en varios perfiles, la misma edicion `actual -> nueva` debe repetirse en cada archivo de la columna "Archivos".

### ⚠️ Regla de aplicacion (critica)

Editar **localizando la opcion por `id_preg` (= `codigo_externo`) + `id_resp_vivanto`**, NO por find/replace ciego de la cadena. Muchas de estas etiquetas (`Ninguna`, `Otra`, `Otra ¿Cuál?`, `En Usufructo**`, `Rural disperso (vereda,)`, `No Sabe/No Responde`) aparecen en decenas de opciones distintas; un reemplazo global corromperia opciones no relacionadas.

### Leyenda de archivos (`srni-backend/apps/formulario/fixtures/`)

| tok | archivo | perfil |
|---|---|---|
| T8 | `perfil_territorial_v8.json` | TERRITORIAL (vigente) |
| T7 | `perfil_territorial_v7.json` | TERRITORIAL (version previa; patchear solo si se mantiene) |
| BV | `perfil_buenaventura_v7.json` | BUENAVENTURA |
| SA | `perfil_san_andres_v7.json` | SAN_ANDRES |
| UE | `perfil_urbano_etnico_v1.json` | URBANO_ETNICO |
| TEL | `perfil_telefonico_v8.json` | TELEFONICO |
| AS | `perfil_asistencia_v8.json` | ASISTENCIA |

---

## 2. Tabla APLICAR (21)

Ubicacion de todas: **inline** en `preguntas[].opciones[]` (ningun `$ref`). Localizar por `codigo_externo`+`id_resp_vivanto`.

| tipo | pre_id | res_id (`id_resp_vivanto`) | cód | etiqueta ACTUAL (exacta) | etiqueta NUEVA (exacta, manual) | Archivos | pág. manual |
|---|---:|---:|---|---|---|---|---|
| TYPO | 49 | 176 | D13A | `Por recolecion pública o privada` | `Por recolección pública o privada` | BV · SA · T7 · T8 · UE | TERR p73 |
| TYPO | 300 | 2369 | D10 | `De ota fuente por tubería (Redes comunitarias)` | `De otra fuente por tubería (Redes comunitarias)` | BV · SA · T7 · T8 · UE | TERR p72 |
| TYPO | 872 | 2644 | C17A | `Combares o bombardeos` | `Combates o bombardeos` | BV · SA · T7 · T8 · UE | TERR p76 |
| TYPO | 872 | 2642 | C17A | `Exploración y exploración minero-energética (petróleo, gas etc)` | `Exploración y explotación minero-energética (petróleo, gas etc)` | BV · SA · T7 · T8 · UE | TERR p76 |
| TYPO | 872 | 2647 | C17A | `Megaproyectos de infraestructura y/o turiísticos (represas, hotelería etc.)` | `Megaproyectos de infraestructura y/o turísticos (represas, hotelería etc)` | BV · SA · T7 · T8 · UE | TERR p76 |
| TYPO | 1504 | 4754 | D13A_tel | `Por recolecion pública o privada` | `Por recolección pública o privada` | AS | ASIS p58 |
| REV | 36 | 1064 | C1 | `Otra vivienda  (carpa, vagón, cueva, refugio natural,albergue, embarcación, campamento, Asentameinto fluvial, rancho, etc)` | `Otra vivienda  (carpa, vagón, cueva, refugio natural,albergue, embarcación, campamento, Asentamiento fluvial, rancho, etc)` | BV · SA · T7 · T8 · UE | TERR p65 |
| REV | 45 | 164 | D5 | `En Usufructo**` | `Usufructo` | BV · SA · T7 · T8 · UE | TERR p67 |
| REV | 49 | 179 | D13A | `la queman o entierran` | `Las queman o entierran` | BV · SA · T7 · T8 · UE | TERR p73 |
| REV | 76 | 261 | G7B_GRADO | `Ninguna` | `Ninguno` | BV · SA · T7 · T8 | TERR p84 |
| REV | 76 | 263 | G7B_GRADO | `Básica_primaria_1°_a_5°` | `Básica primaria (1º - 5º)` | BV · SA · T7 · T8 | TERR p84 |
| REV | 76 | 264 | G7B_GRADO | `Básica_Secundaria_6°_a_9°` | `Básica secundaria (6º - 9º)` | BV · SA · T7 · T8 | TERR p84 |
| REV | 76 | 265 | G7B_GRADO | `Media_10°_a_13°` | `Media (10º - 13º)` | BV · SA · T7 · T8 | TERR p84 |
| REV | 124 | 424 | L6 | `Puso consultó avisos clasificados` | `Puso o consultó avisos clasificados` | BV · SA · T7 · T8 | TERR p108 |
| REV | 812 | 2414 | I28A | `Comunitaria` | `Comunitario` | BV · SA · TEL · T7 · T8 | TERR p97 |
| REV | 849 | 2592 | PL24 | `Otra ¿Cuál?` | `Otro ¿Cuál?` | BV · SA · T7 · T8 | TERR p133 |
| REV | 1164 | 3811 | Z16 | `Rural disperso (vereda,)` | `Rural disperso (vereda)` | BV · SA · T7 · T8 · UE | TERR p45-46 |
| REV | 1452 | 4574 | Z6_tel | `Rural disperso (vereda,)` | `Rural disperso (vereda)` | AS | ASIS p30-31 |
| REV | 1461 | 4586 | Z16_tel | `Rural disperso (vereda,)` | `Rural disperso (vereda)` | AS | ASIS (zona corresp.) |
| REV | 1494 | 4704 | D5_tel | `En Usufructo**` | `Usufructo` | AS | ASIS p52 |
| REV | 1493 | 4701 | C1_tel | `Otra vivienda  (carpa, vagón, cueva, refugio natural,albergue, embarcación, campamento, Asentameinto fluvial, rancho, etc)` | `Otra vivienda  (carpa, vagón, cueva, refugio natural,albergue, embarcación, campamento, Asentamiento fluvial, rancho, etc)` | AS | ASIS p50-51 |

**Notas de la tabla APLICAR**

- **pre36 / pre1493 (`Asentameinto`→`Asentamiento`):** es la MISMA cadena larga en TERR (pre36) y ASIS (pre1493); se corrige solo el typo, se conserva todo lo demas (incl. el doble espacio tras "vivienda"). ⚠️ **pre1493:** el manual de Asistencia (p50-51) ademas propone "**Otra vivienda**" → "**Otro tipo de vivienda**". Ese reword queda **PENDIENTE / NO se aplica aqui** (target del crosswalk truncado); requiere el texto completo del manual antes de tocarse.
- **pre872 res2647:** ademas del typo `turiísticos`→`turísticos`, el manual no lleva punto final (`etc.)`→`etc)`). Se adopta la cadena del manual.
- **Ordinales G7B (pre76):** el manual usa el indicador ordinal `º` (U+00BA), no el signo de grado `°` (U+00B0) del SICAV. Copiar la cadena NUEVA tal cual.
- **pre812 (`Comunitaria`→`Comunitario`):** incluye la variante telefonica (`I28A_tel`) en `perfil_telefonico_v8.json`.
- **T7 (`perfil_territorial_v7.json`):** es la version previa de Territorial (vigente = T8). Patchear T7 solo si se decide mantener ese fixture; no es bloqueante.
- **pre872 res2644 sin colision:** al corregir `Combares`→`Combates o bombardeos`, existe ya un `Combates o bombardeos` correcto pero en **otra** pregunta (pre907 `AT8A`, res 2780). No hay duplicado dentro de C17A; por eso es imprescindible editar por `id_resp_vivanto`, no por texto.

### Verificaciones hechas

- **`perfiles_iniciales.json`** NO se toca: es metadata Django serializada (6 `formulario.perfil` + 6 `formulario.instrumentoversion`), sin opciones. Los 7 archivos listados son el conjunto completo.
- **Todas** las cadenas ACTUAL de la seccion 2 se verificaron presentes en los fixtures; las NUEVAS aun no existen (p.ej. `Asentamiento fluvial` = 0 ocurrencias hoy).
- **Mismo artefacto fuera de alcance:** la coma parasita `Rural disperso (vereda,)` aparece **2 veces por archivo** en la familia territorial: `Z16` (pre1164, EN este batch) y **`Z6` (pre5, res10) que el crosswalk marco `CROSSWALK_SOLO`** y por tanto queda fuera. Es la misma limpieza trivial; se recomienda corregir ambas juntas para consistencia visual (idem `Z6_tel`/`Z16_tel` en Asistencia, ya incluidas).

---

## 3. Tabla NO TOCAR (39, crosswalk-solo / no aplicable)

Agrupadas por razon. En estos casos SICAV ya coincide con el manual, el manual tiene el typo, el cambio es un reword/variante caso-a-caso, o el target no es reconstruible. Conforme a "si dudas, NO TOCAR".

### A) Familia NS/NR — variante lexica de una opcion de control (16)
El manual usa "informa" en vez de "responde", o recorta a "No sabe". No es typo; cambia semantica de una opcion de control estandar del SICAV.

| pre_id | res_id | cód | actual (fixture) | manual (crosswalk) |
|---:|---:|---|---|---|
| 79 | 278 | H8 | `NS/NR` | `No sabe, no informa` |
| 124 | 428 | L6 | `No sabe, no responde` | `No sabe, no informa` |
| 139 | 492 | L20 | `No sabe/No responde` | `No sabe / No informa` |
| 140 | 495 | L21 | `No sabe/No responde` | `No sabe / No informa` |
| 161 | 548 | M4C1A | `No sabe, no responde` | `No sabe, no informa` |
| 1439 | 4531 | SA_PS_1 | `NS/NR` | `No sabe no responde` |
| 151 | 518 | M2A | `No Sabe/No Responde` | `No sabe` |
| 152 | 521 | M2B | `No Sabe/No Responde` | `No sabe` |
| 153 | 524 | M2C | `No Sabe/No Responde` | `No sabe` |
| 154 | 3787 | M5 | `No Sabe/No Responde` | `No sabe` |
| 894 | 2724 | M6 | `No Sabe/No Responde` | `No sabe` |
| 895 | 2727 | M7 | `No Sabe/No Responde` | `No sabe` |
| 896 | 2730 | M8 | `No Sabe/No Responde` | `No sabe` |
| 897 | 2733 | M9 | `No Sabe/No Responde` | `No sabe` |
| 898 | 2736 | M10 | `No Sabe/No Responde` | `No sabe` |
| 899 | 2739 | M11 | `No Sabe/No Responde` | `No sabe` |

> Las de la serie M (ingresos) recortarian "No responde": perdida de informacion. Si negocio confirma la redaccion del manual, tratarlas como un lote aparte.

### B) Reword substantivo / cambio de palabras (no typo) (11)

| pre_id | res_id | cód | actual (fixture) | manual (crosswalk) | por que NO |
|---:|---:|---|---|---|---|
| 124 | 1283 | L6 | `Se presento a una finca a trabajar como jornalero` | `Se presentó a alguna finca a trabajar como jornalero` | `una`→`alguna` (reword). ⚠️ Ademas falta tilde `presento`→`presentó` (typo embebido). |
| 126 | 438 | L8 | `Los empleadores lo consideran muy joven / viejo` | `Los empleadores lo consideran muy joven o muy viejo` | Agrega `muy` y cambia `/`→`o`. |
| 293 | 1046 | A16 | `Lo habla y lo entiende bien` | `Lo entiende y lo habla bien` | Cambio de ORDEN de palabras. |
| 300 | 1101 | D10 | `Aguas lluvias` | `Agua lluvia` | Numero (pl→sg); SICAV es castellano valido. |
| 798 | 2378 | E1A | `Ya se reubicó ... a causa del desplazamiento` | `...a causa del desplaza...` (SICAV omite `forzado`) | Agrega calificador; manual truncado en crosswalk. |
| 837 | 2535 | PL19 | `Dueño y gerente` | `Dueño o gerente` | `y`→`o` cambia el sentido logico. |
| 866 | 2630 | B17 | `Territorio ancestral Habitado` | `Territorio Ancestralmente Habitado` | `ancestral`→`Ancestralmente` (adj→adv) + mayusculas. |
| 872 | 2645 | C17A | `Restricción a la movilidad - Confinamiento` | `Restricciones a la movilidad – Confinamiento` | Numero (sg→pl) + raya `–`. |
| 872 | 2649 | C17A | `Presencia de cultivos ilícitos` | `Presencia de cultivos de uso ilícito` | Agrega `de uso`. |
| 400 | 1400 | I7E | `A causa del conflicto armado (minas, cambates, otros)` | `Porque fue víctima del conflicto armado (minas, combates, otros)` | Reword `A causa`→`Porque fue víctima`. ⚠️ Typo embebido `cambates`→`combates`. |
| 1435 | 4504 | A24 | `Otro pariente del jefe` | `OTRO PARIENTE DEL RESPONSABLE DEL HOGAR` | `del jefe`→`del responsable del hogar` (B24) + mayus. Ademas la frase se usa consistente en SICAV (cat. `A9_PARENTESCO`). **Escalar a negocio.** |

> ⚠️ **Typos embebidos** (pre124 `presento`, pre400 `cambates`): son errores reales, pero un fix parcial no alcanza el target del manual (que ademas rehace la frase). Se dejan para el curador junto con el reword.

### C) Pronombre Lo/La atado al referente del enunciado (3)

| pre_id | res_id | cód | actual (fixture) | manual (crosswalk) |
|---:|---:|---|---|---|
| 273 | 969 | A15 | `Lo habla y lo entiende bien` | `La habla y la entiende bien` |
| 273 | 970 | A15 | `Lo entiende y habla poco` | `La entiende y habla poco` |
| 273 | 971 | A15 | `Lo entiende pero no lo habla` | `La entiende pero no la habla` |

> El pronombre depende de si el enunciado dice "idioma" (masc.) o "lengua" (fem.). Si SICAV usa "idioma", `Lo` es coherente; cambiar solo la opcion crearia inconsistencia interna. Revisar el texto de la pregunta A15 antes de decidir.

### D) SICAV ya coincide con el manual / solo agrega prompt de sub-campo (2)

| pre_id | res_id | cód | actual (fixture) | manual (crosswalk) | por que NO |
|---:|---:|---|---|---|---|
| 2 | 3 | Perfil_tel/Z3 | `Entrevista telefónica` | `Entrevista Telefónica` | El fixture YA coincide (solo mayuscula inicial). El crosswalk comparo contra `Telefónica` (lado Oracle), no contra el fixture. |
| 809 | 2406 | I25B | `Otra` | `Otra ¿Cuál?` | El fixture YA tiene el genero correcto `Otra`; el unico delta es agregar el prompt `¿Cuál?` (sub-campo). Regla: no agregar prompts. |

### E) Typo de ORACLE — mantener la grafia correcta del SICAV (2)

| pre_id | res_id | cód | actual (fixture) | manual (crosswalk) | por que NO |
|---:|---:|---|---|---|---|
| 865 | 3865 | B13A | `Trasplante renal` | `TRANSPLANTE RENAL` | `TRANSPLANTE` (con N) es typo de Oracle + mayusculas. SICAV es correcto; no introducir el error. |
| 1478 | 4629 | B13A_tel | `Trasplante renal` | `TRANSPLANTE RENAL` | Idem (variante telefonica). |

### F) Target del manual truncado/placeholder o con artefacto de captura — no reconstruible (4)

| pre_id | res_id | cód | actual (fixture, resumen) | manual (crosswalk) | por que NO |
|---:|---:|---|---|---|---|
| 1424 | 4476 | ST2 | `De manera limitada: ...` (parrafo completo) | `DE MANERA LIMITADA = ... (texto completo, res 4476)` | El crosswalk trae un PLACEHOLDER, no el texto exacto del manual. No reconstruible. |
| 1424 | 4477 | ST2 | `Hasta cierto punto: ...` (parrafo completo) | `HASTA CIERTO PUNTO = ...` (placeholder) | Idem. |
| 1424 | 4478 | ST2 | `De manera significativa: ...` (parrafo completo) | `DE MANERA SIGNIFICATIVA = ...` (placeholder) | Idem. |
| 1494 | 4711 | D5_tel | `Otra ¿Cuál?` | `Otro. ¿Cuál? ____________` | El target trae artefacto de linea de captura (`____`). El unico delta real es genero `Otra`→`Otro`, pero la cadena del manual esta contaminada. |

> El fixture de pre1424 (ST2) ademas tiene un typo interno propio: `pocos de etos derechos` (deberia `estos`). Es un typo de contenido dentro de un parrafo largo; se deja para una curacion de texto libre dedicada, no para este batch.

### G) Mismatch de `res_id` — apunta a otra opcion en el fixture (1)

| pre_id | res_id | cód | actual EN EL FIXTURE (res 4751) | manual (crosswalk) | por que NO |
|---:|---:|---|---|---|---|
| 1503 | 4751 | D10_tel | `Río, quebrada, yacimiento o manantial` | `Carrotanque` (SICAV `Agua de carro tanques`) | En el fixture, `id_resp_vivanto=4751` es OTRA opcion. Editar aqui corromperia esa opcion. Es un asunto de mapeo Oracle. **Escalar.** |

---

## 4. Como aplicar (una sola pasada)

Este documento NO modifica fixtures. Cuando se apruebe, aplicar el lote de la seccion 2 asi, en UNA pasada:

1. **Editar el fixture (fuente de verdad)** — cada opcion por `codigo_externo`+`id_resp_vivanto`, cambiando SOLO `etiqueta`. Repetir la misma edicion en cada archivo de la columna "Archivos" (las opciones estan inline duplicadas; `opciones_compartidas.json` no se toca).
2. **`cargar_perfil --reemplazar`** de los perfiles editados (recargar BD desde el fixture).
3. **`exportar_a_mobile`** para regenerar el/los bundle(s).
4. **Bump de version del bundle** en los **4 lugares** (archivo de bundle, `index.json`, `require`/`BUNDLED` en `instrumentos.ts`, backend) para que el build EAS no falle en "Bundle JavaScript".

Alcance del lote: **7 archivos** (`perfil_asistencia_v8`, `perfil_buenaventura_v7`, `perfil_san_andres_v7`, `perfil_telefonico_v8`, `perfil_territorial_v7`, `perfil_territorial_v8`, `perfil_urbano_etnico_v1`), **~79 ediciones de string**, **0 cambios en el catalogo compartido**.
