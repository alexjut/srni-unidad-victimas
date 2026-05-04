# Sprint 3 — Hogares, Encuestas y Pantallas Móviles

**Branch:** `main`
**Estado:** ✅ Completado
**Inicio:** 2026-04-16
**Cierre:** 2026-04-16
**Commit:** `ec50cb3`

---

## Objetivos

1. Implementar el modelo completo de Hogares y Miembros con PII cifrado
2. Crear el modelo de Sesiones de Encuesta con seguimiento de progreso
3. Desarrollar las pantallas móviles principales de hogares y encuestas
4. Alcanzar suite completa de 53 tests passing

---

## Entregables backend

### App Hogares

**Modelos:**

```python
class Hogar:
    id = UUIDField(primary_key=True)
    sesion_encuesta = ForeignKey(SesionEncuesta)
    encuestador = ForeignKey(Usuario)
    # Datos hogar sin PII (dirección general, estrato, tipo vivienda)
    created_at, updated_at

class MiembroHogar:
    id = UUIDField(primary_key=True)
    hogar = ForeignKey(Hogar)
    # Campos PII cifrados:
    nombre_completo = EncryptedCharField()
    numero_documento = EncryptedCharField()
    fecha_nacimiento = EncryptedCharField()
    tipo_persona = CharField()        # NATURAL, JURIDICA
    incluido_ruv = BooleanField()
    tiene_discapacidad = BooleanField()
    tiene_enfermedad_ruinosa = BooleanField()
```

**Endpoints:**
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/hogares/` | Lista hogares del encuestador (paginada) |
| POST | `/api/hogares/` | Crear nuevo hogar |
| GET | `/api/hogares/{id}/` | Detalle de hogar con miembros |
| PATCH | `/api/hogares/{id}/` | Actualizar datos del hogar |
| GET | `/api/hogares/{id}/miembros/` | Lista de miembros |
| POST | `/api/hogares/{id}/miembros/` | Agregar miembro al hogar |

### App Encuestas

**Modelos:**

```python
class SesionEncuesta:
    id = UUIDField(primary_key=True)
    hogar = ForeignKey(Hogar)
    encuestador = ForeignKey(Usuario)
    instrumento = ForeignKey(InstrumentoVersion)
    estado = CharField()  # BORRADOR, EN_CURSO, FINALIZADA, RECHAZADA
    porcentaje_completado = FloatField(default=0.0)  # calculado
    created_at, updated_at, cerrada_en

class RespuestaEncuesta:
    sesion = ForeignKey(SesionEncuesta)
    pregunta = ForeignKey(Pregunta)
    valor = TextField()   # siempre string (serializado)
    created_at, updated_at
    # Upsert: si ya existe respuesta para (sesion, pregunta) → actualiza
```

**Endpoints:**
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/encuestas/` | Sesiones del encuestador |
| POST | `/api/encuestas/` | Iniciar nueva sesión |
| GET | `/api/encuestas/{id}/` | Detalle de sesión con progreso |
| POST | `/api/encuestas/{id}/respuestas/` | Guardar respuestas (batch upsert) |
| POST | `/api/encuestas/{id}/cerrar/` | Cerrar y firmar sesión |

**Management command:**
- `crear_usuario_prueba` — crea `ENCUESTADOR001` / `SrniTest2026!` para pruebas

**Correcciones técnicas:**
- `_force_auth_user` → `_force_user` (DRF correcto)
- `total_miembros` calculado en `HogarDetalleSerializer` mediante `annotate`

---

## Entregables mobile

### Pantallas Hogares

**`hogares/index.tsx`**
- Lista de hogares asignados al encuestador
- Pull-to-refresh
- Filtro por estado (borrador / en curso / finalizado)
- Navegación a detalle

**`hogares/nuevo.tsx`**
- Formulario de creación de nuevo hogar
- Campos: dirección, estrato, tipo vivienda, municipio (selector paramétrico)
- Validación antes de enviar

**`hogares/[hogarId].tsx`**
- Detalle completo del hogar
- Lista de miembros con botón agregar
- Botón iniciar encuesta

### Pantallas Encuestas

**`encuestas/index.tsx`**
- Lista de sesiones de encuesta
- Barra de progreso por sesión (% completado)
- Filtro por estado

**`encuestas/[sesionId].tsx`**
- Detalle de sesión con botón finalizar
- Resumen de capítulos completados
- Estado de la sesión

### Tipos TypeScript agregados
```typescript
interface HogarResumen { id, direccion, municipio, total_miembros, estado }
interface HogarDetalle extends HogarResumen { miembros: MiembroHogar[] }
interface SesionResumen { id, hogar_id, estado, porcentaje_completado, created_at }
interface MiembroHogar { id, nombre_completo, tipo_documento, tipo_persona }
```

### Clientes API
- `src/api/hogares.ts` — CRUD hogares y miembros
- `src/api/encuestas.ts` — CRUD sesiones y respuestas

---

## Tests: 53/53 passing (20 nuevos)

| Módulo | Tests nuevos | Total |
|--------|-------------|-------|
| Hogares serializers | 5 | — |
| Hogares endpoints | 8 | — |
| Encuestas serializers | 4 | — |
| Encuestas endpoints | 3 | — |
| Regresión sprint 1+2 | 0 (todos pasan) | 33 |
| **Total** | **20** | **53** |

---

## Decisiones técnicas

**Por qué upsert en RespuestaEncuesta:** El encuestador puede corregir respuestas antes de cerrar la sesión. El upsert por `(sesion, pregunta)` evita duplicados y simplifica la sincronización offline.

**Por qué `porcentaje_completado` en el modelo:** Permite mostrar barras de progreso en la lista de sesiones sin cargar todas las respuestas. Se recalcula en cada batch save.
