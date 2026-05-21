# Sprint 11 — Security Hardening

**Branch:** `feature/sprint11-security-hardening`  
**Estado:** ✅ Completo  
**Inicio:** 2026-05-17  
**Cierre:** 2026-05-21

---

## Objetivos del sprint

Auditoría de seguridad completa y corrección de todos los controles faltantes identificados:

1. Rate limiting en endpoints críticos (login, búsqueda RNI, IA)
2. Eliminar `eval()` del motor de skip logic — reemplazar con evaluador AST seguro
3. Validación de longitud máxima en serializers de entrada
4. Configuración de producción completa (DATABASES, SSL, CSRF)
5. Nginx: HTTPS forzado, TLS moderno, headers de seguridad, CSP, rate limiting

---

## Controles auditados

| Control | Estado antes | Estado después |
|---------|-------------|----------------|
| Rate limiting login | ❌ Sin límite | ✅ 5 req/min por IP (`LoginRateThrottle`) |
| Rate limiting búsqueda RNI | ❌ Sin límite | ✅ 30 req/h por usuario (`BusquedaRNIThrottle`) |
| Rate limiting IA | ❌ Sin límite | ✅ 20 req/h por usuario (`IAConsultaThrottle`) |
| `eval()` en skip logic | ❌ Inseguro | ✅ Evaluador AST restringido |
| `max_length` en respuestas | ❌ Sin límite | ✅ 50,000 chars / ítem; máx 2,000 ítems bulk |
| DATABASES producción | ❌ Incompleto | ✅ PostgreSQL + SSL + python-decouple |
| CSRF_TRUSTED_ORIGINS | ❌ Ausente | ✅ Desde variable de entorno |
| Nginx HTTPS | ❌ No existía | ✅ Redirect 80→443 + TLS 1.2/1.3 |
| Headers de seguridad HTTP | ❌ No existían | ✅ HSTS, X-Frame, CSP, Referrer, Permissions |
| `PuedeCaracterizar` en formulario | ❌ Solo IsAuthenticated | ✅ Agrega PuedeCaracterizar |
| GEMINI_API_KEY en `.env.example` | ❌ No documentado | ✅ Agregado |
| Docker Secrets README | ❌ Sin guía | ✅ `infra/secrets/README.md` |

---

## Decisiones técnicas

### Evaluador AST seguro (reemplaza `eval()`)

`eval()` sobre expresiones de la BD es inseguro incluso si la fuente es "de confianza". Se reemplazó con un evaluador que solo permite nodos AST explícitamente permitidos:

```python
# apps/formulario/views.py
_CMP_OPS = {
    ast.Eq:    operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt:    operator.lt,
    ast.LtE:   operator.le,
    ast.Gt:    operator.gt,
    ast.GtE:   operator.ge,
    ast.In:    lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

_BOOL_OPS = {ast.And: all, ast.Or: any}

def _safe_eval(node, ctx):
    # Solo acepta: Expression, Constant, Name, List, Compare, BoolOp, Not
    # Lanza ValueError para cualquier otro nodo
    ...
```

Cualquier expresión con nodos no permitidos (llamadas a funciones, imports, etc.) genera `ValueError` y la regla se evalúa como `False` — fail-safe.

### Throttling DRF — tres throttles

```python
# apps/autenticacion/throttles.py
class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'           # 5/minute

class BusquedaRNIThrottle(UserRateThrottle):
    scope = 'busqueda_rni'    # 30/hour

class IAConsultaThrottle(UserRateThrottle):
    scope = 'ia_consulta'     # 20/hour
```

Aplicados directamente en la vista:
```python
class LoginView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]

class BuscarVictimaView(APIView):
    throttle_classes = [BusquedaRNIThrottle]
```

### Nginx — rate limiting doble capa

Nginx aplica rate limiting *antes* de que el request llegue a Django (primera línea de defensa):

```nginx
limit_req_zone $binary_remote_addr zone=api_general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api_login:10m  rate=3r/m;

location /api/auth/login/ {
    limit_req zone=api_login burst=5 nodelay;
    ...
}

location /api/ {
    limit_req zone=api_general burst=20 nodelay;
    ...
}
```

