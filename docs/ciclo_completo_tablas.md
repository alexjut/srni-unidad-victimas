# El ciclo completo: qué tablas mantienen viva la APK

> **Qué es esto.** El recorrido entero de un dato, desde que la APK se enciende
> hasta que el hogar caracterizado aparece en el Oracle de la UARIV y en un
> reporte. Para cada etapa: **qué tabla la sostiene, quién la llena y qué pasa si
> está vacía**.
>
> **Por qué existe.** Durante meses el trabajo fue por partes —instrumento,
> padrón, escritura a Oracle, reportes— y cada parte se documentó sola. Este es el
> mapa de cómo encajan. Sirve para dos cosas: saber qué falta para que el ciclo
> cierre, y saber qué se rompe cuando algo falla.
>
> Última verificación contra el código: **31-jul-2026**.

---

## El ciclo en una vista

```
        ┌─────────────────── 1. ARRANQUE (online, una vez) ──────────────────┐
        │  login → instrumento → paramétricas → PADRÓN (SQLite, offline)     │
        └────────────────────────────────┬───────────────────────────────────┘
                                         ▼
        ┌─────────────────── 2. CAMPO (offline, sin señal) ──────────────────┐
        │  buscar persona → armar hogar → responder el instrumento           │
        └────────────────────────────────┬───────────────────────────────────┘
                                         ▼
        ┌─────────────────── 3. SINCRONIZACIÓN (al volver la señal) ─────────┐
        │  APK → backend (PostgreSQL) → Celery → procedures GIC_* → Oracle   │
        └────────────────────────────────┬───────────────────────────────────┘
                                         ▼
        ┌─────────────────── 4. REPORTES ────────────────────────────────────┐
        │  producción por encuestador · supervisor · dashboard               │
        └────────────────────────────────────────────────────────────────────┘
```

---

## 1. Arranque — lo que la APK descarga para poder trabajar sin señal

| Tabla | Qué aporta | Quién la llena | Si está vacía |
|---|---|---|---|
| `autenticacion.Usuario` · `Perfil` | quién entra y qué puede hacer | admin web | **nadie puede entrar** |
| `formulario.Instrumento` | los 8 instrumentos (Territorial, Asistencia, Telefónico…) | `cargar_perfil` desde el fixture | no hay nada que preguntar |
| `formulario.Capitulo` | los capítulos A–H de cada instrumento | idem | ídem |
| `formulario.Pregunta` | las preguntas, su tipo y a quién aplican | idem | ídem |
| `formulario.OpcionRespuesta` | las opciones de cada lista | idem | listas vacías en campo |
| `formulario.ReglaSkipLogic` | qué se muestra y qué se salta | idem | se preguntaría **todo a todos** |
| `parametricas.Departamento` · `Municipio` · `Vereda` | DIVIPOLA | `cargar_divipola` | no se puede ubicar el hogar |
| `parametricas.ComunidadNegra` · `ResguardoIndigena` | territorios étnicos | idem | el módulo étnico queda sin listas |
| `parametricas.TipoDocumento` | tipos de documento de SICAV | fixture | la identificación queda incompleta |
| `parametricas.DireccionTerritorial` · `PuntoAtencion` | dónde se atiende | fixture | no se puede cerrar la sesión |
| **`victimas.Victima`** | **el padrón: a quién se caracteriza** | **`cargar_padron_oracle`** | **no se encuentra a nadie en campo** |

**El padrón es la pieza que se acaba de cerrar.** Sale de `GIC_PERSONA` cruzada
con el corte del RUV, filtrando `ESTADO_RUV = 1`: **5.936.769 víctimas
incluidas**. Se baja a la APK como un SQLite indexado por hash del documento.
Detalle en [`oracle-legacy-padron/hallazgos_identidad_padron.md`](oracle-legacy-padron/hallazgos_identidad_padron.md).

**Ojo con esto:** 1.884.872 víctimas incluidas (24 %) **no están** porque la .9 no
tiene su identidad. La APK **tiene que permitir alta manual** — no es un caso raro.

---

## 2. Campo — lo que se llena sin señal

| Tabla | Qué guarda | Cuándo se crea |
|---|---|---|
| `hogares.Hogar` | el hogar: código, vivienda, estrato, municipio | al iniciar la caracterización |
| `hogares.MiembroHogar` | cada persona del hogar y su parentesco | al conformar el hogar |
| `encuestas.SesionEncuesta` | la entrevista: instrumento, ruta, encuestador, avance | al abrir el instrumento |
| `encuestas.RespuestaEncuesta` | **cada respuesta**, por pregunta y por miembro | mientras se responde |
| `victimas.Victima` | altas manuales de quien no estaba en el padrón | en campo, `creado_por` marcado |
| `ia.ConsentimientoIA` · `SesionIA` | el asistente de voz, si se usa | opcional |

`Hogar.autorizado` es el titular de la entrevista. `RespuestaEncuesta.miembro`
distingue lo que se pregunta **por persona** de lo que es **del hogar** — esa
distinción es la que hace que el capítulo étnico y el de salud funcionen.

---

## 3. Sincronización — de nuestra base al Oracle de la UARIV

Cuando vuelve la señal, la APK sube a PostgreSQL y **Celery** dispara la escritura
hacia el legacy. Nunca con `INSERT` directo: **siempre por los procedures
oficiales `GIC_*`**.

