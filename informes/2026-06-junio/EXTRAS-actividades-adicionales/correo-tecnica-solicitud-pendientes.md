# Correo 1 — Solicitud al área técnica (OTI) · tono administrativo/humano

**Para:** Oficina de Tecnologías de la Información (OTI) / Infraestructura UARIV
**CC:** Oscar Andrés Manosalva García — Supervisor SRNI
**Asunto:** Solicitud de apoyo para publicar el sistema de caracterización (URL oficial)

---

Buen día,

Espero que se encuentren muy bien. En el marco del proyecto de la nueva solución de
**caracterización de víctimas** (panel web + aplicación móvil), les cuento que la
herramienta **ya está instalada y funcionando** en el servidor que amablemente nos
asignaron, y la estamos dejando lista para mostrarla a los directivos.

Para esa presentación y para iniciar las pruebas con el equipo, **nos haría falta su
apoyo con lo siguiente:**

1. **Una dirección web oficial con seguridad (HTTPS / “candado”).**
   Hoy estamos entrando por un enlace temporal de pruebas. Nos gustaría contar con una
   dirección institucional —por ejemplo algo como *caracterizacion.unidadvictimas.gov.co*—
   con su certificado de seguridad, para que el acceso sea estable y confiable.
   *(Técnicamente: crear el “proxy host” en el Nginx Proxy Manager del servidor apuntando
   a `30.0.1.109` puerto `8090`, y emitir el certificado TLS del dominio.)*

2. **Más adelante (cuando la Subdirección lo autorice):** la conexión a la base de datos
   del **RNI (Oracle)** para trabajar con información real. Por ahora la herramienta opera
   con datos de prueba, así que esto **no es urgente**, pero lo dejo mencionado para irlo
   previendo.

Quedo muy atento a lo que necesiten de mi parte (datos, una reunión corta para mostrarles
el avance, o cualquier requisito que deba diligenciar). Sé que tienen bastante trabajo, así
que de antemano **mil gracias** por la colaboración.

Cordialmente,

**Javier Alexander Aguilar Castro**
Contratista — Sistema de Caracterización de Víctimas SRNI
Contrato 2226-2026 · Unidad para las Víctimas
