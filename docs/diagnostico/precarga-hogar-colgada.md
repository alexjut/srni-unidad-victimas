# Diagnóstico — Precarga/carga de hogar se queda colgada (>50 s, nunca termina)

**Fecha:** 2026-07-03
**Reporte origen:** video funcional (Alejandro) — al abrir un hogar/caracterización la pantalla queda en "Cargando…" con barra que avanza 20→50→75→90 % y nunca renderiza los integrantes.
**Estado:** diagnóstico (sin desplegar). Fix propuesto de bajo riesgo pendiente de gate de Pruebas.
**Build confirmado (2026-07-03):** el usuario confirma que es **la última publicada** = APK perfil **`preview`** de `srni-mobile` (nuestro código), con backend vía **túnel ngrok** (`EXPO_PUBLIC_API_URL=https://prod-caracterizacion.ngrok.app`). El perfil `production` de `eas.json` aún tiene la URL en placeholder (`CAMBIAR-URL-PRODUCCION...`), así que "producción" en la práctica es ese APK preview.

---

## TL;DR (causa raíz)

**Aclaración de la descripción del video:** la "barra que avanza 20→50→75→90 %" **no corresponde a ninguna barra determinada del código** — ni actual ni en el historial git. La pantalla de carga real es un **spinner indeterminado** (`ActivityIndicator`) con título "Cargando…". El tester describe ese spinner (que gira sin fin) como "una barrita casi llena pero pegada". No es otra app ni un build viejo: **es nuestro APK preview**. El síntoma real es *"la carga nunca termina al abrir el hogar/caracterización, sin mensaje de error"*.

**Causa raíz (código + entorno):** una petición de red durante la carga **se cuelga sin resolver ni rechazar**, y la pantalla queda gated en el spinner para siempre. Dos factores se combinan:

1. **`src/api/client.ts` — refresh de token con `axios.post` crudo SIN `timeout`.** Si una petición recibe **401** y el POST de refresh se cuelga, la promesa nunca settlea → el `finally`/`setCargando(false)` nunca corre → **spinner infinito, sin error** (el `errorReporter` es fire-and-forget). Es el único camino que produce "cuelgue infinito + sin error".

2. **Agravante de entorno: el backend de pruebas va por un túnel ngrok** (lento e inestable). Un tunel ngrok saturado/caído a medias es el disparador ideal de peticiones que quedan colgadas o devuelven 401 con refresh que no termina. Explica por qué se ve en campo/funcional y no en local.

---

## 1. Ubicación del loader

No hay un componente "Precarga de hogar" con barra por etapas. Las pantallas del flujo y su loader:

| Pantalla | Archivo | Gate de carga | Tipo de loader |
|---|---|---|---|
| Detalle de hogar | `app/(main)/hogares/[hogarId]/index.tsx` | `hogaresApi.detalle()` en `useEffect` con `.finally(setCargando(false))` | `ActivityIndicator` (spinner) |
| Hub caracterizaciones | `app/(main)/hogares/[hogarId]/caracterizaciones.tsx` | `hogaresApi.detalle()` | spinner |
| Lista de capítulos | `app/(main)/formulario/index.tsx` | `cargarTodo()` con `try/finally` | spinner; las `ProgressBar` son **contenido** (progreso por capítulo), no carga |
| Captura por persona (lista integrantes) | `app/(main)/formulario/[temaId].tsx` | 1er `useEffect` (línea 299) | spinner (`title="Cargando…"`, línea 973-981) |

La `ProgressBar` de `formulario/index.tsx` (líneas 174, 713) refleja el **% de respuestas del capítulo/instrumento**, y solo se pinta **después** de que `cargando=false`. Es lo más parecido a "barra que avanza" del repo, pero:
- Solo aparece cuando ya cargó (no durante la espera).
- Su valor viene de `respondidas/obligatorias`, no de pasos 20/50/75/90.

**Conclusión:** la barra escalonada del video no mapea a ninguna pantalla actual. Es señal fuerte de **APK desactualizado**.

---

## 2. Cadena de llamadas durante la carga y dónde puede colgarse

