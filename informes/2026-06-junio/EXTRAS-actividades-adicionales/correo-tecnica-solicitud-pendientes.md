# Correo 1 — Para la OTI: lo que nos falta (resumen fácil)

**Para:** Oficina de Tecnologías de la Información (OTI) / Infraestructura UARIV
**CC:** Oscar Andrés Manosalva García — Supervisor SRNI
**Asunto:** Apoyo para publicar el sistema de caracterización — resumen de lo pendiente

---

Buen día,

Espero que estén muy bien. Les escribo para resumirles **de forma sencilla lo único que
nos falta** para dejar publicado el nuevo sistema de caracterización (ya está instalado y
funcionando en el servidor que nos asignaron):

**1. Una dirección web oficial con seguridad (HTTPS / candado).**
Hoy entramos por un enlace temporal de pruebas. Necesitaríamos una dirección institucional
—por ejemplo *caracterizacion.unidadvictimas.gov.co*— con su certificado de seguridad.
> *Para el equipo técnico:* crear el “proxy host” en el Nginx Proxy Manager del servidor
> apuntando a `30.0.1.109:8090` y emitir el certificado TLS del dominio.

**2. (Para más adelante, no urgente) Acceso a la base de datos del RNI (Oracle).**
Por ahora trabajamos con datos de prueba, así que esto puede esperar; lo dejo anotado solo
para irlo previendo cuando la Subdirección lo autorice.

Con el **punto 1** ya podríamos mostrar el sistema a los directivos con una dirección
estable. Quedo atento a cualquier dato o formato que deba diligenciar, y con gusto les hago
una demostración corta del avance.

Mil gracias por su apoyo.

Cordialmente,

**Javier Alexander Aguilar Castro**
Contratista — Sistema de Caracterización de Víctimas SRNI
Contrato 2226-2026 · Unidad para las Víctimas
