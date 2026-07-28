# Plan de alineación y optimización de la BD del APK (SICAV) — al manual y a Oracle

> **Fecha:** 2026-07-22 · **Estado:** plan para revisión de Javier (no commiteado)
> **Base de evidencia:** catálogo COMPLETO de RNIENTREVISTA cargado en el Oracle local
> (902 preguntas / 3069 respuestas), cruzado contra los 8 instrumentos de SICAV.
> **Insumos:** `docs/oracle-legacy/curacion_opciones_sicav_vs_oracle.tsv`,
> `srni-backend/apps/sincronizacion/oracle/respuestas_oracle.json` (`cobertura: COMPLETO`).

---

## 0. Principio rector (arquitectura hacia la que vamos)

- **La BD guarda DATOS, no lógica.** Los procedures `GIC_*` (PL/SQL con `COMMIT` interno
  y `EXCEPTION WHEN OTHERS` que traga errores) ya están **portados a servicios Django**
  con **24/24 tests de paridad**. Estrategia *strangler-fig*: Etapa A escribe vía los
  procedures oficiales (convivencia); Etapa B = escritura directa desde Django cuando se
  retire la app vieja. La BD tiende a **solo data**.
- **El fixture es la fuente viva.** Todo cambio se hace en el fixture y baja por el
  pipeline: `fixture → cargar_perfil --reemplazar → BD → exportar_a_mobile → bundle →
  (bump de versión) → APK`. Nunca se edita solo el bundle.
- **Todo local primero.** Se valida contra el Oracle local (estructura + catálogo real,
  sin PII) antes de cualquier cosa contra prod.
- **Manda el manual.** No se agrega ni se quita una opción que contradiga el manual
  (11-MU territorial/étnicos, 14-MU asistencia). Lección parentesco: mirar el manual
  ANTES de escalar. **Nunca INSERT directo en Oracle prod** — solo procedures oficiales.

---

## 1. Estado del cruce (medido, no estimado)

| Categoría | N | Qué es | Acción |
|---|---:|---|---|
| Pérdidas silenciosas reales | **0** | SICAV no ofrece nada que Oracle no pueda guardar | — (tranquiliza) |
| Huérfanas retiradas | 41 | Oracle las lista pero el manual no; SICAV no las ofrece | ninguna (correcto) |
| "Derivas" con equivalente | 2 | preg 37/300: Oracle tiene la opción escribible con otra redacción | van a §3 (redacción) |
| Artefactos de formato | 56 | mismo texto, difieren espacios/`/`/`(a)` | §2 normalizador |
| **Curación real de redacción** | **178** | misma pregunta, texto distinto | §3 |
| id_preg mal mapeado (perfiles derivados) | 75 | el id_preg apunta a OTRA pregunta de Oracle | §4 |
| Oracle campo abierto | 81 | Oracle es texto libre; SICAV puso lista | no se toca (modelado) |
| Oracle booleano Si/No | 14 | Oracle pregunta por fila; SICAV multi-select | no se toca (modelado) |

---

## 2. Acción barata y de alto impacto: fortalecer el normalizador del resolver

El resolver cruza opciones por texto normalizado. Su normalización actual no colapsa
**56** pares que son el mismo texto (espacios alrededor de `/`, `(a)` con/ sin espacio,
guiones bajos). Endurecerla:

- Quitar espacios adyacentes a puntuación (`/ ( ) , . -`).
- Tratar `_` como espacio (SICAV usa `Básica_primaria_1°_a_5°`).
- (NO fuzzy: seguir exigiendo igualdad tras normalizar; el fuzzy elige mal en silencio.)

**Efecto:** desaparecen los 56 artefactos y **parte de los 178** (los que solo difieren
por formato). Es código, no toca la BD del APK. Va en `oracle/catalogos.normalizar_nombre`.

---

## 3. Curación de redacción (178 casos) — contra el manual

