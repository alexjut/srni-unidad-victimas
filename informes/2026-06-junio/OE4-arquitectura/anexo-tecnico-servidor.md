# Anexo técnico — Solicitud de aprovisionamiento de servidor
## Sistema de Caracterización de Víctimas — SRNI

---

**Contrato:** 2226-2026
**Contratista:** Javier Alexander Aguilar Castro · CC 1.030.547.250
**Supervisor SRNI:** Oscar Andrés Manosalva García
**Solicitante TI:** Ing. Sergio (Infraestructura UARIV)
**Fecha:** 2026-06-02
**Versión del anexo:** 1.1

---

## 0. Propósito del documento

Este anexo complementa la solicitud original de aprovisionamiento de servidor enviada al área de Infraestructura TI de la UARIV. Detalla, en cinco secciones, los elementos solicitados por TI:

1. **Arquitectura** del despliegue
2. **Componentes a desplegar** (backend, panel web y distribución de la APK)
3. **Privilegios** requeridos (sistema operativo, base de datos, red)
4. **Modelo de tablas** de la base de datos operacional
5. **Marco normativo aplicable**

El despliegue solicitado **no requiere conexión a la base de datos Oracle institucional** (`RNIENTREVISTA`). La solución opera sobre su propia base de datos PostgreSQL local en el mismo servidor. La eventual integración con Oracle se tramitará en una solicitud independiente, conforme a los lineamientos que TI y la Oficina de Seguridad de la Información determinen.

---

## 1. Arquitectura

### 1.1 Vista general

La solución se compone de **tres aplicaciones que se despliegan en un solo servidor Linux**, todas contenedorizadas con **Docker** y orquestadas mediante **Docker Compose**, expuestas tras un proxy inverso único Nginx:

