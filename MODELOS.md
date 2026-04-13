# Modelos de Base de Datos — SRNI Web
**Motor:** PostgreSQL 16 + pgcrypto  
**ORM:** Django ORM  
**Fecha:** 2026-04-09

---

## Convenciones

- `EncryptedCharField` / `EncryptedTextField` = campo cifrado con `django-encrypted-model-fields` (pgcrypto AES-256)
- `created_at` / `updated_at` presentes en todos los modelos
- `created_by` FK a Usuario en modelos con datos capturados
- Todos los modelos heredan de `AuditableModel` para registro automático de cambios

---

## 1. Autenticación y Control de Acceso

### 1.1 Usuario (Encuestador)

```python
class Usuario(AbstractBaseUser, PermissionsMixin):
    """Reemplaza EMCUSUARIOS. Sin contraseña en texto plano."""
    id = UUIDField(primary_key=True, default=uuid4)
    codigo_usuario = CharField(max_length=50, unique=True)   # IDUSUARIO
    nombre_completo = CharField(max_length=200)               # NOMBREUSUARIO
    email = EmailField(unique=True)
    perfil = ForeignKey('Perfil', on_delete=PROTECT)          # ID_PERFIL
    activo = BooleanField(default=True)
    # password → Django gestiona hash Argon2 (NUNCA texto plano)
    # token → reemplazado por JWT + blacklist
    fecha_ultimo_login = DateTimeField(null=True)
    punto_atencion = ForeignKey('PuntoAtencion', null=True, on_delete=SET_NULL)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 1.2 Perfil

```python
class Perfil(Model):
    """Tipos de encuestador con permisos diferenciados."""
    codigo = CharField(max_length=20, unique=True)  # PERIDPERFIL
    nombre = CharField(max_length=100)               # NOMBRE_PERFIL
    puede_buscar_rni = BooleanField(default=True)
    puede_caracterizar = BooleanField(default=True)
    puede_ver_reportes = BooleanField(default=False)
    puede_administrar = BooleanField(default=False)
    activo = BooleanField(default=True)
```

### 1.3 TokenBlacklist (Revocación JWT)

```python
class TokenBlacklist(Model):
    """Tokens revocados (logout, expiración forzada)."""
    jti = CharField(max_length=255, unique=True, db_index=True)  # JWT ID
    usuario = ForeignKey(Usuario, on_delete=CASCADE)
    revocado_en = DateTimeField(auto_now_add=True)
    motivo = CharField(max_length=50)  # logout, sesion_expirada, cambio_password
    
    class Meta:
        indexes = [Index(fields=['jti'])]
```

---

## 2. Registro Nacional de Información (RNI)

### 2.1 Víctima

```python
class Victima(AuditableModel):
    """
    Reemplaza las 11 tablas PERSONAS0-9 + PERSONASA.
    Campos PII cifrados en reposo.
    """
    id = UUIDField(primary_key=True, default=uuid4)
    
    # Identificación — CIFRADOS
    tipo_documento = CharField(max_length=5, db_index=True)   # TIPO_DOC
    numero_documento = EncryptedCharField(max_length=30)       # DOCUMENTO
    numero_documento_hash = CharField(max_length=64, db_index=True)  # SHA-256 para búsqueda
    
    # Nombres — CIFRADOS
    primer_nombre = EncryptedCharField(max_length=100)          # NOMBRE1
    segundo_nombre = EncryptedCharField(max_length=100, blank=True)
    primer_apellido = EncryptedCharField(max_length=100)        # APELLIDO1
    segundo_apellido = EncryptedCharField(max_length=100, blank=True)
    
    # Datos básicos — CIFRADOS
    fecha_nacimiento = EncryptedCharField(max_length=20, blank=True)  # F_NACIMIENTO
    
    # Hechos victimizantes (HV1-HV14) — índices de hechos victimizantes del RUPD
    hechos_victimizantes = JSONField(default=list)  # [1,3,7,...] → reemplaza HV1..HV14
    
    # Estado en el proceso
    estado = CharField(max_length=20, db_index=True)  # ESTADO
    encuestado = BooleanField(default=False)           # ENCUESTADO
    fecha_encuesta = DateField(null=True)               # FECHA_ENCUESTA
    
    # Metadatos de origen
    id_declaracion = CharField(max_length=50, blank=True)  # PERIDDECLARACION
    id_siniestro = CharField(max_length=50, blank=True)    # PERIDSINIESTRO
    fuente = CharField(max_length=50, blank=True)           # PERFUENTE
    tipo_victima = CharField(max_length=20, blank=True)     # PERTIPOVICTIMA
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            Index(fields=['tipo_documento', 'numero_documento_hash']),
            Index(fields=['estado']),
            Index(fields=['encuestado']),
        ]
        # La búsqueda por nombre usa Full-Text Search en campos cifrados
        # via un índice sobre campos desencriptados en vista materializada
        # (actualizada por trigger, acceso restringido)
