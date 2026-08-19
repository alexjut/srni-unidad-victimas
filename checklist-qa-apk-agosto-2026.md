# Checklist QA — Informe IGED-QA-C003 (APK Agosto 2026)

Informe: *Informe QA de Revision de Regresion — Aplicacion Movil SICAV (APK) SRNI*
Fecha del informe: Agosto 2026
Responsables: Brandon (mobile), Javier (backend)

---

## APK-001 | CRITICO | Ruta de excepcion no avanza al instrumento

**Contexto:** Javier migro el flujo el 14-ago-2026. La excepcion ahora se autoriza desde el panel web (`Autorizaciones.tsx` → `POST /api/habilitaciones/lote/`). El celular ya no pide foto ni decide la ruta — solo consume la habilitacion. `SoporteExcepcion` fue eliminado del store (`caracterizacionStore.ts`). El flujo nuevo necesita verificacion E2E.

- [ ] **1.1** (Brandon — Mobile) Verificar que `busqueda.tsx` re-consulta correctamente
  - Archivo: `app/(main)/busqueda.tsx:323-333`
  - El boton "Ya la autorizaron — volver a consultar" ejecuta `onUsarExcepcion`. Confirmar que al reconsultar, si la habilitacion existe, la persona aparece como habilitada
- [ ] **1.2** (Javier — Backend) Confirmar que `POST /api/victimas/buscar/` refleja la habilitacion
  - Cuando existe una habilitacion vigente en `/api/habilitaciones/`, el campo `habilitado_para_caracterizacion` del resultado de busqueda debe cambiar a `true`
- [ ] **1.3** (Brandon) Probar el flujo completo E2E
  1. Buscar doc con vigencia en APK → "No habilitado"
  2. Autorizar desde panel web (Autorizaciones)
  3. Presionar "Ya la autorizaron" en APK → debe salir habilitada
  4. Conformar hogar y crear sesion exitosamente

---

## APK-002 | CRITICO | "No se pudo registrar" al conformar hogar

**Contexto:** Error intermitente. Con algunos documentos (Rubiela Diaz Triana, Sara Nicol Salazar Preciado) el boton "Conformar hogar" muestra "No se pudo registrar. Revisa la conexion" pese a tener red. Con otros documentos funciona bien. Origen probable: backend.

- [x] **2.1** (Brandon — Mobile) Mejorar diagnostico del error en `conformar.tsx`
  - **YA RESUELTO por Javier** — `conformar.tsx` ya usa `interpretarError()` de `src/utils/errores.ts`
  - Líneas 338 y 446-447 muestran mensajes legibles con código HTTP y diagnóstico
- [ ] **2.2** (Javier — Backend) Investigar por que `POST /api/hogares/` falla con ciertos documentos
  - Probar con los documentos del informe
  - Puede ser validacion de victima, conflicto de hogar existente, o miembro ya asignado a otro hogar
- [ ] **2.3** (Brandon — Mobile) Fallback offline si el POST falla por red
  - Archivo: `app/(main)/hogares/conformar.tsx`
  - Verificar que el flujo offline (`hogaresOfflineDao.crearLocal()`) se activa cuando no hay red
  - Si `err.response` es `undefined` (sin red), crear el hogar localmente en vez de mostrar error

---

## APK-003 | CRITICO | Modo offline no funciona

**Contexto:** En modo avion: Encuestas muestra "No se pudo cargar las sesiones", Hogares muestra "Sin hogares" pese a existir hogares ya conformados, y las sesiones en curso no se pueden abrir. La busqueda RNI sin conexion es comportamiento esperado (depende de servicio central).

- [x] **3.1** (Brandon — Mobile) Hogares: mostrar hogares offline cuando no hay red
  - **CORREGIDO** — Dos cambios en `app/(main)/hogares/index.tsx`:
  - 1) Cuando el servidor falla, los hogares sincronizados (con `id_servidor`) ahora se muestran como tarjetas offline en vez de saltarse
  - 2) `ListEmptyComponent` devuelve `null` cuando hay error, para no mostrar "Sin hogares" + "Nuevo hogar" que induce duplicados
