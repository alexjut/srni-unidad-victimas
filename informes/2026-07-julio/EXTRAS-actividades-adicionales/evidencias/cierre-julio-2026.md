# Cierre de julio 2026 — SICAV Móvil / SRNI

> **Proyecto:** PRY-0662064 — Modernización de la entrevista de caracterización
> **Periodo:** 1 – 16 de julio de 2026 · **Fecha de cierre:** 2026-07-16
> **Actualizado:** 2026-07-24 con el logro del **Escalón 1** — primera escritura real de
> una caracterización al Oracle legacy vía procedures oficiales, **contra réplica local**
> (no producción). Ver §5.7 y §8.
> **Equipo:** Javier Aguilar (desarrollo + arquitectura) · Brando (frontend web) ·
> Oscar (supervisión funcional, UARIV)
> **Estado:** borrador para revisión de Javier (no commiteado)

---

## 1. Resumen ejecutivo

Julio tuvo **dos frentes grandes y uno nuevo**:

1. **Instrumento territorial V7 → V8** — se cerró el barrido de 4 lotes y el APK quedó
   en producción con **363 preguntas**, skip-logic, multi-select y DIVIPOLA.
2. **Frontend web** — Brando avanzó el grueso de módulos (permisos por rol, dashboard
   contextual, rediseño de instrumentos, detalle de sesión/hogar).
3. **🆕 Migración a Oracle legacy (Etapa A)** — arrancó el 15 de julio. Es el frente
   que abre el camino para que SICAV escriba en el sistema de la UARIV. **El 24 de julio
   pasó de DRY-RUN a la primera escritura real de una caracterización end-to-end vía los
   procedures oficiales, contra la réplica local (no producción) y verificada por SELECT
   (10/10 pasos).** Ver §5.7.

**66 commits** en el periodo: 46 de Javier, 20 de Brando (más el commit `860597c` del
Escalón 1, del 24-jul, fuera del periodo de cierre — ver §8).

| Frente | Commits | Estado (act. 24-jul) |
|---|---:|---|
| Frontend web (Brando) | 30 | En curso |
| Instrumento / bundle / skip-logic | 19 | ✅ V8 en producción |
| Infra / móvil / WAF / dominio | 9 | ✅ Dominio institucional operativo |
| Oracle legacy (Etapa A) | 8 | 🔄 DRY-RUN al 16-jul → ✅ 1ª escritura real en réplica local, verificada (24-jul) |
| Documentación / chore | 9 | — |

---

## 2. Instrumento territorial V8 — cerrado

El barrido V7→V8 se hizo en **4 lotes** y terminó desplegado en el APK (`vc49`):

- **Lote 1** — skip-logic (P26/P27, B26→B27 territorio colectivo).
- **Lote 2** — observaciones por capítulo, estrato de vivienda (C7/energía), sub-campos
  de cursos (K17-19, K35), valores de ingresos (J31-J40), inputs embebidos convertidos
  en preguntas-hija.
- **Lote 3** — multi-select (6 preguntas).
- **Lote 4** — DIVIPOLA (D6/D11 a selector de municipio).

Además: condiciones **AND** en skip-logic vía referencia a respuestas de otras
preguntas, constancia de tutor/cuidador persistida con endpoint de subida, comando
`desactivar_instrumento` y retirada del `cargar_territorial_v7` obsoleto.

**Resultado:** fixture + bundle + backend + APK alineados; **363 preguntas** en el
bundle territorial V8.

## 3. Infraestructura y despliegue — cerrado

- **Dominio institucional operativo**: `caracterizacion.unidadvictimas.gov.co` vía WAF
  FortiWeb → NPM → `cz_nginx`. Se resolvió el 500 en la descarga del APK tras el WAF
  (la IP llegaba con puerto en `X-Forwarded-For`) y se puso `cz_nginx` en
  `uariv-network`.
- **APK apuntando al dominio institucional** (preview y production).
- Mock de víctimas `9990100001–10` habilitadas + manual funcional publicado.

## 4. Frontend web (Brando) — en curso

