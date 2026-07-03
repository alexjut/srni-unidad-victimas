# Resumen para diapositivas — Avance / Dificultad / Solución

> **Periodo:** últimos 20 días (21 de mayo – 10 de junio de 2026)
> **Contrato:** 2226-2026 — Sistema de Caracterización de Víctimas SRNI
> **Contratista:** Javier Alexander Aguilar Castro
> **Equipo:** Javier (backend / móvil / infraestructura / documentación) + Brando (panel web)
> **Supervisor:** Oscar Andrés Manosalva García
> **Uso:** insumo directo para presentación de avance. Cada bloque = una diapositiva con los tres factores **Avance · Dificultad · Solución**.

---

## Diapositiva 0 — Panorama del periodo

En los últimos 20 días el proyecto pasó de "desarrollo en ambiente local" a **preparación para despliegue y publicación**. Tres frentes avanzaron en paralelo:

1. **Panel web** (con Brando) — quedó funcionalmente completo: 15 pantallas operativas.
2. **Backend + app móvil** — endurecimiento pre-producción y configuración para publicación en tiendas.
3. **Gestión institucional** — solicitud del servidor UARIV y apoyo al equipo de caracterización (insumo para video de lanzamiento).

**Cifras del periodo:** ~41 commits integrados de Brando (19 + 22), 15 pantallas del panel web, 8 instrumentos cargados en la APK, 2 entregables documentales (Política de Privacidad + Manual de Uso), 2 correos institucionales (servidor) + 1 insumo para el equipo de caracterización.

---

## Diapositiva 1 — Panel web (trabajo con Brando)

**AVANCE**
- Panel web React quedó **funcionalmente completo**: 15 pantallas operativas (Login, Dashboard, Víctimas, Hogares, Encuestas, Reportes, Instrumentos, Paramétricas, Supervisión, Auditoría, Cambio de contraseña, etc.).
- Librería de **8 componentes reutilizables** (Button, Input, Select, Modal, Card, Alert, Breadcrumb, Table) + Spinner, Badge, EmptyState, Paginación y PageHeader.
- **Paramétricas completas**: mapa de departamentos + 3 tabs nuevas (veredas, comunidades negras, resguardos indígenas).
- **Reportes**: exportación a Excel con formato y modal de filtros.
- **Auditoría**: pantalla conectada a datos reales del backend.
- Revisión UI completa de las 15 páginas (diseño Apple-style / login *liquid glass*).
- Mejoras de rendimiento (**code splitting** con React.lazy) y accesibilidad (**a11y**, aria-labelledby).

**DIFICULTAD**
- El frontend necesitaba datos y campos que el backend aún no exponía (logs de auditoría, `codigo_hogar`), lo que bloqueaba el cierre de varias pantallas.
- El trabajo de Brando vivía en una rama aparte (`frontend`) y había que integrarlo sin romper `main` en los dos remotes (Azure + GitHub).

**SOLUCIÓN**
- Preparé el **backend habilitador**: endpoint `GET /api/auditoria/logs/` (con filtros, paginación y nombres en español) y `codigo_hogar` agregado en los serializers — Brando pudo cerrar las pantallas el mismo día.
- Integré sus ~41 commits con merges controlados (no fast-forward) cascadeando `main → frontend → develop` y empujando a ambos remotes.

---

## Diapositiva 2 — Backend habilitador

**AVANCE**
- Endpoint de **auditoría** `GET /api/auditoria/logs/` con 8 filtros, paginación y 386 registros reales probados.
- Campo **`codigo_hogar`** expuesto en los serializers de hogar.
- **Endurecimiento pre-producción**: control de `DEBUG`, manejo seguro de la clave de Gemini, creación de hogar idempotente.
- Suite de **pruebas resucitada** tras el desfase de esquema entre Sprint 6 y 7.

**DIFICULTAD**
- Tras los cambios de modelo (Sprint 6→7) la suite de tests quedó desalineada y dejó de pasar.
- Riesgo de exponer configuración sensible (Gemini, DEBUG) al pasar de local a un ambiente accesible.

