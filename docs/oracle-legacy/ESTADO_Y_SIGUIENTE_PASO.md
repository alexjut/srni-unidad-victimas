# Oracle legacy → SICAV — Estado y siguiente paso

> **Traspaso de sesión.** Qué hicimos, dónde está todo, qué falta y **con qué empezar
> la próxima vez**. **Fecha de corte: 2026-08-14** — lo más reciente arriba
> (§0-duodecies: la excepción de vigencia se mudó al front).
> **Worktree:** `feat/oracle-legacy-writer` en `D:\desarrollo\uv-oracle-writer`.
> Lo hecho contra Oracle fue **solo lectura** (local + prod), excepto un único `DROP`
> autorizado de una master table huérfana y el piloto de escritura del 28-jul
> (§0-bis). Sobre **PostgreSQL de producción sí se escribe**: es donde vive el padrón
> y el universo. El prompt para retomar está en §5 y quedó viejo — para el frente del
> universo, arrancar por §0-undecies.

---

## 0-duodecies. 2026-08-14 — **LA EXCEPCIÓN DE VIGENCIA SE MUDÓ AL FRONT**

Cambio pedido por la operación: **los caracterizadores no deben tener el
documento de soporte**. El fallo, la tutela o el auto llegan por canal
institucional al nivel central, no a quien está frente a la víctima.

Hasta el 13-ago la APK le pedía al encuestador elegir la ruta y **tomar una foto
del soporte**. O sea que quien ejecutaba el salto del control era el mismo que lo
autorizaba, y encima con un documento que no tiene.

Ahora la excepción se **autoriza antes**, desde la plataforma web, y el celular
solo la consume. Todo está en
[`excepcion_vigencia_desde_el_front.md`](../operacion/excepcion_vigencia_desde_el_front.md)
—incluido el contrato de la API para Brando—. Lo que hay que saber acá:

| | |
|---|---|
| Endpoint nuevo | `POST/GET /api/habilitaciones/` + `{id}/anular/` |
| Quién autoriza | perfil con `puede_autorizar_excepciones` — COORDINADOR, SUPERVISOR, ADMINISTRADOR |
| Qué exige | ruta + **radicado** + motivo. El archivo es opcional |
| Cómo llega a campo | en la precarga de la jornada → **funciona sin señal** (schema móvil v12) |
| Duración | de un solo uso: se consume al finalizar la encuesta |
| La vía vieja | `POST /api/encuestas/{id}/excepcion-vigencia/` responde **410** con la explicación |
| Pruebas | 883 backend + 115 móvil, todas en verde |

### Tres cosas para no olvidar

1. 🔴 **Falta la UI web (Brando).** El backend está completo y probado, pero
   hasta que exista la pantalla **nadie puede autorizar nada** y las personas con
   ficha vigente quedan bloqueadas sin salida. Es lo que desbloquea el frente.

2. 🔴 **Hay 1 coordinador, 1 supervisor y 1 admin para 1.158 encuestadoras.**
   Antes de arrancar en campo hay que decidir cuántas cuentas con permiso de
   autorizar se necesitan y quién las tiene. Es definición de operación, no
   pendiente técnico.

3. **La ruta de excepción nunca funcionó en producción, ni la vieja.** El
   endpoint del 6-ago escribía la auditoría con `LogAcceso.objects.create(...,
   ip=...)` y ese campo se llama `ip_origen` —`detalle` además es `JSONField`—,
   así que toda llamada moría en 500 antes de responder. No se detectó porque
   ninguna encuestadora ha entrado nunca al sistema. Vale como recordatorio de
   que **lo que no se ejecutó no está probado**, por más test unitario que tenga
   alrededor.

⚠️ **La APK en campo (v1.1.0) todavía tiene el botón de adjuntar soporte.** Hasta
que se despliegue una versión nueva responde 410 con el texto que manda a
coordinación —no como error de red—. Falta decidir cuándo se hace ese build.

---

## 0-undecies. 2026-08-11/12 — **EL PADRÓN DEJÓ DE AFIRMAR LO QUE NO SABE**

Arrancó como una verificación de rutina —68 cédulas reportadas desde el territorio— y
terminó destapando que el estado RUV de 5,9 M de personas venía del registro de otra.
Lo del 11 está documentado aparte; acá va el cierre y **el estado con el que se
retoma**.

### Lo que ya tiene su propio documento

| Qué | Dónde |
|---|---|
| 🔴 El join roto (`CONS_PERONA` es un contador de filas, no un id de persona) | [`join_caracterizacion_roto.md`](join_caracterizacion_roto.md) |
| Traslado de la base a `/datos` (disco de 256 GB, 12 min de corte) | [`runbook_traslado_bd_a_datos.md`](../infraestructura/runbook_traslado_bd_a_datos.md) |
| Usuarios y perfiles — el login es `codigo_usuario`, no el nombre | [`usuarios_y_perfiles.md`](../operacion/usuarios_y_perfiles.md) |

El bloom del universo quedó desplegado y verificado (68/68 cédulas reconocidas, cero
invisibles): la APK offline pasó de conocer 5.000 personas a 12.677.172, y el padrón
bajó de 896 MiB a 318,7 MiB. APK v1.1.0 / versionCode 54.

⚠️ El volumen viejo `caracterizacion_cz_pgdata` **sigue intacto a propósito** — es el
rollback del traslado. No borrarlo hasta ~14 días y un reinicio del servidor.

### La 0021 corrió entera: 5.926.005 en `NO_VERIFICADO`

```
estado_ruv     estado_ruv_fuente    count
NO_VERIFICADO  SIN_VERIFICAR      5.926.005     ← todas
INCLUIDO sin verificar:                    0
total de filas:                    5.926.005     ← intacto
tabla 9.199 MB · n_dead_tup 0 · VACUUM final 12-ago 05:04:13 · /datos 207 GB libres
```

Terminó el **12-ago a las 05:04**, en 8 lotes, y la tabla pesa exactamente lo mismo que
antes de empezar: el loteo con `VACUUM` cada 3 no dejó bloat. Se cortó dos veces sin
daño (200.001 y 2.200.001 filas), así que **el diseño retomable está probado en
producción**, no solo escrito.

### La lección cara: un `EXPLAIN` no mide lo que cuesta escribir

A mitad de camino se cortó la migración para cambiar el `UPDATE ... WHERE id IN (...)`
—que hacía 200.000 búsquedas aleatorias por UUID— por uno con `ctid`. El plan prometía
20×:

```
por id (UUID)   cost 1.358.918   Nested Loop → Index Scan on ..._pkey
por ctid        cost    65.517   Nested Loop → Tid Scan
```

**Y no sirvió de nada.** Medido de punta a punta:

```
por id (UUID)   10.870 filas/min   (2.000.000 en 3h04)
por ctid        10.325 filas/min   (3.726.004 en 6h01)
```

Un 5% por debajo, o sea lo mismo. El costo de un plan **no incluye el heap, ni el WAL,
ni las entradas de índice**, y ahí estaba el cuello: `victimas_victima` tiene **26
índices (5,9 GB)** y `estado_ruv` es uno de los indexados, así que ninguna fila se
puede actualizar en modo HOT y cada una inserta una entrada en los 26 — ~97 millones
de escrituras de índice que no evita ningún `WHERE`. Medido en vivo: **260 MB de WAL
por minuto**. Cortar y relanzar costó ~50 min de reloj **en pérdida**.

Queda anotado en el docstring de la migración. **Para futuras escrituras masivas sobre
el padrón, el techo lo ponen los índices, no la consulta** — y buena parte de esos 26
son de baja cardinalidad sobre 5,9 M filas (`genero`, `pertenencia_etnica`,
`estado_valoracion`, `discapacidad`, `fuente_origen`), cada `varchar` con su gemelo
`_like`. Revisarlos es una tarea aparte, con calma, nunca en medio de una migración.

### 🔴 Con qué se retoma: la decisión, no el padrón

El padrón ya no miente, pero **tampoco informa**: `FLAG_EN_RUV` saldría `false` para
todos. Regenerarlo ahora sería hacer el trabajo caro dos veces, y ya se midió lo que
cuesta escribir sobre esta tabla.

Lo que desbloquea todo es **la decisión pendiente de Javier: la fuente definitiva de
`estado_ruv`** —el universo del RUV o `RUV.TBESTADO_VAL`—, porque redefine quiénes son
esas 5,9 M. Ver [`decisiones_negocio_pendientes.md`](../gestion/decisiones_negocio_pendientes.md).
Decidido eso: regenerar el padrón, y después B2 en móvil (que offline reconozca a los
4,5 M con ficha, no solo su existencia).

---

## 0-decies. 2026-08-06 — **EL UNIVERSO ESTÁ CARGADO; LAS TRES FASES, UNA POR UNA**

Resumen: **12.009.492 personas cargadas**, duplicados resueltos y el enlace con el
padrón corriendo. Las tres fases funcionaron, pero **ninguna a la primera**: cada
una tuvo un problema de escala que solo aparece con 12 M de filas delante.

### Fase 1 — cerró sola, y el vigilante hizo su trabajo

```
leídas          : 12,496,965
cargadas        : 12,009,492
sin documento   :    487,473  (descartadas)
sin id de fuente:          0
```

12 h 51 min (16:23 del 5-ago → 05:14 del 6-ago). El vigilante detectó el fin de la
fase 1, mandó `SIGTERM` al PID 1546 y confirmó `procesos que quedan: 0`: **el UPDATE
de 12 M de filas nunca se ejecutó**.

Las dos cifras coinciden **exactamente** con lo medido en Oracle antes de cargar
(12.009.492 con documento usable, 487.473 sin él): no se perdió una fila por el
`ignore_conflicts`. Tabla: **13 GB** (heap 9.212 MB + índices 3.669 MB), o sea la
proyección con los índices podados y no los 18,7 GB del diseño original.

### Deploy del parche

`git archive` → build → `up --force-recreate` de los cuatro servicios → `migrate`
(`0016` aplicada, no-op como se esperaba) → `restart cz_nginx` → `/api/` **200**.

**No se usó `deploy-all.sh`**: su paso `40-cargar-datos.sh` recarga los 8
instrumentos con `cargar_perfil --reemplazar` (purga capítulos en cascada) y
reconstruye el frontend. Para un cambio de código Python, eso es riesgo gratis.

### Fase 2 — el doble `GROUP BY` (y el N+1 detrás)

Primer intento: **más de 45 minutos con el log mudo**. En `pg_stat_activity` estaba
la causa: un `DECLARE CURSOR` sobre el `GROUP BY`, o sea **la segunda pasada
completa** sobre 12 M. El método hacía tres cosas caras:

```python
total_grupos = repetidos.count()                  # GROUP BY sobre 12 M   (1)
for grupo in repetidos.iterator():                # GROUP BY sobre 12 M   (2)
    filas = list(base.filter(hash=grupo["hash"])) # una consulta POR GRUPO (60.438)
```

Se cortó **sin haber escrito nada** (acumula en memoria y escribe al final, en una
sola transacción: verificado, 0 marcadas). Arreglado con subconsulta + `groupby`
sobre un único recorrido ordenado, progreso cada 10.000 grupos y el UPDATE de
perdedoras por lotes de 10.000. **Segunda corrida: menos de 5 minutos.**

| | |
|---|---:|
| Documentos compartidos | 60.438 |
| Filas que pierden el desempate | 62.202 |
| Preferidas | **11.947.290** |
| **Grupos con ≠ 1 preferida** | **0** ← la invariante, medida sobre los 12 M |

### 🔴 Postgres tenía 64 MB de `/dev/shm`

El `VACUUM ANALYZE` de rutina falló:

```
ERROR: could not resize shared memory segment to 67145408 bytes: No space left on device
```

67145408 son **exactamente los 64 MB** que Docker da por defecto cuando el compose
no declara `shm_size`. **No era el disco** —había 15 GB libres— y el host ofrece
7,8 GB de shm. El mensaje engaña: dice "no space left on device" y manda a mirar la
partición equivocada.

Postgres usa esa memoria para las consultas **paralelas**, así que alcanzaba a
cualquier consulta grande, no solo al `VACUUM`. Arreglado en el compose
(`shm_size: 1gb`) junto con `stop_grace_period: 3m` — Docker da 10 s antes del
SIGKILL y el checkpoint de apagado de una base de 28 GB no cabe ahí.

Recrear `cz_postgres` se hizo con `CHECKPOINT` previo. El log confirma apagado
limpio (`database system was shut down`, no "was interrupted") y los datos quedaron
intactos: 11.947.290 preferidas · 5.926.004 víctimas.

### Fase 3 — el enlace no podía hacerse desde Python

Primer intento cancelado: en varios minutos no había enlazado ni el 0,05 %.

```
DECLARE ... CURSOR WITH HOLD FOR SELECT "victimas_personauniverso"."id", ...
temp_files: 1840   temp_bytes: 24 GB
```

Tres costos, y el tercero lo hacía inviable: un cursor que **materializa 11,9 M
filas antes de entregar la primera**; trae las 20 columnas necesitando dos; y
`numero_documento` más los cuatro nombres son `EncryptedField`, así que instanciar
cada objeto **descifra cinco campos** — 11,9 millones de veces, para escribir un id.

Ahora el cruce ocurre **dentro de la base**: `UPDATE … FROM victimas_victima` con
`NOT EXISTS` (que es literalmente "solo si es la única con ese documento"),
troceado en 16 lotes por el primer carácter del hash, con `>=`/`<` y no `LIKE`
—el `LIKE` querría el `varchar_pattern_ops` que podamos ayer—. Cada lote commitea
y loguea.

**En curso al momento de escribir esto:**

```
Enlazando con el padrón operativo (11,941,782 sin enlazar)
  [0] enlazadas   178,519 · ambiguas   60,419
  [1] enlazadas   357,418 · ambiguas  120,445
```

~6,5 min por lote ⇒ ETA ~1 h 45. Proyección: **~2,9 M enlazadas y ~960 K
ambiguas** — una de cada tres que cruza resuelve a más de una `Victima` y por
diseño no se enlaza a ninguna (coherente con las 768.096 filas de
`victimas_colisiondocumento`). Quedan registradas como `ENLACE_AMBIGUO`.

Vigilando mientras corre: guardián de disco a 5 GB (`/tmp/vigilante_disco.log`) y
un `VACUUM` en paralelo, porque el autovacuum no se dispara hasta 2,4 M de tuplas
muertas y cada lote costaba ~0,5 GB.

### Lo aprendido, que vale más que las cifras

1. **Todo lo que traiga 12 M de filas a Python es inviable**, y con PII cifrada lo
   es dos veces. Las tres fases fallaron por lo mismo.
2. **Un proceso sin log de progreso es indistinguible de uno colgado.** Costó 40
   minutos de espera antes de mirar `pg_stat_activity`.
3. **Cortar es barato si la escritura es al final o por lote**; las tres corridas
   canceladas no dejaron un solo dato a medias.

### 🌅 Siguiente paso

1. Esperar el cierre de los 16 lotes y verificar enlazadas + ambiguas.
2. `VACUUM ANALYZE` y medir el disco.
3. Con eso cierra el paso 2 del ADR. Quedan los pasos 3 a 5:
   **derivar el subconjunto territorial** desde el servidor, `NO_VERIFICABLE` en el
   cliente móvil y la reconsulta automática al recuperar conexión.
4. Aparte, y sin relación con el código: el escalamiento de disco a Oscar
   (`docs/gestion/correo_oscar_espacio_disco_urgente.md`) sigue pendiente de envío.

---

## 0-novies. 2026-08-05 — **EL UNIVERSO SE ESTÁ CARGANDO, Y LA FASE 2 NO CABE EN EL DISCO**

La carga del universo (12,5 M) arrancó a las **16:23 UTC** dentro de `cz_backend`:

```
docker exec cz_backend python manage.py cargar_universo_victimas --confirmar --lote 5000
log: /tmp/carga_universo_20260805_1623.log     (sobrevive a la VPN)
```

Medido a las 20:11 UTC, con 3 h 47 min de corrida:

| | |
|---|---|
| Corte | `TEMP_UNIV_VICT_PER_MI010726ALL` (julio, 35 días) — el de agosto **no existe**; el fallback avisó y funcionó |
| Avance | 4.300.000 leídas · 4.132.190 cargadas de **12.496.965** (34 %) |
| Ritmo | ~1,13 M/h ⇒ fin de la fase 1 hacia las **03:20 UTC del 6-ago** |
| Descartes | 164.313 `SIN_DOCUMENTO` (3,9 %, en línea con los 487.473 proyectados) |

### 🔴 El hallazgo: el reset de la fase 2 pedía ~19 GB que no hay

`victimas_personauniverso` va a **1,58 KB por fila** (heap 3.212 MB + índices
3.323 MB sobre 4,15 M filas, **12 índices**). Proyectada a 12 M: **~19 GB**, y el
disco del servidor tiene **19 GB libres de 61**, así que al terminar la fase 1
quedan ~6 GB.