| Orden | Procedure | Qué escribe en Oracle |
|---:|---|---|
| 1 | `GIC_CATEGORIZACION.GIC_INSERT_HOGAR1` | `GIC_HOGAR` |
| 2 | `GIC_CATEGORIZACION.GIC_INSERT_PERSONAS` | `GIC_PERSONA` |
| 3 | `GIC_CATEGORIZACION.GIC_INSERT_MIEMBRO_HOGAR` | `GIC_MIEMBROS_HOGAR` |
| 4 | `GIC_N_CARACTERIZACION.SP_SET_RESPUESTAS_DE_ENCUESTA` | `GIC_N_RESPUESTASENCUESTA` |
| 5 | `GIC_N_CARACTERIZACION.GIC_SP_OBDEPTOPORDT` | cascada territorial |
| 6 | `GIC_N_CARACTERIZACION.GIC_SP_OBTPUNTOATECION` | punto de atención |
| 7 | `GIC_N_CARACTERIZACION.GIC_SP_OBMUNICIPIOATECION` | municipio de atención |
| 8 | `GIC_N_CARACTERIZACION.GIC_SP_GUARDAMUNATEN` | `GIC_MUNICIPIOATENCION` |

| Tabla nuestra | Para qué |
|---|---|
| `sincronizacion.RegistroEscrituraOracle` | qué se escribió, cuándo, con qué resultado — **la evidencia** |
| `sincronizacion.PasoEscritura` · `EstadoPaso` | en qué paso va cada hogar |
| `auditoria.LogAcceso` | quién consultó qué |

**Por qué el registro no es opcional.** Los procedures hacen `COMMIT` interno y
tienen `EXCEPTION WHEN OTHERS` sin re-lanzar: **se tragan los errores y devuelven
éxito igual**. Un escrito solo cuenta si después se verifica con un `SELECT`. Eso
es lo que hace `verificacion.py` y lo que queda en `RegistroEscrituraOracle`.
Ver [`oracle-legacy/defectos_bd_legacy.md`](oracle-legacy/defectos_bd_legacy.md) D1.

**Estado:** piloto en producción logrado el 28-jul (hogar `999999-2W832`, 11/11
verificados). Ya hay filas de SICAV en el Oracle de la UARIV.

---

## 4. Reportes — el cierre del ciclo

Todos leen de `SesionEncuesta` + `RespuestaEncuesta`; no hay tablas propias de
reportes (`apps/reportes/models.py` está vacío a propósito: se calcula al vuelo).

| Endpoint | Qué responde |
|---|---|
| `GET /api/reportes/produccion/` | cuánto lleva cada encuestador en un período |
| `GET /api/reportes/produccion/detalle/` | sesión por sesión |
| `GET /api/reportes/produccion/export/` | lo mismo en CSV |
| `GET /api/reportes/supervisor/` | consolidado para el supervisor |
| `GET /api/reportes/dashboard/series/` | series para las gráficas del panel |

---

## Qué falta para que el ciclo cierre entero

| # | Falta | Impacto | Estado |
|---|---|---|---|
| 1 | Terminar la carga del padrón | sin esto la APK no encuentra a nadie | **en ejecución** |
| 2 | `cargar_fechas_caracterizacion` | sin esto no se sabe a quién recaracterizar | listo, ~1 min |
| 3 | **Poner `VICTIMA_REPOSITORY=DJANGO`** | **producción responde con el MOCK** | **corregido, falta desplegar** |
| 4 | Generar el padrón SQLite descargable | la APK baja el archivo, no consulta en línea | pendiente |
| 5 | Disparador automático (Celery) | hoy la escritura a Oracle se dispara a mano | credenciales ya en el contenedor |
| 6 | Etiqueta del alta manual | ver abajo | a decidir |

### El punto 3, que es el más grave y el más invisible

`get_repository()` elige la fuente con `settings.VICTIMA_REPOSITORY`, y **ese
setting no existía**: `getattr(settings, "VICTIMA_REPOSITORY", "MOCK")` caía al
mock. Producción llevaba semanas respondiendo **ENC001 y documentos 999…** a las
búsquedas por documento.

Lo engañoso es que el sistema *funciona*: busca, encuentra, deja caracterizar. Solo
que contra otra base. Se podría haber cargado el padrón entero sin que cambiara
nada en la APK.

**Corregido:** el setting ya se lee (`base.py`), el compose lo pone en `DJANGO`, y
`test_el_selector_de_repositorio_es_una_variable_de_settings` falla si alguien
vuelve a quitarlo.

### El punto 6 — cómo se etiqueta a quien no está en el padrón

La alta manual **sí existe y está conectada** (`busqueda.tsx` → `crearVictimaOffline`,
con camino online y offline por cola). Funciona.

El detalle es la etiqueta: hoy el flujo dice *"No encontrado → registrar como
**Víctima No Incluida**"*. Eso es correcto para quien de verdad no está en el RUV,
pero **las 1,88 M que quedan fuera del padrón SÍ son víctimas incluidas** — lo que
falta es su identidad en la .9, no su condición.

Registrarlas como "No Incluida" les pone un estado que no les corresponde, y ese
estado viaja al hogar y a los reportes.

**Propuesta:** un tercer resultado, *"no está en el padrón descargado"*, distinto de
*"no está en el RUV"*. Es decisión funcional, no técnica.

---

## Cómo usar este mapa

Cuando algo falle en campo, la pregunta es **en qué etapa**: si no encuentra a la
persona es (1), si no puede guardar es (2), si no llega a la UARIV es (3), si no
aparece en el tablero es (4). Cada etapa tiene su tabla y su comando.