**SOLUCIÓN**
- Realineé el esquema y reactivé las pruebas para volver a tener red de seguridad antes del despliegue.
- Endurecí la configuración por variables de entorno y dejé el hogar idempotente para evitar duplicados en sincronización.

---

## Diapositiva 3 — App móvil / APK (camino a tiendas)

**AVANCE**
- Configuración de **builds para tiendas** (`eas.json` + versionado).
- Mejoras de **robustez de sincronización** y corrección de bugs de formulario y estilos.
- **Debounce** de respuestas y navegación directa al formulario.
- APK con los **8 instrumentos oficiales precargados**, funcionamiento **offline-first** y sincronización automática.

**DIFICULTAD**
- La publicación en tiendas exige metadatos, versionado y políticas (privacidad) que aún no estaban formalizados.
- La sincronización en campo (zonas con señal intermitente) debía ser tolerante a fallos.

**SOLUCIÓN**
- Dejé listo `eas.json` y el esquema de versionado para generar los builds firmados.
- Endurecí la cola de sincronización (reintentos automáticos) y produje los entregables documentales que piden las tiendas (ver Diapositiva 5).

---

## Diapositiva 4 — Aprovisionamiento del servidor UARIV

**AVANCE**
- Envié la **solicitud formal del servidor** al supervisor y a TI/Infraestructura, con un **anexo técnico** detallado (arquitectura, componentes, privilegios, modelo de 27 tablas y marco normativo).
- TI **aprovisionó el servidor** (`30.0.1.109`, Linux / openresty) — ya responde por HTTP/HTTPS.

**DIFICULTAD**
- Con las credenciales entregadas **no se podía entrar por SSH**: el puerto 22 aparece **filtrado**.
- Diagnóstico: el equipo de desarrollo está en otro segmento de red (`172.20.x`) y, aun conectándose por VPN (IP `192.168.200.18`), el SSH sigue bloqueado, mientras que 80/443 sí pasan.

**SOLUCIÓN**
- Verifiqué que **el enrutamiento ya funciona** (el tráfico llega al servidor por el túnel VPN; 80 y 443 responden) y que **lo único pendiente es una regla de firewall para el puerto 22**.
- Preparé el **correo a la Oficina de Seguridad / Redes** solicitando habilitar SSH (22/TCP) desde la IP de VPN hacia `30.0.1.109` (ver Anexo B). Queda como trámite en curso, sin bloquear el resto del avance.

---

## Diapositiva 5 — Apoyo al equipo de caracterización (funcionales) y entregables

**AVANCE**
- Atendí la solicitud de **Difusión & Aprendizaje** (Andrea Castro) entregando el **insumo para el guion del video de lanzamiento** de la APK, redactado para **funcionarios y encuestadores** (tono operativo, funcionalidades ya construidas).
- Produje los dos **entregables documentales para la UARIV**: **Política de Privacidad** y **Manual de Uso del Encuestador**.

**DIFICULTAD**
- El material para los funcionales debía describir solo funciones **reales y operativas** (sin prometer pendientes) y en lenguaje no técnico.
- Plazo corto del requerimiento de comunicaciones (05-jun).

**SOLUCIÓN**
- Redacté el insumo a partir de funcionalidades verificadas (login biométrico, búsqueda RNI, conformación de hogar, 8 instrumentos, formulario inteligente, asistente de voz IA, offline + sincronización) y lo remití dentro del plazo, ofreciendo apoyo para la grabación de la demo (ver Anexo C).

---

## Diapositiva 6 — Cierre / próximos pasos

- **Pendiente externo:** habilitación de la regla de firewall (SSH 22) para desplegar en el servidor.
- **Listo para ejecutar:** una vez abierto el SSH, la instalación y verificación toma 2 días hábiles (stack Docker Compose reproducible).
- **En marcha:** generación automática de `codigo_hogar`, publicación de la APK en tiendas y validación funcional con el equipo de caracterización en el ambiente compartido.

---
---

# ANEXOS — Documentos de soporte citados

> Estos anexos respaldan las diapositivas 4 y 5. Los documentos completos viven en las carpetas indicadas.

## Anexo A — Correo: solicitud de aprovisionamiento del servidor

