# Seguridad e infraestructura de SICAV — el mapa completo

**Corte: 18 de septiembre de 2026.** Este documento existe para tener una sola imagen
mental: qué está protegido, cómo, dónde vive cada cosa y qué falta. Todo lo que dice
está verificado contra el código y contra producción en esta fecha; lo que no se pudo
verificar se dice que no.

---

## 1. Las piezas y dónde viven

| Pieza | Dónde | Quién la sirve |
|---|---|---|
| Panel web (React) | Servidor institucional `30.0.1.109`, contenedor `cz_nginx` | El mismo origen que la API |
| API (Django) | Contenedor `cz_backend` (+ `cz_celery`, `cz_celery_padron`, `cz_beat`) | Gunicorn detrás de Nginx |
| Base de datos | `cz_postgres` (PostgreSQL 16), en el disco `/datos` | Sin puerto expuesto fuera de la red de contenedores |
| Cola y tareas | `cz_redis` (con contraseña) | Solo interno |
| APK | Archivo servido por el propio servidor, con descarga auditada | `caracterizacion.unidadvictimas.gov.co/descargar/` |
| Teléfonos | SQLite local + archivos del padrón y del filtro | El dispositivo de cada encuestadora |

**Entrada única:** el dominio institucional, por HTTPS, detrás del firewall de
aplicaciones (WAF FortiWeb). El servidor no se administra por internet: SSH con llave,
y solo a través de la VPN de la entidad.

---

## 2. Identidad y sesión

| Qué | Cómo está hoy |
|---|---|
| Autenticación | JWT propio (SimpleJWT). **No hay proveedor de identidad externo**; la integración con Auth SSO está propuesta, no hecha |
| Token de acceso | **15 minutos** |
| Token de refresco | **7 días en producción** (8 horas es el valor de desarrollo). Largo a propósito: una jornada de campo puede pasar días sin señal |
| Rotación | Sí: cada refresco emite uno nuevo y **revoca el anterior** (lista de revocación en base de datos) |
| Cierre de sesión | Revoca el token de refresco. Cambiar la contraseña también lo revoca |
| Contraseñas | **Argon2id**. Se descartó replicar el esquema del sistema anterior (SHA-512 con sal fija) |
| Biometría | Opcional y explícita, para reabrir la app. No reemplaza la contraseña |
| Dónde viven los tokens en el teléfono | Almacén seguro del sistema operativo (Keystore), nunca en la base local |

**Perfiles:** ADMINISTRADOR, COORDINADOR, SUPERVISOR, DOCUMENTADOR (solo lectura) y
ENCUESTADOR. Los permisos se evalúan **en el servidor**; ocultar botones en la
interfaz es comodidad, no control. Hay una prueba automática que verifica 61
combinaciones de permiso en cada cambio.

**Desde el 18-sep** existe además la jerarquía de equipos (quién supervisa a quién),
con el alcance «lo de mi equipo» ya disponible pero **todavía no encendido** en las
consultas de sesiones, hogares y reportes.

---

## 3. Los datos personales, uno por uno

### En el servidor
| Dato | Protección |
|---|---|
| Nombre, documento, fecha de nacimiento de víctimas | **Cifrados por campo** (Fernet: AES + HMAC), con la llave fuera del código, en variable de entorno |
| Búsqueda por documento | Sobre un **resumen SHA-256 indexado**, nunca sobre el campo cifrado |
| Respuestas de la entrevista | En claro en la base, ligadas a códigos de pregunta |
| Accesos | Registro **de solo inserción**: ingreso, búsqueda, consulta, captura, cierre, uso de IA, descarga de APK |

**Lo que esto significa:** un volcado no autorizado de la base no entrega identidades.
No es cifrado total del disco ni de toda la base.

