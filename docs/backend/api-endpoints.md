# API Endpoints — Backend SRNI

**Framework:** Django REST Framework  
**Base URL dev:** `http://localhost:8001/api/`  
**Base URL prod:** `https://srniapk-dev.ngrok.app/api/` (tunnel ngrok)  
**Autenticación:** JWT Bearer Token  
**Última actualización:** 2026-05-25 (Sprint 13 — backend habilitador panel web)

---

## Health Check

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/health/` | Estado del servidor | No |

```json
{ "status": "ok", "proyecto": "SRNI — Unidad para las Víctimas" }
```

---

## Autenticación

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/auth/login/` | Obtener access + refresh token | No |
| POST | `/auth/refresh/` | Renovar access token | No |
| POST | `/auth/logout/` | Invalidar refresh token (blacklist) | Sí |
| GET | `/auth/me/` | Perfil del usuario autenticado | Sí |
| POST | `/auth/cambiar-password/` | Cambiar contraseña | Sí |

### Credenciales de login
```json
{ "codigo_usuario": "ENCUESTADOR001", "password": "SrniTest2026!" }
```

### Respuesta de login
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "usuario": {
    "id": "uuid",
    "codigo_usuario": "ENCUESTADOR001",
    "nombre_completo": "Encuestador de Prueba",
    "perfil": "ENCUESTADOR",
    "activo": true
  }
}
```

**Tokens:** access 15 min · refresh 8 h rotativo con blacklist.

---

## Búsqueda RNI

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/victimas/buscar/` | Buscar víctima por documento o nombre (server-side) | Sí |
| GET | `/victimas/{id}/` | Detalle de víctima — solo campos necesarios | Sí |

**Importante:** Nunca se devuelven datos PII completos al cliente.
La búsqueda se ejecuta en el servidor con índice SHA-256 sobre campos cifrados.
Rate limit: **30 búsquedas / hora por usuario** (`BusquedaRNIThrottle` — Sprint 11).

---

## Formularios / Instrumentos

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/formulario/perfiles/` | Lista de 7 perfiles activos con versiones vigentes | Sí |
| GET | `/formulario/instrumento/{perfil_codigo}/` | Instrumento completo para descarga offline | Sí |
| GET | `/formulario/capitulos/` | Capítulos filtrados por instrumento | Sí |
| GET | `/formulario/preguntas/` | Preguntas filtradas por capítulo | Sí |
| POST | `/formulario/evaluar-skip-logic/` | Evaluar reglas skip logic server-side | Sí |

### `GET /formulario/instrumento/{perfil_codigo}/`

Endpoint offline-first: descarga el instrumento completo en una sola llamada.
Usado por `sincronizacion.ts` en la app móvil al inicio de cada sesión.

**Perfiles disponibles:** `TERRITORIAL`, `BUENAVENTURA`, `SAN_ANDRES`, `TELEFONICO`, `URBANO_ETNICO`, `RURAL_ETNICO`, `ASISTENCIA`

```json
{
  "id": "22222222-0001-0001-0001-000000000001",
  "numero": "V7",
  "vigente_desde": "2023-07-15",
  "capitulos": [
    {
      "id": "uuid",
      "codigo": "A",
      "nombre": "A. IDENTIFICACIÓN",
      "orden": 1,
      "nivel": "HOGAR",
      "preguntas": [
        {
          "id": "uuid",
          "no_pregunta": "A3",
          "codigo_externo": "Z3",
          "texto": "Método de recolección",
          "tipo": "LISTA",
          "obligatoria": true,
          "orden": 3,
          "opciones": [
            {"valor": "1", "etiqueta": "Cara a cara", "orden": 1}
          ],
          "reglas": []
        }
      ]
    }
  ],
  "reglas": []
}
```

### `POST /formulario/evaluar-skip-logic/`

```json
{
  "capitulo_id": "uuid",
  "respuestas": [{"codigo_externo": "A8", "valor": "1"}],
  "contexto": {"edad": 25, "sexo": "1", "ruv_incluido": true}
}
```

Respuesta:
```json
{
  "preguntas_visibles": ["A8", "B9", "C1"],
  "preguntas_obligatorias": ["A8", "C1"],
  "finalizar_capitulo": false,
  "total": 3
}
```

---

## Paramétricas

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/parametricas/departamentos/` | Lista de 33 departamentos | Sí |
| GET | `/parametricas/municipios/` | Municipios filtrados por departamento | Sí |

