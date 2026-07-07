# Sprint 19 — Barrido de instrumentos a producción + motor AND + constancia + reset de demo

**Branch:** `main` (commits directos, según convención de ramas del proyecto)
**Estado:** ✅ Completo · ✅ Desplegado a producción (backend + APK vc50) · 🔒 Fase 1 (cifrado) bloqueada por Oracle
**Inicio:** 2026-07-06
**Cierre:** 2026-07-06
**Remotes:** GitHub (`origin`) + Azure DevOps (`azure`) — `git push all main`

---

## Motivación

Tras el despliegue de Territorial V8 (sprint anterior), quedaba un backlog de 5 frentes
identificados en las memorias del proyecto. El objetivo del sprint fue cerrarlos **en orden
(P1→P5)** y llevar lo aplicable a producción el mismo día, incluyendo el redeploy del código
backend y el rebuild del APK.

Puntos abordados:

1. **P1 — Instrumentos:** propagar a los demás perfiles el barrido que solo tenía Territorial,
   y corregir defectos de skip-logic detectados al auditar.
2. **P2 — Motor skip-logic (condiciones AND):** el motor solo hacía OR; el manual exige ~15
   reglas "étnico Y otra respuesta".
3. **P3 — Captura grupal (constancia tutor/cuidador):** el móvil adjuntaba el documento pero
   no se persistía en el servidor.
4. **P4 — Cifrado Fase 1:** SQLCipher + hash SHA-256 con sal (bloqueado por Oracle).
5. **P5 — Limpieza:** huérfanas en prod, comando obsoleto, archivos sin trackear.

---

## Entregables

### P1 — Instrumentos (✅ en producción)

- **Bug corregido `A30→B17` (Territorial V8, ya estaba en prod):** la regla usaba
  `valor_trigger='1'` sobre un origen BOOLEAN. El motor hardcodea las respuestas BOOLEAN como
  `"true"/"false"` y parte el trigger por comas, por lo que `'1'` **nunca disparaba** → la
  pregunta B17 ("¿en qué tipo de territorio?") quedaba **oculta para siempre** para quien habita
  territorio colectivo. Corregido a `'true'` en el script fuente `migrar_territorial_v7_a_v8.py`,
  el fixture y el bundle. **Verificado vivo en prod** (`A30→B17 = true`).
- **Barrido V8 portado a Buenaventura, San Andrés y Urbano Étnico:** aplicados los cambios del
  barrido que corresponden por código compartido con Territorial:
  - Multi-select: `C6A, C17A, I1A1, I10A, I11A, PL21A` → `LISTA_MULTIPLE`.
  - DIVIPOLA: `RR1, RR6` → `COMBO_DINAMICO` (selector de municipio).
  - Reglas de skip-logic portables (cadena de primas L22, `A30→B17`, cadena Z de identificación)
    con **guarda de similitud de texto ≥0.85** para evitar falsos positivos.
  - Resultado: Buenaventura 183→**199** reglas, San Andrés 183→**199**, Urbano 67→**74**.
  - Herramienta nueva reusable: `srni-backend/scripts/portar_barrido_v8_a_perfil.py` (determinista,
    preserva el indent del fixture; dos reglas dudosas quedaron sin portar para revisión manual).
- **Asistencia:** bundle validado limpio (105 preg / 43 reglas, 0 rotas) — ya estaba en prod.
- **TERRITORIAL V7 desactivado en prod** (`activo=False`): era un cascarón (0 caps) que aún
  aparecía en el selector. Nuevo comando `desactivar_instrumento --codigo --ver` para retirarlo
  sin borrar su histórico.

### P2 — Motor skip-logic: condiciones AND (✅ en producción)

El motor solo evaluaba **O** `pregunta_origen` **O** `expresion_origen`, y hacía OR entre reglas.
Ahora `expresion_origen` puede **referenciar la respuesta de otra pregunta por su `codigo_externo`**:
cualquier nombre que no sea variable de contexto (`edad/sexo/etnia/ruv_incluido`) se resuelve contra
las respuestas capturadas. Esto habilita AND mixto, p.ej. `etnia == 'indigena' and D6 == '2'`, y
cierra los casos "étnico Y otra respuesta" (RR2-RR5A, I30, H11/H12A).

- Móvil `src/services/skipLogic.ts`: `_evaluarExpresion`/`_varContexto` reciben `respuestas`;
  soporte de pertenencia (`==`) para orígenes multi-select. **+4 tests (40/40 pasan).**
