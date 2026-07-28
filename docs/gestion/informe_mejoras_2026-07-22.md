# Informe de mejoras — sesión 2026-07-22

> **Frente:** Migración Oracle legacy (RNIENTREVISTA) ↔ SICAV + alineación del instrumento.
> **Worktree:** `feat/oracle-legacy-writer` (`D:\desarrollo\uv-oracle-writer`).
> **Todo en DRY-RUN / solo lectura. Cero escrituras en producción.** No commiteado (a revisión).

---

## Resumen ejecutivo — qué mejoramos

1. **Se pobló el Oracle local con el catálogo real completo** de RNIENTREVISTA (sin PII),
   por SELECT directo desde prod. Cerró el bloqueo #1 (catálogo truncado a 200 filas).
2. **Se verificó la alineación SICAV↔manual↔Oracle con dato completo**, no con muestra:
   confirmado que **no hay pérdida silenciosa real** de datos.
3. **Se produjo un plan de alineación** de la BD del APK y la **corrección del correo**
   de parentescos (era falsa alarma).
4. Se corrigió un desvío de rumbo: un re-export de bundles hecho sobre la BD equivocada
   (sqlite dev) se **revirtió**; `main` quedó intacto.

---

## 1. Catálogo Oracle completo en local — el cambio grande

| | |
|---|---|
| **Cómo estaba** | Oracle local con **estructura only** (333 tablas, 0 filas). El catálogo de respuestas para el análisis estaba **truncado a 200 filas** (temas 1-2) porque el cliente SQL cortaba el export. `respuestas_oracle.json` tenía `cobertura: PARCIAL`. |
| **Qué hicimos** | Traer el catálogo por **SELECT directo** de 8 tablas de definición (sin PII) desde prod `30.0.1.9/ENTREVISTARN` (solo lectura, **cero footprint**: ni .dmp, ni job, ni archivo en el server) y cargarlo en el Oracle local. Script reproducible `srni-backend/scripts/cargar_catalogo_local.py`. |
| **Cómo quedó** | **9.316 filas** cargadas (GIC_N_PREGUNTAS 1108, GIC_N_RESPUESTAS 3686, GIC_N_INSTRUMENTOXPREG 903, GIC_N_INSTRUMENTOXRESP 3533, +tipos/temas). `respuestas_oracle.json` regenerado → **`cobertura: COMPLETO`** (902 preguntas / 3069 respuestas / 43 huérfanas). Todo el análisis corre **local**, sin depender de prod ni tocar PII. |

**No se trajo** `GIC_N_RESPUESTASENCUESTA` (respuestas reales = transaccional/sensible).

---

## 2. Alineación SICAV ↔ manual ↔ Oracle (verificado con catálogo completo)

| Tema | Cómo estaba | Cómo quedó |
|---|---|---|
| **Parentesco (preg 28)** | Se había escalado a Oscar como "defecto activo: 7 opciones se pierden". | **Falsa alarma confirmada con catálogo completo.** SICAV ofrece las 6 del manual = las 6 escribibles de Oracle. Las 7 huérfanas no las declara el manual ni las ofrece SICAV → nadie puede elegirlas → 0 pérdida. **Correo corregido** (§ deliverable). |
| **Cédula (preg 30)** | Duda: 4 ids escribibles con el mismo texto. | Confirmado con dato completo: los 4 (`93/3852/3853/3854`) son escribibles → **pendiente de negocio** (cuál usa SICAV, el 3854 con 8.620 usos). |
| **Pérdidas silenciosas reales** | Riesgo teórico (procedure traga NO_DATA_FOUND). | **0 casos.** No hay ninguna opción que SICAV ofrezca y Oracle no pueda guardar. |
| **Huérfanas (43)** | Se conocían 10 de 153 (export parcial). | Lista completa: **41 opciones retiradas** (SICAV no las ofrece, ok) + 2 con equivalente escribible (redacción). |
| **Opciones que no cruzan por texto** | Sin medir (catálogo truncado). | **56 artefactos de formato** (los arregla el normalizador) · **178 curación real de redacción** · **75 id_preg mal mapeados** en perfiles derivados · **95 de modelado distinto** (campo abierto/booleano, no se tocan). Lista en `curacion_opciones_sicav_vs_oracle.tsv`. |

---

## 3. Instrumento SICAV (backend ↔ APK) — auditoría de alineación

| | |
|---|---|
| **Cómo estaba** | Sospecha de "error de bd" entre fixture y bundle. |
| **Qué hicimos** | Auditamos los 8 instrumentos fixture↔bundle (resolviendo `$ref:`). |
| **Cómo quedó** | **7/8 alineados al 100%.** Diferencias reales solo en Telefónico (DT_ATENCION/huérfanas T1-T3), Rural-Étnico (DT_ATENCION) y Víctimas-Exterior (A25 opciones) — el **fixture es la fuente correcta**; se arreglan por re-export desde fixture. Documentado en el plan §. **No ejecutado aún** (requiere decisión de versionado). |

> ⚠️ **Desvío corregido:** se intentó regenerar los bundles vía `exportar_a_mobile`, pero
> se hizo sobre el **sqlite dev** (BD equivocada) e introdujo ruido (un `territorial_v7`
> vacío, cambios por capítulo de control). **Se revirtió por completo**; `main` quedó
> **intacto** (solo sus 2 borradores de gestión previos). Lección → memoria [[feedback_handoff_doc]].

