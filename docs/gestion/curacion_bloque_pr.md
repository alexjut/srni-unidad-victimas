# Curación del bloque PR (perfil rural-étnico): re-enganche a Oracle de PR1_re, PR2_re, PR4_re, PR5_re

**Estado:** PROPUESTA para revisión. NO modifica ningún fixture, crosswalk ni código.
**Fecha:** 2026-07-23
**Autoridad:** Manual oficial **11-MU** (Territorial y Étnicos) y **14-MU** (Asistencia). Ante duda, MANDA EL MANUAL.
**Alcance:** completa la curación del bloque PR iniciada en `curacion_pr3_ayuda_humanitaria.md` (que resolvió **PR3_re → pre 354**). Aquí se resuelven los **4 hermanos restantes**: PR1_re, PR2_re, PR4_re y PR5_re.
**Insumos:**
- SICAV: `srni-backend/apps/formulario/fixtures/perfil_rural_etnico_v1.json` (PR1_re…PR5_re) + `.../opciones_compartidas.json` (`listas.SI_NO_NS`).
- Oracle: `srni-backend/apps/sincronizacion/oracle/respuestas_oracle.json` (902 preguntas, 3069 respuestas, 43 no escribibles; prod solo lectura, 2026-07-22) y `.../crosswalk_opciones.json` (156 filas).
- Manual: `docs/perfiles/11-MU_...TERRITORIAL-Y-ETNICOS...pdf` (139 pág.) y `.../14-MU_...ASISTENCIA...pdf` (74 pág.).

> Convención: **pre NNN** = `pre_idpregunta` de Oracle; **res NNN** = `res_idrespuesta` de Oracle. No confundir con número de página (para páginas se usa "pág. N" o "p N").

---

## 1. Decisión (TL;DR)

El capítulo PR del fixture asignó a sus preguntas un rango secuencial de `id_preg` (**90-94**) que cae sobre el **tema 10 de Oracle (Rehabilitación / atención psicosocial)** y sobre dos ids que **no existen**. Ninguno de los 5 engarces era correcto. Resultado de esta curación:

| SICAV | `id_preg` actual | Diagnóstico | Propuesta | Estado |
|---|---:|---|---|---|
| PR1_re | 90 | pre 90 = "¿Recibe actualmente algún tipo de rehabilitación?" (tema 10) | **SIN EQUIVALENTE** en Oracle | Desenganchar (no escribir) · escalar |
| PR2_re | 91 | pre 91 **no existe** | **→ pre 353** (compuerta AHE, tema 15) | **RE-ENGANCHE OK** |
| PR3_re | 354 | (ya corregido, doc previo) | pre 354 | HECHO |
| PR4_re | 93 | pre 93 = "…¿ha recibido atención psicosocial…?" (tema 10) | **→ pre 228** (indemnización, tema 19) | **RE-ENGANCHE OK** |
| PR5_re | 94 | pre 94 **no existe** | **SIN EQUIVALENTE** en Oracle | Desenganchar (no escribir) · escalar |

**Cuenta:** 5 preguntas PR. 1 ya resuelta (PR3). De las 4 restantes: **2 se re-enganchan** (PR2→353, PR4→228, ambas con su Sí/No verificado escribible) y **2 quedan sin equivalente** (PR1 "Familias en Acción", PR5 "PAARI"), confirmado por barrido exhaustivo en Oracle **y** ausencia total en ambos manuales.

**Riesgo que esto corrige (no cosmético):** PR1_re (`id_preg 90`) y PR4_re (`id_preg 93`) apuntan hoy a **preguntas Oracle reales del tema 10**. Si el hogar marca "Sí" en PR1 (Familias en Acción) o PR4 (indemnización), la capa de escritura **contaminaría** las preguntas de rehabilitación/psicosocial de Oracle con datos ajenos. PR2 (`91`) y PR5 (`94`) apuntan a ids inexistentes (escritura silenciosa/fallida, menos dañino pero igual de incorrecto).

