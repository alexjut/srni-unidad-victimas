# Constancia — qué tocó SICAV y qué no, en las bases de la UARIV

> **Fecha:** 2026-07-30 · Proyecto PRY-0662064
> **Para qué sirve este documento:** responder con precisión, y no de memoria, si
> alguien pregunta qué hizo el equipo de SICAV en las bases de Vivanto o del Modelo
> Integrado. Todo lo afirmado aquí es verificable con los artefactos que se citan.

---

## Resumen

| Base / esquema | Qué hicimos |
|---|---|
| `RNIENTREVISTA` en `30.0.1.9` (**nuestro esquema**) | lectura + **una escritura autorizada**: el piloto |
| `RNIPAQUETES` (Vivanto) | **solo `SELECT`** |
| `MODELOINTEGRADO` (Vivanto) | **solo `SELECT`** |
| `ADMINUSUARIOS` (Vivanto) | **solo `SELECT`** |
| `AUDITORIAVIVANTOPROD` | **solo `SELECT`** (consultas al diccionario) |
| Réplica local en Docker | escritura libre — es nuestra, no es de nadie más |

**En ninguna base de Vivanto ni del Modelo Integrado se ejecutó un `INSERT`,
`UPDATE`, `DELETE`, `MERGE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT` ni ningún DDL.**

### Precisión importante sobre "solo tocamos la .9"

Es cierto que **la única base a la que nos conectamos fue `30.0.1.9/ENTREVISTARN`**
—la del sistema de encuesta, la que alimenta la APK—. Nunca se abrió una conexión
directa contra Vivanto ni contra el Modelo Integrado.

**Pero conviene decirlo completo:** varias consultas salieron *desde* `.9` a través
del **dblink `DBL_VIVANTO`**, que es un puente que ya existía en esa base y que el
propio legacy usa. Esas consultas viajan al otro lado y **pueden quedar registradas
en la auditoría de Vivanto**.

Siguen siendo `SELECT` —no cambia nada de lo dicho arriba— pero si alguien de
Vivanto revisa sus registros de lectura, verá actividad nuestra. Es esperable y está
justificada: se buscaba la fuente del padrón de víctimas para poblar SICAV. No hay
nada que explicar más allá de eso, pero es mejor saberlo de antemano que enterarse
por un tercero.

---

## Lo único que escribimos en producción, con detalle

Fue en **nuestro propio esquema** `RNIENTREVISTA`, el 2026-07-28, mediante los
**procedimientos oficiales `GIC_*`** —nunca `INSERT` directo a tablas— y con
aprobación explícita de Javier Aguilar:

| Tabla | Filas | Identificable por |
|---|---:|---|
| `GIC_HOGAR` | 1 | `HOG_CODIGO = '999999-2W832'`, `USU_IDUSUARIO = 999999` |
| `GIC_PERSONA` | 3 | ids 9184502-9184504 |
| `GIC_MIEMBROS_HOGAR` | 3 | por `HOG_CODIGO` |
| `GIC_N_RELACION_DT_PUNTO` | 1 | por `HOG_CODIGO` |
| `GIC_N_RESPUESTASENCUESTA` | 3 | por `HOG_CODIGO` |

Son **datos sintéticos de prueba**, no de una persona real. Todo se identifica con
`USU_IDUSUARIO = 999999`, un usuario de servicio que ningún otro sistema usa, y es
reversible con un `DELETE` acotado por `HOG_CODIGO`.

Detalle completo y verificación en `docs/oracle-legacy/plan_escalon_2.md` §8.

---

## La evidencia de que en Vivanto solo se leyó

**1. El harness del agente de auditoría bloqueaba las escrituras por regla.** No es
que "no las usáramos": no podían ejecutarse. El guard, textual:

```python
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|truncate|create|grant|revoke|"
    r"commit|rollback|execute|begin)\b", re.I)
```

Cualquier consulta con uno de esos verbos se rechazaba antes de llegar a Oracle.

**2. Los scripts son auditables.** Las ~45 consultas se ejecutaron desde scripts
Python guardados. Una revisión de todos ellos buscando verbos de escritura devuelve
únicamente: `sys.path.insert()` —una función de Python, no SQL—, un comentario que
dice *"SOLO SELECT"*, y el propio regex de bloqueo citado arriba.

