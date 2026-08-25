# Informe Mensual — Agosto 2026

**Contrato:** 2226-2026 — Sistema de Caracterización de Víctimas (SRNI)
**Contratista:** Javier Alexander Aguilar Castro · CC 1.030.547.250
**Supervisor:** Oscar Andrés Manosalva García (SRNI)
**Período cubierto:** 1 de agosto 2026 → 25 de agosto 2026
**Estado:** en cierre — actualizado al 25-ago-2026, con evidencia física por obligación (formato del supervisor en [`COPIAR-PEGAR-FORMATO-SUPERVISOR.md`](COPIAR-PEGAR-FORMATO-SUPERVISOR.md)).

---

## El mes en una frase

Agosto fue el mes de **poner el sistema a prueba contra la realidad**: se cargaron
el padrón y el universo de víctimas, se respondieron **tres informes de calidad**
de la Unidad corrigiendo sus hallazgos de raíz, y se cerró de punta a punta el
flujo de excepción de vigencia. El backend y la base quedan **sólidos y
verificables**; lo que queda pendiente es, sobre todo, **revalidación en
dispositivo real y por QA**, no construcción.

---

## Cifras del mes (medidas, no estimadas)

| | | Comando / fuente |
|---|---:|---|
| Cambios versionados (commits) | **142** | `git log --since=2026-08-01 --until=2026-08-26` |
| — de Javier (backend/BD/móvil/infra) | 131 | `git log --pretty=%an \| sort \| uniq -c` |
| — de Brando (frontend web) | 11 | idem |
| Líneas de código | **+44.081 / −868** (287 archivos) | `git diff --shortstat 686d0ad..HEAD` |
| Pruebas de backend en verde | **973** (+1 xfail) | `pytest -q` |
| Pruebas de móvil en verde | **140** | `npm test` (jest) |
| Informes de QA respondidos | **3** (APK v1, APK v2, WEB v2) | `docs/` y `docs/pruebas/` |
| Padrón operativo cargado | **5.936.769** víctimas | `hallazgos_identidad_padron.md` |
| Universo del RUV (corte 01-jul) | **12.496.965** filas | `adr-padron-universo-victimas.md` |
| Instrumentos empaquetados (offline) | **8** · 92 capítulos · 1.640 preguntas | `assets/instrumentos/index.json` |
| Versiones de la APK publicadas | 1.1.0 · 1.2.0 · 1.2.2 | `git log -p -- srni-mobile/app.json` |

---

## Índice por obligación

| OE | Tema | Carpeta | Estado |
|---|---|---|---|
| OE1 | Desarrollo, mantenimiento, documentación y soporte | [`OE1-desarrollo/`](OE1-desarrollo/README.md) | 🟢 3 informes de QA respondidos y corregidos de raíz (APK-002/005, H-024/010/011/025) |
| OE2 | Captura, procesamiento y calidad de datos | [`OE2-datos/`](OE2-datos/README.md) | 🟢 768.096 duplicados clasificados (92 % misma persona); colapso por identidad; estado NO_VERIFICADO |
| OE3 | Medidas de seguridad — protección PII | [`OE3-seguridad/`](OE3-seguridad/README.md) | 🟢 Claves con Argon2id (comando + 9 tests); corrección del borrado de PII al cerrar sesión |
| OE4 | Diseño e implementación de soluciones tecnológicas | [`OE4-arquitectura/`](OE4-arquitectura/README.md) | 🟢 Excepción de vigencia extremo a extremo; autorizar desde el universo; offline + sincronización |
| OE5 | Estructura de bases de datos | [`OE5-bd/`](OE5-bd/README.md) | 🟢 Padrón (5,9 M) + universo (12,5 M) cargados; cruce por documento; escritura a Oracle por procedimientos |
| OE6 | Modelos de datos documentados | [`OE6-modelos/`](OE6-modelos/README.md) | 🟢 Motor de skip-logic unificado; porcentaje por obligatorias visibles con contexto |
| OE7 | Reuniones y coordinación con supervisor | [`OE7-reuniones/`](OE7-reuniones/README.md) | 🟢 Respuesta a los 3 informes; decisiones de negocio delegadas resueltas |
| OE8 | Carga mensual de documentos | [`OE8-informes/`](OE8-informes/README.md) | 🟢 2 presentaciones de avance + documento de capacidades + plan de QA |
| OE9 | Actividades adicionales | [`OE9-adicionales/`](OE9-adicionales/README.md) | 🟢 Análisis del formato de claves legado; prueba E2E documentada; registro de pendiente de BD |
| **EXTRAS** | Trabajo por fuera del cronograma | [`EXTRAS-actividades-adicionales/`](EXTRAS-actividades-adicionales/README.md) | 🟢 Seguimiento de la escritura al legado; consolidación de tres rondas de QA |

---

## Lo que queda abierto (para transparencia con la supervisión)

Se documenta sin adornos, porque es información que la supervisión necesita para
decidir:

- **Revalidación en dispositivo.** Los hallazgos de la APK están corregidos en
  código con pruebas automáticas, pero **requieren una build nueva y reprueba de
  QA en un teléfono** para darse por cerrados. El modo sin conexión (APK-003) no
  se ha probado en modo avión en un dispositivo real.
- **Tres ajustes de despliegue conocidos:** el endpoint de versión de la APK
  responde 1.0.0 en producción mientras la app va en 1.2.2; el porcentaje de
  avance de las sesiones ya guardadas necesita un recálculo (backfill) antes del
  próximo reporte; y el instrumento de Asistencia humanitaria no tiene preguntas
  obligatorias, lo que hay que curar contra el manual.
- **Decisiones de la Unidad:** si la excepción de vigencia aplica a quien no está
  en el padrón (o si el camino es alta manual), y el encendido continuo de la
  escritura automática hacia Oracle (hoy apagada por defecto, deliberadamente).
- **Frontend (Brando):** el indicador de carga (spinner) del panel y el badge de
  estado "Sin verificar" quedaron pendientes; no bloquean el uso.

---

## Evidencia física

Cada obligación tiene una subcarpeta **`evidencias/`** con los artefactos que la
respaldan. La evidencia transversal del mes (histórico de cambios, autores y
volumen) está en [`OE8-informes/evidencias/`](OE8-informes/evidencias/).

---

## Enlaces

- Estado del proyecto: [`docs/estado-actual.md`](../../docs/estado-actual.md)
- Informes de QA: `docs/Informe_Seguimiento_Regresion_APK_v2.pdf`,
  `docs/Informe_Seguimiento_Regresion_WEB_v2.pdf`
- Repositorios:
  - Azure DevOps (oficial UARIV): `tfsunidad.visualstudio.com/…IGED MOVIL 2026-04`
  - GitHub (respaldo): `github.com/alexjut/srni-unidad-victimas`