---

## 4. Arquitectura (rumbo confirmado)

- **La lógica ya está fuera de la BD:** los 5 bloques de procedures `GIC_*` (PL/SQL con
  COMMIT interno + WHEN OTHERS que traga errores) están **portados a servicios Django**,
  con **24/24 tests de paridad**. La BD tiende a **solo data**. Estrategia strangler-fig
  (Etapa A vía procedures oficiales ahora; Etapa B = Django escribe directo, después).
- El fixture es la fuente viva; los cambios bajan por el pipeline
  `fixture → cargar_perfil → BD → exportar_a_mobile → bundle → APK`. Todo local primero.

---

## 5. Archivos (antes → después)

**Repo principal (`main`):** **sin cambios netos** — el re-export se revirtió. Solo siguen
sus 2 borradores previos (`cierre-julio-2026.md`, `implementacion_capacitacion_despliegue.md`).

**Worktree (`feat/oracle-legacy-writer`), sin commitear (a revisión).** Inventario
completo del diff (verificado por auditoría independiente):

*Nuevos (??):*
| Archivo | Estado |
|---|---|
| `apps/sincronizacion/oracle/respuestas_oracle.json` | regenerado → **COMPLETO** (902/3069/43) |
| `scripts/cargar_catalogo_local.py` | carga catálogo prod→local (reproducible) |
| `apps/sincronizacion/management/commands/generar_catalogo_respuestas.py` | genera el catálogo desde el TSV |
| `apps/sincronizacion/tests/test_resolver_respuestas.py` | tests del resolver |
| `docs/oracle-legacy/query_a_v2_completo.tsv` | export completo del catálogo (versionado) |
| `docs/oracle-legacy/curacion_opciones_sicav_vs_oracle.tsv` | 178 casos de curación (gitignored) |
| `docs/gestion/plan_alineacion_bd_apk.md` | plan de cambios del instrumento |
| `docs/gestion/correo_correccion_parentescos_oscar.md` | correo corregido |
| `docs/gestion/informe_mejoras_2026-07-22.md` | este informe |
| `infra/oracle-local/.env.prod` | credenciales prod EN CLARO (gitignored) — ⚠️ ver §6.4 |

*Modificados (M):*
| Archivo | Estado |
|---|---|
| `apps/sincronizacion/oracle/catalogos.py` | resolver + **normalizador reforzado hoy** (§2 plan): pliega puntuación y `_` |
| `apps/sincronizacion/oracle/mapeo.py` | resolver de respuestas (id_preg + texto) |
| `apps/sincronizacion/management/commands/cargar_hogar_demo_oracle.py` | escenario demo alineado al catálogo |
| `apps/sincronizacion/tests/test_escritor_territorio.py` · `test_resolver_catalogos.py` | tests |
| `docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md` | **§0 handoff** actualizado |
| `.gitignore` | regla `.env.prod` + allowlist `query_a_v2_*.tsv` |

*Huérfano (a borrar):* `docs/oracle-legacy/query_a_v2_parcial_temas_1_2.tsv` — el export
truncado viejo; lo reemplaza el `_completo.tsv`.

> **Tests:** `pytest apps/sincronizacion` → tras regenerar el catálogo, 4 tests
> asertaban el contrato *truncado* (`completo=False`, "no quiere decir que no exista");
> se están actualizando al contrato *completo* preservando la cobertura del camino
> truncado con un catálogo sintético. Los otros 92 pasan (el normalizador no rompió nada).

---

## 6. Pendientes / siguiente paso

1. **Curación de redacción (178)** contra el manual → crosswalk curado (no fuzzy). Ver plan §3.
2. **Investigar 75 id_preg mal mapeados** en perfiles derivados. Plan §4.
3. ~~Fortalecer el normalizador del resolver~~ ✅ **HECHO hoy** (§2 del plan): pliega
   puntuación y `_`, simétrico, sin fuzzy; elimina los 56 artefactos + parte de los 178;
   los 92 tests previos siguen verdes.
4. ⚠️ **Seguridad — credencial de prod EN CLARO.** `infra/oracle-local/.env.prod` guarda
   la clave de `RNIENTREVISTA` en texto plano (gitignored, pero viva en disco).
   **(1) rotarla con OTI** (3a.5, se reusó para leer el catálogo); **(2) borrar `.env.prod`**
   al cerrar el análisis — el catálogo ya está en el Oracle local.
5. **Gobernanza:** `query_a_v2_completo.tsv` (definiciones, **sin PII**) queda versionado;
   confirmar que no hay política que lo impida.
6. **Negocio (Oscar):** Cédula 3854; puntos de atención; mapeo P8; tipos PE/NES.
7. **Enviar** el correo corregido de parentescos (tras tu revisión).
8. **Commitear** el worktree cuando Javier revise; borrar el TSV parcial huérfano.

---

## Anexo — reproducir

```bash
docker start srni-oracle-local                         # Oracle local (catálogo persiste)
# credenciales prod en infra/oracle-local/.env.prod (gitignored)
python scripts/cargar_catalogo_local.py                # recarga catálogo desde prod (RO)
python manage.py generar_catalogo_respuestas ../docs/oracle-legacy/query_a_v2_completo.tsv --fecha 2026-07-22
```
