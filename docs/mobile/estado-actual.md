# Frontend — App Móvil SRNI

**Tecnología:** React Native + Expo SDK 54  
**Enrutamiento:** Expo Router (file-based routing)  
**Estado:** En desarrollo activo  
**Última actualización:** 2026-04-28

---

## Qué ES el frontend actual

El frontend del SRNI es la **app móvil React Native**, no una SPA Angular.
La ARQUITECTURA.md menciona Angular 17 como plan a futuro (Fase 2 — web).
Lo que existe y funciona hoy es `srni-mobile/`.

No existe aún:
- Frontend web Angular
- PWA offline-first
- Dashboard web de supervisores

---

## Pantallas implementadas

```
srni-mobile/app/
├── _layout.tsx                       ← Root layout + PaperProvider + auth guard
├── index.tsx                         ← Redirect según sesión
├── (auth)/
│   ├── _layout.tsx
│   └── login.tsx                     ✅ Login JWT con UI GOV.CO
└── (main)/
    ├── _layout.tsx                   ✅ Bottom tabs (Dashboard, Búsqueda, Hogares, Encuestas)
    ├── index.tsx                     ✅ Dashboard con resumen del encuestador
    ├── busqueda.tsx                  ✅ Búsqueda RNI (server-side, sin PII en cliente)
    ├── hogares/
    │   ├── index.tsx                 ✅ Lista de hogares asignados
    │   ├── nuevo.tsx                 ✅ Crear nuevo hogar
    │   └── [hogarId].tsx            ✅ Detalle/edición de hogar
    ├── formulario/
    │   ├── index.tsx                 ✅ Lista de 54 temas del instrumento
    │   ├── [temaId].tsx             ✅ Motor de preguntas + skip logic
    │   └── consentimiento-ia.tsx    ✅ Consentimiento para asistente IA
    └── encuestas/
        ├── index.tsx                 ✅ Lista de sesiones de encuesta
        └── [sesionId].tsx           ✅ Detalle de sesión
```

---

## Stack técnico

| Componente | Tecnología |
|-----------|-----------|
| Framework | React Native + Expo SDK 54 |
| Routing | Expo Router (file-based) |
| UI | React Native Paper (estilo GOV.CO) |
| Estado global | Zustand (`authStore`) |
| HTTP | Axios + interceptores JWT |
| Almacenamiento local | expo-sqlite (schema offline) |
| IA asistente | Proxy Gemini vía backend Django |

---

## Seguridad implementada

- Tokens JWT en memoria (Zustand) — nunca en AsyncStorage persistente
- `sessionStorage.clear()` equivalente en logout → limpia Zustand + expo-sqlite
- Búsqueda RNI solo server-side, el cliente recibe resúmenes paginados
- Sin datos PII almacenados localmente en SQLite
- Interceptor Axios que añade `Authorization: Bearer` en cada request

---

## Pendientes de la app móvil

| Pendiente | Sprint | Prioridad |
|-----------|--------|-----------|
| Motor de formularios: skip logic completo | Sprint 7 | Alta |
| Sincronización offline → backend | Sprint 7 | Alta |
| Pantalla de perfil del encuestador | Sprint 7 | Media |
| Push notifications para asignaciones | Sprint 8 | Baja |
| Firma digital del encuestador al cerrar encuesta | Sprint 8 | Media |

---

## Cómo levantar el frontend

```bash
cd srni-mobile
npm install
npx expo start --tunnel   # usar tunnel para celular físico
# o
npx expo start            # para emulador
```

Puerto: `8081`

Para conectar al backend en desarrollo usar ngrok (ver README-TUNEL.md).
