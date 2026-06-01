# OE6 — Modelos de datos documentados

> **Obligación contractual:** *Crear y documentar modelos de datos que reflejen con precisión la información que se desea analizar, considerando las relaciones entre los diferentes conjuntos de datos en las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se diseñaron, implementaron y documentaron **tres modelos de datos integrados** que reflejan el dominio completo del procedimiento de instrumentalización de víctimas. **Modelo del Instrumento:** Instrumento → Capítulo → Pregunta → OpcionRespuesta + ReglaSkipLogic, soportando 9 tipos de pregunta (TEXTO, TEXTO_LARGO, NUMERICO, FECHA, BOOLEAN, RADIO, LISTA, LISTA_MULTIPLE y COMBO_DINAMICO para selectores DIVIPOLA dinámicos), 2 niveles (HOGAR único o PERSONA repetido por miembro) y 4 acciones de skip logic (HABILITAR, DESHABILITAR, OBLIGAR, FINALIZAR). El modelo se materializa en **1 001 preguntas activas** y **2 239 opciones** distribuidas en los 8 instrumentos UARIV. **Modelo del ciclo de caracterización:** Victima (PII cifrado + hash SHA-256) → Hogar (autorizado, municipio, vivienda) → MiembroHogar (rol, parentesco, género, es_autorizado, estado_inclusion) y, paralelamente, Hogar → SesionEncuesta (instrumento + ruta + encuestador + 4 FKs de ubicación de atención de la Sprint 19) → RespuestaEncuesta (con FK opcional a miembro de la Sprint 21 y UniqueConstraint `(sesion, pregunta, miembro)` que diferencia respuestas tipo HOGAR de las repetidas por miembro). **Modelo paramétrico:** Departamento DANE → Municipio DANE → Vereda, con M2M a DireccionTerritorial UARIV y FK desde PuntoAtencion. La documentación incluye reglas de cardinalidad (1:N, 1:1), reglas de integridad (validación cascada UARIV en el serializer, `es_autorizado` único por hogar, coherencia HOGAR/PERSONA en respuestas) y cantidades cargadas en BD al cierre del mes (33 deptos, 1102 muns, 21 DTs, 41 puntos, 8 instrumentos, 1001 preguntas activas).

## Evidencia que soporta esta actividad

- **Modelo Django del instrumento:** `srni-backend/apps/formulario/models.py` (Instrumento, Capitulo, Pregunta, OpcionRespuesta, ReglaSkipLogic).
- **Modelo Django del ciclo de caracterización:** `srni-backend/apps/encuestas/models.py` (SesionEncuesta, RespuestaEncuesta), `srni-backend/apps/hogares/models.py` (Hogar, MiembroHogar), `srni-backend/apps/victimas/models.py` (Victima).
- **Modelo Django paramétrico:** `srni-backend/apps/parametricas/models.py` (Departamento, Municipio, Vereda, DireccionTerritorial, PuntoAtencion, TipoDocumento, ComunidadNegra, ResguardoIndigena).
- **Documentación de relaciones:** sección "Reglas de cardinalidad" y "Reglas de integridad" del README.md de esta carpeta, con diagramas ASCII de cada modelo.
- **Schema SQLite móvil reflejando los modelos:** `srni-mobile/src/db/schema.ts` con tablas borradores y respuestas.
- **Documentación cualitativa de cada tipo de pregunta:** sección "Tipos de pregunta soportados" del README.md.
- **Copias locales en esta carpeta:** `modelos-py-formulario.py`, `modelos-py-encuestas.py`, `modelos-py-hogares.py`, `modelos-py-parametricas.py`.

---

## Actividades del cronograma

1. Modelo instrumento → tema → pregunta → opción con skip logic
2. Modelo víctima → hogar → encuesta → respuesta — ciclo completo
3. Modelo paramétrico: departamentos, municipios, veredas, tipos de documento
4. Documentación de relaciones, dependencias y cardinalidades

## Modelo del Instrumento (formulario)

```
Instrumento (codigo + version, único)
   │
   │ FK reverse
   ▼
Capitulo (codigo, nombre, orden, nivel HOGAR/PERSONA)
   │
   │ FK reverse
   ▼
Pregunta (codigo_externo, tipo, nivel, orden, obligatoria, activa)
   │
   │ FK reverse
   ▼
OpcionRespuesta (valor, etiqueta, orden, finaliza_capitulo)

ReglaSkipLogic
   pregunta_origen FK ── Pregunta
   pregunta_afectada FK ── Pregunta (opcional)
   capitulo_afectado FK ── Capitulo (opcional)
   valor_trigger, accion (HABILITAR/DESHABILITAR/OBLIGAR/FINALIZAR)
```

### Reglas de cardinalidad

- 1 Instrumento tiene N Capítulos (1:N)
- 1 Capítulo tiene N Preguntas (1:N)
- 1 Pregunta tiene 0..N Opciones (1:N opcional; tipos TEXTO/NUMERICO/FECHA no necesitan)
- 1 ReglaSkipLogic apunta a 1 Pregunta origen, opcionalmente a 1 Pregunta afectada o 1 Capítulo afectado