```

---

## 3. Instrumento de Caracterización (Motor de Formulario)

### 3.1 Instrumento

```python
class Instrumento(Model):
    """Versión del instrumento de caracterización."""
    id = PositiveIntegerField(primary_key=True)   # INSIDINSTRUMENTO
    nombre = CharField(max_length=200)
    version = CharField(max_length=20)             # VERVERSION
    activo = BooleanField(default=True)
    fecha_publicacion = DateField()
    created_at = DateTimeField(auto_now_add=True)
```

### 3.2 Tema / Módulo

```python
class Tema(Model):
    """
    54 módulos del instrumento. Reemplaza EMCTEMAS.
    Ej: 'Datos del Hogar', 'Hechos Victimizantes', 'Salud', etc.
    """
    id = PositiveIntegerField(primary_key=True)   # TEMIDTEMA
    nombre = CharField(max_length=200)             # TEMNOMBRETEMA
    orden = PositiveIntegerField()                 # TEMORDEN
    activo = BooleanField(default=True)            # TEMACTIVO
    instrumento = ForeignKey(Instrumento, on_delete=CASCADE)
    created_by = CharField(max_length=100, blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

### 3.3 TemaPerfilAcceso

```python
class TemaPerfilAcceso(Model):
    """Qué módulos puede ver cada perfil. Reemplaza EMCTEMAPERFILES."""
    tema = ForeignKey(Tema, on_delete=CASCADE)
    perfil = ForeignKey(Perfil, on_delete=CASCADE)
    
    class Meta:
        unique_together = [['tema', 'perfil']]
```

### 3.4 Pregunta

```python
class Pregunta(Model):
    """Catálogo maestro de preguntas. Reemplaza EMCPREGUNTAS."""
    id = CharField(max_length=20, primary_key=True)   # PREIDPREGUNTA
    texto = TextField()                                 # PREPREGUNTA
    observacion = TextField(blank=True)                # PREOBSERVACION
    activa = BooleanField(default=True)                # PREACTIVA
    created_by = CharField(max_length=100, blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

### 3.5 PreguntaInstrumento

```python
class PreguntaInstrumento(Model):
    """
    Pregunta dentro de un instrumento con configuración.
    Reemplaza EMCPREGUNTASINSTRUMENTO (~1416 preguntas).
    """
    instrumento = ForeignKey(Instrumento, on_delete=CASCADE)
    pregunta = ForeignKey(Pregunta, on_delete=CASCADE)
    tema = ForeignKey(Tema, on_delete=CASCADE)
    
    orden = PositiveIntegerField()                  # IXPORDEN
    tipo_campo = CharField(max_length=30)           # PRETIPOCAMPO: TEXTO, NUMERICO, LISTA...
    tipo_pregunta = CharField(max_length=30)        # PRETIPOPREGUNTA: HOGAR, PERSONA, GENERAL
    activa = BooleanField(default=True)
    
    # Dependencias y condicionales
    pregunta_padre = ForeignKey('self', null=True, blank=True, on_delete=SET_NULL)  # PREDEPENDE
    valor_default = CharField(max_length=100, blank=True)  # RDEFUALT
    
    # Validación
    validador_dato = CharField(max_length=50, blank=True)  # VALIDVALIDADORDATO
    validador_max = CharField(max_length=50, blank=True)   # PREVALIDADORMAX
    validador_min = CharField(max_length=50, blank=True)   # PREVALIDADORMIN
    longitud_campo = PositiveIntegerField(null=True)        # PRELONGCAMPO
    
    # Flags especiales
    aplica_todo_hogar = BooleanField(default=False)          # VALTODOHOGAR equivalente
    es_pregunta_general = BooleanField(default=False)        # VALPREGGENERAL
    respuesta_multiple = BooleanField(default=False)         # VALRESPUESTAMULTIPLE
    diferenciado = BooleanField(default=False)               # VALDIFERENCIADO
    diferenciado_nu = BooleanField(default=False)            # VALDIFERENCIADONU
    
    created_by = CharField(max_length=100, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['instrumento', 'pregunta']]
        indexes = [
            Index(fields=['instrumento', 'tema', 'orden']),
            Index(fields=['pregunta_padre']),
        ]
```

### 3.6 Respuesta (Opción de respuesta)

```python
class Respuesta(Model):
    """Opciones de respuesta para preguntas de lista. Reemplaza EMCRESPUESTAS."""
    id = CharField(max_length=20, primary_key=True)     # RESIDRESPUESTA
    pregunta = ForeignKey(Pregunta, on_delete=CASCADE)  # PREIDPREGUNTA
    texto = CharField(max_length=500)                    # RESRESPUESTA
    activa = BooleanField(default=True)                  # RESACTIVA
    orden = PositiveIntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['orden']
```

### 3.7 RespuestaInstrumento

```python
class RespuestaInstrumento(Model):
    """
    Respuesta con comportamiento en instrumento.
    Reemplaza EMCRESPUESTASINSTRUMENTO.
    """
    instrumento = ForeignKey(Instrumento, on_delete=CASCADE)
    respuesta = ForeignKey(Respuesta, on_delete=CASCADE)
    
    orden = PositiveIntegerField(default=0)              # RESORDENRESPUESTA
    es_obligatoria = BooleanField(default=False)         # RESOBLIGATORIO
    es_padre = CharField(max_length=20, blank=True)      # RESPADRE
    finaliza_modulo = BooleanField(default=False)        # RESFINALIZA
    habilita = CharField(max_length=200, blank=True)     # RESHABILITA
    respuestas_habilitar = TextField(blank=True)         # RESRESPUESTASHBILITAR
    autocompletar = BooleanField(default=False)          # RESAUTOCOMPLETAR
    texto_campo = TextField(blank=True)                  # PRECAMPOTEX
    
    # Validadores
    validador = CharField(max_length=50, blank=True)
    validador_max = CharField(max_length=50, blank=True)
    validador_min = CharField(max_length=50, blank=True)
    longitud = PositiveIntegerField(null=True)
    
    class Meta:
        unique_together = [['instrumento', 'respuesta']]
```

### 3.8 PreguntaHijo (Dependencias)

```python
class PreguntaHijo(Model):
    """
    Define qué preguntas se activan cuando una respuesta es seleccionada.
    Reemplaza EMCPREGUNTAHIJOS.
    """
    pregunta_padre = ForeignKey(Pregunta, on_delete=CASCADE, related_name='hijos')
    respuesta_activadora = ForeignKey(Respuesta, on_delete=CASCADE)
    pregunta_hija = ForeignKey(Pregunta, on_delete=CASCADE, related_name='padres')
    aplica_todo_hogar = BooleanField(default=False)       # VALTODOHOGAR
```

### 3.9 ValidadorExpresion

```python
class ValidadorExpresion(Model):
    """Expresiones complejas de validación. Reemplaza EMCVALIDADOREXPRESON."""
    codigo = CharField(max_length=20, unique=True)
    expresion = TextField()
    descripcion = CharField(max_length=500, blank=True)
    activo = BooleanField(default=True)
```

### 3.10 ComboQuery

```python
class ComboQuery(Model):
    """Queries para listas dinámicas. Reemplaza EMCADMONCOMBOS."""
    id_combo = CharField(max_length=30, unique=True)   # GICIDCOMBO
    query = TextField()                                 # GICQUERY
    # NOTA: Solo queries de SELECT sobre paramétricas, nunca sobre PII
```

---

## 4. Hogares y Encuestas

### 4.1 Hogar

```python
class Hogar(AuditableModel):
    """Hogar en proceso de caracterización. Reemplaza EMCHOGARES."""
    id = UUIDField(primary_key=True, default=uuid4)
    codigo = CharField(max_length=50, unique=True, db_index=True)  # HOGCODIGO
    tipo = CharField(max_length=20)                                  # HOGTIPO
    estado = CharField(max_length=20, db_index=True)                # ESTADO
    instrumento = ForeignKey(Instrumento, on_delete=PROTECT)
    punto_atencion = ForeignKey('PuntoAtencion', null=True, on_delete=SET_NULL)
    encuestador = ForeignKey(Usuario, on_delete=PROTECT)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 4.2 MiembroHogar

```python
class MiembroHogar(AuditableModel):
    """Persona miembro del hogar. Reemplaza EMCMIEMBROSHOGAR."""
    id = UUIDField(primary_key=True, default=uuid4)
    hogar = ForeignKey(Hogar, on_delete=CASCADE)
    victima = ForeignKey(Victima, null=True, on_delete=SET_NULL)  # PERIDPERSONA
    
    # Datos capturados al momento del ingreso al hogar — CIFRADOS
    primer_apellido = EncryptedCharField(max_length=100)
    segundo_apellido = EncryptedCharField(max_length=100, blank=True)
    primer_nombre = EncryptedCharField(max_length=100)
    segundo_nombre = EncryptedCharField(max_length=100, blank=True)
    tipo_documento = CharField(max_length=5)
    numero_documento = EncryptedCharField(max_length=30)
    fecha_nacimiento = EncryptedCharField(max_length=20, blank=True)
    
    es_jefe_hogar = BooleanField(default=False)    # INDJEFE
    estado = CharField(max_length=20)
    tipo_persona = CharField(max_length=20, blank=True)  # TIPO_PERSONA
    created_by = ForeignKey(Usuario, on_delete=PROTECT)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 4.3 SesionEncuesta

```python
class SesionEncuesta(AuditableModel):
    """
    Sesión de diligenciamiento de encuesta.
    Equivale al ciclo completo de DiligenciarPregunta.
    """
    id = UUIDField(primary_key=True, default=uuid4)
    hogar = ForeignKey(Hogar, on_delete=CASCADE)
    encuestador = ForeignKey(Usuario, on_delete=PROTECT)
    instrumento = ForeignKey(Instrumento, on_delete=PROTECT)
    estado = CharField(max_length=20, db_index=True)
    # Estados: INICIADA, EN_PROGRESO, LISTA_PARA_ENVIO, ENVIADA, VALIDADA
    
    fecha_inicio = DateTimeField(auto_now_add=True)
    fecha_finalizacion = DateTimeField(null=True)
    fecha_envio = DateTimeField(null=True)
    
    # Metadatos de localización del levantamiento
    departamento = ForeignKey('Departamento', null=True, on_delete=SET_NULL)
    municipio = ForeignKey('Municipio', null=True, on_delete=SET_NULL)
    vereda = ForeignKey('Vereda', null=True, on_delete=SET_NULL)
    
    class Meta:
        indexes = [Index(fields=['hogar', 'estado'])]
```

### 4.4 CapituloTerminado

```python
class CapituloTerminado(Model):
    """Progreso por módulo. Reemplaza EMCCAPITULOSTERMINADOS."""
    sesion = ForeignKey(SesionEncuesta, on_delete=CASCADE)
    tema = ForeignKey(Tema, on_delete=CASCADE)
    terminado_en = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['sesion', 'tema']]
