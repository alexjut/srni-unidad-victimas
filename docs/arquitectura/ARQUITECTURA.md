# Arquitectura — Sistema Web SRNI
**Stack:** Django REST Framework + Angular 17  
**Versión:** 1.0  
**Fecha:** 2026-04-09

---

## 1. Visión General

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTERNET (HTTPS/TLS 1.3)                      │
└──────────────┬──────────────────────────────────┬───────────────┘
               │                                  │
    ┌──────────▼──────────┐             ┌─────────▼──────────┐
    │   Angular 17 SPA     │             │   Nginx (Reverse   │
    │   (encuestador)      │             │   Proxy + WAF)     │
    │   - PWA offline      │             └─────────┬──────────┘
    │   - IndexedDB cache  │                       │
    └──────────────────────┘             ┌─────────▼──────────┐
                                         │  Django REST API   │
                                         │  (Gunicorn/uvicorn)│
                                         └─────────┬──────────┘
                                                   │
                            ┌──────────────────────┼──────────────┐
                            │                      │              │
                   ┌────────▼──────┐    ┌──────────▼────┐  ┌─────▼─────┐
                   │  PostgreSQL   │    │     Redis      │  │  MinIO /  │
                   │  (pgcrypto)   │    │  (Cache+Queue) │  │  S3 docs  │
                   └───────────────┘    └───────────────┘  └───────────┘
```

---

## 2. Principios de Seguridad (No Negociables)

1. **HTTPS obligatorio** — TLS 1.2+ en todos los endpoints. HSTS habilitado.
2. **Datos sensibles nunca en cliente** — El RNI vive solo en el servidor. El frontend recibe únicamente lo necesario por sesión.
3. **Cifrado en reposo** — Campos PII cifrados con `pgcrypto` (AES-256). BD completa sobre volumen cifrado (LUKS).
4. **JWT con refresh tokens** — Access token (15 min), Refresh token (8 horas laborales), rotación en cada uso.
5. **Auditoría completa** — Toda acción sobre datos de víctimas queda registrada (quién, qué, cuándo, desde dónde).
6. **Sin backups de cliente** — Service Worker limpia IndexedDB al cerrar sesión.
7. **Cumplimiento Ley 1581/2012** — Habeas Data, consentimiento, minimización de datos.

---

## 3. Componentes del Backend (Django REST Framework)

### 3.1 Aplicaciones Django

```
srni_backend/
├── apps/
│   ├── autenticacion/       — JWT auth, roles, perfiles de encuestador
│   ├── victimas/            — Registro Nacional de Información (RNI)
│   ├── formulario/          — Motor de formularios dinámico (54 módulos)
│   ├── hogares/             — Hogares y miembros
│   ├── encuestas/           — Sesiones de encuesta y respuestas
│   ├── parametricas/        — Municipios, veredas, comunidades étnicas
│   ├── sincronizacion/      — Importación/exportación de datos de campo
│   ├── auditoria/           — Log de accesos y cambios
│   └── reportes/            — Reportes de producción por encuestador
```

### 3.2 Autenticación y Autorización

```python
# Flujo JWT
POST /api/auth/login/          → { access: "...", refresh: "..." }
POST /api/auth/refresh/        → { access: "..." }
POST /api/auth/logout/         → Invalida refresh token (blacklist)
GET  /api/auth/me/             → Perfil y permisos del usuario

# Perfiles de encuestador
ENCUESTADOR_CAMPO    — Puede buscar, caracterizar, enviar encuestas
COORDINADOR_DT       — Lo anterior + ver resumen de su equipo
SUPERVISOR           — Acceso de solo lectura a todas las encuestas
ADMINISTRADOR        — CRUD de usuarios, instrumentos, parametricas
```

### 3.3 API REST — Recursos principales

```
# Víctimas (RNI)
GET  /api/victimas/buscar/?doc=&nombre=&dpto=    — Búsqueda con filtros
GET  /api/victimas/{id}/                         — Detalle (solo campos permitidos por perfil)

# Formulario dinámico
GET  /api/instrumento/modulos/                   — Módulos activos para el perfil
GET  /api/instrumento/modulos/{id}/preguntas/    — Preguntas de un módulo
GET  /api/instrumento/preguntas/{id}/opciones/   — Opciones de respuesta
POST /api/instrumento/validar/                   — Valida respuesta en servidor

