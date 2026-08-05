# Capacidad de disco del servidor SICAV — análisis con el universo de víctimas cargado

**5 de agosto de 2026** · servidor `30.0.1.109` (compartido) · medido con la carga
del universo en curso, no estimado en frío.

La pregunta que responde: **con el universo de 12,5 M dentro, ¿cómo queda la base,
cuánto margen de maniobra tenemos, y hace falta más disco?**

---

## 1. De dónde partimos (medido el 5-ago 21:30 UTC)

### El disco

```
/dev/root   61 GB total · 43 GB usados · 19 GB libres · 70 %
inodos: 7 % (no son problema)
```

De los 43 GB usados, **23 GB son la base de datos** y ~20 GB son el sistema, las
imágenes de Docker y los otros servicios que conviven en la máquina
(`sidi-api`, `catalogo-si`, `uariv-auth`, `nginx-proxy-manager`).

### La base, tabla por tabla

| Tabla | Filas | Heap | Índices | Total |
|---|---:|---:|---:|---:|
| `victimas_victima` (padrón operativo) | 5.916.880 | 9.199 MB | **5.915 MB** | **15 GB** |
| `victimas_personauniverso` (universo, **cargando**) | 4.507.634 | 3.531 MB | 3.657 MB | 7.188 MB |
| `victimas_colisiondocumento` | 768.096 | 217 MB | 360 MB | 577 MB |
| `sincronizacion_caracterizacionlegacy` | 222.094 | 39 MB | 73 MB | 113 MB |
| `victimas_descarteuniverso` | 169.606 | 28 MB | 21 MB | 49 MB |
| todo lo demás (formulario, auth, auditoría…) | — | — | — | ~15 MB |

WAL: 3.312 MB (`max_wal_size` = 1.024 MB — está inflado por la carga masiva y se
recicla solo cuando termine).

**Dato que conviene mirar dos veces:** en las dos tablas grandes, los índices pesan
casi tanto como los datos. En `victimas_victima` son 5,9 GB de índices para 9,2 GB
de datos.

---

## 2. Cómo queda cuando termine la carga

Con 4.507.634 filas cargadas, el costo real es **1,633 KB por fila** (0,802 de
datos + 0,831 de índices). El corte trae 12.496.965 filas y se descarta el 3,9 %
sin documento usable ⇒ **~12,01 M filas finales**.

| | Heap | Índices | Total |
|---|---:|---:|---:|
| Universo completo | 9,19 GB | 9,52 GB | **18,7 GB** |

Faltan por escribir **11,7 GB**, así que al terminar la fase 1 quedan **~7,3 GB
libres** en el disco.

### 🔴 Y ahí la fase 3 no entra

El enlace con el padrón (`_enlazar_con_padron`) actualiza `victima_id` en cada fila
que cruce. Estimando ~5 M cruces (el padrón tiene 5,92 M y el 76 % cruzó en la
carga anterior), y como `victima_id` está indexado, Postgres **no puede hacer HOT
update**: reescribe la fila y toca todos los índices.

```
5 M filas × 1,633 KB = 8,2 GB de espacio muerto   vs   7,3 GB libres
```

**Falta ~1 GB, y eso es antes de contar el WAL.** No es un margen que se pueda
apostar en un disco compartido.

---

## 3. La grasa: 5,8 GB de índices que no sirven

Medido con `pg_stat_user_indexes` sobre la tabla a medio cargar — la columna de
usos es real, no teórica:

| Índice | Hoy | Usos | Proyectado a 12 M | Veredicto |
|---|---:|---:|---:|---|
| `..._numero_documento_hash_..._like` | 540 MB | **0** | 1.439 MB | 🔴 `varchar_pattern_ops` sobre un hash hexadecimal. Django lo crea solo para `LIKE 'abc%'`, que sobre un hash no tiene sentido |
| `..._hash_si_..._like` | 539 MB | **0** | 1.436 MB | 🔴 idem |
| `..._numero_documento_hash` | 540 MB | **0** | 1.439 MB | 🔴 es el hash **con tipo**; el cruce del universo va por el hash **sin tipo** |
| `..._numero_documento_hash_sin__...` | 539 MB | **0** | 1.436 MB | 🔴 redundante: el compuesto `(hash_sin_tipo, corte)` ya lo cubre como prefijo izquierdo |
| `..._corte` + `..._corte_like` | 60 MB | **0** / 6 | 160 MB | 🔴 la tabla tiene **un solo valor** de corte |
| | | | **5.910 MB** | **≈ 5,8 GB recuperables** |

Los que sí trabajan y se quedan: el compuesto del cruce (698 MB, es *el* índice de
la búsqueda), la unicidad por corte (332 MB, 4,6 M usos — la usa la propia carga) y
la PK (171 MB, 4,6 M usos).

Podarlos tiene **dos efectos**, y el segundo importa más que el primero:

1. El universo pasa de 18,7 GB a **~13 GB**.
2. Cada fila que la fase 3 reescriba cuesta **1,12 KB en vez de 1,633** (hay menos
   índices que actualizar) ⇒ el enlace baja de 8,2 GB a **5,6 GB**, con 13,1 GB
   disponibles. Entra con holgura.

---

## 4. Los tres escenarios

| Escenario | Universo | BD total | Disco usado (de 61) | Libre | Veredicto |
|---|---:|---:|---:|---:|---|
| **A.** Terminar como está + fase 3 | 18,7 GB | ~35 GB | ~63 GB | **−2 GB** | 🔴 **se llena a mitad del enlace** |
| **B.** Podar índices + fase 3 por lotes | 13,0 GB | ~29 GB | ~49 GB | 12 GB (80 %) | 🟡 **operable**, sin margen para mantenimiento |
| **B+.** B + limpieza (imágenes huérfanas, logs) | 13,0 GB | ~29 GB | ~44 GB | 17 GB (73 %) | 🟢 lo mejor que se puede hoy |
| **C.** Dos cortes conviviendo (agosto sin borrar julio) | 26,0 GB | ~42 GB | ~62 GB | **−1 GB** | 🔴 **no cabe** |

El escenario C no es hipotético: el modelo **está diseñado** para que dos cortes
convivan mientras se valida el nuevo (`UniqueConstraint(corte, cons_persona)`).
Con este disco, esa validación **no se puede hacer como está diseñada**.

---

## 5. ¿Hay movilidad? Sí, ~11 GB — y se agota rápido

| Palanca | Libera | Riesgo | Cuándo |
|---|---:|---|---|
| Imágenes Docker huérfanas (6 × 772 MB de builds viejos del backend) | **~4,6 GB** | ninguno | ya |
| Podar los 5 índices muertos | **~5,8 GB** | ninguno (0 usos medidos) | en la ventana entre fase 1 y fase 2 |
| `journalctl --vacuum` sobre `/var/log` (641 MB) | ~0,4 GB | ninguno | ya |
| WAL, al terminar la carga | ~2 GB | se recupera solo | automático |
| Borrar el corte anterior al validar el nuevo | 13 GB por corte | **decisión de negocio** | política a definir |
| `VACUUM FULL` de `victimas_victima` | ¿? | **hoy imposible: necesita 15 GB libres para correr** | requiere más disco |

Esa última fila es la que mejor describe la situación: **hoy no hay espacio ni para
hacerle mantenimiento a la tabla más grande.** Un `VACUUM FULL` o un `REINDEX`
necesitan reescribir la tabla al lado antes de soltar la vieja.

---

## 6. Respuesta: ¿necesitamos más disco?

**Para terminar esta carga, no** — con la poda y la limpieza alcanza, y el
escenario B+ deja el disco al 73 %.

**Para operar mes a mes, sí.** Tres razones concretas, en orden de peso:

1. **El corte es mensual.** Cada uno son 13 GB y el diseño previsto pide tener dos a
   la vez mientras se valida el nuevo. Hoy no caben dos.
2. **No hay espacio de mantenimiento.** `VACUUM FULL`/`REINDEX` de una tabla de 15 GB
   piden 15 GB libres. Sin eso, el bloat que dejen los enlaces mensuales no se puede
   recuperar nunca.
3. **El disco es compartido.** Cualquier crecimiento de `sidi`, `catalogo-si` o
   `uariv-auth` nos come el margen sin avisar, y al revés: si nos pasamos, **el
   Postgres que se detiene también es el de ellos**.

### Lo que hay que pedir

| Concepto | GB |
|---|---:|
| BD con dos cortes conviviendo | 42 |
| Sistema + Docker + otros servicios | 20 |
| Espacio de mantenimiento (reescribir la tabla mayor) | 15 |
| Subtotal | 77 |
| Margen operativo 25 % | 19 |
| **Total recomendado** | **~96 GB** |

**Pedido concreto: llevar el volumen de 61 GB a 120 GB.** Es el número redondo
inmediatamente superior, deja crecer el padrón operativo (que sube con cada
caracterización) y no obliga a volver a pedir en seis meses.

Si OTI solo pudiera dar un incremento parcial, **el mínimo viable son 100 GB**; por
debajo de eso volvemos a quedar sin espacio de mantenimiento.

---

## 7. Decisión que no es técnica

**¿Se conserva el corte anterior mientras se valida el nuevo?**

- **Sí** (lo previsto en el diseño): hacen falta 13 GB extra y **exige el disco nuevo**.
- **No** (retención de un solo corte): cabe en el disco actual, pero entonces la
  validación del corte nuevo hay que hacerla **antes** de cargarlo —contra Oracle,
  no contra Postgres— porque al cargarlo ya se habrá borrado el anterior y no habrá
  contra qué comparar.

No es una decisión de infraestructura: define cómo se valida el dato que ve el
encuestador cada mes.
