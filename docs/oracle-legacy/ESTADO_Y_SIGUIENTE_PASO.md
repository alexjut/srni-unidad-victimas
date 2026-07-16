# Oracle legacy → SICAV — Estado y siguiente paso

> **Traspaso de sesión.** Qué hicimos, dónde está todo, qué falta y **con qué empezar
> la próxima vez** (incluye el prompt listo para pegar). Fecha de corte: 2026-07-16.
> **Worktree:** `feat/oracle-legacy-writer` en `D:\desarrollo\uv-oracle-writer`.
> Todo lo hecho fue **solo lectura** contra Oracle (local + prod), excepto un único
> `DROP` autorizado de una master table huérfana. La escritura real a Oracle **NO
> está activada** (todo en DRY-RUN).

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

- **Commiteado y pusheado** en `feat/oracle-legacy-writer`: `b504d79` (Etapa A + ResolverCatalogos, 17 archivos), en ambos remotes (`origin` + `azure`).
- **Todo en DRY-RUN.** La ruta `--confirmar` aborta a propósito hasta resolver los pendientes de negocio.
- Máquina de estados hoy ejecuta **HOGAR → PERSONA → MIEMBRO**. Los pasos **TERRITORIO y RESPUESTA están diseñados pero NO cableados** al flujo (esperan el mapeo de catálogos geográficos/instrumento).
- Docs de análisis en `docs/oracle-legacy/` están **gitignored** por convención del equipo (menos `oracle-local-setup.md` y este archivo, que son traspaso/arquitectura sin datos de prod).

---

## 3. Qué falta (pendientes)

### 3a. Bloqueantes de NEGOCIO (los resuelve Javier con Oscar/UARIV — no los decido yo)
1. **Usuario/perfil de servicio SICAV en Oracle** → poner valor en `settings.ORACLE_LEGACY['USUARIO_SERVICIO_ID' / 'PERFIL_SERVICIO_ID']`.
2. **Mapeo P8** (campos vivos de `GIC_INSERT_PERSONAS`): `ID_SINIESTRO`→hecho/siniestro (`HechoVictima`), `ID_DECLAR`→declaración/FUD, `T_VICTIMA`→tipo de víctima.
3. **Tipo de documento PE (PEP) y NES** — sin equivalente en `GIC_TIPODOC`: ¿mapear a Otro(13)/Indocumentado(14) o pedir alta de catálogo?
4. **SISBEN** (N3): ¿SICAV usa el cruce `TEMP_SISBEN`?
5. **Rotar clave RNIENTREVISTA** (se usó para lectura/export).

### 3b. Incrementos TÉCNICOS (los puedo hacer yo, en DRY-RUN)
6. **Cablear TERRITORIO + RESPUESTA** en la máquina de estados (`escritor.py`).
7. **Resolver territorio** SICAV→Oracle desde el crosswalk `catalogos_oracle.json` (1370 filas) por **nombre** (los ids son surrogate Oracle, NO DANE).

### 3c. Después (no ahora)
- Escalón 1 del rollout: 1 hogar contra Oracle **local** con `--confirmar` (requiere ResolverCatalogos completo + tu aprobación).
- Etapa B (escritura directa Django) — fase separada, cuando se retire la app vieja.

---

## 4. Con qué EMPEZAR la próxima sesión (recomendación)

**Empezar por el incremento técnico 6+7** (cablear TERRITORIO+RESPUESTA y resolver territorio desde el crosswalk), porque:
- No depende de negocio (avanza sin esperar a Oscar).
- Deja el DRY-RUN mostrando el flujo **completo** de un hogar (hogar→personas→miembros→territorio→respuestas), que es lo que se revisa antes de aprobar el escalón 1.
- En paralelo, Javier junta las decisiones de negocio (3a) para la siguiente.

---

## 5. Qué DECIR la próxima sesión (prompt listo para pegar)

> Retomamos la migración Oracle legacy → SICAV, worktree `feat/oracle-legacy-writer`.
> Lee `docs/oracle-legacy/ESTADO_Y_SIGUIENTE_PASO.md` para el contexto completo.
>
> Sigue todo en **DRY-RUN, solo lectura** contra Oracle. Tarea: **incrementos
> técnicos 6 y 7** del documento:
> 1. Cablear los pasos **TERRITORIO** y **RESPUESTA** en la máquina de estados
>    (`apps/sincronizacion/oracle/escritor.py`), siguiendo el mismo patrón de
>    HOGAR/PERSONA/MIEMBRO (invocar → verificar por SELECT → ledger).
> 2. Implementar `resolver_territorio` usando el crosswalk real
>    `catalogos_oracle.json` (cruce por **nombre** DT/municipio/punto, porque los
>    ids son surrogate Oracle, no DANE), con error claro si no hay match.
> 3. Tests de los nuevos resolvers + re-correr `escribir_a_oracle` en DRY-RUN
>    mostrando el flujo completo de un hogar.
> No commitees hasta que yo revise. Si algo necesita decisión de negocio, márcalo
> pendiente (no lo adivines).

*(Si en vez de eso quieres avanzar los bloqueantes de negocio, dime cuáles resolviste
de la sección 3a y los cableo.)*

---

## 6. Punteros rápidos

- Código Etapa A: `srni-backend/apps/sincronizacion/` (models, oracle/, management/, tests/).
- Crosswalk catálogos: `apps/sincronizacion/oracle/catalogos.py` + `catalogos_oracle.json`.
- Diseño Etapa A: `docs/oracle-legacy/diseno_etapa_a_escritura.md`.
- Auditoría + veredicto a1/a2: `docs/oracle-legacy/auditoria_diseno_legacy.md`.
- Ruta de escritura (análisis PL/SQL): `docs/oracle-legacy/ruta_escritura.md`.
- Correr DRY-RUN: `python manage.py escribir_a_oracle --hogar <cod> --settings=srni.settings.development`.
- Oracle local: `cd infra/oracle-local && docker compose --env-file .env up -d`.