---

## 2. Estado actual del bloque en el fixture

Los 5 registros `PR*_re` (capítulo `PR`, todos `nivel = HOGAR`):

| `no_pregunta` | `codigo_externo` | `id_preg` | `tipo` | Texto SICAV | `opciones` |
|---|---|---:|---|---|---|
| PR1 | PR1_re | **90** | BOOLEAN | ¿El hogar está vinculado a Familias en Acción? | — (Sí/No) |
| PR2 | PR2_re | **91** | BOOLEAN | ¿El hogar ha recibido alguna Ayuda Humanitaria de Emergencia (AHE)? | — (Sí/No) |
| PR3 | PR3_re | 354 | LISTA_MULTIPLE | ¿Qué tipo de ayuda humanitaria ha recibido? | `$ref:TIPO_AYUDA_HUMANITARIA` |
| PR4 | PR4_re | **93** | BOOLEAN | ¿El hogar ha recibido indemnización administrativa? | — (Sí/No) |
| PR5 | PR5_re | **94** | LISTA | ¿El hogar conoce el Plan de Atención, Asistencia y Reparación Integral (PAARI)? | `$ref:SI_NO_NS` |

**Qué son realmente esos `id_preg` en Oracle** (verificado contra `respuestas_oracle.json`):

- **pre 90** — "¿Recibe actualmente algún tipo de rehabilitación?" (tema 10). ❌
- **pre 91** — **no existe**. ❌
- **pre 92** — "¿…qué tipo de rehabilitación ha recibido?" (tema 10) — era el engarce errado de PR3, ya corregido a 354.
- **pre 93** — "En relación con el acompañamiento psicosocial, ¿…ha recibido atención psicosocial…?" (tema 10). ❌
- **pre 94** — **no existe**. ❌

Lista `SI_NO_NS` (opciones de PR5): `Sí` (valor 1), `No` (valor 2), `No sabe / No responde` (valor 99).

---

## 3. PR2_re → pre 353 (compuerta AHE) — RE-ENGANCHE

### 3.1 Destino Oracle
**pre 353** (tema 15, tipo IN, orden 4):
> "Después de haber sido incluido en el RUV y antes de haber cumplido un año de ocurrido el hecho victimizante, ¿… recibió la ayuda humanitaria?"

Respuestas: **res 1225 = "Sí"**, **res 1226 = "No"** (ambas activas y escribibles).

### 3.2 Justificación (manual + estructura)
- **Semántica AHE — manual 11-MU pág. 5 (DEFINICIONES, Art. 64):** *"ATENCIÓN HUMANITARIA DE EMERGENCIA: es la ayuda humanitaria a la que tienen derecho las personas u hogares en situación de desplazamiento **una vez se haya expedido el acto administrativo que las incluye en el Registro Único de Víctimas**…"*. La compuerta de pre 353 ("después de haber sido incluido en el RUV") es la **redacción operativa exacta** de esa definición. El rótulo literal de PR2_re es "Ayuda Humanitaria de **Emergencia (AHE)**".
- **Descarte de la fase inmediata:** el mismo Art. 62 (11-MU pág. 5) separa las 3 fases (Inmediata, Emergencia, Transición). La rama inmediata de Oracle (pre 162/163/164) NO es AHE y además pre 164 está restringida "sólo… por desplazamiento forzado". PR2 pregunta por AHE genérica de un hogar rural-étnico.
- **Coherencia estructural (sello de calidad):** en Oracle, **pre 353 es la compuerta de pre 354** ("¿en qué gastó el dinero, o qué recibió?"). En SICAV, **PR2_re es la compuerta de PR3_re** (skip-logic: si AHE=Sí, mostrar tipos de ayuda). El par SICAV `PR2→PR3` calca el par Oracle `353→354`. Como PR3_re ya quedó en 354, mandar PR2_re a 353 cierra el par de forma consistente.

