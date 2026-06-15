# Despliegue — SRNI Caracterización (servidor UARIV)

Infraestructura-como-código para desplegar la solución de caracterización
(backend Django + panel web React + distribución APK) en el servidor de la UARIV.

- **Servidor:** `30.0.1.109` (Ubuntu 25.10, 4 vCPU, 15 GB RAM)
- **Usuario:** `admin_rni` (acceso por llave SSH, miembro del grupo `docker`)
- **Carpeta de despliegue:** `/home/admin_rni/caracterizacion/`
- **Acceso (fase actual):** por **IP + puerto 8090 (HTTP)**, sin tocar el 80/443

---

## ⚠️ Contexto: servidor COMPARTIDO

El servidor ya tiene en producción dos contenedores de la UARIV que **no se deben tocar**:

| Contenedor | Puertos | Rol |
|---|---|---|
| `nginx-proxy-manager` | 80, 81, 443 | Proxy inverso + TLS de la entidad. Vive en la red `uariv-network`. |
| `uariv-auth-service` | 8080 | Servicio de autenticación existente. |

Por eso nuestro stack:
- Corre **aislado** en su propia red `caracterizacion_net`.
- **No** usa los puertos 80/443 (los tiene el NPM). Publica en el **8090**.
- Cuando se decida publicar con dominio + TLS, se engancha al `uariv-network`
  y se crea un *proxy host* en el NPM (fase posterior).

---

## Arquitectura del stack

```
  Navegador / móvil ──HTTP:8090──► cz_nginx (nginx:1.25)
                                     ├── /            → panel web SPA (dist estático)
                                     ├── /api/, /admin → cz_backend (gunicorn)
                                     ├── /static/      → estáticos Django
                                     └── /movil/       → APK
                                          │
                       red interna caracterizacion_net
                                          │
            ┌───────────────┬─────────────┴───────────┐
        cz_backend      cz_celery                 cz_postgres / cz_redis
        (Django 5.2)    (worker async)            (BD + cola, sin puerto al host)
```

El panel web y el API se sirven en el **mismo origen** (puerto 8090) → sin CORS.

---

## Componentes creados para este despliegue

| Archivo | Propósito |
|---|---|
| `srni-backend/Dockerfile` | Imagen del backend (Python 3.12 + Gunicorn). |
| `srni-backend/srni/settings/servidor.py` | Settings para IP/HTTP (relaja TLS de `production`). |
| `infra/deploy/docker-compose.caracterizacion.yml` | Stack completo, aislado, puerto 8090. |
| `infra/deploy/nginx.caracterizacion.conf` | Nginx del contenedor (SPA + API mismo origen). |
| `infra/deploy/.env.caracterizacion.example` | Plantilla de variables de entorno. |
| `infra/deploy/scripts/*.sh` | Orquestación reproducible (ver abajo). |

---

## Cómo desplegar (desde cero)

> Todo se ejecuta **en el servidor**, dentro de `/home/admin_rni/caracterizacion/`.
> El código se sube con `git archive` desde la máquina de desarrollo (sin credenciales en el servidor).

### 1. Subir el código (desde la máquina de desarrollo)
```powershell
# Genera un tar de los archivos rastreados y lo extrae en el servidor
git archive --format=tar HEAD | ssh -i $KEY admin_rni@30.0.1.109 `
  "mkdir -p ~/caracterizacion && tar -x -C ~/caracterizacion"
