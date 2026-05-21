# API Endpoints — Backend SRNI

**Framework:** Django REST Framework  
**Base URL dev:** `http://localhost:8001/api/`  
**Base URL prod:** `https://srniapk-dev.ngrok.app/api/` (tunnel ngrok)  
**Autenticación:** JWT Bearer Token  
**Última actualización:** 2026-05-06

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
Rate limit: 100 búsquedas / hora por usuario.

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
| GET | `/hogares/` | Hogares del encuestador autenticado | Sí |
| POST | `/hogares/` | Crear nuevo hogar | Sí |
| GET | `/hogares/{id}/` | Detalle de hogar | Sí |
| PATCH | `/hogares/{id}/` | Actualizar hogar | Sí |
| GET | `/hogares/{id}/miembros/` | Miembros del hogar | Sí |
| POST | `/hogares/{id}/miembros/` | Agregar miembro | Sí |

### Crear hogar
```json
{
  "jefe_hogar": "uuid-victima",
  "municipio": 29,
  "tipo_vivienda": "CASA",
  "condicion_ocupacion": "ARRIENDO",
  "estrato": 2,
  "numero_cuartos": 3,
  "numero_personas": 4
}
```

---

## Encuestas (Sesiones)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/encuestas/` | Sesiones del encuestador | Sí |
| POST | `/encuestas/` | Iniciar nueva sesión | Sí |
| GET | `/encuestas/{id}/` | Detalle de sesión | Sí |
| POST | `/encuestas/{id}/responder/` | Guardar respuesta individual | Sí |
| POST | `/encuestas/{id}/finalizar/` | Cerrar sesión (estado COMPLETADA) | Sí |

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

---

## IA Gemini (Asistente)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/ia/mapear-audio/` | Sugerencia de respuesta para una pregunta (audio/texto) | Sí |
| POST | `/ia/procesar-entrevista/` | Batch: extrae respuestas de toda la entrevista de un capítulo | Sí ⚠️ Pendiente |

**Nota:** El cliente nunca llama directamente a la API de Google.
Todo pasa por el proxy Django que valida consentimiento IA y aplica rate limiting.

### `POST /ia/procesar-entrevista/` (pendiente Sprint 7)
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

## Auditoría

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/auditoria/accesos/` | Log de accesos (inmutable) | Supervisor+ |
| GET | `/reportes/produccion/` | Producción por encuestador | Supervisor+ |

**LogAcceso es inmutable:** la tabla no tiene permisos UPDATE/DELETE desde la app.

---

## Documentación interactiva

- Swagger UI: `http://localhost:8001/api/docs/`
- ReDoc: `http://localhost:8001/api/redoc/`
- Schema OpenAPI JSON: `http://localhost:8001/api/schema/`
