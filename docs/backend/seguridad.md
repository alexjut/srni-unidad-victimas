# Seguridad Backend — SRNI

**Última actualización:** 2026-04-28

---

## Principios de seguridad (no negociables)

1. **HTTPS obligatorio** en todos los endpoints — `SECURE_SSL_REDIRECT = True`
2. **Sin PII en el cliente** — el RNI vive solo en el servidor
3. **Cifrado en reposo** — campos PII con AES-256 (pgcrypto)
4. **JWT con rotación** — access 15 min, refresh 8 h rotativo
5. **Auditoría completa** — LogAcceso inmutable en cada acción sobre datos de víctimas
6. **Nunca credenciales hardcodeadas** — `python-decouple` + `.env` excluido del repo

---

## Configuración Django (settings/production.py)

```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
```

---

## Autenticación JWT

**Librería:** `djangorestframework-simplejwt`

| Token | TTL | Almacenamiento |
|-------|-----|----------------|
| Access | 15 minutos | Memoria (Zustand en mobile) |
| Refresh | 8 horas | `expo-secure-store` (mobile) |

**Flujo:**
1. POST `/api/auth/login/` → devuelve `access` + `refresh`
2. El cliente usa `access` en cada request: `Authorization: Bearer <token>`
3. Al recibir 401 → el interceptor Axios llama `/api/auth/refresh/` automáticamente
4. Al logout → POST `/api/auth/logout/` → agrega `refresh` a la blacklist

**TokenBlacklist:** jti del refresh token invalidado se guarda en BD. En cada refresh se verifica que el jti no esté en la blacklist.

**Rate limiting auth:**
- 5 intentos de login fallidos → bloqueo 15 min por IP
- Implementado con `django-ratelimit` o middleware custom

---

## Cifrado de campos PII

**Campos cifrados (AES-256 via pgcrypto):**
- `Victima.nombre_completo`
- `Victima.apellidos`
- `Victima.numero_documento`
- `Victima.fecha_nacimiento`
- `MiembroHogar.nombre_completo`
- `MiembroHogar.numero_documento`
- `MiembroHogar.fecha_nacimiento`

**Implementación:**
```python
from encrypted_model_fields.fields import EncryptedCharField

class Victima(Model):
    nombre_completo = EncryptedCharField(max_length=200)
    numero_documento = EncryptedCharField(max_length=20)
    numero_documento_hash = CharField(max_length=64, db_index=True)
    # hash SHA-256 del numero_documento para búsquedas sin descifrar
```

**Búsqueda segura por documento:**
```python
import hashlib
hash_doc = hashlib.sha256(numero_documento.encode()).hexdigest()
Victima.objects.filter(numero_documento_hash=hash_doc)
# Nunca: Victima.objects.filter(numero_documento=...)  ← no funciona con cifrado
```

**Clave de cifrado:**
```
FIELD_ENCRYPTION_KEY=<clave Fernet 32 bytes base64>  # en .env, nunca en el código
```

---

## Auditoría — LogAcceso

Tabla inmutable: sin permisos `UPDATE` ni `DELETE` desde la aplicación.

```python
class LogAcceso(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    usuario = ForeignKey(Usuario, on_delete=PROTECT)
    accion = CharField(max_length=50)   # ver lista de acciones
    ip_origen = GenericIPAddressField()
    user_agent = CharField(max_length=500)
    objeto_tipo = CharField(max_length=50, blank=True)  # 'Victima', 'Hogar', etc.
    objeto_id = CharField(max_length=100, blank=True)
    detalle = JSONField(default=dict)
    timestamp = DateTimeField(auto_now_add=True)

    class Meta:
        # Impide UPDATE y DELETE desde código de app
        default_permissions = ('add', 'view')
```

**Acciones auditadas:**
| Acción | Descripción |
|--------|-------------|
| `LOGIN` | Inicio de sesión exitoso |
| `LOGOUT` | Cierre de sesión |
| `LOGIN_FALLIDO` | Intento fallido de autenticación |
| `BUSCAR_VICTIMA` | Búsqueda en el RNI |
| `VER_VICTIMA` | Acceso a detalle de víctima |
| `CREAR_HOGAR` | Nuevo hogar creado |
| `ACTUALIZAR_HOGAR` | Modificación de hogar |
| `INICIAR_ENCUESTA` | Nueva sesión iniciada |
| `GUARDAR_RESPUESTAS` | Batch de respuestas guardado |
| `CERRAR_ENCUESTA` | Sesión finalizada |
| `LLAMADA_GEMINI` | Asistencia IA solicitada |
| `CONSENTIMIENTO_IA` | Consentimiento IA registrado |

---

## Permisos por rol

| Permiso | ENCUESTADOR_CAMPO | COORDINADOR_DT | SUPERVISOR | ADMINISTRADOR |
|---------|:-----------------:|:--------------:|:----------:|:-------------:|
| `puede_buscar_rni` | ✅ | ✅ | ✅ | ✅ |
| `puede_caracterizar` | ✅ | ✅ | ❌ | ❌ |
| `puede_ver_reportes` | ❌ | ✅ | ✅ | ✅ |
| `puede_administrar` | ❌ | ❌ | ❌ | ✅ |

---

## Rate limiting

| Recurso | Límite | Ventana |
|---------|--------|---------|
| Login fallido | 5 intentos | 15 minutos por IP |
| Búsqueda RNI | 100 búsquedas | 1 hora por usuario |
| Llamadas Gemini | 30 llamadas | 1 hora por usuario |

---

## Headers de seguridad (Nginx)

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Referrer-Policy "no-referrer" always;
```

---

## Cumplimiento normativo

| Norma | Medida implementada |
|-------|---------------------|
| Ley 1581/2012 — Protección datos personales | Cifrado PII, auditoría, minimización |
| CONPES 3995 — Seguridad Digital | HTTPS, JWT, auditoría |
| Decreto 1377/2013 — Reglamento Ley 1581 | Consentimiento IA documentado |
| Principio de finalidad | Solo caracterización — sin acceso a otros sistemas |
| Principio de minimización | Frontend recibe solo campos necesarios por tarea |

---

## Checklist de seguridad por sprint

| Control | Sprint | Estado |
|---------|--------|--------|
| HTTPS forzado (settings) | 1 | ✅ |
| JWT con blacklist | 1 | ✅ |
| PII cifrado AES-256 | 1 | ✅ |
| SHA-256 para búsqueda | 2 | ✅ |
| LogAcceso inmutable | 1 | ✅ |
| Sin PII en SQLite local | 4 | ✅ |
| Consentimiento IA firmado | 5 | ✅ |
| Proxy Gemini (clave no en cliente) | 5 | ✅ |
| Validadores cruzados de hogar | 6 | ✅ |
