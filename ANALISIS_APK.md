# Análisis Técnico — APK Encuestador Móvil SRNI
**Aplicación:** `co.com.rni.encuestadormovil` v4.1  
**Entidad:** Unidad para las Víctimas — Colombia  
**Propósito:** Caracterización de víctimas del conflicto armado (SRNI)  
**Fecha análisis:** 2026-04-09

---

## 1. Metadatos del APK

| Campo | Valor |
|-------|-------|
| Package | `co.com.rni.encuestadormovil` |
| Version | 4.1 |
| Min SDK | 9 (Android 2.3) |
| Target SDK | 28 (Android 9) |
| Compile SDK | 28 |
| Tamaño APK | ~787 MB |

---

## 2. Vulnerabilidades Críticas de Seguridad

### 2.1 CRÍTICO — 785 MB de datos de víctimas sin cifrar en el APK

La base de datos `assets/databases/dbencuestadormovil.db` (785.1 MB) contiene el **Registro Nacional de Información (RNI)** completo distribuido como asset estático del APK.

- **Formato:** SQLite sin cifrado (magic: `SQLite format 3`)
- **Estructura:** 11 tablas sharding de víctimas (`PERSONAS0` a `PERSONAS9` + `PERSONASA`)
- **Estimado:** ~9.4 millones de registros de víctimas

**Campos expuestos por persona:**
```
TIPO_DOC, DOCUMENTO, NOMBRE1, NOMBRE2, APELLIDO1, APELLIDO2,
F_NACIMIENTO, HV1–HV14 (hechos victimizantes), ESTADO, ENCUESTADO, FECHA_ENCUESTA
```

**Riesgo:** Cualquier persona con acceso físico al dispositivo, una copia del APK o un backup ADB puede extraer la identidad completa de 9.4 millones de personas vulnerables.

**Violación:** Art. 17 Ley 1581/2012 (deber de seguridad), Principio de seguridad Habeas Data.

---

### 2.2 CRÍTICO — Comunicación HTTP sin cifrado

```
usesCleartextTraffic = true
```

**Endpoints en texto plano (HTTP):**
```
http://herramientasrni1.unidadvictimas.gov.co/LoginRest/Autentica.svc/LoginPerfil/
http://herramientasrni1.unidadvictimas.gov.co/LoginRest/Autentica.svc/Logout/
http://herramientasrni1.unidadvictimas.gov.co/LoginRest/Autentica.svc/LogoutTemp/
http://herramientasrni1.unidadvictimas.gov.co/LoginRest/Autentica.svc/Valor/
```

**Riesgo:** Credenciales y tokens viajan en texto plano. Susceptible a ataques MITM en redes WiFi públicas o mediante puntos de acceso falsos, comunes en contextos de trabajo de campo.

**Tecnología backend:** WCF (Windows Communication Foundation) — SOAP/REST Microsoft, legacy.

---

### 2.3 CRÍTICO — Transferencia de BD via FTP sin TLS

```
ftp.unidadvictimas.gov.co
ftp.isegoria.co   ← servidor de desarrollo/tercero
```

La clase `asyncDownloadDBVivantoFTP` y `asyncUploadFile` sincronizan la base de datos completa de víctimas mediante FTP estándar (no FTPS/SFTP). Los archivos de encuestas completadas se suben sin cifrado.

---

### 2.4 ALTO — Contraseñas en texto plano

Tabla `EMCUSUARIOS` (vivanto.db):
```sql
CREATE TABLE EMCUSUARIOS (
  ID INTEGER PRIMARY KEY AUTOINCREMENT,
  ID_PERFIL TEXT, FECLOGIN TEXT, FECVALIDATOKEN TEXT,
  IDUSUARIO TEXT, NOMBRE_PERFIL TEXT, NOMBREUSUARIO TEXT,
  PASSWORD TEXT,        -- ← Texto plano
  TOKENUSUARIO TEXT,    -- ← Token sin expiración visible
  PCSENT TEXT
)
```

Sin hashing (bcrypt, PBKDF2, Argon2). Cualquier backup o dump de la BD expone todas las credenciales.

---

### 2.5 ALTO — Backup ADB habilitado

```xml
android:allowBackup="true"
```

Permite extraer toda la base de datos SQLite con un simple:
```bash
adb backup -noapk co.com.rni.encuestadormovil
```

No requiere root en Android < 9. En dispositivos de campo perdidos o robados, compromete todos los datos almacenados.