# Hogares y encuestas
POST /api/hogares/                               — Crear hogar
GET  /api/hogares/{codigo}/                      — Detalle hogar
POST /api/hogares/{codigo}/miembros/             — Agregar miembro
GET  /api/hogares/{codigo}/progreso/             — Progreso por módulo

# Sesiones de encuesta
POST /api/encuestas/iniciar/                     — Inicia sesión de encuesta
POST /api/encuestas/{id}/responder/              — Guarda respuesta
POST /api/encuestas/{id}/finalizar/              — Cierra encuesta
GET  /api/encuestas/{id}/resumen/                — Resumen para revisión

# Paramétricas
GET  /api/parametricas/departamentos/
GET  /api/parametricas/municipios/?dpto=
GET  /api/parametricas/veredas/?mpio=
GET  /api/parametricas/comunidades-negras/
GET  /api/parametricas/resguardos-indigenas/
GET  /api/parametricas/puntos-atencion/?dt=
```

### 3.4 Motor de Formulario Dinámico

El sistema debe replicar la lógica de `DiligenciarPregunta` en el servidor:

```python
class EvaluadorLogicaFormulario:
    """
    Determina qué preguntas mostrar/ocultar dado el estado actual
    de respuestas de un hogar/persona.
    
    Reglas implementadas:
    - PREDEPENDE: pregunta aparece si otra tiene valor específico
    - VALTODOHOGAR: pregunta aplica a todos los miembros
    - VALRESPUESTAMULTIPLE: permite selección múltiple
    - VALIDVALIDADORDATO: tipo de dato esperado (fecha, número, texto)
    - PREVALIDADORMAX/MIN: rangos permitidos
    - RDEFAULT: valor por defecto
    - RESFINALIZA: respuesta que cierra el módulo
    - RESHABILITA: respuesta que habilita nuevas preguntas
    """
```

### 3.5 Seguridad implementada en Django

```python
# settings/production.py
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Rate limiting (django-ratelimit)
# Login: 5 intentos / 15 min por IP
# API general: 1000 req / hora por usuario
# Búsqueda RNI: 100 req / hora por usuario

# Campos PII cifrados (django-encrypted-model-fields)
# pgcrypto para campos en PostgreSQL
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY')  # Nunca hardcodeado
```

---

## 4. Componentes del Frontend (Angular 17)

### 4.1 Estructura de módulos

```
srni-frontend/
├── core/
│   ├── auth/           — JWT interceptor, guards, servicios de auth
│   ├── http/           — HTTP interceptor (auth header, error handling)
│   └── audit/          — Client-side logging
├── features/
│   ├── login/          — Pantalla de autenticación
│   ├── dashboard/      — Resumen y estadísticas del encuestador
│   ├── busqueda-victimas/ — Búsqueda en el RNI
│   ├── conformar-hogar/   — Creación y gestión de hogares
│   ├── formulario/     — Motor de formulario dinámico (componente clave)
│   │   ├── pregunta/   — Componente genérico de pregunta
│   │   ├── modulo/     — Wrapper de módulo (capítulo)
│   │   └── validador/  — Validación en tiempo real
│   ├── resumen-encuesta/  — Vista final antes de enviar
│   └── reportes/       — Resumen de producción
├── shared/
│   ├── components/     — UI compartida
│   └── pipes/          — Formateo de datos (documento, fecha)
└── offline/            — PWA + Service Worker + IndexedDB sync
```

### 4.2 Offline-first con PWA

Para trabajo de campo con conectividad limitada:

```typescript
// Estrategia offline
// 1. El instrumento (módulos + preguntas + opciones) se cachea al iniciar sesión
// 2. Las respuestas se guardan en IndexedDB mientras sin conexión
// 3. Service Worker sincroniza automáticamente al recuperar red
// 4. Al cerrar sesión: IndexedDB limpia completamente (sin datos PII en cliente)