### 2.1 Detalle de hogar (`[hogarId]/index.tsx`)
```
useEffect → hogaresApi.detalle(hogarId)
  .then(setHogar).catch(setError).finally(setCargando(false))
```
- Petición única, con `try/catch/finally`. En error normal (timeout 15 s del `apiClient`) → muestra mensaje y corta. **No** se cuelga por sí sola.
- **Salvo** que `detalle` reciba 401 → entre al refresh sin timeout (ver §3) → la promesa nunca settlea → `finally` nunca corre → spinner infinito.

### 2.2 Captura por persona (`[temaId].tsx`, 1er useEffect)
```
(async () => {
  ... lee bundle (memoria, instantáneo) ...
  if (sesionServerId) {
     encuestasApi.detalle(...)              // red
     ... crearBorrador / vincularSesion ...
     if (estaOnline) encuestasApi.getRespuestas(sesionServerId)   // red  ← await que puede colgarse
  }
  setCargando(false)          // ← solo corre si NINGÚN await previo se cuelga
})().catch(() => setCargando(false))
```
- **No hay `finally`**: `setCargando(false)` está al final del `try` implícito. El `.catch` **solo cubre rechazos**, **no cuelgues**. Si `getRespuestas` (u otra red) queda pendiente para siempre (401→refresh sin timeout), **el spinner queda infinito**.
- El `useEffect` de miembros (línea 407) es independiente y **no** bloquea `cargando`; degrada bien a `[]`.

### 2.3 Progreso "20/50/75/90"
No existe en código. No hay animación por pasos acoplada ni desacoplada. → refuerza hipótesis de build viejo o descripción del reporter sobre un spinner/indeterminado.

---

## 3. Causa raíz de código: refresh de token sin timeout

`src/api/client.ts` — interceptor de respuesta 401:

```ts
export const apiClient = axios.create({ baseURL: BASE_URL, timeout: 15000, ... });
...
// al recibir 401:
const { data } = await axios.post(                    // ← axios CRUDO, no apiClient
  `${BASE_URL}/api/auth/refresh/`,
  { refresh },
  { headers: { 'ngrok-skip-browser-warning': 'true' } },   // ← SIN timeout
);
```

Problemas:
1. **Sin `timeout`**: el default de axios es `0` (infinito). Si el endpoint de refresh se cuelga (red parcial: el server responde 401 rápido pero el POST de refresh queda en el limbo, típico en campo con conectividad intermitente o proxy openresty a medio camino), la promesa **nunca settlea**.
2. **Efecto dominó**: mientras `isRefreshing`, todas las peticiones 401 se encolan en `refreshQueue`. Si el refresh nunca resuelve ni rechaza, **todas quedan colgadas** — no solo la de la pantalla actual.
3. **Silencioso**: el `errorReporter` es fire-and-forget (`.then().catch(()=>{})`), así que ni siquiera se emite un error visible. Encaja con "no hay mensaje de error en pantalla".

Este es el **único camino** que explica "carga infinita + sin error". Cualquier petición vía `apiClient` **sin** 401 rechaza a los 15 s y la pantalla muestra su estado de error/offline.

---

## 4. Offline-first: ¿está yendo a red antes que a SQLite?

Parcial, y relevante:
- `cargarMiembrosHogar` (`src/services/miembrosHogar.ts`) intenta **red primero** (`hogaresApi.detalle`) y solo cae a SQLite/caché en el `catch`. Si esa petición se cuelga (401→refresh), el `catch` nunca corre → no llega al fallback offline. (No bloquea `cargando`, pero sí deja la lista de integrantes vacía indefinidamente.)
- El detalle de hogar y el hub **exigen** `GET /hogares/{id}/` (no tienen ruta offline para id de servidor sin caché previa). Con red colgada, no hay plan B.

---

## 5. Fix propuesto (bajo riesgo, pendiente de Pruebas)

**Prioritario — cerrar el cuelgue infinito (systemic):**
1. Añadir `timeout` explícito al `axios.post` del refresh en `client.ts` (p. ej. `timeout: 15000`), para que un refresh colgado **rechace** en vez de colgar. Al rechazar, `rejectQueue()` ya libera la cola encolada (esa lógica ya existe) → las pantallas caen a su `catch`/`finally` y muestran error/offline.

