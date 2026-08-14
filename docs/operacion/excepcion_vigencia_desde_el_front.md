# Excepción de vigencia — se autoriza desde el front, no desde el celular

**Decidido el 14-ago-2026 · Backend y pantalla implementados y probados**

> **La pantalla ya existe: `/autorizaciones/`.** Se hizo en el backend y no en
> `srni-frontend/` para no depender del ciclo del front web ni pisar el trabajo
> de Brando. Es HTML plano servido por Django, sin build y sin CDN —el filtro
> institucional corta dominios externos—, y consume la misma API documentada
> acá. Si más adelante el front web la incorpora, el contrato ya está.

---

## 1. Qué cambió y por qué

Una persona caracterizada hace menos de dos años tiene **ficha vigente** y no se
puede recaracterizar. El Manual UARIV §5.1.1 autoriza tres rutas a omitir esa
regla —acciones constitucionales, modificación de núcleo familiar y ruta
especial— siempre que haya un soporte: un fallo, una tutela, un auto.

**Cómo era (6-ago → 13-ago):** el encuestador encontraba la ficha vigente,
elegía la ruta en el celular, **tomaba una foto del soporte** y con eso
continuaba.

**Por qué no servía:** el caracterizador no tiene ese documento. El fallo o la
tutela llegan por canal institucional al nivel central, no a quien está parado
frente a la víctima en el barrio. Se le estaba pidiendo algo que no puede dar.

**Cómo es ahora:** la excepción se **autoriza antes**, desde la plataforma web,
por coordinación o supervisión. El celular solo la consume.

El efecto secundario es el que más importa: **quien autoriza el salto de un
control dejó de ser quien lo ejecuta.** Antes el encuestador se autoautorizaba.

---

## 2. El flujo completo

```
1. El encuestador busca a la persona y ve:
      «Ficha vigente hasta el 14/03/2028. Para actualizarla hace falta una
       excepción, que se autoriza desde la plataforma web: solicítela a su
       coordinación con el radicado del soporte.»

2. Coordinación recibe el soporte por el canal institucional y lo registra:
      POST /api/habilitaciones/

3. La persona queda habilitada.

4. El celular lo ve:
      · en la precarga de la jornada siguiente  → funciona SIN señal
      · o al tocar «Ya la autorizaron — volver a consultar», con señal

5. Al finalizar la caracterización la habilitación se consume (USADA).
   No queda un permiso abierto.
```

---

## 3. Contrato de la API — lo que necesita el front

### Quién puede

Perfil con `puede_autorizar_excepciones`. La migración lo enciende en
**COORDINADOR, SUPERVISOR y ADMINISTRADOR**.

No lo tienen, a propósito:

- **ENCUESTADOR** — es quien ejecuta; separar autorización de ejecución es la
  razón del cambio.
- **DOCUMENTADOR** — se creó de solo lectura el 11-ago. Habilitar una excepción
  altera la caracterización de una víctima. Se usa un flag propio y no
  `puede_ver_reportes` justamente para no darle por la puerta de atrás lo que se
  le negó de frente.

> ⚠️ **Cuello de botella operativo.** Hoy en producción hay **1 coordinador, 1
> supervisor y 1 admin** para 1.158 encuestadoras. Antes de arrancar en campo
> hay que decidir cuántas cuentas con este permiso se necesitan y quién las
> tiene. No es un pendiente técnico: es una definición de operación.

### `POST /api/habilitaciones/` — autorizar

```jsonc
{
  "victima_id": "uuid",                     // requerido
  "ruta": "ACCIONES_CONSTITUCIONALES",      // o MODIFICACION_NUCLEO, ESPECIAL
  "radicado": "T-2026-451",                 // requerido
  "observacion": "Fallo de tutela que ...", // requerido, mínimo 10 caracteres
  "soporte": <archivo>                      // OPCIONAL (multipart)
}
```

Respuestas:

| Código | Cuándo |
|---|---|
| `201` | Autorizada. Devuelve la habilitación completa. |
| `400` | Falta radicado, motivo muy corto, o la ruta es `GENERAL` (esa respeta la vigencia: no hay excepción que autorizar). |
| `403` | El perfil no puede autorizar. |
| `404` | La víctima no existe. |
| `409` | Ya hay una habilitación vigente para esa persona, **o** la persona está excluida del RUV. En el primer caso devuelve la existente en `habilitacion`. |

El archivo es **opcional** a propósito: exigirlo dejaría fuera los casos que
llegan por correo o por teléfono, y el radicado ya permite ir a buscar el
documento. Lo obligatorio es el par radicado + motivo.

### `GET|POST /api/habilitaciones/buscar/` — documento → personas

Devuelve el `id` que pide el POST, que ningún otro endpoint daba: la búsqueda de
víctimas no expone el id y el detalle exige `puede_caracterizar` (permiso que el
supervisor no tiene).

```
GET  ?tipo_documento=CC&numero_documento=1115724047
POST {"tipo_documento": "CC", "documentos": ["1115724047", "1030547250"]}
```

Acepta hasta 200 documentos. Cada resultado trae `motivo`, `ficha_vigente_hasta`,
`requiere_excepcion` y `habilitacion_vigente` (si ya la tiene). Los documentos
que no existen vuelven en `sin_coincidencia` — es lo que evita dar por cubierta
a una persona del oficio que no está en el padrón.

