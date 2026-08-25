# Borrador de respuesta a QA — informes v2 (APK y WEB)

> **Para:** Jorge (QA) · **De:** Javier Aguilar (desarrollo SRNI) · **Fecha:** 25-ago-2026
>
> ✅ **Listo para enviar.** El despliegue quedó completo y verificado en producción
> el 25-ago 20:10 (por el dominio `caracterizacion.unidadvictimas.gov.co`):
> backend con los arreglos, `backfill_porcentaje` corrido, panel reconstruido con
> el merge de Brando (`tsc` limpio), **APK 1.2.3** publicada y descargable
> (78.761.973 bytes), y `/api/movil/version/` respondiendo **1.2.3**. Todo lo que
> el correo afirma está en el aire.

---

**Asunto:** Respuesta a los informes de regresión v2 — APK (IGED-QA-C003) y WEB (IGED-QA-C002)

Jorge, buen día. Gracias por las dos versiones v2. Varios hallazgos resultaron
tener una causa distinta de la reportada, así que en lugar de parchar el síntoma
fuimos a la raíz. Resumen por informe.

## Informe WEB (IGED-QA-C002 v2) — listo para reprobar

- **H-024 (búsqueda lenta / intermitente):** la causa era una consulta que
  recorría los 12 millones de registros del universo sin usar el índice (medido:
  ~5,8 s). Ya usa el índice (~2 ms) y no repite la misma persona. **Corregido.**
- **H-010 / H-011 ("undefined sesión(es)" y "Página 1 de NaN"):** corregido por
  los dos lados — el backend ahora entrega el conteo y el panel tiene además un
  respaldo. **Corregido.**
- **H-025 (persona repetida al buscar):** se colapsan los registros que son la
  misma persona, con el mismo criterio de la búsqueda de víctimas. **Corregido.**
- **H-027 (aviso de búsqueda):** **Corregido.**

El panel queda listo para una nueva pasada.

## Informe APK (IGED-QA-C003 v2)

- **APK-002 (conformar hogar, crítico):** no era intermitente ni de red. Eran tres
  rechazos del propio servidor —documento repetido, documento sin tipo, y
  género/estado vacíos—. Los tres corregidos, con prueba de regresión. Además, el
  mensaje que veían en pantalla ahora es el del servidor (por ejemplo, "el hogar
  es de otro encuestador"), no un texto genérico. **Corregido.**
- **APK-005 (sesión "Completada" en 0 %, crítico):** el cálculo dividía por todas
  las preguntas obligatorias sin descontar las que las reglas del formulario
  mantienen ocultas. Corregido de raíz, y además **recalculamos las sesiones ya
  guardadas** para que las que ya estaban en 0 % muestren su valor real.
  **Corregido.**
- **APK-006 (barras que se desbordan):** **Corregido.**
- **APK-001 y APK-007:** corregidos; les pedimos confirmarlos en el dispositivo.
- **APK-003 (modo sin conexión):** además de las tres pantallas reportadas,
  encontramos y cerramos dos defectos que habrían hecho engañosa una reprueba: la
  app se salía del sistema al abrir sin señal, y el filtro del universo no se
  descargaba. **Ahora sí está listo para probar sin conexión**; adjuntamos un
  guion corto para esa prueba.
- **APK-019 (falla intermitente al consultar el RNI):** agregamos instrumentación
  para poder diagnosticarla (antes el error se veía siempre igual, sin código).
  La estamos midiendo en el servidor para acotar la causa.
- **APK-004 (editar/eliminar integrante):** *quitar* ya está; sobre *editar*
  tenemos una consulta —¿estaba en el levantamiento inicial?— para definir si se
  incluye o se cierra como fuera de alcance.

## Un punto que nos costó a todos

La APK ahora **muestra su versión en el pie del login**. La versión a reprobar es
la **1.2.3**. Con eso, en el próximo informe podemos amarrar cada hallazgo a un
binario exacto y evitamos la ambigüedad de la ronda pasada.

Quedamos atentos para coordinar la fecha de la reprueba una vez confirmemos el
despliegue. Gracias de nuevo por el detalle de los reportes.

Un saludo,
Javier Aguilar — Desarrollo SRNI