- [ ] **3.2** (Brandon — Mobile) Encuestas: fallback a borradores locales offline
  - Archivo: `app/(main)/encuestas/index.tsx:44-54`
  - Actualmente solo consulta el API. Agregar: si `catch`, leer borradores de `borradoresDao` y mostrarlos como tarjetas "pendiente de sincronizar" (mismo patron que hogares offline)
- [ ] **3.3** (Brandon — Mobile) Sesion detalle: leer borrador local si el API falla
  - Archivo: `app/(main)/encuestas/[sesionId].tsx`
  - Cuando el detalle falla offline, buscar el borrador local con `borradoresDao.getBorrador(sesionId)` y mostrar las respuestas guardadas localmente
- [ ] **3.4** (Brandon + Javier) Definir con el equipo si offline es requisito formal
  - Si lo es, documentar que funciona offline y que no
  - La busqueda RNI sin red es comportamiento esperado (ya lo dice el informe)

---

## APK-004 | MEDIO | No se puede editar ni eliminar integrante del hogar

**Contexto:** No existe opcion de edicion ni eliminacion desde la pantalla de "Conformar Hogar". Un integrante agregado por error queda fijo de forma permanente.

- [ ] **4.1** (Javier — Backend) Crear endpoint para eliminar miembro
  - `DELETE /api/hogares/{id}/miembros/{mid}/`
  - Solo si hogar esta en BORRADOR y el miembro no es el autorizado
- [ ] **4.2** (Brandon — Mobile) UI: boton eliminar en la lista de integrantes
  - Archivo: `app/(main)/hogares/conformar.tsx`
  - Agregar swipe-to-delete o boton X en cada miembro (excepto el autorizado)
  - Solo disponible antes de confirmar el hogar (estado BORRADOR)
- [ ] **4.3** (Javier — Backend + Brandon — Mobile) Edicion de datos del miembro
  - Backend: `PATCH /api/hogares/{id}/miembros/{mid}/`
  - Mobile: al tocar un miembro, abrir modal pre-poblado con sus datos para editar

---

## APK-005 | MEDIO | Sesion "Completada" con barra de progreso en 0%

**Contexto:** La sesion de "Asistencia humanitaria" quedo con estado "Completada" (6 respuestas guardadas) pero su barra de progreso permanece en 0%.

- [ ] **5.1** (Javier — Backend) Verificar calculo de `porcentaje_completado`
  - El serializer calcula `porcentaje_completado` de `SesionEncuesta`
  - Si la sesion se finaliza manualmente con `POST .../finalizar/`, el porcentaje puede no actualizarse
  - Verificar que al finalizar se recalcula
- [ ] **5.2** (Brandon — Mobile) Si estado es COMPLETADA, forzar barra a 100%
  - Archivo: `app/(main)/encuestas/index.tsx:124`
  - Fix: `progress={item.estado === 'COMPLETADA' ? 1 : Math.max(0, Math.min(1, item.porcentaje_completado / 100))}`
  - Sesion completada = progreso 100% por definicion

---

## APK-006 | MEDIO | Barras de progreso desbordan el contenedor

**Contexto:** Las barras de progreso de "Asistencia humanitaria" y "Caracterizacion territorial" exceden el ancho de su tarjeta. Defecto visual de frontend.

- [ ] **6.1** (Brandon — Mobile) Clamp del valor de progreso
  - Archivo: `app/(main)/encuestas/index.tsx:124`
  - Agregar clamp: `progress={Math.max(0, Math.min(1, item.porcentaje_completado / 100))}`
  - Si el backend devuelve >100, la barra se sale del contenedor
- [ ] **6.2** (Brandon — Mobile) Limitar overflow del contenedor de la barra
  - Archivo: `app/(main)/encuestas/index.tsx:171`
  - La barra tiene `flex: 1` — agregar `overflow: 'hidden'` al estilo `progresoRow` o al contenedor de `ProgressBar`