```

### 4.5 RespuestaEncuesta

```python
class RespuestaEncuesta(AuditableModel):
    """
    Respuesta individual capturada. Reemplaza EMCRESPUESTASENCUESTA.
    Tabla de alta concurrencia — optimizada con índices.
    """
    id = UUIDField(primary_key=True, default=uuid4)
    sesion = ForeignKey(SesionEncuesta, on_delete=CASCADE)
    miembro = ForeignKey(MiembroHogar, null=True, on_delete=SET_NULL)  # null=preguntas de hogar
    pregunta_instrumento = ForeignKey(PreguntaInstrumento, on_delete=PROTECT)
    respuesta = ForeignKey(Respuesta, null=True, on_delete=PROTECT)    # null=texto libre
    texto_respuesta = EncryptedTextField(blank=True)  # RXPTEXTORESPUESTA — puede tener PII
    tipo_pregunta = CharField(max_length=20)           # RXPTIPOPREGUNTA
    created_by = ForeignKey(Usuario, on_delete=PROTECT)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            Index(fields=['sesion', 'pregunta_instrumento']),
            Index(fields=['sesion', 'miembro']),
        ]
```

### 4.6 ValidadorPersona (Estado de validación por persona)

```python
class ValidadorPersona(Model):
    """
    Estado de validaciones por persona en la sesión.
    Reemplaza EMCVALIDADORESPERSONA.
    """
    sesion = ForeignKey(SesionEncuesta, on_delete=CASCADE)
    miembro = ForeignKey(MiembroHogar, on_delete=CASCADE)
    instrumento = ForeignKey(Instrumento, on_delete=CASCADE)
    pregunta = ForeignKey(Pregunta, null=True, on_delete=SET_NULL)
    validador = CharField(max_length=20)         # VALIDVALIDADOR
    valor = CharField(max_length=200, blank=True) # PREVALOR
    fecha_hecho = DateField(null=True)            # FECHAHECHO
    comodin = CharField(max_length=100, blank=True)
    
    class Meta:
        indexes = [Index(fields=['sesion', 'miembro', 'validador'])]