Permisos y componentes de acceso restringido, dashboard contextual por rol,
visibilidad de módulos por rol, rediseño de instrumentos (grid de cards + drill-down),
detalle de sesión con agrupación de respuestas por miembro, normalización de nombres a
formato título, modal de confirmación para activar/desactivar usuarios, migración de
imágenes del login a `.avif` (34 MB → 4 MB) y varias correcciones de nullables.

---

## 5. Migración a Oracle legacy (Etapa A) — el frente nuevo

**Objetivo:** que SICAV escriba en `RNIENTREVISTA` (el Oracle de la UARIV) **invocando
los procedures oficiales `GIC_*`**, nunca con INSERT directo. Estrategia *strangler-fig*:
convivir con el sistema viejo en vez de reemplazarlo de golpe. **El 24 de julio se logró
la primera escritura real de una caracterización end-to-end vía los procedures oficiales
(Escalón 1, §5.7); fue contra la RÉPLICA LOCAL en Docker, no contra producción. Se
mantiene la regla del proyecto: no se ha escrito ni una fila en producción.**

### 5.1 Lo que está hecho

- **Lógica PL/SQL portada a Django** — 5 bloques `GIC_*` → servicios Django, con
  **24/24 tests de paridad**.
- **Capa de escritura vía procedures** (`apps/sincronizacion/oracle/`) con máquina de
  estados reanudable y *ledger* en PostgreSQL.
- **Oracle local en Docker** (`gvenzl/oracle-free`) con la **estructura real** de
  RNIENTREVISTA importada, para validar SQL sin tocar producción.
- **Los 5 pasos cableados**: HOGAR → PERSONA → MIEMBRO → TERRITORIO → RESPUESTA
  (ejecutados y **verificados por SELECT** el 24-jul contra la réplica local — ver §5.7).
- **Escenario reproducible** del Escalón 1 (`cargar_hogar_demo_oracle`).
- **105 tests** en `apps/sincronizacion` (96 al 16-jul → 105 con el Escalón 1).

### 5.2 Por qué esto es delicado (y por qué se va tan despacio)

Los procedures de Oracle **hacen `COMMIT` interno y se tragan las excepciones**
(`EXCEPTION WHEN OTHERS`). Consecuencia: **no hay transacción envolvente y no hay
errores en los que confiar**. Un dato mal mapeado no explota — *no escribe nada y nadie
se entera*. De ahí las dos reglas del trabajo:

1. **Nunca se inventa un valor.** Lo que no está confirmado sale como marcador
   `‹PEND:...›` y el modo estricto lanza excepción.
2. **Solo avanza lo verificado por SELECT**, no lo que el procedure "dijo" que hizo.

### 5.3 Decisiones y hallazgos con dato (no con parecido)

| Hallazgo | Veredicto |
|---|---|
| `Pregunta.id_preg == PRE_IDPREGUNTA` | ✅ **Confirmado** (14/14 ids) — es el puente bueno |
| `OpcionRespuesta.id_resp_vivanto == RES_IDRESPUESTA` | ❌ **Refutado** (0/14): Mujer es 4599 en SICAV y **69** en Oracle. Hay test de regresión |
| `INS_IDINSTRUMENTO` | ✅ Oracle tiene **un solo instrumento** (1=CARACTERIZACION). No había crosswalk |
| `RXP_TIPOPREGUNTA` | ✅ **Resuelto con dato**: dominio `{GE, IN}` medido en prod. No es el tipo de widget, es el **nivel** (GE=hogar/IN=persona) ⇒ se copia de Oracle |
| Cascada territorial | ✅ Resuelve ids reales por **nombre** (los ids de Oracle son surrogates, no DANE) |

**Dos trampas encontradas leyendo el PL/SQL** (habrían causado pérdida silenciosa):

- El parámetro formal `Id_DT` de `GIC_SP_OBTPUNTOATECION` **espera el id del
  DEPARTAMENTO**, no el de la dirección territorial. El nombre miente.
- En Oracle **`''` ES `NULL`**: un hogar sin `creado_por` produce `USUA_CREACION=''`,
  el INSERT falla contra un NOT NULL, y el procedure se lo traga.

