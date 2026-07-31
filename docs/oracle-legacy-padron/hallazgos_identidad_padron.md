# Cómo está armada la identidad de las personas en el legacy — hallazgos

> **Qué es esto.** Lo que encontramos al intentar reconstruir el padrón desde
> `MI_PERSONAS` (31-jul-2026). Buscábamos una cosa —de dónde sacar las víctimas y
> sus datos— y lo que apareció fue el **mapa de cómo está partida la identidad de
> las personas entre tres bases**. Este documento es ese mapa, con los defectos
> que trae y qué decidimos hacer hoy.
>
> **Por qué importa.** Estos no son detalles técnicos: definen **a quién le
> aparece la caracterización en la APK** y **con los datos de quién**. Un puente
> mal elegido no da un error: da la persona equivocada, en silencio.
>
> **Complementos:** la mecánica de los procedures va en
> [`../oracle-legacy/defectos_bd_legacy.md`](../oracle-legacy/defectos_bd_legacy.md);
> la calidad de los datos que ya escribimos, en
> [`../oracle-legacy/veredicto_calidad_bd.md`](../oracle-legacy/veredicto_calidad_bd.md).
>
> **Regla:** todo lo de aquí se midió con `SELECT` sobre producción. Nada se
> modificó. Cada cifra tiene su consulta.

**Leyenda:** 🔴 puede dar datos de otra persona · 🟠 obliga a un rodeo ·
🟡 higiene / deuda.

---

## El mapa: tres bases, tres nociones de "persona"

| Base | Host | Tabla maestra | Volumen | Qué es |
|---|---|---|---:|---|
| **ENTREVISTARN** (la .9) | 30.0.1.9 | `RNIENTREVISTA.GIC_PERSONA` | 7.760.393 | Las personas **caracterizadas** (nuestra base de trabajo) |
| **MODELO** | vía `DBL_RNIENTREVISTA` | `RNI_MI_PRU.MI_PERSONAS` | 49.529.440 | El **modelo integrado**: el país entero, víctimas y no víctimas |
| **VIVANTO** | vía `DBL_VIVANTO` | `RNIPAQUETES.M_CARACT_TABLA_RA_PER` | 9.961.503 | El **corte del RUV**: quién es víctima y en qué estado |

Ninguna de las tres es "el padrón". El padrón es el **cruce** de las tres, y ahí
está todo el problema.

---

## H1 — El corte del RUV es la única autoridad sobre quién es víctima ✅

**Evidencia.** `RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO`, 9.961.503 filas:

| `ESTADO_RUV` | Personas | Significado (`TBESTADO_VAL`) |
|---:|---:|---|
| 1 | **7.821.641** | Incluido |
| 2 | 1.702.949 | No Incluido |
| 3 | 430.499 | En Valoración |
| 4 | 340 | Excluido |

**Por qué creemos que el catálogo es `TBESTADO_VAL` y no otro.** Los 7.821.641
incluidos coinciden con la cifra pública del RUV de víctimas sujeto de atención.
Y "Excluido" con **340 personas** es coherente: excluir requiere acto
administrativo, es rarísimo. La otra lectura que se manejó (`3=Excluido`,
`4=Cesado`) daría 430.499 excluidos y 340 cesados, que no se sostiene.

**Consecuencia:** el filtro de víctimas es `ESTADO_RUV = 1`. Es lo que aplica la
carga. → `apps/victimas/homologacion.py::es_victima()`

---

## H2 — `MI_PERSONAS` **no tiene el estado del RUV** 🟠

**Evidencia.** Las 38 columnas de `RNI_MI_PRU.MI_PERSONAS` son de identidad
(documento, nombres, nacimiento, sexo, etnia, discapacidad, defunción). No hay
ninguna columna de condición de víctima ni de valoración.

**Consecuencia.** `MI_PERSONAS` **no puede ser la fuente del padrón por sí sola**:
son 49,5 millones de personas, el país entero. Filtrar a las víctimas obliga
siempre a cruzar contra Vivanto. Esto responde la pregunta de origen: MI_PERSONAS
es la fuente de **datos**, nunca de **universo**.

---

## H3 — El `CONS_PERONA` del corte no es un id del RUV: es de RUPD y SIV 🔴

