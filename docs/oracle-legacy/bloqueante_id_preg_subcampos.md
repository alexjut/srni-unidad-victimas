# 🔴 BLOQUEANTE — preguntas de SICAV apuntando al `id_preg` equivocado de Oracle

> **Fecha:** 2026-07-28 · **Detectado al** mapear las 19 preguntas geográficas contra
> el instrumento (punto 3 de la lista previa al piloto).
> **Estado: ABIERTO. Bloquea el piloto en producción** de los perfiles afectados.

## El problema en una frase

Hay **75 preguntas de SICAV cuyo `id_preg` corresponde, en el catálogo real de Oracle, a
una pregunta completamente distinta**. Si se escriben, la respuesta se guarda **en la
pregunta equivocada** — y como los procedures se tragan los errores, nadie se entera.

## Ejemplos, del catálogo completo de producción

| Pregunta en SICAV | `id_preg` | Lo que ese id ES en Oracle |
|---|---:|---|
| `OBS_F` "Observaciones a este capítulo" | 1438 | *"QUÉ DIAGNÓSTICO DE ENFERMEDAD PRESENTA?"* |
| `D8A_ESTRATO` "¿Cuál es el estrato de la vivienda?" | 1443 | *"En este trabajo… es"* |
| `PL11A_TIPO` "Tipo" (de curso) | 1451 | *"Lugar de Residencia"* |
| `M8_VALOR` "¿Valor recibido el mes pasado? $" | 1460 | *"Departamento y municipio de Correspondencia"* |
| `C1_re` "¿Cuál es el tipo de vivienda?" | 42 | *"Incluyendo sala-comedor, ¿de cuántos cuartos…"* |
| `C3_re` "¿El piso es principalmente de?" | 44 | *"Regularmente, ¿cuántas personas duermen…"* |

## Alcance medido

Cruce de **1.155** preguntas con `id_preg` contra las 902 del catálogo Oracle,
comparando el texto por solapamiento de palabras significativas:

| | |
|---|---:|
| Coherentes (solape ≥ 20 %) | **1.080** |
| **Sospechosas (solape < 20 %)** | **75** |
| `id_preg` que no existen en el catálogo Oracle | 59 |

Por perfil: **rural_etnico_v1: 43** · **territorial_v8: 41** · **telefonico_v8: 16**.

> ⚠️ El detector es heurístico: compara textos. Puede dar falsos positivos cuando SICAV
> reformuló la redacción. **Cada caso hay que confirmarlo a mano** antes de tocarlo. Pero
> los ejemplos de arriba no son falsos positivos: "Observaciones a este capítulo" no es
> "QUÉ DIAGNÓSTICO DE ENFERMEDAD PRESENTA".

## De dónde salió — son dos causas distintas

**1. Sub-campos del barrido V7→V8 (territorial_v8).** Los 41 casos son preguntas
**nuevas** creadas en ese barrido: observaciones por capítulo, `D8A_ESTRATO`, los
sub-campos de cursos (`PL9A_*`, `PL10A_*`, `PL11A_*`) y los valores de ingresos
(`M8_VALOR`…). Se les asignó un `id_preg` correlativo libre **en SICAV**, sin comprobar
que ese número ya está ocupado **en Oracle** por otra pregunta. El rango 1438-1461 de
Oracle está lleno de preguntas reales.

**2. Desplazamiento sistemático (rural_etnico_v1).** Aquí el patrón es otro: bloques
enteros corridos. `C1_re`→42, `C2_re`→43, `C3_re`→44, `C4_re`→45, `C5_re`→46… cada una
apunta a la vecina de Oracle. Parece un *off-by-N* al generar el perfil, no ids
inventados. **Es el más peligroso de los dos: los textos son verosímiles y del mismo
capítulo, así que el error no salta a la vista.**

## Por qué no lo habíamos visto

- El catálogo completo de Oracle (902 preguntas) solo existe desde el **22-jul**; antes
  estaba truncado a 200 filas y estos ids no se podían comprobar.
- Los Escalones 1 y 2 escribieron con las preguntas **5, 24 y 3**, que están bien
  mapeadas. El escenario demo nunca tocó una pregunta afectada.
- Es un caso de la misma familia que el `PR3_re → id_preg=92` detectado el 22-jul (todo el
  bloque de Ayuda Humanitaria apuntaba a rehabilitación). Aquel se corrigió; **este es el
  mismo defecto a mayor escala**.

---

## ✅ territorial_v8 — CERRADO (2026-07-28)

