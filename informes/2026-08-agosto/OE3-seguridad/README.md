# OE3 — Medidas de seguridad — protección de datos PII

> **Obligación contractual:** *Procesar, implementar y documentar medidas de seguridad para proteger la integridad, confiabilidad y confidencialidad de los datos utilizados para el procedimiento de Instrumentalización, de acuerdo con su naturaleza, calidad y contexto en soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

**Contraseñas de las cuentas de encuestador.** El sistema legado guarda las claves
con un algoritmo antiguo: **SHA-512 con una sal fija escondida dentro de la
aplicación**. Ese esquema es débil frente a ataques modernos (SHA-512 es rápido de
forzar por fuerza bruta y una sal única para todos no protege), y además la sal no
es recuperable, así que las claves viejas no se pueden recalcular. Se verificó que
**ninguna de las 1.158 encuestadoras ha ingresado nunca** al sistema nuevo, de modo
que no hay nada que preservar del esquema viejo.

Con ese diagnóstico, la decisión fue **no replicar el esquema legado** y asignar las
claves nuevas guardándolas con **Argon2id**, el estándar actual (el que Django trae
por defecto cuando se activa). Se construyó un comando de carga que:

- lee las claves desde un archivo que provee la coordinación;
- las guarda **hasheadas con Argon2id**, nunca en texto plano;
- es **reproducible sin duplicar** (se puede volver a correr sin dañar lo cargado);
- valida el formato y reporta lo que no cuadre.

**Protección de datos en el dispositivo.** Al revisar el trabajo sin conexión se
detectó y corrigió un defecto de confidencialidad: si la cola de sincronización
tenía un envío fallido, al cerrar sesión **no se borraban del teléfono** los datos
personales ya capturados. Se corrigió para que el cierre de sesión limpie la PII del
dispositivo aunque queden envíos pendientes.

La búsqueda de personas sigue siendo **por hash del documento** y la PII sigue
**cifrada en reposo** (medidas establecidas en julio, vigentes).

## Evidencia que soporta esta actividad

- Comando: `srni-backend/apps/autenticacion/management/commands/cargar_claves.py`
  (commit `10bc0b9`), con **9 pruebas** en
  `srni-backend/apps/autenticacion/tests/test_cargar_claves.py`.
- Corrección del borrado de PII al cerrar sesión con cola no vacía: commit `2812ffc`,
  documentado en `docs/pruebas/estado_hallazgos_qa_apk.md` §8.
- Configuración de hashers: `PASSWORD_HASHERS` con Argon2 en la configuración de
  Django del backend.

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `commit-cargar-claves.txt` | Detalle del commit del comando de carga de claves (archivos y volumen) |
| `commits-seguridad-agosto.txt` | Commits del mes relacionados con seguridad y protección de datos |

## Pendiente / siguiente paso

- Recibir de la coordinación el archivo definitivo de claves de las encuestadoras y
  ejecutar la carga en producción.
- Definir política de expiración/rotación de contraseñas para el primer ingreso.