---

## APK-007 | MEDIO | No muestra nombre en resultado "No habilitado"

**Contexto:** Al buscar un documento con caracterizacion vigente, el resultado "No habilitado para caracterizacion" no mostraba el nombre de la persona.

- [x] **7.1** YA CORREGIDO por Javier
  - Commit: `1b346d7` — `feat(victima): anadir el estado No verificado a las opciones de la insignia del RUV`
  - Archivo: `app/(main)/busqueda.tsx:298-304`
  - Se agrego `<Text style={styles.nombreCompleto}>{nombreCompleto(v)}</Text>` en `TarjetaNoHabilitado`
  - El comentario en linea 299 menciona "APK-007" explicitamente
- [ ] **7.2** (Brandon) Verificar en dispositivo que se ve correctamente

---

## Resumen por responsable

### Brandon (Mobile) — 12 tareas

| Prioridad | ID | Descripcion |
|-----------|----|-------------|
| Alta | 1.1 | Verificar reconsulta en busqueda |
| Alta | 1.3 | Prueba E2E ruta de excepcion |
| Alta | 3.1 | Hogares offline — no mostrar EmptyState si hay datos locales |
| Alta | 5.2 | Barra 100% si sesion completada |
| Alta | 6.1 | Clamp del valor de progreso |
| Alta | 6.2 | Overflow hidden en contenedor de barra |
| Media | 2.1 | Mejor mensaje de error al conformar hogar |
| Media | 2.3 | Fallback offline al conformar hogar |
| Media | 3.2 | Encuestas offline — leer borradores locales |
| Media | 3.3 | Sesion detalle offline — leer borrador local |
| Baja | 4.2 | UI eliminar miembro del hogar |
| Baja | 4.3 | UI editar miembro del hogar |

### Javier (Backend) — 5 tareas

| Prioridad | ID | Descripcion |
|-----------|----|-------------|
| Alta | 1.2 | Habilitacion refleje en resultado de busqueda |
| Alta | 2.2 | Investigar POST /api/hogares/ con ciertos documentos |
| Media | 5.1 | porcentaje_completado al finalizar sesion |
| Baja | 4.1 | DELETE /api/hogares/{id}/miembros/{mid}/ |
| Baja | 4.3 | PATCH /api/hogares/{id}/miembros/{mid}/ |

### Definicion de negocio (escalar con equipo funcional)

| Tema | Pregunta |
|------|----------|
| Recaracterizacion | La regla es recaracterizar libremente, o se mantiene el control por excepcion con soporte? (Seccion 8 del informe) |
| Modo offline | Es requisito formal que la APK funcione sin conexion? Si si, documentar alcance |

### Ya resuelto

| ID | Hallazgo | Estado |
|----|----------|--------|
| APK-007 | Nombre en resultado "No habilitado" | Corregido en commit `1b346d7` — pendiente verificar en dispositivo |
| APK-008 | Autenticacion | Cumplido |
| APK-009 | Alerta de vigencia Ruta General | Cumplido |
| APK-010 | Exactitud datos busqueda RNI | Cumplido |
| APK-011 | Captura y guardado Ruta General | Cumplido |
| APK-012 | Validacion de campos integrante | Cumplido |
| APK-013 | Diseno mecanismo de excepcion | Cumplido |

---

## Orden sugerido de trabajo

1. **5.2 + 6.1 + 6.2** — Barras de progreso (3 fixes rapidos, 1 archivo, ~15 min)
2. **2.1** — Mejor mensaje de error al conformar hogar (~20 min)
3. **3.1** — Hogares offline sin EmptyState falso (~30 min)
4. **1.1 + 1.3** — Verificar flujo excepcion E2E (depende de 1.2 de Javier)
5. **3.2 + 3.3** — Encuestas offline (~1-2 h)
6. **2.3** — Fallback offline conformar hogar (~30 min)
7. **4.2 + 4.3** — Editar/eliminar miembros (depende de 4.1 de Javier)