### 5.4 El episodio que conviene recordar

Se detectaron 10 respuestas que Oracle ofrece pero no puede guardar — **7 de ellas
opciones de parentesco** (Nieto(a), Abuelo(a), Sobrino(a)…). Se iba a escalar a Oscar
**con prioridad, como defecto activo de producción**.

**Era falsa alarma.** El manual oficial (11-MU pág. 56) lista **exactamente 6 opciones**
para esa pregunta — justo las 6 que Oracle sí deja escribir — y SICAV ofrece esas
mismas 6. Verificado 10/10: SICAV no ofrece ninguna. Las "huérfanas" son **opciones
retiradas**; la escribibilidad de Oracle **implementa el manual**.

> **Lección:** un fallo silencioso en una ruta que nadie recorre no es un fallo. Tener
> el mecanismo bien verificado no basta: hay que comprobar si alguien llega a recorrer
> esa ruta. La regla del proyecto — **consultar el manual ANTES de escalar** — es lo
> que lo atajó.

### 5.5 Decisiones de negocio (delegadas por Oscar en Javier)

Oscar (supervisor UARIV) delegó en Javier estas decisiones de negocio, con los manuales
oficiales 11-MU/14-MU como guía. Al 24-jul, **5 de las 8 se resolvieron con dato** (fueron
las que habilitaron el Escalón 1, §5.7); **3 siguen abiertas**.

| # | Pendiente | Estado (24-jul) |
|---|---|---|
| 3a.1 | Usuario/perfil de servicio de SICAV en Oracle | ✅ **Resuelto** → usuario de servicio **sintético 999999** (sin PII) para `ID_USUARIO`; `USU_USUARIOCREACION` sale del **encuestador real** |
| 3a.2 | Mapeo P8: `ID_SINIESTRO`, `ID_DECLAR`, `T_VICTIMA` | ✅ **Resuelto** → los tres a **NULL** (estructura los confirma nullable; SICAV no origina esos enlaces internos). `T_VICTIMA`: medido en prod, NULL en **7.755.818 de ~7,76 M** personas → campo en desuso |
| 3a.3 | Tipos de documento PE (PEP) y NES: sin equivalente en `GIC_TIPODOC` | ⚠️ **PENDIENTE CONFIRMAR** — abierto |
| 3a.5 | **Rotar la clave de RNIENTREVISTA** (se usó para lectura/export) | ⚠️ **PENDIENTE** — abierto (seguridad) |
| 3a.8 | `PPER_IDPERSONA` en preguntas de nivel hogar | ✅ **Resuelto** → se ancla al **jefe/autorizado** del hogar |
| 3a.9 | `PBANDERA`: con 1 **borra** las respuestas previas. No se asume | ✅ **Resuelto** → **1** (upsert idempotente). En un hogar **nuevo** el borrado es *no-op*: ya no es riesgo destructivo, es decisión deliberada y documentada |
| 3a.11 | El catálogo de puntos de atención de SICAV es un placeholder (37 vs 266 reales) | ⚠️ **PENDIENTE** — abierto |
| 3a.13 | 🆕 **Cédula: ¿qué es el id 3854?** (ver abajo) | ✅ **Resuelto/refutado** → 3854 es un **id DUPLICADO de catálogo**, no otro canal. SICAV usa el **93** |

**3a.13 — el caso Cédula, medido en producción:** la pregunta 30 tiene 4 ids
escribibles con el texto `Cédula de ciudadanía / Contraseña`, y el manual declara la
opción una sola vez. El uso real:

| id | usos |
|---:|---:|
| **93** | **29.338** |
| **3854** | **8.620** ⚠️ |
| 3852 | 19 |
| 3853 | 15 |

3852/3853 son ruido. **3854, con 8.620 usos, no.** Hay algo real detrás y el manual no
lo explica (los ids internos no son asunto del manual). **Pregunta que se abrió para
Oscar:** *¿qué representa el 3854 — un período distinto, otro canal de captura, una
migración anterior? ¿Cuál debe usar SICAV?*

