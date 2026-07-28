# Escalón 2 — la ruta geográfica, verificada contra la réplica local

> **Fecha:** 2026-07-28 · **Rama:** `feat/oracle-legacy-writer` · **Worktree:** `D:\desarrollo\uv-oracle-writer`
> **Escrituras en producción: 0.** Contra prod solo se ejecutaron `SELECT` (catálogo, sin PII).

## ✅ RESULTADO — LOGRADO

`escribir_a_oracle --hogar LISTO-96001 --confirmar --destino local` →
**11/11 pasos VERIFICADO**, idempotente. Y lo que el Escalón 1 no había probado:

```
res_id=6   nivel=GE  texto='5001'   ->  Medellin / Antioquia     ← resuelto por Oracle
res_id=8   nivel=GE  texto='1'      ← Zona / Cabecera
res_id=69  nivel=IN  texto='2'      ← Sexo / Mujer
```

La primera línea es el Escalón 2: la respuesta geográfica no solo se escribió, sino que
**Oracle la resuelve** con el mismo join que usan sus reportes
(`SP_CONSTANCIA`, body 3625-3626: `RE.RXP_TEXTORESPUESTA = M.ID_MUNI_DEPTO`).

---

## 1. El bloqueante que se disolvió

El Escalón 1 se cerró con esta reserva: *"el paso RESPUESTA corrió con `AP_GEOGRAFIA`
stubeada; valida la forma, no el comportamiento geográfico. El fiel de verdad se repite
en un entorno de Pruebas de OTI"*.

**Ya no hace falta ese entorno.** Análisis estático del PL/SQL (auditado por segunda vez,
de forma independiente):

- Las **18 referencias** a `rni_mi_pru.AP_GEOGRAFIA@DBL_RNIENTREVISTA` del paquete
  `GIC_N_CARACTERIZACION` caen **todas** dentro de `SP_CONSTANCIA_GAVE` (body 4446-4779).
- `SP_CONSTANCIA_GAVE` **no tiene un solo llamador** en el volcado: es punto de entrada
  externo (el front lo invoca para la constancia GAVE).
- El **cierre transitivo** de la ruta de escritura (`SP_SET_RESPUESTAS_DE_ENCUESTA`,
  cascada territorial, `FN_GET_CODIGOENCUESTA`) alcanza **17 subprogramas y ninguno
  referencia un dblink**. `ALL_DEPENDENCIES` lo confirma a nivel paquete.
- Los 5 **triggers** de las tablas destino son asignaciones de secuencia. Sin geografía.
- Los `@DBLINK_VIVANTO` de `GIC_CATEGORIZACION` están **dentro de comentarios**: código muerto.

**Redacción correcta** (la imprecisa decía "solo hacía falta para compilar"): en Oracle un
package body INVALID hace fallar la ejecución de *cualquiera* de sus procedures, así que el
stub **sí era necesario para poder ejecutar**. Lo que no hace es influir en ningún valor
escrito ni en ninguna decisión de control de flujo del paso RESPUESTA — su tabla vacía
nunca se lee en esa ruta. **La fidelidad del dato escrito no estaba comprometida.**

---

## 2. El bloqueante REAL que apareció en su lugar

Buscando lo anterior salió un defecto que sí habría corrompido datos en producción.

**Las preguntas de departamento/municipio (`PRE_TIPOCAMPO='DP'`) no guardan un
`RES_IDRESPUESTA` por municipio:** Oracle les da **una respuesta contenedora** (con
`RES_RESPUESTA` vacío) y el lugar viaja como texto en `RXP_TEXTORESPUESTA`.

**Medición en producción (2026-07-28, solo lectura):**

| Qué | Resultado |
|---|---|
| `GIC_MUNICIPIO.ID_MUNI_DEPTO` | **es el código DIVIPOLA/DANE** como número: Medellín `5001`, Alvarado `73026`, Cali `76001` |
| Cruce de respuestas reales contra ese catálogo | **28.151 / 28.151 = 100 %** |
| Convención `AP_GEOGRAFIA` + split por `-` (la de GAVE) | **no aparece** en ninguna fila real de estas preguntas |
| Preguntas con tipo de campo DP/DT | **19** (no 5, como se creyó al principio) |