Y la fase 2 empezaba con un `UPDATE` sobre **las 12 M de filas**
(`es_preferida=True`). Como `es_preferida` está indexada, Postgres no puede hacer
HOT update: reescribe el heap completo **y** los 12 índices ⇒ otros ~19 GB, más
el WAL de una transacción `atomic()` que no se recicla hasta el commit.

**No era solo nuestro problema:** ese disco es compartido con `sidi-api`,
`catalogo-si`, `uariv-auth` y el `nginx-proxy-manager`. Un Postgres sin espacio se
detiene y se lleva servicios de otros equipos por delante.

### Lo que se hizo (5-ago, tarde)

1. **Parche** — el reset se acota a `filter(corte=corte, es_preferida=False)`. El
   resultado es idéntico (las que ya están en `True` no cambian) y en la primera
   corrida toca **0 filas**, porque el default del modelo ya es `True`. La fase 2
   pasa a mover las ~55.100 perdedoras, no 12 M.
   Con test que **falla** si alguien le quita el filtro.
2. **Flag `--sin-enlace`** — la fase 3 (`_enlazar_con_padron`) reescribe una fila
   por cada cruce con el padrón de 5,9 M: millones más. Con el disco así, se corre
   aparte y midiendo entre fases.
3. **Vigilante** en el servidor (`/tmp/vigilante_universo.sh`, lanzado con
   `setsid nohup`, log en `/tmp/vigilante_universo.log`): detecta el fin de la
   fase 1 en el log y **mata el proceso antes del UPDATE**. Corta también si el
   disco baja de 4 GB. Los dos patrones de corte están probados contra el log real.

> **La ventana es cómoda.** Entre el fin de la carga y el primer UPDATE hay varios
> minutos de solo lectura: el `count` de verificación, el `GROUP BY` sobre 12 M y
> el bucle de ~55 K grupos. El polling es de 20 s.

### Poda de índices — aplicada EN CALIENTE a las 21:44 UTC

No se esperó a la ventana: la carga se había degradado a la mitad (572.580 filas/h
contra 1,14 M/h al arrancar, con el backend en `LWLock` sobre el `INSERT`) y la
causa era la misma que la del espacio — **cada fila mantenía 12 índices, 6 de ellos
sin un solo uso**.

Los 6 `DROP INDEX` fueron en **una sola transacción** con `lock_timeout`. Con 5 s
abortaron los seis: `bulk_create` sostiene una transacción de 5.000 filas que
duraba ~30 s. Con 90 s entró a la primera, en 78 segundos totales.

| | Antes | Después |
|---|---:|---:|
| Índices | 12 | **6** |
| Disco libre | 19 GB | **21 GB** |
| Ritmo | 572.580 filas/h | **772.000 filas/h** (+35 %) |
| Universo proyectado | 18,7 GB | **13,1 GB** |
| Fase 3 (enlace) | 8,2 GB — **no cabía** | 5,5 GB — **cabe con 7,5 GB de margen** |

La migración `0016_podar_indices_universo` deja el modelo consistente con eso. Al
aplicarla será un **no-op** (`DROP INDEX IF EXISTS` sobre índices ya borrados), y
eso está bien: lo que importa es que el estado de Django y el de la base coincidan.
Detalle completo: [`docs/infraestructura/analisis_capacidad_disco.md`](../infraestructura/analisis_capacidad_disco.md).

### 🌅 Siguiente paso, **en este orden**

1. **Dejar terminar la fase 1** (ETA ~9 h desde las 21:45 UTC ⇒ madrugada del 6-ago).
   Interrumpirla obliga a borrar y reempezar: el guard de `_cargar` no deja reanudar
   un corte a medias.
2. Confirmar en `/tmp/vigilante_universo.log` que el proceso murió **antes** de la
   fase 2.
3. **Recién ahí desplegar** la imagen con el parche y la migración. Desplegar antes
   reinicia `cz_backend` y **mata la carga en curso**.
4. Fase 2 sola, con el disco a la vista:
   `docker exec cz_backend python manage.py cargar_universo_victimas --solo-resolver --sin-enlace --confirmar`
5. `VACUUM ANALYZE` + medir, y recién entonces la fase 3 (sin `--sin-enlace`).

---

## 0-octies. 2026-08-04 (mañana) — **LA UARIV YA TIENE SERVICIO DE AUTENTICACIÓN, Y ESTÁ AL LADO**

Sesión desde la sede (red institucional). El objetivo era desatascar el acceso de
las 1.150 cuentas y apareció una vía que no estábamos considerando.

### La .9 está arriba, y sabemos por qué se había caído

| | |
|---|---|
| Sesión Oracle real | **OK en 0,09 s** — `ENTREVIS` / `RNIENTREVISTA`, sin `ORA-12518` |
| Instancia | `entrevistarn` **OPEN / ACTIVE**, `startup_time` = **3-ago 09:26** |
| Margen | 128 procesos de 1500 · 155 sesiones de 2272 (pico 135) |
| API prod | `/api/` → **200** |
| Los 4 interruptores | **apagados** — no hay ni una variable de escritura en el `.env` de prod |

El `ORA-12518` de ayer fue un **reinicio de la instancia**, no la VPN ni nuestro
código: el `startup_time` cae justo en esa mañana. Y no era agotamiento de
recursos — la base usa el **8 %** de sus procesos. Lleva 24 h estable.

### Las dos opciones que teníamos escritas, medidas de verdad

1. **Restablecimiento por correo: hoy no tiene por dónde salir.** `production.py`
   **no define ningún `EMAIL_*`** (el único backend de correo del proyecto es el
   de consola, en `development.py:49`) y el `.env` de producción **no tiene
   ninguna variable de correo**. Django caería a `smtp.EmailBackend` contra
   `localhost`, que en el contenedor no existe. No es un `settings`: requiere que
   OTI habilite un relay SMTP institucional y que el firewall lo deje salir.
2. **Copiar el hash de Vivanto: sigue siendo mala idea, por otra razón.** El
   catálogo de `ADMINUSUARIOS.USUARIO` (solo metadatos, no se leyó ni una
   credencial) trae todo el aparato de una política de credenciales:
   `CAMBIARCONTRASENIA`, `CANTIDADDEINTENTOS`, `FECHACADUCIDAD`,
   `FECHAULTIMOINTENTO`, `DESBLOQUEOAUTOMATICO`, `FECHACAMBIOCONTRASENA`,
   `IDESTADO`. Replicar el hash obligaría a replicar la parte que **sí** se
   aplica —bloqueo y estado— o SICAV quedaría desincronizado: alguien bloqueado
   en Vivanto entraría igual acá. Se mantiene el criterio de
   `crear_usuarios_activos`: **la contraseña no se copia**.

   > **Corrección (4-ago, tarde).** Arriba se escribió que Vivanto "ya tiene
   > política de credenciales completa". Medido, es **a medias**: ver el bloque
   > siguiente. Tiene el aparato; aplica el bloqueo y las franjas horarias, pero
   > **no caduca las claves** ni usa el cambio forzado.

### La política de Vivanto, medida (no supuesta)

Está declarada en `ADMINUSUARIOS.POLITICA` — **4 políticas activas**, todas
creadas entre 2014 y 2016:

| Política | Horario | Días | `MAXINTENTOS` | `TIEMPOBLOQUEO` | Longitud | `DURACIONCLAVE` |
|---|---|---|---|---|---|---|
| `GENERAL` | 06:00–19:00 | L-S (**sin domingo**) | 3 | 30 | 6–10 | **vacío** |
| `7X24` | 04:00–23:59 | todos | 3 | 30 | 6–10 | **vacío** |
| `JORNADA CONTINUA` | 00:01–23:59 | todos | 3 | 30 | 6–10 | **vacío** |
| `POLITICA OPERADORES` | 06:00–21:59 | L-S | 3 | 30 | 6–10 | **vacío** |

Tres lecturas que cambian el diseño:

1. **`DURACIONCLAVE` vacío en las cuatro: Vivanto NO caduca las contraseñas.**
   Lo confirman los datos: `CAMBIARCONTRASENIA` y `DESBLOQUEOAUTOMATICO` están en
   **0 en las 81.370 cuentas**, y la diferencia entre `FECHACADUCIDAD` y
   `FECHACAMBIOCONTRASENA` no tiene ningún período estable (225 días en 2.410
   cuentas, pero **miles en negativo**: caducidad anterior al último cambio).
   Si SICAV rota cada 45 días, **es una decisión nuestra, no paridad con ellos**,
   y como tal hay que documentarla.
2. **Longitud máxima de 10 caracteres.** Es una política de 2014 y no se copia:
   un tope de longitud impide frases de paso y no aporta nada. SICAV usa Argon2 y
   los validadores de Django, sin techo.
3. **Franjas horarias y días.** `GENERAL` **no permite domingo** y corta a las
   19:00. Copiar eso dejaría a un encuestador sin poder entrar un domingo en
   territorio. **No se replica**; el trabajo de campo no tiene horario de oficina.

Lo que **sí** vale la pena adoptar de ellos: `MAXINTENTOS = 3` con
`TIEMPOBLOQUEO = 30` minutos (hoy SICAV usa 5 intentos / 15 min de bloqueo, en
`apps/autenticacion/views.py`).

### La tercera vía: `UARIV.AUTH.API`, ya desplegada en el mismo servidor

En el `docker ps` del `.109` llevan semanas corriendo dos contenedores que no son
nuestros (proyecto compose `auth-api`, en `/home/adminuariv/auth-api`):

| | |
|---|---|
| `uariv-auth-api` | `crunidad.azurecr.io/uariv-auth-api:1.0.0` — **:8080**, Up 4 semanas |
| `uariv-auth-ui` | `crunidad.azurecr.io/uariv-auth-ui:1.0.1` — **:8081**, Up 2 semanas |

Su contrato es público en `/swagger/v1/swagger.json` (16 rutas, seguridad
`Bearer`), y es exactamente lo que necesitamos:

```
POST /auth/AuthByUser      { userName, password }
                        →  { success, access_token, refresh_token, errors[] }
POST /auth/AuthByEntraId   (SSO Microsoft Entra ID)
GET  /auth/start · /auth/callback · /auth/result   (flujo OIDC)
PUT  /api/User/ChangePassword
```

Es decir: **la institución ya resolvió identidad**, con SSO corporativo incluido,
y el servicio está a un salto de red de SICAV (`localhost:8080`) — sin VPN, sin
Oracle y sin el dblink en el camino del login.

> **Hasta acá llegó el sondeo, a propósito.** El servicio es de otro equipo: no se
> inspeccionaron sus variables de entorno ni su cadena de conexión, y **no se
> probó ninguna credencial contra él**. Solo se leyó el swagger que publica.

### 🔴 La pregunta que decide todo (para OTI / dueño de `auth-api`)

**¿Los 1.150 encuestadores de campo existen en el directorio de `UARIV.AUTH.API`?**
Si su base es la misma `ADMINUSUARIOS` de Vivanto —de donde sacamos su identidad—
la respuesta es sí y el bloqueo se cae solo. Si es un directorio distinto (por
ejemplo solo funcionarios de planta), esta vía no sirve para el territorio y
volvemos al SMTP. **No se puede responder desde nuestro lado sin husmear infra
ajena: hay que preguntarlo.**

Con eso hay que preguntar también: si nos autorizan a consumirlo desde SICAV,
cómo se emiten las credenciales de cliente, y cuál es el tiempo de vida del
`access_token`.

### Lo que igual queda por resolver, aunque la respuesta sea sí

**El campo trabaja sin señal.** Un login delegado a un servicio en línea resuelve
la primera entrada, no la operación offline. Hay que diseñar el esquema
—autenticación en línea la primera vez y credencial derivada en el dispositivo
para las jornadas sin cobertura—, que además es coherente con
[`project_arquitectura_offline`] (la precarga del padrón ya asume una primera
conexión). Esto no bloquea la decisión, pero sí es trabajo, y no está hecho.

---

## 0-octies-bis. 2026-08-04 (tarde) — **APARECIERON LOS HECHOS VICTIMIZANTES**

El área funcional aportó un nombre —`Tbsiniestros_persona`— y con eso se cayó el
pendiente **5a**, que llevaba días esperando respuesta de negocio.

### No había que pedir nada: ya teníamos el acceso

Vive en el esquema `RUV`, alcanzable desde `ENTREVISTARN` por el dblink
**`CONSULTARUV`**, que ya existía.

| Objeto | Qué es | Volumen |
|---|---|---|
| `RUV.TBHECHOS_VICTIMIZANTES` | el catálogo oficial | **13 hechos** |
| `RUV.TBSINIESTROS_PERSONA` | el hecho con **fecha y municipio** | **4.033.355** |
| `RUV.TBREG_PERSONA_HECHOS` | persona ↔ hecho | **9.331.396** |
| `RUV.TBPERSONAS` | `ID`, `NUMERODOCUMENTO`, `PARAM_TIPODOCUMENTO` | 7.330.769 |

El enlace **está declarado con foreign keys** (`FK_REGPER_SINIESTRO` y
`FK_REGISTRO_PERSONA_HECHOS`, ambas contra `PK_TBREGISTROS_PERSONAS`): la ruta
hasta el documento no es conjetura nuestra. Y como `TBSINIESTROS_PERSONA` trae
fecha y lugar, no solo se llenan las 14 columnas — se puede poner **cuándo y
dónde**.

### El catálogo, verificado con datos y no solo con nombres

La distribución de `PARAM_TIPOHECHO` da **51,8 % al 5 (Desplazamiento Forzado)**,
que es lo que tiene que dominar en Colombia, y **ningún valor cae fuera de 1..13**.
Con eso queda confirmado por evidencia lo que antes era inferencia: el
desplazamiento es el **5**, no el 1.

| | | | |
|---|---|---|---|
| 5 Desplazamiento **51,8 %** | 2 Amenaza 15,5 % | 13 Censo Masivo 10,8 % | 6 Homicidio 6,8 % |
| 1 Acto terrorista 3,4 % | 11 Despojo 3,2 % | 8 Secuestro 2,2 % | 12 Otro 1,9 % |
| 3 · 4 · 9 · 10 · 7 (sexual, desaparición, tortura, NNA, minas) 4,6 % | | | |

### 🔴 Son TRES catálogos, no dos — y la trampa se repite

```
SICAV   HV01..HV16   (este repo)
legacy  1..14        (GIC, congelado 2015)
RUV     1..13        (el nuevo)
```

RUV y legacy coinciden en 1..11 y **divergen justo donde está el volumen**:

| Código | Legacy | RUV |
|---|---|---|
| **12** | Pérdida de bienes muebles o inmuebles | **Otro** (75.264) |
| **13** | Otros | **Censo Masivo** (434.178) |

Copiar el número de un lado al otro escribe el hecho equivocado en **509.442
registros (12,6 %)** sin que nada falle — exactamente el mismo modo de fallo que
ya estaba documentado para el cruce SICAV→legacy, pero contra un tercer catálogo.

### La decisión, y por qué no se resolvió con lo que ya había

**Decisión de Javier:** traer **el catálogo, no las 9,3 M de filas**; el cruce por
persona se resuelve **bajo demanda**. Y «censo masivo a otros».

Aplicarla mandando `HV13` habría sido el error: para que Censo Masivo aterrizara
en el `'Otros'` del legacy había que mapearlo a `HV13`… que en SICAV es
**Confinamiento**. Eso habría marcado a **434.178 personas como confinadas** en
nuestra propia base. Por eso se agregaron **`HV15 Otro`** y **`HV16 Censo
Masivo`**: la pérdida de precisión ocurre **solo en la frontera** con el legacy
—ambos se escriben como `13 'Otros'`—, declarada en
`HECHO_VICTIMIZANTE_APROXIMADO` para que el escritor la informe en cada corrida.

### Lo hecho

| | |
|---|---|
| `HECHO_RUV_A_SICAV` | nuevo mapeo por **significado**, en `oracle/catalogos.py` |
| `HECHO_SIN_ORIGEN_EN_RUV` | `HV12`/`HV13`/`HV14` — su ausencia al importar es lo esperado |
| Fixture del catálogo | **16 entradas**, y con eso mueren los **14 `TODO: confirmar texto oficial`**: ahora llevan el texto del RUV |
| Producción | catálogo cargado: **0 → 16 filas** (estaba vacío desde siempre) |
| Tests | **7 nuevos** · suite **729 pass / 1 xfail** |

### Lo que falta para que el reporte se llene

El catálogo por sí solo no puebla `HechoVictima`: **falta el cruce por persona**
contra `TBSINIESTROS_PERSONA`, bajo demanda. Ese es el paso que finalmente llena
las 14 columnas.

> **Detalle operativo:** barrer varios dblinks en una sesión da
> `ORA-02020: too many database links in use` (límite `OPEN_LINKS`, 4 por
> defecto). El comando de importación tendrá que cerrar cada link al terminar.

> **Nota de despliegue:** el fixture nuevo entró a producción por `docker cp`
> sobre el contenedor, no en la imagen. Los **datos** ya están en PostgreSQL y
> persisten; la imagen traerá el fixture correcto en el próximo deploy, porque ya
> está en git.

