# SICAV Móvil — Resumen Directivo del Lanzamiento

> **Sistema de Caracterización a Víctimas (Móvil)** · Unidad para la Atención y Reparación
> Integral a las Víctimas (**UARIV**) · Subdirección Red Nacional de Información (**RNI**).
> Documento de contexto institucional para directivos e invitados al acto de lanzamiento.
> **Fecha:** 2026-07-07 · **Gestión PETI:** PRY-0662064.

---

## 1. Qué es y para qué sirve

**SICAV Móvil** es la nueva aplicación Android con la que los encuestadores de la UARIV
**caracterizan a los hogares víctimas en todo el territorio nacional** —vivienda, salud,
educación, alimentación, generación de ingresos, retornos y reubicaciones, entre otros—
para orientar la oferta institucional.

Reemplaza a la aplicación anterior (*IgedEncuesta*, tecnológicamente desactualizada) con una
solución **propia, moderna, segura y 100 % funcional sin conexión a internet**, diseñada para
operar en **zonas rurales, dispersas y de difícil acceso** donde antes la captura no era viable.

---

## 2. El valor para la Entidad (en una frase)

> **Caracterizar con calidad y seguridad donde antes no había cómo hacerlo —sin internet,
> protegiendo los datos de las víctimas y actualizable sin reinstalar la app.**

| Beneficio | En qué se traduce |
|---|---|
| **Cobertura territorial** | Caracterización de punta a punta **sin conectividad**; sincroniza sola cuando hay red. |
| **Calidad de los datos** | Lógica de saltos (*skip-logic*) y validaciones: solo se pregunta lo que aplica → menos errores y menos reprocesos. |
| **Pertinencia poblacional** | **8 perfiles** ajustados a cada tipo de comunidad. |
| **Seguridad y cumplimiento** | Datos personales cifrados y trazables conforme a la **Ley 1581 de 2012**. |
| **Sostenibilidad** | Cuestionarios actualizables **de forma centralizada**, sin reinstalar la app. Solución propia y mantenible por la UARIV. |

---

## 3. Cifras clave

| Indicador | Valor |
|---|---:|
| Instrumentos de caracterización (perfiles poblacionales) | **8** |
| Capítulos temáticos | **93** |
| Preguntas activas | **995** |
| Opciones de respuesta parametrizadas | **2 239** |
| Departamentos (DIVIPOLA DANE) | **33** |
| Municipios (DIVIPOLA DANE) | **1 102** |
| Direcciones Territoriales UARIV | **21** |

**Los 8 perfiles:** Territorial · Asistencia · Telefónico · Buenaventura · San Andrés ·
Rural Étnico · Urbano Étnico · Víctimas en el Exterior.

---

## 4. Cómo funciona (flujo del encuestador)

1. **Ingreso** con usuario y contraseña + **biometría opcional** (huella).
2. **Precarga** del padrón y la jornada al primer login con red → luego trabaja **offline**.
3. **Busca o registra a la víctima** titular del hogar.
4. **Conforma el hogar** (integrantes y datos básicos).
5. **Diligencia por capítulos**: la app muestra **solo las preguntas que aplican** según
   respuestas, edad, sexo y pertenencia étnica.
6. **Asistente de IA por voz** (opcional) para apoyar el llenado.
7. **Finaliza** la caracterización (queda guardada en el dispositivo).
8. **Sincroniza** automáticamente al recuperar red → la información viaja **ordenada y segura**.
9. **Supervisión** desde el panel web de la Entidad.

---

## 5. Seguridad y cumplimiento normativo

- **Ley 1581 de 2012** — datos personales (PII) **cifrados en reposo** + **registro de acceso
  inmutable** (auditoría).
- **CONPES 3995** — endurecimiento de seguridad de la plataforma.
- **Decreto 1377 de 2013** — minimización de datos.
- Autenticación segura con tokens (JWT), biometría opcional y protección del almacenamiento
  local del dispositivo.

---

## 6. Estado a la fecha del lanzamiento

- ✅ **Backend y aplicación móvil operativos.**
- ✅ **APK publicado** y disponible para instalación mediante **código QR** en el entorno
  autorizado de la Entidad.
- ✅ Aplicación con su marca definitiva: **SICAV Móvil**.
- ✅ Los **8 instrumentos** cargados, versionados y empaquetados en la app (funcionan sin descarga en campo).
- ✅ Auditoría de calidad y seguridad aplicada (integridad de sincronización, privacidad,
  progreso, operación offline, biometría opt-in).

---

## 7. Arquitectura en tres frentes

| Componente | Tecnología | Función |
|---|---|---|
| **App móvil (Android)** | React Native / Expo SDK 54 | Captura offline-first en campo, biometría, IA por voz. |
| **Backend / API** | Django 5.2 LTS + DRF, JWT, PostgreSQL, Redis/Celery, MinIO | Gestión, cifrado de PII, auditoría, sincronización. |
| **Panel web de supervisión** | React 18 + Vite + Tailwind | Consulta de avances y reportes (rol supervisor). |

**Infraestructura:** Docker + Nginx en el servidor institucional UARIV · Compilación del APK
en la nube (EAS Build) · Distribución por QR.

---

## 8. Equipo

- **Ing. Javier Alexander Aguilar Castro** — Desarrollo backend, base de datos, móvil e
  infraestructura.
- **Brando** — Frontend del panel web de supervisión.
- **Ing. Oscar Andrés Manosalva García** — Supervisión funcional (UARIV).

---

> **Nota de manejo:** documento de contexto institucional. No contiene contraseñas, llaves ni
> direcciones internas del servidor. El enlace de descarga del APK (con QR) se comparte
> únicamente en el entorno autorizado de la Entidad.
