# Estado actual del proyecto — SRNI / Unidad para las Víctimas

**Fecha de corte:** 2026-06-23
**Sprint vigente:** post-Sprint 20 (trabajo continuo en `main`)
**Contratista:** Javier Alexander Aguilar Castro · CC 1.030.547.250
**Contrato:** 2226-2026
**Supervisor UARIV:** Oscar Andrés Manosalva García

> Para el panorama consolidado de arquitectura y stack, ver
> [`INFORME-ARQUITECTURA-ESTADO.md`](INFORME-ARQUITECTURA-ESTADO.md).
> Las secciones 1–8 de abajo conservan el detalle histórico hasta el Sprint 20.

---

## 0. Actualización — Junio 2026 (hitos recientes)

| Frente | Avance |
|---|---|
| **Auditoría APK** (3 oleadas) | 31 hallazgos corregidos: integridad de cola, login, privacidad, progreso con skip-logic, hogar online capturable offline, flujo IA, degradación offline, reconciliación de cola al arranque, **biometría opt-in**. 57 tests verdes. |
| **Instrumento Territorial V7** | Nuevas preguntas (Novedades RUV, años en municipio, IPS), **sub-campos condicionales** (Estrato, "¿cuántos días?") con primer uso de reglas `HABILITAR`, ajustes de texto. Cargado a BD + exportado al bundle móvil. |
| **Marca "Vínculo Colombiano"** | Nombre en login y launcher de la APK + constantes de marca centralizadas (`src/config/marca.ts`). El rediseño del panel web lo lleva Brando. |
| **Base de datos móvil** | Migración v9: tabla `hogares_cache` (captura offline de hogares creados online). |
| **Despliegue** | Backend operando en `30.0.1.109:8090`; **APK builds #15 y #16** compilados (EAS) y publicados al servidor con QR estable (cascada `deploy-apk.sh`). |
| **Documentación** | Informe de arquitectura ([`INFORME-ARQUITECTURA-ESTADO.md`](INFORME-ARQUITECTURA-ESTADO.md)) + informe mensual de junio diligenciado por obligación. |

---

## 1. Resumen ejecutivo

El sistema reemplazo del APK móvil de caracterización SRNI está construido sobre 3 componentes que ya hablan entre sí:

| Componente | Tecnología | Estado | Quién lo construye |
|------------|-----------|--------|--------------------|
| Backend Django REST + JWT | Python 3.14 / Django 5.2 / DRF 3.16 | ✅ Operativo | Javier + Claude |
| App móvil offline-first | React Native / Expo SDK 54 | ✅ Operativa | Javier + Claude |
| Panel web supervisor | React 18 / Vite / Tailwind / Zustand | 🟡 En desarrollo | Brando |

Los 3 componentes corren en local hoy mismo. Backend en `:8001`, panel web en `:5173`, app móvil en Expo Go conectada a la IP de red.

---

## 2. Inventario de datos cargados en BD

| Entidad | Cantidad | Origen |
|---------|---------:|--------|
| Instrumentos UARIV | 8 | Diccionarios oficiales V7/V8 (`docs/perfiles/`) |
| Capítulos | 93 | Diccionarios oficiales |
| Preguntas activas | 995 | Diccionarios oficiales |
| Opciones de respuesta | 2 239 | Diccionarios oficiales + parser Excel UARIV |
| Direcciones Territoriales UARIV | 21 | Estructura organizacional pública UARIV |
| Departamentos DANE | 33 | DIVIPOLA DANE 2023 |
| Municipios DANE | 1 102 | DIVIPOLA DANE 2023 |
| Puntos de atención | 41 | **Placeholder** — falta dataset oficial UARIV |
| Usuarios | 2 | `ALEXJUT`, `ADMIN01` |
| Hogares de prueba | 8 | Pruebas de QA |
| Sesiones de prueba | 15 | Pruebas de QA |

---

## 3. Los 8 instrumentos cargados

| Código | Nombre | Versión | Capítulos | Preguntas |
|--------|--------|---------|----------:|----------:|
| ASISTENCIA | Perfil Asistencial | V8 | 7 | 174 |
| TERRITORIAL | Perfil Territorial | V7 | 14 | 197 |
| BUENAVENTURA | Perfil Buenaventura | V7 | 17 | 151 |
| SAN_ANDRES | Perfil San Andrés | V7 | 14 | 109 |
| TELEFONICO | Perfil Telefónico SAAH | V8 | 7 | 64 |
| URBANO_ETNICO | Perfil Urbano Étnico | V1 | 12 | 85 |
| RURAL_ETNICO | Perfil Rural Étnico | V1 | 14 | 105 |
| VICTIMAS_EXTERIOR | Víctimas en el Exterior | V1 | 8 | 110 |

Todos los instrumentos van empaquetados con la app móvil (~675 KB total en `srni-mobile/assets/instrumentos/`) — el encuestador puede caracterizar sin internet.

---

## 4. Sprints completados (1 al 20)

