# CLAUDE.md — Sistema de Caracterización de Víctimas SRNI

## Identidad del proyecto

| Campo | Valor |
|-------|-------|
| Proyecto | Sistema de Caracterización de Víctimas — Unidad para las Víctimas (SRNI) |
| Desarrollador | Javier Alexander Aguilar Castro |
| C.C. | 1.030.547.250 |
| Email | ingaguilarsistemas@gmail.com |
| Repositorio | D:/desarrollo/unidad-victima |

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

## Fases del proyecto

### Fase 1 — Backend + App Móvil (~2 meses)
- Backend Django REST Framework completo
- App móvil React Native + Expo (Android primero)
- Motor de formularios dinámico (54 módulos, ~1416 preguntas)
- Autenticación JWT con refresh tokens
- Módulo de búsqueda en el RNI (servidor, nunca en cliente)
- Roles y permisos por perfil de encuestador
- Auditoría de accesos y cambios (LogAcceso inmutable)
- Docker Compose para desarrollo y producción

### Fase 2 — Aplicación Móvil (~4 meses)
- Angular + Capacitor o React Native
- PWA offline-first con sincronización
- Sin datos PII almacenados localmente
- Sin APK con datos embebidos (error crítico del sistema anterior)

---

## Idioma y estilo de respuesta

- **Idioma:** Siempre responder en **español**
- **Estilo:** Dar un **plan detallado por fases** antes de ejecutar cualquier tarea no trivial
- **Subagentes:** Usar subagentes paralelos cuando las tareas sean independientes entre sí
- **Confirmación:** En operaciones destructivas o irreversibles, confirmar antes de ejecutar

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

## Diseño y UX — decisiones tomadas (Sprint 7)

### Login
- Fondo con `LinearGradient` azul oscuro (`#00234E → #003A80 → #1565C0`) + franja GOV.CO amarilla
- Tiles decorativos de regiones colombianas (Pacífico, Caribe, Andes, Amazonia, Orinoquía, Insular)
- Botón de **biometría** (huella/Face ID) — círculo azul prominente estilo banca moderna
- Auto-habilitación biométrica en primer login si el dispositivo la soporta (`expo-local-authentication`)
- Tokens guardados en `expo-secure-store` (nunca en localStorage)

### Pantalla de Entrevista (busqueda.tsx)
- Primera pantalla visible tras el login (`initialRouteName="busqueda"`)
- Imagen auténtica de comunidad indígena Emberá — fuente: unidadvictimas.gov.co
- Gradiente oscuro sobre la imagen para legibilidad del formulario
- Formulario como **tarjeta flotante** sobre la imagen (estilo card elevada)
- Selector de tipo de documento: **dropdown profesional** con Modal bottom-sheet
- Selección de instrumento de caracterización **inline** (no pantalla separada)
- Flujo: buscar → instrumento → conformar hogar → crear sesión → encuesta

### Paquetes adicionales instalados (Expo SDK 54 compatible)
- `expo-local-authentication` — biometría nativa Android/iOS
- `expo-linear-gradient` — gradientes de fondo

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
│   │   ├── autenticacion/        ← JWT, roles, perfiles
│   │   ├── victimas/             ← RNI — búsqueda y detalle
│   │   ├── formulario/           ← Motor dinámico — 7 perfiles, 85 caps, 1319 preguntas
│   │   │   ├── fixtures/
│   │   │   │   ├── opciones_compartidas.json  ← Catálogo 40 listas UARIV
│   │   │   │   ├── perfil_asistencia_v8.json  ← ASISTENCIA V8 completo
│   │   │   │   └── perfil_territorial_v7.json ← TERRITORIAL V7 (Sprint 7)
│   │   │   └── management/commands/
│   │   │       └── cargar_perfil.py           ← Loader genérico (--perfil, $ref, --dry-run)
│   │   ├── hogares/              ← Hogares y miembros
│   │   ├── encuestas/            ← Sesiones y respuestas
│   │   ├── parametricas/         ← Geo, comunidades étnicas
│   │   ├── ia/                   ← Proxy Gemini — asistente + batch
│   │   ├── sincronizacion/       ← Import/export seguro
│   │   ├── auditoria/            ← LogAcceso inmutable
│   │   └── reportes/             ← Producción por encuestador
│   └── tests/
│
├── srni-mobile/                  ← React Native + Expo SDK 54
│   ├── app/                      ← Expo Router (file-based routing)
│   │   ├── _layout.tsx           ← Root layout + PaperProvider + auth guard
│   │   ├── (auth)/
│   │   │   └── login.tsx         ← Gradiente azul + biometría (huella/Face ID) + regiones decorativas
│   │   └── (main)/
│   │       ├── _layout.tsx       ← Bottom tabs — initialRouteName="busqueda"
│   │       ├── index.tsx         ← Dashboard (tab Inicio)
│   │       ├── busqueda.tsx      ← ENTREVISTA DE CARACTERIZACIÓN — imagen indígena fondo + instrumento inline
│   │       ├── caracterizar/
│   │       │   └── index.tsx     ← Flujo: instrumento → hogar → crear sesión
│   │       ├── formulario/
│   │       │   ├── index.tsx     ← Lista de capítulos del instrumento
│   │       │   ├── [temaId].tsx  ← Motor de preguntas + skip logic offline
│   │       │   ├── consentimiento-ia.tsx
│   │       │   ├── grabacion-entrevista.tsx  ← modo Gemini (batch)
│   │       │   └── revision-ia.tsx           ← revisión batch IA
│   │       └── encuestas/
│   │           ├── index.tsx     ← Lista de sesiones
│   │           └── [sesionId].tsx← Detalle sesión + nav al formulario
│   └── src/
│       ├── api/                  ← axios client + interceptores JWT
│       ├── stores/               ← Zustand (authStore, syncStore, iaStore, caracterizacionStore)
│       ├── db/                   ← expo-sqlite schema V2 (UUID PKs)
│       │   ├── schema.ts         ← Migration V2: tablas con UUID
│       │   ├── instrumentoDao.ts ← Acceso a capítulos/preguntas/opciones
│       │   ├── borradoresDao.ts  ← Sesiones y respuestas offline
│       │   └── colaDao.ts        ← Cola de sincronización
│       ├── services/
│       │   ├── sincronizacion.ts ← Cola offline → servidor
│       │   └── skipLogic.ts      ← Motor de reglas HABILITAR/DESHABILITAR
│       └── components/           ← Componentes compartidos GOV.CO
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
