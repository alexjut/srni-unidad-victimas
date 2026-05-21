# Informe de Avance — Sistema de Caracterización de Víctimas SRNI
## Contrato 2226-2026 | Unidad para las Víctimas — UARIV

| Campo | Valor |
|-------|-------|
| **Proyecto** | Sistema de Registro Nacional de Información (SRNI) |
| **Contrato** | 2226-2026 |
| **Entidad** | Unidad para las Víctimas (UARIV) |
| **Desarrollador** | Javier Alexander Aguilar Castro — C.C. 1.030.547.250 |
| **Correo** | ingaguilarsistemas@gmail.com |
| **Período reportado** | 2026-04-13 al 2026-04-28 |
| **Fecha del informe** | 2026-05-04 |
| **Estado general** | Sprint 6 completado — 6 sprints de desarrollo entregados |

---

## 1. Resumen Ejecutivo

Se ha desarrollado el **Sistema de Caracterización de Víctimas SRNI** como reemplazo seguro del APK `co.com.rni.encuestadormovil` v4.1, que presentaba vulnerabilidades críticas de seguridad documentadas en el análisis técnico previo (ver `ANALISIS_APK.md`).

El sistema entregado comprende:

- **Backend Django REST Framework** completo con autenticación JWT, motor de formularios dinámico, manejo de PII cifrado y auditoría inmutable.
- **App móvil React Native + Expo SDK 54** con soporte offline, sincronización automática e integración de asistente de voz IA.
- **6 instrumentos de caracterización** cargados con sus respectivos loaders idempotentes (Perfiles V7 y V8, UARIV).
- **Corrección de los 10 errores críticos de seguridad** identificados en el APK original.

---

## 2. Problemas corregidos del sistema anterior

El APK original presentaba las siguientes fallas críticas, todas corregidas en el nuevo sistema:

| # | Error en APK v4.1 | Corrección implementada | Sprint |
|---|-------------------|------------------------|--------|
| 1 | HTTP sin TLS (`usesCleartextTraffic=true`) | HTTPS obligatorio, HSTS activado | 1 |
| 2 | 785 MB PII sin cifrar en el dispositivo | Sin datos PII en cliente. RNI solo en servidor | 1 |
| 3 | FTP plano a `ftp.isegoria.co` (tercero) | HTTPS a servidores propios únicamente | 1 |
| 4 | Contraseñas en texto plano (`PASSWORD TEXT`) | Argon2 (Django default) | 1 |
| 5 | `allowBackup=true` (ADB sin root) | `allowBackup=false` en manifiesto | 1 |
| 6 | SQLite sin cifrar | PostgreSQL + pgcrypto + volumen LUKS | 1 |
| 7 | Token sin expiración (`TOKENUSUARIO`) | JWT: access 15 min, refresh 8 h rotativo | 1 |
| 8 | Permisos excesivos en Android | Principio de mínimo privilegio | 1 |
| 9 | Credenciales hardcodeadas en el DEX | `python-decouple` + `.env` excluido del repo | 1 |
| 10 | ORM deprecado (SugarORM 2017) | Django ORM con migraciones versionadas | 1 |

---

## 3. Sprints entregados

### Sprint 1 — Fundamentos (2026-04-13)
**Commit:** `b08bc47`

- Backend Django 5.2 + DRF 3.15 configurado
- Autenticación JWT completa (login, refresh, logout, me, cambiar-password)
- Modelos base: Usuario, Perfil, LogAcceso inmutable, Victima con PII cifrado
- App móvil React Native scaffold con Expo Router, Zustand, expo-sqlite
- Motor de preguntas con skip logic base

**Indicadores:**
- Tests: suite base establecida
- Seguridad: 10/10 errores críticos del APK corregidos desde el inicio

---

### Sprint 2 — Motor de Formularios y Paramétricas (2026-04-13)
**Commit:** `12c7d7b`

