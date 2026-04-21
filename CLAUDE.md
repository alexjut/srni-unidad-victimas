# CLAUDE.md — Sistema de Caracterización de Víctimas SRNI

## Identidad del proyecto

| Campo | Valor |
|-------|-------|
| Proyecto | Sistema de Caracterización de Víctimas — Unidad para las Víctimas (SRNI) |
| Contrato | 2226-2026 |
| Contratista | Javier Alexander Aguilar Castro |
| C.C. | 1.030.547.250 |
| Email | ingaguilarsistemas@gmail.com |
| Supervisor | Oscar Andrés Manosalva García (SRNI) |
| Repositorio local | D:/desarrollo/unidad-victima |
| Repo oficial (Azure DevOps) | https://tfsunidad.visualstudio.com/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED-MOVIL/_git/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED%20MOVIL%202026-04 |
| Repo backup (GitHub) | https://github.com/alexjut/srni-unidad-victimas |

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | Django + Django REST Framework | 5.x / 3.15.x |
| Autenticación | djangorestframework-simplejwt | 5.x |
| Mobile | React Native + Expo | SDK 54 |
| Base de datos | PostgreSQL + pgcrypto | 15 |
| Caché / Cola | Redis + Celery | 7 / 5.x |
| Proxy / WAF | Nginx | 1.25 |
| Contenedores | Docker + Docker Compose | latest stable |
| Almacenamiento docs | MinIO (compatible S3) | latest |
| Cifrado campos PII | cryptography.fernet (custom EncryptedField) | AES-128-CBC |
| Hash contraseñas | Argon2 (Django default) | — |

### Puertos de desarrollo

| Servicio | Puerto |
|---------|--------|
| Expo Dev Server | 8081 |
| Backend Django | 8001 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Nginx (prod) | 80 / 443 |

---

## Estado actual del desarrollo — Sprints completados

| Sprint | Rama | Estado | Contenido principal |
|--------|------|--------|-------------------|
| Sprint 1 | `main` (base) | ✅ Completo | Backend Django inicial + scaffold mobile |
| Sprint 2 | `feature/sprint2-parametricas-formulario` | ✅ Completo | Paramétricas (geo, municipios, veredas), motor formulario 54 módulos, victimas con PII cifrado |
| Sprint 3 | `feature/sprint3-hogares-encuestas-mobile` | ✅ Completo | Hogares, miembros, sesiones de encuesta, pantallas móviles |
| Sprint 4 | `feature/sprint4-motor-offline` | ✅ Completo | Motor offline expo-sqlite, cola de sincronización, skip logic |
| Sprint 5 | `feature/sprint5-ia-gemini` | ✅ Completo | Integración IA Gemini, asistente de voz, UI GOV.CO institucional |

### Rama activa de trabajo
- `feature/sprint5-ia-gemini` — rama de desarrollo activa para Sprint 5 y siguientes
- `develop` — integra Sprints 1-5 completos
- `main` — producción, contiene todo el historial (18 commits, 188 archivos)

### Git remotes configurados
| Remote | URL | Uso |
|--------|-----|-----|
| `origin` | `github.com/alexjut/srni-unidad-victimas` | Backup personal privado |
| `azure` | `tfsunidad.visualstudio.com/.../RNI - VIVANTO - ENCUESTA IGED MOVIL 2026-04` | **Repo oficial UARIV** |

> **Regla de push:** `origin` = backup (push libre). `azure` = repo oficial (requiere PR o autorización del supervisor).

---

## Fases del proyecto

### Fase 1 — Backend + App Móvil (Sprints 1-5 — COMPLETADA)
- ✅ Backend Django REST Framework completo (autenticación, formulario, hogares, encuestas, victimas, paramétricas, IA)
- ✅ App móvil React Native + Expo SDK 54 con UI GOV.CO
- ✅ Motor de formularios dinámico (54 módulos, skip logic PREDEPENDE/RESHABILITA/RESFINALIZA)
- ✅ Autenticación JWT con refresh tokens (access 15 min, refresh 8 h)
- ✅ Módulo de búsqueda en el RNI (server-side only)
- ✅ Motor offline con expo-sqlite y cola de sincronización automática
- ✅ Integración IA Gemini con consentimiento y asistente de voz
- ✅ Docker Compose para desarrollo y producción

### Fase 2 — Próximos sprints
- Reportes de producción por encuestador
- Panel de supervisión (web Angular o Django Admin extendido)
- Sincronización masiva optimizada
- Pruebas de carga y hardening de seguridad para producción

---

## Idioma y estilo de respuesta