Las 41 pasaron a `id_preg = null`. Ninguna tenía equivalente 1:1 en Oracle: son
sub-campos propios de SICAV. El detector automático lo confirmó por reducción al
absurdo — proponía mandar las 10 preguntas de *"¿Valor recibido el mes pasado? $"* al
id **138**, que es *"Incluyo este valor en los ingresos del mes pasado"*: otra pregunta.

Con `null`, el resolver las declara *"SICAV pregunta algo que Oracle no tiene dónde
guardar"* y **no escribe nada**; el dato sigue completo en PostgreSQL. Se añadió el test
`test_id_preg_no_apunta_a_pregunta_ajena.py`, verificado que detecta de verdad.

---

## Lo aprendido en telefonico_v8 y rural_etnico_v1 (siguen ABIERTOS)

Al buscarles el id correcto aparecieron **tres situaciones distintas**, y por eso no se
puede aplicar una regla única:

**a) Campos que Oracle no modela como pregunta.** `A2_tel` = *"Segundo nombre"*, con
`id_preg=15`. Oracle **no tiene** "Segundo nombre": tiene *"Nombres y apellidos"* (457) y
*"Nombre(s) y Apellidos (s)"* (1542), en un solo campo. SICAV parte el nombre porque
`GIC_INSERT_PERSONAS` lo recibe partido, pero eso viaja en el paso **PERSONA**, no como
respuesta de encuesta. ⇒ estos van a `null`.

**b) Desplazamiento sistemático, con offset constante.** En el bloque C (vivienda) de
rural_etnico el corrimiento es **+6**, verificado:

| SICAV | tiene | debería tener | Oracle |
|---|---:|---:|---|
| `C1_re` "¿Cuál es el tipo de vivienda?" | 42 | **36** | "¿En qué tipo de vivienda habita el hogar?" |
| `C2_re` "¿Las paredes exteriores…?" | 43 | **37** | "¿Cuál es el material predominante de las paredes…?" |

⚠️ **Pero hay ids duplicados**: esa misma pregunta existe también como **1493** y **1496**.
Es el caso Cédula otra vez (93 vs 3854). Elegir exige **medir el uso real en producción**,
no adivinar.

**c) Falsos positivos del detector.** `G4_tel` = *"¿Por qué no asiste actualmente a un
establecimiento educativo?"* con `id_preg=73`, que en Oracle es *"¿Cuál es la razón
principal para que… no estudie?"*. **Es la misma pregunta con otra redacción** — el
detector la marcó porque comparte pocas palabras. Aquí no hay nada que arreglar.

> **Conclusión operativa:** estos dos perfiles necesitan **curaduría caso por caso contra
> el manual oficial**, más una medición de uso en prod para desempatar los ids duplicados.
> No admiten arreglo masivo. Es media jornada de trabajo, no diez minutos.

---

## ✅ telefonico_v8 y rural_etnico_v1 — CERRADOS (2026-07-28, tarde)

Curados con el método que resolvió la geografía: **medir el uso real en producción**,
no adivinar. Resultado sobre los 34 casos:

| Decisión | Cuántos | Criterio |
|---|---:|---|
| **CORREGIR** | 3 | hay candidato con el mismo texto **y** el uso lo desempata |
| **DEJAR** | 4 | falso positivo del detector: misma pregunta, otra redacción |
| **A NULL** | 27 | Oracle no la tiene, o el candidato no tiene evidencia de uso |

### Las 3 correcciones, con su dato

| Pregunta | Tenía | Pasa a | Por qué |
|---|---:|---:|---|
| `C1_re` "¿Cuál es el tipo de vivienda?" | 42 | **36** | Oracle repite *"¿En qué tipo de vivienda habita el hogar?"* en 36 y 1493. **36 tiene 15.948 usos; 1493 solo 1.165.** El id 42 que tenía es *"¿de cuántos cuartos dispone?"*, con 15.009 usos: escribíamos en una pregunta muy transitada |
| `I7E_tel` "enfermedades ruinosas" | 400 | **794** | El mismo texto existe en 794, 1477 y 1567. **794: 33.051 usos** · 1477: 5.800 · 1567: 20 |
| `H14_tel` "¿Cuál enfermedad?" | 808 | **865** | 865: 740 usos · 1478: 309 · 1568: 0 |

### Las 4 que NO se tocaron — y por qué importa

El detector las marcó, y hacerle caso habría **roto** mapeos correctos:

