# Curación PR3_re: re-enganche de "tipo de ayuda humanitaria" (perfil rural-étnico)

**Estado:** PROPUESTA para revisión. NO modifica ningún fixture, crosswalk ni código.
**Fecha:** 2026-07-23
**Autoridad:** Manual oficial **11-MU** (Territorial y Étnicos) y **14-MU** (Asistencia). Ante duda, MANDA EL MANUAL.
**Insumos:**
- SICAV: `srni-backend/apps/formulario/fixtures/perfil_rural_etnico_v1.json` (PR3_re) + `.../opciones_compartidas.json` (`listas.TIPO_AYUDA_HUMANITARIA`, 9 opciones).
- Oracle: `srni-backend/apps/sincronizacion/oracle/respuestas_oracle.json` (902 preguntas, 3069 respuestas, 43 no escribibles; solo lectura de prod, 2026-07-22).
- Manual: `docs/perfiles/11-MU_...TERRITORIAL-Y-ETNICOS...pdf` y `.../14-MU_...ASISTENCIA...pdf`.

> Convención en este doc: **pre NNN** = `pre_idpregunta` de Oracle; **res NNN** = `res_idrespuesta` de Oracle. No confundir con números de página.

---

## 1. Decisión (TL;DR)

1. **PR3_re debe re-engancharse de `id_preg=92` → `id_preg=354`.** pre 92 es "¿Qué tipo de rehabilitación ha recibido?" (Capítulo H del manual, tema 10 en Oracle): enganche errado. La pregunta correcta de ayuda humanitaria para PR3_re es **pre 354** (tema 15, rama **AHE — Atención Humanitaria de Emergencia**), **no** pre 164 (rama de atención inmediata, solo desplazamiento).
2. **Justificación de fondo:** la compuerta de PR3_re es PR2_re = "¿El hogar ha recibido alguna **Ayuda Humanitaria de Emergencia (AHE)**?". El manual (11-MU p5, glosario, Art. 64) define AHE como la ayuda "una vez se haya expedido el acto administrativo que las incluye en el RUV". La compuerta Oracle de pre 354 es pre 353: "Después de haber sido incluido en el RUV y antes de haber cumplido un año…". Coincidencia semántica exacta. pre 164, en cambio, es la fase inmediata ("durante los tres primeros meses") y está restringida a "quienes recibieron ayuda por desplazamiento forzado".
3. **Mapeo de las 9 opciones contra pre 354:** 5 cruzan (2 idénticas, 3 con calificador), 1 requiere decisión de negocio (médica/psicosocial: SICAV junta, Oracle separa), y 3 quedan **pendientes sin equivalente** en Oracle (Auxilio funerario, Aseo personal y elementos de hábitat, Apoyo económico). Ver §5.
4. **Alcance mayor (nota):** no es solo PR3. Todo el bloque PR del fixture (`id_preg` 90-93) está mal enganchado a Oracle. Ver §2.3. Este doc resuelve PR3; PR1/PR2/PR4 se dejan señalados.

---

## 2. El problema y su alcance

### 2.1 Estado actual del fixture (PR3_re)

```jsonc
{
  "no_pregunta": "PR3",
  "codigo_externo": "PR3_re",
  "id_preg": 92,                                  // <-- ERRADO
  "texto": "¿Qué tipo de ayuda humanitaria ha recibido?",
  "tipo": "LISTA_MULTIPLE",
  "nivel": "HOGAR",
  "capitulo_codigo": "PR",
  "opciones": "$ref:TIPO_AYUDA_HUMANITARIA",      // 9 opciones
  "id": "47449b03-d049-444a-80eb-5bf757516bf3"
}
```

### 2.2 Qué es realmente pre 92 en Oracle

pre 92 (tema 10, "Rehabilitación") = **"¿Qué tipo de rehabilitación ha recibido?"** con opciones Fisioterapia (res 342), Fonoaudiología (343), Terapia ocupacional (344), Lengua de señas (345), Braille (346), Oftalmología (347), Psiquiatría (348), Psicología (349), Trabajo social (350), Otra (351), Ninguna (352), Medicamentos permanentes (1405).

