# Cálculo del % de avance al 30 de junio de 2026

**Proyecto:** PRY-0662064 — Modernización de la entrevista de caracterización · APK
**Corte:** 2026-06-30 · **Commit de referencia:** `5fba1fa`

> **Advertencia metodológica que debe leerse antes que las cifras.**
> **No existe cronograma aprobado con fechas en el repositorio.** El acta de constitución
> (§6) lista 5 hitos y **3 dicen `[Por completar]`**. En consecuencia:
> **no se calcula avance planeado, ni desviación, ni curva S.** Las dos cifras de abajo
> son **avance ejecutado**, medido contra lo comprometido en el acta — no contra un
> calendario.

---

## Método 1 — Avance por hitos

**Fuente del denominador:** acta de constitución §6 "Hitos de alto nivel".
**Criterio de "cerrado":** existe evidencia documental **en el repositorio, con fecha
anterior al corte**, que demuestre el cumplimiento. Sin evidencia, no se cuenta —aunque
el hito haya ocurrido.

| # | Hito (acta §6) | Fecha estimada | ¿Cerrado? | Evidencia |
|---|---|---|---|---|
| 1 | Constitución del proyecto (Iniciación) | Junio 2026 | ✅ **Sí** | `docs/gestion/acta-constitucion-PRY-0662064.md`, 18-jun-2026 |
| 2 | Reunión de seguimiento PETI | 23-jun-2026, 9–11 a.m. | ⚠️ **No verificable** | El informe de junio marca OE7 como *"📝 Pendiente actas"*. **No hay acta en el repositorio** |
| 3 | Versión funcional de la APK en pruebas | `[Por completar]` | ✅ **Sí** | Builds **#15 y #16** publicados con QR (`docs/estado-actual.md` §0; informe junio OE1) |
| 4 | Habilitación de accesos OTI (dominio/internet, Oracle) | `[Por completar]` | ❌ **No** | Pendiente de comité de cambios (acta §3 y §9) |
| 5 | Despliegue / salida a producción | `[Por completar]` | ❌ **No** | Backend operando en `30.0.1.109:8090` (institucional, sin exposición a internet). **No hay acta de paso a producción** |

```
                hitos cerrados con evidencia      2
avance por hitos = ───────────────────────── = ───── = 40 %
                     hitos totales del acta      5
```

**Avance por hitos: 40 %.**

Si el hito 2 se acredita con un acta firmada fuera del repositorio, la cifra sube a
**60 %** (3/5). **Es el campo que más conviene cerrar antes de entregar.**

---

## Método 2 — Avance por alcance funcional

**Fuente del denominador:** acta §3 "Alcance — Incluido" (5 componentes comprometidos).
**Criterio de "completado":** existe código funcional en el repositorio al corte **y**
evidencia documental de su operación. Un componente en desarrollo cuenta como 0, no como
fracción — no se ponderó nada por criterio propio.

| # | Componente comprometido (acta §3) | Estado al corte | ¿Completado? | Evidencia medida sobre `5fba1fa` |
|---|---|---|---|---|
| 1 | Backend (API REST) con 7 módulos | **11 módulos**, 204 archivos `.py` | ✅ **Sí** | `srni-backend/apps/`: los 7 comprometidos + `ia`, `movil`, `reportes`, `sincronizacion` |
| 2 | App móvil Android offline (pre-carga + sincronización) | 77 archivos `.ts/.tsx`, motor offline + cola de sincronización | ✅ **Sí** | Builds #15/#16; `docs/mobile/`, `docs/arquitectura/plan-offline-precarga.md` |
| 3 | Panel web (administración, supervisión, reportes) | **En desarrollo** (Brando) | ❌ **No** | 37 archivos; `docs/frontend/estado-actual.md` lo marca 🟡 en desarrollo |
| 4 | Soporte de múltiples instrumentos | **8 de 8** empaquetados y cargados | ✅ **Sí** | `srni-mobile/assets/instrumentos/` (8 bundles) |
| 5 | Infraestructura de despliegue institucional | Stack Docker en `30.0.1.109:8090` | ✅ **Sí** | `infra/deploy/`, `docs/INFORME-ARQUITECTURA-ESTADO.md` |

```
                          componentes completados      4
avance por alcance = ──────────────────────────── = ───── = 80 %
                     componentes comprometidos §3      5
```

**Avance por alcance funcional: 80 %.**

### Lo que esta cifra NO dice, y hay que decir en la mesa

**80 % es avance de construcción, no de aceptación.** Al corte **no hay en el
repositorio** ningún acta de aceptación funcional, prueba de usuario firmada ni
aprobación del supervisor. El propio `docs/estado-actual.md` deja abierto que falta
*"abordar perfil por perfil para validar las 995 preguntas"*: los 8 instrumentos están
**cargados**, no **validados uno a uno**.

---

## Cifra recomendada

**Se recomienda reportar el 80 % (alcance funcional)**, y declarar el 40 % (hitos) como
cifra secundaria con su salvedad.

**Por qué:**

1. **El denominador por hitos está roto.** Tres de los cinco hitos no tienen fecha, y dos
   dependen de un tercero (la OTI) que no controla el proyecto. Un avance calculado
   contra un cronograma incompleto mide la calidad del cronograma, no la del proyecto.
2. **El alcance sí está definido y es verificable.** Los cinco componentes del acta §3
   están enunciados sin ambigüedad y cada uno se pudo contrastar contra código existente
   en una fecha concreta.
3. **Es la cifra defendible ante la OCI**, porque cada casilla de su tabla apunta a un
   archivo del repositorio en un commit con fecha, no a un juicio.

**Con dos condiciones que deben acompañar el número:**
- Declarar que es avance **de construcción**, sin aceptación formal.
- Declarar que los hitos 4 y 5 (accesos OTI y salida a producción) **dependen de un
  tercero** y son el riesgo principal del cierre.

---

## Lo que haría subir la cifra sin escribir una línea de código

| Acción | Efecto |
|---|---|
| Adjuntar el acta de la reunión PETI del 23-jun | Hitos: 40 % → **60 %** |
| Acta de aceptación funcional del supervisor | Convierte "construcción" en "aceptación" |
| Fechar los 3 hitos `[Por completar]` del acta | Habilita calcular avance **planeado** y desviación |
| Etiquetar en Git las APK entregadas | Hace auditables las entregas por fecha |
