# Oracle local (estructura) — setup para validación de paridad

Instancia Oracle **LOCAL** (Docker) que replica la **estructura** del esquema
`RNIENTREVISTA` de producción, para validar los servicios Django portados
(feat/oracle-legacy-writer) contra un esquema con la misma forma que producción,
**sin datos reales ni sensibles**.

> **Local únicamente.** No toca 30.0.1.9 ni ningún servidor de Pruebas.
> Solo se importa un export de **estructura (metadata)**, sin filas.

## 1. Levantar el contenedor

```bash
cd infra/oracle-local
cp .env.example .env        # y edita las 3 contraseñas
docker compose --env-file .env up -d
docker compose ps           # esperar STATUS = healthy (1-2 min la 1ª vez)
```

- Imagen: `gvenzl/oracle-free:slim` (Oracle Database Free, liviana y mantenida).
- CDB `FREE`, PDB **`FREEPDB1`**; el esquema destino `RNIENTREVISTA` se auto-crea
  vía `APP_USER` (gvenzl) al primer arranque.
- Volumen `srni-oracle-local-data` → los datos sobreviven a `down`/reinicios.
- Contraseñas: se pasan por `infra/oracle-local/.env` (nunca hardcodeadas).

### Conexión de prueba (oracledb thin, desde Python)

```bash
cd srni-backend
D:/desarrollo/unidad-victima/srni-backend/.venv/Scripts/python.exe -c "import oracledb; \
c=oracledb.connect(user='RNIENTREVISTA', password='<tu-pass>', host='localhost', \
port=1521, service_name='FREEPDB1'); \
print(c.cursor().execute('SELECT 1 FROM DUAL').fetchone())"
```

En DBeaver: driver *Oracle*, host `localhost`, port `1521`, **Service Name** (no SID)
`FREEPDB1`, user `RNIENTREVISTA`.

## 2. Importar el `.dmp` cuando llegue (de OTI)

El script tiene **DRY-RUN por defecto**: sin `.dmp` válido y sin `--confirmar` no
ejecuta nada, solo imprime el plan.

```bash
# 1. Deja el archivo en la carpeta compartida (visible dentro del contenedor):
cp <ruta>/rnient_estructura.dmp infra/oracle-local/dumps/

# 2. Verifica el mecanismo (dry-run, no ejecuta):
cd srni-backend && python scripts/import_estructura.py

# 3. Import real (metadata only):
python scripts/import_estructura.py --dmp infra/oracle-local/dumps/rnient_estructura.dmp --confirmar
```

El script: verifica el contenedor → crea `DIRECTORY DUMP_DIR` → otorga privilegios
al esquema → corre `impdp` con `CONTENT=METADATA_ONLY TRANSFORM=SEGMENT_ATTRIBUTES:N
EXCLUDE=STATISTICS TABLE_EXISTS_ACTION=SKIP` → reporta INVALID → recompila.

> `TRANSFORM=SEGMENT_ATTRIBUTES:N` ignora tablespaces/almacenamiento del origen, así
> que los objetos caen en el tablespace del usuario local sin errores de "tablespace
> not found".

## 3. Packages INVALID tras el import — qué es crítico y qué se ignora

Es **esperable** que varios objetos queden `INVALID` porque dependen de otros
esquemas/dblinks que NO existen localmente (visto en el análisis de dependencias):

| Dependencia externa | Objetos afectados | ¿Crítico? |
|---|---|---|
| `ACCIONSOCIAL` (package) | `GIC_CATEGORIZACION`, `GIC_N_CARACTERIZACION` | **No** — ver abajo |
| `GIC_CURSOR` (package) | ambos packages GIC | **No** |
| `RNI_MI_PRU.AP_GEOGRAFIA` (tabla, otro esquema) | `GIC_N_CARACTERIZACION` | **No** |
| `SP_GEN_LOG_ERROR` (procedure) | ambos packages GIC | **No** |

**Clave — por qué NINGUNO es crítico para esta validación:**
nuestra validación **NO ejecuta los packages PL/SQL**. Los servicios bajo prueba son
los **Django** (alta_hogar, alta_miembro, territorio, respuestas). El Oracle local
solo aporta la **forma del esquema** (tablas, columnas, constraints, triggers,
secuencias) para comparar que lo que producen los servicios calza con esa forma.
Por eso, que `GIC_CATEGORIZACION`/`GIC_N_CARACTERIZACION` queden INVALID **no bloquea
nada**.

### Objetos que SÍ deben quedar VALID (los usa la comparación de forma)

Sin dependencias externas → importan VALID sin problema:

- **Tablas:** `GIC_HOGAR`, `GIC_PERSONA`, `GIC_MIEMBROS_HOGAR`,
  `GIC_N_RELACION_DT_PUNTO`, `GIC_N_DT_PUNTOS_ATENCION`, `GIC_N_RESPUESTASENCUESTA`,
  `GIC_TIPOCARACTERIZACION`, `GIC_USUARIO`.
- **Secuencias:** `GIC_SEQ_HOGAR`, `GIC_SEC_PERSONA`.
- **Triggers:** `TS_GIC_HOGAR`, `TS_GIC_PERSONA_GIC_SEC_PERSONA` (asignan PK).

Si alguna de estas quedara INVALID, ahí sí revisar (no debería).

### Si en el futuro se quisiera EJECUTAR los packages (no en esta fase)

Habría que **stubear** las dependencias externas: crear en local versiones vacías de
`ACCIONSOCIAL`, `GIC_CURSOR`, `SP_GEN_LOG_ERROR` y una tabla `AP_GEOGRAFIA` mínima,
luego `ALTER PACKAGE ... COMPILE`. Fuera de alcance de esta fase (solo comparamos forma).

## 4. Conexión desde Django / tests de validación

Parametrizada en `settings.base.ORACLE_LEGACY` (leída de `.env`):

```
ORACLE_LEGACY_HOST=localhost
ORACLE_LEGACY_PORT=1521
ORACLE_LEGACY_SERVICE=FREEPDB1
ORACLE_LEGACY_USER=RNIENTREVISTA
ORACLE_LEGACY_PASSWORD=...
```

Los tests/scripts de validación de paridad leen `settings.ORACLE_LEGACY` y apuntan
por defecto al Oracle **local**, nunca a producción.

## 5. Comandos útiles

```bash
docker compose -f infra/oracle-local/docker-compose.yml logs -f oracle-local   # ver arranque
docker compose -f infra/oracle-local/docker-compose.yml down                   # parar (datos persisten)
docker compose -f infra/oracle-local/docker-compose.yml down -v                # borrar TODO
```