```
                                INTERNET / Intranet UARIV
                                          │
                                          │ HTTPS (443/TCP)
                                          ▼
                         ┌──────────────────────────────┐
                         │   Nginx 1.25 — Reverse Proxy │
                         │   TLS 1.2+ · HSTS · CSP      │
                         └────────────┬─────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
   /api/* ──►                /panel/* ──►              /movil/app.apk
            │                         │                         │
            ▼                         ▼                         ▼
   ┌──────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
   │  Backend Django  │  │  Panel Web SRNI      │  │  Distribución APK    │
   │  Gunicorn 21     │  │  React 18 + Vite     │  │  Archivo .apk firmado│
   │  Python 3.12     │  │  Build estático      │  │  Servido por Nginx   │
   │  contenedor:     │  │  servido por Nginx   │  │  como descarga       │
   │    backend       │  │  (volumen montado)   │  │  controlada          │
   └────────┬─────────┘  └──────────────────────┘  └──────────────────────┘
            │
            │  (red interna Docker, sin exposición al host)
            │
   ┌────────┼─────────┐    ┌──────────────────┐
   ▼                  ▼    ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ PostgreSQL16 │  │   Redis 7    │  │  Celery 5    │
│ pgcrypto     │  │ cola Celery  │  │ worker async │
│ contenedor:  │  │ contenedor:  │  │ contenedor:  │
│   postgres   │  │   redis      │  │   celery     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 1.2 Modelo de despliegue — Docker Compose

Cada componente se ejecuta en su propio **contenedor Docker**, orquestados por un único archivo `docker-compose.yml` que reside en el repositorio del proyecto. Este modelo aporta:

- **Reproducibilidad total** — `docker compose up -d` reconstruye el stack idéntico en cualquier servidor con el SO indicado.
- **Aislamiento** — cada servicio (backend, BD, cola, panel web) corre en su propio espacio de procesos, red y filesystem. Una eventual vulneración de un contenedor no compromete al resto.
- **Versionado explícito** — las versiones de Nginx 1.25, PostgreSQL 16, Redis 7, Python 3.12 y demás quedan fijadas en el `docker-compose.yml`, eliminando drift entre entornos.
- **Gestión de secretos** — credenciales de BD entregadas vía **Docker secrets** (`/run/secrets/`), nunca en variables de entorno legibles ni en código.
- **Volúmenes persistentes** — datos de PostgreSQL y Redis viven en volúmenes nombrados (`pgdata`, `redisdata`), separados del ciclo de vida de los contenedores.
- **Healthchecks integrados** — PostgreSQL expone un healthcheck que retrasa el arranque del backend hasta que la BD esté lista (`depends_on: service_healthy`).
- **Reinicio automático** — directiva `restart: unless-stopped` en cada servicio.
- **Operación estándar** — `docker compose up/down/ps/logs` cubre todo el ciclo de vida del stack.

Sin orquestadores externos (no Kubernetes, no Swarm) — Docker Compose es suficiente para el volumen esperado en validación y producción inicial, y simplifica la operación.

Comandos básicos de administración:

```bash
sudo docker compose up -d        # arrancar todo el stack
sudo docker compose ps           # estado de cada contenedor
sudo docker compose logs -f api  # logs en vivo del backend
sudo docker compose down         # detener todo
```

### 1.3 Flujos funcionales

| Origen | Destino | Canal | Propósito |
|--------|---------|-------|-----------|
| Encuestador móvil (Android, en campo) | Backend Django | HTTPS 443 | Autenticación, búsqueda RNI, envío de respuestas, descarga de la APK actualizada |
| Supervisor / Coordinador DT (panel web) | Panel web → Backend | HTTPS 443 | Login, dashboards, listados de hogares y encuestas, reportes, consulta de auditoría |
| Administrador UARIV | Backend (`/admin`) | HTTPS 443 | Gestión de usuarios, perfiles y parámetros |
| Backend | PostgreSQL | Red interna Docker | Persistencia operacional |
| Backend | Redis | Red interna Docker | Cola asíncrona de sincronización |

**No existe** tráfico saliente del servidor hacia internet abierto, salvo:
- Resolución DNS y NTP estándar.
- Renovación de certificado TLS (si TI autoriza ACME / Let's Encrypt; opcional).
- Llamada al servicio Gemini de Google (IA) **solo si el supervisor lo activa** — la clave API reside en variable de entorno del backend; la APK nunca conoce esa clave.

### 1.4 Resiliencia y operación

- **Logs:** centralizados con el driver de logging de Docker; rotación diaria, retención 30 días, formato JSON estructurado sin PII. Acceso vía `docker compose logs`.
- **Salud:** endpoint `GET /health/` del backend + healthcheck nativo de Docker en PostgreSQL.
- **Backups:** dump cifrado de PostgreSQL diario por `pg_dump` desde un contenedor de respaldo, retención 7 días local + envío opcional a OneDrive institucional del supervisor.
- **Reinstalación:** procedimiento reproducible — clonar el repositorio Azure DevOps, copiar el archivo `.env` con secretos, ejecutar `docker compose up -d`. Sin instalaciones manuales fuera del propio Docker.

---

## 2. Componentes a desplegar

### 2.1 Backend — API REST (Django)

| Atributo | Valor |
|----------|-------|
| Lenguaje | Python 3.12 |
| Framework | Django 5.2 + Django REST Framework 3.16 |
| Servidor de aplicación | Gunicorn 21 (4 workers) |
| Autenticación | JWT (access 15 min, refresh 8 h con rotación) |
| Empaque | Imagen Docker construida desde `srni-backend/Dockerfile` |
| Contenedor | Servicio `backend` del `docker-compose.yml` |
| Puerto interno | 8001 (red interna Docker, no expuesto al host) |
| Función | Expone la API REST que consumen tanto el panel web como la app móvil |

### 2.2 Panel web — Interfaz para supervisores y coordinadores

| Atributo | Valor |
|----------|-------|
| Tecnología | React 18 + Vite 5 + TailwindCSS 3 + Zustand |
| Tipo de despliegue | Compilado a **archivos estáticos** (HTML/CSS/JS), servidos por el contenedor `nginx` desde un volumen montado |
| Acceso | `https://<servidor>/panel/` |
| Usuarios | Supervisor SRNI, Coordinadores de Dirección Territorial, Administradores UARIV |
| Funcionalidades vigentes | Login, Dashboard, listado de hogares y encuestas, detalle de víctima y de hogar, reportes de producción, vista de instrumentos, paramétricas, supervisión, **auditoría** |
| Almacenamiento local | Solo `sessionStorage` (se borra al cerrar sesión). Nunca `localStorage`. Service Worker limpia caché al logout. |
| Idioma | Español (institucional UARIV) |

El panel web **no almacena PII** en el navegador. Recibe del backend únicamente los campos necesarios por endpoint (principio de minimización del Decreto 1377/2013).

### 2.3 Distribución de la APK móvil

