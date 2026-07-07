# Contexto para las presentaciones del Acto Protocolario — SICAV Móvil

> **Para qué sirve este documento:** es el *brief* completo para que un asistente de IA
> (Claude) genere **dos presentaciones**. Contiene todo el contexto del proyecto,
> los datos verificados y el guion de la demostración. No requiere conocimiento previo.
>
> **Instrucción para la IA:** Con base en este documento, genera **dos presentaciones
> separadas** (diapositivas con título + viñetas, lenguaje claro e institucional, apto
> para público mixto técnico/no técnico de la UARIV):
> 1. **Presentación A — Contexto general** (conferencista: Ing. Alexandra María López
>    Sevillano · 9:45–10:15 a.m. · ~12–15 diapositivas).
> 2. **Presentación B — Operativa y demostración funcional** (presentador: Ing. Javier
>    Alexander Aguilar Castro · 10:30–11:00 a.m. · ~12–15 diapositivas + guion de demo).
>
> Tono: institucional, claro, orientado a beneficios. Evitar jerga innecesaria en la
> Presentación A; permitir más detalle técnico-operativo en la B.

---

## 0. Ficha del evento

| | |
|---|---|
| **Producto** | **SICAV Móvil** — Sistema de Caracterización a Víctimas (Móvil) |
| **Entidad** | Unidad para la Atención y Reparación Integral a las Víctimas (**UARIV**) |
| **Área** | Subdirección Red Nacional de Información (**RNI**) |
| **Acto 1** | Contexto general — Ing. Alexandra María López Sevillano (9:45–10:15) |
| **Acto 2** | Operativa + demo — Ing. Javier Alexander Aguilar Castro (10:30–11:00) |
| **Entrega** | A la Ing. Alexandra para validación, **01 de julio antes del mediodía** |
| **Gestión PETI** | PRY-0662064 |

---

# PRESENTACIÓN A — Contexto general

*(Conferencista: Ing. Alexandra María López Sevillano)*

### A.1 Contexto y justificación del proyecto
- La UARIV, a través de la Subdirección Red Nacional de Información (RNI), realiza la
  **caracterización de los hogares víctimas** en el territorio nacional: recoge
  información sobre vivienda, salud, educación, alimentación, generación de ingresos,
  retornos y reubicaciones, entre otros, para orientar la oferta institucional.
- Esta caracterización ocurre con frecuencia en **zonas rurales, dispersas o de difícil
  acceso, sin conectividad a internet**, donde las herramientas dependientes de red no
  son viables.
- **Justificación:** se requiere una herramienta moderna, **100 % funcional sin
  conexión**, segura y alineada con la normativa de protección de datos, que reemplace la
  aplicación anterior y profesionalice el proceso de captura en campo.

### A.2 Antecedentes y necesidad institucional
- Existía una aplicación Android previa de caracterización (*IgedEncuesta*, v4.1) que
  quedó **tecnológicamente desactualizada** y con limitaciones operativas.
- Necesidades institucionales identificadas:
  - **Operación sin conectividad** confiable en territorio.
  - **Seguridad y trazabilidad** de datos personales sensibles de las víctimas (Ley 1581).
  - **Múltiples perfiles poblacionales** (territorial, étnico, insular, telefónico,
    víctimas en el exterior) con cuestionarios y flujos propios.
  - **Sincronización ordenada** de la información recogida hacia los sistemas de la entidad.
  - **Mantenibilidad**: poder actualizar los cuestionarios sin reinstalar la aplicación.
- **Respuesta:** un desarrollo propio de tres frentes (móvil + backend/API + infraestructura)
  construido sobre tecnologías actuales y estándares de seguridad.

### A.3 Alcances de la solución tecnológica
- **Aplicación móvil (APK Android)** para los encuestadores, **offline-first**: opera de
  punta a punta sin internet desde el primer ingreso.
- **Backend (API) y panel web** para gestión, consulta y supervisión.
- **Infraestructura reproducible** desplegada en el servidor institucional de la UARIV.
- **8 instrumentos de caracterización** (perfiles poblacionales) cargados y versionados.
- **Caracterización completa por hogar**: registro de la víctima → conformación del hogar →
  captura por capítulos con lógica de saltos (skip-logic) → finalización → sincronización.
- **Asistencia con Inteligencia Artificial** para apoyar el diligenciamiento por voz.
- **Seguridad y cumplimiento** normativo incorporados desde el diseño.

