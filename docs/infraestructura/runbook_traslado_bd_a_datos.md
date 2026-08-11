# Runbook — trasladar la base de datos al disco `/datos`

**Servidor:** 30.0.1.109 (UARIV, VPN requerida) · **Redactado:** 11-ago-2026
**Mueve:** el volumen `caracterizacion_cz_pgdata` (33,68 GB) del disco raíz a `/datos`
**Indisponibilidad:** 35-50 min reales — anunciar **1 hora**

> **Por qué.** El disco raíz tiene 61 GB y está al 76 %. Cada regeneración del
> padrón pide ~4 GB de temporales de Postgres (medido el 11-ago: `pgsql_tmp` llegó
> a 3,9 GB y el disco cayó al 87 %). Mover la base libera **33,68 GB** y deja el
> raíz cerca del 20 %.

---

## 0. Lo verificado antes de escribir esto

No son supuestos. Se comprobaron el 11-ago contra el servidor:

| | |
|---|---|
| `/datos` | `/dev/sdc1`, 251 GB, 239 libres, ext4 |
| ¿Sobrevive a un reinicio? | **Sí** — está en `/etc/fstab` por UUID `33ca4125-8ef1-4a4d-adba-4e96f5148d48` |
| Volumen a mover | `caracterizacion_cz_pgdata` = **33,68 GB** |
| Usuario de Postgres **dentro** del contenedor | **`uid=70 gid=70`** (imagen Alpine, no el 999 habitual) |
| ¿`admin_rni` puede escribir en `/datos`? | **No** — es `root:root`. Pero **sí está en el grupo `docker`** |
| ¿`sudo`? | **No usar.** Pide contraseña interactiva y **cuelga** la sesión SSH en vez de fallar |
| ¿Otros equipos usan esta base? | **No.** `cz_postgres` está solo en `caracterizacion_net`, y la única base de aplicación es `srni_caracterizacion`. `sidi-*`, `catalogo-si-*` y `uariv-auth-*` tienen lo suyo |

**Consecuencia:** la ventana afecta solo a caracterización (panel web, sincronización
de la APK, tareas Celery). Los demás servicios del servidor siguen operando.

### El truco que evita `sudo`

`admin_rni` no puede escribir en `/datos`, pero pertenece al grupo `docker`, y un
contenedor sí corre como root:

```bash
docker run --rm -v /datos:/d alpine sh -c "mkdir -p /d/pgdata && chown 70:70 /d/pgdata"
```

Ese `70` es el uid de Postgres dentro del contenedor. **Si la copia no preserva
ese dueño, Postgres no arranca** y parece que se perdieron los datos cuando solo
son permisos.

---

## 1. Antes de empezar

Ninguna es opcional. Si una falla, se aplaza.

- [ ] **Autorización de Javier** y ventana avisada.
- [ ] **Fuera de jornada de campo.** Ninguna APK sincronizando.
- [ ] **Cola de Celery vacía** — ninguna carga de padrón o universo en vuelo.
- [ ] **Respaldo lógico** hecho el día anterior y validado.
- [ ] Sesión con `tmux`, o todo lo largo con `docker run -d`. **La VPN se cae seguido.**

```bash
cd ~/caracterizacion
C="docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml"
W=~/traslado-$(date +%Y%m%d); mkdir -p $W
```

> `--env-file .env` **no es opcional**: sin él `SECRET_KEY` queda vacío y el backend
> responde 502. El `.env` vive en `~/caracterizacion`, no en `infra/deploy/`.

---

## 2. Preflight

### 2.1 Respaldo lógico (el día ANTERIOR, en caliente, ~30-45 min)

```bash
docker run -d --name cz_dump --network caracterizacion_net \
  --env-file ~/caracterizacion/.env --user 0:0 -v /datos:/dst postgres:16-alpine \
  sh -c 'export PGPASSWORD="$DB_PASSWORD"; mkdir -p /dst/respaldos
         pg_dump -h cz_postgres -U "$DB_USER" -d "$DB_NAME" -Fc -Z6 \
           -f /dst/respaldos/srni_pre_traslado.dump && echo DUMP_OK'
docker logs -f cz_dump
```

**Esperado:** `DUMP_OK` y `exit=0`. Validar que el dump sirve:

```bash
docker run --rm --user 0:0 -v /datos:/d:ro postgres:16-alpine \
  pg_restore --list /d/respaldos/srni_pre_traslado.dump | grep -c victimas_victima
```

Si falla: el dump es requisito para **borrar** el volumen viejo, no para el
traslado. Se puede seguir, pero entonces el volumen viejo se conserva sí o sí.

### 2.2 Fotografía del estado

```bash
cp infra/deploy/docker-compose.caracterizacion.yml $W/compose.ANTES.yml
$C ps > $W/ps.ANTES.txt
df -h / /datos > $W/disco.ANTES.txt
docker exec cz_postgres psql -U srni_app -d srni_caracterizacion -Atc \
  "select count(*) from victimas_victima"        # esperado: 5926005
docker exec cz_postgres psql -U srni_app -d srni_caracterizacion -Atc \
  "select count(*) from victimas_personauniverso"  # esperado: 12009492
```

⚠️ **El servidor no tiene `.git`.** Sin esa copia del compose no hay rollback.
Si el `cp` falla, **abortar**.

### 2.3 🚨 Puerta crítica: que `/datos` esté montado HOY

```bash
findmnt -n -o SOURCE,TARGET,FSTYPE /datos
test ! -e /datos/pgdata && echo "DESTINO LIBRE OK"
```

**Esperado:** `/dev/sdc1 /datos ext4` y `DESTINO LIBRE OK`.

**Si no aparece `/dev/sdc1`: ABORTAR.** Con `/datos` sin montar, la copia se
escribiría en el disco raíz (16 GB libres), lo llenaría al 100 % y **tumbaría
también a sidi, catálogo-si y el proxy**. Aquí no hay atajo.

### 2.4 Nadie usando el sistema

```bash
docker exec cz_postgres psql -U srni_app -d srni_caracterizacion -Atc \
  "select count(*) from pg_stat_activity
    where backend_type='client backend' and pid<>pg_backend_pid();"
docker exec cz_redis redis-cli llen celery
```

**Esperado:** `0` y `0`. Si hay un encuestador sincronizando, **esperar**.

---

## 3. Apagado limpio

```bash
$C stop cz_beat cz_celery cz_celery_padron cz_backend
$C stop cz_postgres
docker ps --filter name=cz_ --format '{{.Names}}\t{{.Status}}'
```

El orden importa: primero quien escribe, después la base. El compose ya tiene
`stop_grace_period: 3m` — **hay que dejarlo terminar**: 10 s no alcanzan para el
checkpoint de una base de 33 GB, y matarla a mitad obliga a recuperación al
arrancar.

**Esperado:** los cinco en `Exited (0)`. Si alguno sale con código ≠ 0, mirar sus
logs antes de seguir.

---

## 4. La copia — 🔴 punto de no retorno a partir de aquí

```bash
docker run --rm -v /datos:/d alpine sh -c "mkdir -p /d/pgdata && chown 70:70 /d/pgdata"

docker run --rm \
  -v caracterizacion_cz_pgdata:/origen:ro \
  -v /datos/pgdata:/destino \
  alpine sh -c "cp -a /origen/. /destino/ && echo COPIA_OK"
```

`cp -a` preserva dueño, grupo, permisos y marcas de tiempo. **No usar `cp -r`.**

**Verificar ANTES de arrancar Postgres:**

```bash
docker run --rm -v caracterizacion_cz_pgdata:/o:ro -v /datos/pgdata:/d:ro alpine sh -c '
  echo "archivos origen : $(find /o -type f | wc -l)"
  echo "archivos destino: $(find /d -type f | wc -l)"
  echo "bytes origen    : $(du -sb /o | cut -f1)"
  echo "bytes destino   : $(du -sb /d | cut -f1)"
  echo "dueño destino   : $(stat -c "%u:%g" /d/PG_VERSION)"'
```

**Esperado:** los conteos y bytes coinciden, y el dueño es `70:70`. Si el dueño
no es 70:70, corregirlo antes de seguir:

```bash
docker run --rm -v /datos/pgdata:/d alpine chown -R 70:70 /d
```

---

## 5. Repuntar el compose