| Atributo | Valor |
|----------|-------|
| Plataforma | Android 8.0+ |
| Tecnología | React Native + Expo SDK 54 |
| Tamaño | ≈ 60 MB (incluye los 8 instrumentos pre-empaquetados) |
| Forma de distribución | Archivo `.apk` firmado, servido por Nginx en `https://<servidor>/movil/app.apk` |
| Versionado | Endpoint `GET /api/movil/version` que informa la última versión disponible |
| Almacenamiento local en el dispositivo | SQLite con redactor de PII; sincronización al backend en cuanto hay conexión |
| Funcionalidad offline | Total — el encuestador puede caracterizar sin internet; la única operación que requiere red es la búsqueda en el RNI |

### 2.4 Componentes de soporte (contenedores Docker)

| Componente | Imagen / Versión | Contenedor (compose) | Propósito |
|------------|------------------|----------------------|-----------|
| Nginx | `nginx:1.25-alpine` | `nginx` | Proxy inverso, TLS, servir estáticos del panel y la APK |
| Gunicorn (backend) | construida desde `Dockerfile` propio · Python 3.12 | `backend` | Servidor WSGI del backend Django |
| Celery worker | misma imagen del backend | `celery` | Cola asíncrona de sincronización y reportes |
| PostgreSQL | `postgres:16-alpine` | `postgres` | Persistencia operacional (volumen `pgdata`) |
| Redis | `redis:7-alpine` con `--requirepass` | `redis` | Cola y caché en memoria (volumen `redisdata`) |

Todos los servicios se gestionan con `docker compose <up|down|ps|logs|restart>` y exponen sus logs por el driver de logging de Docker.

---

## 3. Privilegios requeridos

### 3.1 Sistema operativo del servidor

| Sujeto | Privilegio | Justificación |
|--------|-----------|---------------|
| Usuario `srni-deploy` (contratista) | Acceso SSH por **llave pública** desde una IP autorizada por TI | Despliegue, actualización y diagnóstico |
| Usuario `srni-deploy` | Membresía en el grupo `docker` | Necesaria para administrar el stack Docker Compose sin ser root |
| Usuario `srni-deploy` | `sudo` restringido a comandos específicos: `docker compose`, `pg_dump` dentro del contenedor de respaldo, lectura de logs | Operación rutinaria sin acceso root completo |
| Root | No se requiere acceso interactivo en operación normal | Solo TI mantiene root |

**SSH:** únicamente por llave pública, sin contraseña; puerto SSH a criterio de TI (estándar o no estándar).
**Sudoers:** archivo separado `/etc/sudoers.d/srni-deploy` con comandos explícitos, sin `ALL`.

### 3.2 Red y firewall

| Puerto | Protocolo | Origen | Estado | Uso |
|--------|-----------|--------|--------|-----|
| 443 | TCP | Cualquiera (o intranet UARIV) | ABIERTO | HTTPS (único punto de entrada) |
| 22 | TCP | IP del contratista autorizada por TI | ABIERTO restringido | SSH administrativo |
| 80 | TCP | Cualquiera | OPCIONAL | Solo si TI autoriza redirección a 443 |
| Todos los demás | — | — | CERRADOS | — |

### 3.3 Base de datos PostgreSQL (interna al servidor)

La base de datos corre como contenedor Docker en la red interna del stack y **no expone puerto al host ni al exterior**. Solo es accesible desde los contenedores `backend`, `celery` y el contenedor de respaldo. Roles previstos:

| Rol | Privilegios | Uso |
|-----|-------------|-----|
| `postgres` (superusuario local) | Todos | Creación inicial, mantenimiento de TI |
| `srni_app` (usuario de aplicación) | `CONNECT` a la base · `USAGE` en esquema `public` · `SELECT`, `INSERT`, `UPDATE`, `DELETE` en todas las tablas **excepto auditoría** · `USAGE`, `SELECT` en secuencias | Backend Django |
| `srni_app` sobre `auditoria_logacceso` | `INSERT` y `SELECT` únicamente — **`UPDATE` y `DELETE` revocados a nivel de motor** | Inmutabilidad de la auditoría (requisito Ley 1581) |
| `srni_backup` (usuario de respaldo) | `SELECT` en todas las tablas | `pg_dump` programado |

Las credenciales se entregan al contratista por canal cifrado y se gestionan vía **Docker secrets** (archivos montados como `/run/secrets/pg_db`, `/run/secrets/pg_user`, `/run/secrets/pg_password` solo en los contenedores que los requieren). El archivo `.env` de la aplicación tiene permisos `0600` y **nunca reside en el código fuente** del repositorio.

### 3.4 Perfiles de usuario dentro de la aplicación

Independiente de los privilegios de infraestructura, la aplicación maneja cuatro perfiles funcionales:

| Perfil | Puede buscar en RNI | Puede caracterizar | Puede ver reportes | Puede administrar |
|--------|:-------------------:|:------------------:|:------------------:|:-----------------:|
| Encuestador de campo | ✅ | ✅ | ❌ | ❌ |
| Coordinador DT | ✅ | ✅ | ✅ | ❌ |
| Supervisor | ✅ | ❌ | ✅ | ❌ |
| Administrador | ✅ | ✅ | ✅ | ✅ |

Cada acción de cada perfil queda registrada en la tabla inmutable de auditoría.

---

## 4. Modelo de tablas — Base de datos operacional

La base de datos `srni` se compone de **27 tablas** organizadas en 10 dominios (apps Django). Toda la información personal sensible (PII) está cifrada en reposo con AES-256 (`pgcrypto`) y, cuando aplica, se almacena además un hash SHA-256 sin reversibilidad para permitir búsquedas exactas sin descifrar.

### 4.1 Convenciones

- **PII cifrado:** identifica campos con cifrado simétrico AES-256.
- **Hash:** campos con hash determinístico SHA-256 (solo para búsqueda exacta).
- **Inmutable:** la tabla no admite `UPDATE` ni `DELETE` (control a nivel de motor + a nivel ORM).
- **UUID:** clave primaria UUIDv4 (no expone secuencia interna).

### 4.2 Inventario de tablas

#### Dominio Autenticación

| Tabla | Propósito | PII | Notas |
|-------|-----------|-----|-------|
| `autenticacion_perfil` | Catálogo de perfiles y banderas de permisos | No | 4 registros (Encuestador, Coordinador, Supervisor, Administrador) |
| `auth_usuario` | Usuarios del sistema (Django personalizado) | Nombre completo, correo | Contraseñas con Argon2 |

#### Dominio Auditoría (inmutable)

| Tabla | Propósito | PII | Notas |
|-------|-----------|-----|-------|
| `auditoria_logacceso` | Bitácora inmutable de toda acción sobre datos de víctimas | No directo | UUID. Sin UPDATE/DELETE a nivel motor |

#### Dominio Paramétricas (datos de referencia, sin PII)

| Tabla | Propósito |
|-------|-----------|
| `parametricas_departamento` | 33 departamentos DANE 2023 |
| `parametricas_municipio` | 1 102 municipios DANE 2023 |
| `parametricas_vereda` | Veredas / centros poblados rurales |
| `parametricas_tipodocumento` | Tipos de documento oficiales |
| `parametricas_comunidadnegra` | Consejos comunitarios |
| `parametricas_resguardoindigena` | Resguardos indígenas |
| `parametricas_direccionterritorial` | 21 DT UARIV |
| `parametricas_direccionterritorial_departamentos` | Cobertura geográfica de cada DT |
| `parametricas_puntoatencion` | Puntos de atención por DT |

#### Dominio Víctimas (PII cifrado)

| Tabla | Propósito | PII | Notas |
|-------|-----------|-----|-------|
| `victimas_victima` | Registro Nacional de Información (vista operativa) | **Sí**: nombres, documento, fecha nacimiento | Documento adicionalmente con hash SHA-256 para búsqueda |

#### Dominio Formulario (catálogo de instrumentos, sin PII)

| Tabla | Propósito |
|-------|-----------|
| `formulario_perfil` | Los 8 instrumentos UARIV vigentes |
| `formulario_instrumentoversion` | Versionado de cada instrumento (V7, V8…) |
| `formulario_capitulo` | 93 capítulos transversales |
| `formulario_pregunta` | 995 preguntas activas |
| `formulario_opcionrespuesta` | 2 239 opciones de respuesta |
| `formulario_reglaskiplogic` | Reglas PREDEPENDE / RESHABILITA / RESFINALIZA |

#### Dominio Hogares y caracterización (PII cifrado)

| Tabla | Propósito | PII |
|-------|-----------|-----|
| `hogares_hogar` | Núcleo familiar caracterizado | No directo (FK a víctima) |
| `hogares_miembrohogar` | Integrantes del hogar | **Sí**: nombres, documento, parentesco |
| `encuestas_sesionencuesta` | Sesión de caracterización por instrumento | No directo |
| `encuestas_respuestaencuesta` | Respuestas individuales | Solo si la pregunta captura PII |

#### Dominio IA (asistencia opcional)

| Tabla | Propósito | PII |
|-------|-----------|-----|
| `ia_consentimientoia` | Consentimiento explícito de uso de IA por sesión | No directo |
| `ia_sesion_ia` | Bitácora de prompts y respuestas IA | Redactor PII elimina nombres y documentos antes de persistir |