- Backend `apps/formulario/views.py`: `evaluar_expresion_segura(expr, contexto, respuestas)`
  (ámbito = respuestas + contexto con precedencia). Espejo exacto del móvil.
- Convención: valores del lado derecho entre comillas (`'2'`, `'true'`) para paridad móvil/backend.
- **Verificado vivo en prod:** firma `(expresion, contexto, respuestas)` + prueba AND = `True`.
- **Pendiente (dato, no motor):** reescribir las ~15 reglas concretas para USAR el AND requiere las
  condiciones exactas del manual — no se inventan.

### P3 — Constancia de tutor/cuidador (✅ en producción)

- `MiembroHogar`: campos `constancia` (FileField), `constancia_nombre`, `constancia_subida_en`
  (migración `hogares.0006`).
- Endpoint `POST /api/hogares/{id}/subir-constancia/` (multipart) con validación de rol
  (solo `TUTOR`/`CUIDADOR_PERMANENTE`) y auditoría (`LogAcceso` acción `SUBIR_CONSTANCIA`,
  migración `auditoria.0007`).
- Serializer expone los campos (lectura). **3 tests** (OK / 400 no-tutor / 404 hogar ajeno).
- **Migraciones aplicadas y verificado vivo en prod** (campo `constancia` presente).
- **Pendiente:** lado móvil (POST real del archivo + sincronización offline de la cola binaria)
  y refinamiento visual.

### P4 — Cifrado Fase 1 (🔒 bloqueado)

SQLCipher en reposo + hash SHA-256 con sal **no se implementa en fase mock**: requiere DDL,
credenciales y datos reales de Oracle. Documentado como bloqueado (regla del proyecto:
no migrar mock→Oracle sin contexto). Sin acción posible en este sprint.

### P5 — Limpieza (✅)

- Huérfanas `T1_te/T2_te/T3_te`: **ya estaban en 0 en prod** (limpiadas en sprint previo) — el
  DELETE resultó innecesario.
- Comando obsoleto `cargar_territorial_v7.py` **eliminado** (hardcodeado, divergía del fixture;
  el cargador vigente es `cargar_perfil --fixture`).

---

## Decisiones técnicas

1. **Fixture como fuente de verdad, bundle regenerado por pipeline.** Los cambios de P1 se hicieron
   sobre los fixtures y el bundle se regeneró con `cargar_perfil` + `exportar_a_mobile` (los UUID del
   bundle son deterministas por perfil). No se editan bundles a mano.
2. **Guarda de texto al portar reglas.** Portar una regla de Territorial a otro perfil solo si ambos
   extremos existen Y el texto de la pregunta origen coincide ≥0.85 (mismo criterio que los
   generadores de perfil). Dos reglas quedaron sin portar (Z7→VEREDA 0.81, Z17→Z18 0.65) para
   revisión manual — se prefirió no-portar antes que cablear una regla sobre una pregunta distinta.
3. **AND por referencia a respuestas, no por reestructurar reglas.** El operador `and` del evaluador
   ya existía; la única capacidad faltante era referenciar respuestas por código. Extensión mínima y
   retro-compatible en ambos motores.
4. **Constancia gestionada por acción dedicada** (no escritura directa del serializer), con validación
   de rol y auditoría — coherente con el resto de operaciones de hogares.

---

## Archivos creados / modificados

### Nuevos
- `srni-backend/scripts/portar_barrido_v8_a_perfil.py`
- `srni-backend/scripts/reset_conservar_hogar05.py`
- `srni-backend/scripts/reset_y_demo_territorial.py`
- `srni-backend/apps/formulario/management/commands/desactivar_instrumento.py`
- `srni-backend/apps/hogares/migrations/0006_miembrohogar_constancia_and_more.py`
- `srni-backend/apps/auditoria/migrations/0007_alter_logacceso_accion.py`
- `srni-backend/apps/hogares/tests/test_constancia.py`
- `docs/sprints/sprint-19.md`

### Modificados
- Fixtures: `perfil_territorial_v8.json`, `perfil_buenaventura_v7.json`, `perfil_san_andres_v7.json`,
  `perfil_urbano_etnico_v1.json`
- Bundles: `territorial_v8.json`, `buenaventura_v7.json`, `san_andres_v7.json`, `urbano_etnico_v1.json`,
  `index.json`
- `srni-mobile/src/services/skipLogic.ts` (+ `__tests__/skipLogic.test.ts`)
- `srni-backend/apps/formulario/views.py`
- `srni-backend/apps/hogares/{models,serializers,views}.py`
- `srni-backend/apps/auditoria/models.py`
- `srni-backend/scripts/migrar_territorial_v7_a_v8.py`
- `srni-backend/apps/formulario/management/commands/crear_instrumentos_base.py`
- Eliminado: `srni-backend/apps/formulario/management/commands/cargar_territorial_v7.py`

