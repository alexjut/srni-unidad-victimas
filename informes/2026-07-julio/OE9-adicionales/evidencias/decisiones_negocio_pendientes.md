# Hoja de decisiones de negocio — SICAV ↔ Oracle

> **Fecha:** 2026-07-23 · **Decide:** Javier (Oscar le delegó la responsabilidad).
> **Regla:** manda el manual (11-MU / 14-MU); lo que el manual no cubre, lo decides tú.
> Formato: **contexto → opciones → mi recomendación → tu decisión**. Marca y yo ejecuto.

---

## Ya resueltas (recap, no requieren acción)
- **NS/NR:** gana SICAV, el crosswalk mapea a Oracle. ✅
- **Parentesco A24:** "Otro pariente del responsable del hogar" (manual B24). ✅ aplicado.
- **Agua de carro tanques:** crosswalk → "Carrotanque". ✅
- **PR3_re:** re-enganchada a AHE (pre 354). 5/9 opciones mapean. ✅ aplicado. Faltan las 4 de abajo.

---

## 1. PR3_re — 4 opciones de Ayuda Humanitaria sin equivalente directo en Oracle (pre 354)

Oracle (pre 354) tiene: Alimentación, Alojamiento, Vestuario, Atención médica, Atención
psicosocial, Transporte, **Kit de habitabilidad** (1235), Agua potable, Educación, Pago de
deudas, Pago de servicios, Saneamiento básico, **Otra Cuál?** (1241).

### 1a. "Atención médica y psicosocial" — SICAV la junta, Oracle la separa (1232 médica / 1233 psicosocial)
- **Opciones:** (A) **dividir** la opción de SICAV en dos ("Atención médica" + "Atención psicosocial") → calza con Oracle, sin pérdida. (B) dejar una sola y mapear solo a médica (pierde psicosocial). (C) mapear a "Otra".
- **Mi recomendación:** **(A) dividir.** Es lo más fiel; el manual las trata como dos. (Es un cambio de instrumento: 1 opción → 2.)
- **Tu decisión:** ☐ A dividir ☐ B una sola ☐ C otra ☐ ____________

### 1b. "Aseo personal y elementos de hábitat"
- **Contexto:** Oracle tiene "**Kit de habitabilidad**" (1235 — utensilios de aseo, cocina, hábitat).
- **Mi recomendación:** **mapear a "Kit de habitabilidad" (1235)** — misma naturaleza (kit de hábitat/aseo).
- **Tu decisión:** ☐ Kit de habitabilidad (1235) ☐ Otra (1241) ☐ ____________

### 1c. "Auxilio funerario"
- **Contexto:** Oracle **no tiene** "auxilio funerario" en ninguna pregunta (barrido global).
- **Opciones:** (A) mapear a "**Otra, Cuál?**" (1241) con el texto "Auxilio funerario" en el detalle → no se pierde el dato. (B) no migrarla (queda sin escribir).
- **Mi recomendación:** **(A) → "Otra" (1241) con detalle.**
- **Tu decisión:** ☐ A "Otra"+detalle ☐ B no migrar ☐ ____________

### 1d. "Apoyo económico (transferencia monetaria)"
- **Contexto:** Oracle **no tiene** transferencia monetaria (354 es "en qué gastó/qué recibió").
- **Mi recomendación:** **(A) → "Otra, Cuál?" (1241) con detalle** "Apoyo económico (transferencia monetaria)".
- **Tu decisión:** ☐ A "Otra"+detalle ☐ B no migrar ☐ ____________

---

## 2. Método de recolección (pre 2) — mapear la automatización de SICAV a Oracle

Oracle (pre 2): Vivienda de residencia (2), Entrevista Telefónica (3), **Entrevista presencial (lugar distinto)** (4), Otro Cuál? (5), Jornada de Atención (2334).

### 2a. "Cara a cara" (SICAV)
- **Contexto:** genérico presencial; Oracle distingue "en la vivienda" vs "lugar distinto".
- **Mi recomendación:** **"Vivienda de residencia" (2)** por defecto (la mayoría se hace en casa); si SICAV sabe que fue en otro lugar, usar "Entrevista presencial" (4).
- **Tu decisión:** ☐ Vivienda (2) ☐ Presencial lugar distinto (4) ☐ Otro (5) ☐ ____________

