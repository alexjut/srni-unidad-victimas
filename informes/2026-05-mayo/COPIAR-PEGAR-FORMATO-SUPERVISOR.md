# Copiar-pegar al formato del supervisor — Informe Mayo 2026

> Este documento concentra las **2 secciones que pide el formato del supervisor**
> (Actividad desarrollada en este periodo + Evidencia que soporta esta actividad)
> para cada una de las 9 obligaciones. Está listo para copiar y pegar directo.

---

## Obligación 1 — Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Durante mayo 2026 se ejecutaron 16 sprints técnicos (6 al 21) con un total de 80 commits firmados distribuidos en los 3 componentes del sistema: backend Django REST Framework, app móvil React Native + Expo SDK 54 y panel web React + Vite. Los avances incluyeron: rediseño completo de UX del login con biometría y flujo de caracterización (Sprint 7), motor de formulario end-to-end con bulk sync (Sprint 8), sincronización masiva robusta con backoff exponencial (Sprint 9), reportes de producción del encuestador (Sprint 10), hardening de seguridad para producción (Sprint 11), implementación del panel web React + Tailwind para supervisores (Sprint 12), backend habilitador con filtros server-side y endpoints de supervisor/dashboard (Sprint 13), refactor del flujo móvil a un hub de caracterizaciones por hogar (Sprint 14), carga completa de los 8 instrumentos UARIV (Sprint 15), fix de 3 bugs críticos en el flujo móvil (Sprint 16), QA exhaustivo con sistema de captura de errores en producción (Sprint 17), refactor a arquitectura in-memory que elimina el "database is locked" recurrente (Sprint 18), implementación de la ubicación de atención como metadata de la sesión con cascada UARIV de 21 DTs y 1102 municipios (Sprint 19), backend habilitador para el panel web con renombrado descriptivo de instrumentos y render del selector dinámico de municipio (Sprint 20) y, finalmente, soporte de preguntas tipo PERSONA por cada miembro del hogar con wizard de navegación + calendario nativo en fechas (Sprint 21). El soporte continuo del mes resolvió 8 bugs críticos sin afectar la disponibilidad del entorno de desarrollo.

### Evidencia que soporta esta actividad

Repositorio Git oficial UARIV (Azure DevOps `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04`) y backup GitHub (`github.com/alexjut/srni-unidad-victimas`) — rama `main` consolidada al commit `7d1a6b9`. Bitácora completa de commits: `OE8-informes/git-log-mayo-2026.txt` (80 commits con fecha, hash y mensaje). Documentación de sprints: `docs/sprints/sprint-07.md` a `sprint-11.md` + bitácora interna `docs/frontend/bitacora-desarrollo.md`. Snapshot del estado del proyecto: `docs/estado-actual.md`. Reporte automatizado de QA por instrumento: `docs/qa-perfiles-sprint20.md` (regenerable con `scripts/qa_perfiles.py`). Correo de coordinación técnica con frontend: `docs/correo-brando.md`. Código fuente versionado en las carpetas `srni-backend/`, `srni-mobile/`, `srni-frontend/`.

---

## Obligación 2 — Realizar la captura, el procesamiento, la transformación y la gestión de calidad de datos de las fuentes recibidas por la entidad

### Actividad desarrollada en este periodo

