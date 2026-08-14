# Índice de soportes — Monitoreo PETI, corte 30 de junio de 2026

**Proyecto:** PRY-0662064 — Modernización de la entrevista de caracterización · APK
**Commit de referencia:** `5fba1fa682c109089ccd397ecffc86cce6c4ac67` (2026-06-30 19:15:42 −05:00)

> **Cada archivo es la versión que existía AL CORTE**, extraída con
> `git show 5fba1fa:<ruta>`. No son los archivos de hoy: un soporte de junio no puede
> contener cambios de julio o agosto. La columna "fecha" es la del último commit que
> modificó ese archivo antes del corte.

---

| # | Archivo | Qué demuestra | Fecha | Ruta original |
|---|---|---|---|---|
| 01 | `01_acta-constitucion-PRY-0662064.md` | Constitución del proyecto: objetivos, alcance, hitos, riesgos e interesados | 2026-06-19 | `docs/gestion/acta-constitucion-PRY-0662064.md` |
| 02 | `02_informe-arquitectura-estado.md` | Arquitectura de la solución y estado consolidado de los tres componentes | 2026-06-23 | `docs/INFORME-ARQUITECTURA-ESTADO.md` |
| 03 | `03_estado-del-proyecto-23jun.md` ⚠️ | Estado del proyecto al 23-jun: inventario de datos cargados, sprints cerrados y hallazgos abiertos | 2026-06-23 | `docs/estado-actual.md` |
| 04 | `04_auditoria-pre-publicacion-10jun.md` | Auditoría de seguridad y calidad previa a la publicación de la APK | 2026-06-10 | `docs/auditoria-pre-tiendas-2026-06-10.md` |
| 05 | `05_respuesta-analisis-seguridad.md` | Atención formal al análisis de seguridad recibido en junio | 2026-06-19 | `docs/gestion/respuesta-analisis-seguridad-2026-06.md` |
| 06 | `06_qa-por-perfil-de-instrumento.md` | Pruebas de calidad ejecutadas perfil por perfil | 2026-05-26 | `docs/qa-perfiles-sprint20.md` |
| 07 | `07_medidas-de-seguridad-backend.md` | Controles de seguridad y protección de PII — Ley 1581 de 2012 | 2026-05-04 | `docs/backend/seguridad.md` |
| 08 | `08_politica-de-privacidad-movil.md` | Política de tratamiento de datos personales de la aplicación | 2026-06-10 | `docs/publicacion/politica-privacidad-srni-mobile.md` |
| 09 | `09_manual-de-uso-movil.md` | Manual de uso para el encuestador en territorio | 2026-06-10 | `docs/publicacion/manual-de-uso-srni-mobile.md` |
| 10 | `10_plan-operacion-offline.md` | Diseño de la operación sin conexión (pre-carga + sincronización) | 2026-06-17 | `docs/arquitectura/plan-offline-precarga.md` |
| 11 | `11_plan-reutilizacion-ruv.md` | Reutilización de la información del RUV para no re-preguntar | 2026-06-17 | `docs/arquitectura/plan-prellenado-ruv.md` |
| 12 | `12_informe-mensual-mayo.md` | Informe mensual de mayo por obligación contractual | 2026-05-28 | `informes/2026-05-mayo/README.md` |
| 13 | `13_informe-mensual-junio.md` | Informe mensual de junio por obligación contractual, al corte | 2026-06-26 | `informes/2026-06-junio/README.md` |
| 14 | `14_commits_al_corte.txt` | Línea de tiempo completa: 284 commits con fecha, hash y asunto | — | Generado con `git log 5fba1fa --since=2026-01-01` |
| 15 | `15_inventario_codigo_al_corte.txt` | Módulos, instrumentos y conteo de archivos existentes al corte | — | Generado con `git ls-tree -r 5fba1fa` |

---

## ⚠️ Nota obligatoria sobre el soporte 03

`03_estado-del-proyecto-23jun.md` **fue redactado antes de copiarse**: el original contiene
una **credencial de acceso al sistema en texto plano** (usuario y contraseña de pruebas).
En la copia, ese valor aparece como `[CREDENCIAL REDACTADA — ver nota del INDICE]`.

**El resto del documento está íntegro.** La redacción se declara acá para que nadie
interprete que el original decía otra cosa.

## 🔴 Archivos excluidos por contener datos sensibles

Se encontraron y **NO se copiaron**:

| Archivo del repositorio | Motivo |
|---|---|
| `informes/2026-06-junio/OE8-informes/credenciales-usuarios-pruebas.md` | Es íntegramente una tabla de usuarios con sus contraseñas en texto plano |
| `informes/2026-06-junio/EXTRAS-actividades-adicionales/correo-brando-credenciales-datos.md` | Contiene la contraseña de un integrante del equipo |
| `informes/2026-05-mayo/OE8-informes/correo-brando.md` | Contiene credenciales de acceso al panel web |
| `docs/sprints/sprint-03.md` | Contiene la contraseña del usuario de pruebas |
| `informes/2026-05-mayo/OE8-informes/estado-actual.md` | Ídem, más la cédula del contratista |

**Ninguno se incluyó**, y ninguno era necesario como evidencia: lo que demuestran ya está
cubierto por los soportes 03, 12 y 13.

### Hallazgo que conviene atender aparte del monitoreo

**Hay credenciales de acceso en texto plano versionadas en el repositorio**, en al menos
seis archivos. No es un problema de este monitoreo —quedaron fuera del paquete— pero sí
del repositorio: cualquiera con acceso al historial las tiene, y **rotarlas no basta si el
archivo sigue en el historial de Git**. Se recomienda rotar esas credenciales y dejar de
versionarlas.

## Sobre datos personales

- **No se incluyó ningún dato de víctimas.** Ningún soporte contiene documentos, nombres
  ni datos identificables de población víctima: los archivos son de arquitectura, gestión
  y calidad.
- Los informes mensuales (soportes 12 y 13) contienen **el nombre y la cédula del
  contratista**, porque son documentos contractuales donde ese dato es parte del
  encabezado formal. Se conservan por eso; si la OCI prefiere anonimizarlos, se puede
  redactar igual que el soporte 03.
- No se copió ningún `.env`, dump de base de datos, llave ni captura de pantalla.
