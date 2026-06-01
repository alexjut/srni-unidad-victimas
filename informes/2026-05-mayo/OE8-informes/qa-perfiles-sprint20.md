# QA detallado perfil por perfil — Sprint 20

**Fecha:** 2026-05-26

**Generado automáticamente** por `srni-backend/scripts/qa_perfiles.py`


Compara para cada instrumento: BD ↔ Bundle ↔ Tipos problemáticos.

## Resumen ejecutivo

| Instrumento | Caps | BD activas | Bundle | Coincide | Sin opciones | Hogar / Persona |
|---|---:|---:|---:|:-:|---:|---|
| ASISTENCIA | 7 | 174 | 174 | ✅ | 1 | 100 / 74 |
| BUENAVENTURA | 17 | 151 | 151 | ✅ | 3 | 90 / 61 |
| RURAL_ETNICO | 14 | 105 | 105 | ✅ | 2 | 66 / 39 |
| SAN_ANDRES | 14 | 109 | 109 | ✅ | 0 | 59 / 50 |
| TELEFONICO | 7 | 67 | 67 | ✅ | 4 | 18 / 49 |
| TERRITORIAL | 14 | 200 | 200 | ✅ | 4 | 91 / 109 |
| URBANO_ETNICO | 12 | 85 | 85 | ✅ | 2 | 42 / 43 |
| VICTIMAS_EXTERIOR | 8 | 110 | 110 | ✅ | 0 | 110 / 0 |

**Leyenda:** "Coincide" indica si el número de preguntas activas en BD coincide con las del bundle exportado.
"Sin opciones" cuenta preguntas LISTA/RADIO/LISTA_MULTIPLE/COMBO_DINAMICO sin opciones cargadas (no renderizan bien).

## Detalle por instrumento

### ASISTENCIA — Asistencia humanitaria (vV8)

- Capítulos: **7**
- Preguntas activas en BD: **174** (inactivas: 4)
- Preguntas en bundle: **174**
- Reglas skip logic en bundle: 38

**Tipos de pregunta (bundle):**
  - `RADIO`: 97
  - `TEXTO`: 23
  - `NUMERICO`: 21
  - `BOOLEAN`: 21
  - `LISTA`: 8
  - `COMBO_DINAMICO`: 3
  - `FECHA`: 1

**Nivel (bundle):**
  - `HOGAR`: 100
  - `PERSONA`: 74

**⚠️ Preguntas sin opciones cargadas (1):**
  - `A/-Z15_tel(COMBO_DINAMICO)`

### BUENAVENTURA — Buenaventura — Sentencia T-045 (vV7)

- Capítulos: **17**
- Preguntas activas en BD: **151** (inactivas: 1)
- Preguntas en bundle: **151**
- Reglas skip logic en bundle: 22

**Tipos de pregunta (bundle):**
  - `BOOLEAN`: 68
  - `LISTA`: 44
  - `TEXTO_LARGO`: 11
  - `TEXTO`: 10
  - `NUMERICO`: 8
  - `LISTA_MULTIPLE`: 4
  - `COMBO_DINAMICO`: 3
  - `FECHA`: 3

**Nivel (bundle):**
  - `HOGAR`: 90
  - `PERSONA`: 61

**⚠️ Preguntas sin opciones cargadas (3):**
  - `A/A2-Z2_bv(COMBO_DINAMICO)`
  - `A/A5-Z5A_bv(COMBO_DINAMICO)`
  - `HV/HV3-HV3_bv(COMBO_DINAMICO)`

### RURAL_ETNICO — Rural étnico (vV1)

- Capítulos: **14**
- Preguntas activas en BD: **105** (inactivas: 1)
- Preguntas en bundle: **105**
- Reglas skip logic en bundle: 25

**Tipos de pregunta (bundle):**
  - `BOOLEAN`: 41
  - `LISTA`: 36
  - `TEXTO`: 9
  - `TEXTO_LARGO`: 8
  - `NUMERICO`: 4
  - `LISTA_MULTIPLE`: 4
  - `COMBO_DINAMICO`: 2
  - `FECHA`: 1

**Nivel (bundle):**
  - `HOGAR`: 66
  - `PERSONA`: 39

**⚠️ Preguntas sin opciones cargadas (2):**
  - `A/A2-Z2_re(COMBO_DINAMICO)`
  - `A/A5-Z5A_re(COMBO_DINAMICO)`

