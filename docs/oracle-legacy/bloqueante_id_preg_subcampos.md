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
