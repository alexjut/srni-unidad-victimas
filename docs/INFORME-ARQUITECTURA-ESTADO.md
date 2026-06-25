# SRNI — Informe de Arquitectura y Estado del Proyecto

> Documento de contexto consolidado (generado 2026-06). Sirve como **brief inicial
> para compartir en claude.ai** u onboarding de nuevos integrantes. Autocontenido:
> no requiere leer el código para entender qué es, cómo está construido y en qué punto va.

---

## 1. Qué es el proyecto

**SRNI — Sistema de Registro y Núcleo de Información / Caracterización de Víctimas**
para la **Unidad para las Víctimas (UARIV, Colombia)**. Objetivo: **replicar y
modernizar** el APK Android viejo (`IgedEncuesta`, v4.1) de caracterización de hogares
víctimas, como una solución de tres frentes:

1. **API + panel web** (backend Django + frontend React) para gestión y consulta.
2. **APK móvil** (Expo/React Native) para encuestadores en campo, **100% offline**.
3. **Infraestructura** reproducible para desplegar en el servidor de la entidad.

El encuestador caracteriza hogares (vivienda, salud, educación, alimentación, retornos,
etc.) mediante **instrumentos** (cuestionarios versionados por tipo de población:
Territorial, Asistencia, Telefónico, Buenaventura, San Andrés, Rural/Urbano Étnico,
Víctimas Exterior).

**Gestión PETI:** PRY-0662064. **Equipo:** Javier (backend/BD/móvil/infra + Claude),
Brando (frontend web), Oscar (supervisor funcional UARIV).

---

## 2. Arquitectura general

```
┌─────────────────────┐     HTTPS/JWT      ┌──────────────────────────────┐
│  APK Encuestador     │ ◄────────────────► │  Backend Django (API DRF)     │
│  (Expo / RN)         │   sync cola offline │  + Panel admin (django-unfold)│
│  SQLite local + IA   │                     └───────────┬──────────────────┘
└─────────────────────┘                                 │
                                                          │ mismo origen
┌─────────────────────┐     HTTP             ┌───────────┴──────────────────┐
│  Panel Web (React)   │ ◄─────────────────► │  PostgreSQL · Redis · Celery  │
│  Vite + Tailwind     │                     │  MinIO (S3) · Nginx           │
└─────────────────────┘                     └──────────────────────────────┘
```

- **Mismo origen** web+API (puerto 8090) → sin CORS en producción.
- **Offline-first** en móvil: el APK trae los instrumentos pre-empaquetados y opera
  sin red desde el primer login; sincroniza por una **cola de operaciones** cuando hay red.
- **PII cifrada** en reposo en backend (Fernet/cryptography); el móvil hoy guarda PII en
  SQLite sin cifrar (pendiente SQLCipher — Fase 1).

---

## 3. Stack por componente (verificado)

### 3.1 Backend — `srni-backend/`
| Componente | Versión / Tech |
|---|---|
| Framework | **Django 5.2.15 (LTS)** + **DRF 3.15** |
| Auth | **SimpleJWT 5.4** (JWT access/refresh) |
| API docs | **drf-spectacular 0.28** (OpenAPI / Swagger / ReDoc) |
| Admin | **django-unfold 0.98** (tema oscuro; NO jazzmin) |
| BD | **PostgreSQL** (psycopg3 binary) |
| Async | **Celery 5.4** + **Redis 5.2** (django-redis) |
| Seguridad PII | **cryptography 44** (Fernet), **argon2-cffi** (hash passwords), **django-ratelimit** |
| Storage | **boto3 / django-storages** → MinIO (S3-compatible) |
| Config | python-decouple, settings por entorno (development / servidor / production) |
| Tests | pytest + pytest-django |

**Apps Django:** `auth/usuarios`, `victimas` (PII cifrada, repositorio **MOCK** —
Oracle real pendiente), `hogares`, `encuestas`, `formulario` (instrumentos, capítulos,
preguntas, opciones, skip-logic), `parametricas` (municipios/DT/tipos doc), `ia`
(mapeo de entrevista por IA), `auditoria`.

### 3.2 Frontend web — `srni-frontend/` (Brando)
| Componente | Versión |
|---|---|
| **React 18.3** + **Vite 5** + **TypeScript 5.4** |
| react-router-dom 6 · axios · **Tailwind 3.4** |

Panel SPA servido como estático por Nginx, mismo origen que la API.

### 3.3 Móvil — `srni-mobile/`
| Componente | Versión |
|---|---|
| **Expo SDK 54** + **React Native 0.81** |
| Navegación | **expo-router 6** |
| BD local | **expo-sqlite 16** (esquema versionado, v9) |
| Estado | **zustand 5** |
| UI | **react-native-paper 5** + tema GOV propio |
| Red | axios |
| IA | **@google/generative-ai** (Gemini — mapeo de entrevista hablada) |
| Seguridad | **expo-secure-store** (tokens) + **expo-local-authentication** (biometría opt-in) |

**Arquitectura offline (clave del móvil):**
- Instrumentos en **bundle JSON** (`assets/instrumentos/*.json`) leídos en memoria
  (`services/instrumentos.ts`) — generados desde el backend con `exportar_a_mobile`.
