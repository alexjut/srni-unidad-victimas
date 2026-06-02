# Informe Mensual — Junio 2026 *(en curso)*

**Contrato:** 2226-2026 — Sistema de Caracterización de Víctimas (SRNI)
**Contratista:** Javier Alexander Aguilar Castro · CC 1.030.547.250
**Supervisor:** Oscar Andrés Manosalva García (SRNI)
**Período cubierto:** 1 de junio 2026 → 30 de junio 2026
**Estado:** mes en ejecución — este documento se completa al cierre.

---

## Plan del mes — Qué vamos a trabajar en junio

| Frente | Resultado esperado al cierre de junio | OE asociada |
|---|---|---|
| Integración Brando (panel web) | Pantalla de auditoría con datos reales + campo `codigo_hogar` desde el panel + atención a nuevos pedidos | OE1 |
| Generación automática de `codigo_hogar` | Implementar formato (prefijo municipio + año + consecutivo) y aplicar al crear hogar | OE5, OE6 |
| Despliegue producción UARIV | Aprovisionamiento del servidor por TI + instalación del stack Docker Compose + pruebas con encuestadores | OE4, OE9 |
| Esquema propio de integración eventual con Oracle | Diseño documentado de tablas espejo / staging para futura integración (sin tocar Oracle prod) | OE5 |
| Atención de hallazgos abiertos | Preguntas tipo PERSONA por miembro · `cliente_uuid` para idempotencia de cola · versionado de instrumentos | OE1, OE2 |
| QA por instrumento | Validación de las 1 001 preguntas activas instrumento por instrumento | OE2 |
| Documentación arquitectónica | ADRs nuevos (decisiones de mayo/junio que no estaban formalizadas) + actualización `docs/estado-actual.md` | OE6, OE8 |
| Coordinación supervisor / TI | Anexo técnico entregado a TI · seguimiento a aprobación de servidor · eventual solicitud Oracle | OE7, OE9 |

---

## Índice por obligación

| OE | Tema | Carpeta | Estado |
|---|---|---|---|
| OE1 | Desarrollo, mantenimiento, documentación y soporte | [`OE1-desarrollo/`](OE1-desarrollo/README.md) | 🟡 En curso |
| OE2 | Captura, procesamiento y calidad de datos | [`OE2-datos/`](OE2-datos/README.md) | 🟡 En curso |
| OE3 | Medidas de seguridad — protección PII | [`OE3-seguridad/`](OE3-seguridad/README.md) | 🟢 Mantenimiento |
| OE4 | Diseño e implementación soluciones tecnológicas | [`OE4-arquitectura/`](OE4-arquitectura/README.md) | 🟡 Despliegue prod |
| OE5 | Estructura de bases de datos | [`OE5-bd/`](OE5-bd/README.md) | 🟡 Esquema integración |
| OE6 | Modelos de datos documentados | [`OE6-modelos/`](OE6-modelos/README.md) | 🟡 ADRs nuevos |
| OE7 | Reuniones y coordinación con supervisor | [`OE7-reuniones/`](OE7-reuniones/README.md) | 📝 Pendiente actas |
| OE8 | Carga mensual de documentos | [`OE8-informes/`](OE8-informes/README.md) | 🔄 Este informe |
| OE9 | Actividades adicionales | [`OE9-adicionales/`](OE9-adicionales/README.md) | 📝 Trámites |
| **EXTRAS** | Trabajo por fuera del cronograma | [`EXTRAS-actividades-adicionales/`](EXTRAS-actividades-adicionales/README.md) | 🟡 En curso |

---

## Enlaces

- Estado del proyecto: [`docs/estado-actual.md`](../../docs/estado-actual.md)
- Sprints: [`docs/sprints/`](../../docs/sprints/)
- Repos:
  - Azure DevOps (oficial UARIV): `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04`
  - GitHub (backup): `github.com/alexjut/srni-unidad-victimas`