```

### 2. Desplegar (en el servidor)
```bash
cd ~/caracterizacion
bash infra/deploy/scripts/deploy-all.sh
```

El orquestador ejecuta en orden:

| Paso | Script | Qué hace |
|---|---|---|
| 1 | `10-generar-secrets.sh` | Crea `.env` con SECRET_KEY, passwords y Fernet key aleatorios (chmod 600). Idempotente. |
| 2 | `20-build-frontend.sh` | Compila el panel web (node:20) con API relativa → `srni-frontend/dist`. |
| 3 | `30-desplegar.sh` | `docker compose build && up`, migraciones y `collectstatic`. |
| 4 | `40-cargar-datos.sh` | Carga paramétricas, instrumentos y usuario de prueba `ENC001`. |
| 5 | `50-verificar.sh` | Comprueba contenedores, HTTP local, conteos de BD y login. |

---

## Acceso para probar

Mientras la OTI no abra el puerto 8090 al exterior, probar por **túnel SSH** desde tu equipo:

```powershell
ssh -i $KEY -L 8090:localhost:8090 admin_rni@30.0.1.109
# luego abrir en el navegador:  http://localhost:8090/
```

**Usuario de prueba:** `ENC001` / `SrniTest2026!`
**Cédulas de prueba (mock):** ver `apps/victimas/repository/mock.py` (ej. `CC 9990100001`).

> Para acceso externo permanente por IP, solicitar a la OTI **abrir el puerto 8090/TCP**
> (o publicar vía NPM con dominio + TLS — fase posterior).

---

## Operación

```bash
cd ~/caracterizacion
C="docker compose -f infra/deploy/docker-compose.caracterizacion.yml"
$C ps                 # estado
$C logs -f cz_backend # logs del backend
$C restart cz_backend # reiniciar un servicio
$C down               # detener el stack (NO afecta a NPM ni al auth-service)
```

---

## Automatización del build/deploy de la APK (Opción A)

Para no compilar/desplegar la APK a mano cada vez. **Cualquier desarrollador** con el
repo, el token de Expo, la llave SSH y la VPN puede ejecutarlo (con el OK del líder).

**Configuración (una sola vez en la máquina del dev):**
```bash
# Token de Expo (https://expo.dev/settings/access-tokens)
printf 'TU_TOKEN_EXPO' > ~/.eas-token        # queda fuera de git, en el equipo del dev
# Llave SSH del servidor en ~/.ssh/id_srni_servidor (o exportar SSH_KEY=ruta)
```

**Cada vez que se quiera publicar una nueva APK (con el OK):**
```bash
bash infra/deploy/scripts/deploy-apk.sh        # perfil preview (APK)
```
Hace: build en EAS (cloud) → descarga el `.apk` → respaldo de la anterior → sube a
`/movil/app.apk` en el servidor. El **QR no cambia** (sirve siempre la última).
El `versionCode` sube solo (autoIncrement) → se instala encima **sin desinstalar**.

> La APK de **campo/producción** debe construirse con la **URL de la OTI** (no ngrok):
> cambiar `EXPO_PUBLIC_API_URL` del perfil en `srni-mobile/eas.json` y reconstruir.
>
> **Opción B (CI/CD en la nube)** no aplica directo: el servidor es de red privada
> (VPN) y los runners en la nube no lo alcanzan por SSH. Requeriría un *runner propio*
> dentro de la red UARIV — pendiente para cuando crezca el equipo.

---

## Estado verificado (12-jun-2026)

Desplegado y probado funcionando en `30.0.1.109:8090`:

| Ítem | Resultado |
|---|---|
| 5 contenedores | Up (postgres healthy) |
| Panel web `/` · API `/api/` · estáticos | HTTP 200 |
| Login JWT (`ENC001` / `SrniTest2026!`) | HTTP 200 ✅ |
| Departamentos / Municipios / Tipos doc | 33 / 1102 / 8 |
| Instrumento ASISTENCIA-V8 | 178 preguntas |
| Permisos (auditoría con encuestador) | 403 (correcto) |

### Carga completa de municipios (1102)

El comando por defecto solo carga 33 capitales. Para el set completo:

```bash
docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml \
  exec -T cz_backend python manage.py cargar_departamentos_municipios --csv=/app/data/municipios_dane.csv
```

### ⚠️ Caveat: reiniciar nginx tras reconstruir el backend

`cz_nginx` resuelve la IP de `cz_backend` al arrancar. Si se **reconstruye/recrea**
`cz_backend` (nueva IP), nginx devuelve **502** hasta reiniciarlo:

```bash
docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml restart cz_nginx
```

### Deuda técnica conocida (código de la app, NO del despliegue)

Pendiente de resolver por el flujo de desarrollo (git):

- **Cargadores de instrumentos antiguos** (`cargar_territorial_v7`, `cargar_buenaventura_v7`,
  `cargar_san_andres_v7`, `cargar_telefonico_v8`, `cargar_rural_etnico_v1`,
  `cargar_urbano_etnico_v1`) fallan con `ImportError: cannot import name 'InstrumentoVersion'`
  — referencian un modelo **renombrado a `Instrumento`**. Por eso solo carga 1 de ~8 instrumentos.
  El cargador vigente basado en fixtures (`cargar_diccionario_v8`) sí funciona.
- **`cargar_direcciones_territoriales`** falla (`DireccionTerritorial.DoesNotExist`) →
  DTs y puntos de atención quedan incompletos.

Estos no bloquean el despliegue ni el login; son tareas de mantenimiento del backend.

---

## Seguridad y notas

- `.env` y cualquier secreto **no** se versionan (excluidos por `.gitignore`).
- BD y Redis **no** exponen puertos al host: solo se alcanzan dentro de la red interna.
- Fase IP/HTTP: settings `servidor.py` desactiva la redirección a HTTPS. Al pasar a
  dominio + TLS se vuelve a `production.py`.
- Víctimas: repositorio **MOCK** (datos 100 % ficticios). La integración con Oracle
  es un trámite independiente y posterior.