- **Idioma:** Siempre responder en **español**
- **Estilo:** Dar un **plan detallado por fases** antes de ejecutar cualquier tarea no trivial
- **Subagentes:** Usar subagentes paralelos cuando las tareas sean independientes entre sí
- **Confirmación:** En operaciones destructivas o irreversibles, confirmar antes de ejecutar
- **Bash:** El desarrollador ha aprobado ejecución automática de comandos bash sin pedir confirmación

---

## Errores críticos del APK original — NUNCA repetir

Estos errores fueron identificados en el análisis del APK `co.com.rni.encuestadormovil` v4.1:

| Error | Descripción | Corrección obligatoria |
|-------|-------------|----------------------|
| HTTP sin TLS | `usesCleartextTraffic=true`, todos los endpoints HTTP | HTTPS obligatorio en todos los endpoints |
| PII en cliente | 785 MB de datos de 9.4M víctimas sin cifrar en el APK | Datos solo en servidor, API paginada |
| FTP sin cifrado | Sincronización via FTP plano a `ftp.unidadvictimas.gov.co` y **`ftp.isegoria.co` (tercero)** | HTTPS/SFTP solo a servidores propios |
| Contraseñas TEXT plano | Campo `PASSWORD TEXT` en SQLite sin hash | Argon2 (Django default) |
| allowBackup=true | ADB puede extraer toda la BD sin root | No aplica en web; en móvil: `allowBackup=false` |
| SQLite sin cifrar | BD local sin SQLCipher | PostgreSQL + pgcrypto + volumen LUKS |
| Token sin expiración | `TOKENUSUARIO` string sin TTL | JWT: access 15 min, refresh 8 h rotativo |
| Permisos excesivos | READ_CALENDAR, KILL_BACKGROUND_PROCESSES sin justificación | Principio de mínimo privilegio |
| Credenciales hardcodeadas | URL de servidores embebidas en el DEX | `python-decouple` + variables de entorno |
| ORM deprecado | SugarORM (sin mantenimiento desde 2017) | Django ORM con migraciones versionadas |

---

## Estándares de seguridad obligatorios

### Backend
- `HTTPS` en todos los endpoints — `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 31536000` con subdomains y preload
- `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`
- `X_FRAME_OPTIONS = 'DENY'`
- Contraseñas con **Argon2** (nunca MD5, SHA1, texto plano)
- Campos PII cifrados con **EncryptedCharField** (AES-256 via pgcrypto)
- Búsqueda sobre PII cifrada via **índice SHA-256** del campo
- **LogAcceso inmutable**: sin permisos UPDATE/DELETE sobre esa tabla desde la app
- Rate limiting: 5 intentos login / 15 min por IP; 100 búsquedas RNI / hora por usuario
- **Nunca credenciales hardcodeadas** — usar `python-decouple` + `.env` (excluido del repo)
- **Docker Secrets** para contraseñas de servicios en producción

### Frontend Angular
- Tokens JWT en **`sessionStorage`** (NUNCA en `localStorage`)
- `sessionStorage.clear()` al hacer logout — limpia tokens Y datos cacheados
- Interceptor HTTP que añade `Authorization: Bearer` en cada request
- Refresh automático de token al recibir 401
- **Nunca cachear datos del RNI** en IndexedDB o localStorage
- Instrumento (módulos/preguntas) puede cachearse en memoria, no en disco

### Base de datos
- PostgreSQL con extensión `pgcrypto` habilitada
- Campos PII (nombre, documento, fecha nacimiento, apellidos) cifrados en reposo
- `numero_documento_hash` (SHA-256) como campo adicional para búsquedas eficientes
- Volumen de PostgreSQL sobre almacenamiento cifrado (LUKS en producción)
- Backups cifrados con `pg_dump` + GPG

---

## Cumplimiento normativo

| Norma | Descripción |
|-------|------------|
| **Ley 1581 de 2012** | Protección de datos personales — Colombia |
| **CONPES 3995** | Política Nacional de Confianza y Seguridad Digital |
| **Resolución MINTIC 1519** | Lineamientos para publicación de datos abiertos (aplica en negativo: datos de víctimas NO son datos abiertos) |
| **Decreto 1377 de 2013** | Reglamentario Ley 1581 |

Principios que deben reflejarse en el código:
- **Finalidad:** Solo para caracterización de víctimas, no otro uso
- **Minimización:** El frontend recibe solo los campos necesarios para la tarea
- **Seguridad:** Cifrado en reposo y en tránsito
- **Auditoría:** Trazabilidad de quién accedió a qué dato y cuándo
- **Derechos ARCO:** API para acceso, rectificación, cancelación, oposición

---

## Estructura del proyecto

