# OE1 — Desarrollo, mantenimiento, documentación y soporte

> **Obligación contractual:** *Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante julio se ejecutó un **correctivo sobre el módulo B. Datos Básicos** del
formulario móvil de caracterización, atendiendo dos defectos reportados en una
entrevista real (hogar de 3 miembros), y se llevó a producción.

**Bug 1 — Hidratación de la precarga por CADA miembro del hogar.**
Las preguntas ya conocidas (nombres, fecha de nacimiento, años, grupo etario, tipo
y número de documento) salían vacías ("0 de 3 personas respondidas") porque el
prellenado solo sembraba al miembro autorizado y desde una fuente única y volátil.

- El prellenado ahora **itera todos los miembros** y siembra fecha (A6), años (B9),
  grupo etario (B10) y sexo (A8) desde `MiembroHogarResumen` — el mismo origen que
  usa el motor de skip-logic, disponible para todos online y offline.
- El autorizado recibe además nombres, tipo y número de documento desde su registro
  del RUV; los miembros adicionales creados offline reciben el número de documento
  desde su payload local.
- **B9 (años) y B10 (grupo etario)** pasan a **calculados no editables**, con
  recálculo automático desde la fecha de nacimiento (campo automático del manual).
- **Tipo de documento (A3)** con *fallback por edad* cuando no hay dato guardado
  (Registro Civil 0-6, Tarjeta de Identidad 7-17, Cédula 18+), según el manual.

**Bug 2 — Condicional de embarazo y campo "¿Cuántas?" (semanas de gestación).**
Al responder "Sí" a embarazo no aparecía el campo para capturar la cantidad.

- Se limpió la pregunta de embarazo (B2): opciones **"Sí, ¿Cuántas?" / "No"** y se
  eliminó una opción huérfana mal reconstruida.
- Se creó la **pregunta hija numérica "¿Cuántas?" (B2_CANT)**, que aparece solo
  cuando embarazo = "Sí".
- **Desviación deliberada del manual 520.06.06-1, avalada por el líder funcional
  (Alejandro):** embarazo y madre lactante se habilitan para **mujeres de 12 años en
  adelante y sin tope superior** (`sexo == '2' and edad >= 12`), en vez del rango
  12-50 del manual.
- Aplicado a los **4 perfiles**: Buenaventura, San Andrés, Territorial y Urbano-Étnico.

## Evidencia que soporta esta actividad

- Commit en `main` (GitHub + Azure DevOps): `3249a85` — *feat(modulo-b): precarga por
  miembro + condicional embarazo/gestación (Bug 1 y Bug 2)*.
- Archivos de código:
  - `srni-mobile/app/(main)/formulario/[temaId].tsx` (prellenado por miembro,
    B9/B10 calculados, fallback A3 por edad).
  - `srni-backend/apps/formulario/fixtures/perfil_{buenaventura,san_andres,territorial,urbano_etnico}_v*.json`
    y sus bundles en `srni-mobile/assets/instrumentos/`.
  - `srni-backend/scripts/patch_bug2_embarazo_gestacion.py` (reconciliación idempotente).
- Verificación: `tsc --noEmit` **0 errores** · `jest` **77/77** (incluye prueba de
  paridad `datosBasicosB2.test.ts` que corre el motor real contra el bundle).
- Publicado en ambos remotes (GitHub + Azure DevOps).

## Pendiente / siguiente paso

- Siembra en el servidor (`cargar_perfil` ×4 + `exportar_a_mobile`), reconciliación
  del UUID de la pregunta B2_CANT y build del APK.
- Verificación en el APK real del hogar de 3 miembros.