---

## 0-septies. 2026-08-03 (tarde) — **1.150 ENCUESTADORES VEN SU TRABAJO EN SICAV**

Entró una novedad del territorio (Pandi) y terminó abriendo el trabajo del día.
Todo lo de abajo está **desplegado y corriendo en producción**.

### El caso: la encuesta nunca llegó

Detalle completo en [`caso_pandi_encuesta_no_aparece.md`](caso_pandi_encuesta_no_aparece.md).
Resumen: el documento no está en `GIC_PERSONA`, ni en el histórico, ni en las 7
tablas de staging del móvil. `JGUARINH` no capturó nada el 2-jul (su hueco va del
25-may al 29-jul). Ese día sí se crearon 429 hogares de otros. **Hay que
repetirla** — pero antes conviene confirmar el documento: existe una MONICA …
CORTES AGATON de 2015 con el número terminado en **…545** y no en …540.

### Lo construido, y lo que mide

| | |
|---|---|
| `diagnosticar_encuesta_legacy` | 7 causas de "no aparece"; en 5 el dato NO se perdió. Modos `--documento/--usuario/--hogar/--perdidas` |
| `importar_usuarios_legacy` | los 8.172 de `GIC_USUARIO` (histórico) + `--medir-autoria` |
| `crear_usuarios_activos` | **1.150 cuentas creadas** con identidad de Vivanto |
| `importar_caracterizaciones_legacy` | **222.094 caracterizaciones** de 1.151 encuestadores |
| `/api/sincronizacion/mis-caracterizaciones/` + `/resumen/` | el encuestador entra y ve lo suyo |

**2.422 caracterizaciones con datos que ningún reporte ve**, y en todas el dato
está en la base: 1.459 `NO_CERRO_POR_CAPITULOS`, 885 `ABIERTO_CON_DATOS`, 62
`ARCHIVADO_FUERA_DE_REPORTES`, 16 `CERRADO_SIN_ARCHIVAR`. (Las 4.763 `ANULADA` y
3.303 `MARCADA_ERROR` son decisiones tomadas, no pérdida.)

### Cinco cosas que la base nos enseñó, contra lo que teníamos escrito

1. **`CERRADA` son 62 hogares en toda la base.** El estado normal de uno
   terminado es `MIGRADOAHISTORICO` (1.039.334). Verificar el cierre contra el
   literal `'CERRADA'` funciona minutos y falla para siempre. Corregido.
2. **`GIC_USUARIO` está congelado desde 2017.** De los 1.153 encuestadores
   activos, solo **26** figuran ahí. El directorio vivo es
   `ADMINUSUARIOS.USUARIO ⨝ PERSONA` en Vivanto: 1.150 de 1.153, con correo y
   sin duplicados (el local tiene 608 repetidos).
3. **`GIC_HOGAR.USU_IDUSUARIO` es el id de VIVANTO**, no el de `GIC_USUARIO`.
   `JGUARINH` = 197035, y sus hogares se llaman `197035-31TUK`. El "99,7 % que no
   cruzaba" era una lectura equivocada nuestra, no dato roto.
4. **`LOG_ERRORES_ENCUESTA` está vacía.** Es la tabla correcta por su forma, así
   que queda cerrada la pregunta de "por qué falló": **no hay nada que leer**.
5. **La `Ñ` viene rota** en 6 logins (UTF-8 escrito con el charset mal), y dejaba
   131 caracterizaciones sin autor. Reparado validando contra el directorio.

### Cuatro defectos propios, todos encontrados al correrlo de verdad

- Una fila ilegible (`LookupError: unknown encoding`) tumbaba los 1.150, y el
  guardado iba al final: se perdían los 334 anteriores. Ahora va por usuario.
- **3.284 hogares anulados se presentaban como trabajo recuperable** — el listado
  le decía a su propio encuestador "está completa, no hay que repetirla".
- Las fechas del legacy entraban con **+5 h** (Oracle `DATE` es hora local y
  `USE_TZ=True` las leía como UTC): el trabajo de una tarde aparecía al día
  siguiente.
- El `/resumen/` decía "total 18" y el desglose sumaba 3: el `ordering` del
  modelo entraba al `GROUP BY`.

### 🔴 Lo único que bloquea

**Las 1.150 cuentas no pueden iniciar sesión.** Se crearon con
`set_unusable_password()`: no se leyó la columna `CONTRASENA` de Vivanto ni se
inventaron claves. Falta decidir cómo se entrega el acceso —restablecimiento por
correo, o que SICAV valide contra Vivanto, que es donde ya vive la credencial—.

---

## 0-sexies. 2026-08-03 — **LOS DIEZ PASOS ESTÁN CABLEADOS** (y lo que falta ya no es código)

Ayer faltaban los pasos 4, 5 y 6. Hoy están: **validadores**, **hechos
victimizantes** y **marca de encuestado**. Con eso, la cadena de diez pasos del
legacy está completa de punta a punta. Sigue todo en DRY-RUN y los cuatro
interruptores en `False`.

### Lo que ahora sí puede salir en un reporte

| Columna del reporte | De dónde sale | Antes | Ahora |
|---|---|---|---|
| `ESTADO_RUV` | `PRE_VALOR` del validador **1** | vacío | ✅ INCLUIDO / NO INCLUIDO |
| tipo de persona | validador **5001-5004** (23 lecturas en el legacy) | vacío | ✅ |
| perfil | validador **5005** | vacío | ✅ |
| `JEFE_HOGAR` | `MH.PER_ENCUESTADA='SI'` | 'NO' para todos | ✅ solo el autorizado |
| `HECHO_VICTIMIZANTE_1..14` | validadores **101-114** | vacío | ⚠️ el código está; **falta el dato** (abajo) |

### El hallazgo que habría corrompido el dato sin dar error

**El cruce de hechos victimizantes NO es el número del código.** Los dos catálogos
tienen 14 entradas y los dos numeran de 1 a 14, así que quitarle el prefijo a `HV01`
y usar el `1` parece razonable. Están en **orden distinto** y siete de las catorce no
coinciden:

```
HV01 Desplazamiento forzado   →  el "1" de Oracle es 'Acto terrorista'   (correcto: 5)
HV02 Acto terrorista…         →  el "2" es 'Amenaza'                     (correcto: 1)
HV03 Amenaza                  →  el "3" es 'Delitos … sexual'            (correcto: 2)
HV04 Delitos … sexual         →  el "4" es 'Desaparición forzada'        (correcto: 3)
HV05 Desaparición forzada     →  el "5" es 'Desplazamiento forzado'      (correcto: 4)
```

Y no habría fallado: el procedure acepta cualquier entero de 1 a 14. El reporte
diría **'ACTO TERRORISTA' en la fila de una persona desplazada**. Encima el
desplazamiento es el único hecho con efecto en cadena —deja el validador 105 y con
él se crea el 506 del hogar—, así que perderlo también borra la marca del hogar.
Cruce por significado, con test de regresión que falla si alguien lo "simplifica".

### 🔴 Lo que falta ahora NO es código: es de dónde sacar los hechos

`HechoVictima` está **vacía en producción y nada la puebla**. `cargar_padron_oracle`
trae identidad, etnia, género, discapacidad y estado en el RUV; **los hechos no
están en su `SELECT`**, y ningún otro comando ni endpoint escribe ahí. El paso corre,
está probado y verificado, y escribe **cero** validadores.

Traerlos parece factible por el mismo camino que el padrón (dblink a Vivanto, cruce
por `cons_persona`), pero hay que saber qué tabla los tiene. Es el punto **5a** de
[`../gestion/decisiones_negocio_pendientes.md`](../gestion/decisiones_negocio_pendientes.md).

### Cuatro defectos más, todos encontrados antes de correr nada

1. **`TypeError` esperando en la ruta confirmada.** `paso_cierre` llamaba a
   `verificar_cierre(..., tipo=tipo)` y la función no tenía ese parámetro. Solo
   revienta con `--confirmar`, que es la única ruta donde se verifica: los tests,
   todos en DRY-RUN, no llegaban nunca hasta ahí. De paso el parámetro ahora sirve —
   anular deja `ANULADA`, no `CERRADA`, y verificarlo contra el literal fijo lo daba
   por fallido siempre.
2. **`origen_id` de 73 caracteres en una columna de 64** (dos UUID pegados). Habría
   sido un `DataError` en el primer hecho, *después* de commitear los validadores en
   Oracle: hogar a medias y sin rollback. Mío, encontrado releyendo mi propio código.
3. **`confirmar=True` aceptaba un resolver no estricto**, que devuelve marcadores
   `‹PEND:...›` en vez de lanzar — o sea que esos marcadores podían entrar como
   datos en columnas de producción sin que nada fallara. Los llamadores reales ya
   pasaban `estricto=True`, pero era suerte, no barrera. Ahora aborta.
4. **Los tres procedures nuevos no son idempotentes** y la tabla no tiene PK ni
   UNIQUE: un reintento duplicaba el validador 1, y el reporte lo lee con una
   subconsulta escalar ⇒ **ORA-01427** en vez del dato. Hay chequeo previo por
   SELECT antes de cada invocación.

### Una corrección a lo que dijimos ayer

`SP_INS_ETNIA_ARES` **no borra los validadores del hogar ajeno**, como decía el
análisis. Sus dos `DELETE` están acotados también por `COMODIN`: borran solo los
**derivados** (5007-5012 y 506 con `COMODIN=1`; 267/266/173 con `COMODIN=2`), que el
propio procedure recalcula tres líneas más abajo. Los **base** —estado en el RUV,
5001-5005, 20/21, 101-114— entran con `COMODIN=0` y no los toca. Escribir en un
hogar ajeno sigue siendo grave y la guarda anti-fusión sigue siendo obligatoria; lo
que cambia es el tamaño del daño, y conviene tenerlo bien medido y no inflado.

En la otra dirección, la buena: mandamos `PPER_IDPREGUNTAPADRE` en NULL, así que el
`SP_BORRADOVALIDADORES` que dispara `pbandera=1` recorre un cursor vacío. **Los
validadores sobreviven a las respuestas.**

### Estado

| | |
|---|---|
| Tests backend | **683 pass** / 1 xfail (+26 nuevos) |
| Migración | `sincronizacion/0005` (tres pasos nuevos en el enum) |
| Escrituras en producción | **0** |
| Los 4 interruptores | **`False`** |

### Lo que sigue

1. **Resolver de dónde salen los hechos** (decisión 5a). Sin eso, 14 columnas del
   reporte quedan vacías por diseño.
2. **Un hogar real escrito a mano** con `--confirmar`, mirándolo paso por paso.
   Sigue siendo el siguiente paso operativo, y ahora escribiría el hogar completo.
3. Antes de ese hogar: el respaldo de las 8 tablas (B16) y el comando de reversión
   (B17), que siguen sin existir.
4. Las **117 preguntas sin `id_preg`**, y en particular **`Z2`**.

---

## 0-quinquies. Cierre del 2026-08-02 (noche) — **LA CADENA DE ESCRITURA ESTÁ COMPLETA**

23 commits en el día. Lo de arriba (identidad, duplicados, padrón) se cerró por la
tarde; esto es lo de la noche, que fue entrar al legacy en serio.

### El hallazgo que cambió el plan

**Llenar `GIC_PERSONA` y `GIC_HOGAR` no hace aparecer nada en los reportes.** Los
reportes leen `GIC_N_RESPUESTASENCUESTA_C`, y las respuestas solo pasan ahí cuando
la encuesta se **cierra** con `SP_ACTUALIZAR_ESTADO_ENCUESTA(..., '4')`. Un hogar
en el legacy no son dos tablas: son **ocho** y **diez pasos**.

El análisis completo, con el PL/SQL citado línea por línea, está en
[`escritura_legacy_analisis.md`](escritura_legacy_analisis.md). El volcado crudo
(1.000.516 caracteres de PL/SQL, 72 triggers, 57 jobs) queda **local**, en
`volcado/`, que el `.gitignore` protege a propósito.

### Los diez pasos, y dónde estamos

| # | Paso | Estado |
|---|---|---|
| 1-3 | Hogar · personas · miembros | ✅ y con los defectos de hoy corregidos |
| 4-5 | **Validadores · hechos** | ❌ **lo que falta** |
| 6 | Marca de encuestado | ❌ |
| 7-8 | Territorio · respuestas | ✅ |
| 9-10 | **Capítulos · cierre** | ✅ hechos hoy |

Sin los **validadores** el hogar llega al legacy pero `ESTADO_RUV` y
`HECHO_VICTIMIZANTE_1..14` salen **vacíos** en los reportes. Es el siguiente
trabajo grande, y sus tres procedures ya están identificados con su firma.

### Lo que se arregló, en orden de gravedad

1. **`GIC_PERSONA` recibía personas SIN nombre ni documento.** El mapeo leía los
   campos del `MiembroHogar`, que —lo dice su propio `help_text`— solo se llenan
   para quien **no** está en el RNI. El miembro que viene del padrón los tiene
   vacíos: su identidad está en `Victima`. El piloto no lo detectó porque usó
   datos sintéticos. *Es el defecto que habría vaciado los reportes.*
2. **Fusión de hogares.** `GIC_INSERT_HOGAR1` devuelve `MARCADOR='1'` cuando crea
   y **el código del hogar viejo** cuando no; se estaba tomando ese código como
   propio. Cuatro cerrojos ahora, y si el hogar no queda verificado **se aborta
   todo**: una sola respuesta en un hogar ajeno dispara `SP_INS_ETNIA_ARES`, que
   borra sus validadores filtrando solo por código.
3. **No cerrar un hogar incompleto.** Los capítulos se derivaban de todas las
   respuestas de la sesión, no de las escritas: con 39 de 40 fallando se marcaban
   los capítulos igual, el cierre se disparaba, copiaba **una** fila y borraba la
   tabla de trabajo. Irreversible y sin reparación posible.
4. **Cinco valores fuera de dominio** que hacían invisible el dato: `PER_ESTADO`
   mandaba `'ACTIVA'` (que es el estado del *hogar*), `PER_ENCUESTADA` mandaba
   `'S'` donde el legacy compara `'SI'`, `PER_IDMODELOINT` iba en `NULL` —y el job
   que resuelve el cruce con el RUV busca `= 0`, así que esa fila no la vería
   nunca—, el usuario podía ir vacío contra una columna `NOT NULL`, y la fecha iba
   en UTC (+5 h) sobre un `DATE` que los reportes leen como hora local.
5. **256 preguntas abiertas** no se podían escribir: abortaban el hogar. En
   territorial v8 son 56 —documento, dirección, teléfonos, correo—, así que ningún
   hogar completo pasaba.

### Un 500 en producción, que no era de duplicados

El WAF reenvía `X-Forwarded-For` **con puerto** (`186.29.187.18:62432`) y
`LogAcceso.ip_origen` es un `GenericIPAddressField`: el INSERT del log reventaba y
**toda la búsqueda respondía 500**. Por `localhost` la IP llega limpia, así que
las pruebas locales pasaban y fallaba solo entrando por el dominio — o sea, solo
para los usuarios. Cinco módulos leían esa cabecera por su cuenta; ahora hay una
sola implementación en `apps/auditoria/red.py`.

### Sincronización de novedades: segundos, no horas

El legacy mueve **~592 personas y ~270 hogares por día**. Traerlos por marca de
agua sobre `PER_IDPERSONA` (que tiene índice único) tarda **4,2 s**; por fecha
tardaba 16 s solo en la consulta, porque `USU_FECHACREACION` no está indexada en
`GIC_PERSONA` —en `GIC_HOGAR` sí, y por eso cada tabla va por su camino—.
Programada cada 15 min, **apagada** por defecto, con freno anti-eco desde el día
uno (los hogares del usuario 999999 se excluyen de la lectura).

### El piloto quedó ANULADO

`999999-2W832` pasó a `ANULADA` el 2-ago 17:48. **No se perdió nada**: sus 3
respuestas se movieron de la tabla de trabajo a la definitiva —comportamiento
correcto del procedure, que corrigió dos cosas que yo había leído mal—. El usuario
999999 quedó **libre**: ya se puede escribir un hogar nuevo.

### Estado al cierre

| | |
|---|---|
| Backend | ✅ desplegado · 657 tests · migraciones al día |
| Panel web | ✅ desplegado |
| APK | compilando al cierre de esta nota |
| **Los 4 interruptores** | **`False`** — nada escribe solo |
| Padrón offline | 5.001.402 filas, publicado |

### Lo que sigue

1. **Validadores y hechos** (pasos 4-6). Sin ellos los reportes salen con las
   columnas de RUV y hechos vacías.
2. **Un hogar real escrito a mano**, mirándolo, antes de encender nada.
3. Las **117 preguntas sin `id_preg`**: la mayoría no van a la tabla de respuestas
   (subcampos "Otro", identidad, hechos), pero **`Z2` sí** — y sin ella el hogar
   no aparece en los reportes por departamento.
4. Los **878→896 MB** del padrón y los **nombres en claro**: sin tocar.

---

