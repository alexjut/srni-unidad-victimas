# Excepción de vigencia — se autoriza desde el front, no desde el celular

**Decidido el 14-ago-2026 · Backend implementado y probado · Falta la UI web (Brando)**

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

### Pantalla sugerida

1. **Buscar la persona** por documento (`/api/victimas/buscar/`). Si responde
   `FICHA_VIGENTE`, mostrar hasta cuándo y ofrecer autorizar.
2. **Formulario**: ruta (3 opciones), radicado, motivo, archivo opcional.
3. **Listado** de habilitaciones con su estado, para poder anular.

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
| 998 pruebas automáticas en verde (883 backend + 115 móvil) | ✅ |
| **UI web para autorizar** | ⬜ Brando |
| **Build de APK con estos cambios** | ⬜ pendiente de decidir fecha |

---

## 5. Límites conocidos

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