Durante mayo 2026 se implementó la carga completa de paramétricos oficiales DANE y UARIV en la base de datos del sistema: 33 departamentos, 1 102 municipios (extraídos de la hoja DIVIPOLA del Excel oficial del Diccionario Territorial V7 UARIV mediante script Python), 21 Direcciones Territoriales UARIV con su mapeo M2M a departamentos, 41 puntos de atención y 3 tipos de documento. Se cargaron también los 8 instrumentos de caracterización (ASISTENCIA, TERRITORIAL, BUENAVENTURA, SAN_ANDRÉS, TELEFÓNICO, URBANO_ÉTNICO, RURAL_ÉTNICO y VÍCTIMAS_EXTERIOR) con un total de 1 001 preguntas activas y 2 239 opciones de respuesta (incluyendo 175 opciones extraídas del Diccionario Excel UARIV oficial para preguntas tipo LISTA que estaban vacías). Se diseñó e implementó el motor de sincronización automática offline → servidor en la app móvil con cola persistente en SQLite, backoff exponencial (2, 4, 8, 16, 32 segundos con jitter), 5 tipos de operación (CREAR_HOGAR, CREAR_SESION, RESPONDER_PREGUNTA, RESPONDER_BULK, FINALIZAR_SESION), detección de conectividad por ping a `/health/`, polling cada 60 segundos cuando hay conexión, idempotencia con marcado ENVIADO y propagación automática de IDs del servidor a items dependientes. La gestión de calidad de datos se automatizó mediante un script que compara la base de datos con los bundles JSON de la app móvil y genera reporte de discrepancias por instrumento; al cierre del mes el resultado es 0 discrepancias en los 8 instrumentos, 0 capítulos vacíos y 0 preguntas obligatorias sin opciones.

### Evidencia que soporta esta actividad

Scripts de carga versionados en el repositorio: `srni-backend/apps/parametricas/management/commands/cargar_departamentos_municipios.py`, `cargar_direcciones_territoriales.py`, `cargar_puntos_atencion.py`, y `srni-backend/scripts/extraer_municipios_divipola.py`. Dataset oficial generado: `srni-backend/data/municipios_dane.csv` (1102 municipios DANE). Comandos de mantenimiento de instrumentos: `cargar_capitulo_control.py`, `desactivar_preguntas_atencion.py`, `renombrar_instrumentos.py`, `exportar_a_mobile.py`. Motor de sincronización: `srni-mobile/src/services/sincronizacion.ts` + DAO de cola `srni-mobile/src/db/colaDao.ts`. Reporte automatizado de calidad de datos: `docs/qa-perfiles-sprint20.md` (regenerable con `srni-backend/scripts/qa_perfiles.py`). Bundles JSON generados: `srni-mobile/assets/instrumentos/` (8 archivos, ~675 KB).

---

## Obligación 3 — Procesar, implementar y documentar medidas de seguridad para proteger integridad, confiabilidad y confidencialidad de los datos

### Actividad desarrollada en este periodo

Durante mayo 2026 se implementó un hardening de seguridad integral alineado con la Ley 1581/2012 (Habeas Data), CONPES 3995 (Confianza Digital) y Decreto 1377/2013. En el Sprint 11 se aplicaron las siguientes medidas: throttle de 5 intentos de login cada 15 minutos por IP y 100 búsquedas RNI por hora por usuario; sustitución de la peligrosa función `eval()` por un parser AST seguro con lista blanca de nodos permitidos para evaluación de expresiones de skip logic; máximos de longitud en todos los serializers como protección anti-DoS; configuración de bases de datos para producción con SSL forzado; headers CSP en Nginx; gestión de secretos con Docker Secrets en `infra/secrets/` (excluidos del repositorio); cookies seguras (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, X_FRAME_OPTIONS=DENY); y rotación de tokens JWT (access 15 min, refresh 8 h rotativo). En el Sprint 18 Fase G se realizó una auditoría propia de fuga de PII en logs remotos: se identificó que el interceptor del cliente móvil enviaba la URL completa (con número de documento en query string) al endpoint de debug; se implementó un redactor PII que detecta 5 endpoints sensibles y omite el query string + reemplaza el body por "[REDACTADO — endpoint PII]". Adicionalmente, todos los campos PII (nombres, apellidos, documento, fecha de nacimiento) están cifrados en reposo con EncryptedCharField (Fernet AES-128) y se acompañan de un hash SHA-256 para búsqueda eficiente sin desencriptar. La auditoría inmutable se garantiza mediante el modelo LogAcceso (tabla sin permisos UPDATE ni DELETE desde la app) que registra cada consulta a víctimas, cada respuesta y cada finalización de sesión.

### Evidencia que soporta esta actividad