```

### 4.7 SoporteJefeHogar

```python
class SoporteJefeHogar(Model):
    """Documentos soporte del jefe de hogar. Reemplaza EMCSOPORTEJEFEHOGAR."""
    id = UUIDField(primary_key=True, default=uuid4)
    hogar = ForeignKey(Hogar, on_delete=CASCADE)
    cc_jefe_hogar = EncryptedCharField(max_length=30)  # CIFRADO
    url_archivo = CharField(max_length=500)              # URL en MinIO/S3 (nunca ruta local)
    tipo_persona = PositiveSmallIntegerField(default=0)
    created_by = ForeignKey(Usuario, on_delete=PROTECT)
    created_at = DateTimeField(auto_now_add=True)
```

---

## 5. Paramétricas Geográficas

```python
class Departamento(Model):
    codigo = CharField(max_length=5, primary_key=True)  # IDDEPTO
    nombre = CharField(max_length=100)                   # NOMDEPTO

class Municipio(Model):
    codigo = CharField(max_length=10, primary_key=True)  # IDMUNICIPIO
    departamento = ForeignKey(Departamento, on_delete=CASCADE)
    codigo_depto_mpio = CharField(max_length=10)          # IDMUNIDEPTO
    nombre = CharField(max_length=150)                    # NOMMUNICIPIO
    # Campos adicionales del APK
    categoria = CharField(max_length=50, blank=True)
    clima = CharField(max_length=50, blank=True)
    grupo_especial = CharField(max_length=100, blank=True)
    operador = CharField(max_length=200, blank=True)