---

## Hogares

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/hogares/` | Hogares del encuestador autenticado (filtros server-side) | Sí |
| POST | `/hogares/` | Crear nuevo hogar (auto-inserta autorizado como primer miembro) | Sí |
| GET | `/hogares/{id}/` | Detalle de hogar con miembros + sesiones asociadas | Sí |
| PATCH | `/hogares/{id}/` | Actualizar hogar | Sí |
| GET | `/hogares/{id}/miembros/` | Miembros del hogar | Sí |
| POST | `/hogares/{id}/agregar-miembro/` | Agregar miembro (rol MIEMBRO/TUTOR/CUIDADOR_PERMANENTE) | Sí |
| PATCH | `/hogares/{id}/cambiar-autorizado/` | Reasignar el autorizado del hogar | Sí |

### Crear hogar (Sprint 12 — modelo v2)
```json
{
  "autorizado": "uuid-victima",
  "municipio": 29,
  "tipo_vivienda": "CASA",
  "condicion_ocupacion": "ARRIENDO",
  "estrato": 2,
  "numero_cuartos": 3,
  "numero_personas": 4
}
```

### Filtros del listado (Sprint 13)

`GET /api/hogares/` acepta los siguientes query params server-side:

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `estado` | string | `BORRADOR` / `ACTIVO` / `ARCHIVADO` |
| `municipio` | UUID | ID del municipio |
| `tipo_vivienda` | string | `CASA` / `APARTAMENTO` / `CUARTO` / `CAMBUCHE` / `CONTENEDOR` / `OTRO` |
| `creado_por` | UUID | ID del encuestador |
| `created_at_after` | date | Hogares creados desde esta fecha (inclusive) |
| `created_at_before` | date | Hogares creados hasta esta fecha (inclusive) |
| `busqueda` | string | Texto libre en `codigo_hogar` o `observaciones` |
| `ordering` | string | `created_at`, `updated_at`, `estado`, `numero_personas` (prefijo `-` para descendente) |
| `page` | int | Página (default 1, 20 por página) |

**Ejemplo combinado:** `GET /api/hogares/?estado=ACTIVO&tipo_vivienda=CASA&created_at_after=2026-01-01&ordering=-created_at`

### Respuesta del detalle (Sprint 13)

`GET /api/hogares/{id}/` ahora incluye:

```json
{
  "id": "uuid", "autorizado": "uuid-victima", "autorizado_hash": "sha256",
  "municipio": 29, "municipio_nombre": "Medellín",
  "municipio_detalle": { "id": 29, "codigo_dane": "05001", "nombre": "Medellín", ... },
  "tipo_vivienda": "CASA", "tipo_vivienda_display": "Casa",
  "condicion_ocupacion": "ARRIENDO", "condicion_ocupacion_display": "Arriendo",
  "estrato": 2, "numero_cuartos": 3, "numero_personas": 4,
  "estado": "ACTIVO", "estado_display": "Activo — caracterización completa",
  "miembros": [
    {
      "id": "uuid", "rol": "MIEMBRO", "rol_display": "Miembro del hogar",
      "es_autorizado": true, "estado_inclusion": "INCLUIDO",
      "estado_inclusion_display": "Incluido — víctima registrada en el RUV",
      "parentesco": "", "parentesco_display": "",
      "tipo_persona": "5001", "incluido_ruv": true, "tiene_discapacidad": false,
      "victima": "uuid", "victima_hash": "sha256"
    }
  ],
  "total_miembros": 4,
  "sesiones": [
    {
      "id": "uuid", "hogar": "uuid",
      "instrumento": "uuid", "instrumento_nombre": "Territorial",
      "instrumento_numero": "V7",
      "encuestador": "uuid", "encuestador_nombre": "Javier Aguilar",
      "estado": "COMPLETADA", "estado_display": "Completada",
      "porcentaje_completado": 100,
      "fecha_inicio": "2026-05-20T14:00:00Z",
      "fecha_fin": "2026-05-20T15:32:00Z",
      "created_at": "...", "updated_at": "..."
    }
  ],
  "total_sesiones": 1,
  "creado_por": "uuid-usuario", "encuestador_nombre": "Javier Aguilar",
  "created_at": "...", "updated_at": "..."
}
```

---

## Encuestas (Sesiones)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/encuestas/` | Sesiones del encuestador (filtros + paginación cursor) | Sí |
| POST | `/encuestas/` | Iniciar nueva sesión | Sí |
| GET | `/encuestas/{id}/` | Detalle de sesión | Sí |
| GET | `/encuestas/{id}/respuestas/` | Listado de respuestas guardadas | Sí |
| POST | `/encuestas/{id}/responder/` | Guardar respuesta individual | Sí |
| POST | `/encuestas/{id}/responder-bulk/` | Guardar N respuestas en una sola llamada (Sprint 8) | Sí |
| POST | `/encuestas/{id}/finalizar/` | Cerrar sesión (estado COMPLETADA) | Sí |

