# Por qué "no se pudo caracterizar" — análisis del error

**4-ago-2026.** Disparado por dos casos reales del territorio: `28548486` y
`1115724047`, que en **Vivanto sí aparecen para caracterizar** y en SICAV no.

La conclusión corta: **el reporte junta dos problemas distintos**, y el segundo
es un incumplimiento del manual que afecta a **1.058.971 personas**.

---

## 1. Qué pasa con cada cédula

| Cédula | `GIC_PERSONA` (legacy) | RUV | Padrón SICAV |
|---|---|---|---|
| **28548486** | **no está** | **sí** — `TBPERSONAS.ID` = 17796377 | **no está** |
| **1115724047** | **sí**, 3 registros (2017-04-28, 2022-04-08, **2026-07-28**) | — | **no está** |

### Por qué no están: el padrón nace del legacy, no del RUV

```sql
FROM gic_persona p
JOIN RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO c
  ON c.cons_perona = p.per_idpersona
```

Es un **`INNER JOIN` que parte de `GIC_PERSONA`**, y de ahí salen dos exclusiones
que nadie ve al usar la app:

1. **Quien no está en `GIC_PERSONA` no puede entrar jamás** — da igual que esté
   en el RUV. Es el caso de `28548486`.
2. Quien sí está pero cuyo `per_idpersona` no cruza con `cons_perona` tampoco
   entra. Es el caso probable de `1115724047`.

Son los **1.884.872 (24 %)** que quedaron fuera.

**El manual explica por qué en Vivanto sí salen.** Al consultar la cédula, el
sistema oficial consulta (§5.1.1, pág. 22): *Registraduría · TUP · **Búsqueda
RUV** · Ficha de Caracterización · Entrevista Única*. **Vivanto pregunta al RUV;
SICAV pregunta a su padrón derivado del legacy.** No es un bloqueo: es ausencia.

---

## 2. 🔴 Las rutas no hacen nada — y el manual dice que tres deben omitir la vigencia

**Esto es lo más grave del análisis.** El manual (§5.1.1, pág. 22) define cuatro
rutas y qué hace cada una con la regla de vigencia:

| Ruta | Manual | SICAV hoy |
|---|---|---|
| **General** | casos **sin** ficha vigente — *"se respeta la regla de vigencia"* | etiqueta |
| **Acciones Constitucionales** | fallos, tutelas, autos de seguimiento **con ficha vigente** — *"se deberá **omitir** la regla de vigencia"* | **etiqueta — no omite nada** |
| **Modificación núcleo familiar** | ficha vigente pero diferencias en la conformación — *"se deberá **omitir**"* | **etiqueta — no omite nada** |
| **Especial** | protección especial o urgencia, con ficha vigente — *"se deberá **omitir**"* | **etiqueta — no omite nada** |

> **Nota del manual:** *"Para las jornadas de caracterización, a excepción de la
> realizada directamente por la Unidad para las Víctimas en el marco de la
> solicitud de entrega de atención humanitaria, se debe seleccionar RUTA
> GENERAL."*

En SICAV, `ruta_entrevista` es **solo un campo de `SesionEncuesta`**
(`apps/encuestas/models.py:36`): registra bajo qué condición se hizo la
entrevista y **no hay una sola línea que la use para saltar el bloqueo**.

**Consecuencia:** las tres rutas que existen precisamente para atender casos con
ficha vigente **no pueden atenderlos**. Una tutela no habilita nada.

---

## 3. Cuánta gente afecta (medido en producción, 4-ago)

| | |
|---|---|
| Padrón total | **5.926.004** |
| **Bloqueadas por la regla de vigencia** | **1.058.971 (17,9 %)** |
| Bloqueadas sin fecha (mensaje mudo) | **0** |
| Excluidas del RUV | **0** |

**1.058.971 personas** están hoy detrás del mensaje *"Ya fue caracterizada el
…"*, sin vía de excepción funcionando. Es a quienes afecta el punto 2.

Los otros dos estados —bloqueada sin fecha, y excluida del RUV— **hoy no le
ocurren a nadie**. Están en el código y conviene arreglarlos por higiene, pero
no son el problema de nadie ahora mismo.

---

## 4. Los mensajes: qué se le dice al encuestador

| # | Situación | Qué responde hoy | Problema |
|---|---|---|---|
| 1 | Elegible | ficha, sin mensaje | ✅ |
| 2 | **No está en el padrón** | *"No se encontró la persona en el padrón cargado en SICAV."* | 🔴 se lee como **"no es víctima"** |
| 3 | Documento de relleno | mensaje propio + `no_identificante=True` | ✅ bien resuelto |
| 4 | Excluida del RUV | *"Persona excluida del RUV — no elegible."* | 🟠 nadie hoy |
| 5 | **Ficha vigente (< 2 años)** | *"Ya fue caracterizada el 2025-03-14."* | 🔴 **1.058.971 personas** |
| 6 | Bloqueada sin fecha | *"La persona no está habilitada para caracterización."* | 🟠 nadie hoy |

### 🔴 "No se encontró en el padrón" miente por omisión

