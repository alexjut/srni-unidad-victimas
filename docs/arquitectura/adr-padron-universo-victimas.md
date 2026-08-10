# ADR — Padrón de búsqueda SICAV: del legacy de caracterización al universo de víctimas

**Fecha:** 5 de agosto de 2026
**Estado:** aprobado para implementación
**Reemplaza:** el padrón derivado de `GIC_PERSONA ⨝ M_CARACT_TABLA_RA_PER`

---

## 0. Qué disparó esto

Dos cédulas reportadas desde el territorio: en Vivanto se podían caracterizar y en
SICAV no aparecían.

| Documento | En `GIC_PERSONA` | En el universo | Diagnóstico |
|---|---|---|---|
| `28548486` | **no está** | **sí** — `CONS_PERSONA` 23988216, 3 hechos | nunca fue caracterizada |
| `1115724047` | sí, 3 filas | sí — `CONS_PERSONA` 23664117, 1 hecho | `ESTADO_RUV=2`, el filtro la excluyó |

**El padrón nacía del lugar equivocado.** `GIC_PERSONA` es el registro de *quién ya
fue caracterizado*; preguntarle "¿existe esta víctima?" es preguntarle al libro de
visitas quién vive en la ciudad. `28548486` era invisible porque nunca fue
caracterizada — no era un filtro mal puesto, era la fuente mal elegida.

---

## 1. Decisión

Arquitectura de **dos niveles con fuente única de verdad**:

| Nivel | Contenido | Volumen | Almacenamiento |
|---|---|---|---|
| Servidor | Universo completo de víctimas | ~12,5 M | PostgreSQL |
| Dispositivo | Subconjunto territorial de la jornada | ≤ 500 K | SQLite |

**Fuente:** `FUENTES.TEMP_UNIV_VICT_PER_MI<DDMMAA>ALL` vía dblink `CONSULTAFUENTES`.

El dispositivo **no** puede alojar 12,5 M en SQLite: el padrón offline ya son
5.001.402 registros, y duplicarlo es inviable en tamaño, tiempo de sincronización y
desempeño de consulta en equipos de campo.

---

## 2. 🔴 La llave de cruce es el DOCUMENTO, no `CONS_PERSONA`

**Medido el 5-ago-2026 y es el hallazgo que condiciona toda la implementación:**

```
pares con documento común comparados : 243.610
que tienen el mismo identificador    :       0   (0,0 %)
```

Concreto:

```
1115724047 → universo:    CONS_PERSONA  = 23664117
1115724047 → GIC_PERSONA: PER_IDPERSONA = 958858 / 6566478 / 9184606
```

`CONS_PERSONA` (universo) y `PER_IDPERSONA` (legacy) son **espacios de
identificadores distintos**. Nuestro `Victima.cons_persona` viene del segundo.

Dos consecuencias, y la segunda es la peligrosa:

1. **Un upsert por `cons_persona` no haría match con nada.** En vez de enriquecer
   5,9 M los duplicaría: el padrón terminaría en ~18 M con todo el mundo repetido.
2. **`cons_persona` es lo que `apps/sincronizacion/oracle/mapeo.py` usa para escribir
   al legacy.** Sobrescribirlo con el id del universo haría que la escritura mande
   identificadores de otro sistema. **No falla: escribe mal en silencio**, que es el
   modo de fallo que este proyecto viene evitando en todos los catálogos.

**Reglas que se derivan, no negociables:**

- El cruce universo ↔ padrón se hace **por documento** (hash), nunca por id.
- El id del universo se guarda en un **campo propio**, y **jamás** pisa
  `cons_persona`.
- Toda carga verifica que no se toque `cons_persona` de filas existentes.

---

## 3. Fuente única: el dispositivo deriva del servidor

El subconjunto del dispositivo **debe derivarse del universo cargado en el
servidor**, filtrado por territorio. No se conserva el extracto de `GIC_PERSONA`.

