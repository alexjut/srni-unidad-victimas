# OE3 — Medidas de seguridad — protección de datos PII

> **Obligación contractual:** *Procesar, implementar y documentar medidas de seguridad para proteger la integridad, confiabilidad y confidencialidad de los datos utilizados para el procedimiento de Instrumentalización, de acuerdo con su naturaleza, calidad y contexto en soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Durante julio se incorporó al sistema el **padrón real de víctimas** —5.926.004
personas con nombre, documento y fecha de nacimiento—, lo que convirtió la
protección de PII en una condición de operación y no en un requisito formal. Se
implementaron y documentaron cuatro medidas:

**1. Cifrado en reposo de los datos personales.** Documento, nombres, apellidos y
fecha de nacimiento se almacenan cifrados con Fernet (AES en modo CBC con
HMAC-SHA256) mediante un campo propio (`EncryptedField`), no en texto plano.

**2. Búsqueda sin descifrar.** Como el cifrado no es determinista, no se puede
filtrar por esos campos con un `WHERE`. Toda búsqueda por documento pasa por un
**hash SHA-256** de la forma canónica: se localiza a la persona sin descifrar el
padrón entero.

**3. Doble llave de búsqueda, por un problema medido.** El **14,5 %** de la fuente
(1.126.615 personas) no trae tipo de documento. Con una sola llave `tipo|número`
esas personas serían **inencontrables** — el encuestador escribe "CC + número" y la
llave nunca coincide. Se agregó un segundo índice solo por número. La alternativa
—asumir "CC", que serían el ~90 %— se descartó: sería afirmar un documento que
nadie verificó.

**4. Trazabilidad de accesos.** Toda consulta al padrón queda registrada en
`LogAcceso` con usuario, acción, IP y resultado, incluidos los accesos denegados y
los bloqueos por intentos fallidos.

**Constancia de acceso a fuentes externas.** Se documentó por escrito que sobre
Vivanto y el Oracle de la UARIV **solo se ejecutaron lecturas**, con el detalle de
qué se consultó y con qué usuario, para dejar constancia ante la entidad.

## Evidencia que soporta esta actividad

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `cifrado-de-pii-codigo-fuente.txt` | La implementación real del cifrado, del hash de búsqueda y del registro de auditoría, extraída del código fuente |
| `auditoria-de-accesos-produccion.txt` | Los registros de auditoría existentes en la base de producción, por tipo de acción |
| `constancia_accesos_vivanto.md` | Constancia escrita de que sobre las fuentes externas de la entidad solo se leyó |

## Pendiente / siguiente paso

- Rotación de la credencial del usuario de base de datos del legado (tarea interna:
  el esquema es propio, no requiere gestión ante OTI).
- Definir política de retención de `LogAcceso`.
