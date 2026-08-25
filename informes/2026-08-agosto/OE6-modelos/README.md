# OE6 — Modelos de datos documentados

> **Obligación contractual:** *Crear y documentar modelos de datos que reflejen con precisión la información que se desea analizar, considerando las relaciones entre los diferentes conjuntos de datos en las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

**Motor de reglas del formulario (skip-logic) unificado.** La lógica que decide qué
preguntas se muestran y cuáles son obligatorias para cada persona estaba **triplicada
**: una copia en la aplicación móvil, otra en el tablero del celular y otra en el
servidor, y habían empezado a divergir —el mismo formulario podía comportarse
distinto según dónde se evaluara—. Se **unificó en un solo lugar** del sistema, de
modo que las tres partes deciden exactamente igual para una misma persona. El motor
evalúa reglas por valor (booleanos, listas), por pertenencia étnica, por edad y por
sexo, y maneja el caso de "dato aún desconocido" sin romperse.

**Porcentaje de avance calculado sobre el modelo correcto.** Sobre ese motor se
corrigió el cálculo del porcentaje de una entrevista (defecto APK-005): ahora cuenta
solo las preguntas obligatorias **visibles**, evaluando las reglas con los **datos
reales de cada integrante** del hogar (edad, sexo, pertenencia étnica, condición en
el registro), en vez de dividir por todas las obligatorias incluyendo las que quedan
ocultas y que nadie puede responder. Así una sesión realmente completa marca 100 %.

Estos modelos —instrumentos, capítulos, preguntas, reglas— siguen teniendo el
**fixture como fuente viva** y se exportan al bundle que viaja en la APK con
identificadores deterministas, de modo que backend y APK comparten exactamente la
misma definición.

## Evidencia que soporta esta actividad

- Motor unificado: `srni-backend/apps/formulario/skiplogic.py`.
- Cálculo del porcentaje por obligatorias visibles con contexto: commits `3dfcd61`,
  `3fe431f`, `ff861c5`; **35 pruebas de backend + 6 de móvil**, verificadas por
  mutación.
- Modelo de instrumentos: **8 instrumentos · 92 capítulos · 1.640 preguntas**
  empaquetados (`srni-mobile/assets/instrumentos/index.json`).
- Recálculo del porcentaje en el modelo de sesión:
  `srni-backend/apps/encuestas/models.py` (`recalcular_porcentaje`).

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `commits-modelos-agosto.txt` | Commits del mes sobre skip-logic, porcentaje e instrumentos |

## Pendiente / siguiente paso

- Recalcular (backfill) el porcentaje de las sesiones ya guardadas con el motor
  corregido.
- Curar contra el manual el instrumento de Asistencia humanitaria, que hoy no tiene
  preguntas obligatorias.