**Archivo:** `informes/2026-06-junio/OE4-arquitectura/correo-solicitud-servidor.md`
**Anexo técnico:** `informes/2026-06-junio/OE4-arquitectura/anexo-tecnico-servidor.md`

- **Para:** Oscar Andrés Manosalva García (Supervisor) · **CC:** TI / Infraestructura UARIV
- **Asunto:** Solicitud de aprovisionamiento de servidor para despliegue del sistema de caracterización (backend + panel web + distribución APK).
- **Contenido:** justificación, los 3 componentes a desplegar, especificaciones (Ubuntu 22.04, 4 vCPU, 8 GB RAM, 100 GB SSD), puertos (443 y 22 restringido), aspectos de seguridad (Ley 1581, CONPES 3995) y aclaración de que **no requiere Oracle** en esta fase.
- **Estado:** servidor aprovisionado (`30.0.1.109`).

## Anexo B — Correo: solicitud de habilitación de firewall (acceso SSH)

**Para:** Oficina de Seguridad de la Información / Redes UARIV (por intermedio del supervisor)
**Asunto:** Habilitación de regla de firewall — acceso SSH (22/TCP) a servidor 30.0.1.109

> Buen día,
>
> Ya me conecté a la **VPN** y confirmo que mi tráfico **sí llega al servidor `30.0.1.109`**: los puertos 80 y 443 responden correctamente por el túnel (IP de VPN asignada **192.168.200.18**).
>
> Sin embargo, **no puedo acceder por SSH**: el **puerto 22 (TCP) está bloqueado por firewall**, aun estando dentro de la VPN. Como el enrutamiento ya funciona, se trata únicamente de **habilitar la regla de firewall para el puerto 22**.
>
> **Solicito** habilitar el acceso **SSH (22/TCP)** desde la VPN (IP **192.168.200.18**) hacia el servidor **30.0.1.109**, usuario `admin_rni`.
>
> | Concepto | Valor |
> |---|---|
> | IP origen (VPN) | 192.168.200.18 |
> | IP destino (servidor) | 30.0.1.109 |
> | Puerto / Servicio | 22 / SSH (TCP) |
> | Usuario | admin_rni |
>
> Quedo atento. Gracias.
>
> Cordialmente,
> **Javier Alexander Aguilar Castro** — Proyecto SRNI / VIVANTO

- **Estado:** trámite en curso (pendiente de la Oficina de Seguridad).

## Anexo C — Insumo para el equipo de caracterización (video de lanzamiento)

**Correo:** `informes/2026-06-junio/EXTRAS-actividades-adicionales/correo-respuesta-andrea-castro.md`
**Insumo completo:** `informes/2026-06-junio/EXTRAS-actividades-adicionales/insumo-guion-video-lanzamiento-apk.md`

- **Para:** Andrea Estefanía Castro Ibarra (Difusión & Aprendizaje) · **CC:** Oscar Manosalva (Supervisor)
- **Asunto:** RE: lanzamiento APK - Caracterización — Insumo para guion del video
- **Audiencia:** funcionarios y encuestadores que usarán la herramienta (tono operativo).
- **Mensaje central:** la APK funciona **sin conexión** (offline-first) y **sincroniza automáticamente** al recuperar señal, protegiendo siempre los datos personales.
- **Funcionalidades destacadas:** ingreso biométrico (huella/rostro), búsqueda por documento (verifica habilitación), conformación del hogar, **8 instrumentos** precargados, formulario inteligente (salta lo que no aplica), **asistente de voz con IA** (con autorización), trabajo offline + sincronización automática.
- **Beneficios al proceso:** amplía cobertura en zonas sin conectividad, agiliza entrevistas, eleva seguridad/privacidad (Ley 1581, CONPES 3995), estandariza la captura y acelera la disponibilidad de los datos.

## Anexo D — Entregables documentales para la UARIV

**Carpeta:** `informes/2026-06-junio/OE9-adicionales/`

- **`Politica_de_Privacidad_SRNI_Encuestador.docx`** — política de privacidad para publicación/tiendas.
- **`Manual_de_Uso_SRNI_Encuestador.docx`** — manual de uso del encuestador para entrega a la UARIV.
