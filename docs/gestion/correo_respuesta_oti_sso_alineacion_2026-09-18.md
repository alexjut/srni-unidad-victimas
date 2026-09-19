# Respuesta al concepto técnico de la OTI — alineación con Auth SSO y Unidad en Línea

**Para:** OTI (autores del concepto) · **Copia:** Alexandra, Oscar Andrés Manosalva (SRNI), Rommey Ruiz (PMO)
**De:** Javier Alexander Aguilar Castro — Desarrollo SRNI
**Fecha:** 19 de septiembre de 2026
**Asunto:** Respuesta al concepto técnico sobre alineación de la app de caracterización con Auth SSO y Unidad en Línea

---

Buen día.

Gracias por el análisis. Es un trabajo serio y preciso en casi todo, y coincidimos con
la recomendación de fondo: **abordar primero la integración con Auth SSO** y dejar la
interoperabilidad de servicios como consecuencia, no al revés.

Abajo confirmamos lo correcto, corregimos tres puntos que quedaron desactualizados,
informamos lo que ya se resolvió esta semana y exponemos **por qué la solución está
construida como está**. Esto último no es defensa de oficio: varias de esas decisiones
son las que permiten caracterizar en territorio sin señal, y conviene que la alineación
se diseñe sabiendo qué se sostiene sobre qué.

Adjuntamos la versión 2 del informe técnico **«SICAV — Arquitectura, datos e
integración»**, que incluye el diagrama de la solución, el sustento de cada decisión,
dónde queda cada dato y las interfaces ya publicadas.

## 1. Lo que confirmamos del concepto

El stack está bien descrito: Django 5.2 con DRF y JWT propio, PostgreSQL 16, Redis y
Celery, despliegue con Docker Compose detrás de Nginx, panel en React 18 servido en el
mismo origen que la API, y app móvil en Expo SDK 54 con operación sin conexión, cola de
sincronización, tokens en almacenamiento seguro del sistema y biometría opcional.
También es correcto que **hoy no estamos integrados con ningún proveedor de identidad**:
el modelo de usuarios es propio.

## 2. Tres precisiones sobre el estado actual

**a) La fuente de datos de víctimas ya no es de prueba.** Es la precisión más
importante. **Desde agosto producción trabaja contra el padrón real**: 5.926.004
personas incluidas y un universo del RUV de 12.009.492 registros, cargados desde las
fuentes oficiales por los enlaces autorizados.

La descripción que ustedes encontraron corresponde a una etapa anterior del proyecto y
**el cambio no alcanzó a reflejarse en la documentación publicada**, que quedó con la
versión de junio. A eso se suma que en el repositorio permanecían artefactos de
configuración de esa etapa que no se retiraron a tiempo y que refuerzan esa lectura. Ya
están corregidos.

Vale la pena precisar además **cómo** se resolvió, porque tampoco fue como lo
anticipaba aquella documentación: allí se contemplaba consultar Oracle en línea, y lo
implementado es distinto —el padrón oficial **se carga** a la base de SICAV y la
aplicación lo consulta desde ahí—, porque una consulta en vivo no funciona en una
jornada sin señal. La integración con la fuente oficial ocurrió; por otro camino.

**b) No usamos MinIO.** Se evaluó y se descartó en su momento. Los archivos se guardan
en el volumen del servidor y los estáticos los sirve la propia aplicación. Lo que
quedó fueron variables de configuración de esa evaluación que no se retiraron y que
inducen a esa conclusión; las estamos limpiando.

**c) El cifrado de datos personales es a nivel de campo, con Fernet** (AES + HMAC) sobre
los campos identificadores, y búsqueda por resumen SHA-256 indexado para no tener que
descifrar. No es cifrado de toda la base ni pgcrypto. La vigencia real del token de
refresco en producción es de 7 días, no de 8 horas: se amplió justamente por las
jornadas de campo sin señal.

## 3. Lo que ya se resolvió esta semana

La revisión que motivó su concepto nos sirvió para cerrar frentes. Al 19 de septiembre:

| Observación | Estado |
|---|---|
| (i) Cifrado del almacenamiento local del móvil | **Hecho** para los datos personales pendientes de sincronizar: van cifrados, con la llave en el almacén seguro del sistema. Cifrar el archivo completo exige cambiar el motor de base de datos del dispositivo y queda planificado |
| (ii) Documentación que describía una fuente de prueba | **Actualizada**: los cuatro documentos quedaron marcados como superados, con el estado vigente |
| Dependencia del proveedor de IA en la aplicación | **Retirada** del inventario: no se usaba —la ruta real es el intermediario del servidor— pero inducía a error |
| Documentación interactiva de la API sin autenticación | **Corregida**. Hallazgo propio de esta revisión; ya exige sesión |

## 4. Por qué la solución está construida así

Tres decisiones que conviene tener presentes antes de definir la integración, porque
cualquiera de las tres puede romperse sin querer:

**La operación es sin conexión, y eso manda.** Una jornada dura horas en zonas sin
señal, con familias ya convocadas. Un sistema que exija estar en línea no captura menos:
pierde la jornada, el desplazamiento y la convocatoria. Por eso la captura escribe en el
dispositivo en el momento, los instrumentos viajan dentro de la aplicación y la
sincronización ocurre después.

**El padrón se carga, no se consulta en vivo.** La consulta en línea contra Oracle,
que era lo contemplado al inicio, no funciona en una jornada sin señal. Hoy el padrón
oficial vive en la base de SICAV y el dispositivo lleva una copia consultable por
documento hasheado.

