# ACTA DE CONSTITUCIÓN DEL PROYECTO

**Unidad para la Atención y Reparación Integral a las Víctimas (UARIV)**
**Plan Estratégico de Tecnologías de la Información — PETI 2026**

| Campo | Detalle |
|---|---|
| **Nombre del proyecto** | Modernización de la entrevista de caracterización — Aplicación Móvil (APK) |
| **Código del proyecto** | PRY-0662064 — Modernizacion_entrevista_caracterizacion-APK |
| **Fecha de elaboración** | 18 de junio de 2026 |
| **Área / dependencia** | Red Nacional de Información (RNI) — VIVANTO / Oficina de Tecnologías de la Información (OTI) |
| **Patrocinador (Sponsor)** | [Por completar — directivo patrocinador] |
| **Gerente / Referente del proyecto** | Javier Alexander Aguilar Castro |
| **Versión del documento** | 1.0 |

---

## 1. Propósito y justificación del proyecto

El proceso de **caracterización de víctimas** requiere una herramienta moderna que permita su
diligenciamiento **en campo**, incluso en **territorios sin conectividad**, reduciendo reprocesos
y errores de transcripción, y aprovechando la información que el **Registro Único de Víctimas
(RUV/RNI)** ya posee.

El proyecto moderniza el instrumento de caracterización mediante una **aplicación móvil
Android (offline-first)** para los encuestadores en territorio y un **panel web** de gestión y
supervisión, integrados con un **backend** institucional, garantizando la **trazabilidad y
protección de datos personales (Ley 1581 de 2012)**.

## 2. Objetivos del proyecto

**Objetivo general:** Modernizar la herramienta de caracterización de víctimas mediante una
solución móvil + web, con capacidad de operación sin conexión y sincronización posterior,
integrada con el RNI.

**Objetivos específicos:**
1. Desarrollar una **APK Android** que permita realizar la caracterización **en campo y sin internet** (pre-carga de datos + captura offline + sincronización al recuperar señal).
2. Implementar un **backend (API)** que gestione víctimas, hogares, instrumentos, sesiones de encuesta, usuarios y auditoría.
3. Entregar un **panel web** de administración, supervisión y reportes.
4. **Reutilizar la información del RUV** para no re-preguntar lo ya registrado (identidad, grupo familiar, hechos victimizantes).
5. Garantizar la **seguridad y trazabilidad** de los datos personales conforme a la Ley 1581 de 2012.

## 3. Alcance

**Incluido:**
- Backend (API REST) con sus módulos: víctimas, hogares, encuestas, formulario/instrumentos, paramétricas, autenticación y auditoría.
- Aplicación móvil **Android** (entrevista de caracterización, modo **offline** con pre-carga y sincronización).
- **Panel web** (administración de usuarios, supervisión, reportes).
- Soporte de **múltiples instrumentos** de caracterización.
- Infraestructura de **despliegue** en el servidor institucional.

**Excluido (fases posteriores / fuera de este alcance):**
- Aplicación para **iOS** (se evaluará posteriormente; requiere cuenta de desarrollador Apple).
- Integración productiva con **Oracle/RUV real** (dependiente de la habilitación de la OTI).
- Exposición a **internet** del servicio (en trámite por comité de cambios).

## 4. Entregables principales

- Aplicación móvil Android (APK) distribuible.
- Backend / API en operación.
- Panel web de gestión y supervisión.
- Mecanismo de operación **offline** (pre-carga + sincronización).
- Documentación técnica y de despliegue.

## 5. Interesados (stakeholders)

| Rol | Responsable |
|---|---|
| Patrocinador | [Por completar] |
| Referente / Gerente del proyecto | Javier Alexander Aguilar Castro |
| Desarrollo frontend (panel web) | Brando |
| Supervisión funcional (UARIV) | Oscar |
| Oficina de Tecnologías de la Información (OTI) | Infraestructura / despliegue / accesos |
| PMO — Gestión de proyectos PETI | Rommey Edwin Ruiz Rivera |
| Usuarios finales | Encuestadores / referentes territoriales |

## 6. Hitos de alto nivel

| Hito | Fecha estimada |
|---|---|
| Constitución del proyecto (Iniciación) | Junio 2026 |
| Reunión de seguimiento PETI | **Martes 23 de junio de 2026, 9:00–11:00 a.m.** |
| Versión funcional de la APK en pruebas | [Por completar] |
| Habilitación de accesos OTI (dominio/internet, Oracle) | [Por completar — dependiente de comité de cambios] |
| Despliegue / salida a producción | [Por completar] |

## 7. Supuestos

- La OTI habilita la infraestructura, accesos y publicación requeridos.
- Se dispone de la información del RUV/RNI para integración.
- El equipo de desarrollo y los referentes territoriales están disponibles según cronograma.

## 8. Restricciones

- Cumplimiento obligatorio de la **Ley 1581 de 2012** (protección de datos personales — datos de víctimas).
- Servidor institucional **compartido**; uso de red privada (VPN) y dominio institucional.
- Distribución inicial **solo Android**.
- Publicación a internet sujeta a **comité de cambios**.

## 9. Riesgos de alto nivel

| Riesgo | Mitigación |
|---|---|
| Dependencia de la OTI para accesos (internet/dominio, Oracle) | Gestión temprana por comité de cambios; uso de entornos internos mientras tanto |
| Conectividad en territorio | Arquitectura **offline-first** (pre-carga + sincronización) |
| Seguridad de datos PII | Cifrado, hash de documentos, auditoría, minimización de datos |
| Integración con RUV/Oracle real pendiente | Diseño desacoplado por repositorio (mock → Oracle sin reescritura) |

## 10. Presupuesto / recursos

[Por completar — recurso humano del equipo de desarrollo, infraestructura institucional y demás recursos según PETI.]

## 11. Criterios de éxito

- La APK permite caracterizar **en campo y sin internet**, sincronizando sin pérdida ni duplicación de datos.
- Reutilización efectiva de la información del RUV (menos re-preguntas, menos errores).
- Cumplimiento de la normativa de protección de datos.
- Adopción por parte de los encuestadores/referentes territoriales.

## 12. Aprobaciones

| Nombre | Rol | Firma | Fecha |
|---|---|---|---|
| [Patrocinador] | Patrocinador | | |
| Javier Alexander Aguilar Castro | Gerente / Referente del proyecto | | |
