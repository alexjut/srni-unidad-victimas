# API Endpoints — Backend SRNI

**Framework:** Django REST Framework  
**Base URL:** `https://api.srni.unidadvictimas.gov.co/api/v1/`  
**Autenticación:** JWT Bearer Token  
**Última actualización:** 2026-04-28

---

## Autenticación

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/auth/login/` | Obtener access + refresh token | No |
| POST | `/auth/refresh/` | Renovar access token | No |
| POST | `/auth/logout/` | Invalidar refresh token (blacklist) | Sí |
| GET | `/auth/me/` | Perfil y permisos del usuario | Sí |

### Respuesta de login
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "usuario": {
    "id": "uuid",
    "nombre_completo": "...",
    "perfil": "ENCUESTADOR_CAMPO",
    "punto_atencion": "..."
  }
}
```

---

## Búsqueda RNI

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/victimas/buscar/` | Buscar víctima por doc/nombre (server-side) | Sí |
| GET | `/victimas/{id}/` | Detalle de víctima (solo campos necesarios) | Sí |

**Importante:** Nunca se devuelven datos PII completos al cliente.
El RNI vive exclusivamente en el servidor.

---

## Formularios / Instrumentos

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/formulario/perfiles/` | Lista de perfiles disponibles para el usuario | Sí |
| GET | `/formulario/instrumento/{perfilCodigo}/` | Capítulos y preguntas del instrumento | Sí |
| GET | `/formulario/capitulo/{id}/preguntas/` | Preguntas de un capítulo | Sí |

---

## Hogares

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/hogares/` | Lista de hogares del encuestador | Sí |
| POST | `/hogares/` | Crear nuevo hogar | Sí |
| GET | `/hogares/{id}/` | Detalle de hogar | Sí |
| PATCH | `/hogares/{id}/` | Actualizar datos del hogar | Sí |
| GET | `/hogares/{id}/miembros/` | Miembros del hogar | Sí |
| POST | `/hogares/{id}/miembros/` | Agregar miembro | Sí |

---

## Encuestas (Sesiones)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/encuestas/` | Sesiones del encuestador | Sí |
| POST | `/encuestas/` | Iniciar nueva sesión de encuesta | Sí |
| GET | `/encuestas/{id}/` | Detalle de sesión | Sí |
| POST | `/encuestas/{id}/respuestas/` | Guardar respuestas (batch) | Sí |
| POST | `/encuestas/{id}/cerrar/` | Cerrar y firmar sesión | Sí |

---

## IA Gemini (Asistente)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/ia/transcribir/` | Transcripción de audio a texto | Sí |
| POST | `/ia/asistir/` | Asistencia en respuesta de pregunta | Sí |

**Nota:** El cliente nunca llama directamente a la API de Google.
Todo pasa por el proxy Django que valida consentimiento y aplica rate limiting.

---

## Auditoría (solo lectura para supervisores)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/auditoria/accesos/` | Log de accesos del equipo | Supervisor+ |
| GET | `/reportes/produccion/` | Producción por encuestador | Supervisor+ |