**El defecto:** SICAV escribe el DANE de 5 dígitos **con** el cero a la izquierda
(`'05001'`, tal como lo deja el selector de municipio del móvil) y Oracle espera
`'5001'`. Rompe en los **8 departamentos cuyo código empieza por cero** (Antioquia,
Atlántico, Bolívar, Boyacá, Caldas, Caquetá, Cauca, Cesar) — y rompe **en silencio**:
el `EXCEPTION WHEN OTHERS` del procedure no avisa, y la fila queda con un texto que
ningún reporte territorial resuelve. Exactamente la forma del bug histórico.

**Corrección** (`catalogos.normalizar_codigo_municipio` + `mapeo._texto_respuesta`):
traduce solo las preguntas DP, deja el resto intacto y **no inventa** — un municipio
ausente del catálogo lanza `MapeoDesconocido` en estricto y deja `‹PEND:GEOGRAFIA›`
en dry-run. Además `resolver_res_idrespuesta` aprendió el caso de la respuesta
contenedora única (sin él, la respuesta geográfica se perdía por no tener texto que cruzar).

---

## 3. Riesgo crítico corregido de paso (no era del Escalón 2)

**`--destino local` no validaba nada.** Resolvía el host desde `settings.ORACLE_LEGACY`,
alimentado por `ORACLE_LEGACY_HOST`. Una sesión con esa variable apuntando a prod —cosa
normal para una lectura de referencia— convertía
`escribir_a_oracle --confirmar --destino local` en una **escritura a producción**, con el
banner del comando diciendo "local". Con `COMMIT` interno: sin vuelta atrás.

Ahora `local` solo resuelve a `localhost`/`127.0.0.1`/`::1`/`0.0.0.0`/`host.docker.internal`;
cualquier otro host aborta con `DestinoLocalNoLocal`. Y el comando **imprime el DSN
resuelto** antes de escribir, para no fiarse de la etiqueta:

```
⚠️  MODO ESCRITURA REAL sobre Oracle 'local'.
    Destino resuelto: RNIENTREVISTA@localhost:1521/FREEPDB1
```

---

## 4. Qué cambió en el repo

| Archivo | Qué |
|---|---|
| `oracle/conexion.py` | guarda `HOSTS_LOCALES` + `describir_destino()` |
| `oracle/catalogos.py` | `cargar_geografia()` + `normalizar_codigo_municipio()` |
| `oracle/mapeo.py` | `_texto_respuesta()`; respuesta contenedora DP/DT en el resolver |
| `oracle/geografia_oracle.json` | **nuevo** — volcado de prod: 1.126 municipios, 33 deptos, 19 preguntas DP/DT |
| `parametricas/commands/cargar_puntos_atencion_oracle.py` | **nuevo** — carga los 266 puntos reales (3a.11, §7). El catálogo ya estaba en `catalogos_oracle.json` → `dt_puntos`: no hizo falta volcado nuevo |
| `commands/escribir_a_oracle.py` | imprime el DSN resuelto |
| `commands/cargar_hogar_demo_oracle.py` | 3.ª respuesta demo: la geográfica (`'05001'` a propósito) |
| `infra/oracle-local/cargar_geografia_local.py` | **nuevo** — puebla GIC_MUNICIPIO/DEPARTAMENTO en la réplica |
| `tests/test_conexion_destino.py` | **nuevo** — 10 tests de la guarda de destino |
| `tests/test_geografia.py` | **nuevo** — 18 tests del cruce geográfico |
| `.env.example` | `ORACLE_USUARIO_SERVICIO_ID=999999` / `ORACLE_PERFIL_SERVICIO_ID=1` |

**Tests: 134/134** en `apps/sincronizacion` (eran 105) + 6 nuevos en `apps/parametricas`.
Suite completa: **292 pasan** (eran 286 antes de 3a.11), con los mismos 7 fallos
preexistentes de `apps/formulario/tests/test_cargar_diccionario.py` (verificados ajenos
a este trabajo).

---

## 5. Reproducir

