# Auditoría pre-publicación en tiendas — 2026-06-10

Auditoría integral (4 agentes en paralelo + verificación manual de cada hallazgo)
sobre mobile, backend y frontend web, con miras a publicar la app en Google Play
Store y Apple App Store. Todos los hallazgos confirmados fueron corregidos en
esta misma fecha; los descartados se documentan para no re-investigarlos.

## Resumen ejecutivo

| Área | Estado previo | Estado posterior |
|---|---|---|
| Mobile (Expo) | 3 bugs de robustez confirmados, sin config de tiendas, 45 errores TS, 35 tests rotos | 0 errores tsc, 41/41 tests, eas.json + versioning listos |
| Backend (Django) | Endpoint debug expuesto, riesgo de fuga de API key, carrera en hogar idempotente | Corregido, 112/112 tests |
| Frontend web (Brando) | 8.5/10 — sin bugs críticos | Sin cambios (dominio de Brando); pendientes menores listados abajo |

## Corregido — Mobile

1. **Cola de sincronización bloqueable por item corrupto** (`src/services/sincronizacion.ts`).
   Un `SyntaxError` de `JSON.parse` (payload corrupto) caía en la rama
   `status === undefined` → se marcaba "Sin conexión" y `sinRed = true` →
   **un solo item corrupto detenía la cola entera para siempre**. Ahora el
   error de red real se detecta con `err.isAxiosError || err.request`; los
   errores locales marcan solo su item y la cola continúa.

2. **`persistirRespuesta` referenciada antes de declararse** (`app/(main)/formulario/[temaId].tsx`).
   El `useEffect` de desmontaje la incluía en sus deps 2 líneas antes del
   `const` (TDZ / undefined según transpile → el cleanup podía re-ejecutarse
   en cada render). Reordenado.

3. **Bulk online sin fallback** (`guardarYVolver`). Si `responderBulk` fallaba
   (500/timeout) el catch silencioso no encolaba nada — las respuestas quedaban
   solo en SQLite sin reintento. Ahora el fallo online cae al encolado offline.

4. **Creación offline de hogar con campo errado** (`app/(main)/hogares/nuevo.tsx`).
   Se pasaba `autorizado_uuid` a un DAO que espera `jefe_hogar_uuid` → el INSERT
   local iba con `undefined`. Mapeado explícitamente.

5. **8 estilos con `color` pisado por spread** (`{ color: X, ...FONT.label }` —
   FONT.* también trae `color` y sobrescribía el intencional). Spread primero.

6. **`FONT.subtitle` inexistente** en `conformar.tsx` → `FONT.h3`.

7. **Suite de tests resucitada**: `skipLogic.test.ts` probaba una API eliminada
   (`evaluarOperador`) — reescrita para `calcularVisibles` (HABILITAR /
   DESHABILITAR / OBLIGAR / FINALIZAR, triggers multivalor, null-safety).
   2 asserts de `sincronizacion.test.ts` actualizados (`ruta_entrevista`,
   `miembro_id`). Resultado: 41/41.

8. **`@expo/vector-icons` declarada como dependencia directa** (antes solo
   transitiva — tsc no la resolvía).

## Corregido — Configuración de tiendas

- **`eas.json` creado**: perfiles development / preview (APK interno) /
  production (AAB + autoIncrement). ⚠️ **Pendiente Javier**: reemplazar las
  URLs `CAMBIAR-URL-*` por las reales de staging/producción cuando existan.
- **`app.json`**: `android.versionCode: 1` + `ios.buildNumber: "1"`.
- **`client.ts`**: el fallback `http://localhost:8001` ahora solo aplica en
  `__DEV__`; un build de producción sin `EXPO_PUBLIC_API_URL` falla al arrancar
  con mensaje claro (antes intentaba conectarse a localhost silenciosamente).
- **`errorReporter.ts`**: no-op en producción (su endpoint solo existe en dev).

## Corregido — Backend

1. **`/api/_debug/log/` (AllowAny) solo se registra con `DEBUG=True`** — en
   producción esa superficie no existe (`srni/urls.py`).
2. **Fuga potencial de `GEMINI_API_KEY`** (`apps/ia/services.py`): la librería
   de Google puede incluir `?key=...` en mensajes de error que iban a logs
   (`exc_info=True`) y al mensaje de `GeminiError`. Ahora se redacta con
   `_sin_credenciales()` y sin traceback.
3. **Carrera en hogar idempotente** (`apps/hogares/`): la validación
   "1 víctima → 1 hogar no archivado" era solo de vista (filter + create sin
   lock) — dos reintentos simultáneos del móvil podían crear duplicados.
   Nuevo constraint condicional en BD (`uniq_hogar_no_archivado_por_autorizado`,
   migración 0005) + `IntegrityError` → devuelve el hogar ganador (mismo
   contrato 200). 7 fixtures de tests corregidas (creaban N hogares por víctima,
   violando la regla que el constraint ahora hace cumplir).

## Hallazgos DESCARTADOS (verificados como falsos — no re-investigar)

- "Mojibake en `app.json` (faceIDPermission)": el archivo es UTF-8 correcto;
  era PowerShell 5.1 leyendo UTF-8 como ANSI en consola.
- "skipLogic crashea con `valor_trigger` null": hay guard en `_reglaActiva`
  (línea `if (!regla.valor_trigger)`). Test añadido que lo cubre.
- "`(r as any).miembro ?? null` rompe claves": `?? null` ya normaliza undefined.
- "`estaOnline` siempre truthy en formulario": viene del `useSyncStore`
  (booleano de estado), no es la función importada.
- "JSON.parse sin try-catch deja items en 'enviando'": sí estaban cubiertos por
  el try del orquestador (el bug real era la clasificación del error, ver #1).

## Pendientes para publicar (no son de código)

1. **URL de producción del backend** (HTTPS) — actualizar `eas.json`.
2. **Política de privacidad publicada** (URL pública UARIV) — requisito de
   ambas tiendas; debe declarar: respuestas de encuesta, municipio, datos de
   vivienda, envío de transcripciones a Gemini vía backend.
3. **Data Safety form** (Play Console) y **App Privacy** (App Store Connect).
4. **Cuentas**: Google Play Console (org gubernamental) y Apple Developer.
5. **Firmas**: keystore Android y certificados iOS (EAS los gestiona).
6. Infra producción backend: `ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS` con valores
   reales, registrar dominio en HSTS preload, CSP en Nginx.
7. Evaluar cifrado de la SQLite local (hoy sin PII directa — solo UUIDs opacos
   y respuestas; clasificar con Oscar si las respuestas exigen SQLCipher).

## Pendientes del frontend web (dominio de Brando)

- `parametricas.ts:55` llama `/api/parametricas/municipios/todos/` que no
  existe en el backend (verificar uso o remover).
- Los comentarios "endpoint auditoría pendiente" y "codigo_hogar pendiente"
  ya están resueltos en backend (commit `5c1f25d`) — actualizar la rama
  `frontend` y quitar las notas.
- Duplicación de `DatoItem`/`InfoCard`/`BarraProgreso` → extraer a `ui/`.