> **✅ Resuelto/refutado (24-jul), con análisis en producción.** El 3854 **no** es otro
> canal ni categoría: comparte el mismo texto y los mismos encuestadores que el 93 y
> **convive con él desde 2020** → es un **id duplicado de catálogo**. Decisión (Javier,
> por delegación de Oscar): SICAV usa el **93** (canónico/mayoritario). El resolver ya
> elige el 93.

### 5.6 Bloqueo técnico (✅ resuelto 24-jul)

El catálogo de respuestas de Oracle estaba cargado **solo parcialmente** (62 preguntas,
temas 1-2): el cliente SQL cortó el export en exactamente 200 filas. El código convivía
con esto sin mentir: una pregunta ausente producía *"no está en el volcado — lo que NO
quiere decir que no exista en Oracle"*, nunca *"no existe"*.

> **✅ Resuelto (24-jul).** Se regeneró el catálogo completo (`respuestas_oracle.json`,
> `_meta.completo=True`): **902 preguntas / 3.069 respuestas**. Ya no hay corte en 200
> filas.

### 5.7 🆕 Escalón 1 — primera escritura real (réplica local), 2026-07-24

El 24 de julio se ejecutó, **end-to-end y por primera vez**, la escritura de una
caracterización SICAV al Oracle legacy **vía los procedures oficiales `GIC_*`**.

> ⚠️ **Precisión crítica (no es producción).** La escritura fue contra la **réplica local**
> (Docker `gvenzl/oracle-free`, con la **estructura real** de RNIENTREVISTA), **no contra
> producción**. Se mantiene la regla del proyecto: **cero filas escritas en producción.**

**Resultado — 10/10 pasos VERIFICADO por SELECT**, **idempotente** (re-correr no duplica).
Hogar de prueba `999999-K34C6`:

| Paso | Detalle verificado por SELECT |
|---|---|
| HOGAR | estado=ACTIVA, `ID_USUARIO`=999999 (servicio), `USU_USUARIOCREACION`=encuestador real, tpocrn=2 |
| 3× PERSONA | RELAC fiel: jefe=**1** (Jefe de hogar), cónyuge=**4**, hijo=**3**; nombres partidos bien; extras (declar/siniestro/fuente/`T_VICTIMA`)=**NULL** |
| 3× MIEMBRO | ✓ |
| TERRITORIO | ✓ (iddt=7, punto=13, muni=32) |
| 2× RESPUESTA | ✓ (res_id 8 y 69) |

**Fidelidad (nota honesta).** HOGAR / PERSONA / MIEMBRO / TERRITORIO corrieron contra sus
procedures **reales** (VALID). El paso **RESPUESTA** corrió con la tabla `AP_GEOGRAFIA`
**stubeada** (vacía): valida la **forma**, no el comportamiento geográfico. El fiel de
verdad se repite en un **entorno de Pruebas de OTI** con geografía real.

**Tres bugs encontrados y resueltos (todos verificados):**

1. **Causa raíz única** de los cuelgues/fallos: el paquete `GIC_N_CARACTERIZACION` estaba
   **INVALID** porque referencia un dblink `DBL_RNIENTREVISTA` inexistente en la réplica
   (para `AP_GEOGRAFIA`). Afectaba HOGAR (vía `FN_GET_CODIGOENCUESTA`), TERRITORIO y
   RESPUESTA, y su `WHEN OTHERS` **se tragaba el error**. *Fix:* stub loopback (esquema
   `RNI_MI_PRU` + `AP_GEOGRAFIA` vacía + dblink que apunta al propio FREEPDB1) + recompile
   → VALID. Script reproducible: `infra/oracle-local/setup_escalon1_geografia_stub.py`.
2. Los procedures de la cascada territorial devuelven un **REF CURSOR OUT** que colgaba la
   llamada al bindarse con `cursor.var` sobre el mismo cursor que ejecuta. *Fix:* bindear
   un objeto cursor separado.
3. La idempotencia **perdía el `HOG_CODIGO`/`PER_IDPERSONA`** reales en un re-run. *Fix:*
   recuperarlos del ledger.

