# Qué va a pasar en la BD de la UARIV cuando migremos

> **Para:** decidir la migración con el movimiento exacto sobre la mesa.
> **Fecha:** 2026-07-28 · **Objetivo:** migrar antes del lunes 2026-08-03.
> **Regla que gobierna el documento:** *no se toca lo que ya existe; solo se agrega.*
>
> Todo lo de aquí está **verificado leyendo el PL/SQL de producción**, no supuesto.
> Cada afirmación cita la línea del cuerpo del paquete.

---

## 1. La respuesta corta

Escribimos **7 tablas**, todas con **filas nuevas de hogares nuevos**. Ningún `UPDATE`
ni `DELETE` de la ruta puede alcanzar una fila que ya exista, por dos razones
independientes que se verifican abajo. **Nada de lo que hoy está en la base cambia.**

| # | Tabla | Qué le hacemos | ¿Toca lo existente? |
|---|---|---|---|
| 1 | `GIC_HOGAR` | 1 `INSERT` por hogar | No — código nuevo |
| 2 | `GIC_PERSONA` | 1 `INSERT` por miembro | No — id nuevo de secuencia |
| 3 | `GIC_MIEMBROS_HOGAR` | 1 `INSERT` por miembro | No |
| 4 | `GIC_N_RELACION_DT_PUNTO` | 1 `INSERT` + 3 `UPDATE` | No — todos `WHERE hogarcodigo = <el nuestro>` |
| 5 | `GIC_N_RESPUESTASENCUESTA` | 1 `INSERT` por respuesta | No |
| 6 | `GIC_N_VALIDADORESXPERSONA` | `INSERT` colateral | No |
| 7 | `GIC_N_PREGUNTASDERIVADAS` | `INSERT`/`UPDATE`/`DELETE` colateral | No — ver §4 (una salvedad) |

Las tablas 6 y 7 son **efectos colaterales de los procedures**, no algo que nosotros
pidamos. Aparecieron al hacer el cierre transitivo completo (18 subprogramas) y no
estaban en el inventario anterior, que solo listaba 5 tablas. Están aquí para que no
haya sorpresas.

---

## 2. El movimiento, paso a paso

Por cada hogar caracterizado en SICAV:

```
1. HOGAR       GIC_INSERT_HOGAR1        → INSERT GIC_HOGAR              (1 fila)
2. PERSONA     GIC_INSERT_PERSONAS      → INSERT GIC_PERSONA            (1 por miembro)
3. MIEMBRO     GIC_INSERT_MIEMBRO_HOGAR → INSERT GIC_MIEMBROS_HOGAR     (1 por miembro)
4. TERRITORIO  GIC_SP_OBDEPTOPORDT      → INSERT GIC_N_RELACION_DT_PUNTO (1 fila)
               + 3 procedures más       → UPDATE de esa misma fila
5. RESPUESTA   SP_SET_RESPUESTAS_...    → INSERT GIC_N_RESPUESTASENCUESTA (1 por respuesta)
                                        → INSERT GIC_N_VALIDADORESXPERSONA (si aplica)
                                        → toca GIC_N_PREGUNTASDERIVADAS (colateral)
```

**Volumen del piloto:** 1 hogar. Con 3 miembros y ~360 respuestas posibles, son del orden
de **1 + 3 + 3 + 1 + n** filas. Sobre una base de 1.102.878 hogares y 7,76 M de personas.

**Todo pasa por los procedures oficiales `GIC_*`.** Cero `INSERT` directo a tablas: esa es
la decisión de arquitectura del proyecto y se mantiene.

---

## 3. Por qué NO puede tocar lo existente — las dos garantías

### Garantía 1 — el hogar es nuevo, siempre

El código del hogar **lo genera Oracle**, no nosotros (`FN_GET_CODIGOENCUESTA`). Cada
corrida produce un `HOG_CODIGO` que no existía (el del Escalón 1 fue `999999-K34C6`).
Como **todos** los `UPDATE` y `DELETE` de la ruta filtran por `HOG_CODIGO`, ninguno puede
alcanzar una fila de otro hogar. Verificado cláusula por cláusula:

| Operación | Cláusula real (línea del body) |
|---|---|
| `UPDATE GIC_N_RELACION_DT_PUNTO` ×3 | `WHERE hogarcodigo = <hogar>` |
| `DELETE GIC_N_RESPUESTASENCUESTA` | `WHERE HOG_CODIGO=… AND PER_IDPERSONA=… AND INS_IDINSTRUMENTO=… AND RES_IDRESPUESTA=…` (1785-1789) |
| `DELETE GIC_N_VALIDADORESXPERSONA` | `WHERE hog_codigo=… AND val_idvalidador=… AND per_idpersona=…` (2455) |
| `DELETE GIC_N_VALIDADORESXPERSONA` (etnia) | `WHERE HOG_CODIGO=… AND VAL_IDVALIDADOR IN (…) AND COMODIN=…` (3398, 3402, 3405) |
| `DELETE GIC_N_PREGUNTASDERIVADAS` | `WHERE hog_codigo=… AND pre_idpreguntapadre=… AND per_idpersona=… AND ins_idinstrumento=…` (3032, 3047) |

### Garantía 2 — el único borrado peligroso queda desarmado