class Vereda(Model):
    codigo_dane = CharField(max_length=20, primary_key=True)  # CODDANEVER
    departamento = ForeignKey(Departamento, on_delete=CASCADE)
    municipio = ForeignKey(Municipio, on_delete=CASCADE)
    nombre = CharField(max_length=200)                         # NOMVER
    # 32,377 veredas del territorio nacional

class ComunidadNegra(Model):
    id_comunidad = CharField(max_length=20, unique=True)
    nombre = CharField(max_length=200)

class ResguardoIndigena(Model):
    id_resguardo = CharField(max_length=20, unique=True)
    nombre = CharField(max_length=200)
```

---

## 6. Puntos de Atención (DT)

```python
class DireccionTerritorial(Model):
    id = PositiveIntegerField(primary_key=True)   # IDDT
    nombre = CharField(max_length=200)             # DT

class PuntoAtencion(Model):
    id = PositiveIntegerField(primary_key=True)           # IDPUNTOATENCION
    nombre = CharField(max_length=200)                     # PUNTOATENCION
    direccion_territorial = ForeignKey(DireccionTerritorial, on_delete=CASCADE)
    departamento = ForeignKey(Departamento, on_delete=CASCADE)
    municipio = ForeignKey(Municipio, on_delete=CASCADE)