### Filtros del listado (Sprint 13)

`GET /api/encuestas/` acepta:

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `estado` | string | `INICIADA` / `EN_PROGRESO` / `COMPLETADA` / `SUSPENDIDA` |
| `instrumento` | UUID | Filtrar por instrumento |
| `ruta_entrevista` | string | `GENERAL` / `ACCIONES_CONSTITUCIONALES` / `MODIFICACION_NUCLEO` / `ESPECIAL` |
| `encuestador` | UUID | ID del encuestador |
| `hogar` | UUID | ID del hogar |
| `fecha_inicio_after` | date | Sesiones iniciadas desde esta fecha (inclusive) |
| `fecha_inicio_before` | date | Sesiones iniciadas hasta esta fecha (inclusive) |
| `porcentaje_min` | int | Porcentaje completado >= N |
| `porcentaje_max` | int | Porcentaje completado <= N |
| `ordering` | string | `created_at`, `updated_at`, `porcentaje_completado`, `fecha_inicio`, `fecha_fin` |
| `cursor` | opaco | Cursor de paginación (devuelto en `next` / `previous`) |
| `page_size` | int | Tamaño de página (default 20, máx 200) |

**Paginación cursor:** este endpoint usa `CursorTimePagination` (más estable que offset para listas que crecen rápido). El cliente sigue los enlaces `next` / `previous` sin calcular páginas.

### Crear sesión
```json
{ "hogar": "uuid-hogar", "instrumento": "uuid-instrumento-version" }
```

### Responder pregunta
```json
{ "pregunta_id": "uuid-pregunta", "valor": "1" }
```

### Finalizar sesión
```json
{ "observaciones": "Texto libre opcional" }
```

Estados posibles: `INICIADA` → `EN_PROGRESO` → `COMPLETADA` | `CANCELADA`

### `POST /encuestas/{id}/responder-bulk/` (Sprint 8)

Envía todas las respuestas de un capítulo en una sola llamada. Máximo 2,000 ítems por lote.

```json
{
  "respuestas": [
    { "pregunta_id": "uuid", "valor": "1" },
    { "pregunta_id": "uuid", "valor": "texto libre" }
  ]
}
```

Límites (Sprint 11): `valor` máx 50,000 chars · `observaciones` máx 2,000 chars · máx 2,000 ítems por bulk.

---

## IA Gemini (Asistente)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/ia/mapear-audio/` | Sugerencia de respuesta para una pregunta (audio/texto) | Sí |
| POST | `/ia/procesar-entrevista/` | Batch: extrae respuestas de toda la entrevista de un capítulo | Sí |

**Nota:** El cliente nunca llama directamente a la API de Google.
Todo pasa por el proxy Django que valida consentimiento IA y aplica rate limiting.
Rate limit: **20 consultas / hora por usuario** (`IAConsultaThrottle` — Sprint 11).

### `POST /ia/procesar-entrevista/` (implementado Sprint 7)
```json
{
  "sesion_encuesta_id": "uuid",
  "capitulo_id": "uuid",
  "transcripcion_completa": "Texto de toda la entrevista...",
  "preguntas": [
    {
      "pregunta_id": "uuid",
      "codigo_externo": "C1",
      "texto": "¿En qué tipo de vivienda habita el hogar?",
      "tipo": "LISTA",
      "opciones": ["1","2","3"]
    }
  ]
}
```

Respuesta:
```json
{
  "resultados": [
    {
      "pregunta_id": "uuid",
      "codigo_externo": "C1",
      "sugerencia": "1",
      "confianza": 0.95,
      "razonamiento": "El entrevistado mencionó 'vivimos en una casa'"
    }
  ],
  "total_preguntas": 22,
  "con_sugerencia": 18,
  "sin_sugerencia": 4
}
```

---

