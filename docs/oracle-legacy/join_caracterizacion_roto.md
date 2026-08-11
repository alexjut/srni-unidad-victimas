# El join de la caracterización está roto: `CONS_PERONA` no identifica a nadie

**Fecha:** 11-ago-2026 · **Medido contra:** `RNIENTREVISTA@30.0.1.9:1521/ENTREVISTARN`
(producción) y la base de SICAV en el 30.0.1.109.

> **En una línea:** el padrón operativo de 5.926.005 personas tiene el género, la
> etnia y la discapacidad de **otra persona**, y la lista de quiénes lo componen
> se decidió con el estado RUV de **otra persona**. No es un desajuste de
> identificadores que se pueda remapear: la columna que se usa como llave es un
> contador de filas.

---

## 1. Cómo apareció

Verificando 68 cédulas traídas del territorio, el reporte salió con **ROSA BUSTOS
marcada como masculino** y **SIXTO SOLIS MINA como femenino**. No era un caso
aislado ni un error de captura.

## 2. La evidencia

### 2.1 A escala: el género es azar puro

Sobre 5.000 víctimas del padrón cruzadas con el universo del RUV por documento:

| | |
|---|---:|
| Género que coincide con el universo | **50,1 %** |
| Distribución en la muestra | M = 2.479 · F = 2.479 |
| Etnia `NINGUNA` acertada | 87,8 % |

El 50,1 % en una variable binaria es exactamente lo que da tirar una moneda. Y el
87,8 % de la etnia coincide con la **frecuencia base** de `NINGUNA` en el padrón
(4.395 de 5.000 = 87,9 %): es lo que se obtiene asignando al azar respetando la
proporción, no lo que se obtiene acertando.

### 2.2 La prueba que lo cierra: la fecha de nacimiento

`M_CARACT_TABLA_RA_PER` trae `F_NACIMIENTO`. Comparada con `PER_FECHANACIMIENTO`
de `GIC_PERSONA` a través del join actual:

```
F_NACIMIENTO comparables: 34.612 | coinciden: 4 (0,0 %)
```

**Y no es que la fecha esté corrupta.** Cada fila de la caracterización es
*internamente coherente* — `f_nacimiento` + `edad` da ~2015-2016, cuando se
levantó el instrumento:

```
DIF JOSE     AVENDAÑO    gic_fnac=1927-06-27  caract_fnac=2007-07-22  edad=8
DIF JUAN     CONTRERAS   gic_fnac=2017-06-14  caract_fnac=1974-04-12  edad=41
DIF JENNIFER ORTIZ       gic_fnac=2007-02-15  caract_fnac=2004-03-18  edad=11
```

Cada fila describe a **una persona real**. Solo que no es esa.

### 2.3 Por qué no hay llave que encontrar

La consulta que arma el padrón (`cargar_padron_oracle.py`) une así:

```sql
FROM gic_persona p
JOIN RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO c
  ON c.cons_perona = p.per_idpersona      -- ⚠️
WHERE c.estado_ruv IN (...)
```

Se probaron las tres columnas candidatas de la tabla:

| Candidata | Resultado |
|---|---|
| `CONS_PERONA` | **Es un contador de filas.** Con `cons_perona <= 100.000` hay 94.536 filas y 94.477 valores distintos, de 1 a 100.000. Denso y correlativo: 1, 2, 3, 4… |
| `ID_PERSONA_CARACT` | Vacío en el **97 %** de las filas (14.516 de 474.133). |
| `ID_ENTREVISTA` | Vacío en el mismo 97 %. Es alfanumérico de 5 caracteres (`33L4V`, `ODNDI`). El puente `→ GIC_RPT_ENTREVISTA.ID_PERSONAS → GIC_PERSONA` devuelve **0 filas**. |

La tabla **no tiene columna de documento**. Las tres hermanas
(`M_CARACT_TABLA_RA_PER_1`, `…2`, `…1COPIA`) tienen exactamente las mismas
columnas. Tiene 9.961.503 filas contra 7.765.404 de `GIC_PERSONA`.

**Conclusión: el join compara un número de fila con un id de persona.** No está
desalineado — la asignación es aleatoria, y por eso el género acierta el 50 %.

---

## 3. Qué está mal y qué está bien

| Campo | Origen | Estado |
|---|---|---|
| `genero`, `pertenencia_etnica`, `discapacidad` | `c.` (caracterización) | 🔴 de otra persona |
| `estado_ruv` | `c.` | 🔴 ver §3.1 — es peor |
| documento, tipo, nombres, apellidos, `fecha_nacimiento`, `cons_persona` | `p.` (`GIC_PERSONA`) | ✅ correctos |
| `habilitado_para_caracterizacion`, `fecha_ult_caracterizacion` | join local sin dblink | ✅ correctos **por persona** |

### 3.1 `estado_ruv` no tiene un valor equivocado: decidió la población

Medido en producción:

```
estado_ruv        n
INCLUIDO          5.926.004
NO_VERIFICADO             1
```