### A.4 Componentes tecnológicos
*(Nivel alto — para la diapositiva basta el bloque conceptual; el detalle de versiones está en la ficha técnica al final.)*
- **App móvil:** React Native / Expo (Android), base de datos local cifrable, lógica de
  cuestionarios y sincronización offline, biometría opcional, asistente de IA.
- **Backend / API:** Django REST Framework con autenticación JWT, cifrado de datos
  personales (PII) en reposo y registro de auditoría inmutable.
- **Panel web de supervisión:** React + Vite (gestión, hogares, encuestas, reportes).
- **Datos y servicios:** PostgreSQL, Redis/Celery (procesos asíncronos), almacenamiento
  de archivos compatible con S3 (MinIO), Nginx como proxy.
- **Distribución:** compilación en la nube (EAS Build) y publicación del APK con
  **código QR** para instalación directa por los encuestadores.

### A.5 Módulos de la aplicación
1. **Acceso y seguridad:** ingreso con usuario/contraseña + biometría opcional (huella).
2. **Búsqueda y registro de la víctima:** identificación del titular del hogar (offline,
   contra padrón precargado).
3. **Conformación del hogar:** registro de los integrantes y sus datos básicos.
4. **Caracterización por instrumentos:** cuestionarios por perfil poblacional, organizados
   en capítulos (Identificación, Vivienda, Salud, Educación, Alimentación, Retornos y
   Reubicaciones, Generación de Ingresos, Uso del Territorio, etc.).
5. **Lógica de diligenciamiento (skip-logic):** muestra solo las preguntas que aplican
   según las respuestas, el sexo, la edad y la pertenencia étnica.
6. **Asistente de IA por voz:** apoya el llenado a partir del relato hablado.
7. **Sincronización:** envío ordenado y seguro de la información a los sistemas de la entidad.
8. **Panel web de supervisión:** seguimiento de avances y consulta (rol supervisor).

### A.6 Impacto esperado en la caracterización territorial
- **Cobertura en territorio sin conectividad:** caracterizar donde antes no era posible.
- **Calidad e integridad de los datos:** validaciones y lógica de saltos reducen errores
  y preguntas innecesarias.
- **Pertinencia por población:** 8 perfiles ajustados a cada tipo de comunidad (territorial,
  étnica, insular, exterior, telefónica).
- **Seguridad y cumplimiento:** protección de datos personales y trazabilidad conforme a
  la Ley 1581 de 2012.
- **Eficiencia operativa:** menos tiempo por encuesta, sincronización automática, menos
  reprocesos.
- **Sostenibilidad:** los cuestionarios se actualizan de forma centralizada, sin reinstalar
  la app; solución propia y mantenible por la entidad.

---

# PRESENTACIÓN B — Operativa y demostración funcional

*(Presentador: Ing. Javier Alexander Aguilar Castro)*

### B.1 Acceso y autenticación
- Ingreso con **usuario y contraseña** institucional.
- **Autenticación biométrica opcional** (huella) para reingresos rápidos.
- Sesión segura con **tokens JWT**; los datos sensibles se guardan protegidos en el
  dispositivo.
- **Precarga al ingresar:** al primer login con red, la app descarga el padrón y la
  jornada para poder trabajar después **sin conexión**.

### B.2 Navegación general de la aplicación
- Pantalla principal / hub de caracterizaciones por hogar.
- **Búsqueda de la víctima** (titular) y registro si no existe.
- **Hogar:** lista de integrantes y de caracterizaciones asociadas.
- Acceso a los **instrumentos** disponibles según el perfil.
- Indicadores de **progreso** y de **estado de sincronización** (pendiente / enviado).

### B.3 Funcionalidades principales
- **Operación 100 % offline** y sincronización automática al recuperar red.
- **8 instrumentos** de caracterización pre-empaquetados (no requieren descarga en campo).
- **Skip-logic**: solo se muestran las preguntas pertinentes (según respuestas, edad,
  sexo, pertenencia étnica).
- **Captura por hogar y por persona** (preguntas que se repiten por cada integrante).
- **Asistente de IA por voz** para apoyar el diligenciamiento.
- **Biometría**, **barra de progreso real** y **cola de sincronización** robusta
  (reintentos automáticos, sin pérdida ni duplicación de datos).

### B.4 Flujo de diligenciamiento de la información
1. **Ingreso** (login + biometría) → precarga de padrón/jornada.
2. **Buscar/registrar la víctima** titular del hogar.
3. **Conformar el hogar** (integrantes y datos básicos).
4. **Seleccionar el instrumento** según el perfil de la población.
5. **Responder por capítulos**: la app va mostrando solo lo que aplica (skip-logic);
   los capítulos se cierran automáticamente cuando corresponde.
