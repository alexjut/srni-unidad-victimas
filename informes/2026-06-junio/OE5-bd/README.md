# OE5 — Estructura de bases de datos

> **Obligación contractual:** *Crear, diseñar y documentar la estructura de bases de datos para garantizar la eficiencia, integridad y seguridad de los datos utilizados en los procedimientos de instrumentalización de la información y análisis tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

*(Pendiente — se completa al cierre del mes.)*

**Frente que se ejecuta este mes:**

- Implementación del campo `codigo_hogar` con generación automática (formato: prefijo municipio + año + consecutivo) al pasar el hogar de BORRADOR a ACTIVO. Migración nueva.
- Diseño del **esquema propio para integración eventual con Oracle**: tablas espejo / staging que permitan sincronizar sin acoplarse al esquema legacy `RNIENTREVISTA`. Documentación de cardinalidades, claves, índices y reglas de mapeo.
- Mantenimiento del esquema existente: revisión de índices, conteos de tablas grandes y vacuum/analyze cuando aplique.

## Evidencia que soporta esta actividad

*(Pendiente — migraciones nuevas en `srni-backend/apps/*/migrations/`, documentación actualizada en `docs/base-datos/backend-postgresql.md` y `docs/base-datos/MODELOS.md`.)*