---

### 2.6 ALTO — Sin cifrado en reposo (SQLite)

- `dbencuestadormovil.db`: SQLite plano, sin SQLCipher
- `vivanto.db` / `vivanto.db.zip`: SQLite plano comprimido pero sin cifrar

---

### 2.7 MEDIO — Token sin mecanismo de expiración robusto

El campo `TOKENUSUARIO` es un string almacenado localmente. No se observa estructura JWT ni mecanismo de refresh/revocación. El campo `FECVALIDATOKEN` sugiere validación por fecha pero del lado del cliente.

---

### 2.8 MEDIO — Permisos excesivos

| Permiso | ¿Justificado? |
|---------|---------------|
| `ACCESS_FINE_LOCATION` | Podría justificarse para georreferenciación |
| `ACCESS_NETWORK_STATE` | Justificado |
| `INTERNET` | Justificado |
| `READ_EXTERNAL_STORAGE` | Justificado (archivos adjuntos) |
| `WRITE_EXTERNAL_STORAGE` | Justificado |
| `KILL_BACKGROUND_PROCESSES` | **No justificado** |
| `READ_CALENDAR` | **No justificado** |
| `WRITE_INTERNAL_STORAGE` | **No justificado** (no es permiso estándar) |

---

### 2.9 BAJO — Servidor de desarrollo tercero expuesto

El dominio `ftp.isegoria.co` (empresa de desarrollo) aparece como servidor FTP alternativo. Implica que datos de víctimas pueden estar transitando por infraestructura de terceros fuera del control estatal.

---

### 2.10 BAJO — Asset HTML de prueba embebido

El directorio `assets/www/` contiene un sitio HTML de tutorial (bextlan.com) con código de prueba SQLite Web. No tiene funcionalidad en producción pero aumenta la superficie de ataque y el tamaño del APK innecesariamente.

---

## 3. Arquitectura de la Aplicación Actual

### 3.1 Componentes principales (Activities)

| Clase | Función |
|-------|---------|
| `Login` | Autenticación contra WCF SOAP |
| `MainActivity` | Menú principal, resumen encuestas |
| `PersonasCardViewd` | Búsqueda y listado de víctimas del RNI |
| `conformarHogar` | Creación/gestión del hogar encuestado |
| `DiligenciarPregunta` | Motor de formulario dinámico (activity más compleja, 24+ clases internas) |
| `Parametricas` | Gestión de parámetros del instrumento |
| `Servicios` | Sincronización FTP, descarga/upload de BD |
| `resumen_encuestas_por_usuario` | Reporte por encuestador |
| `configuracionencuestas.AgregarTema` | Configuración de módulos |

### 3.2 Utilidades asíncronas (AsyncTask)

| Clase | Función |
|-------|---------|
| `asyncCargaVictimas` | Carga masiva del RNI a memoria |
| `asyncConsultarVictimas` | Búsqueda en la BD de víctimas |
| `asyncDownloadDBVivantoFTP` | Descarga vivanto.db desde FTP |
| `asyncUploadFile` | Sube encuestas al servidor FTP |
| `asyncValidateVersions` | Valida versión del instrumento |
| `asyncPrepararBD` | Inicializa la BD local |
| `asyncEncrypDecryp` | Cifrado/descifrado de archivos adjuntos |
| `asyncUpdateDBVivanto` | Actualiza instrumento desde servidor |
| `asyncAgregarNoIncluido` | Agrega persona no en el RNI |

### 3.3 ORM y acceso a datos

- **SugarORM** (deprecated, última versión 2017) para vivanto.db
- **SQLiteOpenHelper** directo para dbencuestadormovil.db
- Sin migraciones versionadas

---

## 4. Modelo de Datos (vivanto.db — Instrumento)

### Tablas identificadas

