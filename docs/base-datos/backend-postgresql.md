# Base de Datos Backend — PostgreSQL SRNI

**Motor:** PostgreSQL 16
**Extensiones:** `pgcrypto`, `uuid-ossp`
**ORM:** Django 5.2 + django-encrypted-model-fields
**Última actualización:** 2026-05-04

---

## Configuración inicial

```sql
-- Extensiones requeridas (ejecutar una sola vez como superusuario)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Usuario de aplicación (permisos mínimos — sin UPDATE/DELETE en auditoria)
CREATE USER srni_app WITH PASSWORD '<password-from-secrets>';
GRANT CONNECT ON DATABASE srni TO srni_app;
GRANT USAGE ON SCHEMA public TO srni_app;

-- Permisos estándar (todas las tablas excepto auditoria)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO srni_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO srni_app;

-- Revocar UPDATE/DELETE en la tabla de auditoría (inmutabilidad)
REVOKE UPDATE, DELETE ON TABLE auditoria_logacceso FROM srni_app;
```

---

## Diagrama de relaciones

```
parametricas_tipodocumento ──┐
parametricas_municipio ──────┤──► victimas_victima ──────────────┐
                             │         ↑                          │
parametricas_departamento ───┘         │ jefe_hogar               │
       ↑                         hogares_hogar ◄── hogares_miembrohogar
       │ FK                            ↑
parametricas_vereda                encuestas_sesionencuesta ──────► ia_consentimientoia
parametricas_comunidadnegra             ↑                          ia_sesion_ia
parametricas_resguardoindigena          │                          encuestas_respuestaencuesta
parametricas_puntoatencion         formulario_capitulo
                                        ↑
autenticacion_perfil ──► auth_usuario   │
                              ↑    formulario_instrumentoversion
                              │         ↑
                         auditoria_logacceso    formulario_perfil
                                        │
                              formulario_pregunta ──► formulario_opcionrespuesta
                                        │
                              formulario_reglaskiplogic
```

---

## 1. App `autenticacion`

### `autenticacion_perfil`

```sql
CREATE TABLE autenticacion_perfil (
    id                  SERIAL          PRIMARY KEY,
    codigo              VARCHAR(20)     NOT NULL UNIQUE,
    nombre              VARCHAR(100)    NOT NULL,
    puede_buscar_rni    BOOLEAN         NOT NULL DEFAULT TRUE,
    puede_caracterizar  BOOLEAN         NOT NULL DEFAULT TRUE,
    puede_ver_reportes  BOOLEAN         NOT NULL DEFAULT FALSE,
    puede_administrar   BOOLEAN         NOT NULL DEFAULT FALSE,
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Perfiles iniciales
INSERT INTO autenticacion_perfil (codigo, nombre, puede_ver_reportes, puede_administrar) VALUES
    ('ENCUESTADOR_CAMPO',  'Encuestador de campo',    FALSE, FALSE),
    ('COORDINADOR_DT',     'Coordinador Dirección Territorial', TRUE,  FALSE),
    ('SUPERVISOR',         'Supervisor',               TRUE,  FALSE),
    ('ADMINISTRADOR',      'Administrador',             TRUE,  TRUE);
```

### `auth_usuario`

```sql
CREATE TABLE auth_usuario (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_usuario      VARCHAR(50)     NOT NULL UNIQUE,   -- login username
    nombre_completo     VARCHAR(200)    NOT NULL,
    email               VARCHAR(254)    NOT NULL UNIQUE,
    password            VARCHAR(128)    NOT NULL,           -- Argon2 hash (Django)
    perfil_id           INTEGER         REFERENCES autenticacion_perfil(id) ON DELETE SET NULL,
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    es_admin            BOOLEAN         NOT NULL DEFAULT FALSE,  -- acceso /admin/
    fecha_ultimo_login  TIMESTAMPTZ,
    last_login          TIMESTAMPTZ,                        -- Django requerido
    is_superuser        BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usuario_codigo ON auth_usuario(codigo_usuario);
CREATE INDEX idx_usuario_perfil ON auth_usuario(perfil_id);
```

---

## 2. App `auditoria`

### `auditoria_logacceso` — INMUTABLE (sin UPDATE/DELETE desde app)