Cifrado de PII en reposo: `srni-backend/apps/victimas/fields.py` (definición de EncryptedCharField) y `srni-backend/apps/victimas/models.py` (uso en campos PII). Auditoría inmutable LogAcceso: `srni-backend/apps/auditoria/models.py` + `views.py`. Hardening Sprint 11: `srni-backend/srni/settings/production.py` con todas las directivas de seguridad. Redactor PII en logs (Sprint 18-G): `srni-mobile/src/api/client.ts` (líneas 40-100). Configuración Nginx con TLS + CSP: `infra/nginx/srni.conf`. Docker Secrets: estructura `infra/secrets/` (contenido excluido del repo por `.gitignore`). Hash SHA-256 para búsqueda PII: campo `Victima.numero_documento_hash` con `db_index=True`. Commits clave: `5ff906b` (Sprint 11 hardening) y `d289a7c` (Sprint 18-G redactor PII).

---

## Obligación 4 — Realizar el diseño e implementación de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Durante mayo 2026 se consolidó la arquitectura completa de 3 componentes del sistema de caracterización de víctimas, todos comunicándose por HTTPS + JWT. El backend Django REST Framework quedó operativo con 8 apps (autenticación, víctimas, formulario, hogares, encuestas, paramétricas, IA y reportes) + 2 transversales (auditoría y sincronización), con autenticación JWT de refresh rotativo (access 15 min, refresh 8 h), Swagger autogenerado en `/api/schema/swagger-ui/`, throttle global y por endpoint, filtros server-side con django-filter, paginación cursor para listas volátiles (sesiones) y page-number para el resto. La aplicación móvil React Native + Expo SDK 54 quedó implementada con Expo Router file-based, motor offline expo-sqlite con cola de sincronización, instrumentos pre-empaquetados como bundle JSON (no requiere descarga online), y bibliotecas auxiliares: react-native-paper para UI, expo-secure-store para tokens, expo-local-authentication para biometría, datetimepicker para calendario nativo y linear-gradient para fondos institucionales. El panel web React + Vite + Tailwind + Zustand quedó scaffolded con 5 páginas (Login, Dashboard, Hogares, Encuestas, Reportes), cliente axios con auto-refresh JWT en cola y estado global persistido en sessionStorage (nunca localStorage por seguridad). El despliegue local quedó orquestado por `docker-compose.yml` que levanta PostgreSQL con pgcrypto habilitado, Redis para cache y broker de Celery, backend Django con gunicorn y Nginx con configuración TLS lista. Los Docker Secrets quedaron preparados en `infra/secrets/` (excluidos del repo) para inyectar credenciales en producción.

### Evidencia que soporta esta actividad

Diagrama de arquitectura: sección "Arquitectura general" del archivo `informes/2026-05-mayo/OE4-arquitectura/README.md`. Orquestación de contenedores: `docker-compose.yml` (raíz del repositorio). Configuración Nginx + TLS: `infra/nginx/srni.conf`. Settings backend: `srni-backend/srni/settings/base.py`, `development.py`, `production.py`. Inicializador PostgreSQL: `infra/postgres/init.sql` (habilita pgcrypto). Backend operativo: carpeta `srni-backend/` con 8 apps Django. App móvil operativa: carpeta `srni-mobile/` con Expo SDK 54. Panel web operativo: carpeta `srni-frontend/` con Vite + React 18. Documentación de arranque: `docs/ARRANQUE-DEV.md` y scripts `arrancar-backend.ps1` + `arrancar-mobile.ps1`.

---

## Obligación 5 — Crear, diseñar y documentar la estructura de bases de datos

### Actividad desarrollada en este periodo