### 3.3 Mapeo de la opción (BOOLEAN → Sí/No de pre 353)

| SICAV (BOOLEAN) | Oracle pre 353 | res_id | Escribible | Estado |
|---|---|---:|:--:|---|
| `true` (Sí) | Sí | **1225** | Sí | **CONFIRMADO** |
| `false` (No) | No | **1226** | Sí | **CONFIRMADO** |

---

## 4. PR4_re → pre 228 (indemnización administrativa) — RE-ENGANCHE

### 4.1 Destino Oracle
**pre 228** (tema 19 —"Indemnización"—, tipo IN, orden 1):
> "¿… ha recibido indemnización **por parte de la Unidad de Víctimas o Acción Social** por alguno de los hechos declarados?"

Respuestas: **res 860 = "Si"**, **res 861 = "No"** (ambas activas y escribibles).

### 4.2 Justificación (manual + descarte de la vía judicial)
El tema 19 de Oracle desglosa la indemnización en varias preguntas; la clave es distinguir **administrativa** (UARIV) de **judicial**:

| pre | Texto Oracle | ¿Administrativa? |
|---:|---|---|
| **228** | "…recibió indemnización **por parte de la Unidad de Víctimas o Acción Social**…" | **SÍ ← destino** |
| 229 | "…**solicitó** indemnización ante un **juez**…" | No (judicial) |
| 230 | "…recibió la indemnización **por vía judicial**…" | No (judicial) |
| 357 / 391 | participación en acompañamiento para inversión de la indemnización | No (es sobre acompañamiento) |
| 231 | "…en qué invirtió/le gustaría invertir la(s) indemnización(es)…" | No (es el destino del dinero) |

- **Manual 11-MU pág. 6 (DEFINICIONES, "Método Técnico de Priorización"):** define la **indemnización administrativa** como la que otorga *"la Subdirección de Reparación Individual"* de la UARIV, priorizada "de acuerdo con la disponibilidad presupuestal anual". Es decir: "indemnización **administrativa**" = la de la **Unidad para las Víctimas** (pre 228), explícitamente distinta de la **judicial** (pre 230). El calificativo "administrativa" de PR4_re selecciona a pre 228 y descarta 229/230.
- **Descartada la opción de checklist:** existe res 5086 ("Reparación integral - Indemnización administrativa") dentro del multiselect pre 1593 (tema 67). Se descarta como destino: pre 1593 es "¿a cuáles medidas ha accedido?" (una casilla entre muchas), no una compuerta Sí/No 1:1 como PR4_re. pre 228 es el match estructural correcto.

> Nota: ni 11-MU ni 14-MU desarrollan un capítulo Q&A de "indemnización" con tabla de opciones (las menciones de "indemnización" en 11-MU pág. 122 son el ítem de **ingresos** J40 —loterías, indemnizaciones, venta de propiedades—, que es tema 13/pre 899, NO reparación). Por eso la autoridad para PR4 se ancla en la **definición del glosario (pág. 6)** + el texto de la propia pre 228, no en una pregunta desarrollada.

### 4.3 Mapeo de la opción (BOOLEAN → Sí/No de pre 228)

| SICAV (BOOLEAN) | Oracle pre 228 | res_id | Escribible | Estado |
|---|---|---:|:--:|---|
| `true` (Sí) | Si | **860** | Sí | **CONFIRMADO** |
| `false` (No) | No | **861** | Sí | **CONFIRMADO** |

---

## 5. PR1_re — SIN EQUIVALENTE en Oracle (Familias en Acción)

**SICAV:** BOOLEAN "¿El hogar está vinculado a Familias en Acción?" (`id_preg 90`, errado).

