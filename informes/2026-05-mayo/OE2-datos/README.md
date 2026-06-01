# OE2 — Captura, procesamiento y calidad de datos

> **Obligación contractual:** *Realizar la captura, el procesamiento, la transformación y la gestión de calidad de datos de las fuentes recibidas por la entidad en el desarrollo de las mediciones para las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se implementó la **carga completa de paramétricos oficiales DANE y UARIV** en la base de datos del sistema: 33 departamentos, 1 102 municipios (extraídos de la hoja DIVIPOLA del Excel oficial del Diccionario Territorial V7 UARIV mediante script Python), 21 Direcciones Territoriales UARIV con su mapeo M2M a departamentos, 41 puntos de atención y 3 tipos de documento. Se cargaron también los **8 instrumentos de caracterización** (ASISTENCIA, TERRITORIAL, BUENAVENTURA, SAN_ANDRÉS, TELEFÓNICO, URBANO_ÉTNICO, RURAL_ÉTNICO y VÍCTIMAS_EXTERIOR) con un total de **1 001 preguntas activas** y **2 239 opciones de respuesta** (incluyendo 175 opciones extraídas del Diccionario Excel UARIV oficial para preguntas tipo LISTA que estaban vacías). Se diseñó e implementó el **motor de sincronización automática offline → servidor** en la app móvil con cola persistente en SQLite, backoff exponencial (2, 4, 8, 16, 32 segundos con jitter), 5 tipos de operación (CREAR_HOGAR, CREAR_SESION, RESPONDER_PREGUNTA, RESPONDER_BULK, FINALIZAR_SESION), detección de conectividad por ping a `/health/`, polling cada 60 segundos cuando hay conexión, idempotencia con marcado ENVIADO y propagación automática de IDs del servidor a items dependientes. La gestión de calidad de datos se automatizó mediante el script `qa_perfiles.py` que compara la base de datos con los bundles JSON de la app móvil y genera reporte de discrepancias por instrumento; al cierre del mes el resultado es **0 discrepancias** en los 8 instrumentos, **0 capítulos vacíos** y **0 preguntas obligatorias sin opciones**.

## Evidencia que soporta esta actividad

- **Scripts de carga (versionados):**
  - `srni-backend/apps/parametricas/management/commands/cargar_departamentos_municipios.py`
  - `srni-backend/apps/parametricas/management/commands/cargar_direcciones_territoriales.py`
  - `srni-backend/apps/parametricas/management/commands/cargar_puntos_atencion.py`
  - `srni-backend/scripts/extraer_municipios_divipola.py`
- **Dataset oficial generado:** `srni-backend/data/municipios_dane.csv` (1102 municipios DANE).
- **Comandos de mantenimiento de instrumentos:** `cargar_capitulo_control.py`, `desactivar_preguntas_atencion.py`, `renombrar_instrumentos.py`, `exportar_a_mobile.py`.
- **Motor de sincronización:** `srni-mobile/src/services/sincronizacion.ts` + DAO de cola `srni-mobile/src/db/colaDao.ts`.
- **Reporte automatizado de calidad de datos:** `docs/qa-perfiles-sprint20.md` (regenerable con `srni-backend/scripts/qa_perfiles.py`).
- **Bundles JSON generados:** `srni-mobile/assets/instrumentos/` (8 archivos, ~675 KB).
- **Copias locales en esta carpeta:** todos los scripts arriba mencionados están en `OE2-datos/` como copia autocontenida.

---

## Actividades del cronograma

1. Análisis y mapeo de datos del APK (9.4 M registros sin cifrado identificados)
2. Implementación de modelos de datos (víctimas, hogares, encuestas, respuestas)
3. **Scripts de carga de paramétricos:** 33 departamentos, 1 102 municipios DANE
4. **Motor de sincronización automática offline** a servidor (cola de envío al recuperar señal)

## Avances en Mayo 2026

### Modelos implementados

Los 5 modelos principales del dominio quedaron implementados y aplicados en BD:

| Modelo | App | Sprint | Estado |
|---|---|---|---|
| `Victima` (PII cifrado + hash SHA-256) | `apps/victimas` | 1-2 | ✅ |
| `Hogar` (autorizado + rol miembro + estado_inclusion) | `apps/hogares` | 12 | ✅ |
| `MiembroHogar` | `apps/hogares` | 12 | ✅ |
| `SesionEncuesta` (+ 4 FKs ubicación atención) | `apps/encuestas` | 1, 19 | ✅ |
| `RespuestaEncuesta` (+ FK miembro) | `apps/encuestas` | 1, 21 | ✅ |

### Carga de paramétricos DANE + UARIV

| Catálogo | Cantidad | Fuente | Comando | Sprint |
|---|---|---|---|---|
| Departamentos | 33 | DIVIPOLA DANE 2023 | `cargar_departamentos_municipios` | 1 |
| Municipios (capitales) | 33 | DIVIPOLA DANE 2023 | `cargar_departamentos_municipios` | 1 |
| Municipios (todos) | **1 102** | DIVIPOLA DANE 2023 | `cargar_departamentos_municipios --csv` | 19 |
| Direcciones Territoriales UARIV | **21** | Estructura UARIV pública | `cargar_direcciones_territoriales` | 19 |
| Puntos de Atención | **41** (placeholder) | UARIV | `cargar_puntos_atencion` | 19 |
| Tipos de documento | 3 | UARIV | `cargar_tipos_documento` | 1 |

### Motor de sincronización offline → servidor

Implementado en `srni-mobile/src/services/sincronizacion.ts`:

- **Cola persistente** en SQLite local (`cola_sincronizacion`)
- **Backoff exponencial:** 2, 4, 8, 16, 32 segundos con jitter
- **5 tipos de operación:** CREAR_HOGAR, CREAR_SESION, RESPONDER_PREGUNTA, RESPONDER_BULK, FINALIZAR_SESION
- **Detección de conectividad:** ping a `/health/` con timeout corto
- **Polling automático** cada 60 segundos cuando hay conexión
- **Idempotencia:** items marcados como ENVIADO no se reintentan
- **Inyección de IDs del servidor** en items dependientes (cuando se crea un hogar local, los items "crear sesión" pendientes reciben el UUID real)

### Calidad de datos

- **1 001 preguntas activas** (después de QA Sprint 20)
- **2 239 opciones de respuesta** (incluyendo 175 extraídas del Diccionario Excel UARIV oficial)
- **0 discrepancias** BD ↔ Bundle JSON (verificado con script `qa_perfiles.py`)
- **0 capítulos vacíos** (tras cargar T1/T2/T3 en TERRITORIAL+TELEFONICO)
- **16 selectores DIVIPOLA** ahora rinden con search bar sobre 1 102 municipios

## Archivos relevantes

Copias locales en esta carpeta:

- [`cargar_direcciones_territoriales.py`](cargar_direcciones_territoriales.py) — carga las 21 DTs UARIV
- [`cargar_departamentos_municipios.py`](cargar_departamentos_municipios.py) — carga 33 deptos + 1102 muns
- [`cargar_puntos_atencion.py`](cargar_puntos_atencion.py) — carga 41 puntos placeholder
- [`extraer_municipios_divipola.py`](extraer_municipios_divipola.py) — extrae municipios desde Excel UARIV
- [`sincronizacion.ts`](sincronizacion.ts) — motor de cola offline
- [`qa_perfiles.py`](qa_perfiles.py) — script de QA automático BD↔Bundle

Referencias al repo:

- `srni-backend/apps/parametricas/` — modelos + serializers + viewsets
- `srni-backend/apps/parametricas/management/commands/` — comandos de carga
- `srni-mobile/src/db/colaDao.ts` — DAO de la cola offline
- `srni-backend/data/municipios_dane.csv` — dataset DANE

## Pendientes (a complementar Javier)

- Dataset oficial UARIV de Centros Regionales (pendiente solicitar a Oscar)
- Validación con datos reales (50+ caracterizaciones) cuando se autorice
