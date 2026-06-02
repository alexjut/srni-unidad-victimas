# Correo formal — Solicitud de servidor para despliegue de aplicación de caracterización

---

**Para:** Oscar Andrés Manosalva García — Supervisor SRNI
**CC:** TI / Infraestructura UARIV (por intermedio del supervisor)
**De:** Javier Alexander Aguilar Castro — Contratista 2226-2026
**Asunto:** Solicitud de aprovisionamiento de servidor para despliegue del sistema de caracterización de víctimas (backend + panel web + distribución APK)

---

Buen día Oscar,

En el marco de la ejecución del contrato 2226-2026, en el cual estoy desarrollando la nueva solución tecnológica para el procedimiento de instrumentalización de la información en la Subdirección Red Nacional de Información (SRNI), comedidamente solicito el aprovisionamiento de **un servidor** que permita el despliegue de los tres componentes que conforman la solución:

1. **Backend** desarrollado en Django REST Framework (Python 3.12)
2. **Panel web** desarrollado en React + Vite (compilado a archivos estáticos)
3. **Distribución de la APK** del aplicativo móvil para encuestadores en campo

Este servidor se requiere para iniciar las pruebas integradas con datos reales, la validación funcional con el equipo de caracterización y la preparación del paso a producción del nuevo sistema.

---

## Justificación

La solución está terminada a nivel funcional en ambiente local de desarrollo (los tres componentes operan y se comunican entre sí). Para avanzar a las siguientes fases del contrato es necesario:

- Disponer de un ambiente accesible para el equipo de la Subdirección y para usted como supervisor, sin depender de mi equipo de desarrollo personal.
- Realizar pruebas con encuestadores en condiciones de uso real (la APK descarga la actualización desde el servidor y consume la API del backend).
- Permitir a Brando, integrante del equipo, terminar y validar el panel web contra el backend desplegado en ambiente compartido.
- Cumplir con el requisito contractual de entregar los componentes en infraestructura UARIV y no en infraestructura personal del contratista.

---

## Componentes a desplegar y su rol

| Componente | Tecnología | Función |
|------------|-----------|---------|
| Backend API | Django 5 + Django REST Framework + Gunicorn | Expone los endpoints REST que consumen la APK y el panel web. Persiste datos en PostgreSQL local del servidor. |
| Panel web | React 18 + Vite (servido como estático por Nginx) | Interfaz para supervisores y administradores. Consume el backend por HTTPS. |
| Distribución APK | Nginx sirviendo archivo `.apk` firmado | Permite al encuestador descargar e instalar la última versión desde un enlace controlado. |
| Proxy / TLS | Nginx 1.25 | Único punto de entrada externo, con certificado TLS válido. Enruta tráfico a backend y sirve panel web y APK. |
| Base de datos | PostgreSQL 15 (local en el servidor) | Persistencia operacional de la aplicación nueva. **No requiere conexión a la BD Oracle de caracterización en esta fase.** |
| Caché y cola asíncrona | Redis 7 + Celery 5 | Cola de sincronización y tareas en segundo plano. |

Todos los componentes se ejecutarán contenedorizados con Docker y Docker Compose, lo que permite reinstalación reproducible y aislamiento.

---

## Especificaciones técnicas requeridas

| Característica | Recomendación inicial | Notas |
|----------------|----------------------|-------|
| Sistema operativo | Linux Ubuntu Server 22.04 LTS o Debian 12 | Recomendado por compatibilidad con Docker y soporte de largo plazo |
| CPU | 4 vCPU | Suficiente para el volumen esperado en validación; ampliable en producción |
| Memoria RAM | 8 GB | Backend + PostgreSQL + Redis + Nginx |
| Almacenamiento | 100 GB SSD | Sistema, contenedores, BD local y backups locales |
| Conectividad de red | IPv4 pública o expuesta detrás del proxy institucional | Para que la APK pueda conectarse desde campo |
| Puertos a abrir | `443/TCP` (HTTPS), `22/TCP` (SSH restringido por IP del contratista) | El resto cerrado |
| Certificado TLS | Certificado válido para un FQDN institucional o `.uariv.gov.co` | Requerido para HTTPS |
| Acceso administrativo | Acceso SSH con clave pública para el contratista | Sin contraseña, solo llave |
| Backups | Snapshot diario o respaldo de la BD a OneDrive del supervisor | Conforme a la política de la entidad |

Estas son sugerencias razonables para arrancar; queda a criterio de TI / Infraestructura ajustarlas a los estándares vigentes de la UARIV.

---

## Aspectos de seguridad y cumplimiento

- Conexión cifrada con TLS sobre `443/TCP`. Sin HTTP en claro.
- Acceso administrativo SSH restringido por llave pública e IP de origen.
- Contraseñas y secretos almacenados como variables de entorno cifradas, no en código.
- Datos personales tratados conforme a la **Ley 1581 de 2012**, el **Decreto 1377 de 2013**, el **CONPES 3995 de 2020** y la política institucional UARIV vigente.
- Auditoría inmutable de accesos a información personal, registrada en la propia base de datos del servidor.
- Compromiso de notificar a TI cualquier incidente de seguridad detectado.
- Al término del contrato, el contratista entrega contraseñas, credenciales y código fuente al supervisor y elimina copias locales.

---

## Sobre la base de datos Oracle institucional

El despliegue solicitado en este correo **no requiere conexión a la base de datos Oracle institucional** (`RNIENTREVISTA` / `ENTREVISTARN`). La solución opera con su propia base de datos PostgreSQL local al servidor.

Cuando la solución sea evaluada por la Subdirección y se determine integrarla con el sistema histórico de caracterización, se elevará una **solicitud independiente y detallada** sobre el tipo de acceso a Oracle que se requiera, en los términos que TI y la Oficina de Seguridad de la Información indiquen. Ese trámite se hará en su momento por separado.

---

## Plazos

La aplicación está lista para ser desplegada. Si TI confirma viabilidad, una vez aprovisionado el servidor el contratista realiza la instalación y verificación en **2 días hábiles**. A partir de ahí queda disponible para uso del supervisor y del equipo de caracterización.

---

## Lo que solicito formalmente

1. **Aprobación de la solicitud** en los términos descritos.
2. **Aprovisionamiento del servidor** con las especificaciones del cuadro de §"Especificaciones técnicas".
3. **Entrega por canal seguro** de:
   - Host / FQDN del servidor
   - Credenciales iniciales de acceso SSH
   - Certificado TLS y su clave (si TI lo gestiona) o autorización para que el contratista solicite uno via Let's Encrypt
4. **Designación de un punto de contacto técnico** de TI para soporte ante incidentes de infraestructura.

---

Quedo atento a cualquier observación, requisito documental adicional o ajuste que la Subdirección o TI requieran. Estoy disponible para una reunión técnica si conviene aclarar puntos en persona.

Agradezco su gestión y atención.

Cordialmente,

**Javier Alexander Aguilar Castro**
Contratista — Sistema de Caracterización de Víctimas SRNI
CC 1.030.547.250 · Contrato 2226-2026
ingaguilarsistemas@gmail.com
