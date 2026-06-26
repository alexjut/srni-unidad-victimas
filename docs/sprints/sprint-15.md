# Sprint 15 — Estabilización del instrumento + visibilidad RUV + rediseño del login (pre-producción)

**Branch:** `main` (commits directos, según convención de ramas del proyecto)
**Estado:** ✅ Completo (código) · 🟡 Deploy a producción pendiente
**Inicio:** 2026-06-26
**Cierre:** 2026-06-26

---

## Motivación

Tras la reconstrucción del instrumento Territorial V7 y el motor de skip-logic
(commits de junio), una prueba de campo reveló tres problemas concretos que
afectaban la captura real:

1. **La precarga no aparecía.** Ni los datos básicos de la víctima (cédula, edad,
   nombres) ni el hecho victimizante se mostraban precargados, pese a que el
   código de prellenado existía. Los encuestadores tenían que re-teclear datos
   que el RUV ya tiene.
2. **El hecho victimizante estaba oculto.** Por una decisión previa se prellenaba
   "por debajo" y se ocultaba — el encuestador no podía confirmar visualmente el
   dato que venía del RUV.
3. **La obligatoriedad no salía del manual.** Se había marcado 253/268 preguntas
   como obligatorias con una heurística propia, no con el manual oficial 11-MU.

Además, diseño entregó material gráfico nuevo para el login y el buscador.

---

## Objetivos del sprint

1. Desbloquear la precarga de datos básicos de la víctima (cédula, edad, nombres,
   tipo de documento, sexo).
2. Mostrar el hecho victimizante precargado en modo **solo lectura** (no ocultarlo).
3. Alinear la obligatoriedad de las preguntas al **manual oficial 11-MU**.
4. Renovar la identidad visual: fondo del buscador de cédulas y fotos de las
   regiones del login (material de diseño).
5. Dejar el trabajo de Brando (panel web) sincronizado en ambos remotes.

---

## Entregables

### 1. Precarga de datos básicos desbloqueada

El prellenado de todas las preguntas de nivel PERSONA estaba bloqueado por un
candado: si la lista de miembros del hogar llegaba sin ningún miembro marcado
`es_autorizado`, el `useEffect` de prellenado hacía `return` y **no sembraba
nada** (ni cédula, ni edad, ni nombres).

| Antes | Después |
|-------|---------|
| `miembros.find(m => m.es_autorizado) ?? null` → si null, bloquea todo | `… ?? miembros[0] ?? null` → cae al primer miembro (ya ordenado con el autorizado primero) |

Además, **tipo de documento (A3)** y **sexo (A8)** se sembraban con el valor
crudo del RUV (`'CC'`, `'M'`), que nunca coincidía con las opciones numéricas del
instrumento (`'1'`, `'2'`…) y se descartaba en silencio. Se agregaron tablas de
traducción `MAP_TIPO_DOC_A3` y `MAP_GENERO_A8`.

### 2. Hecho victimizante en modo solo lectura

`H_V` (hecho) y `Ocur_HV` (fecha de ocurrencia) dejan de ocultarse. Ahora se
muestran precargados en una tarjeta **"Dato del RUV"** (ícono de candado, fondo
azul), sin controles editables. El encuestador confirma visualmente el dato que
trajo el RUV; no se vuelve a preguntar.

- `PREGUNTAS_OCULTAS_RUV` → renombrado a `PREGUNTAS_RUV_READONLY`.
- Nueva prop `soloLectura` en `PreguntaItem` con render dedicado.

### 3. Obligatoriedad alineada al manual oficial 11-MU

Se contrastó pregunta por pregunta contra el manual `11-MU` (que dice literal
"Obligatorio diligenciamiento" / "Campo no obligatorio"). La heurística previa
quedó casi perfecta: solo **3 campos de contacto** difieren.

| | Obligatorias | Opcionales |
|---|---|---|
| Antes (heurística) | 253 | 15 |
| Después (manual 11-MU) | **250** | **18** |

Cambios (todos OBL → OPC, citados en pág. 45 del manual):
- `Z9A` Teléfono fijo · `Z9C` Otro teléfono de contacto · `Z10` Correo electrónico

Aplicado en el **fixture** (fuente de verdad) y en el **bundle móvil**, con
paridad verificada (268 / 250 / 18 en ambos).

### 4. Identidad visual