**El hallazgo más grave.** El puente `RNI_MI_PRU.DEP_RUV_PERSONAS_MI` (11.437.570
filas) liga ids del registro con ids del modelo integrado. Tiene una columna
`FUENTE` con tres valores:

| `FUENTE` | Filas | Qué registro es |
|---|---:|---|
| `RUPD` | 5.935.569 | Registro Único de Población Desplazada (pre-Ley 1448) |
| `RUV` | 5.067.278 | Registro Único de Víctimas (el vigente) |
| `SIV` | 434.723 | Sistema de Información de Víctimas |

Al cruzar una muestra de **3.000** personas incluidas del corte contra ese puente:

```
RUPD   2.971
SIV    2.946
RUV        0      <-- ninguna
```

**El `CONS_PERONA` del corte de caracterización cruza con RUPD y con SIV, y con
ninguna del RUV.** Es decir: **el mismo número de id existe en dos registros
distintos y apunta a dos personas distintas.** Cruzar sin filtrar por `FUENTE`
devuelve ~2 filas por persona y no hay forma de saber cuál es la buena.

**Medido en toda la tabla:** 433.696 `ID_PERSONA` apuntan a más de un `PER_ID`
del modelo integrado.

**Consecuencia.** Este puente **no se puede usar hoy** para traer datos de
`MI_PERSONAS`: el riesgo es asignarle a una víctima los datos de otra persona.
Necesita que OTI aclare qué `FUENTE` corresponde al `CONS_PERONA` del corte.
**Es la pregunta #1 para OTI.**

---

## H4 — `GIC_PERSONA.PER_IDMODELOINT` no llega a `MI_PERSONAS` 🔴

**Evidencia.** `GIC_PERSONA` tiene 7.760.393 filas y 7.760.390 traen
`PER_IDMODELOINT` — parece la llave natural al modelo integrado. Se probaron
20.000 de esas llaves contra `MI_PERSONAS.PER_ID`:

```
muestra 20.000  ->  encontrados 0
```

**Cero.** La columna existe, está poblada casi al 100%, y **no cruza con nada**.
Apunta a otro modelo integrado (probablemente una versión anterior) o quedó
huérfana de una migración vieja.

**Consecuencia.** El camino "obvio" `GIC_PERSONA → MI_PERSONAS` no existe. Sumado
a H3, hoy **no hay un puente confiable hacia `MI_PERSONAS`**.

---

## H5 — Los documentos de `MI_PERSONAS` tienen basura de alta repetición 🔴

**Evidencia.** Se intentó el cruce por documento (que sería lo semánticamente
correcto: el documento es la identidad real, no un id interno). Con **20.000**
documentos de `GIC_PERSONA` contra `MI_PERSONAS`:

```
filas devueltas: 1.159.036.245     (1.159 millones)
documentos distintos en la muestra: 16.254
tiempo: 220 s
```

Son ~71.000 coincidencias por documento. Eso solo pasa si hay documentos
"comodín" (ceros, unos, cadenas de relleno) repetidos decenas de miles de veces.

**Consecuencia.** El cruce por documento **tampoco sirve sin sanear antes**:
habría que excluir no numéricos, ceros, longitudes imposibles. Y aun saneado
costó 220 s por 20.000 → inviable para 7,8 millones.

---

## H6 — El corte de Vivanto no tiene un solo índice 🟠

**Evidencia.** `all_indexes@DBL_VIVANTO` para `RNIPAQUETES.M_CARACT_TABLA_RA_PER`:
**SIN ÍNDICES**, sobre 9.961.503 filas. Toda consulta es *full scan*.

**Matiz honesto:** el full scan resultó **rápido** — contar los 7.827.597
incluidos tomó **4,1 s**. Para leer la tabla entera de una pasada no es problema.
Se vuelve problema al usarla como lado derecho de un JOIN fila por fila.

**Consecuencia.** La carga lee el corte **de un solo barrido**, nunca por lookup.

---

## H7 — `GIC_RUV_PERSONA` existe, tiene procedure de escritura, y está vacía 🟡

**Evidencia.** `RNIENTREVISTA.GIC_RUV_PERSONA` (`CONS_PERSONA`, `PER_IDPERSONA`,
`REG_TIMESTAMP`) tiene **0 filas**. Su procedure `GIC_SP_INGRESO_RUV_PERSONA`
está escrito y compilado. Nunca se usó.

