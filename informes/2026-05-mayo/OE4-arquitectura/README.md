# OE4 — Diseño e implementación de soluciones tecnológicas

> **Obligación contractual:** *Realizar el diseño e implementación de las soluciones tecnológicas y aplicativos móviles que genere la Subdirección Red Nacional de Información para el procedimiento de Instrumentalización de la Información.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se consolidó la **arquitectura completa de 3 componentes** del sistema de caracterización de víctimas, todos comunicándose por HTTPS + JWT. El **backend Django REST Framework** quedó operativo con 8 apps (autenticación, víctimas, formulario, hogares, encuestas, paramétricas, IA y reportes) + 2 transversales (auditoría y sincronización), con autenticación JWT de refresh rotativo (access 15 min, refresh 8 h), Swagger autogenerado en `/api/schema/swagger-ui/`, throttle global y por endpoint, filtros server-side con django-filter, paginación cursor para listas volátiles (sesiones) y page-number para el resto. La **aplicación móvil React Native + Expo SDK 54** quedó implementada con Expo Router file-based, motor offline expo-sqlite con cola de sincronización, instrumentos pre-empaquetados como bundle JSON (no requiere descarga online), y bibliotecas auxiliares: react-native-paper para UI, expo-secure-store para tokens, expo-local-authentication para biometría, datetimepicker para calendario nativo y linear-gradient para fondos institucionales. El **panel web React + Vite + Tailwind + Zustand** quedó scaffolded con 5 páginas (Login, Dashboard, Hogares, Encuestas, Reportes), cliente axios con auto-refresh JWT en cola y estado global persistido en sessionStorage (nunca localStorage por seguridad). El despliegue local quedó orquestado por `docker-compose.yml` que levanta PostgreSQL con pgcrypto habilitado, Redis para cache y broker de Celery, backend Django con gunicorn y Nginx con configuración TLS lista. Los Docker Secrets quedaron preparados en `infra/secrets/` (excluidos del repo) para inyectar credenciales en producción.

## Evidencia que soporta esta actividad

- **Diagrama de arquitectura:** `informes/2026-05-mayo/OE4-arquitectura/README.md` (sección "Arquitectura general" con ascii diagram).
- **Orquestación contenedores:** `docker-compose.yml` (raíz del repositorio).
- **Configuración Nginx + TLS:** `infra/nginx/srni.conf`.
- **Settings backend:** `srni-backend/srni/settings/base.py`, `development.py`, `production.py`.
- **Inicializador PostgreSQL:** `infra/postgres/init.sql` (habilita pgcrypto).
- **Backend operativo:** carpeta `srni-backend/` con 8 apps Django.
- **App móvil operativa:** carpeta `srni-mobile/` con Expo SDK 54.
- **Panel web operativo:** carpeta `srni-frontend/` con Vite + React 18.
- **Documentación de arranque:** `docs/ARRANQUE-DEV.md` y scripts `arrancar-backend.ps1` + `arrancar-mobile.ps1`.
- **Copias locales en esta carpeta:** `docker-compose.yml`, `nginx.conf`, `base.py`.

---

## Actividades del cronograma

1. Solicitud de usuarios y permisos para servidores SRNI (FTP, Azure, BD, Ficha)
2. **Diseño de arquitectura completa:** backend + móvil + IA + nube + seguridad
3. **Implementación backend Django + PostgreSQL + Redis + Nginx** en desarrollo
4. **Implementación app móvil React Native con SQLite offline**
5. Despliegue en Azure: Docker + Nginx + SSL/TLS + Key Vault

## Avances en Mayo 2026

### Arquitectura general

Sistema de 3 componentes que se comunican por HTTPS + JWT:

```
   ┌──────────────────┐         ┌────────────────────┐
   │  App móvil       │ HTTPS   │  Backend Django    │
   │  Expo SDK 54     │◄───────►│  REST Framework    │
   │  SQLite local    │  JWT    │  PostgreSQL        │
   │  + Bundle JSON   │         │  Redis + Celery    │
   └──────────────────┘         └────────────────────┘
                                          ▲
                                          │ HTTPS + JWT
                                          │
                                 ┌────────┴───────────┐
                                 │  Panel Web React   │
                                 │  Vite + Tailwind   │
                                 │  Zustand           │
                                 └────────────────────┘
```

### Stack tecnológico

| Capa | Tecnología | Versión | Estado mayo |
|---|---|---|---|
| Backend | Django + DRF | 5.2 / 3.16 | ✅ Operativo en local |
| Auth | djangorestframework-simplejwt | 5.x | ✅ |
| BD | PostgreSQL + pgcrypto | 15 | ✅ Configurada |
| Cache / cola | Redis + Celery | 7 / 5.x | ✅ Configurada |
| Proxy / WAF | Nginx | 1.25 | ✅ Configuración lista |
| Contenedores | Docker + Compose | latest | ✅ docker-compose.yml |
| Mobile | React Native + Expo | SDK 54 | ✅ Operativo |
| Panel web | React + Vite + Tailwind | 18 / 5 / 3.4 | ✅ Operativo |
| Almacenamiento docs | MinIO (S3 compatible) | latest | 🟡 Configurado, sin uso aún |
| Cifrado PII | cryptography.fernet | AES-128-CBC | ✅ |
| Hash passwords | Argon2 (Django default) | — | ✅ |

### Componentes implementados en mayo

#### Backend (`srni-backend/`)
- 8 apps Django: autenticación, víctimas, formulario, hogares, encuestas, paramétricas, IA, reportes + auditoría + sincronización
- JWT con refresh rotativo (access 15 min, refresh 8 h)
- Swagger autogenerado en `/api/schema/swagger-ui/`
- Throttle global + per-endpoint
- Filtros server-side con `django-filter`
- Paginación cursor (sesiones) + page-number (resto)

#### Mobile (`srni-mobile/`)
- Expo Router file-based
- Motor offline expo-sqlite + cola de sincronización
- Instrumentos pre-empaquetados en bundle (no descarga)
- Bibliotecas: react-native-paper, expo-secure-store, expo-local-authentication, datetimepicker, linear-gradient

#### Panel web (`srni-frontend/`)
- Scaffold con Vite + TypeScript + Tailwind
- 5 páginas: Login, Dashboard, Hogares, Encuestas, Reportes
- Cliente axios con auto-refresh JWT en cola
- Estado global con Zustand (sessionStorage, nunca localStorage)

### Despliegue en desarrollo local

`docker-compose.yml` orquesta:
- `srni-postgres` con `pgcrypto` habilitado
- `srni-redis` para cache y Celery broker
- `srni-backend` Django gunicorn
- `srni-nginx` con configuración TLS lista
- `srni-mobile` (solo para entornos de demo)

`infra/secrets/` con Docker Secrets para producción (excluido del repo).

### Puertos asignados

| Servicio | Puerto |
|---|---|
| Backend Django | 8001 |
| Panel web Vite | 5173 |
| Expo Metro | 8082 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Nginx (prod) | 80 / 443 |

## Archivos relevantes

Copias locales:

- [`docker-compose.yml`](docker-compose.yml) — orquestación completa
- [`nginx.conf`](nginx.conf) — Nginx con TLS, CSP, headers de seguridad
- [`base.py`](base.py) — settings/base.py con configuración común

Referencias al repo:

- `docker-compose.yml` raíz — entorno completo
- `infra/nginx/` — configuración del proxy
- `infra/postgres/init.sql` — habilita pgcrypto
- `docs/arquitectura/` — diagramas y decisiones

## Pendientes (a complementar Javier)

- **Acceso a servidores UARIV:** sigue pendiente la solicitud formal a Oscar (FTP, Azure IGPD, Azure Móvil, Ficha)
- **Subscription Azure:** definir con UARIV
- **Key Vault:** configurar para secretos de producción
- **API key Gemini institucional:** ver OE9
