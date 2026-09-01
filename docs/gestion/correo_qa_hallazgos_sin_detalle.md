# Solicitud a QA — seis hallazgos sin descripción (informe v1)

**Estado:** listo para enviar
**Para:** Jorge L. Cardona Gregory — Calidad / QA
**CC:** Brandon (panel web)
**Asunto:** Informe de calidad v1 — seis hallazgos sin detalle: ¿siguen abiertos?
**Fecha:** 1 de septiembre de 2026

---

Jorge, buen día.

Al hacer el cierre de pendientes del panel web quedó una bolsa que no podemos resolver de
nuestro lado y que lleva abierta desde junio.

El **informe de calidad v1** trajo 23 hallazgos. De esos, **seis llegaron sin descripción**:

> **H-003 · H-005 · H-006 · H-015 · H-016 · H-018**

En su momento se solicitó la ampliación y no llegó. Revisado hoy el repositorio completo, de
esos seis **no existe una sola línea** que diga qué se observó, en qué pantalla ni con qué
usuario. Solo consta que existen. No están corregidos ni descartados: están en el aire.

## Lo que pedimos

Para cada uno, lo mínimo para poder trabajarlo:

- **Qué se vio** y **qué se esperaba**.
- **Pantalla o endpoint** donde ocurrió.
- **Rol** con el que se estaba navegando (encuestador, supervisor, coordinador,
  documentador o administrador — hoy son cinco perfiles distintos y el comportamiento
  cambia entre ellos).
- **Pasos para reproducirlo**, aunque sean tres líneas.

## Una alternativa, si el detalle ya no está disponible

Entendemos que puede no quedar registro: pasaron dos meses y de por medio llegó el
**informe v2** (IGED-QA-C002 y C003), cuyos doce hallazgos ya están cerrados.

Si esos seis hubieran seguido vivos, lo razonable es que hubieran reaparecido en la segunda
pasada. **Proponemos entonces darlos por superados por el informe v2**, dejando constancia
escrita de la decisión y de que se cierran por falta de detalle, no por haberse verificado.

Nos sirve cualquiera de las dos salidas. Lo que no ayuda es que seis hallazgos queden
indefinidamente sin estado: no se pueden corregir, no se pueden descartar, y ensucian
cualquier conteo de calidad que hagamos.

## Contexto de lo que sí quedó cerrado

Para que la respuesta se dé sobre terreno conocido:

- Los **doce hallazgos del informe v2** están cerrados: siete de la aplicación móvil y cinco
  del panel.
- El **403 del Supervisor** en Hogares, Encuestas y Reportes —que el propio equipo había
  documentado como bug conocido— **ya no ocurre**; se verificó contra el código el 1 de
  septiembre.
- La **matriz de permisos por rol** dejó de ser una lista de chequeo manual: hoy es una
  batería automática de 61 comprobaciones que corre con cada cambio, sobre los cinco perfiles
  reales de producción.

Quedamos atentos.

Cordialmente,

**Javier Alexander Aguilar Castro**
Arquitectura y desarrollo — SICAV / SRNI · Contrato 2226-2026

---

## Nota interna (no enviar)

Si a la vuelta de una semana no hay respuesta, la recomendación es **cerrarlos como superados
por el v2** y anotarlo en `docs/frontend/estado-actual.md`. Un hallazgo sin descripción no es
accionable, y mantenerlo abierto solo distorsiona el semáforo de calidad. Lo importante es que
el cierre quede escrito como lo que es —falta de detalle— y no como verificación.
