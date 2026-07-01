# OE6 — Modelos de datos documentados

> **Obligación contractual:** *Crear y documentar modelos de datos que reflejen con precisión la información que se desea analizar, considerando las relaciones entre los diferentes conjuntos de datos en las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Ajuste y documentación de las **reglas de skip-logic** del capítulo B relacionadas con
salud sexual y reproductiva, en los 4 perfiles.

| Regla | Antes | Ahora | Motivo |
|---|---|---|---|
| Embarazo (B2) visible | `sexo == '2' and edad >= 12` | `sexo == '2' and edad >= 12` | Piso de 12 años, **sin tope superior** |
| Madre lactante (B2A) visible | `sexo == '2' and edad >= 12 and edad <= 50` | `sexo == '2' and edad >= 12` | Se quita el tope de 50 |
| "¿Cuántas?" (B2_CANT) visible | *(no existía)* | `HABILITAR si B2 == '1'` | Campo hijo de embarazo = "Sí" |

**Desviación documentada:** el manual 520.06.06-1 habilita embarazo a toda mujer (sin
piso) y madre lactante entre 12 y 50 años. Por decisión funcional **avalada por el líder
funcional (Alejandro)** se adopta un piso común de 12 años y **sin tope superior** en
ambas (una mujer puede estar embarazada/lactando después de los 50).

## Evidencia que soporta esta actividad

- Reglas en fixtures `perfil_*_v*.json` (sección `reglas_skip_logic`) y bundles
  `srni-mobile/assets/instrumentos/*.json` (sección `reglas`).
- Prueba de paridad con el motor real: `srni-mobile/src/services/__tests__/datosBasicosB2.test.ts`
  (mujer 60 → visible; mujer 10 → oculto; hombre → oculto; B2="Sí" → aparece B2_CANT).
- Commit `3249a85` en `main` (GitHub + Azure DevOps).
