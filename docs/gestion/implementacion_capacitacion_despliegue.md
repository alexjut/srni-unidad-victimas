# SICAV Móvil / SRNI — Implementación, Capacitación y Despliegue

> **Documento técnico** · Sistema de Caracterización de Víctimas — Unidad para las Víctimas (UARIV)
> **Versión:** 1.0 · **Fecha:** 2026-07-15 · **Autor:** Documentación técnica SRNI
> **Estado:** Borrador para revisión de Javier (no commiteado)
> **Gestión PETI:** PRY-0662064

---

## Nota sobre nomenclatura (leer primero)

En el proyecto conviven dos nombres que designan cosas distintas, y conviene no confundirlos:

| Nombre | Qué es | Dónde está la marca |
|---|---|---|
| **SRNI** | Nombre del sistema completo (backend + panel web + móvil). Alude a la Subdirección Red Nacional de Información. | Panel admin (`django-unfold`): `SITE_BRAND = 'SRNI'`, `SITE_TITLE = 'SRNI · Unidad para las Víctimas'`. Repos: `srni-backend`, `srni-frontend`, `srni-mobile`. |
| **SICAV Móvil** | Nombre comercial **de la aplicación móvil Android** para el encuestador de campo. | `srni-mobile/src/config/marca.ts` → `APP_NAME = 'SICAV Móvil'`; `srni-mobile/app.json` → `name: "SICAV Móvil"`. |

Este documento usa **SICAV Móvil** para la app de campo y **SRNI** para el sistema en su conjunto.

> ✅ **RESUELTO (2026-09-01).** Identidad confirmada y en uso: `APP_NAME='SICAV Móvil'`, amarillo institucional `#ffcc03` y tipografía **Nunito Sans**. Vive en la app móvil (`marca.ts`) y en los entregables documentales.
> - El color `#ffcc03` existe **literalmente** en `marca.ts` (comentado "amarillo institucional"), pero el amarillo GOV.CO real que pinta el tema móvil es `#FFCD00` (`srni-mobile/src/theme/govTheme.ts`, `GOV.amarillo`, usado como `secondary`).
> - **Nunito Sans NO aparece en el código** de ninguno de los tres repos. El móvil usa la tipografía por defecto de `react-native-paper` (Material Design 3, sin `fontFamily` custom); el panel web referencia `'Work Sans, system-ui, sans-serif'` (`srni-frontend/src/main.tsx`). La afirmación "Nunito Sans" debe corregirse o eliminarse.

---

# 1. Implementación

## 1.1 Arquitectura general

SRNI es una arquitectura **cliente-servidor de mismo origen** con tres componentes desplegables y un modelo de operación **híbrido online/offline** para el trabajo de campo:

```
                    ┌─────────────────────────────────────────────┐
                    │  SERVIDOR 30.0.1.109 (VPN UARIV, Ubuntu)     │
   Encuestador      │  Stack Docker "caracterizacion" (cz_*)       │
   (Android)        │                                              │
  ┌───────────┐     │   cz_nginx:80  ──►  cz_backend:8001 (gunicorn)│
  │  SICAV    │─────┼─►  (SPA React    │        │                   │
  │  Móvil    │ HTTPS│    + /api +      │        ├─► cz_postgres:16   │
  │ (offline) │     │    /admin +      │        ├─► cz_redis:7       │
  └───────────┘     │    /movil/apk)   │        └─► cz_celery (worker)│
                    │                                              │
   Analista/QA      │   Publicado en host: 8090:80                 │
  ┌───────────┐     └─────────────────────────────────────────────┘
  │ Panel web │            ▲
  │  (React)  │────────────┘  FortiWeb 443 → :80 → NPM → cz_nginx:80
  └───────────┘               (dominio caracterizacion.unidadvictimas.gov.co)
```

**Principio de mismo origen:** en producción el panel web (SPA React compilada) y la API se sirven desde el **mismo host y puerto** a través de `cz_nginx`. El frontend usa rutas relativas (`/api`), por lo que **no hay CORS** entre panel y API en producción.

## 1.2 Backend — Django 5.2 + Django REST Framework

**Repo:** `srni-backend/` · **Proyecto Django:** `srni/` · **Apps propias:** `apps/`

### Stack y dependencias clave
Fuente: `srni-backend/requirements.txt` (objetivo declarado: compatibilidad Python 3.14; imagen Docker corre sobre Python 3.12).