Lista completa en `curacion_opciones_sicav_vs_oracle.tsv`. Dos sub-tipos:

**3a. Trivial (mismo significado, arreglar la redacción de SICAV o del catálogo):**
- Typos de **Oracle**: `No tiene servicio sanitarios`, `¿Cuantás semanas?` → no se
  corrige Oracle (es su dato); se **mapea** la opción de SICAV a ese id.
- Formato de **SICAV**: `Básica_primaria_1°_a_5°` → `Básica primaria (1º - 5º)`;
  `Ninguna` → `Ninguno`. Alinear la etiqueta de SICAV al texto del manual.

**3b. Sustantivo (Oracle trae un calificador que SICAV omite):**
- `Cónyuge o Compañera(o)` ↔ `Cónyuge o Compañera(o) (Personas mayores de 14 años)`
- `Negro(a), afrocolombiano(a)` ↔ `Negro(a), afrocolombiano(a) o afrodescendiente`
- `Rural disperso (vereda)` ↔ `Parte rural disperso (vereda, campo)`
- Estos **confirmar contra el manual** que son la misma opción, y construir un
  **crosswalk curado opción→RES_IDRESPUESTA** (nunca fuzzy). Donde el manual mande una
  redacción, alinear la etiqueta de SICAV a esa.

**Salida:** un crosswalk `opcion_sicav → res_idrespuesta` curado (data, no lógica),
consumible por el resolver. Las que el manual no resuelva → Oscar.

---

## 4. Investigar los 75 id_preg mal mapeados en perfiles derivados

En territorial(24)/telefónico(17)/rural(14)/etc., un id_preg de SICAV apunta a una
pregunta de Oracle **distinta** (p.ej. preg 45: SICAV=material del techo vs Oracle=
tenencia). Hay que decidir, por pregunta: (a) el id_preg de SICAV está mal y se corrige;
(b) esa pregunta del perfil derivado **no existe** en el instrumento único de Oracle y
no debe mapear (Oracle tiene 1 instrumento; SICAV tiene 8). Es la parte más delicada:
el puente `id_preg == PRE_IDPREGUNTA` se verificó para territorial base, no para los
derivados. **Antes de cablear escritura de un perfil derivado, validar su id_preg.**

---

## 5. Lo que NO se cambia (para no romper el manual ni el modelado)

- **Campo abierto (81)** y **booleano Si/No (14)** de Oracle: es modelado legítimo
  distinto, no un error. No se fuerza a lista.
- **No agregar** a Oracle las opciones retiradas (parentesco, etc.): romperían el manual.
- **No INSERT directo** en `GIC_N_INSTRUMENTOXRESP` ni en ninguna tabla de prod.

---

## 6. Cómo se aplica un cambio de instrumento (checklist)

1. Editar el **fixture** del perfil (`apps/formulario/fixtures/perfil_*.json`) — nunca
   solo el bundle.
2. `cargar_perfil --instrumento <COD> --reemplazar` (recarga BD).
3. `exportar_a_mobile` (regenera bundle desde BD).
4. Si cambió la versión: tocar los **4 lugares** (archivo JSON, `index.json`, `require`
   BUNDLED en `instrumentos.ts`, backend) o el build EAS falla.
5. Validar contra Oracle local antes de subir. Versionar el fixture.

---

## 7. Pendiente de NEGOCIO (Oscar) — no es código

- **Cédula (preg 30):** 4 ids escribibles con el mismo texto; el 3854 tiene 8.620 usos.
  ¿Cuál usa SICAV? (3a.13)
- Rotar la clave de RNIENTREVISTA (se usó para lectura/export, 3a.5).
- Catálogo oficial de puntos de atención (3a.11), mapeo P8 (3a.2), tipos PE/NES (3a.3).

---

*Plan generado para revisión. Las acciones §2–§4 son locales y reversibles; ninguna
toca producción. La curación §3b y el §7 requieren validación contra manual / con Oscar.*