## 0-quater. Actualización 2026-08-02 — **DESPLEGADO Y LISTO PARA LAS PRUEBAS**

Todo lo del 1-ago está en producción, y encima se resolvió el problema de fondo:
**qué hacer cuando un documento pertenece a más de una persona**.

### Lo que cambió el diagnóstico

Lo que parecía un millón de colisiones de identidad no lo era. Medido sobre la
base real (768.096 documentos repetidos de 4.928.725):

| Qué es | Documentos | % |
|---|---:|---:|
| Una sola persona duplicada por el Oracle de origen | 706.301 | 92,0 % |
| La misma persona con el nombre mal escrito | 9.710 | 1,3 % |
| **Personas distintas compartiendo documento** | **51.996** | **6,8 %** |
| Valores de relleno (`99`, `0`…) | 89 | 0,0 % |

El documento `1089290511` aparece **505 veces**, siempre ALBA TAPIA RODRIGUEZ, con
504 `cons_persona` distintos. Y `99` sale 4.297 veces con **3.780 nombres
distintos**: no es un documento, es un campo que alguien rellenó.

**El colapso ciego no borraba 997 mil personas: borraba 53.724.** Sigue siendo
inaceptable, pero la decisión correcta era otra —distinguir, no elegir—.

### Qué hace ahora el sistema

| Clase | Búsqueda (web y APK) | Padrón offline |
|---|---|---|
| `DUPLICADO_FUENTE` / `VARIANTE_NOMBRE` | 200, la fila más completa | una fila |
| `AMBIGUO` | **409** con todos los candidatos | **todas**, marcadas |
| `NO_IDENTIFICANTE` | **409 sin mostrar a nadie** → alta manual | una marca vacía |

Sin veredicto se pregunta igual: el default es la pregunta de más, nunca el
silencio. El 409 pasa de dispararse en 768.096 documentos a ~52.000 — el 92 % de
las interrupciones al encuestador desaparecen, que es lo que hace que el aviso
restante se lea en vez de ignorarse.

**El porqué completo, con la investigación de cómo lo resuelven los índices
maestros de pacientes, el registro civil y ACNUR, y lo que descartamos:**
[`../oracle-legacy-padron/decision_documentos_duplicados.md`](../oracle-legacy-padron/decision_documentos_duplicados.md).

### Verificado contra producción (no en local)

Los cuatro casos, con documentos reales sacados de la base:

```
  /buscar/  LIMPIO             HTTP 200   una ficha
  /buscar/  DUPLICADO_FUENTE   HTTP 200   una ficha (2 filas → 1 persona)
  /buscar/  AMBIGUO            HTTP 409   ambiguo=True candidatos=2
  /buscar/  NO_IDENTIFICANTE   HTTP 409   no_identificante=True candidatos=0
```

Y `/consultar-fuente/` (el camino de la APK) coherente con los cuatro. El caso
ambiguo ejercitó además el **respaldo por número sin tipo**, con su aviso.

### Una revisión adversarial encontró 17 defectos ANTES de correr nada

Se revisó el código nuevo antes de soltarlo sobre 5,9 M de filas, y los hallazgos
se verificaron **ejecutando** el módulo. Los graves, todos arreglados:

* **Con apellidos vacíos —Oracle NULL llega como `''`— el clasificador
  sobrescribía una persona entera** y marcaba el grupo como "una sola": el mismo
  borrado silencioso, por la puerta de atrás.
* **Sin fecha de nacimiento, `'' == ''`** daba por cumplida la salvaguarda y unía
  hermanos.
* **El veredicto dependía del orden en que PostgreSQL devolviera las filas**: dos
  corridas podían dar padrones distintos.
* El borrado de la tabla estaba **fuera de la transacción** (una corrida muerta a
  mitad quedaba indistinguible de una completa) y `--limite` sin `--dry-run`
  destruía los 768 mil veredictos.
* `victima_preferida_id` NULL borraba **todas** las filas del documento.
* **La búsqueda web respondía 404 al 14,5 % del padrón** (las cargadas sin tipo).
* **En la APK la ambigüedad se preguntaba sin red y se silenciaba con red**, y la
  migración del schema local **borraba el padrón** dando por hecho que la precarga
  lo repuebla — y solo corre al iniciar sesión.

### Estado al cierre

| | |
|---|---|
| Backend en prod | ✅ desplegado, `/api/` 200, migraciones al día |
| Dominio público | ✅ 200 (`caracterizacion.unidadvictimas.gov.co`) |
| APK nueva | ✅ compilada y publicada — descargable por el dominio, **no solo por ngrok** (la red institucional lo bloquea) |
| Clasificación | ✅ 768.096 documentos |
| Padrón regenerado | ✅ `padron-20260802151221-10b01f88` |
| Tests | backend 602 · APK 88 · `tsc` limpio |

### El padrón nuevo, verificado contra la base

`srni-backend/scripts/verificar_padron.py` comprueba lo que el diseño promete,
contra el archivo y contra PostgreSQL. Las once verificaciones pasaron:

| | Antes (2-ago 04:45) | Ahora |
|---|---:|---:|
| Filas | 4.928.725 | **5.001.402** |
| Personas que el colapso borraba | 53.724 | **0** |
| Filas marcadas para confirmar | — | 124.673 |
| Documentos de relleno (sin datos de nadie) | — | 89 |
| Tamaño | 878 MB | 896 MB |

Las **72.677 filas de más** son exactamente las personas que antes desaparecían.
El caso ALBA TAPIA: 484 filas en la fuente → **1** en el padrón. El documento
`99`: 128 filas → **1 marca vacía**, sin el nombre de ninguno de los 3.780.

Endpoints probados: `/padron/version/` (manifiesto nuevo), `/padron/download/`
(200 + ETag, 940 MB) y `/precarga/` — que ya entrega `clase_colision`: de 5.000
filas del arranque de jornada, 157 vienen marcadas `AMBIGUO`.

⚠️ **La APK vieja no sirve para probar esto**: el almacén local cambió (schema
v11) y sin él la app se comporta como antes.

**Guion de pruebas:**
[`../pruebas/guion_pruebas_funcionales_identidad.md`](../pruebas/guion_pruebas_funcionales_identidad.md)
— los cuatro caminos, con qué debe pasar y **qué sería un fallo**.

### Lo que sigue abierto

1. **Los `AMBIGUO` no dejan rastro.** El encuestador confirma en campo y esa
   decisión no se guarda: la próxima búsqueda vuelve a preguntar. La industria lo
   manda a una cola de curaduría; registrar la confirmación es el paso siguiente.
2. **El padrón pesa 878 MB** (1b) y **los nombres van en claro** (1c). Ninguna de
   las dos se tocó hoy.
3. Las tareas programadas siguen apagadas — ahora la cadena incluye
   `clasificar_colisiones`, pero conviene encenderlas después de resolver 1b/1c.

---

## 0-ter. Actualización 2026-08-01 — **EL PADRÓN REAL ESTÁ CARGADO**

Ya no estamos leyendo el padrón: **está en nuestra base**.

| | |
|---|---|
| Personas en el padrón | **5.927.713** víctimas **incluidas** (`ESTADO_RUV = 1`) |
| Fuente | `GIC_PERSONA` ⨝ `M_CARACT_TABLA_RA_PER@DBL_VIVANTO` |
| Duración de la carga | 19 h (sobrevivió a dos caídas de VPN) |
| Regla de 2 años | **1.940.213 vencidas** · 1.392.101 al día |
| Descartadas | 0 |

**Antes de tocar nada, leer:**
[`../oracle-legacy-padron/hallazgos_identidad_padron.md`](../oracle-legacy-padron/hallazgos_identidad_padron.md)
— 11 hallazgos sobre cómo está partida la identidad entre las tres bases, y las
**5 preguntas para OTI**. Y [`../ciclo_completo_tablas.md`](../ciclo_completo_tablas.md)
— el recorrido entero de un dato y qué se rompe en cada etapa.

### Lo que se decidió, y lo que costó

**No se usó `MI_PERSONAS`**, que era el origen pedido. Tres mediciones lo impidieron:
su `PER_ID` no se alcanza desde `GIC_PERSONA.PER_IDMODELOINT` (**0 de 20.000**); el
puente `DEP_RUV_PERSONAS_MI` mezcla RUPD/RUV/SIV y el `CONS_PERONA` del corte cruza
con **dos fuentes a la vez**; y el cruce por documento devuelve **1.159 millones de
filas a partir de 20.000 documentos** porque hay 1,2 M de documentos de un solo
carácter. Cualquiera de esos caminos asigna datos de **otra persona**, en silencio.

**El precio:** **1.884.872 víctimas incluidas (24 %)** no tienen identidad en la .9 y
**quedan fuera del padrón**. La APK debe permitir alta manual — no es un caso raro,
es una de cada cuatro.

### Cuatro defectos que estaban escondidos y ya no

1. **Producción respondía con el MOCK.** `settings.VICTIMA_REPOSITORY` no existía en
   ningún settings → `getattr(..., "MOCK")`. Las búsquedas devolvían ENC001 y
   documentos 999… El sistema *funcionaba*, solo que contra otra base.
2. **La precarga pedía el padrón entero.** `/api/victimas/precarga/` llamaba a
   `listar_todas()` sin tope: con el mock eran 11 personas, con el padrón real
   5.926.004 → el login de la APK quedaba colgado sin dar error.
3. **`MEDIA_ROOT` solo estaba en development** → `generar_padron` abortaba en el
   servidor.
4. **`CELERY_TASK_TIME_LIMIT = 600`** habría matado la recarga mensual a los 10 min, y
   el `visibility_timeout` de Redis (1 h) habría lanzado **dos cargas simultáneas**
   contra Oracle.

Los cuatro con test de regresión.

### Para que se mantenga solo

`cz_beat` + `cz_celery_padron` desplegados, con tres tareas — **apagadas por defecto**,
porque encenderlas escribe en producción:

| Tarea | Cuándo | Interruptor |
|---|---|---|
| `recargar_padron` (padrón → fechas → SQLite) | 1.º sábado del mes, 20:00 | `PADRON_RECARGA_HABILITADA` |
| `refrescar_fechas_padron` (fechas → SQLite) | diaria, 03:30 (~15 min) | idem |
| `reintentar_sincronizaciones_pendientes` | cada 15 min | `SYNC_REINTENTO_HABILITADO` |

Para encenderlas: editar el `.env` del servidor y `docker compose up -d cz_beat`.

### Lección operativa (costó cuatro intentos)

**La VPN a 30.0.1.109 se cae seguido.** Los comandos largos por SSH mueren con cada
corte. Lo que funciona: subir un script y lanzarlo con `setsid nohup` **del lado del
servidor**, y consultar el log aparte. Así sobrevivió la carga de 19 h. Los cortes a
mitad de un `docker compose up` dejan contenedores huérfanos con nombre hasheado
(`41812ae7da25_cz_backend`) que bloquean el siguiente `up`: hay que `docker rm -f`
esos, **nunca `cz_postgres`**.

### Qué falta

1. ~~Terminar `generar_padron`~~ ✅ **TERMINÓ el 2-ago 04:45 UTC** (11 h en total).
   `padron-20260802044544-9bf121f2.sqlite3`. Paso 3: 2.535.941 fechas aplicadas
   sobre 3.332.338 leídas en 36.619 s; 796.373 fuera del padrón; 24 fechas
   imposibles. Padrón: 5.926.004 · con fecha 2.535.941 · al día 1.058.971.
   **El archivo existe, pero NO está listo para campo — tres hallazgos; al 2-ago
   queda 1a cerrado y 1b/1c abiertos, ambos esperando decisión:**

   🔴 **1a. El manifiesto declara 997.279 filas que no están.** ✅ **ARREGLADO Y
   DESPLEGADO (2-ago, `4b88856`).** `generar_padron` ahora declara el `count(*)`
   del archivo y agrega `registros_leidos` y `colisiones_documento`, con aviso en
   stdout. El manifiesto **ya servido** se corrigió en caliente sin regenerar las
   11 h (mismo `checksum` y `version` → la APK no re-descarga): el endpoint
   `/padron/version/` responde `total_registros 4.928.725`, `registros_leidos
   5.926.004`, `colisiones_documento 997.279`. *Sigue abierta la **decisión
   funcional**: qué hacer con los duplicados dentro del archivo offline (ver más
   abajo, y ojo que el camino ONLINE ya quedó resuelto con el 409).* El texto
   original del hallazgo, para contexto:
   `padron-latest.json` decía 5.926.004 registros; el SQLite tiene **4.928.725**. La
   causa es `INSERT OR REPLACE INTO padron` con `doc_hash TEXT PRIMARY KEY`: cuando
   dos víctimas comparten documento, la segunda pisa a la primera **sin avisar**. El
   número cuadra exacto con la BD (5.926.004 − 4.928.725 pares distintos = 997.279).

   | Repeticiones del documento | Documentos | Personas |
   |---|---:|---:|
   | 2 (probable duplicado real) | 617.770 | 1.235.540 |
   | 3–10 | 149.633 | 509.521 |
   | 11–100 | 678 | 10.756 |
   | **>100 (comodín, uno con 4.297)** | **15** | **9.558** |

   Los pares son probablemente la misma persona (H9) y quedarse con una se defiende.
   Los 693 con >10 repeticiones son el documento basura de H5: ahí son personas
   **distintas** y la búsqueda devuelve una al azar — el riesgo de "datos de otra
   persona, en silencio". *Arreglo inmediato y sin decisión: que el conteo del
   manifiesto salga del `count(*)` del archivo, no del contador del bucle, y que se
   informe cuántas colisiones hubo. Lo que sí es **decisión funcional**: qué hacer
   con los duplicados (la caracterizada más recientemente / excluirlas / marcarlas
   para alta manual).*

   🟠 **1b. Pesa 878 MB, no los ~150 MB de la arquitectura offline** (5,9×). Es el
   punto que decide si "descargar el padrón entero al dispositivo" se sostiene con el
   padrón real. Dónde está el peso: `doc_hash` **301 MB** (SHA-256 en hex de 64
   caracteres; en binario truncado a 16 bytes serían ~75 MB), `nombre` 123 MB,
   `cons_persona` 32 MB, el resto índice y overhead.

   🟠 **1c. Los nombres van en claro.** `nombre TEXT NOT NULL`: 5,9 M nombres reales
   de víctimas sin cifrar en un archivo que se descarga a móviles. El cifrado estaba
   anotado como Fase 1, pero hasta el 1-ago el contenido era el mock de 11 personas.

   🟠 **1d. Los duplicados DENTRO del archivo offline siguen sin decidirse.** El
   online ya está resuelto (409 con candidatos, punto 2). Pero el SQLite tiene una
   sola fila por `doc_hash`, así que **offline** una búsqueda sobre esos 768.096
   documentos devuelve **una** de las personas y no dice que había otra — que es
   justo el silencio que el 409 elimina online. Las salidas posibles: (a) permitir
   varias filas por documento (PK compuesta o `rowid`) y que la APK muestre
   candidatos, como online — es lo coherente, y **aumenta** el tamaño ya
   problemático de 1b; (b) marcar el documento como ambiguo con una bandera y sin
   los datos de nadie, forzando la consulta online o el alta manual; (c) excluirlos
   del archivo. **Decide Javier** (ver [`../gestion/decisiones_negocio_pendientes.md`](../gestion/decisiones_negocio_pendientes.md)).

2. ~~Probar login + búsqueda con un documento real~~ ✅ **HECHO (2-ago), y encontró
   un 500 en producción.** Login `200`; búsqueda con un documento real del padrón:
   **500**. `BuscarVictimaView` hacía `.get()` sobre `numero_documento_hash` y el
   documento estaba repetido — le pasa a **768.096 documentos** de 4.928.725
   (~15,6 % de las búsquedas posibles). Salió en el **primer** intento, sin
   buscarlo. Tres arreglos en `4b88856`, ya desplegados y verificados contra prod:

   | Camino | Antes | Ahora |
   |---|---|---|
   | `/api/victimas/buscar/` (frontend web) | **500** | **409** + `candidatos` + `ambiguo:true` + "CONFIRME cuál corresponde"; auditado con `coincidencias` |
   | `/api/victimas/consultar-fuente/` (APK) | avisaba "Hay 2 registros… CONFIRME" con `candidatos: 0` | manda los candidatos: el aviso ya se puede cumplir |
   | manifiesto del padrón | `total_registros` del contador del bucle | `count(*)` real + `registros_leidos` + `colisiones_documento` |

   La **APK nunca estuvo afectada** por el 500: usa `/consultar-fuente/`, que va por
   el repositorio (que sí manejaba los duplicados). El 500 lo veía el frontend web.
   ⏳ Queda **para Brando**: manejar el `409` en `srni-frontend` — hoy caería en el
   handler de error genérico. El body trae `detail`, `ambiguo` y `candidatos[]`.
   6 tests nuevos en `apps/victimas/tests/test_documento_duplicado.py`;
   suite **558 pass / 1 xfail**.

