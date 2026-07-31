# Defectos del Oracle legacy — registro para arreglar DESPUÉS de la migración

> **Qué es esto.** El inventario de defectos de **diseño y comportamiento** de
> `RNIENTREVISTA` que fuimos encontrando al construir la escritura SICAV→Oracle
> (jul-2026). No es una queja: es la lista de trampas que hoy tenemos rodeadas en
> nuestro código y que **conviene arreglar en la base cuando la migración esté
> cerrada**, para no quedarnos con los parches para siempre.
>
> **Complementos:**
> * la calidad de los DATOS (huérfanos, duplicados, nulos) va en
>   [`veredicto_calidad_bd.md`](veredicto_calidad_bd.md);
> * cómo está partida la **identidad de las personas** entre las tres bases
>   (`.9`, MODELO, VIVANTO) —los puentes rotos, los ids ambiguos y por qué
>   `MI_PERSONAS` no se puede usar todavía— va en
>   [`../oracle-legacy-padron/hallazgos_identidad_padron.md`](../oracle-legacy-padron/hallazgos_identidad_padron.md).
>
> Este documento es el de la **mecánica**: procedures, contratos, convenciones.
>
> **Regla de este registro:** cada defecto va con su evidencia. Lo que es sospecha se
> marca como sospecha. Nada de aquí se midió modificando producción: solo `SELECT` y
> lectura del PL/SQL.

**Leyenda de severidad:** 🔴 puede corromper o perder datos en silencio ·
🟠 obliga a un rodeo permanente en nuestro código · 🟡 higiene / deuda.

---

## Resumen

| # | Defecto | Sev. | Estado hoy |
|---|---|:--:|---|
| D1 | Los procedures hacen `COMMIT` interno y se tragan las excepciones | 🔴 | rodeado (verificamos por SELECT) |
| D2 | `GIC_SP_OBTPUNTOATECION`: el parámetro `Id_DT` espera el id de **DEPARTAMENTO** | 🔴 | rodeado (le pasamos id_depto) |
| D3 | En Oracle `''` **es** `NULL` → un campo vacío rompe un NOT NULL sin avisar | 🔴 | rodeado (nunca mandamos '') |
| D4 | La cascada territorial: solo el 1.º inserta, los otros 3 son UPDATE | 🔴 | rodeado (orden fijo + verificación) |
| D5 | Dos convenciones incompatibles para la geografía, una comentada al lado de la otra | 🟠 | resuelto por medición |
| D6 | Ids duplicados de catálogo (caso Cédula: 4 ids, mismo texto) | 🟠 | rodeado (usamos el canónico) |
| D7 | `SP_CARGAUTOCOMPLETAR` ejecuta SQL **almacenado en una tabla** | 🟠 | no usado por nosotros |
| D8 | `FN_VALOR_DIVIPOLA` devuelve el código crudo cuando falla | 🟠 | no usado por nosotros |
| D9 | `GIC_N_RESPUESTASENCUESTA` no guarda la pregunta, solo la respuesta | 🟠 | rodeado |
| D10 | Objetos INVALID en el esquema | 🟡 | ver veredicto de datos |
| D11 | `PBANDERA=1` borra las respuestas previas del par (hogar, pregunta) | 🟡 | decidido y documentado |
| D12 | Nombres de catálogo divergentes entre sistemas (comas, tildes) | 🟡 | rodeado (normalizadores) |

---

## D1 — Los procedures hacen `COMMIT` interno y se tragan las excepciones 🔴

**Evidencia.** Todos los `GIC_*` de la ruta de escritura terminan en
`EXCEPTION WHEN OTHERS THEN ...` sin re-lanzar, y hacen `COMMIT` dentro del propio
procedure.

**Consecuencia.** No hay transacción envolvente **y no hay errores en los que confiar**.
Un dato mal mapeado no explota: *no escribe nada y nadie se entera*. Es el defecto raíz
del que salen casi todos los demás — convierte cualquier error de contrato en una
pérdida silenciosa.

**Cómo lo rodeamos.** Regla del proyecto: *solo avanza lo verificado por `SELECT`
posterior*, nunca lo que el procedure "dijo" que hizo. Toda escritura queda en un ledger
propio con su verificación.

**Arreglo propuesto.** Quitar el `COMMIT` interno y dejar que el llamador controle la
transacción; re-lanzar la excepción (o devolver un código de error) en vez de tragarla.
Es un cambio de contrato: rompe a los clientes actuales, así que exige coordinación.
**Esfuerzo: alto.** **No hacerlo durante la migración.**

## D2 — `GIC_SP_OBTPUNTOATECION`: el nombre del parámetro miente 🔴

**Evidencia.** El parámetro formal se llama `Id_DT`, pero el cuerpo hace
`SET iddeptoaten = Id_dt` y filtra `T.IDDEPARTAMENTO = pId_DT` (body 3140 y 3162).
Espera el id de **DEPARTAMENTO**, no el de la Dirección Territorial.