```sql
CREATE TABLE auditoria_logacceso (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID            REFERENCES auth_usuario(id) ON DELETE SET NULL,
    codigo_usuario  VARCHAR(50)     NOT NULL DEFAULT '',   -- preservado si el usuario es eliminado
    accion          VARCHAR(30)     NOT NULL,
    -- Valores: LOGIN | LOGOUT | LOGIN_FALLIDO | BUSQUEDA_RNI | VER_VICTIMA |
    --          CREAR_HOGAR | AGREGAR_MIEMBRO | RESPONDER_PREGUNTA | FINALIZAR_ENCUESTA |
    --          EXPORTAR | CAMBIO_PASSWORD | CAMBIO_USUARIO | ACCESO_DENEGADO |
    --          LLAMADA_GEMINI | CONSENTIMIENTO_IA
    recurso         VARCHAR(200)    NOT NULL DEFAULT '',
    recurso_id      VARCHAR(100)    NOT NULL DEFAULT '',
    ip_origen       INET            NOT NULL DEFAULT '0.0.0.0',
    user_agent      VARCHAR(500)    NOT NULL DEFAULT '',
    resultado       VARCHAR(10)     NOT NULL,    -- EXITO | DENEGADO | ERROR
    detalle         JSONB           NOT NULL DEFAULT '{}',
    timestamp       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Índices para consultas de auditoría
CREATE INDEX idx_log_codigo_ts  ON auditoria_logacceso(codigo_usuario, timestamp DESC);
CREATE INDEX idx_log_accion_ts  ON auditoria_logacceso(accion, timestamp DESC);
CREATE INDEX idx_log_resultado  ON auditoria_logacceso(resultado);
CREATE INDEX idx_log_recurso_id ON auditoria_logacceso(recurso_id);

-- NOTA: el usuario de app tiene REVOKE UPDATE, DELETE sobre esta tabla
```

---

## 3. App `parametricas`

```sql
CREATE TABLE parametricas_departamento (
    id          SERIAL          PRIMARY KEY,
    codigo_dane VARCHAR(2)      NOT NULL UNIQUE,    -- '05' = Antioquia
    nombre      VARCHAR(100)    NOT NULL,
    activo      BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE TABLE parametricas_municipio (
    id              SERIAL          PRIMARY KEY,
    codigo_dane     VARCHAR(5)      NOT NULL UNIQUE,   -- '05001' = Medellín
    nombre          VARCHAR(150)    NOT NULL,
    departamento_id INTEGER         NOT NULL REFERENCES parametricas_departamento(id),
    activo          BOOLEAN         NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_mun_dpto ON parametricas_municipio(departamento_id);

CREATE TABLE parametricas_vereda (
    id          SERIAL          PRIMARY KEY,
    codigo_dane VARCHAR(13)     NOT NULL,
    nombre      VARCHAR(200)    NOT NULL,
    municipio_id INTEGER        NOT NULL REFERENCES parametricas_municipio(id),
    activo      BOOLEAN         NOT NULL DEFAULT TRUE,
    UNIQUE (codigo_dane, municipio_id)
);
CREATE INDEX idx_vereda_mun ON parametricas_vereda(municipio_id);

CREATE TABLE parametricas_tipodocumento (
    id                  SERIAL          PRIMARY KEY,
    codigo              VARCHAR(10)     NOT NULL UNIQUE,  -- 'CC', 'TI', 'RC', 'CE', 'PA', 'NIT', 'NUIP', 'PEP'
    nombre              VARCHAR(100)    NOT NULL,
    aplica_nacionales   BOOLEAN         NOT NULL DEFAULT TRUE,
    aplica_extranjeros  BOOLEAN         NOT NULL DEFAULT FALSE,
    activo              BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE TABLE parametricas_comunidadnegra (
    id          SERIAL          PRIMARY KEY,
    codigo      VARCHAR(20)     NOT NULL UNIQUE,
    nombre      VARCHAR(200)    NOT NULL,
    municipio_id INTEGER        NOT NULL REFERENCES parametricas_municipio(id),
    activo      BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE TABLE parametricas_resguardoindigena (
    id          SERIAL          PRIMARY KEY,
    codigo      VARCHAR(20)     NOT NULL UNIQUE,
    nombre      VARCHAR(200)    NOT NULL,
    municipio_id INTEGER        NOT NULL REFERENCES parametricas_municipio(id),
    pueblo      VARCHAR(100)    NOT NULL DEFAULT '',
    activo      BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE TABLE parametricas_direccionterritorial (
    id      SERIAL          PRIMARY KEY,
    codigo  VARCHAR(10)     NOT NULL UNIQUE,
    nombre  VARCHAR(150)    NOT NULL,
    activo  BOOLEAN         NOT NULL DEFAULT TRUE
);

-- Relación M2M DireccionTerritorial ↔ Departamento
CREATE TABLE parametricas_direccionterritorial_departamentos (
    id                      SERIAL  PRIMARY KEY,
    direccionterritorial_id INTEGER NOT NULL REFERENCES parametricas_direccionterritorial(id),
    departamento_id         INTEGER NOT NULL REFERENCES parametricas_departamento(id),
    UNIQUE (direccionterritorial_id, departamento_id)
);

CREATE TABLE parametricas_puntoatencion (
    id                          SERIAL          PRIMARY KEY,
    codigo                      VARCHAR(20)     NOT NULL UNIQUE,
    nombre                      VARCHAR(200)    NOT NULL,
    direccion_territorial_id    INTEGER         NOT NULL REFERENCES parametricas_direccionterritorial(id),
    municipio_id                INTEGER         NOT NULL REFERENCES parametricas_municipio(id),
    direccion_fisica            VARCHAR(300)    NOT NULL DEFAULT '',
    activo                      BOOLEAN         NOT NULL DEFAULT TRUE
);
```