| Sprint | Tema | Estado |
|--------|------|--------|
| 1-5 | Backend + mobile base + motor offline + IA + UI GOV.CO | ✅ |
| 6-7 | Diccionario V8 + 7 perfiles + flujo víctima habilitada + biometría | ✅ |
| 8-10 | Motor end-to-end + sincronización masiva + reportes producción | ✅ |
| 11 | Hardening seguridad (throttle, AST seguro, CSP, secrets) | ✅ |
| 12-13 | Panel web scaffold + modelo hogar v2 + backend habilitador | ✅ |
| 14 | Mobile flujo cosido (hub de caracterizaciones por hogar) | ✅ |
| 15 | Cargar los 8 instrumentos en BD | ✅ |
| 16 | Fix 3 bugs mobile + 175 opciones nuevas del diccionario UARIV | ✅ |
| 17 | Fix flujo offline + cola robusta | ✅ |
| 18 | Endurecimiento: instrumentos en memoria + migration V4 + redactor PII | ✅ |
| 19 | Ubicación de atención como metadata de sesión (5 fases A-E) | ✅ |
| 20 | Backend habilitador panel web (aliases auth + reportes + fix Usuario) | ✅ |

---

## 5. Componentes técnicos clave

### Backend (`srni-backend/`)
- 8 apps Django: `autenticacion`, `victimas`, `formulario`, `hogares`, `encuestas`, `parametricas`, `ia`, `reportes` + `auditoria` + `sincronizacion`
- JWT con refresh rotativo (access 15 min, refresh 8 h)
- PII cifrado (EncryptedCharField + AES-128) + hash SHA-256 para búsqueda
- LogAcceso inmutable (auditoría Ley 1581)
- Throttle: 5 logins / 15 min · 100 búsquedas RNI / hora
- Endpoints habilitados (Sprint 20): `/api/auth/token/`, `/api/auth/perfil/`, `/api/reportes/encuestador/`, etc.

### Mobile (`srni-mobile/`)
- Expo SDK 54 + Expo Router file-based
- Login con biometría (huella/Face ID)
- 8 instrumentos pre-empaquetados como JSON (in-memory cache)
- Motor offline expo-sqlite + cola de sincronización con backoff exponencial
- Skip logic local (PREDEPENDE / RESHABILITA / RESFINALIZA)
- IA Gemini para asistente de voz batch
- Sprint 19: pantalla `caracterizar/ubicacion-atencion.tsx` con cascada UARIV

### Panel web (`srni-frontend/` — Brando)
- React 18 + Vite + Tailwind + Zustand (sessionStorage, nunca localStorage)
- Login + Dashboard + Hogares + Encuestas + Reportes
- Cliente API con auto-refresh JWT en cola
- Layout institucional GOV.CO con sidebar + topbar

---

## 6. Infraestructura y operación

| Recurso | URL / Configuración |
|---------|---------------------|
| Repo oficial UARIV (Azure DevOps) | `tfsunidad.visualstudio.com/.../IGED MOVIL 2026-04` |
| Repo backup (GitHub) | `github.com/alexjut/srni-unidad-victimas` |
| Ramas vivas | `main` · `frontend` (Brando) · `develop` (histórica) |
| Backend dev | `http://localhost:8001` |
| Panel web dev | `http://localhost:5173` |
| Expo dev | `http://localhost:8082` |
| Producción | Docker Compose con Nginx + TLS pendiente |

---

## 7. Hallazgos abiertos (no bloqueantes)

| # | Hallazgo | Impacto | Estado |
|---|----------|---------|--------|
| 1 | Preguntas tipo PERSONA deberían instanciarse por cada miembro del hogar | Motor formulario actual las trata como si fueran únicas | Pendiente diseño |
| 2 | Una sesión muestra código `ASISTENCIA` cuando debería ser `TERRITORIAL` | Revisar mapeo `instrumento_codigo` en panel web | Por validar |
| 3 | Algunas preguntas no se ven todas en el formulario | QA por instrumento | Pendiente QA |
| 4 | Puntos de atención reales por DT | Hoy hay placeholder de 2 puntos por DT | Pendiente: solicitar a Oscar |
| 5 | Versionado de instrumentos `/api/formulario/versiones/` | Permitiría shippear nuevas versiones del diccionario sin reinstall APK | Pendiente Sprint 21 |
| 6 | `cliente_uuid` para idempotencia de cola | Previene duplicación al reintentar POSTs | Pendiente Sprint 21 |

---

## 8. Cumplimiento normativo

| Norma | Cumplimiento |
|-------|--------------|
| Ley 1581/2012 (Protección de Datos) | PII cifrado, LogAcceso inmutable, ARCO via API |
| CONPES 3995 | Hardening Sprint 11 (CSP, throttle, AST, secrets) |
| Decreto 1377/2013 | Minimización (frontend solo recibe campos necesarios) |
| Resolución MINTIC 1519 | Aplica en negativo: datos víctimas NO son datos abiertos |

---

## 9. Próximos pasos sugeridos

1. **Brando**: hacer pull de `frontend` y probar login + dashboard con `ALEXJUT` / `SrniTest2026!`
2. **Javier**: solicitar a Oscar el dataset oficial de centros regionales UARIV
3. **Equipo**: abordar perfil por perfil para validar las 995 preguntas (hallazgo #3)
4. **Sprint 21 (sugerido)**: implementar preguntas tipo PERSONA por miembro del hogar (hallazgo #1)

---

**Generado:** Sprint 20 cierre — 2026-05-26
