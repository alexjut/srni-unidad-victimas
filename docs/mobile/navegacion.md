# Navegación — App Móvil SRNI

**Framework:** Expo Router (file-based routing)
**Última actualización:** 2026-04-28

---

## Estructura de rutas

```
app/
├── _layout.tsx                    Root layout (PaperProvider + auth guard global)
├── index.tsx                      Redirect: si autenticado → /(main), si no → /(auth)/login
│
├── (auth)/
│   ├── _layout.tsx                Stack sin header (pantallas de sesión)
│   └── login.tsx                  ✅ Login JWT + UI GOV.CO
│
└── (main)/
    ├── _layout.tsx                Bottom tabs (Dashboard, Búsqueda, Hogares, Encuestas)
    ├── index.tsx                  ✅ Dashboard con resumen del encuestador
    │
    ├── busqueda.tsx               ✅ Búsqueda RNI server-side
    │
    ├── hogares/
    │   ├── index.tsx              ✅ Lista de hogares (pull-to-refresh, filtros)
    │   ├── nuevo.tsx              ✅ Crear nuevo hogar
    │   └── [hogarId].tsx         ✅ Detalle/edición de hogar + miembros
    │
    ├── encuestas/
    │   ├── index.tsx              ✅ Lista de sesiones con barra de progreso
    │   └── [sesionId].tsx        ✅ Detalle de sesión + finalizar
    │
    └── formulario/
        ├── index.tsx              ✅ Lista de capítulos del instrumento
        ├── [temaId].tsx          ✅ Motor de preguntas + skip logic + IA
        └── consentimiento-ia.tsx ✅ Consentimiento antes de activar IA Gemini
```

---

## Tabs del menú principal

| Tab | Ruta | Ícono | Descripción |
|-----|------|-------|-------------|
| Inicio | `/(main)/` | `home` | Dashboard del encuestador |
| Búsqueda | `/(main)/busqueda` | `search` | Buscar víctimas en el RNI |
| Hogares | `/(main)/hogares/` | `home-group` | Hogares asignados |
| Encuestas | `/(main)/encuestas/` | `clipboard-list` | Sesiones de encuesta |

**Rutas ocultas de los tabs** (accesibles por navegación programática):
- `/(main)/hogares/nuevo`
- `/(main)/hogares/[hogarId]`
- `/(main)/encuestas/[sesionId]`
- `/(main)/formulario/*`

---

## Flujo de navegación principal

```
Login exitoso
     ↓
  Dashboard  ←──────────────────────────────┐
     │                                       │
     ├── Búsqueda → detalle víctima          │
     │                                       │
     ├── Hogares → [hogarId]                 │
     │               │                       │
     │               └── Iniciar encuesta    │
     │                        ↓              │
     │               Formulario → [temaId]   │
     │                        ↓              │
     │               Encuesta finalizada ────┘
     │
     └── Encuestas → [sesionId] → Finalizar
```

---

## Auth guard

`app/_layout.tsx` comprueba `authStore.token` antes de renderizar cualquier ruta `(main)`:

```typescript
// Si no hay token → redirige a login sin mostrar pantalla protegida
const token = useAuthStore(s => s.token)
if (!token) return <Redirect href="/(auth)/login" />
```

Al hacer logout:
1. `authStore.clearSession()` — limpia token y datos de usuario
2. `syncStore.reset()` — limpia estado de sincronización
3. Expo Router detecta `token = null` y redirige a login

---

## Navegación en el formulario

`/(main)/formulario/index.tsx` muestra la lista de capítulos del instrumento activo.

Al seleccionar un capítulo:
```
router.push(`/(main)/formulario/${tema.id}`)
```

`/(main)/formulario/[temaId].tsx` recibe el ID y carga las preguntas del capítulo. Incluye:
- Miga de pan: `Formulario > {nombre_capitulo}`
- Botón "Capítulo anterior" / "Capítulo siguiente"
- Integración de `AudioRecorder` + `SugerenciaIA` por pregunta

---

## Parámetros de ruta

| Ruta | Param | Tipo | Ejemplo |
|------|-------|------|---------|
| `hogares/[hogarId]` | `hogarId` | UUID string | `a1b2c3d4-...` |
| `encuestas/[sesionId]` | `sesionId` | UUID string | `e5f6g7h8-...` |
| `formulario/[temaId]` | `temaId` | UUID string | `i9j0k1l2-...` |

Acceso en componente:
```typescript
const { hogarId } = useLocalSearchParams<{ hogarId: string }>()
```