---

## 4. App `victimas`

```sql
-- NOTA: EncryptedField almacena el valor cifrado como TEXT (Fernet AES-128-CBC + HMAC)
-- La longitud real es mayor que el valor original por el overhead de cifrado + base64.

CREATE TABLE victimas_victima (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_documento_id       INTEGER         NOT NULL REFERENCES parametricas_tipodocumento(id),

    -- Campos PII cifrados con Fernet (python-cryptography)
    -- Formato en BD: base64(IV + ciphertext + HMAC) como TEXT
    numero_documento        TEXT            NOT NULL,    -- PII cifrado
    primer_nombre           TEXT            NOT NULL,    -- PII cifrado
    segundo_nombre          TEXT            NOT NULL DEFAULT '',  -- PII cifrado
    primer_apellido         TEXT            NOT NULL,    -- PII cifrado
    segundo_apellido        TEXT            NOT NULL DEFAULT '',  -- PII cifrado
    fecha_nacimiento        TEXT            NOT NULL,    -- PII cifrado

    -- Hash SHA-256 del numero_documento para búsquedas (NUNCA descifra para buscar)
    numero_documento_hash   VARCHAR(64)     NOT NULL,

    -- Datos demográficos sin PII directa
    genero                  VARCHAR(2)      NOT NULL,    -- M | F | NB | ND
    estado_civil            VARCHAR(15)     NOT NULL DEFAULT '',
    pertenencia_etnica      VARCHAR(20)     NOT NULL DEFAULT 'NINGUNA',
    pueblo_indigena         VARCHAR(150)    NOT NULL DEFAULT '',
    discapacidad            BOOLEAN         NOT NULL DEFAULT FALSE,
    tipo_discapacidad       VARCHAR(100)    NOT NULL DEFAULT '',

    -- Estado en el RUV
    estado_ruv              VARCHAR(15)     NOT NULL DEFAULT 'EN_PROCESO',
    -- INCLUIDO | NO_INCLUIDO | EN_PROCESO | EXCLUIDO

    -- Hechos victimizantes como array JSON
    hechos_victimizantes    JSONB           NOT NULL DEFAULT '[]',

    -- Ubicación actual
    municipio_residencia_id INTEGER         REFERENCES parametricas_municipio(id),

    -- Auditoría
    creado_por_id           UUID            REFERENCES auth_usuario(id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Índice principal de búsqueda (sin descifrar)
CREATE INDEX idx_victima_hash_tipodoc ON victimas_victima(numero_documento_hash, tipo_documento_id);
CREATE INDEX idx_victima_ruv_etnia    ON victimas_victima(estado_ruv, pertenencia_etnica);
CREATE INDEX idx_victima_genero       ON victimas_victima(genero);
```

---

## 5. App `formulario`

