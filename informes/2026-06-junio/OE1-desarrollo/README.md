# OE1 — Desarrollo, mantenimiento, documentación y soporte

> **Obligación contractual:** *Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante junio se ejecutaron actividades de desarrollo, mantenimiento correctivo y
soporte sobre la solución móvil y el backend, además de la atención de pedidos del
panel web (Brando) y de la supervisión.

**Frentes ejecutados este mes:**

- Atención al panel web (Brando): pantalla de auditoría con datos reales del endpoint `/api/auditoria/logs/` y uso de `codigo_hogar` directo en lugar de fallback.
- Generación automática del `codigo_hogar` (modelo Hogar: prefijo municipio + año + consecutivo).
- Atención de hallazgos abiertos: preguntas tipo PERSONA por miembro, `cliente_uuid` para idempotencia de cola de sincronización, versionado de instrumentos.
- **Estabilización pre-producción del instrumento Territorial V7 (26-jun, sprint 15):**
  - Precarga de datos básicos de la víctima desbloqueada (cédula, edad, nombres, tipo de documento y sexo) — se corrigió un candado que impedía el prellenado y se añadió la traducción de códigos del RUV a las opciones del instrumento.
  - El hecho victimizante ahora se muestra precargado en modo **solo lectura** ("Dato del RUV"), en vez de ocultarse.
  - Obligatoriedad de las preguntas alineada al **manual oficial 11-MU**: 250/268 obligatorias (antes 253), aplicado en el fixture y el bundle móvil.
- **Identidad visual móvil:** nuevo fondo del buscador de cédulas (caficultor colombiano) y nuevas fotos de las 5 regiones del login (comunidades de Colombia), con material entregado por diseño y optimizado para el APK.
- Sincronización del trabajo del panel web (Brando) en ambos remotes (GitHub + Azure DevOps).
- Mantenimiento correctivo según se presentó.

## Evidencia que soporta esta actividad

- Commits versionados en `main` (GitHub + Azure DevOps), entre ellos los del 26-jun:
  - `6999857` fix(instrumento): precarga RUV visible + datos persona desbloqueados + obligatoriedad al manual
  - `1c339cc` feat(mobile): fondo del buscador de cédulas → caficultor colombiano
  - `24ed8f4` feat(mobile): nuevas fotos de regiones en el login (comunidades de Colombia)
- Sprint documentado: [`docs/sprints/sprint-15.md`](../../../docs/sprints/sprint-15.md) (y serie `docs/sprints/`).
- Archivos de código: `srni-mobile/app/(main)/formulario/[temaId].tsx`, `srni-mobile/app/(main)/busqueda.tsx`, `srni-mobile/assets/regiones/`, `srni-backend/apps/formulario/fixtures/perfil_territorial_v7.json`, `srni-mobile/assets/instrumentos/territorial_v7.json`.
- Verificación: `tsc --noEmit` limpio · 22/22 tests de skip-logic.