En el manual 11-MU esto es el **Capítulo H – REHABILITACIÓN** (págs. 94-97). Nada que ver con ayuda humanitaria. El crosswalk vigente ya lo trata como rehabilitación (fila `pre_id 92 / I10A "Otra" → res 351`, "TERR p95"). Enganchar PR3_re aquí escribiría "tipo de ayuda humanitaria" dentro de la pregunta de rehabilitación de Oracle.

### 2.3 El bloque PR completo está mal enganchado (contexto, fuera de alcance de este doc)

El fixture asignó al capítulo PR un rango secuencial 90-93 que cae sobre el tema 10 de Oracle (rehabilitación/psicosocial):

| SICAV | `id_preg` actual | Texto SICAV | Qué es esa pre en Oracle | ¿Correcto? |
|---|---:|---|---|---|
| PR1_re | 90 | ¿El hogar está vinculado a Familias en Acción? | pre 90 = "¿Recibe actualmente algún tipo de rehabilitación?" (tema 10) | NO |
| PR2_re | 91 | ¿El hogar ha recibido alguna AHE? | pre 91 **no existe** en Oracle | NO |
| PR3_re | 92 | ¿Qué tipo de ayuda humanitaria ha recibido? | pre 92 = rehabilitación (tema 10) | **NO ← este doc** |
| PR4_re | 93 | ¿El hogar ha recibido indemnización administrativa? | pre 93 = atención psicosocial (tema 10) | NO |

Recomendación derivada (no se resuelve aquí): PR2_re es la compuerta natural de PR3_re y debería apuntar a **pre 353** (compuerta AHE). PR1_re (Familias en Acción) y PR4_re (indemnización) requieren su propia búsqueda de destino Oracle y quedan como pendientes.

---

## 3. Datos Oracle: el capítulo de ayuda humanitaria (tema 15)

Secuencia completa del tema 15, en orden:

| pre | orden | Texto Oracle | Fase |
|---:|---:|---|---|
| 162 | 1 | "Por cuál(es) hecho(s) vivido(s) … recibió ayuda humanitaria **durante los tres primeros meses desde la ocurrencia**?" | Inmediata |
| 163 | 2 | "Por cuáles hechos … **solicitó** ayuda humanitaria durante los tres primeros meses…" | Inmediata |
| **164** | 3 | "En qué gastó el dinero, o qué recibió? *(Sólo aplica para quienes recibieron ayuda por desplazamiento forzado)*" | **Inmediata / solo desplazamiento** |
| 353 | 4 | "**Después de haber sido incluido en el RUV y antes de haber cumplido un año** de ocurrido el hecho victimizante, ¿… recibió la ayuda humanitaria?" (Sí=1225 / No=1226) | **Compuerta AHE** |
| **354** | 5 | "¿En qué gastó el dinero, o qué recibió?" | **AHE (post-RUV)** |
| 263 | 6 | "Observaciones a este capítulo" | — |

Las dos candidatas ("en qué gastó el dinero, o qué recibió") son **pre 164** y **pre 354**:

- **pre 164** (10 opciones): Alimentación (575), Alojamiento (576), Vestuario (577), Atención médica (578), Atención psicosocial (579), Transporte (580), Kit de habitabilidad (581), Otro (582), Agua potable (1223), Saneamiento básico (1224).
- **pre 354** (13 opciones): Alimentación (1229), Alojamiento (1230), Vestuario (1231), Atención médica (1232), Atención psicosocial (1233), Transporte (1234), Kit de habitabilidad (1235), Agua potable (1236), Educación (1237), Pago de deudas y préstamos (1238), Pago de servicios públicos (1239), Saneamiento básico (1240), Otra Cuál? (1241).

---

## 4. Decisión: pre 164 vs pre 354 (justificada con el manual)