### SAN_ANDRES — San Andrés, Providencia y Santa Catalina (vV7)

- Capítulos: **14**
- Preguntas activas en BD: **109** (inactivas: 1)
- Preguntas en bundle: **109**
- Reglas skip logic en bundle: 11

**Tipos de pregunta (bundle):**
  - `BOOLEAN`: 50
  - `LISTA`: 34
  - `TEXTO`: 9
  - `TEXTO_LARGO`: 7
  - `NUMERICO`: 6
  - `FECHA`: 2
  - `LISTA_MULTIPLE`: 1

**Nivel (bundle):**
  - `HOGAR`: 59
  - `PERSONA`: 50

### TELEFONICO — Entrevista telefónica (vV8)

- Capítulos: **7**
- Preguntas activas en BD: **67** (inactivas: 2)
- Preguntas en bundle: **67**
- Reglas skip logic en bundle: 4

**Tipos de pregunta (bundle):**
  - `BOOLEAN`: 20
  - `LISTA`: 19
  - `TEXTO`: 9
  - `NUMERICO`: 7
  - `COMBO_DINAMICO`: 4
  - `LISTA_MULTIPLE`: 3
  - `TEXTO_LARGO`: 3
  - `FECHA`: 2

**Nivel (bundle):**
  - `HOGAR`: 18
  - `PERSONA`: 49

**⚠️ Preguntas sin opciones cargadas (4):**
  - `A/A3-Lud_encuesta(COMBO_DINAMICO)`
  - `A/A6-Z5A_tel(COMBO_DINAMICO)`
  - `A/A16-Z15_tel(COMBO_DINAMICO)`
  - `B/B18-A23A_tel(COMBO_DINAMICO)`

### TERRITORIAL — Caracterización territorial (vV7)

- Capítulos: **14**
- Preguntas activas en BD: **200** (inactivas: 1)
- Preguntas en bundle: **200**
- Reglas skip logic en bundle: 4

**Tipos de pregunta (bundle):**
  - `BOOLEAN`: 84
  - `LISTA`: 52
  - `TEXTO`: 19
  - `NUMERICO`: 16
  - `TEXTO_LARGO`: 12
  - `LISTA_MULTIPLE`: 11
  - `COMBO_DINAMICO`: 4
  - `FECHA`: 2

**Nivel (bundle):**
  - `HOGAR`: 91
  - `PERSONA`: 109

**⚠️ Preguntas sin opciones cargadas (4):**
  - `A/A2-Z2(COMBO_DINAMICO)`
  - `A/A5-Z5A(COMBO_DINAMICO)`
  - `A/A15-Z15(COMBO_DINAMICO)`
  - `B/B47-A23A(COMBO_DINAMICO)`

### URBANO_ETNICO — Urbano étnico (vV1)

- Capítulos: **12**
- Preguntas activas en BD: **85** (inactivas: 1)
- Preguntas en bundle: **85**
- Reglas skip logic en bundle: 6

**Tipos de pregunta (bundle):**
  - `LISTA`: 33
  - `BOOLEAN`: 24
  - `TEXTO`: 10
  - `TEXTO_LARGO`: 6
  - `LISTA_MULTIPLE`: 5
  - `NUMERICO`: 4
  - `COMBO_DINAMICO`: 2
  - `FECHA`: 1

**Nivel (bundle):**
  - `HOGAR`: 42
  - `PERSONA`: 43

**⚠️ Preguntas sin opciones cargadas (2):**
  - `A/A2-Z2_ue(COMBO_DINAMICO)`
  - `A/A5-Z5A_ue(COMBO_DINAMICO)`

### VICTIMAS_EXTERIOR — Víctimas en el exterior (vV1)

- Capítulos: **8**
- Preguntas activas en BD: **110** (inactivas: 0)
- Preguntas en bundle: **110**
- Reglas skip logic en bundle: 0

**Tipos de pregunta (bundle):**
  - `LISTA`: 95
  - `TEXTO`: 15

**Nivel (bundle):**
  - `HOGAR`: 110

## Problemas globales

- Total preguntas sin opciones cargadas: **16**
- Total capítulos vacíos: **0**
- Instrumentos con discrepancia BD↔Bundle: **0** / 8