### 2b. "Autodiligenciada" (SICAV)
- **Contexto:** Oracle **no tiene** autodiligenciado (asume entrevistador).
- **Mi recomendación:** **"Otro, Cuál?" (5) con detalle "Autodiligenciada"**, o no escribir (es automatización SICAV).
- **Tu decisión:** ☐ "Otro" (5)+detalle ☐ no escribir ☐ ____________

---

## 3. Cédula — ¿qué id usa SICAV? (93 vs 3854) — ✅ RESUELTO → **93**

Análisis en prod (2026-07-23): 93 existe desde 2015 (29.272 usos); 3854 aparece en **2020**
y **convive** con 93 (no lo reemplaza). Ambos son **nivel PERSONA, mismo instrumento, y los
MISMOS encuestadores** cargan los dos indistintamente. ⇒ La hipótesis "3854 = víctimas con
acciones victimizantes" **queda refutada**: 3854 es un **id DUPLICADO** de catálogo (calidad
de dato de Oracle), no otro canal ni categoría. **Decisión (Javier): SICAV usa el 93**
(canónico/mayoritario). Cableado en el crosswalk (pre 30 → 93).

---

## 4. Bloque PR completo (id_preg 90-93) mal enganchado — ¿curación completa?

**Hallazgo:** no es solo PR3 — **todo el bloque PR** (Ayuda Humanitaria) está mal enganchado
a Oracle: pre 90/92/93 son de rehabilitación (tema 10) y **pre 91 ni existe** en Oracle.
- **Mi recomendación:** lanzar una **curación del bloque PR completo** (agente contra el manual, como PR3): re-enganchar PR1_re/PR2_re/PR4_re a sus preguntas Oracle correctas.
- **Tu decisión:** ☐ Sí, lánzalo ☐ Después ☐ ____________

---

## 5. Hechos victimizantes — dos cosas, una urgente (3-ago-2026)

Al cablear el paso HECHO (`GIC_INSERT_VALIDADOR_HECHO_AUX`, el que llena las columnas
`HECHO_VICTIMIZANTE_1..14` de los reportes) salieron dos asuntos distintos.

### 5a. 🔴 **No hay de dónde sacar el dato.** — bloquea, y no es decisión mía

El paso está implementado, probado y verificado. Pero la tabla `HechoVictima` de SICAV
**está vacía y nada la puebla**: `cargar_padron_oracle` trae identidad, etnia, género,
discapacidad y estado en el RUV, y **no** los hechos (no están en su `SELECT`); ningún
otro comando ni endpoint escribe ahí. Resultado: hoy el paso corre y escribe **cero**
validadores, y esas 14 columnas del reporte van a seguir vacías aunque todo lo demás
salga perfecto.

- **Opciones:** (A) **traerlos del mismo origen que el padrón** — `M_CARACT_TABLA_RA_PER@DBL_VIVANTO` o la tabla de hechos de Vivanto — en una pasada como la del padrón. (B) capturarlos en campo (hay preguntas de hechos en el instrumento, pero preguntan por hechos *declarados en los últimos 6 meses*, que **no** es lo mismo que los hechos por los que la persona está en el RUV). (C) dejarlas vacías y decirlo por escrito.
- **Mi recomendación:** **(A).** Es el mismo dblink y el mismo cruce por `cons_persona` que ya funcionó para 5,9 M de personas; lo que falta es saber qué tabla de Vivanto tiene los hechos y pedir una muestra. (B) escribiría un dato que significa otra cosa.
- **Tu decisión:** ☑ **A — traerlos del RUV** *(4-ago-2026)*

#### ✅ RESUELTO el 4-ago-2026 — **ya sabemos de dónde salen, y el dato existe**

El área funcional aportó el nombre de la tabla (`Tbsiniestros_persona`) y con eso se
ubicó todo lo demás. **No hace falta pedir accesos nuevos:** vive en el esquema `RUV`,
alcanzable desde `ENTREVISTARN` por el dblink **`CONSULTARUV`** que ya existe.