Durante mayo 2026 se consolidó la estructura completa de las dos bases de datos del sistema: PostgreSQL en el servidor (con extensión pgcrypto habilitada para cifrado de PII a nivel de columna) y SQLite en el dispositivo móvil (para soporte offline). En PostgreSQL, las 8 apps Django evolucionaron a través de 27 migraciones versionadas en Git (todas aplicables idempotentemente) que cubren el modelo del Diccionario UARIV V8, cifrado y hashing de PII, hogares v2 con autorizado + rol + estado_inclusion, sesiones con 4 FKs nuevas de ubicación de atención (Sprint 19), respuestas con FK opcional a miembro y UniqueConstraint compuesta (sesion, pregunta, miembro) (Sprint 21), paramétricas DANE + UARIV, usuario custom con perfiles de permisos granulares, LogAcceso inmutable y modelos de IA (consentimiento + logs Gemini). En SQLite móvil se versionó el schema desde V0 hasta V5 con migraciones controladas por `PRAGMA user_version` y transaccionales: V0 incluía tablas iniciales de captura, V1 agregó instrumento_meta + hogares_offline + cola_sincronizacion, V2 migró a UUIDs, V3 agregó retry_after para backoff, V4 eliminó las tablas de instrumento (al pasar a arquitectura in-memory en el Sprint 18) y V5 (Sprint 21) agregó la columna miembro_id con nuevo UNIQUE index para soportar preguntas tipo PERSONA por miembro. El esquema garantiza integridad referencial con FK PROTECT, integridad lógica con validación en serializers (cascada DT→Depto→Mun, coherencia HOGAR/PERSONA), y eficiencia mediante 14 índices DB-level + cache en memoria de los catálogos paramétricos.

### Evidencia que soporta esta actividad

Migraciones Django versionadas en carpetas `srni-backend/apps/*/migrations/` (27 archivos generados y aplicados en mayo). Migraciones críticas del mes: `encuestas/0005_sesionencuesta_departamento_atencion_*.py` (4 FKs ubicación atención), `encuestas/0006_alter_respuestaencuesta_options_*.py` (miembro FK + UniqueConstraint), `hogares/0003_autorizado_rol_*.py` (Hogar v2), `hogares/0004_remove_miembrohogar_*.py` (renames de índices). Modelos Django: `srni-backend/apps/encuestas/models.py`, `hogares/models.py`, `formulario/models.py`, `parametricas/models.py`. Schema SQLite mobile: `srni-mobile/src/db/schema.ts` (V5 con DDL_V0 + 5 migraciones idempotentes). Habilitación pgcrypto: `infra/postgres/init.sql`. DAOs de acceso a datos en mobile: `srni-mobile/src/db/borradoresDao.ts`, `colaDao.ts`, `hogaresOfflineDao.ts`. Diagrama ER en ASCII: sección "Diseño de relaciones" del README.md de la carpeta `OE5-bd/`.

---

## Obligación 6 — Crear y documentar modelos de datos que reflejen con precisión la información

### Actividad desarrollada en este periodo

Durante mayo 2026 se diseñaron, implementaron y documentaron tres modelos de datos integrados que reflejan el dominio completo del procedimiento de instrumentalización de víctimas. Modelo del Instrumento: Instrumento → Capítulo → Pregunta → OpcionRespuesta + ReglaSkipLogic, soportando 9 tipos de pregunta (TEXTO, TEXTO_LARGO, NUMERICO, FECHA, BOOLEAN, RADIO, LISTA, LISTA_MULTIPLE y COMBO_DINAMICO para selectores DIVIPOLA dinámicos), 2 niveles (HOGAR único o PERSONA repetido por miembro) y 4 acciones de skip logic (HABILITAR, DESHABILITAR, OBLIGAR, FINALIZAR). El modelo se materializa en 1 001 preguntas activas y 2 239 opciones distribuidas en los 8 instrumentos UARIV. Modelo del ciclo de caracterización: Victima (PII cifrado + hash SHA-256) → Hogar (autorizado, municipio, vivienda) → MiembroHogar (rol, parentesco, género, es_autorizado, estado_inclusion) y, paralelamente, Hogar → SesionEncuesta (instrumento + ruta + encuestador + 4 FKs de ubicación de atención de la Sprint 19) → RespuestaEncuesta (con FK opcional a miembro de la Sprint 21 y UniqueConstraint (sesion, pregunta, miembro) que diferencia respuestas tipo HOGAR de las repetidas por miembro). Modelo paramétrico: Departamento DANE → Municipio DANE → Vereda, con M2M a DireccionTerritorial UARIV y FK desde PuntoAtencion. La documentación incluye reglas de cardinalidad (1:N, 1:1), reglas de integridad (validación cascada UARIV en el serializer, es_autorizado único por hogar, coherencia HOGAR/PERSONA en respuestas) y cantidades cargadas en BD al cierre del mes (33 deptos, 1102 muns, 21 DTs, 41 puntos, 8 instrumentos, 1001 preguntas activas).