2-bis. ~~🚀 **DESPLEGAR**~~ ✅ **DESPLEGADO (2-ago).** Migraciones aplicadas:
   `hogares/0007`, `victimas/0008`, `victimas/0009`. La de datos **no tocó nada**:
   en prod hay 0 filas con `fuente_origen='NO_INCLUIDA'`/`'OFFLINE'` (las 5.926.004
   víctimas son padrón puro, todavía no hay altas manuales en producción).
   ⚠️ **Trampa del deploy, para la próxima:** al recrear `cz_backend` cambia su IP y
   `cz_nginx` se queda con la vieja cacheada → **502 en todo `/api/`** aunque
   gunicorn esté sano. Se arregla con `docker restart cz_nginx`. Verificar siempre
   con `curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/` **después**
   de recrear.
3. ~~Decidir la **etiqueta del alta manual**~~ ✅ **DECIDIDO Y APLICADO (1-ago).**
   Estado nuevo **`NO_VERIFICADO`** = *"no está en el padrón descargado"*, que no es
   *"no está en el RUV"*. Toca `Victima.ESTADO_RUV`, `MiembroHogar.ESTADO_INCLUSION`,
   la APK (payload, colores y textos) y tres migraciones —`victimas/0008`,
   `victimas/0009` (datos), `hogares/0007`—. De paso salieron tres defectos: la APK
   mandaba `fuente_origen='NO_INCLUIDA'`, que **no existe** en el modelo y entraba
   porque el serializer era un `CharField` suelto; el default del serializer era
   `NO_INCLUIDO`; y el padrón offline degradaba a `NO_INCLUIDO` todo lo que no viniera
   marcado `INCLUIDO`. 10 tests nuevos; suite 549 pass / 1 xfail.
   **Detalle en [`../ciclo_completo_tablas.md`](../ciclo_completo_tablas.md) §6.**
   ⏳ Queda **para Brando**: la clave `NO_VERIFICADO` en `ESTADO_RUV_BADGE` del
   frontend web (no rompe, solo no pinta el badge).
   🚀 **Al desplegar:** correr las migraciones — hay una de datos que reetiqueta las
   altas manuales ya grabadas.
4. Encender las tareas programadas cuando se quiera.
   Estado verificado el **2-ago**: siguen **apagadas** — no hay ninguna variable
   `PADRON_*` ni `SYNC_*` en el `.env` de prod, y los defaults son `False`.
   💡 **Recomendación: no encenderlas todavía.** `refrescar_fechas_padron` corre a
   diario y **regenera el SQLite**; hoy eso produciría cada noche un archivo de
   878 MB con los nombres en claro (1b y 1c abajo). Encenderlas después de decidir
   tamaño y cifrado, no antes.
   ⚠️ **Antes de encenderlas hacía falta un arreglo, ya hecho (1-ago).** El
   `UPDATE` de `cargar_fechas_caracterizacion` era **incondicional**: cruzaba por
   `cons_persona` y reescribía la fila aunque el valor ya fuera ese. Como
   `refrescar_fechas_padron` corre **a diario a las 03:30**, cada noche habría
   reescrito 3,3 M filas para dejarlas idénticas.
   No es una ineficiencia de manual: `victimas_victima` tiene **24 índices** y el
   UPDATE toca `habilitado_para_caracterizacion`, que está indexada — eso descarta
   el *HOT update*, así que cada fila cuesta **25 escrituras**. Medido en la corrida
   real: **8 h y seguía**, con 61 GB de WAL cada tres horas. La estimación del
   docstring (~12 min) estaba mal por un factor de 40, y ya está corregida con el
   número real.
   Ahora el cruce se materializa en una temporal (que no genera WAL), se marca ahí
   qué cambia de verdad, y el UPDATE va **por PK** solo sobre esas filas. El
   informe pasa a dar dos cifras: las que cruzan y las que se escribieron.
   SQL validado contra el PostgreSQL del servidor con tablas temporales y
   `ROLLBACK` (los tests corren en SQLite y **no** cubren ese camino — es la misma
   trampa de `9a35c18`, el `COPY` de psycopg2).
5. Las 5 preguntas para OTI — **borrador listo (1-ago)**:
   [`../gestion/correo_oti_identidad_padron.md`](../gestion/correo_oti_identidad_padron.md).
   Falta que Javier lo revise y lo mande. Ninguna de las cinco bloquea el despliegue;
   la 1 y la 3 son las que recuperarían al 24 % que quedó fuera del padrón.
6. `xfail` abierto: los capítulos D/E/F/G de ASISTENCIA ya no están cerrados a los
   incluidos en RUV (defecto funcional vivo; reponerlo exige regenerar bundle y
   validar en dispositivo).

---

## 0-bis. Actualización 2026-07-28 — **ESCALÓN 2 LOGRADO**

El corte de este documento (16-jul) quedó viejo. Estado real al 28-jul:

- ✅ **Escalón 1** (24-jul): primera escritura real end-to-end contra la réplica local.
- ✅ **Escalón 2** (28-jul): la **ruta geográfica** verificada. `11/11 VERIFICADO`,
  idempotente, y la respuesta geográfica **la resuelve Oracle**: `'5001' → Medellin /
  Antioquia`, con el mismo join que usan sus reportes.
- ✅ **El bloqueante del "entorno de Pruebas de OTI" se disolvió**: se probó que la ruta
  de escritura no lee `AP_GEOGRAFIA` (las 18 referencias están en `SP_CONSTANCIA_GAVE`,
  que no tiene llamadores; el cierre transitivo de la escritura son 17 subprogramas y
  ninguno usa dblink).
- 🐞 **Defecto real encontrado y corregido**: las preguntas de departamento/municipio
  guardaban el DANE **con** cero a la izquierda (`'05001'`) y Oracle espera `'5001'`
  (`GIC_MUNICIPIO.ID_MUNI_DEPTO`, medido: **28.151/28.151 = 100 %**). Rompía en silencio
  en 8 departamentos.
- 🔒 **Riesgo crítico corregido**: `--destino local` podía resolver a producción si la
  sesión tenía `ORACLE_LEGACY_HOST` exportado. Ahora aborta, y el comando imprime el DSN.
- 📋 **3a.11 con dato**: volcados los **266 puntos de atención** reales.
- **Tests: 134/134** en `apps/sincronizacion`. **Escrituras en producción: 0.**

> **Detalle completo en [`plan_escalon_2.md`](plan_escalon_2.md).** Lo de abajo es
> historia previa; donde contradiga a esta sección, manda esta sección.

---

## 0. Actualización 2026-07-22 — el catálogo COMPLETO ya está en el Oracle local

**Se cerró el bloqueo #1 (catálogo truncado).** En vez de reexportar por el cliente SQL,
se trajo el catálogo entero desde prod al Oracle **local**:

- **Método (cero footprint en prod):** `SELECT` directo de las 8 tablas de **catálogo**
  (sin PII) desde `30.0.1.9/ENTREVISTARN` (solo lectura) e `INSERT` en el Oracle local.
  No se creó `.dmp`, ni job, ni archivo en el server. Script reproducible:
  `srni-backend/scripts/cargar_catalogo_local.py` (lee `infra/oracle-local/.env.prod`,
  gitignored). **No** se trajo `GIC_N_RESPUESTASENCUESTA` (respuestas reales = sensible).
- **Cargado (9.316 filas, todas de definición):** `GIC_N_PREGUNTAS` 1108,
  `GIC_N_RESPUESTAS` 3686, `GIC_N_INSTRUMENTOXPREG` 903, `GIC_N_INSTRUMENTOXRESP` 3533,
  `GIC_INSTRUMENTO` 1, `GIC_TEMA` 69, `GIC_TIPOCARACTERIZACION` 2, `GIC_TIPODOC` 14.
- **`respuestas_oracle.json` REGENERADO → `cobertura: COMPLETO`** (antes: truncado a 200):
  **902 preguntas / 3069 respuestas / 43 huérfanas**. Export crudo versionado en
  `docs/oracle-legacy/query_a_v2_completo.tsv`. Comando:
  `generar_catalogo_respuestas ../docs/oracle-legacy/query_a_v2_completo.tsv --fecha 2026-07-22`
  (en Windows, con `PYTHONUTF8=1` o la consola revienta al imprimir `⇒`).
- **Confirmado con dato completo (no muestra):**
  - **Parentesco (preg 28):** 6 escribibles (`79,80,81,84,906,912`) = las 6 del manual =
    las 6 de SICAV; 7 huérfanas. **Falsa alarma cerrada, ahora con catálogo completo.**
    ⇒ el correo que escala esto como "defecto activo" hay que **corregirlo**, no ejecutarlo.
  - **Cédula (preg 30):** los 4 ids `93/3852/3853/3854` son **todos escribibles** →
    sigue siendo pregunta de negocio para Oscar (3a.13).
- **Nueva lista de curación:** las **43 huérfanas** completas ya salen en el reporte del
  comando. El default es "opciones retiradas" (como parentesco), pero **revisar contra el
  manual** algunas que llaman la atención: **preg 221/222 (hechos victimizantes:** Acto
  terrorista, Minas Antipersonal, Vinculación de NNA, Delitos contra libertad/integridad
  sexual**)** y las SI/NO de preg 1532-1535 — cotejar antes de concluir nada.
- ⚠️ **Se volvió a usar la clave de RNIENTREVISTA (solo lectura).** Sigue **pendiente de
  rotar** (3a.5) — coordinar con OTI. `.env.prod` es local y gitignored.
- **Reproducir todo:** `docker start srni-oracle-local` → `scripts/cargar_catalogo_local.py`
  → `generar_catalogo_respuestas ...`. Sin commitear (a revisión de Javier).

**Avance 2026-07-22 (cont.) — curación cruzada + crosswalk verificado:**
- Se cruzó SICAV ↔ catálogo completo: **0 pérdidas silenciosas reales**; 148 trivial /
  16 sustantiva / 12 mapeo-dudoso / 2 a Oscar (agente experto, contra el manual).
- **Crosswalk verificado** `apps/sincronizacion/oracle/crosswalk_opciones.json` (164
  mapeos SICAV→`res_idrespuesta`). **164/164 verificados: existen y son escribibles**.
  Clasificación: **104 CROSSWALK_SOLO** (dato puro, no toca instrumento — p.ej. `"Otro"`
  →`"Otro,¿cuál?"` es prompt de sub-campo) · **54 FIXTURE_REVISAR** (wording caso a caso)
  · **6 FIXTURE_FIX_TYPO** (typos claros de SICAV: `recolecion`, `ota`, `Combares`,
  `exploración`→`explotación`, `turiísticos`).
- **Hallazgo estructural:** `PR3_re` (Ayuda Humanitaria) está mapeado a `id_preg=92`
  (=rehabilitación) — id_preg mal. Revisar antes de escribir ese perfil.
- Propuesta y detalle: `docs/gestion/curacion_crosswalk_propuesta.md`. Normalizador
  reforzado (§2). Tests: **96/96**.

**Avance 2026-07-22 (cont. 2) — ejecutado:**
1. ✅ **Crosswalk WIREADO** en `resolver_res_idrespuesta` (consulta `crosswalk_opciones.json`
   como autoridad curada antes de fallar, verifica escribibilidad, sin fuzzy). Tests: **100/100**.
2. ✅ **Batch de fixture APLICADO** (en `main`, sin commitear): **21 correcciones** (6 typos +
   15 wording) → **79 ediciones en fixtures + 63 en bundles**, en 7 `perfil_*.json` + 6 bundles.
   Diff mínimo (88 líneas, verificado que es solo `etiqueta`), **fixture↔bundle 0 mismatches**.
   Detalle: `docs/gestion/batch_fixture_correcciones.md`. NO se bumpeó versión (correcciones
   cosméticas, in-place; el APK las toma en el próximo build).

**Avance 2026-07-23 — crosswalk reconciliado:**
- `main` mergeado al worktree (merge `1dd5928`): el worktree ya tiene el instrumento corregido.
- **Crosswalk reconciliado** (`crosswalk_opciones.json`): **164 → 148** mapeos. Se quitaron
  **16 entradas redundantes** (el label corregido ya == Oracle ⇒ el resolver cruza DIRECTO,
  p.ej. `Combates o bombardeos`, `Ninguno`, `Usufructo`) y se **re-clavaron 3** al label nuevo
  (`Rural disperso (vereda)`, pre 1164/1452/1461, que sigue ≠ Oracle `Parte rural disperso…`).
  `_meta.reconciliado` lo documenta. Test del typo reemplazado por uno del caso que sobrevive.
  **100 tests verdes.**

**Siguiente:**
1. **A Oscar:** familia NS/NR (M-series), pre1435 `del jefe`→`del responsable`, pre1503 mismatch,
   PR3_re id_preg, "Autodiligenciada"/"Cara a cara" (pre 2), Cédula 3854.
3. **`cargar_perfil --reemplazar`** de los 7 perfiles editados en el server (en el próximo deploy;
   el fixture es la fuente, la BD se regenera). ¿Bump de versión? Solo si se quiere que el sync
   empuje a dispositivos ya desplegados; para cosmético no hace falta.
4. 🔒 Rotar clave RNIENTREVISTA + borrar `.env.prod`. Commitear (main = instrumento; worktree = migración) cuando Javier revise.

---

## 1. Qué hicimos (fases completadas)

| Fase | Resultado | Artefacto |
|---|---|---|
| **Infra Oracle local** | Contenedor Docker `gvenzl/oracle-free` (`FREEPDB1`), esquema `RNIENTREVISTA` importado con estructura real (333 tablas/78 triggers/68 secuencias). Export lo generamos nosotros (no OTI). | `infra/oracle-local/`, `docs/oracle-legacy/oracle-local-setup.md` |
| **Validación de paridad** | Lógica portada: **24/24** tests Django. Estructura: **12/12** invariantes resuelven contra el esquema real. | `paridad_logica_portada.md` |
| **Housekeeping prod** | `DROP` de master table huérfana `SYS_EXPORT_SCHEMA_01`; secreto de prod borrado. (Falta: rotar clave RNIENTREVISTA — lo hace Javier.) | — |
| **Etapa A — capa de escritura (DRY-RUN)** | Strangler-fig etapa A: escribir vía **procedures oficiales**. Ledger reanudable + máquina de estados + verificación por SELECT + redacción PII. Comando `escribir_a_oracle` (DRY-RUN; `--confirmar` bloqueado). | `apps/sincronizacion/` · commit **`b504d79`** |
| **ResolverCatalogos** | Traduce SICAV→Oracle con **valores reales de prod**: tipo_doc (CC→1…), parentesco (8), tipo_caracterización=HOGAR(2). Nunca inventa. | `oracle/catalogos.py`, `catalogos_oracle.json` |
| **Auditoría de diseño legacy** | 10 hallazgos + 4 nuevos, cada uno con decisión (replicar/mejorar/descartar) y evidencia. | `auditoria_diseno_legacy.md` |
| **Veredicto a1 vs a2** | **a1 (procedures granulares) confirmado.** a2 (ingesta móvil) descartada: no puebla territorio (reintroduce el bug). | `auditoria_diseno_legacy.md` §Veredicto |

**Decisiones de arquitectura cerradas:** strangler-fig (a1 ahora, escritura directa Django = Etapa B después) · ruta = procedures granulares · no arrastrar Java-en-BD, tablas-sombra, packages muertos, reportes congelados.

---

## 2. Estado actual del código

- **Commiteado y pusheado** en `feat/oracle-legacy-writer` (ambos remotes, `origin` + `azure`):
  - `b504d79` — Etapa A + ResolverCatalogos (17 archivos).
  - `38e4bf0` — incrementos 6+7: cascada territorial cableada + `resolver_territorio`
    real (+ fix del diagnóstico de `t_victima`, redacción de `PRXP_TEXTORESPUESTA`).
  - `e57a99d` — `cargar_hogar_demo_oracle`, el escenario del Escalón 1.
  - `88cad0a` — este documento.
- **Todo en DRY-RUN.** La ruta `--confirmar` aborta a propósito hasta resolver los pendientes de negocio.
- **Tests:** 90/90 en `apps/sincronizacion`. La suite completa trae 7 fallos en
  `apps/formulario/tests/test_cargar_diccionario.py` que son **preexistentes**
  (verificado contra HEAD limpio), ajenos a este trabajo.
- Máquina de estados ejecuta ya los **cinco pasos**: HOGAR → PERSONA → MIEMBRO →
  TERRITORIO → RESPUESTA. Corrida real sobre un hogar: **10 pasos, todos DRY_RUN**.
  - **TERRITORIO resuelve ids REALES** contra el crosswalk (DT CENTRAL/TOLIMA/
    JORNADAS/ALVARADO → `id_dt=7, id_depto=30, id_pt=13, id_ma=32`). Único paso que
    sale **sin ningún pendiente**.
  - **RESPUESTA: el cruce ya resuelve a ids reales de Oracle.** `2/2` respuestas del
    demo limpias (`res=8` Zona/Cabecera, `res=69` Sexo/Mujer), con escribibilidad
    confirmada, y **`RXP_TIPOPREGUNTA` cableado** (`GE` para la de hogar, `IN` para la
    de persona). Ya **no** quedan `‹PEND:RES_IDRESPUESTA›`, `‹PEND:ESCRIBIBLE›` ni
    `‹PEND:RXP_TIPOPREGUNTA›`. Siguen marcados solo `PBANDERA` y `PPER_IDPREGUNTAPADRE`
    (+ `PPER_IDPERSONA` en las de nivel hogar), nunca inventados.
  - ⚠️ **El catálogo de respuestas cargado es PARCIAL** (temas 1-2): el export volvió
    truncado a 200 filas. El código lo sabe y lo declara — ver §3b-bis-C.2.
