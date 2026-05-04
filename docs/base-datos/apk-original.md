# Base de Datos APK Original — co.com.rni.encuestadormovil v4.1

**Motor:** SQLite (sin cifrado)
**Fuente:** Análisis técnico del APK — `ANALISIS_APK.md`
**Fecha análisis:** 2026-04-09

> **ADVERTENCIA:** Esta documentación describe el sistema ANTERIOR con sus fallas de seguridad.
> Se registra como referencia histórica y para garantizar la paridad funcional del sistema nuevo.

---

## Archivos SQLite en el APK

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `assets/databases/dbencuestadormovil.db` | 785 MB | RNI completo — 9.4M víctimas **sin cifrar** |
| `assets/databases/vivanto.db` | 3.2 MB | Instrumento de formularios — 37 tablas |

---

## 1. `dbencuestadormovil.db` — Registro de Víctimas (RNI)

### 1.1 Estructura — tablas PERSONAS (sharding por índice)

El APK divide las ~9.4M víctimas en 11 tablas para optimizar SQLite:

```sql
-- Se repite como PERSONAS0, PERSONAS1, ..., PERSONAS9, PERSONASA
CREATE TABLE PERSONAS0 (
    TIPO_DOC        TEXT,            -- Tipo de documento (CC, TI, RC...)
    DOCUMENTO       TEXT,            -- Número de documento EN TEXTO PLANO ← falla crítica
    NOMBRE1         TEXT,            -- Primer nombre EN TEXTO PLANO ← falla crítica
    NOMBRE2         TEXT,            -- Segundo nombre EN TEXTO PLANO
    APELLIDO1       TEXT,            -- Primer apellido EN TEXTO PLANO ← falla crítica
    APELLIDO2       TEXT,            -- Segundo apellido EN TEXTO PLANO
    F_NACIMIENTO    TEXT,            -- Fecha de nacimiento EN TEXTO PLANO ← falla crítica
    HV1             TEXT,            -- Hecho victimizante 1
    HV2             TEXT,            -- Hecho victimizante 2
    HV3             TEXT,
    HV4             TEXT,
    HV5             TEXT,
    HV6             TEXT,
    HV7             TEXT,
    HV8             TEXT,
    HV9             TEXT,
    HV10            TEXT,
    HV11            TEXT,
    HV12            TEXT,
    HV13            TEXT,
    HV14            TEXT,
    ESTADO          TEXT,            -- INCLUIDO / NO_INCLUIDO / EN_PROCESO
    ENCUESTADO      TEXT,            -- 0 / 1
    FECHA_ENCUESTA  TEXT             -- Fecha última encuesta
);
-- Sin PRIMARY KEY declarado
-- Sin índices (consulta secuencial sobre 785 MB)
```

**Fallas de seguridad:**
- PII completo (nombre, documento, fecha nacimiento) en texto plano en el dispositivo
- Sin índices → consultas lentas en ~900,000 registros por tabla
- Sin cifrado del archivo SQLite
- Distribuido como asset estático del APK (descargable con `apktool`)

---

## 2. `vivanto.db` — Instrumento de Formularios

### 2.1 Tablas principales

#### EMCUSUARIOS — Usuarios del sistema

```sql
CREATE TABLE EMCUSUARIOS (
    ID              INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_PERFIL       TEXT,            -- Código del perfil
    FECLOGIN        TEXT,            -- Fecha último login (TEXT, sin tipo DATE)
    FECVALIDATOKEN  TEXT,            -- Fecha validación del token
    IDUSUARIO       TEXT,            -- Username (equivale a codigo_usuario)
    NOMBRE_PERFIL   TEXT,            -- Nombre del perfil
    NOMBREUSUARIO   TEXT,            -- Nombre completo del encuestador
    PASSWORD        TEXT,            -- ← TEXTO PLANO, sin ningún hash
    TOKENUSUARIO    TEXT,            -- Token de sesión SIN expiración
    PCSENT          TEXT             -- Nombre del PC / dispositivo
);
```

**Fallas:** contraseña sin hash, token sin TTL, ID entero predecible.

#### EMCTEMAS — Módulos del formulario (equivale a Capitulo)

```sql
CREATE TABLE EMCTEMAS (
    ID_TEMA         INTEGER PRIMARY KEY AUTOINCREMENT,
    IDTEMA          TEXT,            -- Código legible: 'A', 'B', 'C'...
    NOMBRE_TEMA     TEXT,            -- Nombre del capítulo
    ORDEN           INTEGER,
    ACTIVO          INTEGER          -- 0/1
);
```

#### EMCPREGUNTASINSTRUMENTO — Preguntas del formulario

