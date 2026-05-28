# OE4 — Diseño e implementación de soluciones tecnológicas

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
