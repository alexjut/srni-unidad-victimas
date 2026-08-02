# Documentos repetidos en el padrón: qué son y qué hace SICAV

**Fecha:** 2 de agosto de 2026 · **Decide:** Javier Aguilar (facultad delegada por Oscar)
**Estado:** implementado y desplegado · **Código:** `apps/victimas/identidad.py`, `ColisionDocumento`

---

## 1. El problema, como se veía al principio

Al terminar el padrón real (5.926.004 víctimas) el archivo descargable tenía
**4.928.725 filas**: casi un millón menos. La causa era el esquema del SQLite:

```sql
doc_hash TEXT PRIMARY KEY   -- + INSERT OR REPLACE
```

Cuando dos víctimas comparten número de documento, la segunda **pisaba** a la
primera sin dejar rastro. La lectura inicial fue: "hay un millón de colisiones de
identidad y hay que decidir con cuál quedarse".

Esa lectura era incorrecta, y la diferencia importa porque llevaba a la decisión
equivocada.

## 2. Qué son en realidad (medido, no supuesto)

Medición sobre la base de producción el 2-ago-2026 —768.096 documentos repetidos
de 4.928.725 distintos—:

| Qué es | Proporción | Evidencia |
|---|---:|---|
| **Una sola persona** duplicada por el Oracle de origen | **92,0 %** | nombre y fecha de nacimiento idénticos en todas las filas |
| Una sola persona con el nombre mal escrito | 1,3 % | ERIKA/ERICA, LUS/LUZ, mismos apellidos y fecha |
| **Personas distintas** compartiendo documento | **6,8 %** | nombre y fecha distintos |
| Valores de relleno | decenas de documentos | `99` → 4.297 filas con **3.780 nombres distintos**; `0` → 1.194 filas |

El caso que lo deja claro: el documento `1089290511` aparece **505 veces**,
siempre **ALBA TAPIA RODRIGUEZ**, con 504 `cons_persona` distintos. No son 505
personas: es una persona registrada 505 veces en la fuente.

**Consecuencia:** el colapso ciego no borraba ~997 mil personas sino
**~53 mil** —las del 6,8 %—. Sigue siendo inaceptable, pero es otro problema:
no hay que elegir entre un millón de identidades, hay que **distinguir** tres
situaciones que hasta ahora se trataban igual.

## 3. Qué hace la industria con esto

El campo se llama *record linkage* / *entity resolution*, y la práctica
consolidada —índices maestros de pacientes (EMPI), registro civil, registro de
población desplazada de ACNUR— coincide en cuatro cosas:

1. **Emparejamiento determinístico cuando hay identificador fuerte**, probabilístico
   (Fellegi-Sunter) solo cuando no lo hay. Acá el documento ya empareja: lo único
   que se decide es si el nombre y la fecha describen a la misma persona.
2. **No fusionar automáticamente lo dudoso.** Lo que supera el umbral se resuelve
   solo; lo de la franja gris va a una cola de revisión humana. Nunca se descarta
   un registro en silencio.
3. **Los identificadores de relleno se excluyen del emparejamiento** — la
   *null value list*. Un `99` compartido por 3.780 personas no es una llave: usarlo
   como tal empareja a desconocidos entre sí.
4. **Link, don't merge.** El registro original se conserva; la resolución es un
   dato derivado, auditable y reversible.

## 4. La decisión

**Clasificar cada documento repetido y tratar cada clase distinto.** No se
fusiona, no se borra y no se elige por el encuestador cuando hay algo que elegir.

| Clase | Qué es | Búsqueda online | Padrón offline |
|---|---|---|---|
| `DUPLICADO_FUENTE` | una persona, repetida | 200, la fila más completa | una fila |
| `VARIANTE_NOMBRE` | una persona, nombre mal escrito | 200, la fila más completa | una fila |
| `AMBIGUO` | personas distintas | **409** con todos los candidatos | **todas** las filas, marcadas |
| `NO_IDENTIFICANTE` | valor de relleno | **409** sin mostrar a nadie → alta manual | una marca vacía |

Cuando **no hay veredicto** —la clasificación no ha corrido— se pregunta igual.
El default es la pregunta de más, nunca el silencio.