**Consecuencia.** Quien confíe en el nombre mete el valor equivocado en `IDDEPTOATEN` y
rompe el join de los reportes (`RL.IDDEPTOATEN = PA.IDDEPARTAMENTO`) — sin error, otra
vez por D1. Es exactamente la forma del bug histórico de territorio.

**Arreglo propuesto.** Renombrar el parámetro a `Id_Departamento`. Cosmético en apariencia,
pero evita que el siguiente equipo caiga. **Esfuerzo: bajo** (ojo: los llamadores que
bindean por nombre formal hay que actualizarlos a la vez).

## D3 — En Oracle `''` es `NULL` 🔴

**Evidencia.** Un hogar sin `creado_por` producía `USUA_CREACION=''`; como
`GIC_HOGAR.USU_USUARIOCREACION` es NOT NULL, el INSERT falla… y el procedure se traga el
error (D1). Encontrado en el Escalón 1.

**Arreglo propuesto.** No es un defecto de la base sino de Oracle, pero sí lo es
**depender de NOT NULL para validar** cuando el error se traga. Añadir validación
explícita al inicio del procedure con `RAISE_APPLICATION_ERROR`. **Esfuerzo: bajo.**

## D4 — La cascada territorial: solo el primero inserta 🔴

**Evidencia.** De los 4 procedures, solo `GIC_SP_OBDEPTOPORDT` hace `INSERT` de la fila en
`GIC_N_RELACION_DT_PUNTO`; los otros tres son `UPDATE ... WHERE hogarcodigo=X`.

**Consecuencia.** Un `UPDATE` sin fila **no es error** en Oracle. Invocados fuera de orden,
los pasos "pasan" sin dejar territorio: el hogar queda sin territorio y desaparece de los
reportes territoriales de Vivanto.

**Arreglo propuesto.** Un único procedure transaccional que reciba los 4 ids y haga
`MERGE`, en vez de 4 llamadas con orden implícito. **Esfuerzo: medio.**

## D5 — Dos convenciones para la geografía, una comentada al lado de la otra 🟠

**Evidencia.** `SP_CONSTANCIA` (body 3625-3626) lee `RXP_TEXTORESPUESTA = M.ID_MUNI_DEPTO`
(escalar). `SP_CONSTANCIA_GAVE` (body 4485-4509) parte ese mismo campo por `-` contra
`AP_GEOGRAFIA` — y **deja las dos líneas de la convención vieja comentadas justo al lado**
(body 4510-4511). Dos lecturas incompatibles del mismo campo, conviviendo en el mismo
paquete.

**Qué dijo el dato (medido en prod, 28-jul):** de 28.157 respuestas geográficas reales,
**el 100 % usa la convención escalar** y ninguna el formato compuesto.

**Consecuencia.** Cualquiera que lea `SP_CONSTANCIA_GAVE` para saber qué escribir, escribe
mal. Nos pasó: casi implementamos el formato compuesto.

**Arreglo propuesto.** Decidir cuál es la convención vigente, borrar el código muerto y
dejarlo documentado en la propia base. **Esfuerzo: bajo** (la decisión es de negocio).

## D6 — Ids duplicados de catálogo 🟠

**Evidencia.** La pregunta 30 tiene **4 ids** con el texto `Cédula de ciudadanía /
Contraseña`: 93 (29.338 usos), **3854 (8.620 usos)**, 3852 (19), 3853 (15). El manual
declara la opción **una sola vez**. El 3854 comparte texto y encuestadores con el 93 y
convive con él desde 2020.

**Consecuencia.** Los reportes que agrupan por `RES_IDRESPUESTA` **parten en dos** la misma
opción. Cualquier estadística de tipo de documento está sesgada hoy.

**Arreglo propuesto.** Unificar a un id canónico y migrar el histórico. **Esfuerzo: medio**
(toca datos existentes; requiere decisión de negocio y respaldo previo).

## D7 — SQL almacenado en una tabla 🟠

**Evidencia.** `SP_CARGAUTOCOMPLETAR` (body 2311-2326) ejecuta el texto SQL guardado en
`GIC_N_CONFIGAUTO.CONSULTA`.

**Consecuencia.** Es opaco al análisis estático: no aparece en `ALL_DEPENDENCIES`, no se
puede auditar qué toca, y un cambio de fila cambia el comportamiento del sistema sin pasar
por ningún despliegue. También es superficie de inyección.

**Arreglo propuesto.** Reemplazar por consultas parametrizadas en código.
**Esfuerzo: medio.** *(Nota: no está en nuestra ruta de escritura — no nos afecta hoy.)*

## D8 — `FN_VALOR_DIVIPOLA` enmascara sus fallos 🟠

**Evidencia.**
```sql
EXCEPTION WHEN OTHERS THEN RETURN vcCodigo;
```
Si no encuentra el código, **devuelve el código crudo como si fuera el nombre**.

**Consecuencia.** Un reporte muestra `05001` donde debería decir *Medellín*, y nadie
distingue "no existe" de "se llama así". **Arreglo: bajo** (devolver NULL y que el
llamador decida).

