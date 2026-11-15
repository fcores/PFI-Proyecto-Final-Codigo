#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# bootstrap.sh — Prepara una instancia Ubuntu 22.04 (EC2) para correr la red.
#
# Instala: Docker Engine + compose plugin, Go, git, curl, jq.
# Pensado para ejecutarse UNA vez, recién creada la instancia:
#
#   chmod +x bootstrap.sh && ./bootstrap.sh
#
# Después de correrlo, CERRÁ y reabrí la sesión SSH (o `newgrp docker`) para que
# el usuario tome el grupo 'docker' sin sudo.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

GO_VERSION="1.21.13"

echo "==> Actualizando paquetes del sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo "==> Instalando dependencias base (git, curl, jq, build-essential)..."
sudo apt-get install -y ca-certificates curl gnupg git jq build-essential

# ── Docker Engine (repositorio oficial) ──────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Instalando Docker Engine..."
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Permitir usar docker sin sudo
  sudo usermod -aG docker "$USER"
  echo "==> Usuario '$USER' agregado al grupo docker."
else
  echo "==> Docker ya está instalado: $(docker --version)"
fi

sudo systemctl enable --now docker

# ── Go ───────────────────────────────────────────────────────────────────────
NEED_GO=true
if command -v go >/dev/null 2>&1; then
  echo "==> Go ya instalado: $(go version)"
  NEED_GO=false
fi

if [ "$NEED_GO" = true ]; then
  echo "==> Instalando Go ${GO_VERSION}..."
  ARCH=$(dpkg --print-architecture)   # amd64 / arm64
  curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${ARCH}.tar.gz" -o /tmp/go.tgz
  sudo rm -rf /usr/local/go
  sudo tar -C /usr/local -xzf /tmp/go.tgz
  rm -f /tmp/go.tgz
  # PATH persistente
  if ! grep -q "/usr/local/go/bin" "$HOME/.profile" 2>/dev/null; then
    echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> "$HOME/.profile"
  fi
  export PATH=$PATH:/usr/local/go/bin
  echo "==> Go instalado: $(/usr/local/go/bin/go version)"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " Bootstrap completo."
echo ""
echo " IMPORTANTE: cerrá y reabrí la sesión SSH (o corré 'newgrp docker')"
echo " para usar docker sin sudo y cargar el PATH de Go."
echo ""
echo " Luego:"
echo "   cd PFI-Proyecto-Final/fabric"
echo "   ./network.sh install && ./network.sh up && \\"
echo "   ./network.sh createChannel && ./network.sh deployCC"
echo "════════════════════════════════════════════════════════════════"