6. **Finalizar** la caracterización (queda guardada localmente).
7. **Sincronizar** cuando haya conexión → la información viaja ordenada y segura al backend.
8. **Supervisión** desde el panel web (consulta de avances).

### B.5 Guion sugerido para la demostración práctica
> *Objetivo: mostrar un caso real de principio a fin en ~6–8 minutos.*
1. Mostrar el **ícono y el nombre de la app: “SICAV Móvil”**, abrir y **autenticarse**
   (mostrar la opción biométrica).
2. **Activar modo avión** para evidenciar que **funciona sin internet**.
3. **Buscar una víctima** del padrón y **registrar el hogar** con 2–3 integrantes.
4. Abrir un instrumento (p. ej. **Asistencia** o **Buenaventura**) y **diligenciar un
   capítulo**, evidenciando el **skip-logic** (una respuesta hace aparecer/desaparecer
   preguntas; un capítulo se cierra según la respuesta).
5. (Opcional) Mostrar el **asistente de IA por voz**.
6. **Finalizar** la caracterización y mostrar que queda **pendiente de sincronización**.
7. **Reactivar la red** y mostrar la **sincronización automática**.
8. Cerrar mostrando dónde se **descarga el APK** (página con **código QR**).

### B.6 Preguntas frecuentes anticipadas (para el cierre)
- **¿Funciona sin internet?** Sí, de principio a fin; sincroniza cuando hay red.
- **¿Cómo se protege la información de las víctimas?** Cifrado de datos personales,
  autenticación segura y registro de auditoría, conforme a la Ley 1581 de 2012.
- **¿Cómo se actualizan los cuestionarios?** De forma centralizada desde el backend, sin
  reinstalar la app.
- **¿Para qué poblaciones sirve?** 8 perfiles: Territorial, Asistencia, Telefónico,
  Buenaventura, San Andrés, Rural Étnico, Urbano Étnico y Víctimas en el Exterior.
- **¿En qué dispositivos?** Android (iOS aplazado por ahora).
- **¿Cómo se instala?** Descargando el APK desde la página interna con código QR.

---

## Ficha técnica de referencia (para diapositivas de respaldo / preguntas)

**Cifras clave**
- **8 instrumentos** de caracterización (perfiles poblacionales).
- **~92 capítulos** y **más de 1.500 preguntas** en total entre todos los instrumentos.
- Cobertura geográfica: **33 departamentos**, **1.102 municipios** (DIVIPOLA DANE) y
  **21 Direcciones Territoriales** de la UARIV.

**Componentes (versiones)**
- **Móvil:** Expo SDK 54 / React Native 0.81, expo-sqlite, expo-router, biometría
  (expo-local-authentication), IA (Gemini).
- **Backend:** Django 5.2 LTS + Django REST Framework, JWT (SimpleJWT), cifrado PII
  (cryptography/Fernet), auditoría inmutable (Ley 1581), PostgreSQL, Redis/Celery, MinIO.
- **Panel web:** React 18 + Vite + Tailwind.
- **Infraestructura:** Docker Compose + Nginx, servidor institucional UARIV; compilación
  del APK en EAS Build (Expo) y publicación con QR.

**Cumplimiento normativo**
- **Ley 1581 de 2012** (protección de datos personales): PII cifrada + registro de acceso
  inmutable.
- **CONPES 3995** (seguridad digital): endurecimiento de la plataforma.
- **Decreto 1377 de 2013** (minimización de datos).

**Estado actual (a la fecha del evento)**
- Backend y app móvil **operativos**; **APK publicado** y disponible por QR.
- App **renombrada a “SICAV Móvil”**.
- 4 instrumentos recientemente **reconstruidos y verificados** (Asistencia, Buenaventura,
  San Andrés, Urbano Étnico) con su lógica de diligenciamiento validada.

**Equipo**
- **Ing. Javier Alexander Aguilar Castro** — desarrollo backend, base de datos, móvil e
  infraestructura.
- **Brando** — frontend del panel web.
- **Ing. Oscar Andrés Manosalva García** — supervisión funcional (UARIV).

---

> **Nota de manejo:** documento de contexto institucional. No incluye contraseñas, llaves
> ni direcciones internas del servidor. El enlace de descarga del APK (con QR) se comparte
> únicamente en el entorno autorizado de la entidad.
