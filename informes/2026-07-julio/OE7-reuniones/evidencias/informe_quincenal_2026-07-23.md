# Informe quincenal — SICAV Móvil / SRNI

> **Proyecto:** PRY-0662064 — Modernización de la entrevista de caracterización (UARIV)
> **Período:** 9 – 23 de julio de 2026 · **Corte:** 2026-07-23
> **Equipo:** Javier Aguilar (desarrollo + arquitectura) · Brando (frontend web) ·
> Oscar (supervisión funcional, UARIV)
> **Actividad:** 33 commits (23 backend/migración · 10 frontend web)

---

## 1. Resumen ejecutivo

La quincena estuvo dominada por el **frente que abre el camino a producción real: la
migración de SICAV al sistema oficial de la UARIV (Oracle "RNIENTREVISTA")**. Se pasó de
la idea al mecanismo funcionando, **con dato real y en modo 100% seguro**:

- ✅ Se **portó la lógica del sistema viejo (PL/SQL) a nuestro backend (Django)** — 24/24
  pruebas de equivalencia.
- ✅ Se levantó una **réplica local del sistema Oracle** y se **cargó su catálogo real
  completo** (sin datos de personas) para validar sin tocar producción.
- ✅ Se **alineó el instrumento (las preguntas/opciones de la app) al manual oficial** y
  se **reconciló con el sistema viejo**, corrigiendo desalineaciones históricas.
- 🔒 **No se escribió absolutamente nada en el sistema real** — todo el trabajo es de
  lectura/prueba (DRY-RUN). **101 pruebas automáticas en verde.**

En paralelo, el **frontend web (Brando)** cerró una tanda de mejoras de usabilidad y
calidad de datos.

---

## 2. Migración a Oracle legacy — el frente principal

**Objetivo:** que la app moderna (SICAV) pueda registrar la caracterización en el sistema
oficial de la Unidad, **invocando sus procedimientos oficiales** (sin atajos), conviviendo
con el sistema viejo en vez de reemplazarlo de golpe (estrategia *strangler-fig*).

| Hito | Resultado |
|---|---|
| **Lógica portada a Django** | Los 5 bloques de reglas del sistema viejo (PL/SQL) reescritos como servicios propios, con **24/24 pruebas de paridad**. La lógica sale de la base de datos y queda en el backend. |
| **Réplica Oracle local** | Contenedor con la **estructura real** de RNIENTREVISTA para validar sin producción. |
| **Catálogo real completo** | Se trajo el catálogo de preguntas/respuestas oficial (**9.316 filas, sin PII**) por lectura directa, **sin dejar huella en producción**. Cerró el bloqueo de un catálogo que estaba incompleto. |
| **Traductor SICAV → Oracle** | Motor que cruza las respuestas de la app con los identificadores reales del sistema viejo **por significado/manual, nunca a ciegas**. **160 equivalencias curadas y verificadas** (todas existen y son escribibles). |
| **Escritura (DRY-RUN)** | Los 5 pasos (hogar → persona → miembro → territorio → respuesta) corren de punta a punta en **modo simulación**, sin escribir una sola fila en el sistema real. |

**Principio de seguridad:** nunca se inventa un valor; lo que no está confirmado se marca
como pendiente. Solo avanza lo verificado. Cero escrituras en producción.

---

## 3. Instrumento — alineación al manual oficial

Se auditó y corrigió el instrumento de la app contra el **manual oficial (11-MU / 14-MU)**,
que es la autoridad. Correcciones aplicadas (con respaldo de manual, revisadas por pares):

- **21 etiquetas de opciones** corregidas (errores de digitación y de redacción) para que
  la app coincida exactamente con el manual — p. ej. "responsable del hogar" vs "jefe",
  niveles educativos, tipos de vivienda.
- **Reenganche de preguntas mal vinculadas** al sistema viejo: el bloque de **Ayuda
  Humanitaria** completo estaba apuntando a preguntas equivocadas (rehabilitación); se
  corrigió y se **evitó un riesgo real de contaminar datos** de otro capítulo.
- **Separación de una opción** ("Atención médica y psicosocial" → dos opciones) para
  calzar con el sistema oficial, sin pérdida de información.
- Se verificó que **7 de 8 perfiles** tienen la app y su base de datos **100% alineadas**.

> **Hallazgo de calidad (regalo colateral):** el cruce con el manual detectó desalineaciones
> que llevaban tiempo sin verse. La regla del proyecto —**consultar el manual antes de
> escalar**— evitó varias falsas alarmas.

---

## 4. Frontend web (Brando)

Tanda de mejoras de usabilidad y robustez del panel de analistas/QA:

- **Normalización de nombres** a formato título en varias pantallas (paramétricas).
- **Detalle de sesión**: agrupación de respuestas por miembro del hogar.
- **Robustez de datos**: protección de campos vacíos (elimina "undefined"/"NaN" en pantalla).
- **Gestión de usuarios**: modal de confirmación para activar/desactivar.
- **Login y búsqueda**: preservación de mayúsculas, notificaciones tipo *toast*, paginación.

---

## 5. Infraestructura y datos

- **Fixture de 10 hogares** listos para caracterización (datos de prueba, sin PII).
- **Usuarios de demostración** con rol de administrador para QA (Jorge) y documental (Karen).
- Réplica Oracle local operativa para validación continua.

---

## 6. Métricas de la quincena

| Métrica | Valor |
|---|---:|
| Commits | **33** (23 backend/migración · 10 frontend) |
| Pruebas automáticas (migración) | **101 en verde** |
| Paridad de lógica portada | **24/24** |
| Catálogo Oracle cargado (local, sin PII) | **9.316 filas** |
| Equivalencias SICAV→Oracle curadas | **160** |
| Escrituras en producción | **0 (DRY-RUN)** |
| Instrumentos app↔base alineados | **7 / 8** |

---

## 7. Riesgos y pendientes

| Tema | Estado |
|---|---|
| **Acceso a producción (VPN)** | Intermitente; hoy caída. Bloquea validaciones puntuales contra prod. |
| **Rotar clave de RNIENTREVISTA** | Se usó para lectura; se rotará al cerrar la migración (coordinar con OTI). |
| **Decisiones de negocio** | Oscar **delegó a Javier** la resolución; varias ya cerradas, quedan 1-2 puntuales. |
| **Escritura real a Oracle** | Sigue **desactivada** a propósito hasta cerrar los pendientes de negocio. |

---

## 8. Próximos pasos

1. Cerrar los últimos pendientes de negocio del catálogo (mapeos puntuales).
2. Completar el soporte de preguntas Sí/No en la capa de escritura.
3. Coordinar con OTI el acceso estable a producción y la rotación de credenciales.
4. Preparar el **Escalón 1**: escribir 1 hogar de prueba contra la réplica local (con
   aprobación), como ensayo previo a producción.

---

*Todo el trabajo de migración se mantiene en modo simulación (DRY-RUN): a la fecha no se ha
escrito ningún dato en el sistema oficial. El instrumento de la app quedó alineado al manual
y respaldado en los dos repositorios (GitHub + Azure).*
