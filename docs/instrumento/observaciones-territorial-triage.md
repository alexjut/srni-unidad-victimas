# Triage de observaciones — Instrumento TERRITORIAL (APK)

**Fecha:** 2026-07-05
**Fuente:** observaciones del equipo funcional sobre la APK (Territorial V7).
**Veredicto general:** ✅ **Se puede hacer todo.** Ninguna observación exige la única
capacidad que el motor NO tiene y que sería costosa (AND entre respuestas de preguntas
distintas). El grueso es **configuración de fixture**; solo 2 desarrollos habilitadores
(en móvil) desbloquean lo más complejo, más 1 ajuste de datos de DIVIPOLA.

Artefactos fuente:
- Fixture (fuente de verdad): `srni-backend/apps/formulario/fixtures/perfil_territorial_v7.json`
- Bundle móvil (lo que consume la app): `srni-mobile/assets/instrumentos/territorial_v7.json`
- Renderizador: `srni-mobile/app/(main)/formulario/[temaId].tsx` (`ControlInput`, 1232–1414)
- Motor skip-logic: `srni-mobile/src/services/skipLogic.ts` (espejo de `apps/formulario/views.py`)
- Selector municipio: `srni-mobile/src/components/SelectorMunicipio.tsx`

---

## 1. Hallazgo transversal (reencuadra el trabajo)

**Muchas preguntas reportadas como "faltantes" SÍ existen** en el fixture. No se ven por
una de estas tres razones:

1. **Skip-logic mal disparada / no disparada** → la pregunta existe pero nunca se habilita
   (p. ej. D7/D8 étnicas, la regla no se activa por pertenencia étnica).
2. **Input embebido que el renderizador no pinta** → el fixture modela opciones con
   `valor:"TEXTO"` ("Campo Abierto"/"Cuál") y `valor:"NUMÉRICO"` ("Valor 1 a 7", "$"), pero
   `ControlInput` **no tiene rama** para renderizar un input inline cuando se marca esa opción.
   Hoy esas opciones aparecen como un radio inútil que guarda el literal `"TEXTO"`/`"NUMÉRICO"`.
3. **Orden / capítulo equivocado** → Cap K desordenado; "Supervisor" está en el bloque T.

Consecuencia: parte del trabajo no es "agregar" sino **arreglar renderizado + skip-logic + orden**.

---

## 2. Desarrollos habilitadores (desbloquean lo complejo)

| # | Desarrollo | Dónde | Qué desbloquea |
|---|---|---|---|
| **H1** | **Renderizar input embebido** para opciones `valor:"TEXTO"` y `valor:"NUMÉRICO"` (pintar TextInput/NumericInput inline cuando esa opción se marca; guardar el texto/número en vez del literal) | `[temaId].tsx` `ControlInput` | Frecuencia 1–7 alimentos (I3–I16), I18 abierto, K29 institución, J27 "¿cuánto?", C tipo de riesgo, y todo "Otra ¿cuál?" embebido |
| **H2** | **Disparo de skip-logic sobre multi-select** (que `_reglaActiva` parsee el array `["1","3"]` y haga *contains*, en móvil `skipLogic.ts` **y** backend `views.py`) | `skipLogic.ts` + `views.py` | Toda pregunta que volvamos multi-select y que **dispare** otra regla o abra "otra": H2/I10A, I2/I1A1, C factores (si gatillan algo) |
| **H3** | **DIVIPOLA completo offline** (que la precarga/endpoint entregue los 1102 municipios; hoy el picker offline muestra un subconjunto de la precarga) | backend precarga + `SelectorMunicipio` | "No salen todos los municipios" en municipio/punto de atención, D6, D11, negocio K |
| **H4** | **Cascada depto→municipio en el formulario** (reutilizar el componente que ya existe en `caracterizar/ubicacion-atencion.tsx`) | formulario | "Dos espacios: departamento y luego municipio acorde" |

> Nota: alternativamente H1 se puede evitar convirtiendo cada input embebido en una
> **pregunta hija** (`_OTRO`/`_VALOR`) habilitada por skip-logic (patrón que ya se usa, p. ej.
> `Z3_OTRO`). Es 100% fixture, pero implica MUCHA cirugía de fixture; **H1 es más limpio**.

**Lo que NO se necesita:** AND entre respuestas de preguntas distintas. Ninguna observación
lo pide (todas son condiciones de una sola pregunta origen, con OR de opciones cuando aplica).

---

## 3. Veredicto ítem por ítem

Leyenda arreglo: 🟢 fixture · 🟡 requiere habilitador (H1/H2/H3/H4) · 🔵 skip-logic (fixture) · 🟣 orden/config