// NUNCA se cachean:
// - Datos del RNI (víctimas)
// - Respuestas enviadas
// - Tokens de acceso (solo sessionStorage, nunca localStorage)
```

### 4.3 Tipos de campo del formulario

El motor debe renderizar los mismos tipos que la app Android:

| PRETIPOCAMPO | Componente Angular | Descripción |
|---|---|---|
| `TEXTO` | InputComponent | Campo de texto libre |
| `NUMERICO` | NumericInputComponent | Solo números, con min/max |
| `FECHA` | DatePickerComponent | Selector de fecha |
| `LISTA` | SelectComponent | Lista desplegable |
| `LISTA_MULTIPLE` | MultiSelectComponent | Selección múltiple |
| `RADIO` | RadioGroupComponent | Selección única con opciones |
| `BOOLEAN` | ToggleComponent | Sí/No |
| `TEXTO_LARGO` | TextAreaComponent | Observaciones |
| `COMBO_DINAMICO` | AsyncSelectComponent | Lista cargada por query (EMCADMONCOMBOS) |

---

## 5. Base de Datos (PostgreSQL + pgcrypto)

### 5.1 Por qué PostgreSQL y no SQLite

| Aspecto | SQLite (actual) | PostgreSQL (nuevo) |
|---------|---------|---------|
| Cifrado en reposo | No | Sí (pgcrypto + LUKS) |
| Concurrencia | Limitada | Alta (MVCC) |
| Usuarios simultáneos | 1 por BD | Cientos |
| Campos cifrados | No | pgcrypto (AES-256) |
| Auditoría nativa | No | Sí (triggers) |
| Backups seguros | Inseguros | pg_dump cifrado |
| Full-text search | Básico | Avanzado (para búsqueda RNI) |

### 5.2 Cifrado de campos PII

```sql
-- Campos cifrados con pgcrypto en tabla victimas
UPDATE victimas SET
  primer_nombre = pgp_sym_encrypt(primer_nombre, current_setting('app.encryption_key')),
  segundo_nombre = pgp_sym_encrypt(segundo_nombre, current_setting('app.encryption_key')),
  primer_apellido = pgp_sym_encrypt(primer_apellido, current_setting('app.encryption_key')),
  segundo_apellido = pgp_sym_encrypt(segundo_apellido, current_setting('app.encryption_key')),
  numero_documento = pgp_sym_encrypt(numero_documento, current_setting('app.encryption_key')),
  fecha_nacimiento = pgp_sym_encrypt(fecha_nacimiento::text, current_setting('app.encryption_key'));
```

---

## 6. Infraestructura y Despliegue

```yaml
# docker-compose.prod.yml (simplificado)
services:
  nginx:
    image: nginx:alpine
    ports: ["443:443"]
    # TLS 1.2+, HSTS, WAF rules
    
  backend:
    build: ./backend
    command: gunicorn srni.wsgi --workers 4
    env_file: .env.prod   # NUNCA credenciales hardcodeadas
    
  frontend:
    build: ./frontend
    # Build estático servido por nginx
    
  postgres:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data  # Volumen cifrado LUKS
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password  # Docker secrets
      
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    
  celery:
    build: ./backend
    command: celery -A srni worker -Q sync,reports
```

---

## 7. Reemplazo de Funcionalidades Críticas

| Función APK | Implementación Web |
|-------------|-------------------|
| Descarga BD víctimas por FTP | RNI en servidor, API de búsqueda paginada |
| Instrumento via FTP | API versioned `/api/instrumento/version/` |
| AsyncTask para operaciones largas | Celery tasks + WebSocket progress |
| SQLite local sin cifrar | PostgreSQL con pgcrypto (servidor) |
| Token custom sin expiración | JWT (15 min access + 8h refresh rotativo) |
| `allowBackup=true` | N/A — app web, sin datos locales persistentes |
| HTTP cleartext | HTTPS obligatorio (HSTS) |
| Contraseña en texto plano | Argon2 (Django default desde 4.0) |
| FTP upload de encuestas | `POST /api/encuestas/{id}/finalizar/` HTTPS |

---

## 8. Consideraciones de Cumplimiento (Ley 1581/2012)

- **Responsable del tratamiento:** Unidad para las Víctimas identificada en cada request
- **Finalidad:** Registro y caracterización — no se permite uso para otro fin
- **Minimización:** El frontend solo recibe campos necesarios para la tarea
- **Derechos ARCO:** API para consulta, rectificación, actualización
- **Auditoría:** Log inmutable de todos los accesos a datos de víctimas
- **Transferencia:** Sin transferencia a terceros (eliminar `isegoria.co`)
- **Seguridad:** HTTPS + cifrado en reposo + autenticación fuerte
- **Retención:** Política de retención configurable por tipo de dato
