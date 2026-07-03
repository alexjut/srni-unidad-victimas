# Política de Privacidad — SRNI Encuestador (App Móvil)

**Versión:** 1.0 — Borrador para revisión jurídica
**Fecha:** 2026-06-10
**Responsable del tratamiento:** Unidad para la Atención y Reparación Integral a las Víctimas (UARIV)
**Aplicación:** SRNI Encuestador (`co.gov.unidadvictimas.srni`) — Android / iOS

> **NOTA INTERNA (eliminar antes de publicar):** este borrador debe ser validado
> por la oficina jurídica de UARIV. Los campos marcados `[COMPLETAR]` requieren
> datos institucionales. Google Play exige que esta política esté publicada en
> una **URL pública** antes de enviar la app a revisión.

---

## 1. Quiénes somos

La aplicación **SRNI Encuestador** es una herramienta oficial de la Unidad para
la Atención y Reparación Integral a las Víctimas (UARIV), entidad pública del
orden nacional de Colombia, usada **exclusivamente por encuestadores
autorizados** de la entidad para realizar entrevistas de caracterización a la
población víctima del conflicto armado, en el marco de la Ley 1448 de 2011 y
sus normas reglamentarias.

La app **no está dirigida al público general**: requiere credenciales
institucionales asignadas por UARIV y no permite el registro autónomo de
usuarios.

- **Responsable del tratamiento:** Unidad para la Atención y Reparación
  Integral a las Víctimas (UARIV), NIT `[COMPLETAR]`.
- **Dirección:** `[COMPLETAR — dirección sede principal]`
- **Correo de contacto para protección de datos:** `[COMPLETAR — ej. servicioalciudadano@unidadvictimas.gov.co]`

## 2. Marco normativo

El tratamiento de datos personales realizado a través de la app se rige por:

- Ley 1581 de 2012 (Régimen General de Protección de Datos Personales) y
  Decreto 1377 de 2013.
- Ley 1448 de 2011 (Ley de Víctimas y Restitución de Tierras), en particular
  los deberes de reserva y confidencialidad sobre la información del Registro
  Único de Víctimas (artículo 156 y concordantes).
- Política de Tratamiento de Datos Personales de UARIV: `[COMPLETAR URL]`.

## 3. Qué datos se tratan y con qué finalidad

### 3.1 Datos del encuestador (usuario de la app)

| Dato | Finalidad |
|---|---|
| Código de usuario institucional y contraseña | Autenticación y control de acceso |
| Perfil y permisos asignados | Autorización de funciones dentro de la app |
| Registro de acciones (auditoría) | Trazabilidad de accesos y operaciones sobre datos de víctimas |
| Huella/biometría (opcional) | Desbloqueo rápido de la app. **La biometría se valida únicamente en el dispositivo** (Android Keystore / iOS Keychain); ningún dato biométrico se transmite ni almacena en servidores de UARIV |

### 3.2 Datos de las personas entrevistadas (víctimas y miembros del hogar)

| Dato | Finalidad |
|---|---|
| Tipo y número de documento de identidad | Verificación de la persona en el Registro Nacional de Información (RNI) |
| Nombres, apellidos, fecha de nacimiento, género | Identificación y registro de la persona y de los integrantes del hogar |
| Estado en el RUV, pertenencia étnica, condición de discapacidad | Determinar habilitación y enfoque diferencial de la caracterización |
| Composición del hogar (parentescos, roles) | Conformación del núcleo familiar a caracterizar |
| Datos de la vivienda (tipo, ocupación, estrato, número de cuartos y personas) | Caracterización socioeconómica del hogar |
| Respuestas de la entrevista de caracterización | Medición de subsistencia mínima y superación de situación de vulnerabilidad (finalidad legal de la caracterización) |
| Municipio y punto de atención donde se realiza la entrevista | Registro administrativo de la atención |

La caracterización constituye una **función pública** asignada a UARIV; el
tratamiento de estos datos se realiza en cumplimiento de un deber legal y en
interés de la propia población víctima.

### 3.3 Datos que la app NO recolecta

- Ubicación GPS del dispositivo.
- Contactos, fotos, archivos o mensajes del dispositivo.
- Identificadores publicitarios. La app **no contiene publicidad ni SDKs de
  analítica comercial de terceros**.
- Grabaciones de audio (ver sección 5).

## 4. Dónde se almacenan los datos

- **Servidores de UARIV:** toda la información de caracterización se transmite
  cifrada (HTTPS/TLS) y se almacena en la infraestructura del SRNI. Los datos
  identificadores sensibles (número de documento, nombres) se almacenan
  **cifrados en base de datos** y todo acceso queda registrado en un log de
  auditoría inmutable.
- **En el dispositivo (modo sin conexión):** para permitir el trabajo en campo
  sin señal, la app guarda temporalmente en el dispositivo: respuestas de la
  entrevista en curso, datos del hogar pendientes de envío e identificadores
  técnicos (UUID). **No se almacenan en el dispositivo números de documento ni
  nombres de las víctimas como copia permanente**; los datos pendientes se
  eliminan del teléfono una vez sincronizados con el servidor.
- Las credenciales de sesión se guardan en el almacenamiento seguro del
  sistema operativo (Android Keystore / iOS Keychain).
- La copia de seguridad del sistema (backup de Android) está **deshabilitada**
  para esta app.

## 5. Asistente de voz con inteligencia artificial (opcional)

