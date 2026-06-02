# Respuesta para Brando — integración semana 1 junio 2026

**Para:** Brando
**De:** Javier Alexander Aguilar Castro
**Fecha:** 2026-06-01
**Asunto:** Listo: tu trabajo mergeado a `main` + los dos endpoints que pediste

---

Hola Brando,

Excelente avance. Ya está todo integrado y los dos endpoints que necesitabas están funcionando. Resumen de lo que hice:

## 1. Tu trabajo mergeado a `main` (azure + github)

Hice merge no-fast-forward de `azure/frontend` → `main` con tus 19 commits de la semana. Después cascadé el merge a `frontend` y `develop`, todo pusheado a los dos remotes. Lo verificás en:

- Azure: `main`, `frontend`, `develop` actualizadas
- GitHub: lo mismo

Cuando arranques mañana, hacé `git pull` en tu rama `frontend` para traer también el merge + los endpoints nuevos.

## 2. Endpoint de auditoría — **LISTO**

`GET /api/auditoria/logs/`

**Shape** (paginada PageNumber, igual que hogares/encuestas):

```json
{
  "count": 386,
  "next": "http://.../api/auditoria/logs/?page=2",
  "previous": null,
  "results": [
    {
      "id": "0fd1b7e9-ca28-4aef-bc35-023191927346",
      "codigo_usuario": "ALEXJUT",
      "usuario_nombre": "Javier Alexander Aguilar Castro",
      "accion": "BUSQUEDA_RNI",
      "accion_display": "Búsqueda en el RNI",
      "recurso": "Victima",
      "recurso_id": "d77150a5-1deb-4fca-b5e9-f7bbb44bb63c",
      "ip_origen": "127.0.0.1",
      "resultado": "EXITO",
      "resultado_display": "Éxito",
      "detalle": {"encontrado": true, "tipo_documento": "CC"},
      "timestamp": "2026-05-29T13:53:41.092109-05:00"
    }
  ]
}
```

**Filtros disponibles (query params):**

| Parámetro | Tipo | Ejemplo |
|---|---|---|
| `accion` | exacto (case-insensitive) | `accion=LOGIN`, `accion=BUSQUEDA_RNI`, `accion=CREAR_HOGAR` |
| `resultado` | exacto | `resultado=EXITO`, `resultado=DENEGADO`, `resultado=ERROR` |
| `codigo_usuario` | exacto | `codigo_usuario=ALEXJUT` |
| `fecha_desde` | YYYY-MM-DD | `fecha_desde=2026-01-01` |
| `fecha_hasta` | YYYY-MM-DD | `fecha_hasta=2026-12-31` |
| `search` | búsqueda libre | `search=127.0.0.1` (busca en recurso, recurso_id, ip) |
| `ordering` | campo | `ordering=-timestamp` (default), `ordering=accion` |
| `page` / `page_size` | paginación | `page=2&page_size=50` |

**Acciones disponibles** (para tu `<select>` de filtros):
`LOGIN`, `LOGOUT`, `LOGIN_FALLIDO`, `BUSQUEDA_RNI`, `VER_VICTIMA`, `CREAR_HOGAR`, `AGREGAR_MIEMBRO`, `RESPONDER_PREGUNTA`, `FINALIZAR_ENCUESTA`, `EXPORTAR`, `CAMBIO_PASSWORD`, `CAMBIO_USUARIO`, `ACCESO_DENEGADO`, `LLAMADA_GEMINI`, `CONSENTIMIENTO_IA`.

**Permisos:** solo administrador o supervisor con `ver_reportes`. Si tu usuario de pruebas no entra, decime y le activo el perfil. Para usuarios normales el endpoint responde 403.

**Probado:** HTTP 200, 386 registros reales en BD, filtros funcionando.

## 3. Campo `codigo_hogar` — **LISTO**

Agregado tanto en `HogarListSerializer` como en `HogarDetalleSerializer`. Ya podés quitar el fallback `id.slice(0,8)` y usar `hogar.codigo_hogar` directo. Es `string`; cuando aún no se ha asignado viene vacío (`""`), no `null`.

> Nota: el modelo lo tiene como CharField, así que siempre llega como string. La generación automática del código (prefijo municipio + año + consecutivo) aún no está implementada — está marcada como TODO en el modelo. Mientras tanto viene vacío. Si querés mostrar algo en la UI cuando esté vacío, podés caer en `id.slice(0,8)` como antes solo cuando `!codigo_hogar`.

## 4. Cosas que quedaron observadas (no urgentes)

- Te dejo planteado para más adelante: la generación del `codigo_hogar` la podemos hacer en `Hogar.save()` cuando el hogar pasa de `BORRADOR` a `ACTIVO`. Si querés un formato específico (más legible para el supervisor), decime cuál y lo armamos.
- El endpoint de auditoría incluye `accion_display` y `resultado_display` con los nombres en español — útil para tu tabla sin necesidad de mapeo en frontend.

## 5. Siguiente paso

Cuando termines la pantalla de auditoría con datos reales, contame cómo te quedó. Si encontrás algún campo que te falte en la respuesta de logs (por ejemplo `user_agent` que dejé fuera para no llenar la grilla), me decís y lo agrego en 5 minutos.

Cualquier cosa me escribís.

Saludos,
Javier Alexander Aguilar Castro
Contrato 2226-2026 — SRNI / Unidad para las Víctimas