- Docs de análisis en `docs/oracle-legacy/` están **gitignored** por convención del equipo (menos `oracle-local-setup.md` y este archivo, que son traspaso/arquitectura sin datos de prod).

### 2.1 Lo que se aprendió del PL/SQL real (relevante para revisar)

- **La cascada territorial son 4 procedures y el ORDEN es obligatorio.** Solo el
  primero (`GIC_SP_OBDEPTOPORDT`) hace `INSERT` de la fila en
  `GIC_N_RELACION_DT_PUNTO`; los otros tres son `UPDATE ... WHERE hogarcodigo=X`.
  Un UPDATE sin fila **no es error** en Oracle: fuera de orden, el paso "pasaría"
  sin dejar territorio.
- **⚠️ Trampa de nombres confirmada:** `GIC_SP_OBTPUNTOATECION` recibe un parámetro
  formal llamado `Id_DT`, pero su cuerpo hace `SET iddeptoaten = Id_dt` y filtra
  `T.IDDEPARTAMENTO = pId_DT` (body 3140 y 3162). **Espera el id de DEPARTAMENTO,
  no el de la DT.** Pasarle la DT rompe el join de los reportes
  (`RL.IDDEPTOATEN = PA.IDDEPARTAMENTO`) — la forma exacta del bug histórico.
  Hay test de regresión para esto.
- **Son CUATRO ids, no tres.** El stub anterior devolvía `id_dt/id_pt/id_ma` y se
  comía `IDDEPTOATEN`, que es columna propia. Faltando una, el territorio queda
  incompleto.
- **El cruce debe ser por la FILA COMPLETA, no columna a columna.** Los nombres
  sueltos no son únicos: 68 municipios repiten nombre (BUENAVISTA tiene 4 ids) y
  `JORNADAS DE ATENCION Y/O FERIAS DE SERVICIO` existe con 39 ids (uno por DT).
  La tupla (dt, depto, punto, municipio) sí es única: **1370/1370, 0 ambiguas**.
- **`SP_SET_RESPUESTAS_DE_ENCUESTA` falla en silencio con ids desconocidos:** abre
  con `SELECT ... INTO` sobre `RES_IDRESPUESTA` y su `WHEN OTHERS` se traga el
  `NO_DATA_FOUND` ⇒ retorna sin excepción y sin escribir. Por eso los ids no se
  adivinan y la verificación por SELECT es obligatoria.

---

## 3. Qué falta (pendientes)

### 3a. Bloqueantes de NEGOCIO (los resuelve Javier con Oscar/UARIV — no los decido yo)
1. **Usuario/perfil de servicio SICAV en Oracle** → poner valor en `settings.ORACLE_LEGACY['USUARIO_SERVICIO_ID' / 'PERFIL_SERVICIO_ID']`.
2. **Mapeo P8** (campos vivos de `GIC_INSERT_PERSONAS`): `ID_SINIESTRO`→hecho/siniestro (`HechoVictima`), `ID_DECLAR`→declaración/FUD, `T_VICTIMA`→tipo de víctima.
3. **Tipo de documento PE (PEP) y NES** — sin equivalente en `GIC_TIPODOC`: ¿mapear a Otro(13)/Indocumentado(14) o pedir alta de catálogo?
4. **SISBEN** (N3): ¿SICAV usa el cruce `TEMP_SISBEN`?
5. **Rotar clave RNIENTREVISTA** (se usó para lectura/export).

**Nuevos, detectados al cablear RESPUESTA (bloquean ese paso por completo):**

6. ~~**`PINS_IDINSTRUMENTO`**~~ ✅ **RESUELTO** (Query B): `GIC_INSTRUMENTO` tiene una
   sola fila (1=`CARACTERIZACION`). Oracle no separa por instrumento como SICAV: no
   había crosswalk que resolver. Es la constante `INS_IDINSTRUMENTO_CARACTERIZACION`.
7. ~~**`PRES_IDRESPUESTA`**~~ ✅ **RESUELTO** — y la hipótesis era **falsa**:
   `id_resp_vivanto` **NO** es `RES_IDRESPUESTA` (refutado 0/14: Mujer es 4599 en SICAV
   y 69 en Oracle). El puente bueno es `Pregunta.id_preg == PRE_IDPREGUNTA` (14/14) +
   opción por texto normalizado dentro de la pregunta. Hay test de regresión para que
   no vuelva a colarse: escribir 4599 no habría dado error, simplemente no habría escrito.
8. **`PPER_IDPERSONA` de preguntas de nivel HOGAR** — en SICAV llegan con
   `miembro=NULL` y el procedure exige un NUMBER. La cascada territorial usa el
   literal `'1'` como "persona del hogar"; extrapolarlo sería suponer. ¿Qué manda
   ahí la app vieja?
9. **`PBANDERA`** — con valor 1 dispara `SP_BORRADORESPUESTAS`, que **BORRA** las
   respuestas previas del hogar/instrumento; con 0 solo inserta. Qué corresponde en
   una migración es decisión de negocio, y el lado destructivo no se asume.
10. ~~**`RXP_TIPOPREGUNTA`**~~ ✅ **RESUELTO CON DATO (2026-07-16) — y sin negocio.**
    `SELECT DISTINCT RXP_TIPOPREGUNTA` en prod → **`{GE, IN}`**: mismo dominio que
    `PRE_TIPOPREGUNTA`. No era el tipo de widget, era el **nivel** (GE=hogar,
    IN=persona). ⇒ No hay crosswalk: se **copia** el valor que Oracle ya tiene para esa
    pregunta. Cableado; el DRY-RUN ya no marca `‹PEND:RXP_TIPOPREGUNTA›`.
    ⚠️ Falta el control fila-a-fila (§3b-bis-E.4): el `DISTINCT` prueba el dominio,
    no que la app vieja escriba el `PRE_TIPOPREGUNTA` de SU pregunta. Barato y pendiente.
12. ~~**10 respuestas que Oracle ofrece pero no sabe guardar** (7 parentescos)~~
    ❌ **NO EXISTE — falsa alarma mía, cerrada por el manual antes de escalarla.**
    Las 10 huérfanas son opciones que el manual **no declara** y que SICAV **no ofrece**
    (10/10): filas muertas del catálogo de Oracle, no un agujero funcional. El manual
    (11-MU pág. 56) lista 6 opciones de parentesco y son exactamente las 6 escribibles.
    Ver §3b-bis-E.3 — **no llevar a Oscar.**
13. 🆕 **`Cédula de ciudadanía / Contraseña` con 4 ids escribibles** (pregunta 30).
    **El único de los dos "hallazgos" del 2026-07-16 que sobrevivió.** El manual declara
    la opción una vez ⇒ sobran ids, pero no dice cuál surrogate es el vigente (no es
    dato del manual). Pregunta concreta + consulta de apoyo en §3b-bis-E.1.

**Dato, no decisión — pero también bloquea:**

11. **El catálogo de puntos de atención de SICAV es un placeholder** y no cruza a
    Oracle. `cargar_puntos_atencion.py` lo dice en su propio docstring: carga 2
    puntos por DT (37 en total) hasta que UARIV entregue el oficial. Oracle tiene
    **266 puntos reales**. Medido: las **21/21 DT cruzan** y "JORNADAS…" cruza, pero
    de los 20 "Centro Regional X" **solo 13 existen en Oracle**; no existen Medellín,
    Cartagena, Bogotá, Barrancabermeja, Pasto, Mocoa ni Bucaramanga. "ATENCIÓN
    TELEFÓNICA" tampoco (Oracle usa "ESQUEMA NO PRESENCIAL BOGOTA D.C." y similares).
    ⇒ Con el catálogo actual, un hogar cuyo punto sea un Centro Regional de esos 7
    **falla al resolver** (con error claro, no con un id inventado). Hace falta el
    dataset oficial de UARIV o un crosswalk punto SICAV→Oracle.

### 3b. Incrementos TÉCNICOS
- ~~6. Cablear TERRITORIO + RESPUESTA~~ ✅ **hecho** (pendiente de tu revisión).
- ~~7. Resolver territorio desde el crosswalk~~ ✅ **hecho** (pendiente de tu revisión).
- ~~12. `MiembroHogar.tipo_victima` NO EXISTE y el `getattr(..., None)` lo enmascara~~
  ✅ **corregido**: ahora lanza `CampoOrigenFaltante` nombrando el campo, y en dry-run
  el marcador dice la causa real (`‹PEND:T_VICTIMA(MiembroHogar SIN campo
  tipo_victima)›` en vez del engañoso `‹PEND:TIPO_VICTIMA(None)›`). Ojo: **esto solo
  arregla el diagnóstico**. Siguen abiertos, encadenados: (a) el campo no existe en el
  modelo — ¿se añade o el dato sale de otro lado?; (b) aunque existiera, el mapeo de
  T_VICTIMA sigue pendiente (3a.2, P8, Oscar).

### 3b-bis-A. RESULTADOS de las consultas (2026-07-16) — dos veredictos

Javier corrió las consultas. Lo que cambió:

**❌ REFUTADA — `id_resp_vivanto` NO es `RES_IDRESPUESTA`.** Cero de 14 coinciden:
Mujer es 4599 en SICAV y **69** en Oracle; Indígena 4565 vs **112**; Heterosexual
4602 vs **2351**; Cabecera municipal 4572 vs **8**. Haberla asumido habría escrito
ids ajenos —y como el procedure traga el `NO_DATA_FOUND`, sin error visible—.
Hay test de regresión (`test_no_usa_id_resp_vivanto`).

**✅ CONFIRMADO — el puente ya existía: `Pregunta.id_preg` == `PRE_IDPREGUNTA`.**
14/14 ids del volcado existen en SICAV y, comparando el texto de la pregunta, **52 de
59 coinciden** (39 idénticos tras normalizar + 13 compatibles). Ej.: `id_preg=5` →
'ZONA DE RESIDENCIA' en ambos lados; `id_preg=35` (Z4) → la de autorreconocimiento
étnico. ⇒ Las preguntas **no** se cruzan por texto: se cruzan por id. Solo las
**opciones** se cruzan por texto, y acotadas a su pregunta (2-14 candidatas).

**Query B — hay UN solo instrumento:** `GIC_INSTRUMENTO` = 1 fila, `1 =
'CARACTERIZACION'` (activo desde 2013-10-18). Oracle no modela el cuestionario por
instrumento como SICAV (que tiene 8): todo cuelga de ese id. ⇒ `INS_IDINSTRUMENTO`
deja de ser pendiente y pasa a **constante**. El `= 1` del WHERE nunca fue circular.

**Query C1 — dominio `'SI'`/`'NO'`**: la suposición original era correcta.

**Query C2 — 153 respuestas huérfanas** (sin fila en `GIC_N_INSTRUMENTOXRESP`): el
riesgo de NO_DATA_FOUND es real y medido. ⚠️ **Tenemos el CONTEO pero no la LISTA**,
así que todavía no se pueden excluir: ver 3b-bis-C.

**Query C3 — 0 y 0**: no hay preguntas ni respuestas en varios instrumentos ⇒ el
riesgo de TOO_MANY_ROWS por esa causa no existe (coherente con haber un instrumento).

### 3b-bis-B. Lo que YA quedó implementado (sin commitear, a revisión)

- `respuestas_oracle.json` — catálogo del volcado, **regenerado desde la Query A v2**
  (62 preguntas / 200 respuestas), ahora con `escribible` por fila y `pre_tipopregunta`.
  Export crudo versionado en `docs/oracle-legacy/query_a_v2_parcial_temas_1_2.tsv`.
- `resolver_ins_idinstrumento` → constante 1.
- `resolver_res_idrespuesta` → `id_preg`→`PRE_IDPREGUNTA`, luego opción por texto
  normalizado **dentro de esa pregunta**; error claro y accionable si no cruza.
- Escenario demo alineado al catálogo real (`DEMO_SEXO` id_preg=24 → 69;
  `DEMO_ZONA` id_preg=5 → 8), y el comando **verifica el cruce** y aborta si se rompe.
- 90/90 tests en `apps/sincronizacion`.

**Estado del DRY-RUN de `LISTO-96001` (2026-07-16, corrida limpia de 10 pasos):**

| | |
|---|---|
| Respuestas que resuelven **limpio** | **2/2** — `res=8` (Zona/Cabecera), `res=69` (Sexo/Mujer) |
| Respuestas pendientes de curaduría | **0** |
| `‹PEND:RES_IDRESPUESTA›` / `‹PEND:ESCRIBIBLE›` | **0** — desaparecieron los dos |
| Paso TERRITORIO | **LIMPIO** (único paso sin ningún pendiente) |

Los `‹PEND›` que siguen en el paso RESPUESTA **no son del resolver**: son
`RXP_TIPOPREGUNTA`, `PBANDERA`, `PPER_IDPREGUNTAPADRE` y `PPER_IDPERSONA(nivel_hogar)`
— los bloqueantes de negocio 3a.6-3a.11, intactos.

### 3b-bis-C. Lo que FALTA para cerrar RESPUESTA

1. ~~La LISTA de las 153 huérfanas~~ ✅ **RESUELTO** por la columna `ESCRIBIBLE` de la
   Query A v2. De las filas exportadas ya se **sabe** (no se supone) qué se puede
   escribir: 10 huérfanas identificadas. `escribibilidad_verificada: true`.
2. **El catálogo completo — SIGUE PENDIENTE, es lo único que bloquea.** El export v2
   volvió a llegar **truncado en exactamente 200 filas** (201 con cabecera): ese número
   redondo es la firma del cliente SQL cortando, no el final del instrumento. Cubre
   temas 1-2 (62 preguntas, hasta la 1158 / `IXP_ORDEN` 41) de un cuestionario que en
   SICAV tiene **290 preguntas con `id_preg`**.
   → **Reexportar a archivo** (`SPOOL` en SQL*Plus, o "export to file" en el cliente),
   no a la rejilla de resultados. El SQL de 3b-bis-D no lleva límite: el corte es del
   cliente.
   → El código ya convive con esto sin mentir: `_meta.completo: false`, y una pregunta
   ausente produce *"no está en el volcado — y eso NO quiere decir que no exista en
   Oracle"*, nunca *"no existe"*. Cuando llegue el export completo, `completo` pasa a
   `true` y el mensaje cambia solo.
3. **Curaduría manual** (no se resuelven con código, ver 3b-bis-E).

### 3b-bis-D. Query A v2 — catálogo + escribibilidad en una sola pasada

**Estado: CORRIDA el 2026-07-16, pero el export llegó truncado a 200 filas ⇒ hay que
REEXPORTARLA A ARCHIVO.** Lo que trajo funcionó (resultado crudo en
`docs/oracle-legacy/query_a_v2_parcial_temas_1_2.tsv`, cargado en el catálogo): la
columna `ESCRIBIBLE` cerró el pendiente de las huérfanas y `PRE_TIPOPREGUNTA` destapó
el hallazgo GE/IN de 3b-bis-E.4. Solo falta que no la corte el cliente.

> **El SQL no lleva `LIMIT` ni `ROWNUM`: el corte es del cliente.** Exportar **a
> archivo** (`SPOOL` en SQL*Plus, o "export to file" / "fetch all rows" en el cliente
> gráfico), no a la rejilla de resultados. Señal de que volvió a pasar: el archivo
> tiene exactamente 200 filas de datos y termina en la pregunta 1158.

`ESCRIBIBLE` marca lo que la Query C2 solo contaba, y `PRE_TIPOPREGUNTA` es candidato
a resolver `RXP_TIPOPREGUNTA` (3a.10).
**Sin `WHERE INS_IDINSTRUMENTO` ni límite de filas** (solo hay un instrumento).

```sql
SELECT
  ip.INS_IDINSTRUMENTO,
  ip.TEM_IDTEMA,
  ip.IXP_ORDEN,
  ip.PRE_TIPOPREGUNTA,
  pr.PRE_IDPREGUNTA,
  pr.PRE_PREGUNTA,
  re.RES_IDRESPUESTA,
  re.RES_RESPUESTA,
  re.RES_ACTIVA,
  CASE WHEN EXISTS (SELECT 1 FROM GIC_N_INSTRUMENTOXRESP ir
                    WHERE ir.RES_IDRESPUESTA = re.RES_IDRESPUESTA)
       THEN 'SI' ELSE 'NO' END AS ESCRIBIBLE
FROM GIC_N_INSTRUMENTOXPREG ip
JOIN GIC_N_PREGUNTAS pr ON pr.PRE_IDPREGUNTA = ip.PRE_IDPREGUNTA
JOIN GIC_N_RESPUESTAS re ON re.PRE_IDPREGUNTA = pr.PRE_IDPREGUNTA
WHERE re.RES_ACTIVA = 'SI'
ORDER BY ip.TEM_IDTEMA, ip.IXP_ORDEN, re.RES_IDRESPUESTA;
```