### Carátula / general
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| Municipio de atención no muestra todos | Datos precarga incompletos | A2 `Z2` / A5 `Z5A` | 🟡 H3 |
| Punto de atención igual | idem | — | 🟡 H3 |
| Dos espacios: depto + municipio acorde | form usa campo único | — | 🟡 H4 |
| Falta "Supervisor de la encuesta" | **EXISTE** (en bloque T) | A20 `T6` | 🟣 mover a carátula |
| P22: cuántas **semanas** de embarazo | falta (solo nº de mujeres) | junto a B21 `B2`/`B2_CANT` | 🟢 agregar NUMÉRICO |
| P26=No → no desplegar P27 | skip-logic | (confirmar IDs) | 🔵 regla DESHABILITAR |

### Capítulo C (vivienda)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| No aparece "vivienda acorde a usos y costumbres" | **EXISTE** (revisar por qué no se ve) | C6 `C7` | 🔵 revisar skip-logic/orden |
| Energía eléctrica sin opción de estrato | falta (estrato no existe) | junto a C7 `D8A` | 🟢 agregar pregunta estrato |
| "afectada por factores como" → opción múltiple | single hoy | (Cap C) | 🟢 tipo→LISTA_MULTIPLE |
| …y no habilitar si tipo vivienda = "otro" | skip-logic | — | 🔵 regla |
| Zona de riesgo: escribir **tipo de riesgo** | opción "Si CUAL" sin campo | C19 `C5` | 🟡 H1 (o pregunta hija) |
| "¿Esta zona se ha visto afectada por:" → múltiple | single hoy | (Cap C) | 🟢 tipo→LISTA_MULTIPLE (+🟡H2 si dispara) |

### Capítulo D (retorno/reubicación)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| "¿Solicitó apoyo del Gobierno…?" sin "por qué" | falta el texto | (Cap D) | 🟢 pregunta hija texto + 🔵 regla |
| Étnico no despliega D7/D8 | **EXISTEN**, regla no dispara | D7 `RR2` / D8 `RR3` | 🔵 regla `etnia=='indigena'`→HABILITAR |
| D6 y D11 deben ser DIVIPOLA | hoy TEXTO libre | D6 `RR1` / D11 `RR6` | 🟢 tipo→COMBO_DINAMICO (+🟡H3/H4) |
| Falta D16 razones | **EXISTE** | D16 `E1C` (+`E1C_OTRO`) | 🔵 revisar visibilidad |
| Falta D17 observaciones | falta | — | 🟢 agregar TEXTO_LARGO |

### Capítulo F (educación)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| No da opción para poner los **grados** | solo niveles, sin grado exacto | F7 `G7B_GRADO` | 🟢 agregar grado (NUMÉRICO/lista por nivel) |
| Falta F9 observaciones | falta (el `F_OBSERVA` está en cap E) | — | 🟢 agregar TEXTO_LARGO en F |

### Capítulo H (rehabilitación / psicosocial)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| H3 tipo rehabilitación → múltiple + "otra" no deja escribir | single; "otra" existe | H2 `I10A` (+`I10A_OTRO`) | 🟢 multi + 🟡 H2 (para reactivar "otra") |
| H4 psicosocial → múltiple | single | H3 `I11A` | 🟢 multi (+🟡H2 si dispara) |

### Capítulo I (JA, alimentación)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| I2 aprovisionamiento → múltiple | single | I2 `I1A1` (+`_OTRO`) | 🟢 multi (+🟡H2 por el OTRO) |
| Preg. 3–16: campo 1–7 al responder SÍ | **modelado**, no se pinta | I4–I17 `J1A…J1N` | 🟡 H1 |
| Lácteos incompleta | **completa** en fixture (no se pinta el 1–7) | I13 `J1J` | 🟡 H1 (mismo fix) |
| Falta I18 alimentación adecuada | **EXISTE** (abierto no se pinta) | I18 `I1D` | 🟡 H1 |
| Falta observaciones cap I | falta | — | 🟢 agregar TEXTO_LARGO |

