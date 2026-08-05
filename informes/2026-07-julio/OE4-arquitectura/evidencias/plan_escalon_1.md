# Plan de trabajo — Escalón 1 (primera escritura real contra la réplica LOCAL)

> **Fecha:** 2026-07-24 · **Alcance:** habilitar y ejecutar la escritura de 1 hogar de
> prueba (`LISTO-96001`) contra el Oracle **local** (`srni-oracle-local`), vía los
> procedures oficiales `GIC_*`. **Local únicamente** — cero escrituras en producción
> (contra prod solo lectura de referencia, sin PII).

## ✅ RESULTADO (2026-07-24) — LOGRADO

Primera escritura real de una caracterización SICAV al Oracle legacy (réplica local)
end-to-end vía procedures oficiales. `escribir_a_oracle --hogar LISTO-96001 --confirmar
--destino local` → **10/10 pasos VERIFICADO** (por SELECT), **idempotente** (re-run no
duplica), hogar `999999-K34C6`:

- **HOGAR** ✓ (estado=ACTIVA, usu_id=999999 servicio, usu_creacion=228206 encuestador real, tpocrn=2)
- **3 PERSONA** ✓ — RELAC fiel: jefe=**1** (Jefe de hogar), cónyuge=**4**, hijo=**3**; nombres partidos bien; extras (declar/siniestro/fuente/tvictima) = **NULL**
- **3 MIEMBRO** ✓ · **TERRITORIO** ✓ (iddt=7, punto=13, muni=32) · **2 RESPUESTA** ✓ (res_id 8 y 69)

### Bugs encontrados y resueltos en el camino (todos verificados)
1. **Causa raíz única del cuelgue/fallo**: `GIC_N_CARACTERIZACION` estaba **INVALID** (dblink
   `DBL_RNIENTREVISTA` inexistente → `AP_GEOGRAFIA` sin resolver). Afectaba HOGAR (vía
   `FN_GET_CODIGOENCUESTA`), TERRITORIO y RESPUESTA. **Fix A3**: stub loopback
   (`infra/oracle-local/setup_escalon1_geografia_stub.py`) → paquete VALID.
2. **REF CURSOR OUT colgaba**: `cursor.var(DB_TYPE_CURSOR)` sobre el mismo cursor que ejecuta
   el bloque cuelga indefinidamente en los procedures cascade (INSERT+COMMIT+OPEN). **Fix**:
   bindear un objeto cursor separado (`procedimientos.invocar`). Verificado 0.01s vs timeout.
3. **Idempotencia perdía el destino**: un re-run idempotente descartaba HOG_CODIGO/PER_IDPERSONA
   reales. **Fix**: recuperarlos del ledger (`escritor._registro_verificado`).

### Decisiones de cableado (con dato, no inventadas)
- RELAC del autorizado (`es_autorizado=True`) → **1** (Jefe de hogar).
- Extras P8 (ID_DECLAR/ID_PERS_FUENTE/ID_SINIESTRO/IDPERMI) → **NULL** (estructura nullable; SICAV no los origina).
- PPER_IDPREGUNTAPADRE → **NULL**; PBANDERA → **1** (upsert idempotente, no columna almacenada).
- Respuesta nivel HOGAR → se ancla al **jefe** (per_idpersona del autorizado).

### Fidelidad (nota honesta)
HOGAR/PERSONA/MIEMBRO/TERRITORIO corren contra sus procedures **reales** (VALID). RESPUESTA
corre con `AP_GEOGRAFIA` **stubeada** (vacía) → valida la **forma**, no el comportamiento
geográfico. El fiel de verdad se repite en un **Pruebas de OTI** con la geografía real.

## Diagnóstico de partida (medido 2026-07-24)
- `GIC_CATEGORIZACION` (hogar/persona/miembro): **VALID** local → ejecutable.
- `GIC_N_CARACTERIZACION` (respuestas): **BODY INVALID** (dblink `RNI_MI_PRU.AP_GEOGRAFIA`).
- Falta referencia: `GIC_USUARIO`=0, `GIC_N_DT_PUNTOS_ATENCION`=0, `GIC_PARENTESCOGENEALOGICO`=0.
- Código: `T_VICTIMA`→NULL ya resuelto. Faltan PER_IDPERSONA(hogar), PBANDERA, usuario.

## Fases

### Fase A — Réplica local con capacidad de escritura
- **A1.** Cargar referencia prod→local (sin PII): `GIC_N_DT_PUNTOS_ATENCION` (territorio),
  `GIC_PARENTESCOGENEALOGICO` (parentesco), y las que la cascada/escritura necesite.
- **A2.** Crear 1 **usuario de servicio** sintético en `GIC_USUARIO` (sin PII).
- **A3.** Stub `AP_GEOGRAFIA` (tabla vacía) + `ALTER PACKAGE ... COMPILE` de
  `GIC_N_CARACTERIZACION` (y cualquier otro INVALID que use la escritura). Verificar VALID.

### Fase B — Cablear los bloqueantes de código
- **B1.** `PPER_IDPERSONA` nivel hogar = persona del **jefe/responsable** (medido: 1 por hogar).
- **B2.** `PBANDERA` = 1 (hogar nuevo; escritura completa, no borra nada).
- **B3.** Usuario de servicio: `USUARIO_SERVICIO_ID` / `PERFIL_SERVICIO_ID` en settings.
- **B4.** P8 restantes (`ID_SINIESTRO`, `ID_DECLAR`): medir en prod si son NULL/opcionales.

### Fase C — Ejecutar y verificar
- **C1.** `cargar_hogar_demo_oracle` (precondición).
- **C2.** `escribir_a_oracle --hogar LISTO-96001 --confirmar` contra local.
- **C3.** Verificar por SELECT las filas escritas (hogar, persona, miembro, territorio, respuesta).
- **Iterativo:** cada fallo del procedure (traga errores) se diagnostica por SELECT, se
  corrige (más referencia / más stub / más cableado) y se re-corre.

### Fase D — Cierre
- Commit por unidad lógica (setup, cableado, corrida exitosa). Doc de resultado.

## Fidelidad (nota honesta)
Hogar/Persona/Miembro/Territorio corren contra sus procedures **reales** (VALID). El paso
**Respuesta** corre con `AP_GEOGRAFIA` **stubeado** → valida la **forma**, no el
comportamiento geográfico real. El fiel de verdad se repite en un **Pruebas de OTI**.