### Evidencia que soporta esta actividad

Modelo Django del instrumento: `srni-backend/apps/formulario/models.py` (Instrumento, Capitulo, Pregunta, OpcionRespuesta, ReglaSkipLogic). Modelo Django del ciclo de caracterización: `srni-backend/apps/encuestas/models.py` (SesionEncuesta, RespuestaEncuesta), `srni-backend/apps/hogares/models.py` (Hogar, MiembroHogar), `srni-backend/apps/victimas/models.py` (Victima). Modelo Django paramétrico: `srni-backend/apps/parametricas/models.py` (Departamento, Municipio, Vereda, DireccionTerritorial, PuntoAtencion, TipoDocumento, ComunidadNegra, ResguardoIndigena). Documentación de relaciones: secciones "Reglas de cardinalidad" y "Reglas de integridad" del README.md de la carpeta `OE6-modelos/`, con diagramas ASCII de cada modelo. Schema SQLite móvil reflejando los modelos: `srni-mobile/src/db/schema.ts` con tablas borradores y respuestas. Documentación cualitativa de cada tipo de pregunta: sección "Tipos de pregunta soportados" del README.md.

---

## Obligación 7 — Asistir a las reuniones programadas

### Actividad desarrollada en este periodo

Durante mayo 2026 se asistió a las reuniones de coordinación con el supervisor Oscar Andrés Manosalva García y con el equipo de Caracterización SRNI. Las reuniones de equipo permitieron identificar hallazgos críticos del aplicativo móvil que se atendieron como sprints inmediatos (por ejemplo, el equipo SRNI envió evidencias gráficas el 26/05 mostrando que los 8 instrumentos debían comenzar con un capítulo de Información General de Atención —Dirección Territorial, Departamento, Punto y Municipio de Atención—, lo que se resolvió en el mismo día con el Sprint 19 completo: modelado backend, endpoints de cascada, pantalla móvil con cache local y limpieza de bundles). Adicionalmente se realizó coordinación técnica con el desarrollador del panel web (Brando) mediante un correo formal de onboarding (`docs/correo-brando.md`) que documenta credenciales, endpoints disponibles, procedimiento para solicitar endpoints nuevos y reporte de fallos. **[A complementar por el contratista con actas firmadas, listados de asistencia y presentaciones formales de cada reunión.]**

### Evidencia que soporta esta actividad

Correo de coordinación con frontend versionado: `docs/correo-brando.md`. Integración de trabajo del equipo: commit de merge `d7c9edb` que integró 5 commits del desarrollador frontend Brando sin pisar su trabajo. Hallazgos del equipo SRNI atendidos en sprints inmediatos: Sprint 19 (capítulo Información General de Atención), Sprint 20 (nombres descriptivos de instrumentos), Sprint 20-QA-B (render selector municipio), Sprint 21 (preguntas por miembro + calendario + wizard). **Anexos a aportar por el contratista:** acta de reunión inicial de contrato (abril 2026), acta de reunión de georreferenciación (21/05/2026), listado de asistencia al Taller Aplicativo Tupago (20/05/2026), presentación de avance Mayo (PPTX entregado al supervisor), correos de retroalimentación de Oscar y audios o capturas de las reuniones semanales.

---

## Obligación 8 — Cargar mensualmente los documentos en la ruta dispuesta por la Subdirección

### Actividad desarrollada en este periodo

