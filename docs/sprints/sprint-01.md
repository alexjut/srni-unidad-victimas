# Sprint 1 — Fundamentos: Backend + Scaffold Mobile

**Branch:** `main` (initial commit)
**Estado:** ✅ Completado
**Inicio:** 2026-04-13
**Cierre:** 2026-04-13
**Commit:** `b08bc47`

---

## Objetivos

1. Configurar la estructura base del proyecto Django REST Framework
2. Implementar autenticación JWT segura (reemplaza sistema WCF SOAP del APK original)
3. Modelar la base de datos con PII cifrado desde el inicio
4. Crear el scaffold de la app móvil con routing y estado global
5. Establecer estándares de seguridad que corrijan los errores del APK v4.1

---

## Entregables backend

### Configuración Django
- `srni/settings/base.py` — configuración compartida
- `srni/settings/development.py` — sobrescrituras para local
- `srni/settings/production.py` — HTTPS, HSTS, cookies seguras
- Swagger/OpenAPI disponible en `/api/docs/`
- Docker Compose configurado para PostgreSQL + Redis

### Apps creadas
| App | Descripción |
|-----|-------------|
| `autenticacion` | JWT login/refresh/logout/me, roles y perfiles de encuestador |
| `victimas` | Modelo Victima con PII cifrado (Ley 1581/2012) |
| `formulario` | Scaffold del motor dinámico de 54 módulos |
| `hogares` | Scaffold de hogares y miembros |
| `encuestas` | Scaffold de sesiones de encuesta |
| `parametricas` | Scaffold de tablas geográficas |
| `auditoria` | LogAcceso inmutable |

### Modelos implementados

**Usuario** — Reemplaza `EMCUSUARIOS` del APK
- Hash Argon2 (nunca texto plano como en el APK original)
- UUID como PK (no entero secuencial predecible)
- `ForeignKey` a Perfil con 4 roles: `ENCUESTADOR_CAMPO`, `COORDINADOR_DT`, `SUPERVISOR`, `ADMINISTRADOR`

**LogAcceso** — Auditoría inmutable
- Sin permisos `UPDATE`/`DELETE` desde la app
- Registra: usuario, acción, ip_origen, objeto_tipo, objeto_id, timestamp

**Victima** — Registro con PII cifrado
- `nombre_completo`, `apellidos`, `numero_documento`, `fecha_nacimiento` → `EncryptedCharField` (AES via pgcrypto)
- `numero_documento_hash` → SHA-256 para búsquedas sin descifrar

### Endpoints autenticación
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/login/` | Login → access + refresh token |
| POST | `/api/auth/refresh/` | Renovar access token |
| POST | `/api/auth/logout/` | Invalidar refresh (blacklist) |
| GET | `/api/auth/me/` | Perfil y permisos del usuario |
| POST | `/api/auth/cambiar-password/` | Cambio de contraseña |

---

## Entregables mobile

### Stack configurado
- Expo SDK 54 + React Native
- Expo Router (file-based routing)
- React Native Paper (Material Design 3)
- Zustand (`authStore`) con JWT en `expo-secure-store`
- Axios con interceptores JWT (refresh automático en 401)

### Pantallas
- `(auth)/login.tsx` — Login con validación
- `(main)/index.tsx` — Dashboard placeholder
- `(main)/_layout.tsx` — Bottom tabs

### Schema SQLite offline
- `instrumento_meta` — versión del instrumento descargado
- Sin campos PII almacenados localmente (corrige error crítico del APK)
- Motor de preguntas con skip logic base (`PREDEPENDE`/`RESHABILITA`)

---

## Seguridad implementada

| Error APK original | Corrección sprint 1 |
|-------------------|---------------------|
| `HTTP sin TLS` | `usesCleartextTraffic=false` en app |
| `Contraseñas TEXT plano` | Argon2 via Django |
| `Token sin expiración` | JWT: access 15 min, refresh 8 h rotativo |
| `allowBackup=true` | `allowBackup=false` en manifiesto |
| `PII en cliente` | Sin PII en SQLite local |
| `Credenciales hardcodeadas` | `python-decouple` + `.env` excluido del repo |

---

## Tests
- Autenticación JWT: login, refresh, logout, permisos por perfil
- LogAcceso: inmutabilidad (sin UPDATE/DELETE desde app)
- Cifrado PII: round-trip cifrado/descifrado

---

## Decisiones técnicas

**Por qué UUID como PK:** Evita enumeración de recursos por ID secuencial (ataque común en APIs).

**Por qué Argon2:** Resistente a ataques de GPU/ASIC. El APK original usaba `PASSWORD TEXT` — sin ningún hash.

**Por qué `expo-secure-store` para JWT:** Alternativa segura a `AsyncStorage` (texto plano en disco).