**Razón.** Si el servidor consulta el universo y el dispositivo mantiene el extracto
anterior, el mismo documento responde distinto según haya o no conexión. En campo
eso no se percibe como dos capas de arquitectura sino como **falla intermitente**, y
es un defecto que no se puede reproducir en pruebas. El estado actual es
consistentemente incorrecto; el mixto sería incorrecto de forma aleatoria, que es
peor.

---

## 4. Semántica de búsqueda offline: tres resultados, no dos

| Resultado | Condición | Qué se le dice al encuestador |
|---|---|---|
| `ENCONTRADO` | presente en el subconjunto local | datos de la persona |
| `NO_ELEGIBLE` | presente, con motivo que impide caracterizar | el motivo, y cómo continuar |
| `NO_VERIFICABLE` | ausente del subconjunto local **y sin conexión** | "no se puede confirmar sin conexión" |

**Queda prohibido** que el dispositivo responda "no existe" a un documento ausente
del subconjunto local: la ausencia local **no es evidencia de inexistencia**, solo
indica que está fuera del recorte territorial. Al recuperar señal, el caso se
reconsulta contra el servidor.

> **Ya hay dónde apoyarlo.** `MotivoNoElegible`
> (`apps/victimas/repository/base.py`) se implementó el 4-ago con
> `NO_EN_PADRON`, `DOCUMENTO_NO_IDENTIFICANTE`, `EXCLUIDA_RUV`, `FICHA_VIGENTE`,
> `BLOQUEADA_SIN_MOTIVO`, `ELEGIBLE` y `ELEGIBLE_POR_EXCEPCION`. `NO_VERIFICABLE`
> es **un valor más en ese enum**, no un mecanismo nuevo.

---

## 5. Reglas de carga

### 5.1 Resolución del corte por fecha

El nombre de la tabla origen **no debe quedar embebido en el código**:

```
TEMP_UNIV_VICT_PER_MI + DDMMAA + ALL      (010826 = 1 de agosto de 2026)
```

El proceso debe: verificar existencia en `ALL_TABLES@CONSULTAFUENTES` antes de
cargar; si el corte del mes no existe, usar el anterior **y registrarlo**; y alertar
si el más reciente supera los **45 días**.

**No es precaución teórica — hace falta desde el día uno.** Medido el 5-ago:

| Corte | Filas | Analizada |
|---|---|---|
| `MI010626ALL` (junio) | 12.473.749 | 2026-07-01 |
| `MI010726ALL` (julio) | 12.496.965 | 2026-07-28 |
| `MI010826ALL` (agosto) | — | **no existe todavía** |

La cadencia real no es "del 5 al 10": junio se analizó el 1-jul y julio el 28-jul.
El antecedente de `GIC_REPORTE_HOGAR`, congelado desde 2021 sin que nadie lo
notara, obliga a instrumentar la detección de obsolescencia desde el inicio.

### 5.2 Deduplicación

Sobre el corte 01/07/2026: **12.496.965** filas, **11.954.392** documentos únicos,
**12.009.492** con documento usable (≥5 caracteres). Hay **al menos 55.100 filas**
que comparten documento con otra — es un piso, no la cifra definitiva.

- Regla determinista y parametrizable, definida **antes** de cargar.
- Filas descartadas en tabla lateral, con motivo, para trazabilidad.
- Las duplicidades del snapshot **no deben propagarse** a la taxonomía de colisiones
  (`AMBIGUO`, `DUPLICADO_FUENTE`, `NO_IDENTIFICANTE`): ese mecanismo detecta casos
  legítimos de campo, y contaminarlo con ruido de origen lo inutiliza.

### 5.3 Registros sin documento usable

**487.473 filas** no tienen documento utilizable como criterio de búsqueda. Solo
tiene sentido cargarlas si existe una vía alterna (nombre completo, id del
universo); de lo contrario son volumen sin función.

---

## 6. Qué resuelve el universo y qué no

**Provee:** existencia e identidad.

**No provee** — verificado sobre las 12.496.965 filas:

| Columna | Estado real |
|---|---|
| `IDENTIFICADO` | **0 en todas las filas** — no poblada. **No usable como criterio** |
| `ACTIVO` | nulo en todas |
| `TIPO_VICTIMA` | `'S/I'` en todas |
| `ESTADO_RUV` | **no existe la columna** |