`PBANDERA=1` dispara `SP_BORRADORESPUESTAS`, que borra las respuestas previas del par
(hogar, persona, pregunta). En un hogar nuevo no hay nada que borrar, pero además hay un
segundo cerrojo: ese procedure recibe la pregunta a borrar **desde
`PPER_IDPREGUNTAPADRE`** (línea 36: `pID_RESPUESTA => pper_idPreguntaPadre`), y nosotros
lo mandamos **NULL**. Su cursor compara `PR.PRE_IDPREGUNTA = pId_Respuesta` (1782): contra
`NULL` no devuelve ninguna fila. **El `DELETE` no llega a ejecutarse.**

> Detalle para el registro de defectos: ese parámetro se llama `pId_Respuesta` pero se
> compara contra un `PRE_IDPREGUNTA`. Es el mismo patrón del `Id_DT` que espera un id de
> departamento — otro nombre que miente.

### Lo que NO llamamos

Los borrados masivos que existen en el paquete (`SP_ELIMINAR_ENCUESTA`, `CERRAR_ENCUESTA`,
`SP_ACTUALIZAR_ESTADO_ENCUESTA`) sí borran hogares enteros y mueven filas a las tablas
`_HIS`/`_C`. **No están en nuestro cierre transitivo: no los invocamos.** Varios están
además comentados en el propio fuente.

---

## 4. La única salvedad honesta

Dentro de `SP_SET_PREGUNTAS_DERIVADAS` hay un borrado que **no filtra por hogar**:

```sql
-- body 198
DELETE FROM GIC_N_PREGUNTASDERIVADAS WHERE PER_IDPERSONA = pPER_IDPERSONA AND GUARDADO = 0;
```

Borra las preguntas derivadas *no guardadas* de esa **persona**, en cualquier hogar.

**Por qué no nos afecta hoy:** nuestras personas son nuevas — su `PER_IDPERSONA` sale de
la secuencia al insertarlas en el paso 2, así que no tienen filas previas en ninguna
parte. El borrado es *no-op*.

**Cuándo sí importaría:** el día que escribamos sobre una persona **que ya existe** en
Oracle (por ejemplo, si en vez de crear la persona la reutilizáramos por documento). Ahí
este `DELETE` sí alcanzaría datos de otros hogares. **Mientras la migración cree personas
nuevas, no hay riesgo.** Queda anotado para cuando se plantee la deduplicación.

---

## 5. Trazabilidad — cómo se distingue lo nuestro

Todo lo que escriba SICAV queda identificable y, por tanto, reversible:

- `GIC_HOGAR.USU_IDUSUARIO = 999999` — usuario de servicio sintético, sin PII. **Ningún
  otro sistema lo usa.** Un `WHERE USU_IDUSUARIO = 999999` aísla el 100 % de lo que
  escribamos.
- `USU_USUARIOCREACION` = el código del encuestador real, para auditoría funcional.
- Ledger propio en PostgreSQL (`RegistroEscrituraOracle`) con cada paso, su bloque PL/SQL,
  su resultado y su verificación por `SELECT`.

**Reversión:** si algo sale mal, las filas del piloto se identifican por `HOG_CODIGO` y se
pueden borrar con el mismo criterio con que se escribieron. Más el respaldo previo.

---

## 6. Lo que hay que cerrar antes — y es lo único que falta

| | Pendiente | Estado |
|---|---|---|
| 🔴 | **75 `id_preg` apuntan a la pregunta equivocada** (41 en territorial_v8) | ABIERTO — ver [`bloqueante_id_preg_subcampos.md`](bloqueante_id_preg_subcampos.md) |
| 🟠 | Respaldo de `30.0.1.9` confirmado antes del piloto | pendiente |
| 🟠 | Clave de `RNIENTREVISTA` sin rotar | **aplazado por decisión de Javier** (28-jul): la clave está repartida en la Unidad; rotarla se trata aparte |
| ✅ | 3a.3 tipos de documento PE/NES | cerrado |
| ✅ | 3a.11 catálogo de puntos de atención | cerrado |
| ✅ | Ruta geográfica verificada (Escalón 2) | cerrado |

**El bloqueante 🔴 es el que manda.** Si escribimos hoy un hogar con observaciones de
capítulo o sub-campos de cursos, esas respuestas se guardan en preguntas ajenas de la base
de la UARIV — y el procedure no avisa. Eso sí sería "afectar lo que hay".

---

## 7. Plan hasta el lunes

| Día | Qué |
|---|---|
| **mar 28** | ✅ Escalón 2, 3a.11, 3a.3, veredicto de la BD, este documento |
| **mié 29** | Corregir los 41 `id_preg` de territorial_v8 (el perfil del piloto) + comando `auditar_id_preg` en CI |
| **jue 30** | Corregir telefonico_v8 (16) y empezar rural_etnico_v1 (43) |
| **vie 31** | Respaldo confirmado → **piloto de 1 hogar en producción** → verificación por `SELECT` |
| **sáb–dom** | Margen para reproceso y para el disparador automático (hoy la escritura es manual) |

> **Nota sobre el alcance del lunes.** Lo que estará listo es **escribir hogares a Oracle
> de forma verificada**. Lo que NO estará, salvo que se priorice: el **disparador
> automático** (hoy no hay `tasks.py` ni `signals.py`; Celery corre sin tareas y la
> escritura se lanza a mano, un hogar por vez) y la **lectura del padrón real**
> (`OracleVictimaRepository` sigue siendo un `TODO`: la APK busca contra el mock).
> Se puede migrar el lunes operando el comando a mano; automatizarlo es el paso siguiente.