Durante mayo 2026 se elaboró el informe mensual completo del período, estructurado por las 9 obligaciones específicas del cronograma del contrato 2226-2026 (carpeta `informes/2026-05-mayo/` versionada en el repositorio oficial UARIV en Azure DevOps y backup en GitHub). El informe incluye: un README global con resumen ejecutivo del mes (80 commits, 16 sprints completados, indicadores cuantitativos), 9 subcarpetas con un README cada una documentando actividad desarrollada, evidencias y archivos físicos copiados (total 35 archivos autocontenidos), y una carpeta adicional `EXTRAS-actividades-adicionales/` con el trabajo ejecutado por iniciativa del contratista por fuera del cronograma (mejoras UX, refactors técnicos preventivos, auditoría de seguridad propia, higiene del repositorio, automatizaciones, documentación adicional, coordinación de equipo). Adicionalmente se generaron anexos automatizados: log completo de los 80 commits del mes (`git-log-mayo-2026.txt`), snapshot del estado del proyecto (`estado-actual.md`), reporte automatizado de QA por instrumento (`qa-perfiles-sprint20.md`) y correo de onboarding para el desarrollador del panel web (`correo-brando.md`). **[Pendiente por parte del contratista: completar el formato oficial UARIV con plantilla del supervisor, firmar el PDF, cargar a SECOP II y subir la carpeta a OneDrive del supervisor.]**

### Evidencia que soporta esta actividad

Informe mensual estructurado: `informes/2026-05-mayo/` (carpeta versionada en repositorio Git oficial UARIV y backup GitHub). README global con resumen ejecutivo: `informes/2026-05-mayo/README.md`. 9 README por obligación + EXTRAS: un archivo por carpeta `OE1-desarrollo/` a `OE9-adicionales/` + `EXTRAS-actividades-adicionales/`. 35 archivos físicos copiados autocontenidos para SECOP II / OneDrive sin dependencia del repo. Anexos automatizados generados: `git-log-mayo-2026.txt`, `estado-actual.md`, `qa-perfiles-sprint20.md`, `correo-brando.md`. Commits de generación del informe: `6462314` (carpeta inicial) + `7d1a6b9` (EXTRAS).

---

## Obligación 9 — Cumplir las demás actividades acordadas con el supervisor

### Actividad desarrollada en este periodo

Durante mayo 2026 se atendieron varias actividades adicionales acordadas con el supervisor, complementarias al objeto del contrato. **[Sección a complementar por el contratista con los siguientes ítems: estado del acuerdo de confidencialidad de aplicativos —firma exigida antes del 1 de mayo—; acreditación mensual al supervisor del pago de aportes a seguridad social del mes, ARL y planilla PILA; estado real de las solicitudes formales a Oscar para obtención de accesos a los servidores SRNI —FTP UARIV, Azure IGPD, Azure Móvil y Sistema Ficha—; gestión de la API key Gemini institucional ante Google Cloud con DPA jurídica firmada y configuración en Azure Key Vault para uso en producción; verificación del snapshot semanal del repositorio en OneDrive del supervisor con permisos restringidos solo al contratista y al supervisor.]** El único acceso operativo a la fecha es el repositorio Azure DevOps oficial UARIV (rama `main` consolidada al commit `7d1a6b9`); los demás accesos siguen pendientes de aprobación formal.

### Evidencia que soporta esta actividad

Repositorio Azure DevOps activo: `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04` (acceso aprobado y operativo). Checklist de actividades pendientes: sección "Checklist Mayo 2026" del README.md de la carpeta `OE9-adicionales/` con tabla de estado de cada acceso. **Anexos a aportar por el contratista:** acuerdo de confidencialidad firmado (escaneo PDF), comprobantes de aportes a seguridad social de mayo (PILA o planilla), correos de solicitud de accesos UARIV con fechas (FTP, Azure IGPD, Azure Móvil, Ficha), captura de configuración de la API key Gemini cuando se apruebe, captura de estructura de OneDrive con permisos restringidos, reporte ejecutivo a Oscar sobre estado de la API key Gemini institucional.