```sql
CREATE TABLE formulario_perfil (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo      VARCHAR(30)     NOT NULL UNIQUE,   -- TERRITORIAL, BUENAVENTURA, SAN_ANDRES...
    nombre      VARCHAR(150)    NOT NULL,
    activo      BOOLEAN         NOT NULL DEFAULT TRUE,
    creado      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    actualizado TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE formulario_instrumentoversion (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    perfil_id           UUID            NOT NULL REFERENCES formulario_perfil(id),
    numero              VARCHAR(20)     NOT NULL,   -- 'V7', 'V8', 'V8.1'
    vigente_desde       DATE            NOT NULL,
    vigente_hasta       DATE,
    fuente_documental   VARCHAR(300)    NOT NULL DEFAULT '',
    creado              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (perfil_id, numero)
);

CREATE TABLE formulario_capitulo (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    instrumento_id      UUID            NOT NULL REFERENCES formulario_instrumentoversion(id) ON DELETE CASCADE,
    codigo              VARCHAR(10)     NOT NULL,   -- 'A', 'B', 'C'...
    nombre              VARCHAR(200)    NOT NULL,
    orden               SMALLINT        NOT NULL,
    nivel               VARCHAR(10)     NOT NULL DEFAULT 'HOGAR',  -- HOGAR | PERSONA
    objetivo            TEXT            NOT NULL DEFAULT '',
    poblacion_objetivo  VARCHAR(50)     NOT NULL DEFAULT 'TODOS_MIEMBROS',
    aplicabilidad       JSONB           NOT NULL DEFAULT '{}',
    UNIQUE (instrumento_id, codigo)
);
CREATE INDEX idx_capitulo_instrumento ON formulario_capitulo(instrumento_id, orden);

CREATE TABLE formulario_pregunta (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    capitulo_id         UUID            NOT NULL REFERENCES formulario_capitulo(id) ON DELETE CASCADE,
    codigo_externo      VARCHAR(40)     NOT NULL,   -- 'C1', 'B9_tel', 'Z3', 'DT_ATENCION'
    no_pregunta         VARCHAR(10)     NOT NULL DEFAULT '',
    id_preg             INTEGER,                    -- ID_PREG del Diccionario UARIV para VIVANTO
    variable_bd         VARCHAR(50)     NOT NULL,
    texto               TEXT            NOT NULL,
    descripcion_ayuda   TEXT            NOT NULL DEFAULT '',
    tipo                VARCHAR(20)     NOT NULL,
    -- TEXTO | TEXTO_LARGO | NUMERICO | FECHA | BOOLEAN | RADIO | LISTA | LISTA_MULTIPLE | COMBO_DINAMICO
    nivel               VARCHAR(10)     NOT NULL,   -- HOGAR | PERSONA
    obligatoria         BOOLEAN         NOT NULL DEFAULT TRUE,
    orden               SMALLINT        NOT NULL,
    es_precargada       BOOLEAN         NOT NULL DEFAULT FALSE,
    fuente_precarga     VARCHAR(60)     NOT NULL DEFAULT '',
    validaciones        JSONB           NOT NULL DEFAULT '{}',
    activa              BOOLEAN         NOT NULL DEFAULT TRUE,
    UNIQUE (capitulo_id, codigo_externo)
);
CREATE INDEX idx_pregunta_codigo    ON formulario_pregunta(codigo_externo);
CREATE INDEX idx_pregunta_no        ON formulario_pregunta(no_pregunta);
CREATE INDEX idx_pregunta_id_preg   ON formulario_pregunta(id_preg);
CREATE INDEX idx_pregunta_cap_orden ON formulario_pregunta(capitulo_id, orden);

CREATE TABLE formulario_opcionrespuesta (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    pregunta_id         UUID            NOT NULL REFERENCES formulario_pregunta(id) ON DELETE CASCADE,
    valor               VARCHAR(100)    NOT NULL,
    etiqueta            VARCHAR(500)    NOT NULL,
    id_resp_vivanto     INTEGER,       -- ID_RESP del Diccionario V8 para export VIVANTO
    orden               SMALLINT        NOT NULL,
    finaliza_capitulo   BOOLEAN         NOT NULL DEFAULT FALSE,  -- equivale RESFINALIZA del APK
    UNIQUE (pregunta_id, valor)
);
CREATE INDEX idx_opcion_vivanto ON formulario_opcionrespuesta(id_resp_vivanto);

CREATE TABLE formulario_reglaskiplogic (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    instrumento_id          UUID            NOT NULL REFERENCES formulario_instrumentoversion(id) ON DELETE CASCADE,
    pregunta_origen_id      UUID            REFERENCES formulario_pregunta(id) ON DELETE CASCADE,
    expresion_origen        TEXT            NOT NULL DEFAULT '',
    -- Ej: 'sexo == "Hombre" and 18 <= edad <= 49'
    valor_trigger           VARCHAR(100)    NOT NULL DEFAULT '',
    pregunta_afectada_id    UUID            REFERENCES formulario_pregunta(id) ON DELETE CASCADE,
    capitulo_afectado_id    UUID            REFERENCES formulario_capitulo(id) ON DELETE CASCADE,
    accion                  VARCHAR(20)     NOT NULL,
    -- HABILITAR | DESHABILITAR | OBLIGAR | FINALIZAR
    descripcion             VARCHAR(300)    NOT NULL DEFAULT ''
);
```

