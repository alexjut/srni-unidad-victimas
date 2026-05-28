# OE2 — Captura, procesamiento y calidad de datos

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