Es **constante por construcción**: la consulta filtra `WHERE c.estado_ruv IN (…)`,
así que solo entran las filas ya marcadas como incluidas y todas salen con el
mismo valor. El dato de la otra persona **no se guardó en una columna: se gastó
eligiendo quién entra al padrón**.

Ese es el daño mayor, y el único que no se arregla escribiendo en una columna.
Hay personas que no deberían estar y personas que faltan, y no se sabe cuáles sin
rehacer la selección.

`habilitado_para_caracterizacion` (1.058.972 en `False`) es correcto por persona
pero está calculado **sobre la población equivocada**.

---

## 4. Alcance: ¿hasta dónde llegó?

### 4.1 Al Oracle de la UARIV: **NO** ✅

```
RegistroEscrituraOracle: 0 filas
```

El ledger de escritura está vacío en producción. Nada de este dato viajó al
legacy. **El arreglo es "recargar", no "reparar lo escrito"** — que era la
conversación cara.

### 4.2 A los celulares: **SÍ**

- El padrón offline lleva `FLAG_EN_RUV`, derivado de `estado_ruv`. Como este vale
  `INCLUIDO` para los 5,9 M, **el bit no distingue nada**.
- La precarga de jornada manda `genero`, `pertenencia_etnica` y `discapacidad`.

### 4.3 A entrevistas ya capturadas: **SÍ, y esto no lo repara una recarga**

`srni-mobile/app/(main)/formulario/[temaId].tsx:135`:

```ts
const sexoA8 = v.genero ? MAP_GENERO_A8[v.genero.toUpperCase()] : undefined;
if (sexoA8) m.A8 = sexoA8;                            // sexo (LISTA)
```

Ese valor **se persiste** como respuesta (`upsertRespuesta` + `encolar
('RESPONDER_PREGUNTA')`, líneas 510-517). O sea: hay entrevistas guardadas con el
sexo de otra persona, prellenado por el sistema, sin que nadie lo tocara.

### 4.4 Lo que el análisis afirmó y **no** es cierto

Verificado antes de darlo por bueno:

- **No existe `sincronizar_legacy.py`.** No hay ninguna tarea diaria repitiendo el
  join. El sangrado no está activo.
- Sí existe el comentario mentiroso en `apps/sincronizacion/oracle/mapeo.py:279`:
  «*el job lo cruza contra `M_CARACT_TABLA_RA_PER.CONS_PERONA`, que es de donde lo
  sacamos*». Hay que borrarlo: afirma como cierto justo lo que es falso.

---

## 5. La salida: cambiar de fuente, no arreglar el join

`PersonaUniverso` (12.009.492 filas, cargada el 6-ago) ya trae `genero`,
`pertenencia_etnica`, `discapacidad` y `ciclo_vital`, y **cruza por hash de
documento**, que sí es fiable.

- **Cobertura: 84 %** de los documentos de `Victima` (intersección de 3.823.417
  sobre 4.553.299 únicos).
- El 16 % restante quedaría **sin dato**, que es mejor que con un dato falso — y
  es la distinción que `homologar_etnia` ya hace: «no consta» ≠ «ninguna».

### Pendiente de decidir (negocio, Javier)

De dónde sale `estado_ruv`, que además define la composición del padrón:

1. El propio universo — es el snapshot del RUV, la fuente natural.
2. `RUV.TBESTADO_VAL` — el catálogo oficial de estados.

No es un detalle técnico: redefine quiénes son las 5,9 M de personas que SICAV
caracteriza.

---

## 6. Qué hacer antes de tocar nada

Independiente de la fuente que se elija:

1. **Dejar de sembrar el sexo en la APK** desde `victima.genero`, y de derivar el
   capítulo étnico desde `pertenencia_etnica`. Que se pregunte. (Requiere build.)
2. **Blindar `registrar-desde-fuente`**: hoy acepta del cliente `genero`,
   `pertenencia_etnica`, `discapacidad` y `estado_ruv`, con lo que el dato
   corrupto puede volver a entrar disfrazado de «capturado en campo».
3. **Quitar esos campos del criterio de survivorship** que elige la víctima
   preferida entre documentos repetidos, o habrá que rehacerlo dos veces.
4. **Marcar el dato como no confiable** en el admin y los serializers. El admin es
   la pantalla con la que se «verifica» el padrón: hoy confirma un dato falso.
5. **Borrar los docstrings que mienten** (`mapeo.py:277-288`).

## 7. Lo que no se puede resolver leyendo código

`M_CARACT_TABLA_RA_PER` vive en `RNIPAQUETES`, al otro lado de `DBL_VIVANTO`. No
es nuestra. Si alguien sabe cómo se relaciona con las personas —o si hay otra
tabla puente— hay que preguntárselo a quien mantiene VIVANTO.

Mientras tanto, la ruta del universo no depende de esa respuesta.

---

**Relacionado:** `docs/oracle-legacy/defectos_bd_legacy.md`,
`docs/oracle-legacy-padron/hallazgos_identidad_padron.md`,
`docs/arquitectura/adr-padron-universo-victimas.md`.