**3. Qué se consultó, concretamente:** el diccionario de datos
(`all_tables@DBL_VIVANTO`, `all_tab_columns`, `all_objects`), `COUNT(*)` sobre
tablas para medir volumen, y `SELECT` con `rownum` sobre catálogos de configuración
(`APLICACION`, `NIVELACCESO`, `WS_METODOS`). Nada de eso modifica datos.

---

## Sobre el bloque corrupto — por qué no pudo ser nuestro

Encontramos `ORA-01578: data block corrupted (file # 14, block # 427091)` en
`RNIPAQUETES.CARACT_EVENTOS_VICTIMIZANTES`. Conviene tener claro esto:

1. **Lo detectamos, no lo causamos.** Apareció al ejecutar un `SELECT COUNT(*)`.
2. **Un `SELECT` no puede corromper un bloque.** `ORA-01578` es corrupción **física**
   —del datafile en disco—, típicamente por fallo de almacenamiento, de controladora
   o de escritura previa. Leer no escribe.
3. **Puede llevar mucho tiempo así.** Un `SELECT` acotado sobre esa misma tabla
   funciona: solo falla quien recorre el bloque dañado. Es perfectamente posible que
   la corrupción sea muy anterior y que nadie hubiera hecho un recorrido completo.
4. **La tabla no es nuestra ni la usamos**: pertenece a `RNIPAQUETES`, al otro lado
   del dblink. Nuestro proceso no la lee ni la escribe.

Lo reportamos por responsabilidad, no porque nos corresponda: si el respaldo no
valida bloques, la corrupción puede propagarse a las copias.

---

## Verificación de privilegios — hecha el 31-jul, y el resultado obliga a matizar

Se comprobó qué puede hacer realmente el usuario con el que trabajamos:

| Comprobación | Resultado |
|---|---|
| Privilegios **directos** de escritura sobre esquemas ajenos | **NINGUNO** |
| Roles | `CONNECT`, `RESOURCE`, `JAVAUSERPRIV` y **`DBA`** |
| Privilegios de sistema | `SELECT ANY TABLE`, **`UPDATE ANY TABLE`**, **`ALTER ANY TABLE`**, `GRANT ANY PRIVILEGE`, `EXECUTE ANY PROCEDURE` |

> ⚠️ **Corrección honesta.** La versión anterior de este documento anticipaba que
> quedaría demostrado que "ni siquiera habríamos podido escribir". **Eso es falso y se
> retira.** `RNIENTREVISTA` tiene rol **DBA**: técnicamente podría escribir en
> cualquier esquema de esa base, Vivanto incluido.
>
> Lo que sostiene esta constancia **no es la falta de permisos** —los hay de sobra—
> sino la evidencia de que no se usaron: el bloqueo por regex del harness y los ~45
> scripts auditables, que están arriba. Se deja escrito así porque una constancia que
> se apoya en un dato falso no sirve para nada el día que alguien la revise.

### Y esto es, en sí mismo, un hallazgo de seguridad

El usuario con el que SICAV escribe en producción **es DBA de la base**. Combinado con
el pendiente **3a.5** —la contraseña de `RNIENTREVISTA` está repartida entre varias
personas de la Unidad, razón por la que se aplazó rotarla— el resultado es que **esa
contraseña conocida da control total sobre la base de datos de víctimas**: leer, alterar
o borrar cualquier tabla de cualquier esquema, incluidos los de Vivanto.

No es un riesgo que introdujera este proyecto —la cuenta ya era así— pero sí uno que
conviene dejar registrado, porque cambia la gravedad de 3a.5: no es "rotar una clave de
aplicación", es "una credencial de administrador está circulando".

**Mitigación mínima sugerida**, en orden de esfuerzo:
1. Rotar la contraseña (3a.5).
2. Crear un usuario específico para SICAV **sin rol DBA**, con permiso solo de ejecutar
   los procedures `GIC_*` y leer lo que necesita. La escritura del piloto no necesitó
   DBA: se hace por procedures.
3. Revisar por qué el dueño del esquema tiene `GRANT ANY PRIVILEGE`.

---

## Nota sobre las credenciales

Se usó el usuario `RNIENTREVISTA`, que es el dueño del esquema donde SICAV escribe,
para lectura y para el piloto. Está pendiente su rotación (pendiente 3a.5), aplazada
por decisión de Javier el 28-jul con el argumento de que esa contraseña ya está
repartida en la Unidad. Se deja constancia de que el pendiente existe y de por qué
sigue abierto.