Con el resultado (ya hecho para la parte que llegó): se regenera `respuestas_oracle.json`
con `escribibilidad_verificada: true` + `escribible` por fila, y el DRY-RUN muestra
`pres_idrespuesta` limpio. Reproducible con el conversor
`scratchpad/tsv_a_catalogo_v2.py` (apuntarlo al TSV nuevo y volver a correr).

### 3b-bis-E. Casos de curaduría — **la autoridad es el MANUAL OFICIAL**

> 📌 **Regla del proyecto:** lo funcional (qué preguntas hay, qué opciones, con qué
> texto) lo decide el **manual oficial**, no el criterio de nadie: `11-MU` para
> Territorial y Étnicos, `14-MU` para Asistencia (`docs/perfiles/`, gitignored).
> A Oscar solo lo que el manual no cubra. Antes de marcar algo "pendiente de
> negocio", **mirar el manual primero**.

1. **`Cédula de ciudadanía / Contraseña` con 4 ids** (`93, 3852, 3853, 3854`) en la
   pregunta 30 — **sigue siendo decisión de negocio. Mi predicción falló.**

   > ⚠️ **Aquí decía que el filtro de escribibilidad iba a disolverlo solo.** La
   > hipótesis era que `3852-3854` serían huérfanas y que al descartarlas quedaría
   > `93`. La Query A v2 la **refutó**: los **4 ids están marcados `ESCRIBIBLE=SI`**.
   > El filtro no desempata nada aquí. Se deja escrito porque la teoría era mía y el
   > dato dijo que no; el test `test_el_filtro_de_escribibilidad_disuelve_la_falsa_
   > ambiguedad` se borró (fingía con `monkeypatch` unas huérfanas que no existen) y
   > lo sustituye `test_los_4_ids_de_cedula_son_todos_escribibles`, que fija el dato real.

   Dónde queda, aplicando la escalera:
   - **Peldaño 2 (escribibilidad):** no resuelve — los 4 son escribibles.
   - **Peldaño 3 (manual):** el 11-MU (B6) declara la opción **una sola vez**, y su
     lista de 11 opciones calza exacto con `93-96` + `3799-3805`. ⇒ Confirma que
     **sobran ids**… pero el manual habla de opciones funcionales, no de surrogates:
     **no dice cuál de los 4 es el vigente**. No puede: ese dato no es del manual.
   - **Peldaño 4 (Oscar):** ⇒ **aquí queda.** Es la pregunta exacta a llevarle:
     *"Oracle repite 'Cédula de ciudadanía / Contraseña' con 4 ids escribibles en la
     pregunta 30 y el manual declara la opción una sola vez. ¿Cuál id usamos?"*

   **USO REAL MEDIDO EN PROD (2026-07-16)** — y el resultado **no** es el que esperaba:

   | RES_IDRESPUESTA | usos | lectura |
   |---:|---:|---|
   | **93** | **29.338** | el mayoritario |
   | **3854** | **8.620** | ⚠️ **volumen real — NO es ruido** |
   | 3852 | 19 | ruido (error de captura / duplicado de catálogo) |
   | 3853 | 15 | ruido |

   **Esto es lo que impide resolverlo por código, y es la razón de que siga abierto.**
   Con 3852/3853 no hay discusión: 19 y 15 usos contra 29.338 es ruido. Pero **3854
   tiene 8.620 usos: hay algo real detrás.** Un id con ese volumen no es un duplicado
   accidental — responde a *algo* (¿un período distinto? ¿otro canal de captura?
   ¿una migración pasada? ¿un perfil concreto?). Elegir 93 "porque es el mayoritario"
   sería exactamente la suposición que este proyecto no se permite: si 3854 significa
   algo, mandar 93 en su lugar escribiría mal 8.620 casos… en silencio.

   ⇒ **Pendiente de negocio (3a.13). La pregunta exacta para Oscar:**
   > *"En la pregunta 30 (tipo de documento), Oracle tiene 4 ids escribibles con el
   > texto 'Cédula de ciudadanía / Contraseña' y el manual declara la opción una sola
   > vez. El uso real es 93 → 29.338, **3854 → 8.620**, 3852 → 19, 3853 → 15. Los dos
   > pequeños son claramente ruido. **¿Qué representa el 3854, que tiene volumen
   > significativo — un período distinto, otro canal de captura, una migración
   > anterior?** ¿Cuál debe usar SICAV al escribir?"*

   El resolver **NO** lo resuelve: sigue fallando con las 4 candidatas a la vista.
   Es lo correcto hasta que Oscar diga qué es 3854.

   *(SQL usado, verificado contra el esquema real — la columna de fecha es
   `USU_FECHACREACION`, no `RXP_FECHACREACION`, que fue mi primera suposición y no
   existe:)*

   ```sql
   SELECT RES_IDRESPUESTA, COUNT(*) AS USOS,
          MIN(USU_FECHACREACION) AS PRIMERO, MAX(USU_FECHACREACION) AS ULTIMO
   FROM GIC_N_RESPUESTASENCUESTA
   WHERE RES_IDRESPUESTA IN (93, 3852, 3853, 3854)
   GROUP BY RES_IDRESPUESTA ORDER BY USOS DESC;
   ```

   **Pista barata para la reunión:** las columnas `PRIMERO`/`ULTIMO` de esa misma
   consulta probablemente ya expliquen el 3854 (si sus fechas no se solapan con las de
   93, es un período/migración; si se solapan, es un canal paralelo). Mirar eso antes
   de la reunión puede convertir la pregunta en una confirmación.

2. **Los textos de opción divergen entre SICAV y Oracle** — no es cosa de acentos, y
   por eso no se aplica *fuzzy matching* (elegiría mal en silencio):

   | SICAV | Oracle |
   |---|---|
   | `Palenquero(a)` | `Palenquero (a)` |
   | `Rural disperso (vereda)` | `Parte rural disperso (vereda, campo)` |
   | `Negro(a), afrocolombiano(a)` | `Negro(a), afrocolombiano(a) o afrodescendiente` |

   Con territorio tuvimos suerte (21/21 DT idénticas). Aquí hace falta un crosswalk
   curado opción-a-opción **contra el texto del manual**, que es el que dice cuál es
   la redacción oficial y, por tanto, si las dos variantes son la misma opción. El
   resolver ya falla listando las candidatas reales de la pregunta, así que la
   curaduría se hace con los datos a la vista.