| Criterio | pre 164 | pre 354 | Manual |
|---|---|---|---|
| **Tema** | 15 (ayuda humanitaria) | 15 (ayuda humanitaria) | Ambos correctos a nivel de tema (vs pre 92 que es tema 10). |
| **Fase / nivel** | Atención **inmediata**: su gatillo (162/163) es "ayuda humanitaria durante los **tres primeros meses** desde la ocurrencia" | **AHE**: su gatillo (353) es "después de haber sido incluido en el RUV y antes de un año" | 11-MU **p5, glosario**: define las 3 fases (Art. 62) y separa "Atención Inmediata" de "Atención Humanitaria de Emergencia". |
| **Redacción de la compuerta** | — | pre 353 ≡ definición legal de AHE | 11-MU **p5, Art. 64**: "ATENCIÓN HUMANITARIA DE EMERGENCIA: es la ayuda humanitaria a la que tienen derecho las personas u hogares en situación de desplazamiento **una vez se haya expedido el acto administrativo que las incluye en el Registro Único de Víctimas**". |
| **Restricción de universo** | "**Sólo aplica para quienes recibieron ayuda por desplazamiento forzado**" | Sin restricción de hecho victimizante | PR3_re es de un HOGAR rural-étnico genérico (todos los hechos), no solo desplazamiento. |

**Anclaje con SICAV:** la pregunta que abre PR3_re es **PR2_re = "¿El hogar ha recibido alguna Ayuda Humanitaria de **Emergencia (AHE)**?"**. El rótulo "AHE" es literal. La única rama Oracle que corresponde a AHE es **353 → 354**. pre 164 pertenece a la fase inmediata (y encima restringida a desplazamiento), que en SICAV no es lo que pregunta PR2/PR3.

> **Nota de precisión del manual:** ni el 11-MU ni el 14-MU desarrollan en su cuerpo una pregunta "en qué gastó el dinero / tipo de ayuda humanitaria" con tabla de opciones (sus capítulos son A→M y A→G respectivamente; no hay capítulo de ayuda humanitaria). Por eso la decisión **164 vs 354 se ancla en el glosario (p5, Arts. 47/62/64)**, no en una pregunta desarrollada. El mapeo opción-por-opción (§5) se apoya en (a) identidad textual con las opciones de pre 354 y (b) la lista de componentes del Art. 47; donde ninguna de las dos confirma, se marca PENDIENTE.

**Veredicto: `id_preg = 354`.** Se descarta pre 164 (fase/universo equivocados) y se descarta "ninguno" (tema 15 sí es la ubicación correcta; la metodología del crosswalk mapea a nivel de pregunta y luego opción a opción, no exige identidad total del set de opciones).

---

## 5. Mapeo opción → res_id (contra pre 354)

Regla aplicada: se propone `res_id` **solo si** (a) el texto coincide con una opción de pre 354 o (b) el Art. 47 del manual respalda que es el mismo componente. En caso contrario → PENDIENTE.

| # | Opción SICAV (`TIPO_AYUDA_HUMANITARIA`) | Opción Oracle pre 354 | res_id | Escribible | Estado | Nota |
|---:|---|---|---:|:--:|---|---|
| 1 | Alimentación | Alimentación | **1229** | Sí | **CONFIRMADO** | Texto idéntico; Art. 47 lista "alimentación". |
| 2 | Alojamiento temporal | Alojamiento | **1230** | Sí | **CONFIRMADO** | SICAV añade "temporal"; Art. 47 "alojamiento transitorio". Misma opción. |
| 3 | Auxilio funerario | — | — | — | **PENDIENTE (sin equivalente)** | pre 354 no lista funerario. Barrido global: **ninguna** opción en todo Oracle contiene "funerario"/"auxilio". Escalar a Oscar. |
| 4 | Vestuario | Vestuario | **1231** | Sí | **CONFIRMADO** | Texto idéntico. |
| 5 | Aseo personal y elementos de hábitat | Kit de habitabilidad *(candidato)* | *(1235)* | Sí | **PENDIENTE (dudoso)** | No hay identidad textual. Oracle 1235 "Kit de habitabilidad" ≈ utensilios de aseo/cocina/hábitat; Art. 47 lista "aseo personal" y "utensilios de cocina" como componentes, pero el manual no desarrolla la opción. No forzar; confirmar con negocio. |
| 6 | Transporte de emergencia | Transporte | **1234** | Sí | **CONFIRMADO** | SICAV añade "de emergencia"; Art. 47 "transporte de emergencia". Misma opción. |
| 7 | Atención médica y psicosocial | Atención médica **+** Atención psicosocial | **1232 + 1233** | Sí (ambas) | **DECISIÓN (split)** | SICAV **junta** en una opción; Oracle las **separa** en dos. No hay 1:1. Art. 47 las trata como un mismo componente ("atención médica y psicológica de emergencia"). Ver §6.4. |
| 8 | Apoyo económico (transferencia monetaria) | — | — | — | **PENDIENTE (sin equivalente)** | pre 354 es "en qué gastó el dinero": el dinero es el medio, no una categoría de gasto. Barrido global: ninguna opción Oracle contiene "transferencia monetaria". Escalar a Oscar. |
| 9 | Otra ayuda | Otra, Cuál? | **1241** | Sí | **CONFIRMADO** | Formato; "Otra ayuda" ↔ "Otra, Cuál?". |