```powershell
docker start srni-oracle-local                              # esperar healthy
cd D:\desarrollo\uv-oracle-writer
$PY = "D:\desarrollo\unidad-victima\srni-backend\.venv\Scripts\python.exe"
& $PY infra\oracle-local\setup_escalon1_geografia_stub.py   # stub AP_GEOGRAFIA -> paquete VALID
& $PY infra\oracle-local\cargar_geografia_local.py          # GIC_MUNICIPIO/DEPARTAMENTO reales
cd srni-backend
& $PY manage.py cargar_hogar_demo_oracle
# variables: las de infra\oracle-local\.env + ORACLE_USUARIO_SERVICIO_ID=999999
#            + ORACLE_PERFIL_SERVICIO_ID=1  (NO exportar ORACLE_LEGACY_HOST)
& $PY manage.py escribir_a_oracle --hogar LISTO-96001 --confirmar --destino local
```

---

## 6. Lo que sigue

| # | Pendiente | Estado |
|---|---|---|
| 3a.11 | Reemplazar el placeholder por los **266 puntos reales** | ✅ **CERRADO** — ver §7 |
| 3a.5 | **Rotar la clave de `RNIENTREVISTA`** + borrar `.env.prod` | 🟠 abierto — se volvió a usar el 28-jul |
| 3a.3 | Tipos de documento PE (PEP) y NES sin equivalente en `GIC_TIPODOC` | 🟠 abierto |
| — | Mapear cuáles de las **19 preguntas DP/DT** existen en el instrumento de SICAV | 🟡 pendiente |
| — | Confirmar respaldo de `30.0.1.9` y ejecutar el **piloto de 1 hogar en prod** | 🟠 requiere decisión |

**Ya no queda ningún bloqueante técnico externo para el piloto.**

---

## 7. 3a.11 cerrado — el catálogo real de puntos de atención

`cargar_puntos_atencion_oracle` (nuevo) reemplaza el placeholder por el catálogo de
producción. **266/266 puntos cargados**, 39 placeholder desactivados.

**Por qué era un riesgo real:** el comando viejo inventaba 2 puntos por DT con nombres
que Oracle no conoce (`Centro Regional Medellín`, `ATENCIÓN TELEFÓNICA`). Como el cruce
territorial es **por nombre**, un hogar atendido en uno de ellos no resolvía su
territorio: `GIC_N_RELACION_DT_PUNTO` incompleto y el hogar fuera de los reportes, sin
ningún error. Era el bug histórico del proyecto esperando a ocurrir.

**Estructura del catálogo (medida sobre las 1.370 filas):**

| Hecho | Valor |
|---|---|
| Puntos distintos | **266** |
| Puntos en más de una DT / más de un departamento | **0** — cada punto tiene una y solo una |
| DT que cruzan SICAV ↔ Oracle | **21 / 21** |
| Puntos con un solo municipio (sede propia) | 209 |
| Puntos itinerantes (JORNADAS, hasta 123 municipios) | 57 → sede = capital del departamento |

**Decisiones, con su razón:**

- **El nombre se copia LITERAL de Oracle.** Es la clave del cruce; cualquier retoque
  cosmético rompe el territorio.
- **Sede de los itinerantes = capital del departamento.** Las jornadas no tienen sede
  física. Es seguro porque `resolver_territorio` usa `sesion.municipio_atencion`, **no**
  `punto.municipio`: la sede afecta a la UI, nunca al dato escrito en Oracle.
- **El municipio se resuelve por el par (departamento, municipio)**, no por nombre
  suelto: hay homónimos entre departamentos (La Unión, Albania) y cruzar solo por
  nombre habría puesto sedes en el departamento equivocado.
- **Los placeholder se desactivan, no se borran** (`activo=False`): la FK es PROTECT y
  puede haber sesiones que los referencien.
- **Una divergencia de nombre encontrada y resuelta:** SICAV escribe *"Archipiélago de
  San Andrés**,** Providencia y Santa Catalina"* y Oracle sin la coma. Se resolvió con
  un plegado **local** al comando (`_norm_depto`), sin tocar
  `catalogos.normalizar_nombre` — ese es la autoridad del cruce de opciones, donde la
  coma sí es semántica (*"Otro, ¿cuál?"*). Sin esto se perdían los 2 puntos de San
  Andrés, y ese es un perfil activo del proyecto.
- **`40-cargar-datos.sh` ya llama al comando nuevo**; el viejo queda marcado obsoleto.
  Si no se cambiaba, el próximo despliegue habría vuelto a sembrar los placeholder.

Tests: 6 nuevos en `apps/parametricas`. Suite completa: **292 pasan** (+6), mismos 7
fallos preexistentes.
