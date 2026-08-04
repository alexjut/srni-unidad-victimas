# Correo/mensaje a OTI — Consulta sobre `UARIV.AUTH.API` para el acceso de los encuestadores

> Borrador para revisión de Javier. **No es una solicitud de accesos todavía:** es una
> pregunta de una línea que decide el diseño. Si la respuesta es "sí", nos ahorra montar
> un segundo mecanismo de credenciales y un relay SMTP. Si es "no", volvemos al correo.
>
> Contexto propio (no va en el correo): SICAV tiene **1.150 cuentas de encuestadores
> creadas** con su identidad real, cada una con su trabajo histórico asociado, y **sin
> contraseña a propósito** (`set_unusable_password()`). No se copió la credencial de
> Vivanto ni se inventaron claves. Es lo único que impide que entren.

---

**Para:** [OTI — responsable de `auth-api` / `crunidad.azurecr.io`]
**CC:** Oscar [supervisión funcional UARIV] · [PMO — Rommey Ruiz]
**Asunto:** Consulta — uso de `UARIV.AUTH.API` para la autenticación de encuestadores en SICAV (PRY-0662064)

Estimados,

En el marco del **PRY-0662064**, **SICAV** ya tiene creadas las cuentas de los
**1.150 encuestadores activos**, con su identidad tomada del directorio institucional y
con su trabajo histórico asociado —cada uno entra y ve sus propias caracterizaciones—.

Deliberadamente **no les asignamos contraseña**: no replicamos la credencial de otro
sistema ni generamos claves nosotros. Antes de definir cómo se entrega el acceso, vimos
que en el mismo servidor donde opera SICAV (`30.0.1.109`) está desplegada y activa la
**`UARIV.AUTH.API`**, que expone autenticación por usuario/contraseña y SSO con Entra ID.

Antes de proponer cualquier integración, quisiéramos confirmar con ustedes:

1. **¿Los encuestadores de campo están en el directorio de usuarios de `UARIV.AUTH.API`?**
   Es la pregunta que decide todo. Nuestro padrón de encuestadores proviene de
   `ADMINUSUARIOS` (Vivanto); si `AUTH.API` resuelve contra ese mismo directorio, los
   1.150 podrían autenticarse sin que nadie administre un segundo juego de credenciales.
2. **¿Nos autorizan a consumirla desde SICAV**, y bajo qué condiciones? De ser así, cómo
   se emiten las credenciales de cliente y cuál es el tiempo de vida del `access_token`
   y del `refresh_token`.
3. **¿Es el mecanismo institucional recomendado** para una aplicación como SICAV, o hay
   otro camino previsto que debamos seguir?

Si la respuesta a la primera es negativa, la alternativa es el **restablecimiento de
contraseña por correo**, y en ese caso necesitaríamos de ustedes un **relay SMTP
institucional** (servidor, puerto, credencial y habilitación de salida desde el
servidor `30.0.1.109`), que hoy SICAV no tiene configurado.

Quedamos atentos. Con gusto ampliamos en una llamada corta si resulta más ágil.

Cordialmente,
**Javier Aguilar** — Desarrollo y arquitectura, SICAV / SRNI (PRY-0662064)

---

### Notas para Javier (no enviar)

- **Lo que NO hicimos, y conviene poder decirlo si preguntan:** no se inspeccionaron las
  variables de entorno ni la cadena de conexión del contenedor `uariv-auth-api`, y **no
  se probó ninguna credencial contra el servicio**. Solo se leyó el `swagger.json` que
  publica. El sondeo se detuvo justo donde empezaba infraestructura de otro equipo.
- **El contrato que ya conocemos** (de su propio swagger, 16 rutas, seguridad `Bearer`):
  `POST /auth/AuthByUser {userName, password}` → `{success, access_token, refresh_token,
  errors[]}`; además `POST /auth/AuthByEntraId`, el flujo OIDC `/auth/start` ·
  `/auth/callback` · `/auth/result`, y `PUT /api/User/ChangePassword`.
- **Por qué no copiamos el hash de Vivanto** (por si lo proponen como atajo): el
  directorio ya trae política de credenciales completa —caducidad, conteo de intentos,
  bloqueo, desbloqueo automático y cambio forzado—. Replicar la clave nos obligaría a
  replicar toda esa política o a quedar desincronizados: un usuario bloqueado allá
  entraría igual acá, y una clave caducada seguiría sirviendo.
- **Lo que queda de nuestro lado aunque digan que sí:** el campo trabaja **sin señal**.
  Un login en línea resuelve la primera entrada, no la jornada offline. Hay que diseñar
  autenticación en línea la primera vez + credencial derivada en el dispositivo. Es
  trabajo nuestro, no de OTI, y no está hecho.
- **Se puede fusionar** con el correo de convocatoria a pruebas
  (`correo_convocatoria_pruebas_funcionales_2026-08-04.md`), que ya lleva a OTI en CC y
  una consulta pendiente sobre hechos victimizantes. Si preferís un solo envío, lo
  integro como tercer punto.
