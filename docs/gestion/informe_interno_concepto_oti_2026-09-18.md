# Concepto técnico de la OTI — qué es cierto y qué no

**Interno. Para Javier.** 18 de septiembre de 2026.
Verificación afirmación por afirmación contra el repositorio y el despliegue real.
La respuesta al correo está en [`correo_respuesta_oti_sso_alineacion_2026-09-18.md`](correo_respuesta_oti_sso_alineacion_2026-09-18.md);
el documento que se les adjunta, en `entregables/2026-09-18-oti-arquitectura/`.

---

## 1. Resumen: el concepto está bien hecho

De 23 afirmaciones verificadas: **17 ciertas**, 2 desactualizadas, 3 a matizar y
**1 falsa**. No hay nada malintencionado ni ningún ataque a lo que construimos; leyeron
el repositorio con cuidado. Dos de sus tres observaciones finales son ciertas y ya las
teníamos anotadas.

Lo importante: **la recomendación de fondo es correcta y nos conviene**. Integrar Auth
SSO antes que la interoperabilidad con Unidad en Línea es el orden bueno, y el trabajo
de nuestro lado es acotado.

## 2. Lo que hay que corregirles

| Afirmación | Realidad | Por qué importa |
|---|---|---|
| «La fuente de víctimas es un repositorio de prueba (mock) a la espera de la fuente oficial» | **Desactualizado, y la culpa es nuestra:** la frase sale textual de `informes/2026-06-junio/OE4-arquitectura/solicitud-oti-urls-y-bd.md:70-74`, que les enviamos en junio. Producción usa el padrón real desde agosto | Deja la impresión de que el sistema está en maqueta. Conviene reconocer el origen en vez de tratarlo como error de ellos: citaron bien nuestra propia documentación |
| «Almacenamiento de documentos en MinIO (S3)» | **Falso.** Se evaluó y se descartó; los archivos van a disco. Quedaron variables muertas en el `.env` que lo sugieren | Menor, pero es un dato de arquitectura equivocado que se va a repetir en otros documentos |
| «Refresh de 8 horas» | **Desactualizado.** Producción usa 7 días, justamente por las jornadas sin señal | Relevante para la discusión de SSO: es el punto donde su esquema puede rompernos la operación |
| «Cifrado de campos PII» | **Matizar.** Es Fernet propio sobre los identificadores, con búsqueda por hash; no es pgcrypto ni cifrado de toda la base | Que no quede la idea de que la base entera está cifrada |
| «Roles: encuestador, coordinador, supervisor, administrador» | **Incompleto.** Son cinco: falta DOCUMENTADOR (solo lectura) | Importa para el mapeo de claims cuando llegue el SSO |
| «Distribución por EAS Build con QR» | **Matizar.** La APK se sirve desde nuestro propio servidor y cada descarga queda auditada | Los diferencia de «bajar un APK de internet», que es como suena |

## 3. Lo que ellos vieron y nosotros teníamos pendiente

1. **Cifrado del SQLite del móvil:** cierto, sigue pendiente y documentado como tal.
   Mitigación real: el padrón local se consulta por documento hasheado y al cerrar
   sesión se borran los datos personales.
2. **IA y protección de datos:** cierto que amerita concepto. Y hay un matiz que ellos
   no vieron y que conviene levantar nosotros antes de que lo levante otro: **el
   consentimiento lo registra la encuestadora, no la persona entrevistada**. Está
   auditado y con huella, pero no es lo mismo. Mejor plantearlo nosotros.

## 4. Hallazgo propio de esta revisión (hay que arreglarlo)

**La documentación interactiva de la API (`/api/docs/`, `/api/schema/`, `/api/redoc/`)
está accesible sin autenticación en producción.** No expone datos, pero sí el mapa
completo de la API a cualquiera que abra el dominio. Es un arreglo de dos líneas
(permisos de servicio del generador de esquema). Conviene hacerlo **antes** de mandar la
respuesta, para poder decir «ya está corregido» en vez de «lo vamos a corregir».

Segundo hallazgo menor: el paquete del SDK de Gemini sigue declarado en las dependencias
del móvil aunque no se usa (la ruta real es el proxy del backend). Si alguien audita el
`package.json` va a concluir que el teléfono habla directo con Google. Hay que quitarlo.

## 5. Sobre el SSO: qué nos cuesta y qué hay que exigir

**Nos cuesta poco.** Hoy firmamos con HS256 y llave propia. Aceptar un emisor externo
son dos cambios localizados: configuración de validación (algoritmo asimétrico, URL de
llaves, emisor y audiencia) y una clase de autenticación que mapee la identidad del
token al usuario que ya existe. Las cuentas reales ya están creadas.

**Lo que hay que exigir**, y no como detalle sino como condición:

1. **Vigencias compatibles con campo.** Una jornada dura horas sin señal. Si la sesión
   del SSO expira en campo, se pierde la jornada completa. Necesitamos refresco de
   varios días y revalidación al sincronizar.
2. **Flujo OIDC con código de autorización + PKCE.** Si el Auth API no lo soporta,
   integrarlo desde una app móvil es artesanía insegura. Que lo confirmen por escrito.
3. **Que la autorización siga siendo nuestra.** Ellos ponen la identidad; qué puede
   hacer cada perfil es del negocio y vive en SICAV.

**Riesgo a vigilar:** que la integración se vuelva la excusa para frenar la operación
actual. La respuesta propone mesa técnica y prueba de concepto en ambiente de pruebas,
sin tocar producción mientras tanto.

## 6. Lo que aprovechamos para poner sobre la mesa

El correo es la oportunidad de dejar por escrito, ante la OTI y con copia a la PMO, dos
cosas que llevan semanas sin dueño:

- **La cadena de carga nocturna del aplicativo heredado lleva caída desde el 16 de
  agosto** (caso 14512) y se sigue perdiendo captura diaria. No es nuestro componente y
  la ventana de recuperación de los archivos se cierra hacia el 12 de octubre.
- **El respaldo del legado y el aval formal** para encender la escritura automática.
  Mientras no estén, la ruta seguirá apagada y eso hay que decirlo con nombre propio.

## 6-bis. Documentos que hay que actualizar (de aquí salió el malentendido)

La OTI no se equivocó: leyó lo que nosotros escribimos. Cuatro archivos siguen diciendo
que la fuente es de prueba o que falta desplegarla:

| Archivo | Qué dice hoy |
|---|---|
| `informes/2026-06-junio/OE4-arquitectura/solicitud-oti-urls-y-bd.md:70-74` | «usa un repositorio de datos de prueba (mock)… diseñada para conectarse a Oracle cuando la Subdirección lo autorice» |
| `docs/ciclo_completo_tablas.md:137` | «corregido, falta desplegar» — ya se desplegó |
| `docs/arquitectura/plan-offline-precarga.md:118` | menciona el repositorio de prueba |
| `docs/gestion/acta-constitucion-PRY-0662064.md:107` | ídem |

Además, aquel documento planteaba consultar Oracle **en vivo**; lo implementado carga el
padrón a PostgreSQL y lo consulta desde ahí, que es lo único compatible con operación
sin conexión. Ese cambio de enfoque nunca se les comunicó por escrito, y conviene hacerlo
en esta respuesta.

## 7. Siguiente paso sugerido

1. Restringir la documentación de la API (hoy).
2. Enviar la respuesta con el informe adjunto.
3. Pedir la mesa técnica de una hora esta semana.
4. Actualizar los documentos de sprints que todavía dicen «mock» — es de donde salió el
   malentendido.