El encuestador lee *"no se encontró"* y entiende **"no es víctima"**. Pero
`28548486` **sí es víctima y está en el RUV**. Debe decir las dos cosas: que
**puede estar en el RUV aunque no esté acá**, y que la vía es el **alta manual**
— que no es una excepción, es el flujo previsto para 1 de cada 4.

### 🔴 "Ya fue caracterizada el X" es un callejón sin salida

Le falta todo lo que permite actuar:

- **Hasta cuándo.** La regla es `ANIOS_VIGENCIA_CARACTERIZACION = 2`
  (`apps/victimas/homologacion.py`), pero el encuestador no la conoce: ve una
  fecha suelta y no sabe si faltan dos meses o dos años.

> ### ✅ La regla de 2 años es real y NO se deroga
>
> **Confirmado por Javier el 5-ago-2026.** Un análisis posterior a este documento
> la marcó como *"sin fuente citada"* por no encontrarla en los manuales 11-MU /
> 14-MU, y **esa observación era incorrecta**. Queda anulada: una nota que dice
> que un control no tiene respaldo es una invitación a quitarlo.
>
> **Cómo se aplica:** la **ruta general** la respeta —es el caso por defecto— y
> las otras tres rutas la omiten, según el Manual §5.1.1 (pág. 22).
>
> **Las fechas que la sustentan** están en `TEMP_UNIV_VICT_CONTING`
> (`ENTRE_FICHA_VIGENTE`, `FECHA_CREACION`, `ID_ENTREVISTA`): la vigencia **dicha
> por la fuente**, no calculada por nosotros. Mientras no haya acceso a esa tabla,
> el cálculo con `fecha_ult_caracterizacion` es un **sustituto**, no la fuente.
- **Que existe una vía.** Con acción constitucional **sí debe poder
  caracterizarla**, y el mensaje no lo menciona. Por eso se escala en vez de
  resolverse en campo — que es exactamente lo que pasó.

**El mensaje que se pidió (Javier, 4-ago):**

> *"Esta persona fue caracterizada el **{fecha}**. Solo puede caracterizarla si
> tiene una **acción constitucional** (fallo, tutela o auto). Si la tiene, tome
> **foto del soporte** para continuar."*

### 🟠 La respuesta no trae un motivo legible por máquina

`ResultadoBusqueda` expone `encontrado`, `victima`, `fuente`, `mensaje`,
`candidatos`, `no_identificante`. **El porqué del bloqueo viaja solo como texto
libre.** Por eso la app no puede ofrecer el botón correcto —"Dar de alta",
"Registrar acción constitucional"— y todo termina en una frase sin salida.

### 🟠 La lógica de los mensajes está duplicada

`buscar_por_documento` (`django_orm.py:295-302`) y `estado_habilitacion`
(`:406-413`) deciden lo mismo por separado, y **ya divergen** en el texto. Hoy es
cosmético; el día que una gane un caso y la otra no, son dos comportamientos
distintos según por dónde entre la app.

---

## 5. Qué hacer

### Ahora, para desatascar los dos casos

| Cédula | Vía |
|---|---|
| `28548486` | **alta manual** — no está en el padrón, no hay atajo |
| `1115724047` | **alta manual**, o habilitarla por el endpoint de actualización (`apps/victimas/views.py:477`) |

### Las mejoras, por orden de lo que más duele

1. **Implementar las rutas como excepción real a la vigencia**, según el manual:
   `ACCIONES_CONSTITUCIONALES`, `MODIFICACION_NUCLEO` y `ESPECIAL` omiten la
   regla; `GENERAL` la respeta. Afecta a 1.058.971 personas.
2. **Exigir soporte fotográfico** al usar una ruta de excepción, y guardarlo
   junto con quién la usó, sobre quién y cuándo. Saltarse un control sin dejar
   rastro es peor que el bloqueo.
3. **Un `motivo` enumerado en la respuesta**: `ELEGIBLE` · `NO_EN_PADRON` ·
   `DOCUMENTO_NO_IDENTIFICANTE` · `EXCLUIDA_RUV` · `FICHA_VIGENTE` ·
   `BLOQUEADA_SIN_MOTIVO`. Es lo que habilita que la app ofrezca la acción
   correcta en vez de una frase.
4. **Decir hasta cuándo**: agregar `disponible_desde` (fecha + 2 años) y el
   mensaje pedido arriba.
5. **Reescribir el mensaje de "no está en el padrón"** para que no se lea como
   "no es víctima" y dirija al alta manual.
6. **Unificar los dos lugares** que arman el motivo, para que no puedan divergir.

### Lo que falta confirmar antes de implementar

- **Quién puede usar cada ruta.** El manual dice cuándo aplica cada una, pero no
  si cualquier encuestador puede elegirla o requiere un perfil. Si cualquiera
  puede, la regla de vigencia se vuelve opcional en la práctica.
- **Qué se hace con la ficha anterior** al recaracterizar por excepción:
  ¿se reemplaza, se versiona, conviven? El manual no lo dice en §5.1.1.
