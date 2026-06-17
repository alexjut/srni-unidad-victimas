# Cifrado en reposo del SQLite offline (SRNI mobile)

Estado: **APLAZADO** (documentado, no implementado) — con mitigaciones ligeras ya aplicadas.
Contexto: Fase A del modo offline (conformación de hogar + sesión 100% sin red).

## El problema

Con la Fase A, el dispositivo persiste en SQLite (`srni_offline.db`) datos que SÍ
contienen PII mientras la cola de sincronización está pendiente:

- `victimas_offline.payload_json` → `VictimaResumenFuente` completo (nombre, documento).
- `miembros_offline.payload_json` → nombre completo / documento del integrante.
- `jornada.json` (Fase 0) → `VictimaResumenFuente` de las personas de la jornada.
- `cola_sincronizacion.payload` → copia de los mismos datos hasta sincronizar.

El resto del esquema solo guarda UUIDs opacos y datos de vivienda/respuestas. La PII
es **transitoria**: existe entre el momento de captura offline y la sincronización,
tras la cual `limpiarEnviados()` / `marcarSincronizado` la dejan obsoleta (aunque el
`payload_json` permanece como histórico hasta que se limpie la tabla).

## ¿Se puede cifrar limpio con este stack? (Expo SDK 54, expo-sqlite ~16)

**No de forma limpia.** `expo-sqlite` 16 NO incluye SQLCipher ni expone una opción
`PRAGMA key` / `password` para abrir la BD cifrada. Las vías reales son:

1. **`@op-engineering/op-sqlite` con flag SQLCipher.** Es la opción técnica más sólida
   (cifra el archivo completo con una llave). PERO implica:
   - Reemplazar `expo-sqlite` por `op-sqlite` en TODO `src/db/` (otra API async).
   - Requiere `expo prebuild` + build nativo (EAS) — el proyecto ya usa EAS, así que
     es viable, pero es un cambio nativo grande que hay que **probar en build real**
     antes de confiar en él. No se puede validar en Expo Go.
   - Riesgo de regresión en todo el motor offline ya probado (borradores, cola, sync).

2. **Cifrar a nivel de campo** los `payload_json` con una llave en `expo-secure-store`
   (ya está instalado). Más quirúrgico: solo se cifran las 3-4 columnas con PII, sin
   tocar el motor SQLite ni el build. Requiere una primitiva de cifrado simétrico
   (p.ej. `expo-crypto` para derivar/HMAC + AES vía una lib JS, o `react-native-quick-crypto`).
   `expo-crypto` por sí solo hace hashing pero **no** AES, así que también suma una dep.

Ambas requieren dependencias adicionales y validación en build nativo. Por eso, para
no bloquear la Fase A (cuyo objetivo es la funcionalidad offline), se **aplaza**.

## Mitigaciones ligeras YA aplicadas (baratas, sin deps nuevas)

- `android.allowBackup: false` en `app.json` → impide extraer la BD vía `adb backup`
  sin root. (Ya estaba configurado.)
- `usesCleartextTraffic: false` + `NSAllowsArbitraryLoads: false` → sin tráfico en claro.
- App protegida con `expo-local-authentication` (biometría/PIN) → barrera de acceso.
- El **padrón** (Fase 0) guarda el documento **hasheado**, no en claro (mitigación parcial).
- La PII offline es **transitoria** y se limpia tras sincronizar; conviene además
  ejecutar `limpiarPrecarga()` y limpiar `victimas_offline`/`miembros_offline`
  enviados al cerrar sesión (TODO).

## Approach recomendado para la fase de cifrado (cuando se priorice)

1. Derivar/generar una llave aleatoria de 256 bits y guardarla en `expo-secure-store`
   (Keychain iOS / Keystore Android), creada en el primer arranque autenticado.
2. Opción A (preferida si hay tiempo de QA de build): migrar a `@op-engineering/op-sqlite`
   con SQLCipher, abrir la BD con esa llave. Validar en build EAS de `internal`.
3. Opción B (incremental, menor superficie): cifrar solo los `payload_json` con AES-GCM
   usando esa llave antes de `INSERT` y descifrar al leer. No toca el resto del esquema.
4. Añadir limpieza proactiva de PII offline ya sincronizada (purgar `victimas_offline`
   y `miembros_offline` en estado `enviado` tras cada sync exitoso).

## Referencias en el código

- `src/db/schema.ts` — `MIGRATION_V6` (TODO cifrado) y `MIGRATION_V7` (tablas con PII).
- `src/db/precargaDao.ts` — TODO(cifrado-en-reposo).
- `src/db/victimasOfflineDao.ts` / `src/db/miembrosOfflineDao.ts` — notas de seguridad.
