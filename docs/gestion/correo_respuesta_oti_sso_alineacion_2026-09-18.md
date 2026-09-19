# Respuesta al concepto técnico de la OTI — versión corta

**Para:** OTI (autores del concepto) · **Copia:** Alexandra, Oscar Andrés Manosalva (SRNI), Rommey Ruiz (PMO)
**De:** Javier Alexander Aguilar Castro — Desarrollo SRNI
**Fecha:** 19 de septiembre de 2026
**Asunto:** Respuesta al concepto técnico — alineación con Auth SSO y Unidad en Línea
**Adjunto:** SICAV — Arquitectura, datos e integración (v2, PDF)

> El detalle —diagrama de la solución, el sustento de cada decisión, dónde queda cada
> dato, las interfaces publicadas y los pendientes— está en el informe adjunto. Este
> correo es el resumen.

---

Buen día.

Gracias por el análisis: es un trabajo serio y acertado en lo esencial. Coincidimos con
la recomendación de fondo —**abordar primero la integración con Auth SSO** y dejar la
interoperabilidad de servicios como consecuencia, no al revés— y también en no unificar
la aplicación con Unidad en Línea: son públicos y propósitos distintos.

**Tres precisiones.** La fuente de datos de víctimas **ya no es de prueba**: desde
agosto producción trabaja con el padrón real —5.926.004 personas y 12.009.492 del
universo del RUV—. La descripción que encontraron corresponde a una etapa anterior que
no alcanzó a reflejarse en la documentación publicada, y a eso se sumaron artefactos de
configuración de esa etapa que no se habían retirado; ambas cosas ya están corregidas.
Esos mismos restos explican la mención a MinIO, que se evaluó y se descartó. Y el
cifrado de datos personales es **a nivel de campo**, con búsqueda por resumen indexado,
no de toda la base; la vigencia del token de refresco en producción es de **7 días**, no
de 8 horas, justamente por las jornadas sin señal.

**Sus observaciones ya se atendieron, salvo una.** Los datos personales que quedan en el
teléfono se cifran en reposo desde el 18 de septiembre; la documentación desactualizada
quedó corregida; y retiramos del inventario del móvil la dependencia del proveedor de
IA, que no se usaba —la ruta real es el intermediario del servidor— pero inducía a
error. Queda pendiente el concepto de protección de datos sobre el uso de IA, que
compartimos y solicitamos: hoy el consentimiento lo registra la encuestadora, y falta
definir cómo se documenta el de la persona entrevistada.

**Una condición para el SSO, y es de operación, no de preferencia técnica.** Una jornada
de caracterización dura horas sin conectividad, con familias ya convocadas. El esquema
de sesión debe permitir una credencial de refresco de varios días y revalidación al
sincronizar: si la sesión expira en campo, no se pierde una pantalla, se pierde la
jornada. Del lado nuestro el trabajo es acotado —validar los tokens de su emisor y
mapearlos a los usuarios que ya existen— y la autorización seguiría viviendo en el
negocio.

**Necesitamos de ustedes tres definiciones:** si el Auth API soporta el flujo estándar
para aplicaciones móviles (código de autorización con PKCE), cuál es el punto de
publicación de llaves con su emisor y audiencia, y qué vigencias admite para el caso de
campo. Proponemos una **mesa técnica de una hora esta semana** para cerrarlas y estimar
el trabajo con fechas; después, una prueba de concepto en ambiente de pruebas, sin tocar
producción.

Sobre interoperabilidad: nuestros servicios ya están publicados con su contrato OpenAPI,
incluida la consulta del estado de caracterización de una persona. Falta acordar el
control de acceso y qué campos es pertinente mostrarle al ciudadano, que debería revisar
protección de datos.

Por último, dos asuntos que exceden este alcance y siguen sin dueño: la **cadena de
carga nocturna del aplicativo heredado**, caída desde el 16 de agosto con pérdida diaria
de captura (caso 14512), y la **constancia de los respaldos** del servidor, solicitada
desde junio.

Quedamos atentos.

Cordialmente,

**Javier Alexander Aguilar Castro**
Desarrollo — Subdirección Red Nacional de Información

---

*La versión extensa, punto por punto, queda en el historial del repositorio (commit
`56cc905`) por si se necesita.*