---

## 6. App `hogares`

```sql
CREATE TABLE hogares_hogar (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    jefe_hogar_id       UUID            NOT NULL REFERENCES victimas_victima(id),
    municipio_id        INTEGER         REFERENCES parametricas_municipio(id),
    tipo_vivienda       VARCHAR(15)     NOT NULL DEFAULT '',
    -- CASA | APARTAMENTO | CUARTO | CAMBUCHE | CONTENEDOR | OTRO
    condicion_ocupacion VARCHAR(20)     NOT NULL DEFAULT '',
    -- PROPIA | PROPIA_PAGANDO | ARRIENDO | FAMILIAR | INVASION | OTRO
    estrato             SMALLINT        NOT NULL DEFAULT 0,
    numero_cuartos      SMALLINT        NOT NULL DEFAULT 0,
    numero_personas     SMALLINT        NOT NULL DEFAULT 1,
    estado              VARCHAR(10)     NOT NULL DEFAULT 'BORRADOR',  -- BORRADOR | ACTIVO | ARCHIVADO
    observaciones       TEXT            NOT NULL DEFAULT '',
    creado_por_id       UUID            REFERENCES auth_usuario(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hogar_estado_creador ON hogares_hogar(estado, creado_por_id);
CREATE INDEX idx_hogar_jefe           ON hogares_hogar(jefe_hogar_id, estado);

CREATE TABLE hogares_miembrohogar (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    hogar_id                UUID            NOT NULL REFERENCES hogares_hogar(id) ON DELETE CASCADE,
    victima_id              UUID            REFERENCES victimas_victima(id) ON DELETE SET NULL,

    -- Datos básicos cifrados para miembros NO registrados en el RNI
    nombre_completo         TEXT            NOT NULL DEFAULT '',   -- PII cifrado (Fernet)
    tipo_documento_id       INTEGER         REFERENCES parametricas_tipodocumento(id),
    numero_documento        TEXT            NOT NULL DEFAULT '',   -- PII cifrado (Fernet)

    parentesco              VARCHAR(20)     NOT NULL,
    -- JEFE | CONYUGE | HIJO_A | YERNO_NUERA | NIETO_A | PADRE_MADRE | HERMANO_A | OTRO_PARIENTE | NO_PARIENTE
    genero                  VARCHAR(2)      NOT NULL DEFAULT '',   -- M | F | NB | ND
    fecha_nacimiento        DATE,                                  -- PII — no indexado
    tipo_persona            VARCHAR(15)     NOT NULL DEFAULT 'OTRO',
    -- AUTORIZADO | TUTOR | CUIDADOR | OTRO
    incluido_ruv            BOOLEAN         NOT NULL DEFAULT FALSE,
    tiene_discapacidad      BOOLEAN         NOT NULL DEFAULT FALSE,
    tiene_enfermedad_ruinosa BOOLEAN        NOT NULL DEFAULT FALSE,
    tipo_discapacidad       VARCHAR(100)    NOT NULL DEFAULT '',
    creado_por_id           UUID            REFERENCES auth_usuario(id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
```

---

## 7. App `encuestas`