class RelacionHogarPunto(Model):
    """Reemplaza EMCRELACIONDTPUNTO."""
    hogar = ForeignKey(Hogar, on_delete=CASCADE)
    miembro = ForeignKey(MiembroHogar, null=True, on_delete=SET_NULL)
    punto_atencion = ForeignKey(PuntoAtencion, on_delete=CASCADE)
```

---

## 7. Auditoría

```python
class LogAcceso(Model):
    """Auditoría de accesos al sistema. Inmutable (sin update/delete)."""
    id = UUIDField(primary_key=True, default=uuid4)
    usuario = ForeignKey(Usuario, null=True, on_delete=SET_NULL)
    accion = CharField(max_length=50)     # LOGIN, BUSQUEDA_RNI, VER_VICTIMA, etc.
    recurso = CharField(max_length=100)   # Endpoint o recurso accedido
    recurso_id = CharField(max_length=100, blank=True)  # ID del recurso
    ip_origen = GenericIPAddressField()
    user_agent = CharField(max_length=500, blank=True)
    resultado = CharField(max_length=20)  # EXITO, DENEGADO, ERROR
    detalle = JSONField(default=dict)     # Contexto adicional (filtros usados, etc.)
    timestamp = DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            Index(fields=['usuario', 'timestamp']),
            Index(fields=['accion', 'timestamp']),
            Index(fields=['recurso_id']),
        ]
        # IMPORTANTE: Sin permisos de UPDATE/DELETE en esta tabla desde la app
        # Solo INSERT. Gestión por DBA con MFA.
```

---

## 8. Enfermedades Catastróficas / Ruinosas

```python
class EnfermedadCatastrofica(Model):
    """Reemplaza EMCRUINOSASCATASTROFICAS."""
    id_enfermedad = CharField(max_length=20, unique=True)
    nombre = CharField(max_length(300)
```

---

## 9. Resumen de Cambios respecto al APK

| Tabla APK | Tabla Nueva | Cambio Principal |
|-----------|-------------|-----------------|
| `EMCUSUARIOS` (PASSWORD plano) | `Usuario` | Contraseña con Argon2, JWT |
| `PERSONAS0..PERSONASA` (11 tablas) | `Victima` (1 tabla) | PII cifrada, índice por hash |
| `EMCRESPUESTASENCUESTA` | `RespuestaEncuesta` | texto_respuesta cifrado |
| `EMCMIEMBROSHOGAR` | `MiembroHogar` | Datos personales cifrados |
| Sin auditoría | `LogAcceso` | Auditoría inmutable |
| Sin sesión | `SesionEncuesta` | Contexto completo de trabajo |
| `EMCVERSION` | `Instrumento` | Versionado formal |
| `EMCCAPITULOSTERMINADOS` | `CapituloTerminado` | Vinculado a sesión, no a hogar global |
