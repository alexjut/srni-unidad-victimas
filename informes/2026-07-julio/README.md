# Informe Mensual — Julio 2026 *(en curso)*

**Contrato:** 2226-2026 — Sistema de Caracterización de Víctimas (SRNI)
**Contratista:** Javier Alexander Aguilar Castro · CC 1.030.547.250
**Supervisor:** Oscar Andrés Manosalva García (SRNI)
**Período cubierto:** 1 de julio 2026 → 31 de julio 2026
**Estado:** cerrado — *actualizado al 05-ago-2026, con evidencia física en cada carpeta* (formato del supervisor en [`COPIAR-PEGAR-FORMATO-SUPERVISOR.md`](COPIAR-PEGAR-FORMATO-SUPERVISOR.md)).

---

## Plan del mes — Qué vamos a trabajar en julio

| Frente | Resultado esperado al cierre de julio | OE asociada |
|---|---|---|
| Módulo B. Datos Básicos (correctivo) | Precarga por cada miembro del hogar + condicional de embarazo/gestación en los 4 perfiles | OE1, OE2, OE6 |
| Réplica de estabilización a más perfiles | Llevar los ajustes del manual a Asistencia y los perfiles restantes | OE1, OE2 |
| Verificación en Pruebas y cascada a producción | Validación en APK real + despliegue (backend + bundle + APK) | OE4, OE9 |
| Coordinación supervisor / TI | Seguimiento a pendientes de servidor y aprobaciones | OE7, OE9 |

*(El plan se completará a medida que avance el mes.)*

---

## Índice por obligación

| OE | Tema | Carpeta | Estado |
|---|---|---|---|
| OE1 | Desarrollo, mantenimiento, documentación y soporte | [`OE1-desarrollo/`](OE1-desarrollo/README.md) | 🟢 Módulo B: precarga por miembro + condicional embarazo/gestación (commit `3249a85`, en producción) |
| OE2 | Captura, procesamiento y calidad de datos | [`OE2-datos/`](OE2-datos/README.md) | 🟢 Fixtures + bundles de 4 perfiles actualizados (B2/B2_CANT) |
| OE3 | Medidas de seguridad — protección PII | [`OE3-seguridad/`](OE3-seguridad/README.md) | 🟢 PII cifrada + búsqueda por hash + doble llave (14,5 % sin tipo de doc) + constancia de solo-lectura |
| OE4 | Diseño e implementación soluciones tecnológicas | [`OE4-arquitectura/`](OE4-arquitectura/README.md) | 🟢 Cascada del módulo B + integración con la base de la entidad por escalones (piloto en producción 28-jul) |
| OE5 | Estructura de bases de datos | [`OE5-bd/`](OE5-bd/README.md) | 🟢 Estructura del padrón (5,9 M) + modelo de identidad ambigua + réplica local del legado |
| OE6 | Modelos de datos documentados | [`OE6-modelos/`](OE6-modelos/README.md) | 🟢 Reglas skip-logic B2/B2A/B2_CANT (desviación avalada) |
| OE7 | Reuniones y coordinación con supervisor | [`OE7-reuniones/`](OE7-reuniones/README.md) | 🟢 Acta de constitución + informe quincenal + informe de mejoras |
| OE8 | Carga mensual de documentos | [`OE8-informes/`](OE8-informes/README.md) | 🟢 Informe consolidado con **33 archivos de evidencia física** por obligación |
| OE9 | Actividades adicionales | [`OE9-adicionales/`](OE9-adicionales/README.md) | 🟢 Solicitud de acceso al Parametrizador + reporte del 24 % sin identidad + decisiones de negocio |
| **EXTRAS** | Trabajo por fuera del cronograma | [`EXTRAS-actividades-adicionales/`](EXTRAS-actividades-adicionales/README.md) | 🟢 Ruta de escritura al legado (piloto en producción) + carga del padrón real de 5.926.004 víctimas |

---

## Evidencia física

Cada obligación tiene una subcarpeta **`evidencias/`** con los artefactos que la
respaldan: inventarios extraídos de la base de producción, estructura y volumen
de las tablas, salida de la suite de pruebas, histórico de cambios del
repositorio y los documentos técnicos producidos en el mes.

**33 archivos de evidencia** repartidos en las 10 carpetas. El inventario completo
está en [`OE8-informes/evidencias/inventario-documentos-julio.txt`](OE8-informes/evidencias/inventario-documentos-julio.txt).

---

## Enlaces

- Estado del proyecto: [`docs/estado-actual.md`](../../docs/estado-actual.md)
- Sprints: [`docs/sprints/`](../../docs/sprints/)
- Repos:
  - Azure DevOps (oficial UARIV): `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04`
  - GitHub (backup): `github.com/alexjut/srni-unidad-victimas`