```sql
CREATE TABLE EMCPREGUNTASINSTRUMENTO (
    ID_PREG         INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_TEMA         INTEGER,         -- FK a EMCTEMAS
    CODIGO_PREG     TEXT,            -- Código variable (ej: C1, B9, Z3)
    TEXTO_PREG      TEXT,            -- Pregunta literal
    TIPO_RESPUESTA  TEXT,            -- TEXTO | NUMERICO | FECHA | LISTA | LISTA_MULTIPLE | RADIO | BOOLEAN
    ORDEN           INTEGER,
    OBLIGATORIO     INTEGER,         -- 0/1
    ACTIVA          INTEGER,         -- 0/1
    PREDEPENDE      TEXT,            -- Código de pregunta de la que depende
    VALOR_PREDEPENDE TEXT,           -- Valor que debe tener PREDEPENDE para mostrar esta
    RESHABILITA     TEXT,            -- Pregunta que ESTA respuesta habilita
    RESFINALIZA     TEXT             -- Si se responde, finaliza el capítulo
);
```

#### EMCOPCIONESRESPUESTA — Opciones de respuesta

```sql
CREATE TABLE EMCOPCIONESRESPUESTA (
    ID_OPCION       INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_PREG         INTEGER,         -- FK a EMCPREGUNTASINSTRUMENTO
    VALOR_OPCION    TEXT,
    TEXTO_OPCION    TEXT,
    ORDEN           INTEGER,
    ID_RESP         INTEGER          -- ID del Diccionario VIVANTO para exportación
);
```

#### EMCRESPUESTAS — Respuestas guardadas en dispositivo

```sql
CREATE TABLE EMCRESPUESTAS (
    ID_RESP         INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_HOGAR        INTEGER,         -- Identificador del hogar (entero secuencial)
    ID_PREG         INTEGER,         -- FK a EMCPREGUNTASINSTRUMENTO
    VALOR           TEXT,            -- Respuesta almacenada
    FECHA_RESP      TEXT
);
```

#### EMCHOGAR — Hogares

```sql
CREATE TABLE EMCHOGAR (
    ID_HOGAR        INTEGER PRIMARY KEY AUTOINCREMENT,  -- Predecible, sin UUID
    TIPO_DOC        TEXT,
    DOCUMENTO       TEXT,            -- Documento jefe hogar EN TEXTO PLANO
    NOMBRE          TEXT,            -- Nombre jefe hogar EN TEXTO PLANO
    MUNICIPIO       TEXT,
    TIPO_VIVIENDA   TEXT,
    ESTRATO         INTEGER,
    ESTADO          TEXT             -- BORRADOR / COMPLETADO
);
```

### 2.2 Tablas paramétricas del APK

```sql
CREATE TABLE EMCDEPARTAMENTOS (IDDPTO INTEGER PRIMARY KEY, NOMDPTO TEXT);
CREATE TABLE EMCMUNICIPIOS (IDMUN INTEGER, DPTO INTEGER, NOMMUN TEXT, PRIMARY KEY(IDMUN, DPTO));
CREATE TABLE EMCVEREDAS (IDVEREDA INTEGER, IDMUN INTEGER, IDDEPTO INTEGER, NOMVEREDA TEXT);
CREATE TABLE EMCTIPODOCUMENTO (IDTIPODOC TEXT PRIMARY KEY, NOMTIPODOC TEXT);
CREATE TABLE EMCRESGUARDOS (IDRESG INTEGER PRIMARY KEY, NOMRESG TEXT, IDMUN INTEGER);
CREATE TABLE EMCCOMUNIDADESNEGRAS (IDCOM INTEGER PRIMARY KEY, NOMCOM TEXT, IDMUN INTEGER);
```

---

## 3. Sincronización original (FTP)

El APK usaba estas clases para sincronizar datos de campo:

```java
// Subida de encuestas completadas — FTP sin cifrado
asyncUploadFile.execute("ftp://ftp.isegoria.co/encuestas/", archivoLocal);

// Descarga de actualizaciones del instrumento
asyncDownloadDBVivantoFTP.execute("ftp://ftp.unidadvictimas.gov.co/vivanto.db");
```

**Fallas:** FTP plano (sin TLS), subida a servidor de empresa tercera (`isegoria.co`).

---

## 4. Correspondencia con el sistema nuevo

| Tabla APK (vivanto.db) | Tabla SRNI nuevo | Diferencia principal |
|------------------------|------------------|---------------------|
| `EMCUSUARIOS` | `auth_usuario` | Argon2, JWT, UUID PK |
| `EMCTEMAS` | `formulario_capitulo` | FK a InstrumentoVersion |
| `EMCPREGUNTASINSTRUMENTO` | `formulario_pregunta` | Tipos tipados, skip logic separado |
| `EMCOPCIONESRESPUESTA` | `formulario_opcionrespuesta` | `id_resp_vivanto` para compatibilidad export |
| `EMCRESPUESTAS` | `encuestas_respuestaencuesta` | FK a sesión + pregunta, upsert |
| `EMCHOGAR` | `hogares_hogar` | UUID, FK Victima, PII cifrado |
| `PERSONAS0..PERSONASA` | `victimas_victima` | Solo en servidor, AES-256 |
| `EMCDEPARTAMENTOS` | `parametricas_departamento` | Código DANE normalizado |
| `EMCMUNICIPIOS` | `parametricas_municipio` | FK a departamento |