- **Cola de sincronización** (`cola_sincronizacion`) con orden de dependencias
  (REGISTRAR_VICTIMA → CREAR_HOGAR → AGREGAR_MIEMBRO → CREAR_SESION → RESPONDER_BULK →
  FINALIZAR_SESION), backoff exponencial, reconciliación de huérfanos al arrancar.
- **Padrón/jornada** precargados al login para buscar víctimas offline.
- **Skip-logic** offline (`services/skipLogic.ts`) espejo del backend.
- **Progreso** real por obligatorias visibles (`services/progreso.ts`).

### 3.4 Infraestructura — `infra/`
| Componente | Tech |
|---|---|
| Contenedores | Docker + Docker Compose (stack `cz_*`) |
| Proxy | Nginx 1.25 |
| Build APK | **EAS Build** (Expo cloud) → perfil `preview` (APK) / `production` (AAB) |
| Distribución APK | servida en `/movil/app.apk` + página `/descargar/` con QR estable |
| Servidor | UARIV `30.0.1.109` (Ubuntu, acceso por VPN + llave SSH), **compartido** |
| Acceso actual | IP + **puerto 8090 (HTTP)**; dominio+TLS vía NPM pendiente (OTI) |

---

## 4. Estado de avance

### ✅ Funcionando
- **Backend:** API completa (auth, víctimas, hogares, encuestas, formulario, paramétricas,
  IA, auditoría). **7 instrumentos** cargados (~1.300 preguntas). Desplegado en
  `30.0.1.109:8090`, login JWT OK, panel admin (unfold).
- **Móvil:** caracterización **100% offline** de punta a punta (registro víctima →
  conformar hogar → captura por capítulos con skip-logic → finalizar → sync). IA asistida
  (transcripción → mapeo). Biometría opt-in. **APK build #15 desplegado** (QR estable).
- **Infra:** despliegue reproducible (`deploy-all.sh`), cascada de APK automatizada
  (`deploy-apk.sh`: EAS → descarga → scp al servidor).

### 🔧 Trabajo reciente (oleada 3 — auditoría APK, 2026-06)
8 correcciones aplicadas y desplegadas: progreso real con skip-logic (#8/#18), hogar online
capturable offline (#4/#38), flujo IA conserva contexto (#15), hub degrada offline (#16),
memo + badge de numeración (#23/#34/#27), reconciliación de cola offline (#14), **biometría
opt-in** (#22). 57 tests verdes, tsc limpio.

### ⏳ Pendiente
- **Ajustes al instrumento Territorial V7** (en curso — script de transformación listo, sin ejecutar).
- **Fase 1 (datos reales):** integración **Oracle** (hoy repositorio MOCK), **SQLCipher**
  (cifrado en reposo móvil), **hash SHA-256 con sal** del padrón alineado al backend.
- **OTI:** abrir puerto 8090 / publicar con dominio + TLS.
- **iOS:** aplazado (solo Android por ahora).

---

## 5. Modelo de datos del instrumento (cómo se define un cuestionario)

```
models.py (Instrumento · Capitulo · Pregunta · OpcionRespuesta · ReglaSkipLogic)
   │  seed
   ▼
fixtures/perfil_<codigo>_v*.json   ──(manage.py cargar_perfil)──►  PostgreSQL
   │
   └──(manage.py exportar_a_mobile)──►  srni-mobile/assets/instrumentos/<codigo>_v*.json
                                          (bundle que el APK empaqueta y lee offline)
```

- **Pregunta:** `codigo_externo` (único), `no_pregunta` (etiqueta C7…), `tipo`
  (BOOLEAN/LISTA/NUMERICO/TEXTO/TEXTO_LARGO/LISTA_MULTIPLE/COMBO_DINAMICO), `nivel`
  (HOGAR/PERSONA), `obligatoria`, `orden`, `opciones`.
- **Sub-campos condicionales** ("Sí abre un input"): se modelan con **reglas
  `HABILITAR`** (input oculto que aparece cuando una pregunta origen toma cierto valor).
  El motor `calcularVisibles` ya lo soporta en backend y móvil.
- **Progreso:** `obligatorias_respondidas / obligatorias_VISIBLES` (evaluando skip-logic),
  acotado 0–100% (HOGAR 1× + PERSONA × nº miembros).

---

## 6. Convenciones del proyecto
- Ramas: solo `main`, `frontend`, `develop` (sin feature/*). Todo a **main** con prefijos `feat()/fix()`.
- **Doble remote:** cada push va a **GitHub (origin)** y **Azure DevOps (azure)** → `git push all <rama>`.
- Estructura: `.md` en `docs/`, raíz limpia, secretos fuera de git.
- Víctimas: repositorio **MOCK** (datos ficticios) hasta integrar Oracle (trámite aparte).

---

## 7. Cómo usar este documento en claude.ai
Súbelo como contexto inicial de un proyecto. Da el panorama completo (qué, cómo, estado,
stack) sin exponer secretos. Para profundizar: `docs/arquitectura/ARQUITECTURA.md`,
`infra/deploy/README.md` (despliegue), y `docs/` (bitácoras por sprint).