### Capítulo J (JF, fuerza de trabajo)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| J2 no desplegar si "limitación permanente" | regla incluye L1=5 (limitación) | J2 `L2` (trigger `L1∈{2..7}`) | 🔵 quitar 5 del trigger |
| Falta J11 | **EXISTE y correcto** (habilita si L9=No) | J11 `L11` | ✅ verificar en app |
| Faltan J24/J25/J26 primas | **EXISTEN** | `L22B/C/D` | ✅ verificar |
| J27 "¿cuánto?" | **EXISTE** (`L22E1` no se pinta) | J27 `L22E` | 🟡 H1 |
| J31–J40 sin campos de valor $ | falta $ | `M2A…M11` | 🟢 agregar $ (+🟡H1 si embebido) |
| J41 "ayudas fueron de" + habilitación múltiple | **EXISTE** (6 reglas OR) | J41 `M4C1A` | 🟢 revisar opciones faltantes |
| Falta observaciones cap J | falta | — | 🟢 agregar TEXTO_LARGO |

### Capítulo K (trayectoria laboral)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| Preguntas en desorden | orden | (Cap K) | 🟣 reordenar `orden` |
| K6/K7/K8 incompletas | **completas** | `PL5A/B/C` | 🟣 revisar orden/visual |
| K17 cursos: 4 campos (nombre/institución/tipo/certificó) | 1 campo texto hoy | K17 `PL9A` | 🟢 agregar 3 sub-preguntas |
| Falta K20 sectores | **EXISTE** | `PL12A` | ✅ verificar |
| "ninguno curso" despliega tipo y no aparece K22 | skip-logic | K22 `PL13A` | 🔵 arreglar reglas |
| K29 sin opción institución | **EXISTE** (`Cuál` no se pinta) | K29 `PL20` | 🟡 H1 |
| K33 motivos cierre → múltiple + habilita si negocio activo=No | single | K33 `PL21A` | 🟢 multi + 🔵 regla (single trigger OK) |
| K35 sin "cuál servicio" | falta el "cuál" | K35 `PL23` | 🟢 pregunta hija texto |
| K37 institución (habilita si usó servicios=Sí) | **EXISTE** | K37 `PL23D` | ✅ verificar |
| "¿Dónde se encuentra su negocio?" con DIVIPOLA | (confirmar tipo) | (Cap K) | 🟢 tipo→COMBO_DINAMICO |

### Capítulo L (fuerza pública)
| Observación | Estado real | ID real | Arreglo |
|---|---|---|---|
| L2 habilita si activo/asignación/licenciamiento | **EXISTE** | L2 `FP2` (habilita si `FP1∈{1,2,3}`) | ✅ verificar mapeo de opciones |
| L4 habilita si carrera militar/policial | **EXISTE** | L4 `FP4` (habilita si `FP2∈{1,2}`) | ✅ verificar |
| Falta observaciones en casi todos | faltan D,F,I,J,K,L | — | 🟢 agregar TEXTO_LARGO por capítulo |

### Capítulo T
| Observación | Estado real | Arreglo |
|---|---|---|
| "Nunca lo llenamos, se carga automático" | Cap T tiene `es_precargada:false`, `activa:true` (aparece como captura manual) | 🟣 marcar `es_precargada`/ocultar del flujo de captura |

---

## 4. Esfuerzo y plan de ejecución

**Reparto aproximado (43 ítems):**
- 🟢 Fixture puro (agregar/tipo/regla/orden): ~26 ítems
- 🟡 Requieren habilitador móvil (H1/H2/H3/H4): ~11 ítems (pero solo **4 desarrollos** los cubren a todos)
- ✅ Ya existen, solo verificar en app: ~8 ítems

**Fases sugeridas:**
1. **Habilitadores móvil** (desbloquean lo transversal): **H1** (input embebido) → **H2** (skip-logic sobre multi-select) → **H3** (DIVIPOLA completo) → **H4** (cascada). Con tests.
2. **Barrido de fixture** (curación [B manual] sobre `perfil_territorial_v7.json`): agregar faltantes (semanas embarazo, estrato, D17/F9/obs por capítulo, K17 sub-campos, K35, J31–J40 $), convertir a multi-select (C factores, H2/H3, I2, K33), corregir reglas (D7/D8 étnico, J2, P26→27, "otro"→captura, K "ninguno"→K22), pasar D6/D11/negocio a DIVIPOLA, reordenar K, mover Supervisor, marcar Cap T.
3. **Recompilar**: `cargar_perfil` → BD → `exportar_a_mobile` → bundle → verificar → cascada APK. (Versionar V7→V8.)
4. **Verificación funcional** de los ~8 que ya existen (J11, J24–26, K20, K37, L2, L4, etc.).

**Riesgo/nota:** el instrumento hoy está en V7; estos cambios justifican **V8** versionado (ver
memoria "fuente de verdad": editar fixture, no solo bundle; versionar). Territorial es 1 de 8
perfiles — este triage aplica al Territorial; Asistencia + 6 perfiles replicarían lo que aplique.