| Paquete | Versión | Rol |
|---|---|---|
| Django | 5.2.15 (LTS) | Framework base |
| djangorestframework | 3.15.2 | API REST |
| djangorestframework-simplejwt | 5.4.0 | Autenticación JWT (con blacklist) |
| drf-spectacular | 0.28.0 | Documentación OpenAPI 3.0 / Swagger |
| django-cors-headers | 4.4.0 | CORS (solo relevante fuera de mismo origen) |
| django-filter | 24.3 | Filtros de querysets |
| django-unfold | 0.98.0 | Tema del panel admin (dark) |
| psycopg[binary] | 3.2.3 | Driver PostgreSQL (psycopg **v3**, no psycopg2) |
| cryptography | 44.0.2 | Cifrado PII (Fernet) |
| argon2-cffi | 23.1.0 | Hash de contraseñas (Argon2) |
| django-ratelimit | 4.1.0 | Rate limiting |
| redis / django-redis / celery | 5.2.1 / 5.4.0 / 5.4.0 | Cola y tareas asíncronas |
| boto3 / django-storages | 1.35.86 / 1.14.4 | Almacenamiento de objetos (MinIO/S3) |
| django-auditlog | 3.0.0 | Auditoría de cambios |
| google-generativeai | 0.8.3 | Proxy backend → Gemini (asistente de voz IA) |
| gunicorn / whitenoise | 23.0.0 / 6.8.2 | WSGI de producción / estáticos |

> Nota: `django-encrypted-model-fields` está **omitido/comentado** por incompatibilidad con Python 3.14; el cifrado PII se implementa a mano sobre `cryptography` (ver 1.2.3).

### Apps Django (INSTALLED_APPS)
Fuente: `srni-backend/srni/settings/base.py`. Composición: `UNFOLD_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS`.

**11 apps propias** (prefijo `apps.`):

| App | Propósito |
|---|---|
| `autenticacion` | Usuario custom (UUID, Argon2), `Perfil`/roles, JWT |
| `victimas` | Modelo `Victima` con PII cifrada, hechos victimizantes (Ley 1448) |
| `formulario` | Instrumentos, capítulos, preguntas, opciones, skip-logic |
| `hogares` | `Hogar` y `MiembroHogar` (unidad familiar, integrantes) |
| `encuestas` | `SesionEncuesta` y `RespuestaEncuesta` (captura) |
| `parametricas` | DIVIPOLA (deptos/municipios/veredas), tipos doc, territoriales |
| `sincronizacion` | Sincronización offline↔online (lógica de vistas, sin modelos propios) |
| `auditoria` | `LogAcceso`, trazabilidad |
| `reportes` | Reportería/tableros (sin modelos propios) |
| `ia` | `ConsentimientoIA`, `SesionIA` (asistente de voz Gemini) |
| `movil` | Endpoints específicos del cliente móvil (sin modelos propios) |

### Cifrado de PII
Fuente: `srni-backend/apps/victimas/fields.py`.

- **Mecanismo:** clase `EncryptedField(models.TextField)` que cifra con **Fernet** (AES-128-CBC + HMAC-SHA256). Cifra en `get_prep_value` (escritura a BD) y descifra en `from_db_value` (lectura); detecta tokens ya cifrados por el prefijo `gAAAAA`.
- **Llave:** `settings.FIELD_ENCRYPTION_KEY`, cargada con `python-decouple`. Acepta clave Fernet (44 chars) o 32 bytes en base64.
- **Búsqueda sin exponer PII:** función `sha256_hash` genera un hash SHA-256 indexado (p. ej. `numero_documento_hash`) que permite buscar por documento sin descifrar.
- **Campos cifrados:**
  - `Victima`: `numero_documento`, `primer_nombre`, `segundo_nombre`, `primer_apellido`, `segundo_apellido`, `fecha_nacimiento` (+ `numero_documento_hash` indexado).
  - `MiembroHogar`: `nombre_completo`, `numero_documento` (integrantes no registrados en el RNI).
- **Cumplimiento normativo citado en los docstrings:** Ley 1581/2012 (Habeas Data), CONPES 3995, Ley 1448/2011.

### Autenticación y autorización
Fuente: `base.py`, `production.py`, `development.py`, `apps/autenticacion/`.

- **Usuario custom** `AUTH_USER_MODEL = 'autenticacion.Usuario'`: PK UUID, `USERNAME_FIELD = codigo_usuario`, hash **Argon2** (mínimo 10 caracteres).
- **JWT (simplejwt):** access 15 min / refresh 8 h en base; producción sube refresh a 7 días. `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`, HS256, header `Bearer`.
- **Permiso por defecto:** `IsAuthenticated`.
- **Throttling:** login `5/min`, búsqueda RNI `30/h`, IA `20/h`, anónimo `20/h`, usuario `1000/h`.
- **Roles/perfiles** (`Perfil` con flags `puede_buscar_rni`, `puede_caracterizar`, `puede_ver_reportes`, `puede_administrar`): **ADMINISTRADOR, COORDINADOR, SUPERVISOR, ENCUESTADOR**.
  - Usuarios de demostración (`crear_usuarios_demo`): **Jorge — QA** y **Karen — Documental** están cargados como **ADMINISTRADOR** (admin total), además de ALEXJUT (admin), BRANDO (Coordinador/Líder Frontend), SUPERVISOR y ENC001–ENC005.

### Panel de administración (django-unfold)
Fuente: `base.py` (dict `UNFOLD`), `srni-backend/static/marca/`.