```
EMCUSUARIOS              — Encuestadores con credenciales
EMCTEMAS                 — 54 módulos del instrumento
EMCTEMAPERFILES          — Asignación de módulos por perfil
EMCPREGUNTAS             — Catálogo de preguntas
EMCPREGUNTASINSTRUMENTO  — Preguntas en instrumento (con orden, tipo, validadores)
EMCRESPUESTAS            — Opciones de respuesta por pregunta
EMCRESPUESTASINSTRUMENTO — Respuestas con reglas de habilitación/deshabilitación
EMCPREGUNTAHIJOS         — Preguntas condicionales (lógica de branching)
EMCPREGUNTASDERIVADAS    — Cola de preguntas pendientes por persona/hogar
EMCRESPUESTASENCUESTA    — Respuestas capturadas en campo
EMCHOGARES               — Hogares en proceso de caracterización
EMCMIEMBROSHOGAR         — Miembros del hogar
EMCPERSONAS              — Personas vinculadas (fuente externa)
EMCVICTIMAS              — Víctimas caracterizadas localmente
EMCMUNICIPIO             — Parametrica municipal (operadores, tipos)
EMCDEPARTAMENTO          — Departamentos
EMCVEREDAS               — 32,377 veredas (código DANE)
EMCCOMUNIDADESNEGRAS     — Comunidades negras/afro
EMCRESGUARDOSINDIGENAS   — Resguardos indígenas
EMCRUINOSASCATASTROFICAS — Enfermedades catastróficas/ruinosas
EMCDTPUNTOSATENCION      — Puntos de atención por DT
EMCRELACIONDTPUNTO       — Relación hogar-punto de atención
EMCCAPITULOSTERMINADOS   — Capítulos completados por hogar
EMCENCUESTASTERMINADAS   — Encuestas finalizadas
EMCRESUMENENCUESTASXUSUARIO — Resumen de productividad por encuestador
EMCVALIDADORESINSTRUMENTO  — Validadores a nivel de instrumento
EMCVALIDADORESRESPUESTA    — Condiciones de validación por respuesta
EMCVALIDADORESRESPUESTAINSTRUMENTO — Validadores cruzados
EMCVALIDADORESPERSONA      — Validadores específicos por persona
EMCVALIDADOREXPRESON       — Expresiones de validación complejas
EMCINSTRUMENTOVALIDADOR    — Configuración del validador
EMCVERSION                 — Control de versiones del instrumento
EMCADMONCOMBOS             — Queries para listas dinámicas (combos)
EMCSOPORTEJEFEHOGAR        — Documentos soporte del jefe de hogar
GIC_REPORTE_HOGARXRESPUESTA_V6 — Mapeo respuestas a campos de reporte
ITEMPERSONACARD            — Vista de tarjeta de persona (UI cache)
```

### Datos geográficos
- `veredas.csv` y `veredas2.csv`: 32,377 registros con código DANE (departamento, municipio, vereda)

---

## 5. Flujo de trabajo identificado

```
1. Login → Autenticación WCF HTTP
2. Descarga vivanto.db (instrumento) desde FTP si hay nueva versión
3. Búsqueda de víctima en dbencuestadormovil.db (785 MB local)
4. Conformar Hogar → asignar víctimas como miembros
5. DiligenciarPregunta → motor de formulario dinámico (54 módulos)
   - Preguntas condicionales según respuestas anteriores
   - Validaciones en tiempo real
   - Manejo de preguntas por hogar y por persona
6. Completar capítulos → marcar como terminados
7. Subir encuesta finalizada → FTP
```

---

## 6. Tecnologías Utilizadas

| Componente | Tecnología |
|-----------|------------|
| Lenguaje | Java (Android) |
| Min/Target SDK | 9 / 28 |
| ORM | SugarORM (deprecated) |
| BD local | SQLite (sin cifrar) |
| Red | Apache HTTP Client legacy |
| Imágenes | Glide |
| DI | — (ninguno) |
| CSV | OpenCSV |
| FTP | Apache Commons Net |
| Auth backend | WCF SOAP (Microsoft) |
| Mapa/Geo | — (no evidente) |

---

## 7. Resumen de hallazgos por severidad

| Severidad | Hallazgo |
|-----------|---------|
| CRÍTICO | 9.4M registros de víctimas sin cifrar en el APK |
| CRÍTICO | Comunicación HTTP sin TLS (cleartext) |
| CRÍTICO | Sincronización FTP sin cifrado |
| ALTO | Contraseñas en texto plano en SQLite |
| ALTO | `allowBackup=true` — extracción por ADB |
| ALTO | BD SQLite sin cifrado en reposo |
| MEDIO | Token sin expiración robusta |
| MEDIO | Permisos `READ_CALENDAR` y `KILL_BACKGROUND_PROCESSES` no justificados |
| BAJO | Servidor tercero `isegoria.co` en la cadena de datos |
| BAJO | HTML de tutorial embebido sin propósito funcional |