- Motor dinámico de formularios (54 módulos, replica lógica `vivanto.db`)
- Carga de 33 departamentos, 1122 municipios, 32,377 veredas DANE
- Skip logic server-side con operadores: EQ, NEQ, GT, GTE, LT, LTE, IN, NOTNULL
- Búsqueda de víctimas por hash SHA-256 (sin descifrar PII)

**Indicadores:**
- Tests: 33/33 passing
- Paramétricas cargadas: departamentos, municipios, tipos de documento

---

### Sprint 3 — Hogares, Encuestas y Pantallas Móviles (2026-04-16)
**Commit:** `ec50cb3`

- Modelos completos de Hogar y MiembroHogar con PII cifrado
- SesionEncuesta con seguimiento de progreso (% completado)
- RespuestaEncuesta con upsert (permite corrección antes de cerrar)
- Pantallas móviles: lista hogares, detalle hogar, lista encuestas, detalle sesión

**Indicadores:**
- Tests: 53/53 passing (20 nuevos)
- Pantallas mobile: 5 pantallas funcionales

---

### Sprint 4 — Motor Offline y Sincronización (2026-04-19)
**Commit:** `6a66d64`

- Schema SQLite offline sin PII local
- Capa DAO completa: instrumento, borradores, hogares offline, cola de sincronización
- Evaluador skip logic TypeScript puro (testeable, sin I/O)
- Servicio de sincronización con resolución de conflictos offline→servidor
- Cola ordenada con prioridades (CREAR_HOGAR < CREAR_SESION < RESPONDER < FINALIZAR)
- MAX_INTENTOS=3 para resiliencia en zonas con conectividad intermitente

**Indicadores:**
- Funcionalidad offline: completa
- Tipos de error manejados: 4xx permanentes, 5xx/red con reintento

---

### Sprint 5 — Integración IA Gemini + UI GOV.CO (2026-04-19–21)
**Commits:** `2abf579`, `4bf168a`, `11ee14a`

- Proxy Gemini en el backend (API Key nunca en el cliente)
- Consentimiento IA firmado digitalmente (SHA-256, inmutable)
- Asistente de voz: grabación → transcripción → sugerencia → aceptar/rechazar
- UI rediseñada con identidad visual GOV.CO institucional
- ngrok con dominios permanentes para pruebas en celular físico

**Indicadores:**
- Tests nuevos: 25 (13 backend + 12 mobile)
- Pantallas con integración IA: formulario/[temaId].tsx

---

### Sprint 6 — Diccionario V8 + Loaders de Perfiles (2026-04-21–28)
**Commits:** `5f38078` → `06376de` (rama `feature/sprint6-diccionario-v8`)

- Modelo Django alineado con Diccionario de Datos UARIV V8
- 6 loaders idempotentes (uno por perfil):

| Perfil | Versión | Capítulos | Preguntas |
|--------|---------|-----------|-----------|
| Territorial | V7 | 14 | ~248 |
| Buenaventura | V7 | 17 | ~300 |
| San Andrés / SAI | V7 | 14 | ~290 |
| Telefónico SAAH | V8 | 7 | 54 |
| Urbano Étnico | V1 | 12 | ~120 |
| Rural Étnico | V1 | 14 | ~160 |

- Validadores cruzados de hogar (tutor con menores, cuidador, autorizado adulto+RUV)
- UI móvil: GovHeader, miga de pan, sesionId vinculado al formulario
- Documentación técnica completa del proyecto

**Indicadores:**
- Perfiles cargados: 6/6
- Tests: 29 nuevos (formulario x12 + hogares x17)

---

## 4. Estado actual del sistema

### Backend (Django REST Framework)
| App | Estado | Tests |
|-----|--------|-------|
| `autenticacion` | ✅ Completo | ✅ |
| `victimas` | ✅ Completo | ✅ |
| `formulario` | ✅ Completo (V8) | ✅ |
| `hogares` | ✅ Completo | ✅ |
| `encuestas` | ✅ Completo | ✅ |
| `parametricas` | ✅ Completo | ✅ |
| `ia` | ✅ Completo | ✅ |
| `auditoria` | ✅ Completo | ✅ |
| `sincronizacion` | 🔄 Scaffold | Pendiente |
| `reportes` | 🔄 Scaffold | Pendiente |