**Opciones de pre 354 sin contraparte en SICAV** (no se escriben; solo informativo): Agua potable (1236), Educación (1237), Pago de deudas y préstamos (1238), Pago de servicios públicos (1239), Saneamiento básico (1240) — y, según la decisión §6.4, una de Atención médica/psicosocial.

**Resumen:** 5 confirmadas (1229, 1230, 1231, 1234, 1241) · 1 decisión split (1232/1233) · 3 pendientes (Auxilio funerario, Aseo personal/hábitat [candidato 1235], Apoyo económico).

---

## 6. Arreglo propuesto

> Todo lo siguiente es propuesta. NO se editó ningún archivo.

### 6.1 Re-enganche del fixture (PR3_re)

- `perfil_rural_etnico_v1.json` → PR3_re: **`id_preg: 92` → `id_preg: 354`**.
- Conservar `codigo_externo`, `id` (UUID `47449b03-…`), `texto`, `tipo`, `nivel`, `capitulo_codigo` y `opciones: "$ref:TIPO_AYUDA_HUMANITARIA"` sin cambios.
- (Recordatorio de memoria: al versionar el fixture, actualizar también el bundle móvil `srni-mobile/assets/instrumentos/rural_etnico_v1.json`.)

### 6.2 Entradas de crosswalk propuestas (solo las CONFIRMADAS)

Mismo esquema que `crosswalk_opciones.json`. `cod_sicav = "PR3_re"`, `pagina_manual = "11-MU p5 (glosario AHE / Art. 47)"` (no hay página por-opción).

```jsonc
[
  { "pre_id": 354, "cod_sicav": "PR3_re", "opcion_sicav": "Alimentación",
    "etiqueta_manual": "Alimentación", "res_id": 1229,
    "categoria": "TRIVIAL", "pagina_manual": "11-MU p5 (Art.47)",
    "nota": "Texto idéntico.", "accion": "CROSSWALK_SOLO" },

  { "pre_id": 354, "cod_sicav": "PR3_re", "opcion_sicav": "Alojamiento temporal",
    "etiqueta_manual": "Alojamiento", "res_id": 1230,
    "categoria": "SUSTANTIVA", "pagina_manual": "11-MU p5 (Art.47 'alojamiento transitorio')",
    "nota": "SICAV añade 'temporal'; misma opción.", "accion": "FIXTURE_REVISAR" },

  { "pre_id": 354, "cod_sicav": "PR3_re", "opcion_sicav": "Vestuario",
    "etiqueta_manual": "Vestuario", "res_id": 1231,
    "categoria": "TRIVIAL", "pagina_manual": "11-MU p5",
    "nota": "Texto idéntico.", "accion": "CROSSWALK_SOLO" },

  { "pre_id": 354, "cod_sicav": "PR3_re", "opcion_sicav": "Transporte de emergencia",
    "etiqueta_manual": "Transporte", "res_id": 1234,
    "categoria": "SUSTANTIVA", "pagina_manual": "11-MU p5 (Art.47 'transporte de emergencia')",
    "nota": "SICAV añade 'de emergencia'; misma opción.", "accion": "FIXTURE_REVISAR" },

  { "pre_id": 354, "cod_sicav": "PR3_re", "opcion_sicav": "Otra ayuda",
    "etiqueta_manual": "Otra, Cuál?", "res_id": 1241,
    "categoria": "TRIVIAL", "pagina_manual": "11-MU p5",
    "nota": "Formato; opción 'Otra'.", "accion": "CROSSWALK_SOLO" }
]
```

