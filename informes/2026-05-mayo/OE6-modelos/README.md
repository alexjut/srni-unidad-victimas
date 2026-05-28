# OE6 — Modelos de datos documentados

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