- **Buscador de cédulas** (`busqueda.tsx`): el fondo pasa de una URL remota
  (comunidad Emberá) a una **imagen local** del caficultor colombiano → carga
  offline. Optimizada 2048×1365 (1.7 MB) → 1280×853 q82 (401 KB).
- **Login** (`login.tsx`): las 5 fotos de regiones se reemplazan por fotografías
  de comunidades reales (Caribe, Andes, Amazonia, Orinoquía, Insular).
  Optimizadas a 1400 px / q80 (135–397 KB c/u). Se conservan los nombres de
  archivo → sin cambios en `login.tsx`.

### 5. Sincronización del panel web (Brando)

El trabajo de Brando en `frontend` (Nunito Sans, logos institucionales, liquid
glass, administración de usuarios, paramétricas) ya estaba integrado en `main`;
se actualizó el puntero `origin/frontend` (GitHub) para igualarlo a
`azure/frontend` — el trabajo queda respaldado en **ambos remotes**.

---

## Decisiones técnicas

### 1. Fallback al primer miembro en vez de bloquear el prellenado

`ordenarMiembros` ya deja al autorizado primero. Si el backend no marca el flag
`es_autorizado` (caso observado en offline / hogar creado online sin caché),
usar `miembros[0]` es el autorizado de facto. Es preferible sembrar contra el
primer miembro que dejar al encuestador sin ningún dato precargado.

### 2. Mostrar el hecho (read-only) en vez de ocultarlo

La caracterización es posterior a la victimización: el hecho ya se conoce y no
debe re-preguntarse. Pero ocultarlo del todo impedía la confirmación visual.
El modo solo-lectura concilia ambos: visible para confirmar, no editable para
no introducir inconsistencias con el RUV.

### 3. Obligatoriedad como dato, trazable al manual

Cada `obligatoria: true` debe poder justificarse contra el 11-MU. Las preguntas
condicionales siguen `true` (su visibilidad la controla la skip-logic, que ya
existe) — condicionalidad ≠ no-obligatoriedad.

### 4. Imágenes locales, no remotas

La app es offline-first: un fondo servido por URL no carga sin red. Todas las
imágenes de marca pasan a ser assets bundled y optimizados para no inflar el APK.

---

## Archivos creados / modificados

### Nuevos
```
docs/sprints/sprint-15.md
srni-mobile/assets/fondo-busqueda.jpg
```

### Modificados
```
srni-mobile/app/(main)/formulario/[temaId].tsx   (precarga desbloqueada + A3/A8 + H_V read-only)
srni-mobile/app/(auth)/login.tsx                 (vía reemplazo de assets, sin cambio de código)
srni-mobile/app/(main)/busqueda.tsx              (fondo local)
srni-mobile/assets/regiones/{caribe,andina,amazonia,orinoca,insular}.jpg  (nuevas fotos)
srni-backend/apps/formulario/fixtures/perfil_territorial_v7.json  (obligatoriedad 250/268)
srni-mobile/assets/instrumentos/territorial_v7.json              (bundle espejo)
```

### Commits
```
6999857  fix(instrumento): precarga RUV visible + datos persona desbloqueados + obligatoriedad al manual
1c339cc  feat(mobile): fondo del buscador de cédulas → caficultor colombiano
24ed8f4  feat(mobile): nuevas fotos de regiones en el login (comunidades de Colombia)
```
Subidos a ambos remotes (`origin` GitHub + `azure` DevOps).

---

## Verificación

- `npx tsc --noEmit` sobre el mobile: **limpio** (0 errores).
- Tests de skip-logic: **22/22 pasan** (`npx jest skipLogic`).
- Paridad fixture ↔ bundle: 268 / 250 / 18 confirmada por script.

---

## Pendientes para el próximo sprint

| Pendiente | Prioridad |
|-----------|-----------|
| Deploy a producción — servidor `30.0.1.109` (`git archive` + `deploy-all.sh`) | Alta |
| Deploy a producción — APK EAS (`deploy-apk.sh`) con la URL de la OTI | Alta |
| Persistir `victimaFuente` (hoy en memoria) para que el prellenado sobreviva reinicios / re-foco de búsqueda | Media |
| Mapear `municipio_hecho` del RUV a su pregunta destino en el prellenado | Baja |
| Decidir destino de `srni-mobile/assets/regiones/loguin/` (fuentes de diseño sin trackear) | Baja |