```
unidad-victima/
├── CLAUDE.md                     ← Este archivo
├── ANALISIS_APK.md               ← Hallazgos del APK original
├── ARQUITECTURA.md               ← Diseño de la solución
├── MODELOS.md                    ← Esquema de base de datos
├── docker-compose.yml            ← Orquestación de servicios
├── .gitignore
│
├── srni-backend/                 ← Django REST Framework
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example              ← Plantilla (sin valores reales)
│   ├── srni/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── apps/
│   │   ├── autenticacion/        ← JWT, roles, perfiles (comando crear_usuario_prueba)
│   │   ├── victimas/             ← RNI — búsqueda y detalle (PII cifrado + hash SHA-256)
│   │   ├── formulario/           ← Motor dinámico 54 módulos + skip logic
│   │   ├── hogares/              ← Hogares y miembros
│   │   ├── encuestas/            ← Sesiones y respuestas
│   │   ├── parametricas/         ← Geo, comunidades étnicas (comandos carga municipios/documentos)
│   │   ├── ia/                   ← Proxy Gemini, ConsentimientoIA, logs de uso ← Sprint 5
│   │   ├── sincronizacion/       ← Import/export seguro
│   │   ├── auditoria/            ← LogAcceso inmutable
│   │   └── reportes/             ← Producción por encuestador
│   └── tests/
│
├── srni-mobile/                  ← React Native + Expo SDK 54
│   ├── app/                      ← Expo Router (file-based routing)
│   │   ├── _layout.tsx           ← Root layout + PaperProvider + auth guard
│   │   ├── index.tsx             ← Entry point con Redirect
│   │   ├── (auth)/
│   │   │   ├── _layout.tsx
│   │   │   └── login.tsx
│   │   └── (main)/
│   │       ├── _layout.tsx       ← Bottom tabs (estilo GOV.CO)
│   │       ├── index.tsx         ← Dashboard
│   │       ├── busqueda.tsx      ← Búsqueda RNI (server-side only)
│   │       ├── hogares/
│   │       │   ├── index.tsx     ← Lista hogares
│   │       │   ├── nuevo.tsx     ← Crear hogar
│   │       │   └── [hogarId].tsx ← Detalle hogar + miembros
│   │       ├── encuestas/
│   │       │   ├── index.tsx     ← Lista sesiones
│   │       │   └── [sesionId].tsx← Detalle sesión
│   │       └── formulario/
│   │           ├── index.tsx     ← Lista de 54 temas
│   │           ├── [temaId].tsx  ← Motor de preguntas + skip logic
│   │           └── consentimiento-ia.tsx ← Consentimiento IA Gemini
│   └── src/
│       ├── api/                  ← axios client + interceptores JWT (auth, hogares, encuestas, ia)
│       ├── stores/               ← Zustand (authStore, iaStore, syncStore)
│       ├── db/                   ← expo-sqlite: schema, borradoresDao, colaDao, hogaresOfflineDao, instrumentoDao
│       ├── services/             ← skipLogic.ts, sincronizacion.ts + tests
│       ├── components/           ← GovButton, GovCard, GovHeader, SugerenciaIA, AudioRecorder, EmptyState...
│       ├── theme/                ← govTheme.ts (paleta GOV.CO institucional)
│       └── types/                ← index.ts (tipos compartidos)
│
└── infra/
    ├── nginx/                    ← Configuración proxy + TLS
    ├── postgres/                 ← init.sql (pgcrypto)
    └── secrets/                  ← Docker Secrets (excluido del repo)
```

---

## Contexto técnico del sistema original (APK analizado)

- **Package:** `co.com.rni.encuestadormovil` v4.1
- **BD principal:** `dbencuestadormovil.db` — 785 MB, SQLite plano, ~9.4M víctimas
- **BD instrumento:** `vivanto.db` — 3.2 MB, 37 tablas, formulario dinámico
- **Paramétricas:** 32,377 veredas (CSV DANE), municipios, departamentos
- **Módulos:** 54 temas (`EMCTEMAS`), ~1416 preguntas (`EMCPREGUNTASINSTRUMENTO`)
- **Lógica condicional:** `PREDEPENDE`, `RESHABILITA`, `RESFINALIZA` — replicar fielmente
- **Tipos de campo:** TEXTO, NUMERICO, FECHA, LISTA, LISTA_MULTIPLE, RADIO, BOOLEAN, TEXTO_LARGO, COMBO_DINAMICO
- **Endpoint auth original:** `http://herramientasrni1.unidadvictimas.gov.co/LoginRest/Autentica.svc/` (WCF SOAP — reemplazar completamente)
- **Servidor FTP a eliminar:** `ftp.isegoria.co` (empresa de desarrollo, no debe tocar datos de víctimas)
