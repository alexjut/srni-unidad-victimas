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

*Marca tus decisiones (o me las dices) y las aplico en una pasada: fixture → cargar_perfil →
exportar_a_mobile + las entradas de crosswalk que correspondan. Todo sigue DRY-RUN.*
