#!/usr/bin/env bash
# Reconocimiento del servidor — solo lectura. No modifica nada.
set -euo pipefail

echo "===================== SISTEMA ====================="
. /etc/os-release && echo "SO: $PRETTY_NAME"
echo "Kernel: $(uname -r)   CPU: $(nproc) vCPU   RAM: $(free -h | awk '/Mem/{print $2}')   Libre disco: $(df -h / | awk 'NR==2{print $4}')"

echo
echo "================ CONTENEDORES EXISTENTES ================"
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

echo
echo "===================== REDES DOCKER ====================="
docker network ls
echo "--- Redes a las que pertenece nginx-proxy-manager ---"
docker inspect nginx-proxy-manager --format '{{json .NetworkSettings.Networks}}' | tr ',' '\n' | grep -oE '"[a-zA-Z0-9_-]+":' | tr -d '":' || true

echo
echo "===================== PUERTOS EN USO ====================="
ss -tln | awk 'NR>1 {print $4}' | grep -oE '[0-9]+$' | sort -un | tr '\n' ' '
echo

echo
echo "===================== HERRAMIENTAS ====================="
echo "docker:  $(docker --version)"
echo "compose: $(docker compose version | head -1)"
echo "git:     $(git --version)"

echo
echo "===================== CARPETAS DESPLIEGUE ====================="
echo "--- ~ ---"; ls -la ~ | grep -vE '^total'
echo "--- /opt ---"; ls -la /opt 2>/dev/null | grep -vE '^total' || echo "(sin acceso o vacío)"
echo "--- ¿existe ya caracterizacion? ---"; ls -la ~/caracterizacion 2>/dev/null || echo "(no existe — la crearemos)"

echo
echo "===================== FIN RECON ====================="