### Commits (main → GitHub + Azure)
- `9a9780f` fix(instrumento): A30→B17 trigger 'true' + porta barrido V8 a Buenaventura/San Andrés/Urbano
- `d34ef67` feat(skip-logic): condiciones AND vía referencia a respuestas de otras preguntas
- `ed89bdb` feat(hogares): persistir constancia de tutor/cuidador + endpoint de subida
- `7338993` chore(formulario): comando desactivar_instrumento + retira cargar_territorial_v7
- `<sprint-19>` docs(sprint-19): cierre + scripts de ops (reset/porta barrido)

---

## Verificación

- **Tests móvil:** `skipLogic.test.ts` 40/40 (incl. 4 nuevos de AND).
- **Tests backend:** `test_constancia.py` 3/3. (Nota: 2 tests pre-existentes de
  `test_cargar_diccionario` fallan en `main` — no relacionados con este sprint, son del loader.)
- **Validación de bundles:** 0 reglas rotas en los 8 instrumentos; los triggers BOOLEAN vacíos
  restantes son revelado progresivo intencional (no bugs).
- **Prod (post-deploy):** `A30→B17=true`, `evaluar_expresion_segura(expresion, contexto, respuestas)`
  con AND funcional=True, campo `constancia` presente, HTTP 200, datos íntegros.

---

## Deploy a producción (06-jul) — realizado

**Instrumentos (data):** backup `dumpdata formulario` → `cargar_perfil --reemplazar` de los 4 perfiles
→ `desactivar TERRITORIAL V7`. Verificado (276/199/199/74 reglas, V7 inactivo).

**Código backend (imagen horneada):** tarball de archivos cambiados → `~/caracterizacion/srni-backend`
→ rebuild + `up -d` + `migrate`. **APK vc50** compilado en EAS y publicado en `/movil/app.apk`
(backup `.bak` de la anterior; servido HTTP 200, 78.7 MB).

### ⚠️ Hallazgo crítico durante el deploy — corregido

Se usó por error el compose equivocado (`~/caracterizacion/docker-compose.yml`) en vez del real
(`infra/deploy/docker-compose.caracterizacion.yml`), y sin `--env-file`. Como el compose real
resuelve `SECRET_KEY: ${SECRET_KEY}` desde `~/caracterizacion/.env` (que Compose v2 NO lee si no
se pasa `--env-file`), el `SECRET_KEY` quedó vacío → gunicorn crash-loop → **502 en prod por unos
minutos**. Restaurado con `docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml
up -d --force-recreate cz_backend cz_celery`. Recursos basura del stack paralelo eliminados.
**Cero pérdida de datos** (el volumen `caracterizacion_cz_pgdata` persiste entre recreates).
Método correcto documentado en la memoria `reference_deploy_backend_prod`.

### Reset de datos de demo (post-deploy, a pedido)

Se conservó **solo el hogar "05"** (autorizado doc `9990100005`, 9 miembros, 1 sesión, 59 respuestas
= ejemplo completo) y se borró el resto (2 hogares, 3 miembros, 2 sesiones, 42 respuestas). Las 12
víctimas restantes quedaron vírgenes (`fecha_ult_caracterizacion=None`, `habilitado=True`), listas
para caracterizar desde 0. Backup previo en el servidor. Script reusable
`scripts/reset_conservar_hogar05.py` (dry-run por defecto).

---

## Pendientes para el próximo sprint

| Pendiente | Prioridad |
|-----------|-----------|
| Reescribir las ~15 reglas del manual para USAR el AND (RR2-RR5A, I30, H11/H12A) con condiciones exactas | Alta |
| Lado móvil de la constancia: POST del archivo + sincronización offline en la cola binaria | Alta |
| Replicar el barrido V8 a Asistencia + perfiles étnicos restantes (Rural étnico, Exterior) | Media |
| Drift preexistente fixture↔bundle en Rural étnico (106/105) y Telefónico (66/67) + nombres — resolver aparte | Media |
| Fase 1: cifrado SQLCipher + hash SHA-256 (desbloquea al tener DDL/credenciales Oracle) | Bloqueada |
| Reglas ST/IF (Buenaventura) y SAI (San Andrés) desde su flujograma visual | Media |
| Decidir destino de `srni-mobile/assets/regiones/loguin/` y `docs/presentaciones/` (sin trackear) | Baja |
