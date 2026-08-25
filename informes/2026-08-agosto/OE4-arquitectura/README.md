# OE4 — Diseño e implementación de soluciones tecnológicas

> **Obligación contractual:** *Realizar el diseño e implementación de las soluciones tecnológicas y aplicativos móviles que genere la Subdirección Red Nacional de Información para el procedimiento de Instrumentalización de la Información.*

## Actividad desarrollada en este periodo

**Excepción de vigencia, de punta a punta.** La regla de recaracterizar solo cada
dos años se mantiene (es una regla real, no se derogó). Lo que cambió es **quién
autoriza la excepción** cuando un fallo, una tutela o un auto obliga a actualizar
antes: dejó de pedirse en campo —donde el encuestador no tiene a la vista el
documento de soporte— y pasó a autorizarla la **coordinación desde el panel web**;
el celular solo **consume** esa autorización. Al trazar el flujo completo se
encontró y corrigió el último eslabón que faltaba: **con señal, autorizar no
desbloqueaba la aplicación**, y ahora sí lo hace **sin necesidad de una versión
nueva** del APK (la que ya está en campo funciona). La excepción es de **un solo
uso**: se consume al finalizar la recaracterización y, sin una nueva autorización,
la persona vuelve a quedar bloqueada.

Este flujo quedó **respaldado por una prueba de punta a punta** que recorre la
cadena completa con los mismos endpoints que consume la APK: ficha vigente →
bloqueada → coordinación autoriza → habilitada → se conforma hogar y sesión →
finaliza y consume la excepción → vuelve a bloquearse.

**Autorizar a quien solo está en el universo.** Antes, una persona que está en el
registro de víctimas pero aún no tiene ficha en el padrón operativo era invisible
para el panel. Ahora se le puede autorizar, **creándole la ficha en el momento de
autorizar** (materialización desde el universo), con estado en el RUV *INCLUIDO*.

**Operación sin conexión y sincronización (APK).** Se consolidó la búsqueda offline
contra un **filtro que reconoce a los 12,68 millones de personas del universo en
22,7 MB**, y la **cola de sincronización** que sube el trabajo cuando vuelve la
señal. La asistencia con IA para el mapeo de texto a campo es un apoyo al capturador,
con consentimiento y auditoría; **la captura por voz está simulada**, no es
reconocimiento real de voz —se deja dicho para no crear expectativas.

## Evidencia que soporta esta actividad

- Excepción de vigencia extremo a extremo: commits `2ecf39c`, `63ee8ba` (mover la
  autorización al panel, 14-ago) y `c23c781` (desbloqueo en línea, 25-ago).
- **Prueba de punta a punta:** `srni-backend/tests/test_e2e_excepcion_vigencia.py`
  (copia en `evidencias/`), 6 pasos, en verde.
- Autorizar desde el universo: commits `f1a2522`, `0e0399a`, `cebefe9`; verificado
  contra producción (respuesta correcta, origen UNIVERSO).
- Offline / sincronización: commits `d34fa01` (filtro Bloom del universo), `ddc1c77`,
  `2812ffc`, `421ce61`; documento técnico en `entregables/2026-08-21-offline-sync-ia/`.
- Contrato del flujo para el panel: `docs/operacion/excepcion_vigencia_desde_el_front.md`.

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `test-e2e-excepcion-vigencia.py` | La prueba de punta a punta del flujo de excepción (código y aserciones) |
| `commits-capacidades-agosto.txt` | Commits del mes sobre excepción, autorización, offline y sincronización |

## Pendiente / siguiente paso

- **Verificar el modo sin conexión en un dispositivo real** (modo avión), incluida
  la descarga efectiva del filtro del universo.
- Definir con la Unidad si la excepción aplica también a quien no está en el padrón, o
  si ese caso va por alta manual.
- Ver la fila de origen UNIVERSO y el aviso de coincidencia por número en el panel
  (tarea de frontend, Brando).