### `POST /api/habilitaciones/lote/` — autorizar a varias

Mismo cuerpo que el individual pero con `victima_ids: [...]`. Un fallo ampara a
un hogar entero; pedir que se repita el formulario veinte veces es cómo se
terminan autorizando cosas a las apuradas.

**No es atómico a propósito.** Lo que no se pudo autorizar vuelve en `omitidas`
con su motivo (`YA_HABILITADA`, `EXCLUIDA_RUV`, `NO_EXISTE`) y el resto se
autoriza igual. Responde `201` si se creó al menos una y `409` si no se creó
ninguna — un `201` con cero creadas diría que quedó hecho cuando no se hizo nada.

### `GET /api/habilitaciones/` — listar

Filtros: `?estado=VIGENTE|USADA|ANULADA`, `?ruta=`, `?victima=`.
Orden por defecto: más recientes primero.

Cada fila trae `victima_documento`, `victima_nombre`, `ruta_display`,
`estado_display`, `autorizada_por_codigo`, `created_at`, `usada_at`,
`anulada_at`, `motivo_anulacion`.

### `POST /api/habilitaciones/{id}/anular/`

```jsonc
{ "motivo": "Se autorizó sobre la persona equivocada." }   // mínimo 10 caracteres
```

`409` si ya estaba usada o anulada. **No borra**: una autorización otorgada y
retirada es justamente lo que una auditoría necesita poder ver.

### La pantalla — `/autorizaciones/`

Una sola página, tres bloques:

1. **Buscar** — se pegan una o muchas cédulas (separadas por espacios, comas o
   una por línea). Sale una tabla con la situación de cada persona y una casilla
   solo en las que se puede autorizar. Las que ya tienen excepción, las excluidas
   del RUV y las que ya pueden caracterizarse aparecen con su estado pero sin
   casilla: ofrecer el botón donde el POST va a dar 409 hace que el error se
   descubra después de llenar todo el formulario.
2. **Autorizar** — ruta, radicado, motivo y archivo opcional, aplicados a todas
   las seleccionadas de una vez.
3. **Listado** — filtrable por estado, con el botón de anular en las vigentes.

El token vive en memoria y no en `localStorage`: es un equipo de oficina
compartido, y un token que sobrevive al cierre del navegador es una sesión de
coordinación abierta para quien se siente después.

---

## 4. Lo que ya está hecho (backend + APK)

| | |
|---|---|
| Modelo `ExcepcionVigencia` como habilitación previa, de un solo uso | ✅ |
| Flag de perfil `puede_autorizar_excepciones` + migración que lo enciende | ✅ |
| `POST/GET /api/habilitaciones/` + `anular` | ✅ |
| La búsqueda deja pasar a quien tiene habilitación vigente | ✅ |
| La habilitación viaja en la precarga y se guarda en el celular (schema v12) | ✅ |
| Se consume al finalizar la encuesta | ✅ |
| La APK dejó de pedir la foto; ahora dice a quién solicitarla | ✅ |
| `POST /api/encuestas/{id}/excepcion-vigencia/` responde `410` con la explicación | ✅ |
| Búsqueda por documento y autorización **en lote** | ✅ |
| **Pantalla `/autorizaciones/`** — buscar, seleccionar, autorizar, anular | ✅ |
| 1.008 pruebas automáticas en verde (893 backend + 115 móvil) | ✅ |
| **Build de APK con estos cambios** (v1.2.0) | ⬜ pendiente de decidir fecha |
| **Cuántas cuentas con permiso de autorizar** | ⬜ definición de operación |

Verificado contra el servidor, no solo con pruebas: login, búsqueda de 3
documentos (2 encontrados + 1 inexistente), autorización en lote de 2, y el
intento repetido devolviendo `YA_HABILITADA` sin duplicar nada.

---

## 5. Cómo probarla

En local, con la base de desarrollo ya migrada y sembrada:

```
http://127.0.0.1:8001/autorizaciones/     usuario QACOORD · SrniTest2026!
```

Hay dos personas de prueba con ficha vigente —`9990000001` y `9990000002`— y una
excepción ya autorizada sobre ambas, para ver los dos estados. En producción la
URL es `https://caracterizacion.unidadvictimas.gov.co/autorizaciones/` y se entra
con el usuario real de SICAV.

---

## 6. Límites conocidos

- **Una habilitación otorgada después de que arrancó la jornada no llega al
  celular hasta la sincronización siguiente.** Es la consecuencia de que
  funcione sin señal. El botón «Ya la autorizaron — volver a consultar» cubre el
  caso cuando hay red.
- **La APK en campo (v1.1.0) todavía muestra el botón de adjuntar soporte.**
  Hasta que se despliegue una versión nueva, ese botón responde `410` con el
  texto que explica a dónde ir. No queda como error de red.
- **Un defecto que quedó a la vista:** el endpoint viejo escribía la auditoría
  con `LogAcceso.objects.create(..., ip=...)`, y ese campo se llama `ip_origen`
  mientras `detalle` es un `JSONField`. Toda llamada terminaba en 500 antes de
  responder. No se había detectado porque ninguna encuestadora ha entrado nunca
  al sistema. Ya no aplica —el endpoint se retiró— pero conviene saber que **la
  ruta de excepción nunca funcionó en producción**, ni siquiera la vieja.