DRF throttle es la segunda capa (post-autenticación, por usuario).

### Content-Security-Policy

```nginx
add_header Content-Security-Policy
  "default-src 'self';
   img-src 'self' data: https://www.unidadvictimas.gov.co;
   style-src 'self' 'unsafe-inline';
   script-src 'self';
   connect-src 'self';
   font-src 'self' data:;
   frame-ancestors 'none'" always;
```

`frame-ancestors 'none'` equivale a `X-Frame-Options: DENY` — ambos están presentes para compatibilidad con navegadores sin soporte CSP Level 2.

### Validación de longitud en serializers

```python
# encuestas/serializers.py
valor = serializers.CharField(allow_blank=True, max_length=50_000)

def validate_respuestas(self, value):
    if not value:
        raise serializers.ValidationError('Se requiere al menos una respuesta.')
    if len(value) > 2_000:
        raise serializers.ValidationError('Máximo 2000 respuestas por lote.')
    return value
```

Previene ataques de payload gigante que agotan memoria del servidor.

---

## Archivos creados / modificados

| Archivo | Cambio |
|---------|--------|
| `srni-backend/apps/autenticacion/throttles.py` | NUEVO — 3 clases de throttle |
| `srni-backend/apps/autenticacion/views.py` | `throttle_classes` en `LoginView` |
| `srni-backend/apps/victimas/views.py` | `throttle_classes` en `BuscarVictimaView` |
| `srni-backend/srni/settings/base.py` | `DEFAULT_THROTTLE_RATES` con 5 scopes |
| `srni-backend/srni/settings/production.py` | DATABASES PostgreSQL + SSL, CSRF_TRUSTED_ORIGINS |
| `srni-backend/apps/formulario/views.py` | AST evaluator, `PuedeCaracterizar` en ReadOnlyViewSet |
| `srni-backend/apps/encuestas/serializers.py` | `max_length`, límite bulk 2000 |
| `srni-backend/.env.example` | Agrega `GEMINI_API_KEY` |
| `infra/nginx/srni.conf` | NUEVO — configuración completa Nginx |
| `infra/secrets/README.md` | NUEVO — guía Docker Secrets |
| `CLAUDE.md` | Tabla sprints actualizada hasta Sprint 11 |

---

## Referencia rápida — configuración producción

### Variables de entorno requeridas (`.env`)

```bash
SECRET_KEY=...              # 50+ chars
DEBUG=False
ALLOWED_HOSTS=srni.unidadvictimas.gov.co
DB_NAME=srni_db_produccion
DB_USER=srni_app
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432
DB_SSL_MODE=require
FIELD_ENCRYPTION_KEY=...    # 32 bytes en base64
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=...
MINIO_ENDPOINT=https://minio.srni.interno
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=srni-docs
CORS_ALLOWED_ORIGINS=https://srni.unidadvictimas.gov.co
GEMINI_API_KEY=...
```

### Docker Secrets requeridos

```bash
printf 'srni_db_produccion' > infra/secrets/pg_db.txt
printf 'srni_app'           > infra/secrets/pg_user.txt
printf 'PASSWORD_SEGURO'    > infra/secrets/pg_password.txt
printf 'PASSWORD_REDIS'     > infra/secrets/redis_password.txt
printf 'CLAVE_AES_BASE64'   > infra/secrets/field_encryption_key.txt
chmod 600 infra/secrets/*.txt
```

### Nginx — activar en producción

```bash
sudo cp infra/nginx/srni.conf /etc/nginx/sites-available/srni
sudo ln -s /etc/nginx/sites-available/srni /etc/nginx/sites-enabled/srni
sudo nginx -t && sudo systemctl reload nginx
```

---

## Tareas pendientes (backlog)

| Tarea | Prioridad |
|-------|-----------|
| Panel de supervisión web (Angular/Django Admin) | Alta — Fase 2 |
| Pruebas de carga con Locust | Media |
| Firma digital encuestador al cerrar sesión | Media |
| Push notifications para asignaciones | Baja |
| Auditoría externa de penetración | Alta (antes de producción) |
