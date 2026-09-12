#!/usr/bin/env bash
# ============================================================
# Despliegue del PANEL WEB (Vite) a producción
# ------------------------------------------------------------
#   bash infra/deploy/scripts/desplegar-panel.sh
#
# Construye `srni-frontend/dist` en esta máquina y reemplaza el contenido del
# `dist` del servidor. No toca el backend, ni la base, ni la APK.
#
# ─── Las dos trampas que cuestan el panel entero, las dos medidas ──────
#
# 1. **NO se puede reemplazar el DIRECTORIO `dist`, solo su contenido.**
#    `cz_nginx` lo monta con `- ../../srni-frontend/dist:/usr/share/nginx/html:ro`,
#    y un bind-mount apunta al **inode**. Si se hace `mv dist dist.viejo` y se
#    pone otro en su lugar, el contenedor sigue viendo el directorio movido
#    **para siempre**: serviría el panel anterior sin que nada falle y sin que
#    ningún `curl` lo delate. Por eso acá se vacía y se rellena en el sitio.
#
# 2. **El `dist` del servidor puede ser de `root`.** El script de build del
#    servidor (`20-build-frontend.sh`) compila dentro de un contenedor `node:20`,
#    que escribe como root. Después `admin_rni` no puede borrar ni sobrescribir
#    esos archivos, y `sudo` **cuelga la sesión SSH** en esta máquina.
#
#    Pasó el 11-sep-2026, y el modo de fallo es el peor posible: `index.html` SÍ
#    era escribible, así que quedó apuntando a un bundle que no se pudo copiar.
#    El panel respondía **200** y mostraba una pantalla en blanco.
#
#    La salida es `docker run` como root —`admin_rni` está en el grupo `docker`—
#    y dejar los archivos con su uid al terminar, para que el próximo despliegue
#    no vuelva a chocar.
#
# ─── Por qué se construye acá y no en el servidor ──────────────────────
# El disco del servidor son 61 GB compartidos con otros cuatro despliegues, y un
# `npm install` dentro de un contenedor se lleva cientos de megas. Construir acá
# también permite comprobar el bundle ANTES de subirlo, que es lo que hace el
# paso de verificación de abajo.
#
# Variables opcionales:  SSH_KEY · DEPLOY_HOST
# ============================================================
set -euo pipefail

KEY="${SSH_KEY:-$HOME/.ssh/id_srni_servidor}"
HOST="${DEPLOY_HOST:-admin_rni@30.0.1.109}"
DIST_REMOTO='/home/admin_rni/caracterizacion/srni-frontend/dist'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FRONT="$REPO_ROOT/srni-frontend"

[ -f "$KEY" ] || { echo "ERROR: no se encuentra la llave SSH: $KEY" >&2; exit 1; }
[ -d "$FRONT" ] || { echo "ERROR: no existe $FRONT" >&2; exit 1; }

echo ">> Verificando conexión SSH a $HOST (¿VPN conectada?) ..."
if ! ssh -i "$KEY" -o ConnectTimeout=12 -o BatchMode=yes "$HOST" 'echo ok' >/dev/null 2>&1; then
  echo "ERROR: no hay conexión SSH. Conecta la VPN e inténtalo de nuevo." >&2
  exit 1
fi

cd "$FRONT"

echo ">> Construyendo el panel ..."
# `npm run build` corre `tsc` primero: un error de tipos detiene el despliegue, y
# está bien que lo detenga. Es más barato arreglarlo acá que descubrirlo en el
# navegador de quien coordina.
rm -rf dist
npm run build

[ -f dist/index.html ] || { echo "ERROR: no se generó dist/index.html" >&2; exit 1; }

# ── La verificación que justifica construir del lado del desarrollador ────────
#
# `.env.local` existe en esta máquina con `VITE_API_URL=http://localhost:8001`
# para el desarrollo. En modo producción `.env.production` (vacío → URLs
# relativas) tiene prioridad, pero si algún día deja de tenerla el panel saldría
# pidiéndole la API al teléfono de quien lo abre, y el síntoma sería «el panel no
# carga datos» sin ningún error de despliegue.
if grep -rq "localhost:8001" dist/ 2>/dev/null; then
  echo "ERROR: el bundle quedó apuntando a localhost:8001." >&2
  echo "       Revisar .env.production (VITE_API_URL debe ir VACÍO)." >&2
  exit 1
fi

# El `index.html` tiene que pedir un bundle que exista. Es la comprobación que
# habría atrapado el panel en blanco del 11-sep antes de subirlo.
BUNDLE="$(grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' dist/index.html | head -1)"
[ -n "$BUNDLE" ] && [ -f "dist/$BUNDLE" ] || {
  echo "ERROR: index.html pide '$BUNDLE' y no está en dist/." >&2; exit 1; }
echo ">> Bundle: $BUNDLE  ($(du -sh dist | cut -f1) en total)"

echo ">> Empaquetando y subiendo ..."
TAR="$(mktemp -u)/panel-dist.tar.gz"
mkdir -p "$(dirname "$TAR")"
tar czf "$TAR" -C dist .
scp -i "$KEY" "$TAR" "$HOST:~/panel-dist.tar.gz"

echo ">> Reemplazando el contenido del dist en el servidor ..."
ssh -i "$KEY" "$HOST" "
set -e
# Respaldo del panel que está publicado, para poder volver.
tar czf ~/panel-dist.anterior.tar.gz -C '$DIST_REMOTO' . 2>/dev/null || true

U=\$(id -u); G=\$(id -g)
# Como root vía docker: los archivos pueden ser de root si alguna vez se
# construyó con 20-build-frontend.sh, y \`sudo\` cuelga la sesión.
#
# Se monta el propio dist —no su padre— y se vacía su CONTENIDO: el bind-mount de
# nginx apunta a este inode y reemplazar el directorio dejaría al contenedor
# sirviendo el panel viejo para siempre.
docker run --rm \
  -v '$DIST_REMOTO':/dist \
  -v /home/admin_rni/panel-dist.tar.gz:/panel.tar.gz:ro \
  alpine sh -c 'rm -rf /dist/* /dist/.[!.]* 2>/dev/null; tar xzf /panel.tar.gz -C /dist && chown -R '\$U':'\$G' /dist'
"

echo ">> Verificando lo que sirve nginx ..."
# Contra lo que responde HTTP y no contra el disco: es lo único que prueba que el
# bind-mount está viendo los archivos nuevos.
SERVIDO="$(ssh -i "$KEY" "$HOST" "curl -s http://localhost:8090/ | grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' | head -1")"
CODIGO="$(ssh -i "$KEY" "$HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8090/$BUNDLE")"

echo "   index.html servido pide : ${SERVIDO:-(nada)}"
echo "   ese bundle responde     : $CODIGO"

if [ "$SERVIDO" != "$BUNDLE" ] || [ "$CODIGO" != "200" ]; then
  echo "" >&2
  echo "❌ El panel NO quedó consistente." >&2
  echo "   Si el bundle servido es otro, el contenedor está viendo un directorio" >&2
  echo "   distinto: recrear cz_nginx." >&2
  echo "   Volver atrás:  ssh -i $KEY $HOST 'tar xzf ~/panel-dist.anterior.tar.gz -C $DIST_REMOTO'" >&2
  exit 1
fi

echo ""
echo ">> Panel desplegado ✅  —  https://caracterizacion.unidadvictimas.gov.co/"