### En el teléfono
| Dato | Protección |
|---|---|
| Altas manuales e integrantes capturados sin señal | **Cifrados desde el 18-sep** (AES-256 + sello HMAC; llave de 32 bytes en el Keystore) |
| Padrón descargado (≈320 MB) | Documento **hasheado**, no en claro. Se borra al cerrar sesión |
| Filtro del universo (21,7 MiB) | No contiene nombres ni documentos legibles: solo responde «existe / no existe» |
| Respuestas capturadas | En claro en la base local hasta sincronizar |
| Al cerrar sesión | Se borran los datos personales, el padrón y el filtro. Si hay envíos pendientes, se conserva solo lo pendiente para no perder el trabajo |

**Lo que falta, dicho con todas las letras:** el archivo de la base local **no está
cifrado completo**. Eso exige cambiar el motor por uno con SQLCipher y rehacer la capa
de datos; está documentado y pendiente.

---

## 4. Límites y abuso

| Recurso | Tope | Ámbito |
|---|---|---|
| Ingreso | 40 por minuto | Por origen |
| Consultas anónimas | 240 por hora | Por origen |
| Usuario autenticado | 1.000 por hora | Por usuario |
| Cuestionario de capacitación | 600 por hora | Público |
| Consulta de versión del móvil | 300 por hora | Público |

Están calibrados a la escala de la entidad, no a la de una persona: muchos usuarios
salen por la misma IP institucional. Antes del 12-sep **no contaban nada**, porque el
WAF envía la IP con el puerto y cada petición parecía venir de un cliente distinto.

---

## 5. La ruta hacia el sistema anterior (Oracle)

- SICAV **no escribe directo** en las tablas del legado: usa sus **procedimientos
  oficiales**, en el mismo orden que el aplicativo anterior, y **verifica cada paso con
  una consulta posterior**, porque esos procedimientos confirman por dentro y se tragan
  sus propios errores.
- La escritura automática está **apagada por configuración**. Se enciende cuando haya
  respaldo confirmado y aval de la operación.
- Las lecturas (padrón, universo, hechos, fechas) usan los enlaces autorizados por la
  entidad y quedan registradas.

---

## 6. Lo que NO está resuelto (y de quién es)

| Pendiente | De quién | Riesgo si sigue así |
|---|---|---|
| **Constancia de los respaldos de PostgreSQL**, pedida desde junio | Infraestructura | El mayor del proyecto: sin respaldo probado, una falla del servidor se lleva la operación |
| Cifrado completo del archivo local del teléfono | Nuestro | Un equipo comprometido entrega respuestas de entrevistas (ya no nombres ni documentos) |
| Procedimiento de custodia y rotación de la llave de cifrado del servidor | Nuestro + Seguridad de la Información | Perder esa llave es perder el acceso a los datos cifrados, sin remedio técnico |
| Segundo factor para perfiles administrativos | Por evaluar | Una contraseña robada de un administrador abre todo |
| Integración con Auth SSO | OTI + nosotros | Hoy hay un directorio de usuarios más que mantener |
| Consentimiento del uso de IA **de la persona entrevistada** | Área de protección de datos | Hoy lo registra la encuestadora en nombre de la entrevista |
| Retención del registro de accesos | Nuestro + Seguridad | El registro crece sin política de borrado |
| Cadena de carga nocturna del sistema anterior (`F:\Encuestas`) | OTI / administrador del servidor 65 | Se pierde captura diaria desde el 16 de agosto |

---

## 7. Lo que se corrigió hoy (18-sep-2026)

- La **documentación interactiva de la API** estaba accesible sin autenticación en el
  dominio público. No exponía datos, sí el mapa completo de la API. Cerrada.
- Los **datos personales del teléfono** pasaron a estar cifrados en reposo.
- El **estado de una sesión** ya no se puede cambiar por PATCH: solo por las acciones
  (pausar, reanudar, finalizar). Antes se podía marcar COMPLETADA saltándose el cierre,
  la marca de caracterización y el libro de recaracterizaciones.
- Se quitó del móvil el paquete del SDK de Gemini, que no se usaba pero hacía pensar
  que el teléfono habla directo con el proveedor de IA.