Era exactamente la tabla que resolvería H3/H4: el puente propio de la .9 entre el
id del RUV y el id de la persona caracterizada. Está construida y sin poblar.

**Consecuencia.** Candidata natural para *arreglar* el problema más adelante: si
la poblamos nosotros, el puente queda del lado nuestro y deja de depender de las
tablas de trabajo de MODELO.

---

## H8 — La integración con el modelo integrado quedó a medias, y está anotado 🟡

**Evidencia.** En el cuerpo de `GIC_CARACTERIZACION`, línea 302:

```sql
SELECT GRP.*, GRP.Cons_Persona AS MI_IDPERSONA
  FROM GIC_RUV_PERSONA GRP
-- WHERE GRP.MI_IDPERSONA = ID_PERSONA;
-- SE DEBE CAMBIAR CUANDO SE AGREGUE EL IDPERSONA DE LA TABLA MI_PERSONAS DEL MODELO INTEGRADO
 WHERE GRP.CONS_PERSONA = ID_PERSONA;
```

El propio legacy documenta que **la integración con `MI_PERSONAS` está
pendiente**, y mientras tanto usa `CONS_PERSONA` como sustituto.

**Consecuencia.** Confirma que no estamos ante un puente que no supimos
encontrar: **el puente no se terminó de construir**. Y el paquete
`GIC_CARACTERIZACION` **no lee `MI_PERSONAS`** en ninguna parte (solo escribe en
`GIC_RESPUESTASENCUESTA`, `GIC_RUV_PERSONA` y actualiza `GIC_PERSONA`).

---

## H9 — `GIC_PERSONA` tiene duplicados contra el modelo integrado 🟠

**Evidencia.** 7.760.390 filas con `PER_IDMODELOINT`, pero solo **5.131.334
valores distintos**. Es decir, ~2,6 millones de filas comparten llave con otra.

Con el matiz de H4 (esa llave no cruza con nada), el dato hay que leerlo con
pinzas: puede ser duplicación real de personas o basura heredada. Queda
registrado para revisar.

---

## H10 — Un tercio de `GIC_PERSONA` son documentos repetidos 🔴

**Evidencia.** Documentos de `GIC_PERSONA` por número de veces que aparecen:

| Veces | Documentos | Filas que representan |
|---:|---:|---:|
| 1 | 4.024.467 | 4.024.467 |
| 2 | 1.137.976 | 2.275.952 |
| 3 | 303.587 | 910.761 |
| 4 | 74.521 | 298.084 |
| 5 | 21.027 | 105.135 |
| 6 | 7.673 | 46.038 |

**~5,57 M documentos distintos para 7,76 M de filas: ~2,2 millones de filas son
repeticiones de un documento ya presente.**

**Qué hicimos.** No fusionar. Decisión del 29-jul: dos filas con el mismo documento
**pueden ser personas distintas** (documentos mal digitados, homónimos con error de
captura), y fusionarlas borraría a una del padrón. Se cargan como registros
separados y la búsqueda por documento puede devolver más de un resultado — que es
la verdad de la base, no un defecto de la APK.

**Para arreglar después:** hace falta un criterio de deduplicación con el área
funcional (¿nombre + fecha de nacimiento + documento?), no una decisión técnica.

---

## H11 — 17 personas caracterizadas hace ~2.000 años 🟡

**Evidencia.** Antigüedad de la caracterización por persona, sobre las 3.331.794
que tienen alguna:

```
hace  0 años   685.452        hace  5 años     6.662
hace  1 año    707.853        hace  6 años     6.262
hace  2 años   711.347        ...
hace  3 años   246.122        hace 12 años        10
hace  4 años   912.629        hace 16 años         7
                              hace 2000 años      17   <-- imposible
```

Fechas del año 26 d.C. y similares. La Unidad existe desde la Ley 1448 de **2011**.

**Qué hicimos.** `cargar_fechas_caracterizacion` descarta todo lo anterior a 2011 y
lo deja en nulo, que por `debe_recaracterizarse()` significa "hay que
caracterizarla" — lo correcto para un dato que no sabemos.

**De paso, el dato que importa:** con la regla de 2 años, **1.936.352 personas
(58,2 % de las caracterizadas) están vencidas**. El pico de "hace 4 años"
(912.629) es la campaña masiva de 2022, que venció completa.

