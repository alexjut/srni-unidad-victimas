# Respuesta al concepto técnico de la OTI — alineación con Auth SSO y Unidad en Línea

**Para:** OTI (autores del concepto) · **Copia:** Alexandra, Oscar Andrés Manosalva (SRNI), Rommey Ruiz (PMO)
**De:** Javier Alexander Aguilar Castro — Desarrollo SRNI
**Fecha:** 18 de septiembre de 2026
**Asunto:** Respuesta al concepto técnico sobre alineación de la app de caracterización con Auth SSO y Unidad en Línea

---

Buen día.

Gracias por el análisis. Es preciso en casi todo y coincidimos con la recomendación de
fondo: **abordar primero la integración con Auth SSO** y dejar la interoperabilidad de
servicios como consecuencia, no al revés. Abajo confirmamos lo que está correcto,
corregimos tres puntos que quedaron desactualizados y proponemos cómo seguir.

Adjuntamos el informe técnico **«SICAV — Arquitectura, datos e integración»**, que
incluye el diagrama de la solución, dónde queda cada dato y las interfaces ya
publicadas.

## 1. Lo que confirmamos del concepto

El stack está bien descrito: Django 5.2 con DRF y JWT propio, PostgreSQL 16, Redis y
Celery, despliegue con Docker Compose detrás de Nginx, panel en React 18 servido en el
mismo origen que la API, y app móvil en Expo SDK 54 con operación sin conexión, cola de
sincronización, tokens en almacenamiento seguro del sistema y biometría opcional.
También es correcto que **hoy no estamos integrados con ningún proveedor de identidad**:
el modelo de usuarios es propio.

## 2. Tres precisiones sobre el estado actual

**a) La fuente de datos de víctimas ya no es de prueba.** Es el punto más importante a
corregir, y la imprecisión es nuestra: esa frase sale de un informe que les enviamos en
**junio**, cuando efectivamente la búsqueda usaba un repositorio de prueba. Desde agosto
producción trabaja contra el **padrón real**: 5.926.004 personas incluidas y un universo
del RUV de 12.009.492 registros, cargados desde las fuentes oficiales por los enlaces
autorizados.

Vale la pena precisar cómo se resolvió, porque tampoco fue como lo planteaba aquel
documento. Allí se proponía consultar Oracle en vivo. Lo implementado es distinto: el
padrón oficial **se carga** a la base de SICAV y la aplicación lo consulta desde ahí,
precisamente porque la operación es sin conexión —una consulta en vivo contra Oracle no
funciona en campo—. La integración con la fuente oficial ocurrió; por otro camino.
Estamos actualizando los documentos que quedaron con la versión anterior.

**b) No usamos MinIO.** Se evaluó y se descartó. Los archivos se guardan en el volumen
del servidor y los estáticos los sirve la propia aplicación. Quedaron variables de
configuración sin uso que retiraremos para no inducir a error.

**c) El cifrado de datos personales es a nivel de campo, con Fernet** (AES + HMAC) sobre
los campos identificadores, y búsqueda por resumen SHA-256 indexado para no tener que
descifrar. No es cifrado de toda la base ni pgcrypto. La vigencia real del token de
refresco en producción es de 7 días, no de 8 horas: se amplió justamente por las
jornadas de campo sin señal.

## 3. Sobre la integración con Auth SSO

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

## 4. Sobre la alineación con Unidad en Línea

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

## 5. Sobre las observaciones adicionales

**(i) Cifrado del almacenamiento local del móvil:** cierto, sigue pendiente y está
documentado como tal. Mitigación actual: en el teléfono el padrón se consulta por
documento **hasheado**, no en claro, y al cerrar sesión se borran los datos personales
del dispositivo. La implementación con base cifrada está planificada.

**(ii) Uso de IA:** el asistente está mediado por el backend —la app nunca habla con el
proveedor— y cada sesión exige un consentimiento registrado con su huella y auditado. No
se almacena el audio ni el texto de la entrevista. Compartimos la observación de que
**debe validarse con protección de datos**, y agregamos un matiz que conviene atender:
hoy el consentimiento lo registra la encuestadora en nombre de la entrevista; falta
definir formalmente cómo se documenta el consentimiento de la persona entrevistada.
Sobre eso pedimos concepto expreso del área competente.

**(iii) Documentación de la API:** la revisión nos dejó un hallazgo propio que ya estamos
corrigiendo: la documentación interactiva quedó accesible sin autenticación en el
despliegue. No expone datos, pero sí el mapa de la API, así que la restringimos.

## 6. Lo que proponemos

| # | Acción | Responsable | Cuándo |
|---|---|---|---|
| 1 | Mesa técnica de Auth SSO: OIDC/PKCE, JWKS, vigencias para operación sin conexión | OTI + SRNI | Esta semana |
| 2 | Prueba de concepto de validación de tokens del Auth API en un ambiente de pruebas | SRNI | 1 semana después de la mesa |
| 3 | Contrato de los servicios a consumir entre Unidad en Línea y caracterización | OTI + SRNI | Tras el punto 1 |
| 4 | Concepto de protección de datos sobre el uso de IA y sobre qué se le muestra a la víctima | Oficial de protección de datos | Paralelo |
| 5 | Corrección de la documentación desactualizada y de la exposición de Swagger | SRNI | En curso |

Cordialmente,

**Javier Alexander Aguilar Castro**
Desarrollo — Subdirección Red Nacional de Información