| Objeto | Qué es | Volumen |
|---|---|---|
| `RUV.TBHECHOS_VICTIMIZANTES` | el catálogo oficial | **13 hechos** |
| `RUV.TBSINIESTROS_PERSONA` | el hecho con **fecha y municipio** | **4.033.355** |
| `RUV.TBREG_PERSONA_HECHOS` | persona ↔ hecho | **9.331.396** |
| `RUV.TBPERSONAS` | `ID`, `NUMERODOCUMENTO`, `PARAM_TIPODOCUMENTO` | 7.330.769 |

El enlace **está declarado con foreign keys** (`FK_REGPER_SINIESTRO` y
`FK_REGISTRO_PERSONA_HECHOS`, ambas contra `PK_TBREGISTROS_PERSONAS`), así que la ruta
hasta el documento no es conjetura. Y como `TBSINIESTROS_PERSONA` trae fecha y lugar,
no solo se llenan las 14 columnas: se puede poner **cuándo y dónde**.

**Verificado con datos, no solo con nombres:** la distribución de `PARAM_TIPOHECHO` da
**51,8 % al 5 (Desplazamiento Forzado)** —lo que tiene que dominar en Colombia— y ningún
valor cae fuera de 1..13.

**Decisión tomada (Javier, 4-ago-2026):** se trae **el catálogo, no las 9,3 M de filas**;
el cruce por persona se resuelve **bajo demanda** contra `TBSINIESTROS_PERSONA`, sin
replicar media base. Catálogo cargado en producción el mismo día (0 → 16 filas).

### 5a-bis. 🟠 'Censo Masivo' y 'Otro' del RUV — **resuelto, con pérdida de precisión declarada**

Al conectar el catálogo apareció que **son tres catálogos y no dos**, y que RUV y legacy
divergen justo donde está el volumen:

| Código | Catálogo del legacy | Catálogo del RUV |
|---|---|---|
| 1–11 | idénticos | idénticos |
| **12** | Pérdida de bienes muebles o inmuebles | **Otro** (75.264) |
| **13** | Otros | **Censo Masivo** (434.178) |

Copiar el número escribiría el hecho equivocado en **509.442 registros (12,6 %)** sin que
nada falle.

- **Opciones:** (A) agregar los dos códigos a SICAV y traducir por significado al escribir al legacy. (B) forzarlos a un hecho existente de SICAV. (C) descartarlos.
- **Mi recomendación:** **(A).** (B) era la trampa: mandar 'Censo Masivo' a `HV13` para que aterrizara en el 'Otros' del legacy habría marcado a **434.178 personas como CONFINAMIENTO dentro de SICAV** —un hecho real y distinto—. Con (A) la pérdida ocurre **solo en la frontera** con el legacy, que es donde debe ocurrir.
- **Tu decisión:** ☑ **A — «censo masivo a otros»** *(4-ago-2026)*. Aplicada: `HV15 Otro` y `HV16 Censo Masivo` en SICAV, ambos → 13 `'Otros'` al escribir al legacy, declarados en `HECHO_VICTIMIZANTE_APROXIMADO` para que el escritor lo informe en cada corrida.

### 5b. 🟠 'Confinamiento' no existe en el catálogo del legacy

Los dos catálogos tienen 14 hechos, pero el de Oracle está congelado en 2015 y su 13 es
'Otros'; el 13 de SICAV es **Confinamiento**, que se reconoce como hecho autónomo
(Auto 373/2016). Los otros 13 cruzan exacto.

- **Opciones:** (A) escribirlo como **'Otros' (13)** — la persona queda contada y visible en el reporte, con el detalle recuperable desde SICAV, pero en el legacy se lee 'OTROS'. (B) no escribirlo (esa persona sale sin hechos). (C) pedirle a OTI un alta de catálogo.
- **Mi recomendación:** **(A), ya aplicada** — es el mismo criterio que se usó con PE→'Otro' en tipo de documento: perder precisión antes que perder a la persona. Está declarada como cruce aproximado (`HECHO_VICTIMIZANTE_APROXIMADO`) y el escritor lo informa en cada corrida, así que no se olvida.
- **Tu decisión:** ☑ A 'Otros' (13) — *aplicada, reversible con cambiar un número* ☐ B ☐ C

---

*Marca tus decisiones (o me las dices) y las aplico en una pasada: fixture → cargar_perfil →
exportar_a_mobile + las entradas de crosswalk que correspondan. Todo sigue DRY-RUN.*