La app ofrece un asistente opcional que ayuda al encuestador a diligenciar el
formulario a partir de la entrevista oral:

1. Su uso requiere **consentimiento explícito** del encuestador dentro de la
   app, registrado por sesión de entrevista.
2. El audio se transcribe **en el dispositivo**; el archivo de audio **nunca
   se almacena** ni se envía a ningún servidor.
3. Únicamente el **texto transcrito** se envía a los servidores de UARIV, que
   a su vez lo procesan mediante el servicio de inteligencia artificial
   **Google Gemini** para sugerir valores del formulario. El dispositivo móvil
   no se comunica directamente con Google; la integración ocurre solo desde el
   servidor de UARIV.
4. El asistente **solo sugiere** valores: el encuestador siempre revisa,
   edita, acepta o descarta cada sugerencia.
5. Cada uso del asistente queda registrado en el log de auditoría.
6. El asistente puede desactivarse en cualquier momento y su uso no afecta la
   validez de la encuesta.

## 6. Con quién se comparten los datos

- Los datos de caracterización se usan dentro de UARIV y se comparten con las
  entidades del Sistema Nacional de Atención y Reparación Integral a las
  Víctimas (SNARIV) **únicamente en los términos previstos por la ley**.
- Las transcripciones de texto del asistente de voz se procesan a través del
  servicio Google Gemini (ver sección 5) bajo los términos de servicio
  empresariales de dicho proveedor.
- **No se venden ni se ceden datos a terceros con fines comerciales.**

## 7. Tiempo de conservación

Los datos de caracterización se conservan conforme a las tablas de retención
documental de UARIV y a las obligaciones de la Ley 1448 de 2011 — `[COMPLETAR:
referencia exacta de la TRD aplicable]`. Los datos temporales almacenados en
el dispositivo se eliminan al sincronizarse; la sesión del encuestador expira
automáticamente.

## 8. Derechos de los titulares

Los titulares de los datos (personas entrevistadas) pueden ejercer sus derechos
de conocer, actualizar, rectificar y suprimir sus datos, y los demás previstos
en la Ley 1581 de 2012, a través de los canales oficiales de UARIV:

- Página: `[COMPLETAR — URL de servicio al ciudadano]`
- Correo: `[COMPLETAR]`
- Líneas de atención: `[COMPLETAR]`

La supresión de datos del RUV está sujeta a las reglas especiales de la Ley
1448 de 2011.

## 9. Seguridad

UARIV aplica medidas técnicas y administrativas que incluyen: cifrado en
tránsito (TLS) y en reposo para identificadores sensibles, control de acceso
por perfiles y permisos, expiración corta de sesiones, registro de auditoría
inmutable de todos los accesos a datos de víctimas, y bloqueo de tráfico sin
cifrar en la aplicación móvil.

## 10. Menores de edad

La app puede registrar datos de menores **como integrantes del hogar
caracterizado**, suministrados por el adulto autorizado en el marco de la
entrevista, con las garantías reforzadas de la Ley 1581 de 2012 (artículo 7) y
el interés superior del menor. La app no está dirigida a menores ni permite su
uso por menores.

## 11. Cambios a esta política

Cualquier cambio será publicado en esta misma URL con su fecha de
actualización. Cambios sustanciales serán notificados dentro de la app.

---
---

# ANEXO — Respuestas para el formulario "Data Safety" de Google Play Console

> Uso interno. Estas son las respuestas exactas para diligenciar la sección
> *App content → Data safety* al publicar.

**¿La app recolecta o comparte datos de usuario?** Sí.

**¿Los datos se cifran en tránsito?** Sí (TLS; `usesCleartextTraffic=false`).

**¿Los usuarios pueden solicitar la eliminación de datos?** Sí — vía canales
oficiales de UARIV (indicar URL de la sección 8).

| Categoría Play Console | Dato | ¿Recolectado? | ¿Compartido? | Propósito |
|---|---|---|---|---|
| Personal info → Name | Nombres y apellidos de entrevistados | Sí | No | App functionality |
| Personal info → Other IDs | Número de documento de identidad | Sí | No | App functionality |
| Personal info → User IDs | Código de usuario del encuestador | Sí | No | App functionality, Account management |
| Health and fitness → Health info | Condición de discapacidad (enfoque diferencial) | Sí | No | App functionality |
| Personal info → Race and ethnicity | Pertenencia étnica | Sí | No | App functionality |
| App activity → Other user-generated content | Respuestas de la encuesta de caracterización | Sí | Sí* | App functionality |
| App info and performance → Crash logs | No en producción (reporte de errores solo en builds de desarrollo) | No | No | — |
| Location | NO se recolecta (el municipio se selecciona de una lista, no es GPS) | No | No | — |
| Audio | NO se recolecta (transcripción en dispositivo; el audio nunca se almacena ni transmite) | No | No | — |

\* "Compartido" únicamente en el sentido de que el texto transcrito del
asistente de voz se procesa mediante Google Gemini desde el servidor de UARIV.
Si Play Console pregunta por *data shared with third parties*, declarar: texto
de transcripciones → Google (proveedor de servicio de IA), propósito *App
functionality*.

**Tipo de cuenta:** la app es de uso institucional restringido (credenciales
asignadas por UARIV). Recomendado publicar como **acceso privado/cerrado**
(pista cerrada o distribución gestionada) o app pública con login obligatorio
— en ambos casos Google exige credenciales de demostración para el revisor:
preparar un **usuario de prueba con datos ficticios**.
