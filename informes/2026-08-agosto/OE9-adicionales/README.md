# OE9 — Actividades adicionales con supervisor

> **Obligación contractual:** *Cumplir las demás actividades relacionadas con el objeto del contrato que sean acordadas con el supervisor.*

## Actividad desarrollada en este periodo

- **Análisis del formato de contraseñas del sistema legado.** A partir de una clave
  de ejemplo del sistema en operación, se identificó el algoritmo con que están
  guardadas las credenciales (SHA-512 con sal fija embebida) y se determinó que **no
  debe replicarse**; esa decisión habilitó el comando de carga con Argon2id descrito
  en la Obligación 3.
- **Prueba de punta a punta del flujo de excepción de vigencia.** Se dejó
  **automatizada y reproducible** la verificación de que el flujo cierra el círculo
  en el backend (bloqueada → autorizar → habilitada → recaracterizar → consumir →
  bloqueada), como respaldo objetivo del informe. No reemplaza la verificación en
  dispositivo, que queda pendiente, pero fija por contrato lo que la APK recibe en
  cada paso.
- **Registro del aviso de la Unidad sobre la base Oracle.** Se documentó, para el
  trabajo futuro de mejora de la base, la tabla e índice creados por la Unidad en el
  esquema del universo, dejándolo anotado explícitamente como **fuera del alcance de
  este mes** para no perderlo.

## Evidencia que soporta esta actividad

- Prueba de punta a punta: `srni-backend/tests/test_e2e_excepcion_vigencia.py`
  (copia en `evidencias/`).
- Análisis del formato de claves legado y decisión: [`../OE3-seguridad/README.md`](../OE3-seguridad/README.md).
- Registro del pendiente de base de datos: [`../OE5-bd/README.md`](../OE5-bd/README.md).

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `test-e2e-excepcion-vigencia.py` | La prueba automatizada de punta a punta del flujo de excepción |

## Pendiente / siguiente paso

- Ejecutar la carga de claves en producción cuando llegue el archivo definitivo.
- Verificar en dispositivo el flujo de excepción completo (campo → sincronización).