### 6.3 Pendientes (NO escribir hasta decisión de negocio)

- **Auxilio funerario** (SICAV valor 3): sin opción equivalente en pre 354 ni en ninguna otra pregunta Oracle (barrido global sin resultados para "funerario"/"auxilio"). Escalar a Oscar: ¿se omite, se manda a "Otra" (1241), o Oracle tiene otra ubicación?
- **Apoyo económico (transferencia monetaria)** (SICAV valor 8): sin equivalente (pre 354 modela el gasto del dinero, no el vehículo). Escalar a Oscar.
- **Aseo personal y elementos de hábitat** (SICAV valor 5): candidato débil res 1235 ("Kit de habitabilidad"), sin confirmación textual ni de pregunta desarrollada en el manual. Confirmar antes de crosswalkear.

### 6.4 Decisión requerida: "Atención médica y psicosocial" (SICAV valor 7)

SICAV tiene **una** opción; Oracle pre 354 tiene **dos** (res 1232 médica, res 1233 psicosocial). Opciones:

- **(A) Recomendada — dividir la opción en el fixture** (al versionar): separar valor 7 en dos opciones ("Atención médica" → 1232, "Atención psicosocial" → 1233). Da crosswalk 1:1 limpio y no pierde información. Requiere tocar `TIPO_AYUDA_HUMANITARIA`/el fixture (cambio consciente, versionado).
- **(B) Interina — doble escritura**: mantener la opción única y emitir ambos res_id (1232 y 1233) cuando se marque. Defendible por Art. 47 (las trata como un solo componente). Implica dos filas de crosswalk con el mismo `opcion_sicav` (patrón ya presente en el archivo para sub-campos) y un resolver que acepte 1→N.

Hasta decidir, se marca **DECISIÓN**; no se incluyó en el bloque §6.2.

### 6.5 Hermanos del bloque PR (fuera de alcance)

Señalado para un ticket aparte: PR2_re (`id_preg 91`, inexistente) → candidato **pre 353** (compuerta AHE); PR1_re (`id_preg 90`) y PR4_re (`id_preg 93`) requieren búsqueda de destino Oracle propio. No se resuelven aquí.

---

## 7. Verificación

- **Existencia + escribibilidad** (contra `respuestas_oracle.json`, 2026-07-23): pre 354 tiene 13 respuestas (res 1229-1241). Ninguna figura en `no_escribibles` (las 43 no escribibles son otras). Los res_id propuestos y candidatos — **1229, 1230, 1231, 1232, 1233, 1234, 1235, 1241** — existen todos dentro de pre 354 y son **escribibles**.
- **Sin colisión**: `crosswalk_opciones.json` no contiene aún ninguna entrada con `pre_id` 353/354 ni con res 1229-1241. Las filas propuestas son nuevas.
- **pre 164 (alternativa descartada)**: sus 10 opciones (res 575-582, 1223, 1224) también son escribibles; se documenta por si negocio prefiriera la fase inmediata, pero contradice el rótulo "AHE" de PR2_re.

---

## 8. Qué NO se tocó

No se editó `perfil_rural_etnico_v1.json`, ni `opciones_compartidas.json`, ni `crosswalk_opciones.json`, ni `respuestas_oracle.json`, ni el bundle móvil. Este documento es únicamente la propuesta; la aplicación (re-enganche `id_preg` + alta de filas de crosswalk + decisión §6.4 + escalamiento §6.3) queda pendiente de aprobación.