**Búsqueda realizada (exhaustiva):**
- **Texto de pregunta:** 0 coincidencias con "familias en acción" en las 902 preguntas. El único "familias" es pre 1238 ("número de familias retornadas o reubicadas") — no relacionado.
- **Opciones de respuesta:** 0 coincidencias con "Familias en Acción" / "en acción" en las 3069 respuestas.
- **Programas afines:** sin resultados para "Acción Social", "prosperidad", "DPS", "subsidio", "transferencia condicionada", "renta"/"ingreso" como programa, "vinculado a".
- **Manual:** "Familias en Acción" **no aparece** en 11-MU ni en 14-MU (0 páginas).

**Veredicto:** **SIN EQUIVALENTE.** "Familias en Acción" es un programa de transferencias condicionadas del DPS, ajeno al universo del instrumento legacy (Vivanto/Oracle). Es, con alta probabilidad, una **pregunta de enriquecimiento propia de SICAV** sin contraparte por diseño.

**Acción requerida:** **desenganchar de pre 90** (hoy escribiría en "¿recibe rehabilitación?"). Dejar sin destino Oracle (no se escribe) o, si negocio identifica un destino, documentarlo. **Escalar a Oscar.** Sin mapeo de opciones.

---

## 6. PR5_re — SIN EQUIVALENTE en Oracle (PAARI)

**SICAV:** LISTA `SI_NO_NS` "¿El hogar conoce el Plan de Atención, Asistencia y Reparación Integral (PAARI)?" (`id_preg 94`, inexistente).

**Búsqueda realizada (exhaustiva):**
- **"PAARI":** 0 coincidencias en preguntas y 0 en respuestas.
- **"Plan de Atención…":** 0 (el único "plan de …" es pre 1236 "¿tuvo acompañamiento… o plan de retorno o reubicación?", que es otra cosa).
- **"¿conoce…?":** ~30 preguntas contienen "conoce", pero ninguna es el PAARI; las de sentido afín son pre 1590 ("¿qué tanto conoce la **Ley 1448 de 2011**?"), pre 1591 ("¿…los **decretos Ley étnicos** 4633/4634/4635?"), pre 1643 (RUPTA) y pre 1652 (Ley de Retorno) — instrumentos distintos, no el PAARI.
- **Manual:** "PAARI" y "Plan de Atención, Asistencia y Reparación Integral" **no aparecen** en 11-MU ni en 14-MU.

**Veredicto:** **SIN EQUIVALENTE.** El PAARI es un instrumento de la ruta de reparación no modelado como pregunta en el catálogo Oracle. Igual que PR1, es candidata a **pregunta SICAV-only**.

**Acción requerida:** **desenganchar de pre 94** (inexistente). Dejar sin destino Oracle. **Escalar a Oscar** por si negocio prefiere mapearla a una de las preguntas de conocimiento afines (p. ej. tema 67). Sin mapeo de opciones.

---

## 7. Resumen del re-enganche propuesto (fixture)

> Propuesta. NO se editó ningún archivo. Conservar en cada registro `codigo_externo`, `id` (UUID), `texto`, `tipo`, `nivel`, `capitulo_codigo` y `opciones`; solo cambia `id_preg`.

| SICAV | `id_preg`: de → a | Justificación (autoridad) |
|---|---|---|
| PR1_re | 90 → **(sin destino / null)** | Sin equivalente Oracle; ausente en ambos manuales. Escalar. |
| PR2_re | 91 → **353** | AHE = post-RUV (11-MU pág. 5, Art. 64); par 353→354 ≡ par PR2→PR3. |
| PR4_re | 93 → **228** | Indemnización **administrativa** = UARIV (11-MU pág. 6); descarta 229/230 (judicial). |
| PR5_re | 94 → **(sin destino / null)** | Sin equivalente Oracle (PAARI ausente); ausente en ambos manuales. Escalar. |

*(PR3_re: 92 → 354, ya aplicado en `perfil_rural_etnico_v1.json` — ver doc previo.)*