### Tipos de pregunta soportados

| tipo | render mobile | observaciones |
|---|---|---|
| TEXTO | TextInput simple | |
| TEXTO_LARGO | TextInput multiline | |
| NUMERICO | TextInput keyboardType=numeric | |
| FECHA | **SelectorFecha (Sprint 21-D)** | calendario nativo, max=hoy |
| BOOLEAN | RadioButton Sí/No | guarda "true"/"false" |
| RADIO | RadioButton.Group | con opciones del bundle |
| LISTA | RadioButton.Group | con opciones del bundle |
| LISTA_MULTIPLE | Checkbox.Group | guarda JSON array |
| **COMBO_DINAMICO** | **SelectorMunicipio (Sprint 20-QA-B)** | consume `/api/parametricas/municipios/todos/` |

### Niveles

| nivel | aplica a | UI |
|---|---|---|
| HOGAR | 1 respuesta por sesión | renderizado bajo "Datos del hogar" |
| PERSONA | 1 respuesta por miembro | wizard por miembro (Sprint 21-F) |

## Modelo del ciclo de caracterización

```
Victima (PII cifrado + numero_documento_hash SHA-256)
   │
   │ FK (1 víctima puede ser autorizado de N hogares; en práctica solo 1 activo)
   ▼
Hogar (autorizado FK, municipio FK, tipo_vivienda, estrato, …)
   │
   ├── MiembroHogar (rol, parentesco, género, fecha_nac, es_autorizado, estado_inclusion)
   │
   └── SesionEncuesta
          │  hogar FK
          │  instrumento FK (TERRITORIAL, ASISTENCIA, …)
          │  ruta_entrevista (GENERAL, ACCIONES_CONSTITUCIONALES, …)
          │  encuestador FK
          │  estado (INICIADA, EN_PROGRESO, COMPLETADA, SUSPENDIDA)
          │  porcentaje_completado (calculado)
          │  Sprint 19: direccion_territorial, departamento_atencion, municipio_atencion, punto_atencion FKs
          │
          └── RespuestaEncuesta
                  pregunta FK
                  Sprint 21: miembro FK (null = HOGAR, UUID = PERSONA)
                  valor (TEXT — "true"/"false" para BOOLEAN, JSON array para LISTA_MULTIPLE)
                  UNIQUE(sesion, pregunta, miembro)
```

### Reglas de integridad

- `MiembroHogar.es_autorizado` solo puede ser true para 1 miembro por hogar (validación a nivel de aplicación, no DB constraint)
- `RespuestaEncuesta`:
  - Si `pregunta.nivel = HOGAR` → `miembro` debe ser NULL
  - Si `pregunta.nivel = PERSONA` → `miembro` requerido y debe pertenecer al hogar de la sesión
  - Validado en `_resolver_miembro()` del view + UniqueConstraint
- `SesionEncuesta`:
  - Validación cascada UARIV: depto debe pertenecer a DT (M2M), municipio al depto, punto a la DT

## Modelo paramétrico (DANE + UARIV)

```
Departamento (codigo_dane 2 dígitos)
   │
   ├── Municipio (codigo_dane 5 dígitos, FK departamento)
   │      │
   │      └── Vereda (codigo_dane 13 dígitos, FK municipio)
   │
   └── M2M ↔ DireccionTerritorial (21 DTs UARIV, codigo, nombre, M2M con deptos)
                        │
                        └── PuntoAtencion (FK direccion_territorial + FK municipio)

TipoDocumento (codigo, nombre, aplica_nacionales, aplica_extranjeros)

ComunidadNegra (FK municipio)
ResguardoIndigena (FK municipio, pueblo)
```

### Cantidades cargadas

| Catálogo | Cantidad |
|---|---|
| Departamentos | 33 |
| Municipios | 1 102 |
| Veredas | 0 (pendiente carga masiva — 32 377 disponibles en CSV DANE) |
| Direcciones Territoriales | 21 |
| Puntos de atención | 41 (placeholder) |
| Tipos de documento | 3 (CC, TI, RC; CE, PA disponibles) |

## Archivos relevantes

Copias locales:

- [`MODELOS-resumen.md`](MODELOS-resumen.md) — este mismo archivo expandido
- [`modelos-py-formulario.py`](modelos-py-formulario.py)
- [`modelos-py-encuestas.py`](modelos-py-encuestas.py)
- [`modelos-py-hogares.py`](modelos-py-hogares.py)
- [`modelos-py-parametricas.py`](modelos-py-parametricas.py)

Referencias al repo:

- `docs/MODELOS.md` (a actualizar)
- `srni-backend/apps/*/models.py`

## Pendientes (a complementar Javier)

- Diagrama ER en herramienta visual (drawio, lucidchart) para anexar al informe
- Decisión sobre carga de 32 377 veredas o si se mantiene bajo demanda
