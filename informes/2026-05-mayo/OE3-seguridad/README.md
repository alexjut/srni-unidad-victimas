# OE3 — Medidas de seguridad — protección de datos PII

> **Obligación contractual:** *Procesar, implementar y documentar medidas de seguridad para proteger la integridad, confiabilidad y confidencialidad de los datos utilizados para el procedimiento de Instrumentalización, de acuerdo con su naturaleza, calidad y contexto en soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se implementó un **hardening de seguridad integral** alineado con la Ley 1581/2012 (Habeas Data), CONPES 3995 (Confianza Digital) y Decreto 1377/2013. En el **Sprint 11** se aplicaron las siguientes medidas: throttle de 5 intentos de login cada 15 minutos por IP y 100 búsquedas RNI por hora por usuario; sustitución de la peligrosa función `eval()` por un parser AST seguro con lista blanca de nodos permitidos para evaluación de expresiones de skip logic; máximos de longitud (`max_length`) en todos los serializers como protección anti-DoS; configuración de DATABASES para producción con SSL forzado; headers CSP en Nginx; gestión de secretos con Docker Secrets en `infra/secrets/` (excluidos del repositorio); cookies seguras (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS=DENY`); y rotación de tokens JWT (access 15 min, refresh 8 h rotativo). En el **Sprint 18 Fase G** se realizó una **auditoría propia de fuga de PII en logs remotos**: se identificó que el interceptor axios del cliente móvil enviaba la URL completa (con número de documento en query string) al endpoint `/api/_debug/log/`; se implementó un **redactor PII** que detecta 5 endpoints sensibles (`/api/victimas/`, `/api/hogares/`, `/api/encuestas/`, `/api/auth/login/`, `/api/auth/cambiar-password/`) y omite el query string + reemplaza el body por `[REDACTADO — endpoint PII]`. Adicionalmente, todos los campos PII (nombres, apellidos, documento, fecha de nacimiento) están **cifrados en reposo** con `EncryptedCharField` (Fernet AES-128) y se acompañan de un hash SHA-256 para búsqueda eficiente sin desencriptar. La auditoría inmutable se garantiza mediante el modelo `LogAcceso` (tabla sin permisos UPDATE ni DELETE desde la app) que registra cada consulta a víctimas, cada respuesta y cada finalización de sesión.

## Evidencia que soporta esta actividad

- **Cifrado de PII en reposo:** `srni-backend/apps/victimas/fields.py` (definición de `EncryptedCharField`) y `srni-backend/apps/victimas/models.py` (uso en campos PII).
- **Auditoría inmutable LogAcceso:** `srni-backend/apps/auditoria/models.py` + `views.py`.
- **Hardening Sprint 11:** `srni-backend/srni/settings/production.py` con todas las directivas de seguridad.
- **Redactor PII en logs (Sprint 18-G):** `srni-mobile/src/api/client.ts` (líneas 40-100).
- **Configuración Nginx con TLS + CSP:** `infra/nginx/srni.conf`.
- **Docker Secrets:** `infra/secrets/` (estructura presente, contenido excluido del repo por `.gitignore`).
- **Hash SHA-256 para búsqueda PII:** `Victima.numero_documento_hash` (índice db_index=True).
- **Commits clave:** `5ff906b` (Sprint 11 hardening) y `d289a7c` (Sprint 18-G redactor PII).
- **Copias locales en esta carpeta:** `fields.py`, `logacceso-models.py`, `client-ts-redactor.txt`, `settings-hardening.txt`.

---

## Actividades del cronograma

1. Informe de hallazgos de seguridad del APK (3 críticos)
2. Implementación cifrado AES-256 campos PII
3. HTTPS, JWT seguro, tokens en SecureStore
4. Auditoría inmutable de accesos (LogAcceso)

## Hallazgos del APK original (línea base — anti-patrones que NO se repiten)

| Hallazgo | Severidad | Cómo se reemplaza |
|---|---|---|
| HTTP sin TLS (`usesCleartextTraffic=true`) | 🔴 Crítica | HTTPS obligatorio + `SECURE_SSL_REDIRECT=True` |
| 785 MB de PII de 9.4 M víctimas en disco | 🔴 Crítica | Búsqueda server-side only, paginada, NUNCA cachear PII en dispositivo |
| FTP plano a `ftp.isegoria.co` (tercero) | 🔴 Crítica | Sincronización HTTPS exclusivamente a servidores propios |
| Contraseñas en TEXT plano | 🔴 Crítica | Argon2 (Django default) |
| `allowBackup=true` (ADB extrae todo) | 🟡 Alta | `allowBackup=false` en mobile |
| SQLite sin cifrar | 🟡 Alta | PostgreSQL + pgcrypto + LUKS en producción |
| `TOKENUSUARIO` string sin TTL | 🟡 Alta | JWT: access 15 min + refresh 8 h rotativo |
| Credenciales hardcodeadas | 🟡 Alta | `python-decouple` + `.env` + Docker Secrets |

## Avances en Mayo 2026

### Sprint 7 — SecureStore + biometría (4-8 mayo)

- Tokens JWT en `expo-secure-store` (NUNCA `localStorage`)
- Auto-habilitación biométrica en primer login
- `expo-local-authentication` para huella/Face ID

### Sprint 11 — Hardening completo (21 mayo)

- **Throttle:**
  - Login: 5 intentos / 15 min por IP
  - Búsqueda RNI: 100 / hora por usuario
- **eval() → AST seguro:** las expresiones de skip logic se parsean con `ast.parse` en modo `eval`, lista blanca de nodos permitidos. Cero `eval()` en el código.
- **max_length** en todos los serializers (anti-DoS por payload gigante)
- **DATABASES producción** con SSL forzado
- **CSP headers** en Nginx
- **Docker Secrets** en `infra/secrets/` (excluidos del repo)
- **Cookies:** `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS=DENY`

**Commit:** `5ff906b` feat(sprint11): security hardening

### Sprint 18 Fase G — Redactor PII en logs remotos (26 mayo)

Problema detectado: el interceptor de respuesta de axios logueaba `original.url` (con query string) y `error.response.data` (body) al endpoint `/api/_debug/log/`. Para URLs como `/api/victimas/buscar/?numero_documento=1030547250` esto filtraba la cédula a logs.

Fix:
- Lista `ENDPOINTS_PII` con prefijos sensibles
- `sanitizarUrl()`: omite query string + marca "[query+body redactados por PII]"
- `sanitizarBody()`: devuelve "[REDACTADO — endpoint PII]" para endpoints sensibles

**Commit:** `d289a7c` fix(sprint18-G): redactar PII en logs remotos

### Cifrado PII

Campos cifrados con `EncryptedCharField` (Fernet AES-128):
- `Victima.primer_nombre`, `segundo_nombre`, `primer_apellido`, `segundo_apellido`
- `Victima.numero_documento`
- `Victima.fecha_nacimiento`
- `MiembroHogar.nombre_completo`, `numero_documento`

**Búsqueda eficiente sobre PII cifrado:** índice SHA-256 (`numero_documento_hash`) que se calcula al guardar y se usa para `WHERE hash = ?` sin desencriptar.

### Auditoría inmutable

Tabla `LogAcceso`:
- Se registra cada consulta a `Victima`, cada `RESPONDER_PREGUNTA`, cada `FINALIZAR_ENCUESTA`
- Campos: usuario, acción, recurso, recurso_id, IP, user_agent, resultado, detalle JSON, timestamp
- **Sin permisos UPDATE ni DELETE** sobre esta tabla desde la app (solo INSERT)

## Cumplimiento normativo

| Norma | Implementación |
|---|---|
| Ley 1581/2012 (Habeas data) | Cifrado PII en reposo + cifrado en tránsito (TLS) + LogAcceso + endpoints ARCO |
| CONPES 3995 (Confianza digital) | Hardening Sprint 11 + Sprint 18-G |
| Decreto 1377/2013 (Reglamentario Ley 1581) | Principio de minimización: el frontend solo recibe campos necesarios; en listas no se devuelve PII directa |
| Resolución MINTIC 1519 | Aplica en negativo: datos de víctimas NO son datos abiertos. Endpoints protegidos por JWT + permisos |

## Archivos relevantes

Copias locales:

- [`fields.py`](fields.py) — definición de `EncryptedCharField`
- [`logacceso-models.py`](logacceso-models.py) — modelo de auditoría inmutable
- [`client-ts-redactor.txt`](client-ts-redactor.txt) — interceptor axios con redactor PII (Sprint 18-G)
- [`settings-hardening.txt`](settings-hardening.txt) — fragment de settings/production con todas las directivas de seguridad

Referencias al repo:

- `srni-backend/apps/victimas/models.py` — modelo Víctima con campos cifrados
- `srni-backend/apps/auditoria/` — app de LogAcceso
- `srni-backend/srni/settings/production.py` — hardening de producción
- `srni-mobile/src/api/client.ts` — interceptor con redactor PII
- `infra/nginx/` — configuración Nginx + TLS + CSP

## Pendientes (a complementar Javier)

- Anexar el documento "Informe de Hallazgos APK" formal (firmado)
- Anexar pruebas de pen-test cuando se contrate
- Confirmar con Oscar el procedimiento ARCO oficial UARIV