3. **🆕 Las 10 huérfanas del volcado: NO son un defecto — falsa alarma, cerrada por el
   manual.** ⚠️ **Esto estuvo a punto de escalarse a Oscar como "defecto activo de
   producción con prioridad". Habría sido un error.** Se deja documentado el episodio
   completo porque el mecanismo de la falsa alarma es instructivo.

   **Lo que parecía:** 10 respuestas sin fila en `GIC_N_INSTRUMENTOXRESP` ⇒ el
   procedure las traga con `NO_DATA_FOUND` y no escribe nada sin avisar. **7 de las 13
   opciones de parentesco (pregunta 28)** entre ellas: `Nieto(a)`, `Yerno o nuera`,
   `Abuelo(a)`, `Suegro(a)`, `Tío(a)`, `Sobrino(a)`, `Otros no parientes`. Leído así,
   un hogar extenso no podría registrar el parentesco de sus miembros — grave, y en un
   censo de víctimas los hogares extensos son lo normal.

   **Lo que dice el manual** (11-MU pág. 56, *"El parentesco … frente al jefe del hogar
   es:"*): lista **exactamente 6 opciones** — Jefe(a), Cónyuge o Compañera(o),
   Hijo(a)-Hijastro(a), Padre o madre-Padrastro o madrastra, Hermano(a)-Hermanastro(a),
   **Otro pariente del jefe**. Las 7 "huérfanas" **no están en el manual**: son
   categorías que se absorbieron en *"otro pariente del jefe"*.

   **Los tres lados coinciden:**

   | | opciones de la pregunta 28 |
   |---|---|
   | Manual 11-MU (pág. 56) | **6** |
   | SICAV (`formulario.OpcionRespuesta`) | **6** — las mismas |
   | Oracle **escribibles** | **6** — las mismas (`79, 80, 81, 84, 906, 912`) |
   | Oracle huérfanas | 7 — las que el manual no declara |

   Verificado además **10/10: SICAV no ofrece NINGUNA de las 10 huérfanas** (tampoco
   `No sabe/no informa`, `En trámite` ni `Porque nació así`).
   ⇒ **No hay defecto, ni pérdida de datos, ni nada que escalar.** La escribibilidad de
   Oracle **implementa el manual**: es el mecanismo con que retira opciones que dejaron
   de ser oficiales, igual que los 3 ids de más de Cédula. Filas muertas de catálogo.

   **Dato que descarta la otra hipótesis:** la pregunta 1435 (*"…frente a la persona
   responsable del hogar"*, 6 opciones, todas escribibles) **no es la sustituta** de la
   28 — el manual (B24) dice que *"solo se habilita para el perfil Buenaventura"*.

   **Lo que sí queda, y es útil:** el guard sigue fallando ruidosamente, pero ahora
   apunta a donde toca. Si algún día SICAV manda una huérfana, el hallazgo no es sobre
   Oracle: es que **el instrumento de SICAV se desvió del manual**. El filtro es, de
   hecho, un **detector de deriva SICAV↔manual** gratis.

   **La lección del episodio** (por eso se conserva escrito): tenía el mecanismo bien
   —el `NO_DATA_FOUND` tragado es real y está verificado en el PL/SQL— y aun así la
   conclusión era falsa, porque nunca comprobé si alguien llega a mandar esas opciones.
   *Un fallo silencioso en una ruta que nadie recorre no es un fallo.* La regla del
   proyecto (**mirar el manual ANTES de escalar**) es justo lo que lo atajó.
   ⚠️ Con el export completo saldrán las otras ~143 huérfanas: **el default es que
   sean lo mismo** (opciones retiradas). Antes de alarmarse por ninguna, cotejarla
   contra el manual y contra lo que SICAV ofrece.

4. **🆕 `PRE_TIPOPREGUNTA` es el NIVEL, no el tipo — pista fuerte para 3a.10.**
   Vale `GE`/`IN`. Pese al nombre no es el widget (radio/texto): cruzando las 62
   preguntas del volcado contra `Pregunta.nivel` de SICAV —que se llenó aparte,
   leyendo el manual— concuerdan **61 de 63**:

   | Oracle | SICAV | n |
   |---|---|---|
   | `GE` | HOGAR | 18 |
   | `IN` | PERSONA | 43 |
   | `IN` | HOGAR | **2** ← |

   Y **las 2 excepciones refuerzan la lectura en vez de romperla: en las dos, Oracle
   tiene razón y el que está mal es SICAV.** Consultado el manual (regla del proyecto):
   - **Pregunta 8 — Celular.** 11-MU pág. 45, **A11**, textual: *"Campo abierto.
     Numérico. **Se habilita para cada una de las personas del hogar.**"* ⇒ es PERSONA.
     Oracle dice `IN` ✅. SICAV lo tiene en HOGAR ❌ — **defecto de SICAV**.
   - **Pregunta 35 — Autorreconocimiento étnico.** El manual (A4, pág. 42) **no
     declara el nivel de forma literal** en esa página; lo que hay es el pendiente
     funcional ya registrado del 24-jun ("pertenencia étnica **por persona**") y el
     propio texto de A4, dirigido a un individuo. ⇒ **Corrobora a Oracle (`IN`), pero
     con evidencia más floja que A11**: no lo doy por cerrado igual que el celular.

   **Por qué NO se cableó todavía:** falta probar que `RXP_TIPOPREGUNTA` (el bind del
   procedure) comparta dominio con `PRE_TIPOPREGUNTA`. Los nombres se parecen y sería
   el origen natural del dato — pero *"se parece"* no es evidencia, y ya nos mordió
   una vez (`id_resp_vivanto` también se parecía). **Un renglón lo cierra:**

   ```sql
   SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA ORDER BY 1;
   ```

   Si sale `{GE, IN}`, el pendiente **3a.10 se resuelve sin crosswalk y sin negocio**:
   se copia el valor que el propio Oracle ya tiene para esa pregunta, y el DRY-RUN
   pierde el `‹PEND:RXP_TIPOPREGUNTA(RADIO)›` (ese `RADIO` de ahora es el widget de
   SICAV: dominio equivocado, no lo mandes así).

   **Control que lo prueba de verdad** (que salga `{GE, IN}` es necesario pero no
   suficiente: hay que ver que el valor escrito coincida con el nivel de SU pregunta).
   Si la diagonal `GE/GE` + `IN/IN` concentra casi todo, está probado; si está
   repartido, la corazonada era falsa y no se cablea:

   ```sql
   SELECT re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA, COUNT(*) AS N
   FROM GIC_N_RESPUESTASENCUESTA re
   JOIN GIC_N_RESPUESTAS rs ON rs.RES_IDRESPUESTA = re.RES_IDRESPUESTA
   JOIN GIC_N_INSTRUMENTOXPREG ip ON ip.PRE_IDPREGUNTA = rs.PRE_IDPREGUNTA
   GROUP BY re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA ORDER BY N DESC;
   ```

   *(Los 3 SQL de esta sección parsean contra el esquema real — validados en el Oracle
   local, que tiene la estructura de prod.)*

   **Regalo aparte:** esto detectó **2 defectos en el instrumento de SICAV** (preguntas
   8 y 35 con `nivel` equivocado). No es de esta migración — va a la lista del
   instrumento territorial.

### 3b-bis. Contexto original — desbloquear RESPUESTA con datos reales de Oracle

Es **el** incremento técnico que queda, y no arranca sin dato: hoy el paso RESPUESTA
escribe `‹PEND:...›` en `PRES_IDRESPUESTA`, `PINS_IDINSTRUMENTO` y
`PRXP_TIPOPREGUNTA` porque SICAV no tiene los ids de Oracle (3a.6, 3a.7, 3a.10).
El plan es el mismo que funcionó con territorio: traer el catálogo real y **cruzar
por nombre/significado, nunca por id** (los ids de Oracle son surrogate).

#### Paso 1 — Javier corre estos SELECT contra prod (solo lectura, sin PII) y pega el resultado

**Query A — catálogo de respuestas del instrumento** (la consulta base):

```sql
-- Catálogo de respuestas del instrumento, con texto de pregunta para
-- poder cruzar por nombre/significado (igual que se hizo con territorio)
SELECT
  ip.INS_IDINSTRUMENTO,
  ip.TEM_IDTEMA,
  pr.PRE_IDPREGUNTA,
  pr.PRE_PREGUNTA,
  re.RES_IDRESPUESTA,
  re.RES_RESPUESTA,
  re.RES_ACTIVA
FROM GIC_N_INSTRUMENTOXPREG ip
JOIN GIC_N_PREGUNTAS pr ON pr.PRE_IDPREGUNTA = ip.PRE_IDPREGUNTA
JOIN GIC_N_RESPUESTAS re ON re.PRE_IDPREGUNTA = pr.PRE_IDPREGUNTA
WHERE ip.INS_IDINSTRUMENTO = 1  -- ajustar al instrumento real (ver Query B)
  AND re.RES_ACTIVA = 'SI'
ORDER BY ip.TEM_IDTEMA, ip.IXP_ORDEN, re.RES_IDRESPUESTA;
```

> ✅ **Verificada contra el esquema real** (Oracle local, `user_tab_columns`,
> 2026-07-16): las 3 tablas y las 7 columnas existen con esos nombres exactos.
> La consulta corre tal cual.
>
> ⚠️ Dos ajustes que conviene hacer **antes** de correrla:
> - **`INS_IDINSTRUMENTO = 1` es circular**: ese id es justo lo que buscamos (3a.6).
>   Correr primero la Query B para elegirlo. Ojo: el catálogo se llama
>   **`GIC_INSTRUMENTO`**, sin el `_N` (`GIC_N_INSTRUMENTO` NO existe).
> - **`RES_ACTIVA = 'SI'` es una suposición sobre el dominio.** La columna es
>   `NVARCHAR2(4)` y **no tiene CHECK** que la acote (verificado), así que podría ser
>   `'S'`/`'N'` y el filtro devolvería 0 filas — pareciendo "catálogo vacío" en vez de
>   "filtro mal". Sacar el filtro en la primera corrida, o mirar el
>   `SELECT DISTINCT RES_ACTIVA FROM GIC_N_RESPUESTAS;` de la Query C.

**Query B — instrumentos disponibles** (rompe la circularidad y da el cruce por nombre
contra `formulario.Instrumento` de SICAV):

```sql
SELECT INS_IDINSTRUMENTO, INS_NOMBREINSTRUMENTO, INS_ACTIVO,
       INS_FECHAINICIO, INS_FECHAFIN
FROM GIC_INSTRUMENTO
ORDER BY INS_IDINSTRUMENTO;
```

**Query C — chequeos de los dos fallos SILENCIOSOS del procedure** (esto es lo que
decide qué respuestas son escribibles de verdad — ver la explicación abajo):

```sql
-- C1. Dominio real de las banderas (¿'SI'/'NO'? ¿'S'/'N'?)
SELECT DISTINCT RES_ACTIVA FROM GIC_N_RESPUESTAS;

-- C2. NO_DATA_FOUND: respuestas SIN fila en GIC_N_INSTRUMENTOXRESP.
--     El procedure hace SELECT ... INTO sobre esa tabla ⇒ si no hay fila,
--     no escribe NADA y no avisa.
SELECT COUNT(*) AS respuestas_sin_instrumentoxresp
FROM GIC_N_RESPUESTAS re
WHERE NOT EXISTS (SELECT 1 FROM GIC_N_INSTRUMENTOXRESP ir
                  WHERE ir.RES_IDRESPUESTA = re.RES_IDRESPUESTA);

-- C3. TOO_MANY_ROWS: preguntas que viven en MÁS DE UN instrumento, y
--     respuestas registradas para más de un instrumento. Ambos rompen los
--     SELECT ... INTO del procedure, también en silencio.
SELECT COUNT(*) AS preguntas_en_varios_instrumentos FROM (
  SELECT PRE_IDPREGUNTA FROM GIC_N_INSTRUMENTOXPREG
  GROUP BY PRE_IDPREGUNTA HAVING COUNT(DISTINCT INS_IDINSTRUMENTO) > 1);

SELECT COUNT(*) AS respuestas_en_varios_instrumentos FROM (
  SELECT RES_IDRESPUESTA FROM GIC_N_INSTRUMENTOXRESP
  GROUP BY RES_IDRESPUESTA HAVING COUNT(DISTINCT INS_IDINSTRUMENTO) > 1);
```

**Opcional pero útil — Query D:** `GIC_N_INSTRUMENTOXPREG.TEM_IDTEMA` referencia
**`GIC_TEMA`** (singular; `GIC_TEMAS` en plural es otra cosa, metadata de cruces de
reporte). El "tema" es el equivalente del **Capítulo** de SICAV, así que traer su
nombre permite cruzar también ese nivel:

```sql
SELECT TEM_IDTEMA, TEM_NOMBRETEMA, TEM_ACTIVO, TEM_ORDEN
FROM GIC_TEMA ORDER BY TEM_ORDEN;
```

`GIC_N_INSTRUMENTOXRESP` además trae `RES_ORDENRESPUESTA`, `RES_OBLIGATORIO` y
**`RES_FINALIZA`** — que es exactamente el `OpcionRespuesta.finaliza_capitulo` de
SICAV (el viejo RESFINALIZA del APK). Sirve como verificación cruzada del mapeo.

#### Por qué las Query C importan (los dos fallos silenciosos)

`SP_SET_RESPUESTAS_DE_ENCUESTA` abre con **dos `SELECT ... INTO` sin filtrar por
instrumento** (body líneas 23-29):

```sql
SELECT PR.IXP_ORDEN INTO pOrden FROM GIC_N_INSTRUMENTOXPREG PR
JOIN GIC_N_RESPUESTAS RE ON RE.PRE_IDPREGUNTA = PR.PRE_IDPREGUNTA
WHERE RE.RES_IDRESPUESTA = pres_IdRespuesta;          -- sin AND INS_IDINSTRUMENTO

SELECT COALESCE(VAL_IDVALIDADOR,0), VAL_IDVALIDADOR_DEF INTO pValidador, textVal
FROM GIC_N_INSTRUMENTOXRESP WHERE RES_IDRESPUESTA = pres_IdRespuesta;
```

Como el `EXCEPTION WHEN OTHERS` del procedure se traga todo, hay dos formas de que la
escritura **no ocurra y nadie se entere**:
- **NO_DATA_FOUND** — la respuesta no tiene fila en `GIC_N_INSTRUMENTOXRESP` (C2).
- **TOO_MANY_ROWS** — la pregunta está en más de un instrumento, o la respuesta está
  registrada para varios: el `SELECT INTO` recibe 2+ filas y revienta (C3).

⇒ **No todo `RES_IDRESPUESTA` es escribible.** Si C2/C3 dan > 0, el resolver tendrá
que excluir esos casos explícitamente en vez de confiar en que el procedure avise.
Mejor descubrirlo en el SELECT que con el hogar a medio escribir.

#### Paso 2 — Con el resultado pegado, yo hago (sigue en DRY-RUN, sin commitear)

1. **Resolver de respuestas** en `ResolverCatalogos`: cruce **por texto** de
   pregunta/respuesta contra `formulario.Pregunta` / `formulario.OpcionRespuesta`,
   con la misma normalización que territorio (mayúsculas, acentos, espacios) y el
   mismo criterio: si no hay match, **error claro**, nunca un id inventado.
   Se aprovechará para **contrastar la hipótesis `id_resp_vivanto == RES_IDRESPUESTA`**
   (3a.7): si el cruce por texto coincide con el `id_resp_vivanto` que ya trae SICAV,
   queda confirmada; si no, gana el texto y lo reportamos.
2. **Cablear** ese resolver en `paso_respuesta` de `escritor.py`, quitando los
   `‹PEND:›` que hoy tapan `PRES_IDRESPUESTA` / `PINS_IDINSTRUMENTO` /
   `PRXP_TIPOPREGUNTA`.
3. **Tests** del resolver (incluidos los casos de C2/C3 si aparecen) + re-correr
   `escribir_a_oracle --hogar LISTO-96001` en DRY-RUN con los **10 pasos y sin ningún
   `‹PEND:RESPUESTA...›`**.
4. **Ajustar `cargar_hogar_demo_oracle`** si hace falta: hoy siembra el primer
   `Instrumento` activo de SICAV y dos preguntas demo (`DEMO_SEXO`, `DEMO_ZONA`) con
   `id_resp_vivanto` 4599/4572. Si el instrumento real de Oracle no las tiene, el
   escenario debe sembrar preguntas que **sí** existan en el catálogo, o el Escalón 1
   no probaría nada.

**Lo que seguirá pendiente aunque llegue este SELECT** (no lo desbloquea): `PBANDERA`
(3a.9), `PPER_IDPERSONA` de nivel hogar (3a.8), usuario/perfil de servicio (3a.1) y
`T_VICTIMA` (3a.2). Sin esos cuatro, `--confirmar` sigue bloqueado aunque RESPUESTA
resuelva sus ids.
- 13. **Territorio con varias sesiones** — `GIC_N_RELACION_DT_PUNTO` admite **una sola
  fila por hogar** (PK `hogarcodigo`+`idpersona='1'`). El escritor toma la PRIMERA
  sesión. Si un hogar puede tener sesiones con territorios distintos, Oracle solo
  guarda uno: confirmar si ese caso existe.

### 3c. Después (no ahora)
- Escalón 1 del rollout: 1 hogar contra Oracle **local** con `--confirmar` (requiere ResolverCatalogos completo + tu aprobación).
- Etapa B (escritura directa Django) — fase separada, cuando se retire la app vieja.

---

## 3d. 🌅 MAÑANA (17-jul) — lista corta, en orden

**1. El re-export completo** (lo único que bloquea de verdad). Con `SPOOL`, no la
grilla. Al llegar:
```
python manage.py generar_catalogo_respuestas <tsv> --fecha 2026-07-17
```
Si el comando NO avisa de truncado y dice `cobertura: COMPLETO`, está bien.

**2. Tres consultas de un renglón, ya validadas contra el esquema real.** Las dos
primeras pueden **cerrar pendientes de negocio sin reunión**:

```sql
-- (a) 3a.8: ¿qué PER_IDPERSONA usa Oracle en las respuestas de nivel HOGAR?
--     Ahora que sabemos que GE = hogar, esto se MIDE en vez de preguntarse.
--     Si sale un valor convencional (p.ej. siempre la persona 1 del hogar), 3a.8 cae.
SELECT PER_IDPERSONA, COUNT(*) AS N FROM GIC_N_RESPUESTASENCUESTA
WHERE RXP_TIPOPREGUNTA = 'GE' GROUP BY PER_IDPERSONA
ORDER BY N DESC FETCH FIRST 10 ROWS ONLY;

-- (b) 3a.9 (PBANDERA): ¿Oracle guarda UNA respuesta por hogar+pregunta, o varias?
--     Si es siempre 1, la app vieja borra antes de insertar (PBANDERA=1) y lo sabemos
--     sin arriesgar el lado destructivo. Si hay N>1, acumula (PBANDERA=0).
SELECT N_POR_PREGUNTA, COUNT(*) AS HOGARES FROM (
  SELECT re.HOG_CODIGO, rs.PRE_IDPREGUNTA, COUNT(*) AS N_POR_PREGUNTA
  FROM GIC_N_RESPUESTASENCUESTA re
  JOIN GIC_N_RESPUESTAS rs ON rs.RES_IDRESPUESTA = re.RES_IDRESPUESTA
  GROUP BY re.HOG_CODIGO, rs.PRE_IDPREGUNTA)
GROUP BY N_POR_PREGUNTA ORDER BY N_POR_PREGUNTA;

-- (c) Control pendiente de RXP_TIPOPREGUNTA (§3b-bis-E.4): el DISTINCT probó el
--     dominio, esto prueba la correspondencia fila a fila. Si la diagonal GE/GE + IN/IN
--     no concentra casi todo, hay que descablearlo.
SELECT re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA, COUNT(*) AS N
FROM GIC_N_RESPUESTASENCUESTA re
JOIN GIC_N_RESPUESTAS rs ON rs.RES_IDRESPUESTA = re.RES_IDRESPUESTA
JOIN GIC_N_INSTRUMENTOXPREG ip ON ip.PRE_IDPREGUNTA = rs.PRE_IDPREGUNTA
GROUP BY re.RXP_TIPOPREGUNTA, ip.PRE_TIPOPREGUNTA ORDER BY N DESC;
```

**3. Para la reunión con Oscar** — solo lo que el manual no puede responder:
- **3a.13 Cédula:** *¿qué representa el id 3854 (8.620 usos)?* Llevar los 4 números.
  Truco: las fechas `PRIMERO`/`ULTIMO` de la consulta de §3b-bis-E.1 puede que ya lo
  expliquen solas ⇒ mirarlas antes y convertir la pregunta en una confirmación.
- **3a.5 rotar la clave de RNIENTREVISTA** (con OTI). Es el pendiente más viejo.
- **3a.11 catálogo oficial de puntos de atención** (7 Centros Regionales de SICAV no
  existen en Oracle).
- 3a.2 (mapeo P8) y 3a.3 (PE/NES).

**4. Commitear** lo de julio cuando lo revises (hoy quedó todo sin commitear a
propósito).

**Lo que NO hay que hacer mañana:** escalar lo de las 7 opciones de parentesco. Es
falsa alarma cerrada (§3b-bis-E.3).

---

## 4. Con qué EMPEZAR la próxima sesión (recomendación)

**El resolver de respuestas ya está y funciona** (2/2 del demo a ids reales). Lo que
queda no lo desbloquea el código:

1. **Reexportar la Query A v2 SIN que la corte el cliente** (§3b-bis-D). Es lo más
   barato y lo que más destraba: da el catálogo de los ~228 preguntas que faltan, la
   lista completa de huérfanas (van 10 de 153) y el resto de casos de curaduría.
   **A archivo, no a la rejilla.** Luego:
   `python manage.py generar_catalogo_respuestas <tsv> --fecha <YYYY-MM-DD>` y listo.
2. **Dos consultas de un renglón que pueden cerrar pendientes enteros** (solo lectura):
   - `SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA;` → si sale
     `{GE, IN}`, **3a.10 se resuelve sin negocio** (§3b-bis-E.4).
   - El conteo de usos de los 4 ids de Cédula (§3b-bis-E.1) → convierte la pregunta a
     Oscar en un dato, no en una opinión.
   Ojo: la clave de RNIENTREVISTA **está pendiente de rotar** (3a.5); coordinar.
3. **Con Oscar** (lo que el manual no cubre): 3a.8 (`PPER_IDPERSONA` nivel hogar),
   3a.9 (`PBANDERA`), 3a.11 (puntos de atención), 3a.12 (las 7 opciones de parentesco
   que Oracle no sabe guardar) y 3a.13 (cuál id de Cédula).
4. Con eso, el escalón 1 contra el Oracle **local** sale solo.

---

## 5. Qué DECIR la próxima sesión (prompt listo para pegar)

**Si ya reexportaste la Query A v2 completa** (el camino previsto):

> Retomamos la migración Oracle legacy → SICAV, worktree `feat/oracle-legacy-writer`.
> Lee `docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md`; el estado está en **§3b-bis-B/C**.
> Sigue todo en **DRY-RUN, solo lectura**.
>
> Ya tengo el export completo de la Query A v2 (sin truncar) en `<ruta del TSV>`.
> Regenera el catálogo con `generar_catalogo_respuestas`, comprueba que `completo`
> quede en `true`, y dime: (a) cuántas de las 153 huérfanas aparecen y en qué
> preguntas — sobre todo si hay más agujeros como el de parentesco (§3b-bis-E.3);
> (b) cuántas opciones de SICAV **no cruzan por texto** con Oracle, que es la lista
> de curaduría real contra el manual; (c) si sigue habiendo textos duplicados con
> varios ids escribibles además del de Cédula.
> Tests + re-correr `escribir_a_oracle --hogar LISTO-96001` en DRY-RUN.
> Lo que no cruce, pendiente: **nada de fuzzy matching**, y ante duda funcional manda
> el **manual** (11-MU/14-MU) antes que escalar a Oscar. No commitees hasta que revise.

**Si además corriste el `SELECT DISTINCT RXP_TIPOPREGUNTA`**, añade:

> Y el `SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA` dio: `<...>`.
> Si es `{GE, IN}`, cablea `RXP_TIPOPREGUNTA` desde el `pre_tipopregunta` del catálogo
> (§3b-bis-E.4) y quita ese pendiente.

**Si todavía no hay export**, lo que queda son los bloqueantes de §3a. Ver §4.

---

## 6. Punteros rápidos

- Código Etapa A: `srni-backend/apps/sincronizacion/` (models, oracle/, management/, tests/).
- Crosswalk catálogos: `apps/sincronizacion/oracle/catalogos.py` + `catalogos_oracle.json`.
- Catálogo de respuestas: `apps/sincronizacion/oracle/respuestas_oracle.json` (**generado,
  no se edita a mano**) ← `docs/oracle-legacy/query_a_v2_parcial_temas_1_2.tsv`
  vía `python manage.py generar_catalogo_respuestas <tsv> --fecha <YYYY-MM-DD>`.
- Diseño Etapa A: `docs/oracle-legacy/diseno_etapa_a_escritura.md`.
- Auditoría + veredicto a1/a2: `docs/oracle-legacy/auditoria_diseno_legacy.md`.
- Ruta de escritura (análisis PL/SQL): `docs/oracle-legacy/ruta_escritura.md`.
- Correr DRY-RUN: `python manage.py escribir_a_oracle --hogar <cod> --settings=srni.settings.development`.
- Oracle local: `cd infra/oracle-local && docker compose --env-file .env up -d`.

### Escenario del Escalón 1 (reproducible)

`cargar_hogar_demo_oracle` deja un hogar con sesión, territorio que **cruza a ids
reales de Oracle** y respuestas de los dos niveles. Es command y no fixture JSON a
propósito: el cruce es por NOMBRE y un fixture tendría que fijar `Municipio` por PK
(no hay `natural_key()`), que es la fragilidad que ya advierte `dump/README.md`.

```bash
python manage.py loaddata dump/hogares_demo_10.json          # precondición
python manage.py cargar_departamentos_municipios --csv=data/municipios_dane.csv
python manage.py cargar_direcciones_territoriales
python manage.py cargar_hogar_demo_oracle                    # idempotente
python manage.py escribir_a_oracle --hogar LISTO-96001       # DRY-RUN, 10 pasos
```

Territorio sembrado: DT CENTRAL / Tolima / JORNADAS DE ATENCIÓN / ALVARADO →
`id_dt=7, id_depto=30, id_pt=13, id_ma=32` (el comando lo verifica y aborta si deja
de cruzar). El punto va **con tilde** a propósito, para ejercitar la normalización.

⚠️ **Trampa que el comando ya cubre:** los hogares del fixture vienen con
`creado_por=null` ⇒ `USUA_CREACION` viajaría como cadena vacía y **en Oracle '' ES
NULL**; como `GIC_HOGAR.USU_USUARIOCREACION` es NOT NULL, el INSERT fallaría y
`GIC_INSERT_HOGAR1` se tragaría el error con su WHEN OTHERS: no escribiría nada y no
avisaría. El comando asigna un encuestador si falta.