### Cómo se reconoce que dos filas son la misma persona

Reglas, no un modelo, y por razones concretas:

- **Hay que poder explicar cada decisión.** Si a alguien se le asigna o se le niega
  una caracterización, la respuesta no puede ser "el modelo dio 0,87".
- **No hay franja gris que justifique un modelo**: el 92 % son coincidencia
  *exacta* de nombre y fecha de nacimiento.
- Corre sobre millones de filas en un servidor compartido.

El criterio:

1. Documento en la *null value list* (o con ≥20 nombres distintos) → no identifica.
2. Nombre normalizado (mayúsculas, sin tildes, **ñ→n**) + fecha de nacimiento
   idénticos → misma persona.
3. Bloques distintos que comparten **apellidos y fecha** → misma persona con el
   nombre mal escrito.
4. Lo que sobrevive → personas distintas.

La **ñ se pliega a n** porque la fuente la pierde de forma inconsistente. Para que
eso uniera a dos personas distintas harían falta dos personas con el mismo
documento, la misma fecha de nacimiento y apellidos que solo difieren en la ñ.

Los **hermanos no se unen**: apellidos iguales con fecha distinta quedan ambiguos.
Unirlos fabricaría una persona que no existe.

### Survivorship

Cuando varias filas son la misma persona, viaja **la más completa** (más campos con
dato) y, a igualdad, la caracterizada más recientemente. Es la regla más simple que
no puede sorprender a nadie, y **solo afecta qué se muestra**: ninguna fila de
`Victima` se toca.

## 5. Por qué no se hizo lo otro

- **Fusionar los duplicados en la base.** Es irreversible sobre datos de los que no
  somos la fuente. Si el criterio resulta equivocado, no hay vuelta atrás. La tabla
  derivada se reconstruye corriendo un comando.
- **Excluir del padrón los documentos ambiguos.** Sacaría de circulación a ~53 mil
  víctimas reales para evitar una pregunta.
- **Quedarse con la caracterizada más recientemente.** Es exactamente el colapso
  ciego, con una regla que suena razonable y sigue borrando a la otra persona.
- **Un modelo probabilístico.** Ver arriba: no hay franja gris que lo justifique, y
  perderíamos la explicación.

## 6. Efecto medido

- El **409** pasa de dispararse en el 100 % de los documentos repetidos (768.096) a
  hacerlo en el **~7 %** (~52.000). El 92 % de las búsquedas que hoy interrumpirían
  al encuestador ya no lo hacen — y eso importa: un aviso que salta siempre enseña a
  ignorarlo justo antes de la vez que sí importaba.
- El padrón offline **deja de borrar ~53 mil personas**.
- Buscar `99` deja de devolver a un desconocido.

## 7. Lo que queda abierto

- **Los `AMBIGUO` no tienen cola de revisión.** La industria los manda a un equipo
  de curaduría; acá los resuelve el encuestador en campo, uno por uno, y esa
  decisión no se guarda: la próxima búsqueda vuelve a preguntar. Registrar la
  confirmación (`ConfirmacionIdentidad`) es el paso natural siguiente.
- **La clasificación no corre sola.** Hay que ejecutar `clasificar_colisiones`
  después de cada carga del padrón; todavía no está encadenada a la recarga mensual.
- **El 6,8 % de ambigüedad es un defecto de la fuente**, no de SICAV. Entra en el
  registro de defectos del legacy para arreglar post-migración, y alimenta las
  preguntas a OTI sobre identidad.

## 8. Cómo se corre

```bash
python manage.py clasificar_colisiones --dry-run      # mide sin escribir
python manage.py clasificar_colisiones                # ~30 min sobre 768 k documentos
python manage.py generar_padron                       # el archivo ya sale clasificado
```

Es idempotente: reconstruye la tabla entera en cada corrida.

---

**Fuentes consultadas** (agosto 2026): Elmagarmid et al., *Duplicate Record
Detection: A Survey* (Purdue); AHIMA, *Building an Enterprise Master Person Index*;
CDC, *IIS Patient-Level De-duplication Best Practices*; ACNUR, tutorial de record
linkage para deduplicar listas de registro y documentación de PRIMES/BIMS; guías de
survivorship y *golden record* de MDM.