- `django-unfold` 0.98.0 confirmado, `THEME: 'dark'` (con `SHOW_THEME_SWITCHER`).
- Branding: `SITE_BRAND = 'SRNI'`, `SITE_TITLE/SITE_HEADER = 'SRNI · Unidad para las Víctimas'`, `SITE_SUBHEADER = 'Sistema de Caracterización (SRNI)'`.
- Banner de entorno dinámico (PRODUCCIÓN/rojo vs DESARROLLO/amarillo), dashboard custom (`srni.dashboard.dashboard_callback`), logos SVG institucionales en `static/marca/`.

> ⚠️ **PENDIENTE CONFIRMAR (branding admin).** En el backend **no existe** `APP_NAME='SICAV Móvil'`, ni la clave `COLORS` con `#ffcc03`, ni `FONTS`/Nunito. Ese branding (SICAV, #ffcc03) vive en la **app móvil**, no en el admin web.

### Base de datos y configuración
Fuente: `srni/settings/{base,production,development,servidor}.py`, `.env.example`.

- **Producción/servidor:** PostgreSQL 16 (`django.db.backends.postgresql`), `CONN_MAX_AGE=60`, `sslmode` configurable (`DB_SSL_MODE`, default `require`). Módulo de settings del servidor: `srni.settings.servidor`.
- **Desarrollo:** SQLite (`db.sqlite3`), caché LocMem, Celery en modo *eager*, CORS abierto, `DEBUG=True`.
- **Localización:** `es-co`, zona horaria `America/Bogota`.
- **Variables de entorno** (leídas con `python-decouple`, **no** `DATABASE_URL` — son variables separadas):

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Clave Django (obligatoria; si vacía → 502) |
| `DEBUG`, `ALLOWED_HOSTS` | Modo y hosts permitidos |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSL_MODE` | PostgreSQL |
| `FIELD_ENCRYPTION_KEY` | Llave Fernet de PII (AES-256, 32 bytes base64 url-safe) |
| `REDIS_URL`, `REDIS_PASSWORD` | Redis/Celery |
| `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET` | Almacenamiento de objetos |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos (fuera de mismo origen) |
| `GEMINI_API_KEY` | Proxy IA de voz (opcional) |

### Comandos de management (pipeline de datos)
Fuente: `apps/*/management/commands/`.

- **Instrumentos:** `cargar_perfil` (carga idempotente genérica: `--instrumento`, `--fixture`, `--reemplazar`, `--dry-run`; regenera skip-logic), `crear_instrumentos_base`, `cargar_capitulo_control`, y cargas específicas (`cargar_telefonico_v8`, `cargar_urbano_etnico_v1`, etc.). **`exportar_a_mobile`** exporta los 8 instrumentos activos a `srni-mobile/assets/instrumentos/` con `index.json` (base de la arquitectura offline).
- **Paramétricas:** `cargar_departamentos_municipios`, `cargar_tipos_documento`, `cargar_direcciones_territoriales`, `cargar_puntos_atencion`.
- **Usuarios/demo:** `crear_usuarios_demo`, `crear_usuario_prueba`.
- Los instrumentos se cargan **solo** vía `cargar_perfil` (no `loaddata` paralelo).

## 1.3 Frontend web — React 18 + Vite

**Repo:** `srni-frontend/` — *Panel web SRNI para analistas, QA, supervisión y administración.*

- **Stack:** React 18.3 + Vite 5 + TypeScript 5.4. Router `react-router-dom` 6; estado `zustand` 4; HTTP `axios` 1.7; UI `tailwindcss` 3.4 + `lucide-react` + `sonner`; formularios `react-hook-form` + `zod`; gráficas `recharts` + mapas `react-simple-maps` (`public/geo/colombia.json`); exportación `exceljs`. Tests con `vitest` + Testing Library.
- **Estructura (`src/`):** `api/` (un módulo por dominio: `client.ts`, `auth.ts`, `victimas.ts`, `hogares.ts`, `encuestas.ts`, `formulario.ts`, `supervision.ts`, `auditoria.ts`, `parametricas.ts`, `reportes.ts`, `usuarios.ts`), `pages/` (Login, Dashboard, Víctimas, Hogares, Encuestas, Instrumentos, Supervisión, Reportes, Auditoría, Paramétricas, Usuarios…), `components/` (MainLayout, Sidebar, ErrorBoundary, `ui/`), `stores/` (`authStore.ts` con zustand).
- **Conexión al backend** (`src/api/client.ts`): `baseURL = import.meta.env.VITE_API_URL ?? ''`, timeout 30 s. Interceptor añade `Authorization: Bearer` (tokens en `sessionStorage`); refresh automático contra `/api/auth/token/refresh/`; en fallo → logout + `/login`.
  - `.env.production`: `VITE_API_URL=` **vacío** → mismo origen (rutas relativas), sin CORS.
  - Dev: proxy Vite `/api → http://localhost:8001`, servidor dev en `:5173`.
- **Scripts:** `dev` (vite), `build` (`tsc && vite build`, con manualChunks vendor-react / vendor-charts / vendor-maps), `preview`, `lint`, `test`.

## 1.4 Móvil — SICAV Móvil (Expo / React Native, Android)

**Repo:** `srni-mobile/` — *App de campo del encuestador.*

- **Stack:** Expo SDK 54 (`expo ~54.0.33`), React Native 0.81.5, React 19.1, `expo-router` 6 (typed routes, `newArchEnabled`). HTTP `axios`; estado `zustand` 5; UI `react-native-paper` 5 (MD3). Persistencia local `expo-sqlite` + `expo-secure-store`; biometría `expo-local-authentication`; IA `@google/generative-ai`.
- **Identidad de app** (`app.json`): `name: "SICAV Móvil"`, `slug: "srni-mobile"`, `version: "1.0.0"`, `android.versionCode: 1`, `scheme: "srni"`, package `co.gov.unidadvictimas.srni`, EAS `projectId 2e3c7b13-…`.
- **Plataforma:** solo **Android** se compila (perfiles EAS `preview` = APK y `production` = app-bundle; no hay target iOS en `eas.json`). El `app.json` conserva un bloque `ios` configurado pero **aplazado** (no se construye).
- **Endurecimiento Android:** `allowBackup: false`, `usesCleartextTraffic: false`, permisos solo `USE_BIOMETRIC`/`USE_FINGERPRINT`.
- **Conexión al backend** (`src/api/client.ts`): `BASE_URL = process.env.EXPO_PUBLIC_API_URL`; en `preview`/`production` (eas.json) → `https://caracterizacion.unidadvictimas.gov.co`. Bearer desde `expo-secure-store`; refresh en 401; redacción de PII en logs.

### Arquitectura offline (clave del trabajo de campo)
- **Bundle de instrumentos empaquetado** (`src/services/instrumentos.ts`): los 8 JSON se incluyen en el build con `require` estático (`BUNDLED`). Índice en `assets/instrumentos/index.json`. Versiones actuales por perfil:

| Perfil | Archivo | Versión |
|---|---|---|
| TERRITORIAL | territorial_v8.json | v8 |
| ASISTENCIA | asistencia_v8.json | v8 |
| TELEFONICO | telefonico_v8.json | v8 |
| BUENAVENTURA | buenaventura_v7.json | v7 |
| SAN_ANDRES | san_andres_v7.json | v7 |
| RURAL_ETNICO | rural_etnico_v1.json | v1 |
| URBANO_ETNICO | urbano_etnico_v1.json | v1 |
| VICTIMAS_EXTERIOR | victimas_exterior_v1.json | v1 |

  - Estrategia **lazy per-perfil**: solo un perfil en memoria a la vez, indexado en `Map` para lectura O(1); al cambiar de perfil se libera el anterior (protege gama baja).
- **Precarga al login** (`src/services/precarga.ts`): con conexión, `ejecutarPrecarga()` descarga `GET /api/victimas/precarga/` y persiste padrón + jornada + paramétricas en SQLite. Es *best-effort*: si falla, el login no falla.
- **Búsqueda local del padrón** (`src/db/hashDocumento.ts`): indexa por hash del documento para búsqueda síncrona.

> ⚠️ **PENDIENTE CONFIRMAR / RIESGO (padrón "cifrado").** Hoy (Fase 0) el padrón local usa un **hash NO criptográfico y reversible** (FNV-1a + djb2, 64 bits, **sin sal**) solo para indexar, y opera con **datos MOCK**. El cifrado en reposo real (SHA-256 con sal por dispositivo en secure-store + SQLCipher) está marcado como **TODO PENDIENTE**. No debe documentarse como "padrón cifrado" hasta implementar Fase 1.

## 1.5 Requisitos de infraestructura

| Componente | Requisito |
|---|---|
| Servidor | Ubuntu (25.10 en el actual), 4 vCPU / 15 GB RAM, Docker + Docker Compose; acceso vía **VPN UARIV** + llave SSH |
| Backend runtime | Contenedor Python 3.12-slim, gunicorn 4 workers, `:8001` interno |
| Base de datos | PostgreSQL 16 (contenedor `cz_postgres`, sin puerto al host) |
| Cola/caché | Redis 7 (contenedor `cz_redis`, con `requirepass`) |
| Reverse proxy | nginx 1.25 (contenedor `cz_nginx`), publica `8090:80` |
| Borde | FortiWeb (WAF) 443 → NPM (Nginx Proxy Manager) → `cz_nginx` |
| Dispositivo de campo | Android 8+ (según manual de uso) |
| Build móvil | Cuenta EAS/Expo + `EXPO_TOKEN`; build en la nube de Expo (~10–15 min) |

> ✅ **RESUELTO (2026-09-01).** Ya **no** es MOCK: `VICTIMA_REPOSITORY=DJANGO` en producción, con el padrón real cargado (5.926.004 personas) y el universo del RUV (12.009.492). La escritura hacia Oracle por los procedures `GIC_*` tuvo su piloto verificado en producción el 28-jul-2026.
> **Actualización 2026-07-24:** por primera vez se validó, contra una **réplica local** (Docker con la estructura real de RNIENTREVISTA), la ruta de escritura de una caracterización vía los **procedures oficiales `GIC_*`** (Escalón 1, end-to-end, verificado por SELECT). La escritura contra el **Oracle real/producción sigue pendiente** de un entorno de **Pruebas de OTI** con geografía real.

---

# 2. Forma de capacitación

> ✅ **RESUELTO (2026-09-01).** El plan formal existe y está en ejecución: `entregables/2026-08-27-capacitacion/` — tres sesiones (1, 3 y 8 de septiembre), cronograma, temario, metodología, rosters nominales y **ocho anexos** (pre/post-test, banco de 32 preguntas por capítulo, tres casos de estudio, plantilla de documentación, revisión del manual, encuesta de calidad, piezas gráficas y verificación de dispositivos).

## 2.1 Materiales disponibles (verificados en el repo)

| Material | Ruta | Audiencia |
|---|---|---|
| **Manual de Uso SICAV Móvil v1.1** (2026-07-05) | `docs/publicacion/manual-de-uso-srni-mobile.md` | Encuestadores de campo |
| **Manual Funcional de la app móvil v1.0** (2026-07-03) | `docs/publicacion/manual-funcional-app-movil.md` | Equipo funcional / pruebas / QA |
| Manual Funcional (versión HTML publicada) | `infra/deploy/descargar/manual.html` (servido en `/descargar/manual.html`) | Descarga en línea |
| Política de privacidad | `docs/publicacion/politica-privacidad-srni-mobile.md` | Todos |
| **Manual oficial UARIV — Perfil Territorial y Étnicos** (11-MU) | `docs/perfiles/11-MU_ENTREVISTA-DE-CARACTERIZACION_PERFIL-TERRITORIAL-Y-ETNICOS_EP_V1.pdf` | Encuestadores territoriales |
| **Manual oficial UARIV — Perfil Asistencia** (14-MU) | `docs/perfiles/14-MU_ENTREVISTA-DE-CARACTERIZACION_PERFIL-ASISTENCIA_ENP-V1.pdf` | Encuestadores de asistencia |
| Matriz de permisos por rol | `docs/frontend/VALIDACION-PERMISOS.md` | Coordinación / QA |

El Manual de Uso ya cubre: requisitos (Android 8+), inicio de sesión con biometría, flujo de caracterización paso a paso, asistente de voz IA, hogares, operación offline, seguridad y solución de problemas. (El apartado "Soporte técnico" quedó como `[COMPLETAR — canal de soporte interno UARIV]`.)

## 2.2 Modalidad recomendada

- **Semipresencial / taller práctico.** La caracterización es una tarea de campo, por lo que la formación debe ser mayoritariamente **práctica sobre el dispositivo real**, no solo teórica.
- **Entorno de práctica:** usar el sistema apuntando a datos **MOCK** (padrón ficticio) para no exponer PII real durante el entrenamiento. Acceso de práctica vía APK interno (QR) y panel web en el servidor de la entidad.
- **Grupos pequeños** por perfil, para permitir acompañamiento 1:1 en el primer diligenciamiento completo.

## 2.3 Contenidos por perfil de usuario

### A. Encuestador / caracterizador territorial (rol ENCUESTADOR)
Duración sugerida: **medio día (4 h)** + práctica acompañada.
1. Contexto normativo y de confidencialidad (Ley 1448/2011, Habeas Data Ley 1581/2012). *(0.5 h)*
2. Instalación del APK (QR), inicio de sesión, biometría, cambio de contraseña. *(0.5 h)*
3. **Operación offline**: qué se precarga al login, cómo trabajar sin señal, cola de sincronización, cómo confirmar que los datos "subieron". *(1 h)*
4. Flujo completo de caracterización de un hogar: búsqueda en padrón, conformación del hogar, captura por capítulos, skip-logic, captura grupal, cierre de sesión. *(1.5 h)*
5. Asistente de voz IA (consentimiento previo del entrevistado) y solución de problemas frecuentes. *(0.5 h)*
- **Material:** Manual de Uso SICAV Móvil v1.1 + manual oficial UARIV del perfil correspondiente (11-MU Territorial/Étnicos o 14-MU Asistencia).

### B. Perfil QA (rol ADMINISTRADOR — caso Jorge)
Duración sugerida: **1 día (8 h)**.
1. Todo lo del encuestador (para poder reproducir defectos de campo). *(medio día)*
2. Manual **Funcional** completo: recorrido pantalla-por-pantalla, reglas de negocio, matriz offline, checklists de prueba y pendientes conocidos. *(2 h)*
3. Panel web: vistas de Supervisión, Encuestas, Sesiones, Auditoría; verificación de que lo capturado en móvil llega correctamente al backend. *(1 h)*
4. Gestión de instrumentos y versiones de bundle (v7/v8): cómo validar que un cambio de instrumento se refleja en la app. *(1 h)*
- **Material:** Manual Funcional + `docs/perfiles/` (diccionarios y flujogramas por instrumento) + `docs/frontend/VALIDACION-PERMISOS.md`.

### C. Perfil documental (rol ADMINISTRADOR — caso Karen)
Duración sugerida: **medio día (4 h)**.
1. Navegación del panel web y del admin (django-unfold, tema dark). *(1 h)*
2. Consulta de víctimas, hogares y sesiones; reportería y exportación a Excel. *(1.5 h)*
3. Paramétricas (DIVIPOLA, direcciones territoriales, puntos de atención) y su impacto en la caracterización. *(1 h)*
4. Manejo de PII y trazabilidad: qué campos son sensibles, cómo se registra el acceso (auditoría). *(0.5 h)*
- **Material:** Manual Funcional (secciones de panel) + política de privacidad.

### D. Administrador / Coordinador / Supervisor
- **Administrador:** gestión de usuarios y perfiles, carga de instrumentos (`cargar_perfil`), configuración, monitoreo de despliegue.
- **Coordinador/Supervisor:** vistas de supervisión y seguimiento de avance de jornadas; no requieren operación técnica del servidor.
- **Material:** este documento + `infra/deploy/README.md` (para el rol admin técnico).

## 2.4 Evaluación sugerida
- **Encuestadores:** ejercicio práctico obligatorio — caracterizar de principio a fin **un hogar MOCK completo** en modo offline y verificar su sincronización. Aprobado/No aprobado.
- **QA / Documental:** checklist de tareas cubiertas en el panel + un caso de reporte de defecto (QA) o de exportación/consulta (documental).
- **Registro:** dejar constancia de asistencia y de resultado por participante.

> ✅ **RESUELTO (2026-09-01).** **30 enlaces territoriales** en dos grupos (16 + 14) más el equipo de la Subdirección, en tres jornadas de 4 h (8:00 a.m.–12:00 m.) los días **1, 3 y 8 de septiembre de 2026**. Dictan Javier (APK), Brandon (panel) y Jorge (calidad). Rosters nominales completos en el plan.
>
> ⚠️ **Sigue abierto:** el listado nominal del equipo de la Subdirección para la Sesión 1.

---

# 3. Despliegue

## 3.1 Entornos

| Entorno | Backend | Base de datos | Frontend | Móvil (API) |
|---|---|---|---|---|
| **Desarrollo** | `runserver`, settings `development` | SQLite (`db.sqlite3`) | `vite dev` en `:5173`, proxy `/api → :8001` | perfil EAS `development` → `http://10.67.19.132:8001` |
| **Producción** | Docker `cz_backend` (gunicorn), settings `servidor` | PostgreSQL 16 (`cz_postgres`) | SPA compilada servida por `cz_nginx` | perfiles `preview`/`production` → `https://caracterizacion.unidadvictimas.gov.co` |

## 3.2 Servidor de producción

- **Host:** `30.0.1.109` (Ubuntu, 4 vCPU / 15 GB RAM). **Acceso solo por VPN de la entidad + llave SSH.**
- **Usuario de despliegue:** `admin_rni` (grupo `docker`). Carpeta: `/home/admin_rni/caracterizacion/`.
- **Infraestructura compartida (NO tocar):** el servidor ya corre `nginx-proxy-manager` (NPM, puertos 80/81/443, red `uariv-network`) y `uariv-auth-service` (`:8080`). Por eso el stack SRNI publica en **`:8090`**.
- **Estado de exposición actual:** el puerto 8090 no está expuesto al exterior; se prueba por **túnel SSH**:
  `ssh -i <llave> -L 8090:localhost:8090 admin_rni@30.0.1.109` y luego `http://localhost:8090`.

## 3.3 Stack Docker de producción (`cz_*`)

Fuente: `infra/deploy/docker-compose.caracterizacion.yml` (`name: caracterizacion`, red `caracterizacion_net`).

| Servicio | Imagen / build | Puerto | Rol |
|---|---|---|---|
| `cz_postgres` | postgres:16-alpine | interno | Base de datos |
| `cz_redis` | redis:7-alpine (requirepass) | interno | Caché / broker Celery |
| `cz_backend` | build de `srni-backend` → `srni-caracterizacion-backend:latest`; gunicorn `srni.wsgi` `:8001`, 4 workers; `DJANGO_SETTINGS_MODULE=srni.settings.servidor` | interno | API + admin |
| `cz_celery` | misma imagen; `celery -A srni worker -Q sync,reports` | interno | Tareas asíncronas |
| `cz_nginx` | nginx:1.25-alpine; sirve `srni-frontend/dist` | **8090:80** | Reverse proxy / SPA |

- Solo `cz_nginx` publica puerto al host. `cz_nginx` está también en la red externa `uariv-network` para que NPM lo alcance.
- **Dockerfile del backend** (`srni-backend/Dockerfile`): `FROM python:3.12-slim`, instala `build-essential`/`libpq-dev`/`curl`, `pip install -r requirements.txt`, `COPY . .`, `EXPOSE 8001`, CMD gunicorn `srni.wsgi:application --bind 0.0.0.0:8001 --workers 4 --timeout 120`. La imagen se **hornea** (código copiado dentro); el módulo de settings se inyecta por variable de entorno.

### Reverse proxy y borde
- `cz_nginx` (`infra/deploy/nginx.caracterizacion.conf`): sirve la SPA React en `/`, hace proxy a `cz_backend:8001` para `/api/` y `/admin/`, estáticos en `/static/`, descarga del APK en `/movil/app.apk` (MIME `application/vnd.android.package-archive`), y página de QR en `/descargar`. Mismo origen → sin CORS. `client_max_body_size 5M`.
- **Cadena de borde:** `FortiWeb (WAF, 443) → 30.0.1.109:80 → NPM → cz_nginx:80` (documentada en el compose).
- **Dominio `caracterizacion.unidadvictimas.gov.co`:** DNS interno (LISA.uariv.local) → A → 30.0.1.109; el server block ya está provisionado en NPM.

> ✅ **RESUELTO (2026-09-01).** El dominio institucional está operativo: **`caracterizacion.unidadvictimas.gov.co`**, publicado vía **FortiWeb (WAF) 443 → 30.0.1.109:80 → NPM → `cz_nginx`**. Sirve el panel y la descarga del APK. El acceso por `IP:8090` queda como respaldo dentro de la intranet. Ver `docs/arquitectura/arquitectura-produccion-2026-08-31.html`.

## 3.4 Variables de entorno de despliegue

Fuente: `infra/deploy/.env.caracterizacion.example` (valores reales generados por script; **no versionados**). El compose se ejecuta **siempre** con `docker compose --env-file .env` — si falta, `SECRET_KEY` queda vacío y el backend responde **502**.

| Variable | Nota |
|---|---|
| `DB_NAME` (=`srni_caracterizacion`), `DB_USER` (=`srni_app`), `DB_PASSWORD` | PostgreSQL |
| `SECRET_KEY` | Django (obligatoria) |
| `FIELD_ENCRYPTION_KEY` | Fernet PII (AES-256, 32 bytes base64 url-safe) |
| `ALLOWED_HOSTS` | Incluye `30.0.1.109`, `.unidadvictimas.gov.co`, `.ngrok.app` |
| `CORS_ALLOWED_ORIGINS` | Dominio de caracterización + IP:8090 |
| `REDIS_PASSWORD` | Redis |
| `GEMINI_API_KEY` | IA de voz (opcional) |

## 3.5 Procedimiento de despliegue del backend/panel

Fuente: `infra/deploy/scripts/`. Orquestador: **`deploy-all.sh`** (ejecuta 10 → 20 → 30 → 40 → 50).

1. **`10-generar-secrets.sh`** — genera `.env` con `openssl rand` (SECRET_KEY, credenciales DB/Redis, llave Fernet 32B). Idempotente, `chmod 600`.
2. **`20-build-frontend.sh`** — compila el panel web con `node:20-alpine` (`VITE_API_URL` vacío = rutas relativas) → `srni-frontend/dist`.
3. **`30-desplegar.sh`** — `docker compose build && up -d`, espera `pg_isready`, ejecuta `migrate` y `collectstatic`.
4. **`40-cargar-datos.sh`** — carga paramétricas (tipos doc, DIVIPOLA, direcciones territoriales, puntos de atención), `crear_instrumentos_base`, `cargar_perfil --instrumento <COD> --reemplazar` para los **8 perfiles**, `cargar_capitulo_control`, y crea el usuario de prueba **ENC001**.
5. **`50-verificar.sh`** — verifica contenedores, HTTP local 8090 (`/`, `/api/`, `/static/`), conteos en BD y `POST /api/auth/login/` con ENC001.

**Despliegue remoto desde la máquina del dev (con VPN):** `subir-y-desplegar.sh` valida SSH, sube el código con `git archive HEAD` por SSH a `~/caracterizacion`, corre `deploy-all.sh` y **reinicia `cz_nginx`**.

> **Operación crítica:** tras reconstruir `cz_backend` hay que **reiniciar `cz_nginx`** (re-resuelve la IP del backend); si no, nginx cachea la IP vieja y devuelve **502**.

## 3.6 Publicación del APK (cascada EAS)

Fuente: `infra/deploy/scripts/deploy-apk.sh` + `srni-mobile/eas.json`.

1. En la máquina del dev (con VPN y `EXPO_TOKEN` en `~/.eas-token`): `deploy-apk.sh` corre `eas-cli build --platform android --profile preview --non-interactive --wait --json` (~10–15 min en la nube de Expo).
2. Extrae la URL del `.apk`, lo descarga con `curl`, **respalda el anterior** y lo sube por `scp` a `admin_rni@30.0.1.109:/home/admin_rni/caracterizacion/infra/deploy/movil/app.apk`.
3. El **QR no cambia** (apunta siempre a `/movil/app.apk` y `/descargar/`), por lo que los encuestadores reinstalan con el mismo QR.
4. **Requisitos:** `EXPO_TOKEN`, llave SSH `~/.ssh/id_srni_servidor`, VPN activa.

### Versionado del bundle de instrumentos (checklist al subir v7→v8)
Al cambiar la versión de un instrumento hay que tocar **4 lugares** o el build EAS falla en "Bundle JavaScript":
1. El archivo JSON del instrumento en `srni-mobile/assets/instrumentos/`.
2. `assets/instrumentos/index.json` (versión, capítulos, preguntas).
3. El `require` `BUNDLED` en `src/services/instrumentos.ts`.
4. El instrumento cargado en el backend (`cargar_perfil --reemplazar`).

> El APK de **campo** (OTI) debe compilarse apuntando al dominio de la OTI (no a ngrok), cambiando `EXPO_PUBLIC_API_URL` en `srni-mobile/eas.json`.
> ⚠️ **PENDIENTE CONFIRMAR (cuenta EAS).** El brief menciona la cuenta Expo **alexjut**, pero el repo **no lo confirma**: `app.json` no tiene campo `owner` y "alexjut" solo aparece como cuenta GitHub de backup y como usuario de prueba. Verificar la cuenta EAS real con quien ejecuta `deploy-apk.sh`.

## 3.7 Rollback básico

| Escenario | Acción |
|---|---|
| **Backend/panel roto tras deploy** | La imagen anterior queda en el host; `docker compose up -d` con el commit previo (redeploy de la versión anterior), o `git checkout <commit-anterior>` + `deploy-all.sh`. Reiniciar `cz_nginx` después. |
| **Migración de BD problemática** | Restaurar desde respaldo de PostgreSQL (⚠️ **PENDIENTE CONFIRMAR** política/cron de backup de BD — no documentada en el repo). |
| **APK defectuoso** | `deploy-apk.sh` respalda el APK anterior antes de sobrescribir; restaurar el `.apk` de respaldo en `/movil/app.apk` (QR intacto). |
| **502 tras redeploy** | Verificar `.env` presente (`--env-file .env`) y `SECRET_KEY`; reiniciar `cz_nginx`. |

## 3.8 Verificación post-despliegue (smoke test)

- 5 contenedores `cz_*` en estado *Up*.
- `http://localhost:8090/` (panel), `/api/`, `/static/` responden **200** (vía túnel SSH).
- `POST /api/auth/login/` con **ENC001** devuelve tokens JWT.
- Conteos de paramétricas correctos (referencia documentada: 33 deptos, 1.102 municipios, 8 tipos de documento) e instrumentos cargados.
- APK descargable en `/movil/app.apk` y QR en `/descargar/`.

---

## Apéndice — Fuentes principales (rutas del repo)

- Backend: `srni-backend/requirements.txt`, `srni/settings/{base,production,development,servidor}.py`, `apps/victimas/fields.py`, `apps/*/models.py`, `apps/*/management/commands/`, `Dockerfile`, `.env.example`.
- Frontend: `srni-frontend/package.json`, `src/api/client.ts`, `src/pages/`, `.env.production`, `vite.config.ts`.
- Móvil: `srni-mobile/app.json`, `eas.json`, `src/config/marca.ts`, `src/theme/govTheme.ts`, `src/services/instrumentos.ts`, `src/services/precarga.ts`, `src/db/hashDocumento.ts`, `src/api/client.ts`, `assets/instrumentos/index.json`.
- Infra/deploy: `infra/deploy/docker-compose.caracterizacion.yml`, `nginx.caracterizacion.conf`, `.env.caracterizacion.example`, `scripts/{deploy-all,10-generar-secrets,20-build-frontend,30-desplegar,40-cargar-datos,50-verificar,subir-y-desplegar,deploy-apk}.sh`, `README.md`.
- Docs: `docs/publicacion/{manual-de-uso-srni-mobile,manual-funcional-app-movil,politica-privacidad-srni-mobile}.md`, `docs/perfiles/{11-MU,14-MU}*.pdf`, `docs/frontend/VALIDACION-PERMISOS.md`, `docs/arquitectura/ARQUITECTURA.md`, `docs/gestion/acta-constitucion-PRY-0662064.md`.

---

*Documento generado para revisión. No commiteado. Los apartados marcados con ⚠️ PENDIENTE CONFIRMAR requieren validación de Javier / Oscar antes de considerarse oficiales.*
