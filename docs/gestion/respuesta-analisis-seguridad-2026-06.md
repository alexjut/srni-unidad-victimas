# Respuesta al Análisis de Seguridad y Calidad — APK Encuesta IGED Móvil

**Proyecto:** PRY-0662064 — Modernización entrevista de caracterización (APK)
**Informe de origen:** Análisis de seguridad y calidad — 18/06/2026
**Fecha de respuesta:** 19/06/2026

Se realizó el triage de los hallazgos (real vs. falso positivo) y se aplicaron las
correcciones de bajo riesgo. A continuación, la respuesta hallazgo por hallazgo.

| # | Hallazgo | Estado | Acción / Justificación |
|---|---|---|---|
| 1.1 | Vulnerabilidades en dependencias | **Corregido (parcial) + planificado** | Ver detalle abajo |
| 1.2 | Generic Object Injection Sink | **Falso positivo / riesgo bajo** | Ver detalle |
| 1.3 | Variable Assigned to Object Injection | **Riesgo bajo** | Ver detalle |
| 1.4 | Manejo incorrecto de errores asíncronos | **Falso positivo** | El código citado ya maneja la excepción |
| 1.5 | Binding a todas las interfaces (0.0.0.0) | **Por diseño / aceptado** | Ver detalle |
| 1.6 | Open Redirect (react-router) | **Mitigado** | Actualización de dependencias + rutas same-origin |
| 1.7 | Gestión insegura de credenciales | **Falso positivo** | El match es un *mock* de pruebas |

---

## 1.1 Vulnerabilidades en dependencias

- **Backend (requirements.txt):** `Django` actualizado de `5.2` a **`5.2.15`** (parches de
  seguridad de la línea LTS). Verificado: `manage.py check` sin issues y **119 pruebas OK**.
- **Frontend (package-lock.json):** se aplicó `npm audit fix` (sin `--force`, solo
  correcciones no disruptivas); **build de producción verificado**. Se eliminó un
  **`pnpm-lock.yaml` huérfano** que el escáner leía y reportaba vulnerabilidades de
  dependencias que **no están instaladas** (el proyecto usa npm).
- **Pendiente con justificación (cambios mayores, se aplican con prueba dedicada):**
  - `vite`/`esbuild`: la vulnerabilidad afecta **únicamente al servidor de desarrollo**
    (`GHSA-67mh-4wv8-2f99`), **no al sitio estático compilado** que se despliega → **no
    explotable en producción**.
  - `react-simple-maps`: el fix es un *breaking change* que puede romper el mapa de
    supervisión; se actualizará con pruebas.
- **Mobile:** las dependencias reportadas son en su mayoría del *toolchain* de
  Expo/React Native (*build-time*), no del binario instalado; se actualizan con
  `expo install --fix` y pruebas, para no romper la compatibilidad nativa.
- **Proceso continuo:** se incorpora la revisión de `npm audit` / dependencias al ciclo.

## 1.2 / 1.3 Object Injection

- En `app/(auth)/login.tsx` el patrón señalado es `kbAnims[idx]`, donde `idx` es un
  **índice numérico interno** del carrusel (0..N), **no una entrada del usuario** →
  **falso positivo**.
- En `app/(main)/formulario/[temaId].tsx` las claves dinámicas provienen del
  **instrumento** (`codigo_externo`, `id` de pregunta) y de IDs internos, **no de texto
  libre manipulable por el usuario** → riesgo bajo. Como endurecimiento se puede migrar
  a `Map` o validar contra lista blanca de códigos del instrumento.
- No existe ruta donde el usuario construya claves arbitrarias que lleguen a `Object.prototype`.

## 1.4 Manejo de errores asíncronos

El ejemplo citado (`estaOnline()`) **ya está dentro de un `try/catch`** que captura la
excepción y degrada a `false`. Es el comportamiento correcto (no propaga). **Falso
positivo.** Aun así, se revisó el flujo crítico para asegurar manejo de errores.

## 1.5 Binding a todas las interfaces (0.0.0.0)

El backend corre con **gunicorn dentro de un contenedor Docker**, **detrás de nginx**;
no expone gunicorn directamente al host/red. El valor `'0.0.0.0'` en `LogAcceso.ip_origen`
es un **valor por defecto de un campo IP** (no un binding de servicio). **Aceptado por
diseño**; la segmentación la provee la red interna del stack.

## 1.6 Open Redirect (react-router)

La SPA usa `react-router-dom` con navegación **same-origin** (rutas internas); no se
construyen redirecciones hacia destinos externos a partir de entrada del usuario. Se
mitiga adicionalmente con la actualización de dependencias.

## 1.7 Gestión insegura de credenciales

El hallazgo apunta a `src/__mocks__/expo-secure-store.ts`, que es un **mock para pruebas
unitarias**, no código de producción ni secretos reales. La aplicación almacena tokens
en **`expo-secure-store`** (Keychain/Keystore del sistema operativo, cifrado). **No hay
secretos hardcodeados** en el código de producción.

---

## Resumen

- **Corregido:** Django 5.2.15, `npm audit fix` (frontend), eliminación de lockfile huérfano.
- **Falsos positivos:** 1.2 (login), 1.4 (async), 1.5 (0.0.0.0), 1.7 (mock).
- **Riesgo bajo / endurecimiento opcional:** 1.2/1.3 (object injection sobre claves no manipulables).
- **Planificado con prueba:** vite/esbuild (solo dev), react-simple-maps, dependencias mobile.
