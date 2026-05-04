# Base de Datos — SRNI

**Última actualización:** 2026-05-04

---

## Documentos

| Archivo | Descripción |
|---------|-------------|
| [MODELOS.md](MODELOS.md) | Modelos Django — esquema conceptual y relaciones |
| [backend-postgresql.md](backend-postgresql.md) | BD PostgreSQL actual — sentencias CREATE TABLE completas |
| [apk-original.md](apk-original.md) | BD SQLite del APK v4.1 — estructura original con sus fallas |
| [mobile-sqlite.md](mobile-sqlite.md) | BD SQLite offline de la app móvil — schema y migraciones |

---

## Comparativa rápida

| Aspecto | APK v4.1 (original) | SRNI nuevo |
|---------|---------------------|------------|
| Motor | SQLite (sin cifrar) | PostgreSQL 16 + pgcrypto |
| Ubicación | Dispositivo del encuestador | Servidor (nunca en cliente) |
| PII cifrado | ❌ Texto plano | ✅ AES-256 (EncryptedField) |
| Contraseñas | ❌ TEXT plano | ✅ Argon2 |
| Backup | ❌ ADB sin root | ✅ `allowBackup=false` |
| Búsqueda PII | Directo sobre texto | Hash SHA-256 (sin descifrar) |
| Auditoría | ❌ Sin registro | ✅ LogAcceso inmutable |
| Volumen datos víctimas en cliente | 785 MB | 0 bytes |
| Tablas | 37 (vivanto.db) + 11 shards (personas) | 22 tablas normalizadas |

---

## Extensiones PostgreSQL requeridas

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- cifrado de campos PII
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- generación UUID v4
```