## D9 — `GIC_N_RESPUESTASENCUESTA` no guarda la pregunta 🟠

**Evidencia.** Sus columnas son `RXP_IDRESPUESTAXPERSONA, HOG_CODIGO, PER_IDPERSONA,
RES_IDRESPUESTA, RXP_TIPOPREGUNTA, USU_USUARIOCREACION, USU_FECHACREACION,
INS_IDINSTRUMENTO, RXP_TEXTORESPUESTA`. **No hay `PRE_IDPREGUNTA`.**

**Consecuencia.** La pregunta se deduce navegando `RES_IDRESPUESTA → GIC_N_RESPUESTAS`.
Combinado con D6 (ids duplicados), reconstruir "qué se preguntó" es frágil. Y si una
opción se re-asigna de pregunta, el histórico cambia de significado retroactivamente.

**Arreglo propuesto.** Añadir `PRE_IDPREGUNTA` (desnormalización deliberada) y poblarla
para el histórico. **Esfuerzo: medio.**

## D10 — Objetos INVALID 🟡

**Evidencia.** En la réplica local: **67 objetos INVALID**, entre ellos
`GIC_ADMIN_CRUCES`, `GIC_N_REPORTES`, varios `CURSOR_HOGARES_*` y `FN_VALOR_DIVIPOLA`.
Los de nuestra ruta (`GIC_CATEGORIZACION`, `GIC_N_CARACTERIZACION`) están **VALID**.

> ⚠️ Ese conteo es de la **réplica**, donde parte de los INVALID se explica por el dblink
> ausente. El conteo real de producción lo mide el veredicto de calidad de datos.

**Arreglo propuesto.** Recompilar y borrar lo que ya no se usa. **Esfuerzo: bajo-medio.**

## D11 — `PBANDERA=1` borra las respuestas previas 🟡

**Evidencia.** Con `PBANDERA=1`, el procedure dispara `SP_BORRADORESPUESTAS`: borra e
inserta la respuesta del par (hogar, pregunta).

**Nuestra decisión.** Lo usamos con 1 a propósito: en un hogar **nuevo** el borrado es
*no-op* y nos da idempotencia (re-correr no duplica). Está documentado, no es un riesgo
ciego. **Pero para un hogar existente sí es destructivo**, y el nombre `PBANDERA` no
comunica nada de eso.

**Arreglo propuesto.** Renombrar a algo como `P_REEMPLAZAR_RESPUESTA` y documentarlo.
**Esfuerzo: bajo.**

## D12 — Nombres de catálogo divergentes 🟡

**Evidencia.** Departamentos: SICAV *"Archipiélago de San Andrés**,** Providencia y Santa
Catalina"* vs Oracle sin la coma — era la **única** divergencia de los 33, y tumbaba los 2
puntos de atención de San Andrés. Municipios: 1.012 de 1.058 nombres cruzan directo; el
resto son localidades de Bogotá y corregimientos departamentales que la DIVIPOLA del DANE
no lista como municipios. Puntos de atención: **227 nombres distintos para 266 ids**.

**Consecuencia.** El cruce entre sistemas es **por nombre** (los ids de Oracle son
surrogates, no DANE), así que cada divergencia tipográfica es un dato que se pierde.

**Arreglo propuesto.** Adoptar el código DANE como clave de intercambio en vez del nombre.
**Esfuerzo: medio**, y es el que más deuda quita a futuro.

---

## Defectos que encontramos en SICAV (no en Oracle)

Cruzar el nivel de las preguntas de Oracle (`GE`/`IN`) contra el campo `nivel` de SICAV dio
**61/63** de coincidencia. Las 2 discrepancias son **nuestras**:

| Pregunta | SICAV dice | Debería | Evidencia |
|---|---|---|---|
| 8 — teléfono celular | HOGAR | PERSONA | manual 11-MU pág. 45 (A11): *"Se habilita para cada una de las personas del hogar"* — **cerrado con cita** |
| 35 — autorreconocimiento étnico | HOGAR | PERSONA | Oracle dice persona + pendiente funcional del 24-jun; el manual no lo declara literal en esa página — **evidencia más débil** |

Y el defecto que corrigió el Escalón 2: SICAV escribía el código DANE **con** cero a la
izquierda donde Oracle espera **sin** (ver `plan_escalon_2.md` §2). Ya corregido.

---

## Cómo usar este registro

1. **Durante la migración: no tocar nada de esto.** Todos los defectos 🔴 están rodeados en
   nuestro código y verificados por test. Cambiar la base ahora invalidaría lo verificado.
2. **Al cerrar la migración**, atacar en este orden: D2 y D3 (esfuerzo bajo, riesgo alto),
   D5 y D8 (limpieza de ambigüedad), D12 (quita deuda futura), D4 y D9 (cambios de
   estructura), D1 y D6 al final (rompen contrato / tocan histórico, exigen respaldo y
   coordinación).
3. **Cada arreglo necesita respaldo previo y ventana acordada.** Son datos de víctimas en
   producción.
