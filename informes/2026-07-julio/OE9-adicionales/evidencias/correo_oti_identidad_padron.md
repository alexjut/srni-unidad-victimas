# Correo a OTI — 5 consultas de modelo de datos sobre el puente de identidad (padrón)

> Borrador para revisión de Javier. **No es una solicitud de accesos** (SICAV opera con
> `RNIENTREVISTA`, dueño del esquema): son **cinco preguntas de conocimiento del modelo**
> que ninguna consulta puede responder por nosotros, porque son de intención de diseño.
>
> **Ninguna bloquea la salida a producción.** El padrón ya está cargado (5.927.713
> víctimas incluidas) rodeando los tres puentes rotos. Lo que estas respuestas
> desbloquean es **recuperar al 24 % que quedó fuera** y dejar de depender de un rodeo.
>
> Evidencia completa: `docs/oracle-legacy-padron/hallazgos_identidad_padron.md`.

---

**Para:** [OTI — responsable del modelo de datos / DBA de `RNI_MI_PRU` y `RNIPAQUETES`]
**CC:** Oscar [supervisión funcional UARIV] · [PMO — Rommey Ruiz]
**Asunto:** Consulta técnica — puente de identidad entre el corte de caracterización, el modelo integrado y el RUV (PRY-0662064)

Estimados,

En el marco del **PRY-0662064** construimos el padrón de víctimas que consulta la
aplicación móvil de caracterización. Está **cargado y operativo**: 5.927.713 víctimas
incluidas, resueltas cruzando `RNIENTREVISTA.GIC_PERSONA` con el corte
`RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO`.

Llegamos ahí **por un rodeo**. La ruta natural —`GIC_PERSONA` → `MI_PERSONAS` para
tomar los datos de identidad— no la pudimos usar: los tres caminos que probamos daban,
cada uno a su manera, **datos de otra persona**, y sin error visible. El costo del rodeo
es que **1.884.872 víctimas incluidas (24 %) quedaron fuera del padrón** por no poder
resolver su identidad, y el encuestador tiene que darlas de alta a mano en campo.

Todo lo que sigue se midió con `SELECT` sobre producción; **no se modificó nada**. Son
cinco preguntas de **intención de diseño**, que no se deducen de los datos.

---

**1. ¿Qué `FUENTE` corresponde al `CONS_PERONA` del corte de caracterización?**

`RNI_MI_PRU.DEP_RUV_PERSONAS_MI` (11.437.570 filas) tiene tres valores de `FUENTE`:
`RUPD` (5.935.569), `RUV` (5.067.278) y `SIV` (434.723). Al cruzar una muestra de
**3.000** personas incluidas del corte contra ese puente, obtuvimos:

| `FUENTE` | coincidencias |
|---|---:|
| `RUPD` | 2.971 |
| `SIV` | 2.946 |
| `RUV` | **0** |

Es decir: **el mismo `CONS_PERONA` existe en dos registros distintos** y devuelve ~2
filas por persona, sin criterio para elegir. En toda la tabla, **433.696 `ID_PERSONA`
apuntan a más de un `PER_ID`** del modelo integrado. Sin saber qué fuente aplica,
cualquier elección le asigna a una víctima los datos de otra.

*Es la pregunta más importante de las cinco: resolverla recupera la ruta a
`MI_PERSONAS` y con ella al 24 % que hoy queda fuera.*

**2. ¿Contra qué tabla cruza `GIC_PERSONA.PER_IDMODELOINT`?**

Parecía la llave natural al modelo integrado: 7.760.390 de 7.760.393 filas la traen
poblada. Probamos 20.000 de esas llaves contra `MI_PERSONAS.PER_ID` y el resultado fue
**0 coincidencias**. ¿Apunta a una versión anterior del modelo integrado, o quedó
huérfana de una migración? ¿Hay una tabla vigente contra la cual sí resuelva?

**3. ¿`GIC_RUV_PERSONA` se dejó de usar a propósito, o quedó pendiente de poblar?
¿Podemos poblarla nosotros?**

`RNIENTREVISTA.GIC_RUV_PERSONA` (`CONS_PERSONA`, `PER_IDPERSONA`, `REG_TIMESTAMP`)
tiene **0 filas**, y su procedimiento de escritura `GIC_SP_INGRESO_RUV_PERSONA` está
escrito y compilado. Es exactamente el puente que resolvería los dos puntos anteriores,
y del lado de nuestro esquema.

El propio código lo anota — `GIC_CARACTERIZACION`, línea 302:

```sql
-- SE DEBE CAMBIAR CUANDO SE AGREGUE EL IDPERSONA DE LA TABLA MI_PERSONAS DEL MODELO INTEGRADO
```

Si no hay una razón que lo desaconseje, **nos ofrecemos a poblarla** conforme el
padrón se vaya resolviendo, usando su procedimiento oficial.

**4. Confirmación del catálogo de `ESTADO_RUV` en el corte.**

Interpretamos `ESTADO_RUV` de `M_CARACT_TABLA_RA_PER` con `TBESTADO_VAL`
(1 = Incluido … 7 = No Afectado-No Valorado), y **de eso depende quién entra al
padrón**. Lo que nos hace pensar que es el catálogo correcto: los 7.821.641 con
`ESTADO_RUV = 1` coinciden con la cifra pública de víctimas sujeto de atención, y
"Excluido" con solo 340 personas es coherente con que excluir requiera acto
administrativo. Solo necesitamos que lo confirmen.

**5. ¿Con qué periodicidad se refresca `M_CARACT_TABLA_RA_PER`?**

De eso depende cada cuánto programamos la recarga del padrón. Hoy la dejamos mensual
por precaución (primer sábado, 20:00), pero preferimos alinearla con su ciclo real.

---

Con gusto ampliamos cualquiera de los puntos o mostramos las consultas que usamos.

Cordialmente,
**Javier Aguilar** — Desarrollo y arquitectura, SICAV / SRNI (PRY-0662064)

---

### Notas para Javier (no enviar)

- **Ninguna de las cinco bloquea el despliegue.** Si el correo se demora, no se detiene
  nada: el padrón funciona y el alta manual cubre el hueco.
- **Prioridad real:** la 1 y la 3 son las que recuperan el 24 %. La 2 es diagnóstico, la
  4 es confirmación barata y la 5 es operativa. Si hay que recortar el correo para que
  lo respondan, dejá la 1 y la 3.
- La 3 está redactada como **ofrecimiento**, no como pedido de permiso: `GIC_RUV_PERSONA`
  vive en `RNIENTREVISTA`, que es nuestro. Es cortesía de gobernanza, no autorización.
- **No pedir accesos.** Ya se aclaró en el correo anterior
  (`correo_oti_aviso_escritura_prod.md`) y sigue vigente.
- Si preferís mandarlo como **una sola pregunta** para maximizar la respuesta, la 1 es
  la que hay que hacer.