### App Móvil (React Native + Expo SDK 54)
| Funcionalidad | Estado |
|---------------|--------|
| Autenticación JWT | ✅ |
| Dashboard | ✅ |
| Búsqueda RNI server-side | ✅ |
| Gestión de hogares | ✅ |
| Sesiones de encuesta | ✅ |
| Motor de formularios + skip logic | ✅ |
| Soporte offline + sincronización | ✅ |
| Asistente IA (Gemini) | ✅ |
| UI GOV.CO institucional | ✅ |
| Firma digital al cerrar encuesta | 🔄 Sprint 7 |
| Push notifications | 🔄 Sprint 8 |

### Instrumentos de caracterización
| Perfil | Estado |
|--------|--------|
| Territorial V7 | ✅ |
| Buenaventura V7 | ✅ |
| San Andrés SAI V7 | ✅ |
| Telefónico SAAH V8 | ✅ |
| Urbano Étnico V1 | ✅ |
| Rural Étnico V1 | ✅ |

---

## 5. Métricas acumuladas

| Métrica | Valor |
|---------|-------|
| Sprints completados | 6 |
| Commits en el repositorio | 31 |
| Tests automáticos passing | 82+ |
| Apps Django implementadas | 9 |
| Pantallas móviles | 11 |
| Perfiles UARIV cargados | 6 |
| Preguntas en instrumento | ~1,172 |
| Días de desarrollo | 15 |

---

## 6. Pendientes para próximos sprints

### Sprint 7 (prioridad alta)
| Tarea | Descripción |
|-------|-------------|
| Endpoint API instrumento | `GET /api/formulario/instrumento/{perfilCodigo}/` |
| Skip logic completo | Integrar reglas V8 en el motor mobile |
| Tests de loaders | Carga idempotente + validaciones |
| Fixture Asistencia V8 | Completar opciones de respuesta |

### Sprint 8 (prioridad media)
| Tarea | Descripción |
|-------|-------------|
| Firma digital encuestador | Al cerrar sesión de encuesta |
| Push notifications | Asignaciones y alertas |
| App reportes | Dashboard de supervisores |
| Exportación datos | `pg_dump` + GPG para backup |

---

## 7. Stack tecnológico entregado

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | Django + Django REST Framework | 5.2 / 3.15.2 |
| Autenticación | djangorestframework-simplejwt | 5.x |
| Mobile | React Native + Expo | SDK 54 |
| Base de datos | PostgreSQL + pgcrypto | 16 |
| Cifrado PII | EncryptedField AES-256 | — |
| Hash contraseñas | Argon2 | — |
| IA Asistente | Google Gemini (proxy backend) | — |
| Contenedores | Docker + Docker Compose | latest |
| Repositorio | Azure DevOps + GitHub | — |

---

## 8. Repositorios

| Repositorio | URL | Rama principal |
|-------------|-----|----------------|
| Azure DevOps | (configurado en entorno) | `main` |
| GitHub (espejo) | (configurado en entorno) | `main` |
| Rama activa | `feature/sprint6-diccionario-v8` | → PR a `main` pendiente |

---

## 9. Cómo levantar el entorno de desarrollo

Ver [`docs/ARRANQUE-DEV.md`](ARRANQUE-DEV.md) para instrucciones paso a paso.

Resumen:
```powershell
# Terminal 1 — Backend
cd srni-backend && .venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8001

# Terminal 2 — App móvil
cd srni-mobile
npx expo start --port 8082
```

---

*Informe generado el 2026-05-04. Desarrollado bajo Contrato 2226-2026 — Unidad para las Víctimas (UARIV).*