**Al sistema anterior se le escribe con sus propias reglas y se verifica cada paso.**
No insertamos en sus tablas: invocamos sus procedimientos oficiales y después
comprobamos con una consulta que la fila quedó, porque esos procedimientos confirman por
dentro y capturan sus propios errores. Por eso la escritura automática sigue apagada
hasta que haya respaldo confirmado: allí un error no se deshace.

## 5. Sobre la integración con Auth SSO

Estamos de acuerdo con el enfoque de **federación de tokens**: que el Auth API sea el
emisor de la identidad y que nuestro backend valide firma, emisor y audiencia,
conservando en Django la autorización (el mapeo de la identidad a los roles del
negocio: encuestador, coordinador, supervisor, documentador y administrador).

Del lado nuestro el cambio es acotado y ya está identificado: hoy firmamos con HS256 y
llave propia; aceptar un emisor externo significa habilitar RS256 con la URL de llaves
públicas (JWKS), fijar emisor y audiencia, y agregar una clase de autenticación que
mapee la identidad del token al usuario ya existente. Las cuentas reales ya están
creadas y son las mismas personas, así que no hay duplicación de usuarios.

Para avanzar necesitamos de su parte tres definiciones:

1. **¿El Auth API soporta OIDC con Authorization Code + PKCE?** Es el flujo que exige
   una app móvil. Si todavía no, esta integración es la oportunidad de estandarizarlo.
2. **¿Expone JWKS o llave pública, y con qué emisor y audiencia?**
3. **Vigencias.** Este es el punto que más nos condiciona y conviene resolverlo antes de
   escribir código: una jornada de caracterización dura horas **sin conectividad**, en
   zonas donde no hay señal. El esquema de sesión del SSO debe permitir una credencial
   de refresco de varios días y revalidación al sincronizar. Si la sesión del SSO
   expira mientras la encuestadora está en campo, **se pierde la jornada**: no es una
   molestia de usabilidad, es información de víctimas que hay que volver a levantar.

Proponemos una mesa técnica de una hora con su equipo para cerrar estos tres puntos y
estimar el trabajo con fechas.

## 6. Sobre la alineación con Unidad en Línea

Coincidimos: **no conviene unificar las aplicaciones**. Son públicos y propósitos
distintos —ciudadano frente a operación interna en campo— y la nuestra maneja datos
sensibles en el dispositivo.

La interoperabilidad por servicios sí nos parece valiosa, y de nuestro lado **ya está
disponible**: el backend publica su contrato OpenAPI y expone, entre otros, la consulta
del estado de caracterización de una persona, su grupo familiar, el estado de envío al
sistema legado y los reportes de producción. Si Unidad en Línea quiere mostrarle a la
víctima el estado o el resultado de su caracterización, el servicio existe; solo falta
acordar el contrato, el control de acceso y qué campos son pertinentes de mostrarle al
ciudadano (esto último debería revisarlo protección de datos, no solo nosotros).

En sentido contrario, nos interesa la creación y trazabilidad de casos en integración
con SGV. Quedamos atentos a la documentación de esos servicios.

## 7. Sobre las observaciones adicionales

**(i) Cifrado del almacenamiento local del móvil:** la observación era correcta y **ya
se atendió**: los datos personales que quedan en el teléfono mientras la cola está
pendiente van cifrados, con la llave en el almacén seguro del sistema operativo y un
sello que detecta alteraciones. El padrón local ya se consultaba por documento hasheado
y se borra al cerrar sesión. Queda pendiente cifrar el archivo completo de la base, que
obliga a cambiar el motor del dispositivo.

**(ii) Uso de IA:** el asistente está mediado por el backend —la app nunca habla con el
proveedor— y cada sesión exige un consentimiento registrado con su huella y auditado. No
se almacena el audio ni el texto de la entrevista. Compartimos la observación de que
**debe validarse con protección de datos**, y agregamos un matiz que conviene atender:
hoy el consentimiento lo registra la encuestadora en nombre de la entrevista; falta
definir formalmente cómo se documenta el consentimiento de la persona entrevistada.
Sobre eso pedimos concepto expreso del área competente.

**(iii) Documentación de la API:** la revisión nos dejó un hallazgo propio, **ya
corregido**: la documentación interactiva estaba accesible sin autenticación en el
despliegue. No exponía datos, pero sí el mapa de la API. Hoy exige sesión.

## 8. Lo que proponemos

| # | Acción | Responsable | Cuándo |
|---|---|---|---|
| 1 | Mesa técnica de Auth SSO: OIDC/PKCE, JWKS, vigencias para operación sin conexión | OTI + SRNI | Esta semana |
| 2 | Prueba de concepto de validación de tokens del Auth API en un ambiente de pruebas | SRNI | 1 semana después de la mesa |
| 3 | Contrato de los servicios a consumir entre Unidad en Línea y caracterización | OTI + SRNI | Tras el punto 1 |
| 4 | Concepto de protección de datos sobre el uso de IA y sobre qué se le muestra a la víctima | Oficial de protección de datos | Paralelo |
| 5 | Corrección de la documentación desactualizada y de la exposición de Swagger | SRNI | ✅ Hecho (18-sep) |

Cordialmente,

**Javier Alexander Aguilar Castro**
Desarrollo — Subdirección Red Nacional de Información