Las decisiones de cableado que lo hicieron posible (usuario 999999, extras en NULL, ancla
al jefe, `PBANDERA`=1) son las mismas que cerraron los pendientes **3a.1 / 3a.2 / 3a.8 /
3a.9** (ver §5.5). Esas decisiones de negocio las tomó **Javier**, por delegación de
**Oscar** (supervisor UARIV), con los manuales 11-MU/14-MU como guía.

**Lo que sigue.** Repetir el Escalón 1 en un **entorno de Pruebas de OTI** con geografía
real (para el fiel de verdad del paso RESPUESTA) y, solo entonces, planear la primera
escritura controlada contra producción. Siguen abiertos 3a.3, **3a.5 (rotar la clave)** y
3a.11 (§5.5).

---

## 6. Regalo colateral: 2 defectos detectados en SICAV

Cruzar el nivel de las preguntas de Oracle (`GE`/`IN`) contra el campo `nivel` de SICAV
dio 61/63 de coincidencia. **Las 2 discrepancias son defectos de SICAV**, no de Oracle:

- **Pregunta 8 (teléfono celular)** — SICAV la tiene como HOGAR. El manual (11-MU
  pág. 45, A11) dice textual: *"Se habilita para cada una de las personas del hogar"*
  ⇒ es PERSONA. **Cerrado con cita.**
- **Pregunta 35 (autorreconocimiento étnico)** — SICAV la tiene como HOGAR; Oracle dice
  persona, y coincide con el pendiente funcional ya registrado del 24-jun ("pertenencia
  étnica por persona"). **Corroborado, pero con evidencia más débil** que la anterior:
  el manual no declara el nivel de forma literal en esa página.

Van a la lista del instrumento territorial, no a la de la migración.

---

## 7. Riesgos abiertos

| Riesgo | Estado |
|---|---|
| **Clave de RNIENTREVISTA sin rotar** | ⚠️ **Abierto**. Se usó para lectura/export. Coordinar con OTI (3a.5) |
| Catálogo de puntos de atención placeholder | ⚠️ **Abierto**. 7 Centros Regionales de SICAV no existen en Oracle ⇒ esos hogares fallan al resolver (3a.11) |
| `PBANDERA` destructivo | ✅ **Resuelto (24-jul)**: `PBANDERA`=1 como upsert idempotente; en hogar nuevo el borrado es *no-op* → decisión documentada, no riesgo |
| Export de catálogo incompleto | ✅ **Resuelto (24-jul)**: catálogo completo regenerado (902 preguntas / 3.069 respuestas, ver §5.6) |

---

## 8. ¿Dónde están los cambios? (repos / ramas / URLs)

Para quien lea este informe y quiera encontrar el código:

| Frente | Rama | Referencia |
|---|---|---|
| **Migración a Oracle (Escalón 1)** | `feat/oracle-legacy-writer` | commit `860597c` — *feat(oracle): Escalón 1 — primera escritura real de caracterización a Oracle legacy (réplica local)* |
| Instrumento / bundle / infra | `main` | — |
| Frontend web (Brando) | `frontend` | — |

Toda rama se sube a **ambos remotes** (convención del proyecto, `git push all <rama>`):

- **GitHub (origin):** `https://github.com/alexjut/srni-unidad-victimas.git`
- **Azure DevOps:** `https://tfsunidad.visualstudio.com/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED-MOVIL/_git/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED%20MOVIL%202026-04`

> **Nota honesta.** El detalle del Escalón 1 y su plan viven en
> `docs/oracle-legacy/plan_escalon_1.md` (doc de trabajo, **no versionado**: la carpeta
> `docs/oracle-legacy/` está en `.gitignore`).

---

## 9. Punteros

- Estado y siguiente paso de la migración: `docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md`
- Diseño Etapa A: `docs/oracle-legacy/diseno_etapa_a_escritura.md`
- Paridad de la lógica portada: `docs/oracle-legacy/paridad_logica_portada.md`
- Oracle local: `docs/oracle-legacy/oracle-local-setup.md`
- Implementación/capacitación/despliegue: `docs/gestion/implementacion_capacitacion_despliegue.md`
- Acta de constitución: `docs/gestion/acta-constitucion-PRY-0662064.md`
