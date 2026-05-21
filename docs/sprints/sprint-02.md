# Sprint 2 — Motor de Formularios + Paramétricas + Víctimas PII

**Branch:** `main`
**Estado:** ✅ Completado
**Inicio:** 2026-04-13
**Cierre:** 2026-04-13
**Commit:** `12c7d7b`

---

## Objetivos

1. Implementar el motor dinámico de formularios (replicar lógica del APK `vivanto.db`)
2. Cargar datos paramétricos geográficos (DANE: 33 departamentos, 1122 municipios, 32,377 veredas)
3. Exponer búsqueda de víctimas server-side con PII cifrado
4. Alcanzar 33 tests automáticos passing

---

## Entregables backend

### Paramétricas

**Management commands:**
- `cargar_tipos_documento` — 8 tipos (CC, TI, RC, CE, PA, NIT, NUIP, PEP)
- `cargar_departamentos_municipios` — 33 departamentos DANE + capitales; `--csv` para 1122 municipios completos

**ViewSets de solo lectura** (no requieren PII, pueden cachearse):
| Endpoint | Descripción |
|----------|-------------|
| `GET /api/parametricas/departamentos/` | 33 departamentos |
| `GET /api/parametricas/municipios/?departamento=05` | Filtrado por dpto |
| `GET /api/parametricas/veredas/?municipio=05001` | 32,377 veredas DANE |
| `GET /api/parametricas/tipos-documento/` | 8 tipos |
| `GET /api/parametricas/comunidades-negras/` | Consejos comunitarios |
| `GET /api/parametricas/resguardos-indigenas/` | Resguardos por municipio |
| `GET /api/parametricas/puntos-atencion/` | Puntos de atención UARIV |

### Motor de formularios dinámico

Replica fielmente la lógica del `EMCTEMAS`, `EMCPREGUNTASINSTRUMENTO` del APK original.

**Modelos:**
- `Instrumento` → equivalente a `EMCTIPOENTREVISTA`
- `Tema` → equivalente a `EMCTEMAS` (54 módulos)
- `Pregunta` → equivalente a `EMCPREGUNTASINSTRUMENTO`
- `OpcionRespuesta` → equivalente a `EMCOPCIONESRESPUESTA`
- `ReglaSkipLogic` → equivalente a campos `PREDEPENDE`, `RESHABILITA`, `RESFINALIZA`

**Tipos de campo implementados:**
`TEXTO`, `NUMERICO`, `FECHA`, `LISTA`, `LISTA_MULTIPLE`, `RADIO`, `BOOLEAN`, `TEXTO_LARGO`, `COMBO_DINAMICO`

**Motor skip logic:**
```
POST /api/formulario/evaluar-skip-logic/
Body: { pregunta_id, respuesta_actual, respuestas_previas }
Response: { preguntas_habilitadas: [...], preguntas_deshabilitadas: [...] }
```

Operadores soportados: `EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `NOTNULL`

### Víctimas con PII cifrado

**Serializers diferenciados por permiso:**
- `VictimaListSerializer` — sin PII, solo hash SHA-256 + metadata
- `VictimaDetalleSerializer` — PII descifrado, solo con permiso `puede_caracterizar`

**Búsqueda server-side:**
```
POST /api/victimas/buscar/
Body: { tipo_documento, numero_documento }
→ Busca por hash SHA-256, registra LogAcceso, devuelve resumen sin PII completo
```

**Correcciones técnicas:**
- `LogAcceso.save()`: usar `_state.adding` (UUIDField siempre tiene pk)
- `victimas/urls.py`: `buscar/` antes de `router.urls` para evitar captura por `<pk>`

---

## Tests: 33/33 passing

| Módulo | Tests |
|--------|-------|
| Serializers PII | 8 |
| Endpoints búsqueda víctimas | 7 |
| Motor skip logic | 10 |
| Seguridad y permisos | 8 |

---

## Decisiones técnicas

**Por qué hash SHA-256 para búsqueda:** Permite consultas por número de documento sin descifrar el campo — los índices de BD funcionan sobre el hash, no sobre el valor cifrado.

**Por qué ViewSets de solo lectura para paramétricas:** Los datos geográficos no contienen PII; pueden ser cacheados en el cliente sin riesgo. Los datos de víctimas nunca se cachean.

**Por qué skip logic en el backend:** El APK original evaluaba toda la lógica condicional en el cliente. Mover la evaluación al servidor permite auditoría y facilita cambios sin redistribuir el APK.
