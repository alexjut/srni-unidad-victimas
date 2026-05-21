# Sprint 5 — Integración IA Gemini + UI GOV.CO

**Branch:** `main` (merge `feature/sprint5`)
**Estado:** ✅ Completado
**Inicio:** 2026-04-19
**Cierre:** 2026-04-21
**Commits principales:** `2abf579`, `4bf168a`, `11ee14a`, `082cc13`

---

## Objetivos

1. Integrar el asistente de voz IA (Google Gemini) como proxy seguro en el backend
2. Implementar pantalla de consentimiento obligatorio antes de activar la IA
3. Rediseñar la UI con identidad visual GOV.CO institucional
4. Configurar ngrok con dominios permanentes para pruebas en celular físico

---

## Entregables backend

### App `ia` (nueva)

**Modelos:**
```python
class ConsentimientoIA:
    usuario = ForeignKey(Usuario)
    sesion = ForeignKey(SesionEncuesta)
    acepta = BooleanField()
    firma_sha256 = CharField()  # SHA-256 del payload de consentimiento
    timestamp = DateTimeField(auto_now_add=True)
    # Inmutable: usuario acepta términos de uso de IA Gemini

class SesionIA:
    sesion_encuesta = ForeignKey(SesionEncuesta)
    activa = BooleanField(default=False)
    total_llamadas_gemini = IntegerField(default=0)
```

**Endpoints:**
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/ia/consentimiento/` | Registrar consentimiento (obligatorio) |
| GET | `/api/ia/estado/` | Estado IA de la sesión actual |
| POST | `/api/ia/mapear-audio/` | Proxy: texto → valor campo via Gemini |

**Seguridad del proxy Gemini:**
- `GEMINI_API_KEY` solo en servidor (`python-decouple`) — el cliente nunca la ve
- Valida que existe `ConsentimientoIA` antes de procesar
- Rate limiting: 30 llamadas Gemini / hora por usuario
- Log en `LogAcceso` con acciones `LLAMADA_GEMINI` y `CONSENTIMIENTO_IA`
- Si Gemini falla → devuelve `503` (el encuestador puede continuar manualmente)

**Tests nuevos: 13**
- Auth requerida
- Consentimiento obligatorio antes de mapeo
- Estado de IA por sesión
- Mapeo exitoso y fallo de Gemini (503)

---

## Entregables mobile

### Cliente API (`src/api/ia.ts`)
```typescript
registrarConsentimiento(sesionId, acepta): Promise<void>
obtenerEstado(sesionId): Promise<EstadoIA>
mapearAudio(sesionId, preguntaId, texto): Promise<SugerenciaIA>
```

### Store Zustand (`src/stores/iaStore.ts`)
Estados: `inactivo` → `grabando` → `procesando` → `sugerida` | `error`

Transiciones:
- `inactivo` + botón mic → `grabando`
- `grabando` + detener → `procesando` (llama al backend)
- `procesando` + respuesta → `sugerida` (muestra card)
- `sugerida` + aceptar/rechazar → `inactivo`
- cualquier estado + error → `error`

### Componentes nuevos

**`AudioRecorder.tsx`**
- Botón micrófono con animación pulsante mientras graba
- Usa `expo-av` para grabación de audio
- Transcribe localmente y envía texto (no audio raw) al backend

**`SugerenciaIA.tsx`**
- Card con la respuesta sugerida por Gemini
- Barra de confianza (0–100%)
- Botones Aceptar / Rechazar
- Al aceptar: rellena el campo del formulario automáticamente

### Pantalla de consentimiento

**`formulario/consentimiento-ia.tsx`**
- Aviso legal completo (Ley 1581/2012 + términos Gemini)
- Checkbox de aceptación (obligatorio)
- Se muestra una sola vez por sesión de encuesta
- Sin consentimiento: el botón mic no aparece en el formulario

### Integración en formulario

**`formulario/[temaId].tsx` actualizado:**
- `AudioRecorder` aparece junto a cada pregunta de tipo `TEXTO` y `TEXTO_LARGO`
- `SugerenciaIA` se superpone al campo cuando hay sugerencia activa
- El encuestador siempre puede ignorar la sugerencia y escribir manualmente

### UI GOV.CO institucional

**`GovHeader` (componente nuevo):**
- Franja superior azul oscuro `#003366` con logo Colombia
- Texto "GOV.CO" en la esquina superior derecha
- Presente en todas las pantallas principales

**Paleta de colores actualizada:**
| Token | Hex | Uso |
|-------|-----|-----|
| `primary` | `#003366` | Encabezados, botones primarios |
| `secondary` | `#F2A900` | Acentos, iconos de alerta |
| `surface` | `#FFFFFF` | Fondo de cards |
| `background` | `#F5F5F5` | Fondo general |

**Barra de tabs rediseñada:**
- Íconos actualizados con Material Symbols
- Labels en español: Inicio, Búsqueda, Hogares, Encuestas
- Rutas ocultas (formulario, sesión) no aparecen en tabs

---

## Configuración de desarrollo

**ngrok con dominios permanentes** (`README-TUNEL.md`):
- Backend: `https://srniapk-dev.ngrok.app → localhost:8001`
- Mobile: `https://srniapk.ngrok.app → localhost:8082`
- Permite probar en celular físico sin cambiar la URL en el código

---

## Tests: 25 nuevos (13 backend + 12 mobile)

| Módulo | Tests |
|--------|-------|
| `iaApi` (mobile) | 3 |
| `iaStore` transiciones de estado | 9 |
| Backend auth/consentimiento/estado/mapeo | 13 |

---

## Fixes incluidos

| Fix | Commit | Descripción |
|-----|--------|-------------|
| Render Error Expo Router | `0624d94` | `<Redirect />` en lugar de `router.push()` antes del mount |
| Stack mount race condition | `530b5dd` | Guard `isMounted` antes de navegar |
| Barra de tabs íconos | `11ee14a` | Íconos y labels correctos, rutas ocultas |

---

## Decisiones técnicas

**Por qué proxy Gemini en el backend:** El cliente nunca debe tener la API Key de Gemini. Además, el proxy permite auditoría completa (`LogAcceso`), rate limiting por usuario y cumplimiento de la Ley 1581 (el audio no sale de Colombia sin el consentimiento registrado).

**Por qué firma SHA-256 en el consentimiento:** Crea evidencia técnica inmutable de que el usuario aceptó los términos en un momento específico. No es repudiable.
