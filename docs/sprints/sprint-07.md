# Sprint 7 — Caracterizar Flujo + Loader Data-Driven + Modo Gemini

**Branch:** `feature/sprint7-caracterizar-flujo`  
**Estado:** 🚧 En progreso  
**Inicio:** 2026-05-05  
**Cierre estimado:** TBD

---

## Objetivos del sprint

1. Completar el flujo de caracterización en la app móvil (sesión → formulario → capítulos)
2. Migrar loaders a patrón data-driven (JSON fixtures + loader genérico)
3. Crear catálogo de opciones compartidas entre los 7 instrumentos
4. Implementar modo de captura asistido por Gemini (grabación → batch → revisión)
5. Cargar reglas de skip logic en todos los instrumentos

---

## Tareas completadas

| Tarea | Commit | Fecha |
|-------|--------|-------|
| Migrar app móvil a UUIDs, skip logic V8, flujo sesión→formulario | `caa8e59` | 2026-05-04 |
| Verificación end-to-end del flujo API (login→hogar→sesión→responder→finalizar) | — | 2026-05-05 |
| Ejecutar loaders faltantes: SAI, Telefónico, Urbano Étnico, Rural Étnico | — | 2026-05-05 |
| `Perfil.Meta ordering = ["codigo"]` — fix UnorderedObjectListWarning | `0266f66` | 2026-05-06 |
| `cargar_perfil.py` — loader genérico unificado con `--perfil`, `$ref`, dry-run | `0266f66` | 2026-05-06 |
| `opciones_compartidas.json` — catálogo de 40 listas UARIV | `0266f66` | 2026-05-06 |
| `perfil_territorial_v7.json` — primer fixture JSON con opciones + skip logic | `0266f66` | 2026-05-06 |
| `cargar_diccionario_v8.py` convertido a shim de compatibilidad | `0266f66` | 2026-05-06 |

---

## Tareas pendientes

| Tarea | Prioridad | Dependencia |
|-------|-----------|-------------|
| Completar opciones faltantes en TERRITORIAL V7 (49 de 85 preguntas) | Alta | `vivanto.db` real |
| Fixtures JSON para BUENAVENTURA, SAN_ANDRES, TELEFONICO, URBANO_ETNICO, RURAL_ETNICO | Alta | `vivanto.db` real |
| Skip logic completo en todos los instrumentos | Alta | Fixtures JSON completos |
| Backend: `POST /api/ia/procesar-entrevista/` (batch Gemini por capítulo) | Alta | — |
| Mobile: `grabacion-entrevista.tsx` — grabación de capítulo completo | Alta | Endpoint batch |
| Mobile: `revision-ia.tsx` — revisión y confirmación de sugerencias IA | Alta | Endpoint batch |
| Mobile: selector modo Manual / Asistido en `formulario/index.tsx` | Media | Pantallas nuevas |
| Mobile: extraer `PreguntaItem` a componente reutilizable | Media | — |
| Pantalla finalizar sesión desde el formulario | Media | — |
| Tests de carga idempotente (loaders) | Media | — |

---

## Decisiones técnicas

### Loader data-driven con catálogo `$ref`

**Problema:** 6 archivos Python grandes con datos hardcodeados, sin opciones de respuesta, difíciles de mantener cuando UARIV actualice el instrumento.

**Solución:** Un único `cargar_perfil.py` que lee fixtures JSON. Las opciones compartidas entre instrumentos se definen en `opciones_compartidas.json` y se referencian con la sintaxis `"$ref:CLAVE"` en el fixture del perfil.

**Ventaja:** Separación de datos y lógica. UARIV puede actualizar el JSON sin tocar el código. El `--dry-run` permite validar antes de persistir.

```bash
# Uso
python manage.py cargar_perfil --perfil TERRITORIAL
python manage.py cargar_perfil --perfil TERRITORIAL --dry-run
python manage.py cargar_perfil --fixture apps/formulario/fixtures/perfil_territorial_v7.json
```

### Dos modos de caracterización

| Modo | Descripción | Estado |
|------|-------------|--------|
| **Manual** | Encuestador llena capítulo a capítulo, pregunta por pregunta | ✅ Funciona |
| **Asistido Gemini** | Graba toda la entrevista del capítulo → Gemini extrae respuestas → encuestador revisa | 🚧 Pendiente |

El modo Gemini procesa por capítulo (no entrevista completa) para mantener el contexto de Gemini manejable. Degrada a modo manual cuando no hay conexión.

### UUIDs en SQLite móvil (Migration V2)

Las tablas de SQLite local se recrearon con TEXT PKs (UUID) para alinear con los IDs de servidor. Eliminadas las tablas `temas` y `preguntas_derivadas`, reemplazadas por `capitulos` y `reglas_skip_logic`.

---

## Estado de instrumentos

| Perfil | Capítulos | Preguntas | Opciones cargadas | Fixture JSON | Skip logic |
|--------|-----------|-----------|-------------------|--------------|------------|
| ASISTENCIA V8 | 7 | 178 | ✅ 275 | ✅ | ✅ |
| TERRITORIAL V7 | 14 | 198 | ⚠️ 36/85 | ✅ | ⚠️ 4 reglas |
| BUENAVENTURA V7 | 17 | 288 | ❌ 0 | ❌ | ❌ |
| SAN_ANDRES V7 | 14 | 248 | ❌ 0 | ❌ | ❌ |
| TELEFONICO V8 | 7 | 66 | ❌ 0 | ❌ | ❌ |
| URBANO_ETNICO V1 | 12 | 121 | ❌ 0 | ❌ | ❌ |
| RURAL_ETNICO V1 | 14 | 170 | ❌ 0 | ❌ | ❌ |

**Total:** 85 capítulos, 1.319 preguntas, 249 opciones en TERRITORIAL, 275 en ASISTENCIA.

---

## Cómo cargar instrumentos

```bash
# Prerequisito: cargar departamentos y municipios
python manage.py cargar_departamentos_municipios

# Cargar con el nuevo sistema data-driven (idempotente)
python manage.py cargar_perfil --perfil TERRITORIAL
# python manage.py cargar_perfil --perfil BUENAVENTURA   # pendiente fixture
# python manage.py cargar_perfil --perfil SAN_ANDRES     # pendiente fixture
# python manage.py cargar_perfil --perfil TELEFONICO     # pendiente fixture
# python manage.py cargar_perfil --perfil URBANO_ETNICO  # pendiente fixture
# python manage.py cargar_perfil --perfil RURAL_ETNICO   # pendiente fixture

# Cargar ASISTENCIA (usa shim que llama cargar_perfil internamente)
python manage.py cargar_diccionario_v8

# Dry-run para validar fixture sin persistir
python manage.py cargar_perfil --perfil TERRITORIAL --dry-run
```

---

## Tareas → Sprint 8

| Tarea | Prioridad |
|-------|-----------|
| Push notifications para nuevas asignaciones | Baja |
| Firma digital del encuestador al cerrar encuesta | Media |
| Dashboard web de supervisores (Angular — Fase 2) | Alta |
| Export de respuestas a formato UARIV (.xlsx / .csv) | Media |
