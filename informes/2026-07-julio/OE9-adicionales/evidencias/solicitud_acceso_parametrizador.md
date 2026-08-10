# Solicitud — acceso al Parametrizador de Web Services (consulta al RUV desde SICAV)

> **Borrador para revisión de Javier.** Fecha: 2026-07-29 · Proyecto PRY-0662064.
> **Qué se pide:** acceso de consulta al Parametrizador y confirmación de dos datos.
> **Qué NO se pide:** ni accesos a base de datos, ni un `ID_APLICACION` nuevo, ni
> desarrollo de terceros. Ya tenemos lo demás.

---

**Para:** [OTI / responsable de Vivanto y del Parametrizador de Web Services]
**CC:** Oscar [supervisión funcional UARIV] · [PMO — Rommey Ruiz]
**Asunto:** Acceso al Parametrizador de Web Services para la consulta al RUV desde SICAV (PRY-0662064)

Estimados,

En el marco del proyecto **PRY-0662064**, la aplicación **SICAV Móvil** necesita
**consultar el RUV** para que el encuestador pueda verificar a una persona por documento
antes de caracterizarla. Hoy esa consulta funciona contra un conjunto de datos de prueba;
para pasar a producción necesitamos usar el servicio oficial.

Ya identificamos el mecanismo: el **Parametrizador de Web Services**
(`https://vivantov2.unidadvictimas.gov.co/Parametrizador/`), donde están declarados los
métodos de consulta, y verificamos que **nuestra aplicación ya está registrada** en el
catálogo de Vivanto como **`309 — IGED (IGED ENCUESTA)`**.

Solicitamos:

1. **Acceso de consulta al Parametrizador** para el equipo técnico del proyecto, con el
   fin de ver la configuración de los métodos que necesitamos y sus parámetros de entrada
   y salida. Con acceso de solo lectura nos basta para empezar.
2. **Confirmación de qué métodos tiene habilitados la aplicación 309 (IGED)**, y
   habilitación —si no los tuviera— de los siguientes, que son los que cubren la consulta
   de una persona:

   | Método | Para qué lo necesitamos |
   |---|---|
   | `MI_PERSONAS_UNICA` | traer una persona por tipo y número de documento |
   | `MI_ESTADO_PERSONAS` | su estado en el RUV |
   | `ETNIA` | pertenencia étnica y pueblo |
   | `DISCAPACIDAD` | condición de discapacidad |
   | `WS SERVICIO 418` (o equivalente) | hechos victimizantes |

3. **La especificación de invocación del servicio**: URL de ejecución, formato de la
   petición y de la respuesta, y forma de autenticación de la aplicación consumidora.

### Una observación técnica que conviene revisar

Al revisar la parametrización notamos que **la mayoría de los métodos del Modelo Integrado
—incluidos `MI_PERSONAS_UNICA`, `ETNIA` y `DISCAPACIDAD`— están configurados sobre la
conexión `ConexionModeloIntegradoPru`**, mientras que solo un método usa
`ConexionModeloIntegradoProd`.

Lo señalamos porque, si esos métodos se están sirviendo desde un ambiente de pruebas,
afectaría a **todas** las aplicaciones que los consumen, no solo a la nuestra. Puede ser
que el nombre de la conexión no refleje el ambiente al que apunta —en cuyo caso basta con
que nos lo confirmen— pero preferimos reportarlo a dejarlo pasar.

Quedamos atentos.

Cordialmente,
**Javier Aguilar** — Desarrollo y arquitectura, SICAV / SRNI (PRY-0662064)

---

### Notas para Javier (no enviar)

- **Lo que ya NO hay que pedir**, y por eso no está en el correo: el `ID_APLICACION`
  (tenemos el 309), y accesos a base de datos (leemos `WS_METODOS` y `APLICACION` con lo
  que ya tenemos).
- **Si el acceso al Parametrizador demora**, hay un plan B parcial: los métodos son
  procedures (`mi_pkg_consultas.*`), así que si nos dieran conexión a la base del Modelo
  Integrado podríamos invocarlos igual que hicimos con los `GIC_*`. Pero es peor camino:
  saltarse el middleware significa saltarse su auditoría (`AU_CONSULTA_WEB_SERVICES`), y
  la consulta al RUV es de las que conviene que quede registrada a nuestro nombre.
- **Sobre la observación de `…Pru`:** está redactada como pregunta y no como reclamo a
  propósito. Puede que la conexión se llame así por herencia y apunte a producción. Si
  resulta que no, es un hallazgo que le sirve a la Unidad entera.
- El punto 3 es el que más puede demorar: si nadie tiene la especificación escrita, la
  alternativa es que nos dejen ver una llamada de ejemplo de otra aplicación que ya
  consuma el servicio (la 3 "Consulta Individual" o la 267 "WS MI_PERSONAS_RUV").