Se declara un volumen con **nombre nuevo**, no un bind mount plano. La razón es
concreta: si `/datos` no estuviera montado, con `type: none/o: bind` el contenedor
**falla ruidosamente**, mientras que un bind plano arrancaría Postgres sobre un
directorio vacío del disco raíz — y eso parece "se perdió la base".

```yaml
volumes:
  cz_pgdata_datos:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /datos/pgdata
```

Y en el servicio `cz_postgres`, cambiar el mount a `cz_pgdata_datos:/var/lib/postgresql/data`.

**El volumen viejo `caracterizacion_cz_pgdata` NO se toca: es el rollback.**

⚠️ **Editar en el repo, commitear y desplegar** — no editar solo en el servidor.
El servidor no tiene `.git` y el próximo `git archive` revertiría el cambio sin
avisar.

---

## 6. Arranque y verificación

```bash
$C up -d cz_postgres
sleep 20 && docker logs --tail 30 cz_postgres

# ¿Está leyendo del disco nuevo?
docker exec cz_postgres psql -U srni_app -d srni_caracterizacion -Atc "show data_directory;"

# ¿Los datos están completos?
docker exec cz_postgres psql -U srni_app -d srni_caracterizacion -Atc \
  "select count(*) from victimas_victima"          # 5926005
docker exec cz_postgres psql -U srni_app -d srni_caracterizacion -Atc \
  "select count(*) from victimas_personauniverso"  # 12009492

$C up -d cz_backend cz_celery cz_celery_padron cz_beat
docker restart cz_nginx        # ⚠️ ver abajo
sleep 6
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8090/api/    # 200
```

**El `docker restart cz_nginx` no es opcional.** Al recrear el backend cambia su
IP en la red Docker y nginx se queda con la vieja cacheada: da **502 en todo
`/api/`** aunque gunicorn esté sano.

**Y hay que verificar contra `/api/`, no contra `/`** — la raíz la sirve nginx y
responde 200 aunque el backend esté caído.

---

## 7. Rollback

Mientras no se haya arrancado Postgres sobre `/datos`, es gratis. Después, sigue
siendo un minuto:

```bash
$C stop cz_postgres cz_backend cz_celery cz_celery_padron cz_beat
cp $W/compose.ANTES.yml infra/deploy/docker-compose.caracterizacion.yml
$C up -d cz_postgres && sleep 20
$C up -d cz_backend cz_celery cz_celery_padron cz_beat
docker restart cz_nginx
```

Funciona porque **el volumen viejo sigue intacto**. Ese es el motivo de no
reutilizar su nombre: hacerlo exigiría `docker volume rm` y destruiría la única
copia física.

---

## 8. Cuándo borrar el volumen viejo

**No el mismo día.** Esperar **≥ 14 días** de operación normal y haber comprobado:

- Las cifras de las tablas se mantienen.
- Se sobrevivió a **un reinicio del servidor** (que `/datos` monte solo).
- Se corrió al menos una regeneración de padrón sin incidentes.

```bash
docker volume rm caracterizacion_cz_pgdata
```

Libera los 33,68 GB del disco raíz. Antes de esto, el espacio **no** se ha
liberado todavía: durante esos 14 días conviven las dos copias.

---

## 9. Lo que este runbook NO cubre

- **Mover `cz_media`** (1,27 GB: padrones y APK). Se puede hacer después, en
  caliente y sin ventana.
- **Mover `/var/lib/docker` entero** (liberaría además los 7,6 GB de imágenes).
  Exige parar Docker completo y ahí **sí** se caen los otros equipos.
- **Limpiar imágenes reclamables** (5,24 GB): `docker image prune -a` — se puede
  hacer cualquier día, sin ventana, aunque conviene revisar antes qué se borra.

### Decisión para Javier

Con la base fuera del raíz, este queda al ~20 % **pero solo tras borrar el volumen
viejo** (§8). En el intervalo de 14 días el disco sigue como está. Si hace falta
espacio antes, la vía sin riesgo es limpiar imágenes, no acortar la espera.

---

**Relacionado:** `docs/infraestructura/analisis_capacidad_disco.md`,
`docs/gestion/correo_oscar_espacio_disco_urgente.md`,
`infra/deploy/README.md`.