#### Dominio JWT (gestión de tokens)

| Tabla | Propósito |
|-------|-----------|
| `token_blacklist_outstandingtoken` | Tokens emitidos vigentes (rotación) |
| `token_blacklist_blacklistedtoken` | Tokens revocados |

### 4.3 Controles transversales sobre PII

1. Campos PII cifrados con AES-256 a nivel de columna (`pgcrypto`).
2. Volumen de la BD montado sobre disco cifrado (LUKS recomendado por TI).
3. Hash SHA-256 determinístico únicamente para búsqueda exacta por documento, sin almacenar el documento en claro adicional.
4. Auditoría inmutable a nivel de motor (revocación de `UPDATE`/`DELETE`).
5. Política de minimización en serializadores: el panel web y la app móvil reciben solo los campos necesarios por endpoint.
6. Service Worker del panel web limpia el almacenamiento local al cerrar sesión.

---

## 5. Marco normativo aplicable

La solución se desarrolla en cumplimiento del siguiente marco normativo colombiano vigente:

### 5.1 Protección de datos personales

- **Ley 1581 de 2012** — Régimen general de protección de datos personales.
  *Aplicación:* clasificación de víctimas como **dato sensible**, principios de finalidad, libertad, veracidad, transparencia, seguridad y confidencialidad. Habeas data.
- **Decreto 1377 de 2013** — Reglamentación parcial de la Ley 1581.
  *Aplicación:* aviso de privacidad, consentimiento previo, expreso e informado, atención de PQR y derechos ARCO.
- **Decreto Único Reglamentario 1074 de 2015** — Compila normas del sector comercio incluyendo el régimen de protección de datos.
- **Circular Externa 002 de 2015 (SIC)** — Lineamientos para registro nacional de bases de datos.

### 5.2 Seguridad digital y arquitectura del Estado

- **CONPES 3995 de 2020** — Política nacional de confianza y seguridad digital.
  *Aplicación:* hardening del backend, gestión de incidentes, controles criptográficos, throttle anti-abuso, AST en componentes seguros, gestión de secretos.
- **CONPES 3854 de 2016** — Política nacional de seguridad digital.
- **Decreto 1078 de 2015** — Decreto Único Reglamentario del sector TIC.
- **Resolución MinTIC 1519 de 2020** — Lineamientos de accesibilidad, seguridad, calidad y datos abiertos.
  *Aplicación en negativo:* los datos de víctimas **no son datos abiertos** y no son objeto de publicación; el sistema cumple las exigencias de seguridad y accesibilidad de la resolución.
- **Decreto 620 de 2020** — Servicios Ciudadanos Digitales (SCD).
- **Manual de Gobierno Digital (MinTIC)** — Componente de Seguridad y Privacidad de la Información (PETI institucional).

### 5.3 Marco institucional UARIV

- **Ley 1448 de 2011** — Ley de Víctimas y Restitución de Tierras.
  *Aplicación:* habilita la atención a la población víctima y el deber de la Unidad de caracterizarla.
- **Decreto 4800 de 2011** — Reglamentación de la Ley 1448.
- **Resoluciones internas UARIV** sobre tratamiento y custodia de información de víctimas (instrumentos UARIV V7/V8 incorporados en la solución).

### 5.4 Buenas prácticas de referencia adoptadas

- **NIST SP 800-53** y **ISO/IEC 27001:2022** — controles de seguridad de la información (referenciales, no de obligatorio cumplimiento legal).
- **OWASP ASVS L2** — verificación de seguridad de aplicaciones (referencial).

### 5.5 Compromisos contractuales del contratista en materia de datos

1. No extraer, reproducir o almacenar información de víctimas fuera de la infraestructura UARIV.
2. Devolver y eliminar toda copia local al término del contrato.
3. Notificar a TI y al supervisor cualquier incidente de seguridad detectado.
4. Entregar al supervisor el código fuente, credenciales y procedimientos operativos al cierre.
5. Sujetarse a la política de tratamiento de datos personales de la UARIV.

---

## 6. Cierre

Este anexo se entrega como complemento de la solicitud original. Quedo atento a observaciones, ajustes o documentación adicional que el área de Infraestructura TI o la Oficina de Seguridad de la Información de la UARIV requieran.

Para reunión técnica de aclaración, el contratista queda a disposición.

Cordialmente,

**Javier Alexander Aguilar Castro**
Contratista — Sistema de Caracterización de Víctimas SRNI
CC 1.030.547.250 · Contrato 2226-2026
ingaguilarsistemas@gmail.com
