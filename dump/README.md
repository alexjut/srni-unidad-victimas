# Dump — Hogares demo listos para caracterización

Fixture Django (`loaddata`) que crea **10 hogares NUEVOS ya armados y listos para
caracterización**. Cada hogar trae su **titular autorizado** (enlazado a su registro
de `Victima`) y **1 a 4 miembros adicionales**, pero **SIN sesión de encuesta ni
respuestas**: la idea es que el encuestador entre y empiece la caracterización desde
cero.

## Contenido

Archivo: `hogares_demo_10.json` — **49 objetos**:

| Modelo                 | Cantidad |
|------------------------|----------|
| `victimas.Victima`     | 10       |
| `hogares.Hogar`        | 10       |
| `hogares.MiembroHogar` | 29       |

- **Documentos / consecutivos usados:** rango `9996000001`–`9996000010`
  (`cons_persona` `96001`–`96010`). Se eligieron para **no colisionar** con:
  - el mock de desarrollo (`99901xxxx` titulares / `99902xxxx` miembros),
  - `crear_datos_demo` (`99950000xx`, cons `90001`–`90010`),
  - ni el hogar "05" existente (doc `9990100005` / cons `10005`).
- **Código de hogar:** `LISTO-96001` … `LISTO-96010`.
- **Estado del hogar:** `ACTIVO`.
- **Municipios** (variados, por `codigo_dane`): `05001, 54001, 27001, 19001, 11001,
  76001, 08001, 13001, 50001, 52835`.
- El titular queda como `MiembroHogar` con `es_autorizado=True`,
  `estado_inclusion='INCLUIDO'` y enlazado por FK a su `Victima`. Los demás miembros
  van como no incluidos en RUV (`estado_inclusion='NO_INCLUIDO'`), con nombres
  ficticios cifrados.

> Este fixture **NO incluye ni borra** el hogar "05" (doc `9990100005` / cons `10005`).
> Tampoco crea `SesionEncuesta` ni `RespuestaEncuesta`.

## Precondiciones (IMPORTANTES)

El fixture referencia las FK **por PK** (los modelos `Municipio` y `TipoDocumento`
no tienen `natural_key()`, así que no se pudieron usar natural foreign keys). Por eso,
antes de cargar, la base de datos destino **debe tener las paramétricas cargadas con
los mismos PKs**:

- **`TipoDocumento` `CC`** debe existir (en el fixture se referencia como PK `1`).
- **Municipios DANE** deben estar cargados (se referencian por PK, p. ej. `687`).
  Esto se cumple si la BD destino se pobló con el mismo comando de carga DANE que
  desarrollo/producción (los PKs son estables porque provienen de la misma fuente).

Si en producción los PKs de paramétricas difirieran, habría que regenerar el fixture
contra esa BD. En la práctica, dev y prod comparten el mismo origen de carga, así que
los PKs coinciden.

## Cifrado de PII (Fernet)

Los campos PII (`primer_nombre`, `numero_documento`, etc.) usan `EncryptedField`.
En el JSON van **en texto plano (ficticio)**; al hacer `loaddata`, Django los **cifra
automáticamente** con la `FIELD_ENCRYPTION_KEY` del entorno destino. El
`numero_documento_hash` (SHA-256, sin clave) va precalculado en el fixture, por lo que
la búsqueda por documento funciona en cualquier entorno.

> Requisito: el entorno destino debe tener configurada `FIELD_ENCRYPTION_KEY` (ya es
> obligatoria para operar). No importa que la clave difiera entre dev y prod: cada
> entorno cifra con la suya propia al cargar.

## Cómo aplicarlo

### Local (desarrollo, SQLite)

Desde `srni-backend/`, con el venv:

```bash
DJANGO_SETTINGS_MODULE=srni.settings.development \
  .venv/Scripts/python.exe manage.py loaddata ../dump/hogares_demo_10.json
```

### Producción (contenedor `cz_backend`)

Copiando el archivo dentro del contenedor (o vía volumen montado):

```bash
docker cp dump/hogares_demo_10.json cz_backend:/tmp/hogares_demo_10.json
docker exec -i cz_backend python manage.py loaddata /tmp/hogares_demo_10.json
```

O, si el repo está montado como volumen en el contenedor:

```bash
docker exec -i cz_backend python manage.py loaddata /ruta/al/repo/dump/hogares_demo_10.json
```

## Idempotencia / recarga

`loaddata` inserta por PK (UUID). Volver a cargar el mismo fixture **actualiza** esos
mismos 49 objetos (mismos UUID) sin duplicar. Si ya existieran hogares con esos
titulares y quisieras empezar de cero, borra primero los `Hogar`/`Victima` con cons
`96001`–`96010`.

## Verificación realizada

- Round-trip probado: se cargó el fixture en una BD con paramétricas y **cargó sin
  errores** (`Installed 49 object(s) from 1 fixture(s)`), quedando 10 hogares nuevos,
  29 miembros y 0 sesiones; el descifrado de PII y las FK de municipio resolvieron
  correctamente.