**Defensa en profundidad (opcional, mismo PR o siguiente):**
2. En `[temaId].tsx`, envolver el 1er `useEffect` en `try/finally` (mover `setCargando(false)` al `finally`) para que ningún camino deje el spinner colgado, aun si aparece otro await sin timeout.
3. En cargas gated por red (detalle de hogar / hub / captura), considerar un **watchdog** de UI (p. ej. si a los ~20 s sigue `cargando`, mostrar botón "Reintentar / Trabajar sin conexión") para no dejar nunca al encuestador en un spinner mudo.

Estos cambios son locales y no tocan el esquema ni la reconciliación de UUID.

**Infraestructura (fuera de código, pero causa del entorno):**
4. Sacar el APK de pruebas del **túnel ngrok**: apuntarlo a una URL estable (el vhost `caracterizacion.unidadvictimas.gov.co` en 30.0.1.109 ya está provisionado — ver anexo). Mientras el backend viva en ngrok, los cuelgues/lentitud seguirán apareciendo aunque el timeout del refresh los convierta en error manejable en vez de spinner infinito.
5. `eas.json` perfil `production` sigue con `EXPO_PUBLIC_API_URL` en placeholder (`CAMBIAR-URL-PRODUCCION.unidadvictimas.gov.co`) — definir la URL real antes de un build de producción de verdad.

---

## 6. Información adicional (para confirmar el camino exacto)

Build ya confirmado (APK preview / ngrok). Falta solo evidencia del camino:

1. **Logs del dispositivo** en el momento del cuelgue: ¿sale `HTTP 401 ... /api/hogares/...` (o `/api/encuestas/`) seguido de silencio? ¿aparece el warn de `getRespuestas`/`encuestasApi.detalle`? Eso confirma el camino refresh-sin-timeout. Si en cambio se ve el 301/HTML de ngrok, el disparador es el interstitial del túnel.
2. **Reproducir en Expo** con red degradada (throttling, o apuntar al ngrok y cortar/saturar el túnel a mitad de carga) para forzar el 401+refresh colgado y validar el fix del timeout.
3. **Estado del túnel ngrok** en el momento del reporte: si estaba caído/saturado, es coherente con el cuelgue masivo.

---

## Anexo — Estado del dominio `caracterizacion.unidadvictimas.gov.co`

Consultado el 2026-07-03 desde la red UARIV/VPN:

| Check | Resultado |
|---|---|
| DNS interno (LISA.uariv.local) | **A → 30.0.1.109** (servidor de despliegue) |
| DNS público (8.8.8.8 / 1.1.1.1) | **Sin registro A** — solo devuelve SOA de la zona padre. **No resuelve en internet.** |
| Zona padre `unidadvictimas.gov.co` | Hospedada en **Azure DNS** (ns1-06.azure-dns.com / .net / .org / .info) |
| HTTP :80 al vhost (Host header) | **301 → https://caracterizacion.unidadvictimas.gov.co/** (Server: **openresty**) |
| HTTPS :443 | Timeout desde este segmento (no verificable aquí — falta exponer/validar 443 + certificado) |
| :8090 (stack cz_*) | Timeout desde este segmento (firewall/segmentación) |

**Conclusión del dominio:**
- **NO está "libre":** ya está **provisionado internamente** — el DNS interno lo apunta a 30.0.1.109 y **openresty ya tiene un server block** para ese hostname que fuerza HTTPS. Alguien lo dejó preparado para este proyecto.
- **NO es público todavía:** falta que **OTI publique el registro A/CNAME en la zona Azure DNS** (`unidadvictimas.gov.co`) para acceso externo.
- **Pendiente por confirmar con OTI:** exposición del **:443** y el **certificado TLS** del vhost (no respondió desde la VPN; hay que validar que sirva la app, no solo el redirect de :80).

Acción sugerida: solicitar a OTI (1) publicación del A record público hacia la IP/entrada correspondiente y (2) confirmación de cert TLS + 443 activo para el vhost.
