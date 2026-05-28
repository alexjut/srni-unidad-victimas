# Informe Mensual — Mayo 2026

**Contrato:** 2226-2026 — Sistema de Caracterización de Víctimas (SRNI)
**Contratista:** Javier Alexander Aguilar Castro · CC 1.030.547.250
**Supervisor:** Oscar Andrés Manosalva García (SRNI)
**Período cubierto:** 1 de mayo 2026 → 28 de mayo 2026
**Sprints ejecutados:** 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21

---

## Resumen ejecutivo

| Indicador | Valor |
|---|---|
| Commits realizados en mayo | **80** |
| Sprints completados | **16** (6 a 21) |
| Líneas de código netas agregadas | ~15 000 |
| Instrumentos cargados | 8 (ASISTENCIA, TERRITORIAL, BUENAVENTURA, SAN_ANDRÉS, TELEFÓNICO, URBANO_ÉTNICO, RURAL_ÉTNICO, VÍCTIMAS_EXTERIOR) |
| Preguntas activas en BD | 1 001 |
| Departamentos / municipios DANE | 33 / 1 102 |
| Direcciones Territoriales UARIV | 21 |
| Puntos de atención | 41 (placeholder; oficial pendiente UARIV) |
| Componentes del sistema | 3 (backend Django, app móvil Expo, panel web React) |
| Ramas Git al día | 3 (`main`, `frontend`, `develop`) — en Azure DevOps + GitHub |

---

## Índice por obligación

| OE | Tema | Carpeta | Estado del mes |
|---|---|---|---|
| OE1 | Desarrollo, mantenimiento, documentación y soporte | [`OE1-desarrollo/`](OE1-desarrollo/README.md) | ✅ Alta producción |
| OE2 | Captura, procesamiento y calidad de datos | [`OE2-datos/`](OE2-datos/README.md) | ✅ Completo |
| OE3 | Medidas de seguridad — protección PII | [`OE3-seguridad/`](OE3-seguridad/README.md) | ✅ Hardening Sprint 11 + 18-G |
| OE4 | Diseño e implementación soluciones tecnológicas | [`OE4-arquitectura/`](OE4-arquitectura/README.md) | ✅ Stack completo en local |
| OE5 | Estructura de bases de datos | [`OE5-bd/`](OE5-bd/README.md) | ✅ Migraciones versionadas |
| OE6 | Modelos de datos documentados | [`OE6-modelos/`](OE6-modelos/README.md) | ✅ Documentado |
| OE7 | Reuniones y coordinación con supervisor | [`OE7-reuniones/`](OE7-reuniones/README.md) | 📝 Completar con actas |
| OE8 | Carga mensual de documentos | [`OE8-informes/`](OE8-informes/README.md) | 🔄 Este informe es la entrega |
| OE9 | Actividades adicionales | [`OE9-adicionales/`](OE9-adicionales/README.md) | 📝 Completar trámites |

---

## Hitos del mes

- **Semana 1 (4-8 mayo):** Sprint 7 — UX rediseño login + flujo caracterización + Gemini batch.
- **Semana 2 (9-15 mayo):** consolidación Sprint 7 y preparación Sprint 8.
- **Semana 3 (16-22 mayo):** Sprints 8, 9, 10, 11 — motor formulario end-to-end, sincronización masiva, reportes producción, hardening seguridad.
- **Semana 4 (22-28 mayo):** Sprints 12 a 21 — panel web, backend habilitador, mobile flujo cosido, instrumentos completos, in-memory architecture, ubicación atención, preguntas PERSONA por miembro, calendario nativo, wizard de miembros.

---

## Enlaces

- Mapa completo del estado del proyecto: [`docs/estado-actual.md`](../../docs/estado-actual.md)
- Documentación detallada por sprint: [`docs/sprints/`](../../docs/sprints/)
- Reporte QA perfil por perfil: [`docs/qa-perfiles-sprint20.md`](../../docs/qa-perfiles-sprint20.md)
- Repos:
  - Azure DevOps (oficial UARIV): `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04`
  - GitHub (backup): `github.com/alexjut/srni-unidad-victimas`