- `G4_re` / `G4_tel` (73): *"¿Por qué no asiste a un establecimiento educativo?"* y
  *"¿Cuál es la razón principal para que no estudie?"* son **la misma pregunta**.
- `Z4_ETNIA_re` (35): *"Pertenencia étnica"* == *"De acuerdo con su cultura… se
  autoreconoce como:"*. La 35 **es** la del autorreconocimiento étnico.
- `PR3_re` (354): el detector proponía moverla a **92**… que es justo el error que se
  corrigió el 22-jul. **El detector no distingue una corrección deliberada de un fallo.**

Estas cuatro quedaron como `EQUIVALENCIAS_REVISADAS` en el test, cada una con su razón
escrita — y hay un test que exige que la razón exista y sea algo más que "ok".

### ⚠️ La deuda que queda (importante)

De las **27 que fueron a `null`**, una parte son campos que Oracle sencillamente no
modela como pregunta y ahí no hay nada que recuperar: `A2` "Segundo nombre", `A20`
"Estado de inclusión en el RUV", `A22` "Fecha de ocurrencia", `A23A` "Municipio de
ocurrencia", `A11` "¿la Unidad lo incluyó?". **Son datos del padrón/RUV, no respuestas
del instrumento**, y viajan por el paso PERSONA o vienen del propio RUV.

Pero otras **sí son preguntas legítimas que Oracle muy probablemente tiene con otro
texto**, y no logré identificar su id con certeza: `C2_re` (paredes), `C3_re` (piso),
`C4_re` (techo), `C5_re` (agua), `C6_re` (saneamiento), `H8_re` (régimen de salud),
`H9_re`, `H13_re`/`H13_tel` (enfermedad crónica), `L15_tel` (horas trabajadas),
`I8_tel` (salud mental), `I27_tel`/`I28A_tel` (rehabilitación)…

**Con `null` esas respuestas no se migran a Oracle.** El dato queda completo en
PostgreSQL, pero no llega al sistema de la UARIV. **Es pérdida de alcance, no de datos**,
y es deliberada: la alternativa era escribirlas en una pregunta ajena.

**Para cerrarlo hace falta el manual oficial** (11-MU / 14-MU) y cotejar pregunta por
pregunta contra el catálogo de Oracle. El caso `C5_re` ilustra por qué no se puede
automatizar: su candidato (1305, *"¿DE DÓNDE OBTIENE PRINCIPALMENTE ESTE HOGAR EL AGUA…"*)
calza al 71 % pero tiene **0 usos** en producción — no hay evidencia de que sea el id
vigente, y escribir en una pregunta muerta es tan inútil como escribir en la equivocada.

## Qué hacer

**Nada de arreglos masivos automáticos.** Un `id_preg` mal puesto se arregla con criterio,
caso por caso, y hay dos salidas legítimas:

1. **La pregunta SÍ existe en Oracle con otro id** → corregir el `id_preg` en el fixture
   (y el bundle). Aplica a los desplazamientos de `rural_etnico`.
2. **La pregunta NO existe en Oracle** (es un sub-campo propio de SICAV) → poner
   `id_preg = null`. El resolver ya sabe qué hacer con eso: lo declara *"SICAV pregunta
   algo que Oracle no tiene dónde guardar"* y lo trata como pendiente de negocio, en vez
   de escribir en la casilla equivocada. **Aplica a casi todos los de territorial_v8.**

**Orden sugerido:** territorial_v8 primero (es el perfil del piloto y su arreglo es casi
todo "poner a null"), después telefonico_v8, después rural_etnico_v1 (el más laborioso:
hay que encontrar el id correcto de cada una).

## Efecto sobre el piloto

- El piloto **puede seguir** si se hace con un hogar cuyas respuestas no toquen ninguna de
  las 41 preguntas afectadas de territorial_v8 — pero eso es una restricción artificial y
  frágil.
- **Recomendación:** arreglar territorial_v8 antes del piloto. Es el perfil con el que se
  va a escribir, y el arreglo es mecánico (poner a `null` los sub-campos que Oracle no
  tiene). Sin eso, el primer hogar real con observaciones de capítulo o cursos escribiría
  datos en preguntas ajenas de la base de la UARIV.

## Reproducir

El detector está en el scratchpad de la sesión (`auditar_id_preg.py`): lee los fixtures,
cruza `id_preg` contra `respuestas_oracle.json` y lista los sospechosos con ambos textos.
Conviene convertirlo en un comando de management (`auditar_id_preg`) para que corra en CI
y no vuelva a pasar.