### Modelo de tres capas

| Capa | Fuente | Función |
|---|---|---|
| 1. Existencia e identidad | universo (12,5 M) | toda persona aparece |
| 2. Elegibilidad | `M_CARACT_TABLA_RA_PER` + vigencia | si procede caracterizar |
| 3. Hechos victimizantes | `RUV.TBSINIESTROS_PERSONA` | ya integrado (`hechos_ruv.py`) |

---

## 7. Vigencia: la regla es real, y su fuente está identificada

### ✅ La regla de 2 años NO se deroga

**Confirmado por Javier el 5-ago-2026.** Un análisis previo la marcó como *"sin
fuente citada"* por no encontrarla en los manuales 11-MU / 14-MU; **esa
observación era incorrecta y queda anulada**. Una nota que afirma que un control
no tiene respaldo es una invitación a quitarlo.

**Cómo se aplica:**

| Ruta | Regla de vigencia |
|---|---|
| **General** | **se respeta** — es el caso por defecto |
| Acciones constitucionales · Modificación de núcleo · Especial | se omite (Manual §5.1.1, pág. 22) |

Ya está implementado así en `RUTAS_QUE_OMITEN_VIGENCIA`
(`apps/victimas/homologacion.py`), con la excepción registrada en
`ExcepcionVigencia` y soporte fotográfico obligatorio.

### De dónde salen las fechas

**`TEMP_UNIV_VICT_CONTING`** es la fuente autoritativa: trae
`ENTRE_FICHA_VIGENTE`, `FECHA_CREACION` e `ID_ENTREVISTA` — la vigencia **dicha
por la fuente**, no calculada por nosotros.

Hoy ese objeto **no es accesible** desde nuestro usuario (probado el 5-ago: acceso
directo y los 22 dblinks, `ORA-00942` en todos; falta el `SERVICE_NAME` donde sí
resuelve). Mientras tanto, la vigencia se calcula con `fecha_ult_caracterizacion`,
que viene del legado vía `cargar_fechas_caracterizacion`.

⚠️ **Ese cálculo es un sustituto, no la fuente.** Cuando la tabla esté disponible,
la fecha debe salir de ahí, y el cálculo pasa a ser el respaldo para quien no
figure en ella.

### Lo que sigue siendo decisión de supervisión

Qué hacer con quien **no aparezca** en la fuente de vigencia cuando la tengamos:

- tratarlo como *no elegible* niega caracterización por una limitación de datos;
- tratarlo como *elegible* habilita casos que podrían no corresponder.

Ambas tienen implicaciones frente a la Ley 1448. **No es decisión de desarrollo.**
Hasta que se defina, el estado se registra pero no determina el flujo.

---

## 8. Nota de implementación: la errata de origen

Confirmado el 5-ago leyendo el diccionario:

| Tabla | Columna |
|---|---|
| `TEMP_UNIV_VICT_MI<DDMMAA>ALL` (hechos, 19.899.299 filas) | **`CONS_PERONA`** — col #59, errata de origen |
| `TEMP_UNIV_VICT_PER_MI<DDMMAA>ALL` (personas) | `CONS_PERSONA` — col #1 |

Verificar el nombre de cada lado al construir cruces entre ambas.

---

## 9. Verificación previa a la carga

Confirmar que la autorización vigente ampara la **tenencia** de una copia local de
12,5 M de registros con nombre y documento de víctimas, no solo el **acceso de
consulta**. La carga constituye una copia, no una consulta.

---

## 10. Secuencia de implementación

1. **DDL** de la tabla destino, con índice sobre el hash del documento y sobre el id
   del universo — **sin tocar `Victima.cons_persona`** (ver §2).
2. Proceso de carga con resolución de corte por fecha y deduplicación parametrizable.
3. Derivación del subconjunto territorial a partir de la tabla del servidor.
4. `NO_VERIFICABLE` en el cliente móvil.
5. Reconsulta automática contra el servidor al recuperar conexión.