```sql
CREATE TABLE encuestas_sesionencuesta (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    hogar_id                UUID            NOT NULL REFERENCES hogares_hogar(id),
    instrumento_id          UUID            NOT NULL REFERENCES formulario_instrumentoversion(id),
    encuestador_id          UUID            REFERENCES auth_usuario(id) ON DELETE SET NULL,
    estado                  VARCHAR(15)     NOT NULL DEFAULT 'INICIADA',
    -- INICIADA | EN_PROGRESO | COMPLETADA | SUSPENDIDA
    porcentaje_completado   SMALLINT        NOT NULL DEFAULT 0,
    fecha_inicio            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_fin               TIMESTAMPTZ,
    observaciones           TEXT            NOT NULL DEFAULT '',
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sesion_hogar_estado       ON encuestas_sesionencuesta(hogar_id, estado);
CREATE INDEX idx_sesion_encuestador_estado ON encuestas_sesionencuesta(encuestador_id, estado);

CREATE TABLE encuestas_respuestaencuesta (
    id          BIGSERIAL       PRIMARY KEY,
    sesion_id   UUID            NOT NULL REFERENCES encuestas_sesionencuesta(id) ON DELETE CASCADE,
    pregunta_id UUID            NOT NULL REFERENCES formulario_pregunta(id),
    valor       TEXT            NOT NULL DEFAULT '',
    -- OPCION_UNICA: 'A' / OPCION_MULTIPLE: '["A","B"]' / BOOLEAN: 'true'
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (sesion_id, pregunta_id)   -- upsert constraint
);

CREATE INDEX idx_respuesta_sesion ON encuestas_respuestaencuesta(sesion_id);
```

---

## 8. App `ia`

```sql
CREATE TABLE ia_consentimientoia (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    sesion_encuesta_id  UUID            NOT NULL REFERENCES encuestas_sesionencuesta(id) ON DELETE CASCADE,
    encuestador_id      UUID            REFERENCES auth_usuario(id) ON DELETE SET NULL,
    acepto              BOOLEAN         NOT NULL DEFAULT FALSE,
    -- SHA-256(sesion_id + timestamp) — prueba inmutable de consentimiento
    firma_digital       VARCHAR(64)     NOT NULL DEFAULT '',
    creado_en           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_consent_sesion_acepto ON ia_consentimientoia(sesion_encuesta_id, acepto);
CREATE INDEX idx_consent_encuestador   ON ia_consentimientoia(encuestador_id, creado_en DESC);

CREATE TABLE ia_sesion_ia (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    -- OneToOne con SesionEncuesta
    sesion_encuesta_id  UUID            NOT NULL UNIQUE REFERENCES encuestas_sesionencuesta(id) ON DELETE CASCADE,
    inicio              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fin                 TIMESTAMPTZ,
    total_llamadas      INTEGER         NOT NULL DEFAULT 0,
    -- SHA-256 de la transcripción acumulada — SOLO para auditoría (sin texto real)
    transcripcion_hash  VARCHAR(64)     NOT NULL DEFAULT ''
);
```

---

## 9. Tablas Django internas (generadas automáticamente)

```sql
-- SimpleJWT blacklist (tokens revocados)
CREATE TABLE token_blacklist_outstandingtoken (
    id          BIGSERIAL   PRIMARY KEY,
    user_id     UUID        REFERENCES auth_usuario(id),
    jti         VARCHAR(255) NOT NULL UNIQUE,
    token       TEXT        NOT NULL,
    created_at  TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE token_blacklist_blacklistedtoken (
    id              BIGSERIAL   PRIMARY KEY,
    token_id        BIGINT      NOT NULL UNIQUE REFERENCES token_blacklist_outstandingtoken(id),
    blacklisted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Permisos Django (requeridos por AbstractBaseUser + PermissionsMixin)
-- django_content_type, auth_permission, auth_usuario_user_permissions,
-- auth_usuario_groups, django_admin_log (generadas por Django migrations)
```

---

## 10. Volcado y backup seguro

```bash
# Backup cifrado con GPG (producción)
pg_dump srni \
  --format=custom \
  --no-acl \
  --no-owner \
  | gpg --encrypt --recipient admin@srni.gov.co \
  > backup_srni_$(date +%Y%m%d).dump.gpg

# Restaurar
gpg --decrypt backup_srni_20260504.dump.gpg \
  | pg_restore --dbname=srni --format=custom

# Verificar extensiones activas
SELECT extname, extversion FROM pg_extension;

# Verificar permisos de srni_app sobre auditoria_logacceso
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name = 'auditoria_logacceso' AND grantee = 'srni_app';
-- Debe aparecer: SELECT, INSERT — NO Update, DELETE
```