## Reportes de Producción (Sprint 10)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/reportes/produccion/` | Resumen del encuestador autenticado | Sí |
| GET | `/reportes/produccion/detalle/` | Sesiones paginadas (`?page=1&estado=completada`) | Sí |
| GET | `/reportes/produccion/export/` | Descarga CSV streaming (`?desde=&hasta=`) | Sí |

**Scoping automático:** cada encuestador solo ve sus propias sesiones. El filtro `encuestador=request.user` se aplica en el servidor.

### `GET /reportes/produccion/`

Parámetros opcionales: `desde=YYYY-MM-DD`, `hasta=YYYY-MM-DD`

```json
{
  "total": 42,
  "completadas": 28,
  "en_progreso": 10,
  "sin_iniciar": 4,
  "hogares_caracterizados": 31,
  "respuestas_total": 4820,
  "promedio_completado": 78.3,
  "por_instrumento": [
    { "instrumento": "TERRITORIAL V7", "total": 18, "completadas": 14 }
  ],
  "sesiones_recientes": []
}
```

---

## Reportes — Supervisor y Dashboard (Sprint 13)

Endpoints habilitadores para el panel web. Requieren perfil con `puede_ver_reportes=True`.

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/reportes/supervisor/` | Métricas comparativas por encuestador (vista supervisor) | Sí — `puede_ver_reportes` |
| GET | `/reportes/dashboard/series/` | Series temporales y distribución por instrumento | Sí — `puede_ver_reportes` |

### `GET /reportes/supervisor/`

Tabla cross-encuestador con métricas agregadas del período.

**Query params:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `desde` | date | Inicio del período (default: día 1 del mes actual) |
| `hasta` | date | Fin del período (default: hoy) |

**Respuesta:**

```json
{
  "periodo_desde": "2026-05-01",
  "periodo_hasta": "2026-05-25",
  "encuestadores_activos": 5,
  "totales": {
    "sesiones_total": 120,
    "sesiones_completadas": 87,
    "sesiones_en_progreso": 30,
    "sesiones_suspendidas": 3,
    "hogares_caracterizados": 80,
    "promedio_completado": 76.4
  },
  "encuestadores": [
    {
      "id": "uuid",
      "codigo_usuario": "ALEXJUT",
      "nombre_completo": "Javier Aguilar",
      "perfil_codigo": "ASISTENCIA",
      "sesiones_total": 30,
      "sesiones_completadas": 25,
      "sesiones_en_progreso": 4,
      "sesiones_suspendidas": 1,
      "hogares_caracterizados": 22,
      "promedio_completado": 82.1,
      "ultima_actividad": "2026-05-25T14:32:00Z"
    }
  ]
}
```

### `GET /reportes/dashboard/series/`

Datos para gráficos del dashboard: serie temporal diaria (últimos 30 días por default) y distribución por instrumento. Si el usuario tiene `puede_administrar=True` ve a todo el equipo; si solo tiene `puede_ver_reportes` ve únicamente sus propias sesiones.

**Query params:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `desde` | date | Inicio del período (default: hoy − 30 días) |
| `hasta` | date | Fin del período (default: hoy) |

**Respuesta:**

```json
{
  "periodo_desde": "2026-04-25",
  "periodo_hasta": "2026-05-25",
  "serie_diaria": [
    { "fecha": "2026-04-25", "sesiones_iniciadas": 4, "sesiones_completadas": 3 },
    { "fecha": "2026-04-26", "sesiones_iniciadas": 2, "sesiones_completadas": 0 }
  ],
  "distribucion_por_instrumento": [
    { "instrumento_codigo": "TERRITORIAL", "instrumento_nombre": "Caracterización Territorial", "total": 45 },
    { "instrumento_codigo": "ASISTENCIA",  "instrumento_nombre": "Asistencia",                  "total": 30 }
  ]
}
```

> **Nota:** la serie incluye todos los días del rango (incluso los días sin actividad, con ceros). Esto evita que el frontend tenga que rellenar los huecos.

---

## Auditoría

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/auditoria/accesos/` | Log de accesos (inmutable) | Supervisor+ |

**LogAcceso es inmutable:** la tabla no tiene permisos UPDATE/DELETE desde la app.

---

## Documentación interactiva

- Swagger UI: `http://localhost:8001/api/docs/`
- ReDoc: `http://localhost:8001/api/redoc/`
- Schema OpenAPI JSON: `http://localhost:8001/api/schema/`