**Recordatorio de versionado:** al aplicar cualquier cambio de `id_preg` en el fixture, replicar en el bundle móvil `srni-mobile/assets/instrumentos/rural_etnico_v1.json`.

---

## 8. Mapeo de opciones (solo las re-enganchables)

Ambas re-enganchables son **BOOLEAN**; su "opción" implícita es Sí/No. No requieren fila de `crosswalk_opciones.json` con etiqueta (el crosswalk mapea opciones de listas; el Sí/No de un BOOLEAN lo resuelve la lógica de escritura). Se documenta el destino `res_id`:

| SICAV | valor | Oracle pre | res_id | Texto Oracle | Escribible | ¿en `no_escribibles`? |
|---|---|---:|---:|---|:--:|:--:|
| PR2_re | `true` | 353 | **1225** | "Sí" | Sí | No |
| PR2_re | `false` | 353 | **1226** | "No" | Sí | No |
| PR4_re | `true` | 228 | **860** | "Si" | Sí | No |
| PR4_re | `false` | 228 | **861** | "No" | Sí | No |

PR1_re y PR5_re: **sin mapeo** (sin equivalente).

---

## 9. Verificación

- **Existencia + escribibilidad** (contra `respuestas_oracle.json`, snapshot 2026-07-22): pre **353** existe (res 1225/1226) y pre **228** existe (res 860/861). Los 4 res_id están **activos**, marcados `escribible: true` y **ninguno** figura entre los 43 `no_escribibles`.
- **Descarte verificado:** pre 91 y pre 94 confirmados inexistentes; pre 90 y pre 93 confirmados como tema 10 (rehabilitación/psicosocial). pre 230 (judicial) existe (res 864/865) pero se descarta por semántica.
- **Sin colisión en el crosswalk:** `crosswalk_opciones.json` (156 filas) **no contiene** ninguna fila con `pre_id` 228 ni 353, ni `cod_sicav` PR1_re/PR2_re/PR4_re/PR5_re. Las únicas filas del bloque PR existentes son 6 de **PR3_re** (`pre_id 354`, categoría `PR3_AYUDA_HUMANITARIA`). Las propuestas aquí (si negocio decidiera crosswalkear el Sí/No) serían nuevas.
- **Nota de nivel:** las 4 PR son `nivel = HOGAR` en SICAV; las preguntas Oracle destino (tema 15/19) se responden a nivel de entrevista/persona. No bloquea el re-enganche, pero la capa de escritura debe resolver el nivel al persistir (mismo patrón que PR3).

---

## 10. Pendientes / escalamiento a negocio (Oscar)

1. **PR1_re "Familias en Acción":** ¿se confirma como SICAV-only (no se escribe a Oracle) o negocio conoce un destino? Mientras tanto: desenganchar de pre 90 para no corromper "rehabilitación".
2. **PR5_re "PAARI":** ídem; ¿SICAV-only, o mapear a una pregunta de "conocimiento" del tema 67 (p. ej. Ley 1448 pre 1590)? Definir antes de escribir.
3. **PR4_re — nivel HOGAR vs. universo:** pre 228 pregunta por indemnización "por alguno de los hechos declarados" (típicamente por víctima). Confirmar que la respuesta de hogar de SICAV es aceptable a ese nivel en la escritura.
4. **PR2_re — confirmación semántica AHE:** el equipo ya validó AHE = pre 353 vía Art. 64; se deja registrado por trazabilidad.

---

## 11. Qué NO se tocó

No se editó `perfil_rural_etnico_v1.json`, ni `opciones_compartidas.json`, ni `crosswalk_opciones.json`, ni `respuestas_oracle.json`, ni el bundle móvil, ni código. Este documento es únicamente la propuesta; la aplicación (re-enganche de `id_preg` de PR2→353 y PR4→228, desenganche de PR1 y PR5, y las decisiones de §10) queda pendiente de aprobación.
