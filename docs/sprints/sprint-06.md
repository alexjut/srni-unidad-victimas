# Sprint 6 — Diccionario V8 + Loaders de Perfiles

**Branch:** `feature/sprint6-diccionario-v8`  
**Estado:** ✅ Completado  
**Inicio:** 2026-04-10  
**Cierre:** 2026-04-28

---

## Objetivos

1. Alinear el modelo Django con el Diccionario de Datos UARIV V8
2. Crear management commands idempotentes para cargar todos los perfiles
3. Agregar validadores de hogar al modelo
4. Preparar fixture `perfil_asistencia_v8.json` para el perfil telefónico

---

## Tareas completadas

| Tarea | Commit | Fecha |
|-------|--------|-------|
| Alinear modelo + validadores hogar | `5f38078` | 2026-04-10 |
| `cargar_territorial_v7.py` — 14 caps, 248 preguntas | `0fa48ed` | 2026-04-27 |
| `cargar_buenaventura_v7.py` — 17 caps, ~300 preguntas | `dd91ee6` | 2026-04-28 |
| `cargar_san_andres_v7.py` — 14 caps, ~290 preguntas | `0453bf4` | 2026-04-28 |
| `cargar_telefonico_v8.py` — 7 caps, entrevista telefónica SAAH | `8bace02` | 2026-04-28 |
| `cargar_urbano_etnico_v1.py` — 12 caps, ~120 preguntas | `046b356` | 2026-04-28 |
| `cargar_rural_etnico_v1.py` — 14 caps, ~160 preguntas, offline-first | `046b356` | 2026-04-28 |
| `cargar_diccionario_v8.py` — Asistencia V8 (JSON) | incluido en `5f38078` | 2026-04-10 |
| Docs: structure + index + sprint + mobile + instruments + API | `8bace02` | 2026-04-28 |

---

## Tareas pendientes → Sprint 7

| Tarea | Prioridad |
|-------|-----------|
| Fixture `perfil_asistencia_v8.json` — completar opciones de respuesta | Alta |
| Skip logic (PREDEPENDE / RESHABILITA / RESFINALIZA) en todos los perfiles | Alta |
| Tests de carga idempotente | Media |
| Endpoint API `/formulario/instrumento/{perfilCodigo}/` | Alta |

---

## Decisiones técnicas

### Loader vs Fixture JSON
- Perfiles **V7** (Territorial, Buenaventura, San Andrés): management commands Python
  - Razón: mayor legibilidad, más fácil de mantener con cambios puntuales
- Perfiles **V1** (Urbano Étnico, Rural Étnico): management commands Python
  - Razón: misma convención que V7, capítulos claros y delimitados
- Perfil **V8** (Asistencia/Telefónico SAAH): Python loader + fixture JSON para opciones complejas
  - Razón: el V8 tiene skip logic complejo → mejor representado en JSON estructurado

### Idempotencia
Todos los loaders usan `update_or_create` con `codigo_externo` como key.
Se pueden ejecutar múltiples veces sin duplicar datos.

### INSTRUMENTO_PK asignados
| Perfil | InstrumentoVersion PK |
|--------|-----------------------|
| Territorial V7 | `22222222-0001-0001-0001-000000000001` |
| Buenaventura V7 | `22222222-0002-0002-0002-000000000002` |
| San Andrés SAI V7 | `22222222-0003-0003-0003-000000000003` |
| Telefónico SAAH V8 | `22222222-0004-0004-0004-000000000004` |
| Urbano Étnico V1 | `22222222-0005-0005-0005-000000000005` |
| Rural Étnico V1 | `22222222-0006-0006-0006-000000000006` |

---

## Diferencias entre perfiles

### SAI vs Territorial V7
- Cap. A: `VEREDA` → `SECTOR` (islas no tienen veredas)
- Cap. A7: "Barrio o sector" (sin "vereda" en el texto)
- Cap. B: preguntas de identidad RAIZAL + idioma Creole English
- Cap. M: orientado a territorio insular y pesca artesanal

### Buenaventura vs Territorial V7
- Capítulos exclusivos: NA (Info Adicional Hogar), NP (Info Adicional Persona), O (Seguridad Jurídica del Territorio)
- Total: 17 capítulos vs 14 de Territorial
- Cap. O: ST1–ST13, derechos territoriales específicos de comunidades Afro

### Telefónico SAAH vs Territorial V7
- Solo 7 capítulos (sin Vivienda, Territorio, Fuerza Pública, Sociolaboral)
- Variables con sufijo `_tel` (e.g. `Z5A_tel`, `B9_tel`)
- Modalidad remota — sin desplazamiento presencial

### Urbano Étnico vs Territorial V7
- Sin capítulo M (Territorio/Vivienda rural — contexto urbano)
- 12 capítulos en lugar de 14
- Cap. B: "DATOS BÁSICOS E IDENTIDAD ÉTNICA" — cabildo urbano, consejo comunitario urbano
- Usa "barrio o sector" (sin vereda)

### Rural Étnico vs Territorial V7
- Cap. M extendido con gobernanza étnica: AT9A, AT10A, AT11A (Plan de Vida)
- Cap. B con máximo detalle étnico: B21–B40 (territorio colectivo, resguardo, cabildo, consejo, Vitsa, Kumpania, autoridad propia, idioma propio)
- Diseñado offline-first (app móvil sin conectividad)
- Incluye capítulo L (Fuerza Pública) — igual que Territorial V7

---

## Cómo ejecutar los loaders

```bash
# Prerequisito: fixture inicial de perfiles
python manage.py loaddata perfiles_iniciales

# Cargar cada perfil (idempotente, se puede repetir)
python manage.py cargar_territorial_v7
python manage.py cargar_buenaventura_v7
python manage.py cargar_san_andres_v7
python manage.py cargar_telefonico_v8
python manage.py cargar_urbano_etnico_v1
python manage.py cargar_rural_etnico_v1

# Cargar Asistencia V8 desde JSON
python manage.py cargar_diccionario_v8
python manage.py cargar_diccionario_v8 --dry-run  # simular sin persistir
```