---

## Qué decidimos hacer HOY (y por qué)

La intención era reconstruir el padrón **desde `MI_PERSONAS`**, que es la fuente
más completa y actualizada. **Las mediciones dicen que hoy no se puede hacer sin
riesgo de asignar datos de otra persona** (H3 + H4 + H5).

Entonces, para la carga de esta semana:

| Pieza | De dónde sale | Estado |
|---|---|---|
| **Quiénes** (universo) | corte de Vivanto, `ESTADO_RUV = 1` | ✅ confiable (H1) |
| **Datos** (identidad) | `GIC_PERSONA` de la .9 | ✅ cruza con el corte |
| **Cuándo se caracterizó** | `GIC_HOGAR.USU_FECHACREACION` | ✅ local, sin dblink |
| ~~Enriquecer con `MI_PERSONAS`~~ | — | ⛔ **aplazado**: puente ambiguo |

Esto **cumple lo que se pidió** —solo víctimas, regla de 2 años— y evita meter
datos equivocados por un puente que la propia base documenta como incompleto.

`MI_PERSONAS` queda como el destino, no como el punto de partida: entra cuando
OTI aclare H3, o cuando poblemos `GIC_RUV_PERSONA` nosotros (H7).

### Lo que cuesta esa decisión: 1,88 M de víctimas sin identidad 🔴

Hay que decirlo claro, porque es el precio real:

| | Personas |
|---|---:|
| Víctimas **incluidas** según el corte | 7.821.641 |
| …que además tienen identidad en `GIC_PERSONA` | **5.936.769** |
| **Incluidas SIN identidad en la .9** | **1.884.872 (24,1 %)** |

Una de cada cuatro víctimas incluidas **no puede entrar al padrón** porque la .9
no tiene sus datos de identidad. `MI_PERSONAS` es justamente donde están —por eso
era el origen deseado— pero llegar hasta ellos hoy exige un puente que puede
devolver a otra persona (H3), y eso es peor que no tenerlos.

**Mitigación en campo:** la APK **debe permitir alta manual** de quien no aparezca
en el padrón. No es un caso raro: es una de cada cuatro.

**Y del otro lado:** de las 7.760.393 personas de `GIC_PERSONA`, solo 5.936.769
son víctimas incluidas. El filtro deja fuera a **1.828.305**:

| Estado en el corte | Personas de `GIC_PERSONA` |
|---|---:|
| 1 Incluido | **5.936.769** ← al padrón |
| 2 No Incluido | 1.328.436 |
| (sin corte) | 467.602 |
| 3 En Valoración | 31.990 |
| 4 Excluido | 277 |

Sin el filtro, el padrón llevaría 1,83 M de personas que **no son víctimas
incluidas**, y el encuestador no tendría cómo saberlo.

---

## Preguntas para OTI (en orden de importancia)

1. **(H3)** El `CONS_PERONA` de `M_CARACT_TABLA_RA_PER` cruza con `FUENTE='RUPD'`
   y `'SIV'` en `DEP_RUV_PERSONAS_MI`, nunca con `'RUV'`. ¿Cuál es la fuente
   correcta para resolver una persona del corte de caracterización?
2. **(H4)** ¿Contra qué tabla cruza `GIC_PERSONA.PER_IDMODELOINT`? No cruza con
   `MI_PERSONAS.PER_ID`.
3. **(H7)** ¿`GIC_RUV_PERSONA` se dejó de usar a propósito, o quedó pendiente de
   poblar? ¿Podemos poblarla nosotros?
4. **(H1)** Confirmar que `ESTADO_RUV` de ese corte usa `TBESTADO_VAL`
   (1=Incluido … 7=No Afectado-No Valorado).
5. **(corte)** ¿Con qué periodicidad se refresca `M_CARACT_TABLA_RA_PER`? De eso
   depende cada cuánto recargamos el padrón.

---

## Cómo usar este registro

Nada de aquí bloquea la salida a producción de la APK: **todo está rodeado**. Es
la lista de lo que hay que atacar cuando la APK esté funcionando, que es
exactamente el orden que acordamos. Cuando se resuelva un punto, se marca aquí
con la fecha y cómo se resolvió.
