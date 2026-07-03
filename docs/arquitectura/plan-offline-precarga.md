# Plan — Funcionamiento offline con pre-carga al login (SRNI móvil)

> Objetivo: que el encuestador, **al loguearse con internet**, deje el dispositivo
> listo para trabajar **sin señal** en campo: verificar contra el RUV (~10M) si una
> persona está y si **ya fue caracterizada**, y levantar la caracterización completa
> offline, sincronizando al recuperar conexión.

## 1. Principio de diseño

No se espeja todo el PII de 10M de víctimas en el celular (sería 1–2 GB y un
riesgo legal grave bajo la Ley 1581). Se separan dos cosas:

| Capa | Qué guarda | Para qué | Tamaño aprox. (10M) |
|---|---|---|---|
| **Padrón offline** | por víctima: **documento, nombre, ubicación (municipio), CANTIDAD de hechos** + banderas (`en_ruv`, `habilitada`, `ya_caracterizada`) + `cons_persona`. **NO** guarda el detalle de los hechos. | Buscar/identificar (por cédula o nombre) y verificar a **cualquiera** de los 10M offline | **~700 MB – 1 GB**, cifrado |
| **Jornada** | Datos completos (incluye **detalle de hechos** y grupo familiar) de **los pocos** del día | Precargar el formulario de los que se van a entrevistar | KB–pocos MB |
| **Instrumentos** | Preguntas de los 7 instrumentos | Responder la encuesta offline | Ya empaquetados en el APK |
| **Paramétricas** | Municipios, DT, puntos de atención | Cascada de ubicación offline | ~1 MB |

**Campos del padrón (decisión):** nombre + documento + ubicación + **cantidad** de
hechos + estado (en RUV / habilitada / ya caracterizada). El **detalle de los hechos**
(códigos HV, fechas, municipios del hecho) NO va en el padrón — solo en la **jornada**.

**Implicación de tamaño/seguridad:** incluir nombre+documento+ubicación de 10M sube el
padrón a ~700 MB–1 GB (vs ~150 MB si solo fuera documento hasheado). Sigue cabiendo en
el celular y se baja por WiFi, pero **es una lista de identidad de las víctimas** → va
**cifrado en reposo** (obligatorio, Ley 1581), se borra al cerrar sesión / cerrar jornada,
y el documento se indexa **hasheado** para la búsqueda por cédula.

## 2. Flujo

```
LOGIN (con internet)
  1. Autenticación normal (JWT).
  2. ¿Hay padrón local y está al día (versión == servidor)?  -> si no, descargar (WiFi).
  3. Descargar la jornada asignada (datos completos de los pocos del día).
  4. Refrescar paramétricas a SQLite local.
  -> Dispositivo OFFLINE-READY.

CAMPO (sin internet)
  - Verificar cédula -> hash -> lookup local en el padrón -> está / no está / ya caracterizada.
  - Conformar hogar + responder encuesta -> SQLite local + cola de sincronización.

RECONEXIÓN (online = "actualiza y verifica TODO")
  SUBIR  -> vaciar la cola: crear hogar/sesión, respuestas, finalizar.
  BAJAR  -> refrescar padrón (si cambió de versión), paramétricas/geográfico y listas.
  VERIFICAR -> el servidor reconcilia `ya_caracterizada` y bloquea duplicados (constraint + 409).
  TOKEN  -> se refresca aquí (la captura offline nunca lo necesitó).
```

**Quién es el "master":** mientras está **offline, el dispositivo es la fuente de lo
que capturó** (hogares, respuestas) — nadie más lo tiene. Al reconectar, esa captura
**sube** al servidor (que pasa a ser la fuente de verdad consolidada) y el dispositivo
**baja** las actualizaciones (padrón, estados, geográfico, listas). Nada se pierde por
trabajar sin señal.

**Datos de referencia que también van offline (precargados al login):**
- **Geográfico:** departamentos, municipios, direcciones territoriales, puntos de atención.
- **Listas/catálogos:** las opciones de respuesta de cada pregunta (vienen con los
  instrumentos empaquetados) + cualquier catálogo compartido que use el formulario.

## 3. Componentes a construir

### Backend
- **Generador del padrón** (management command): exporta desde el RUV (Oracle) un
  archivo compacto indexado por `hash(documento)` con las banderas. Versionado
  (fecha + checksum). Se regenera periódicamente (p. ej. nocturno/semanal).
- **Endpoint de descarga del padrón**: `GET /api/victimas/padron/` (gzip) +
  `GET /api/victimas/padron/version/` para que la app sepa si debe re-descargar.
- **Endpoint de jornada**: `GET /api/victimas/jornada/` → datos completos del
  subconjunto asignado al encuestador.

### Móvil
- **Almacén local cifrado** (SQLite cifrado): tablas `padron`, `jornada`,
  `parametricas`, además de las offline ya existentes (hogares/borradores/respuestas/cola).
- **Lookup local**: la búsqueda hashea el documento tecleado y consulta `padron`
  (en vez de pegarle al servidor).
- **Selector de instrumento desde el bundle local** (hoy pide a la API → queda vacío offline).
- **Pre-carga al login**: descarga padrón (si está desactualizado) + jornada + paramétricas.

## 4. Sesión y token (entrevistas de horas)

- La **captura en campo es local** (SQLite) y **no usa el token** → aunque el access
  token expire durante la entrevista, no se interrumpe nada.
- Subir `REFRESH_TOKEN_LIFETIME` en producción (hoy **8 h**) a varios días, para que
  al reconectar y sincronizar no tengan que volver a loguearse tras una jornada larga.
- "Login offline" para reabrir la app sin señal: perfil cacheado; el token solo se
  exige al sincronizar (online).

## 5. Seguridad (no negociable — datos de víctimas)

- Cifrado en reposo de todo el almacén local.
- Documentos **hasheados** en el padrón.
- Borrado de jornada/padrón al cerrar sesión, al cerrar jornada o tras N días.
- Auditoría de descargas (ya existe `LogAcceso`).

## 6. Fases

### Fase 0 — Plomería offline (AHORA, con el mock, sin depender de Oracle)
Construir y probar todo lo que **no** necesita los 10M reales:
- Búsqueda, selector de instrumento y paramétricas leyendo de **local**.
- Pre-carga al login (con los pocos del mock) + almacén cifrado.
- Ajuste del refresh token + no forzar logout offline.
- Validar el flujo **completo offline** end-to-end con el mock.

### Fase 1 — Padrón real (AL MIGRAR a Oracle/RUV)
- Generador del padrón desde Oracle + endpoints de descarga/versión.
- La app baja el padrón real (~150 MB) en el login.
- Verificación offline contra los 10M.

### Fase 2 — Robustez
- Refresco **incremental** del padrón (deltas, no 150 MB cada vez).
- Métricas de sincronización, resolución de conflictos, hardening de seguridad.

## 7. Dependencias

- **Oracle / RUV (OTI):** la Fase 1 necesita el acceso a los datos reales del RUV
  para generar el padrón. Hoy el backend usa el repositorio **mock** (11 registros).
  Ver pendientes con la OTI (acceso a datos + URL permanente). La Fase 0 se puede
  hacer ya, en paralelo, sin esperar a Oracle.
