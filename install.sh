#!/usr/bin/env bash
# ==============================================================================
# Plexi AI (plexi.ai / plexi.fyi) - Robust Single-Line Automated Installer
# Usage:
#   curl -fsSL https://alteredgenome.github.io/plexi.ai/install.sh | bash
#   curl -fsSL https://plexi.fyi/install.sh | bash
# ==============================================================================

set -euo pipefail

# ANSI Colors
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

echo -e "${CYAN}${BOLD}"
cat << "BANNER"
  ____  _            _ 
 |  _ \| | _____  _(_)
 | |_) | |/ _ \ \/ / |
 |  __/| |  __/>  <| |
 |_|   |_|\___/_/\_\_|
BANNER
echo -e "${NC}"
echo -e "${BOLD}Plexi AI - Self-Hosted Executive Assistant & Daily Planner${NC}"
echo -e "${BLUE}================================================================${NC}\n"

# 1. Root & Sudo Handling
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        echo -e "${RED}Error: Root privileges or sudo required to install dependencies.${NC}"
        exit 1
    fi
fi

# 2. Determine Install Directory
INSTALL_DIR="${PLEXI_DIR:-$HOME/.plexi}"
REPO_URL="https://github.com/alteredgenome/plexi.ai.git"
TARBALL_URL="https://github.com/alteredgenome/plexi.ai/archive/refs/heads/main.tar.gz"

echo -e "${CYAN}==>${NC} Installation target directory: ${BOLD}${INSTALL_DIR}${NC}"

# 3. Check and Install System Dependencies
echo -e "${CYAN}==>${NC} Checking and installing system packages (Python 3, venv, git, curl)..."

if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq python3 python3-venv python3-pip python3-full git curl tar build-essential >/dev/null 2>&1 || \
    $SUDO apt-get install -y python3 python3-venv python3-pip git curl tar
elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y python3 python3-pip git curl tar gcc
elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm python python-pip git curl tar base-devel
elif command -v apk >/dev/null 2>&1; then
    $SUDO apk add --no-cache python3 py3-pip git curl tar bash build-base
elif command -v brew >/dev/null 2>&1; then
    brew install python git curl
fi

# 4. Clone or Download Plexi Codebase
echo -e "${CYAN}==>${NC} Fetching latest Plexi release..."
mkdir -p "$INSTALL_DIR"

if command -v git >/dev/null 2>&1; then
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR"
        git pull origin main || true
    else
        if ! git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null; then
            echo -e "${YELLOW}Notice: Git clone restricted or failed, downloading release archive...${NC}"
            curl -fsSL "$TARBALL_URL" | tar -xz -C "$INSTALL_DIR" --strip-components=1
        fi
    fi
else
    curl -fsSL "$TARBALL_URL" | tar -xz -C "$INSTALL_DIR" --strip-components=1
fi

cd "$INSTALL_DIR"

# 5. Setup Python Virtual Environment
echo -e "${CYAN}==>${NC} Initializing isolated Python virtual environment..."
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/activate" ]; then
    rm -rf .venv
    if ! python3 -m venv .venv 2>/dev/null; then
        echo -e "${YELLOW}Notice: Attempting fallback venv initialization...${NC}"
        python3 -m venv --without-pip .venv
        curl -fsSL https://bootstrap.pypa.io/get-pip.py | .venv/bin/python3
    fi
fi

# 6. Install Python Dependencies
echo -e "${CYAN}==>${NC} Installing Python requirements..."
.venv/bin/pip install --upgrade pip >/dev/null 2>&1 || true

if [ -f "requirements.txt" ]; then
    .venv/bin/pip install -r requirements.txt
else
    .venv/bin/pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings email-validator python-multipart httpx openai python-dotenv wyoming websockets
fi

# 7. Generate Secure Configuration
if [ ! -f ".env" ]; then
    echo -e "${CYAN}==>${NC} Generating cryptographic configuration in .env..."
    RANDOM_SECRET=$(.venv/bin/python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    cat << ENVFILE > .env
PROJECT_NAME="Plexi"
SECRET_KEY="${RANDOM_SECRET}"
DATABASE_URL="sqlite+aiosqlite:///./plexi.db"
OPENROUTER_MODEL="google/gemma-2-9b-it:free"
ENVFILE
fi

# 8. Create Systemd Service (Optional helper for system installations)
if [ -d "/etc/systemd/system" ] && [ "$(id -u)" -eq 0 ]; then
    cat << SYSTEMD > /etc/systemd/system/plexi.service
[Unit]
Description=Plexi AI Executive Assistant
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
EnvironmentFile=-${INSTALL_DIR}/.env

[Install]
WantedBy=multi-user.target
SYSTEMD
    systemctl daemon-reload || true
    systemctl enable plexi || true
    systemctl restart plexi || true
    echo -e "${GREEN}${BOLD}✔ Systemd service 'plexi' installed and started!${NC}"
fi

# 9. Completion Message
echo -e "\n${GREEN}${BOLD}================================================================${NC}"
echo -e "${GREEN}${BOLD}   ✔ Plexi AI Installation Complete!${NC}"
echo -e "${GREEN}${BOLD}================================================================${NC}\n"

echo -e "${BOLD}To run Plexi manually:${NC}"
echo -e "  cd ${INSTALL_DIR}"
echo -e "  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2\n"

if [ -d "/etc/systemd/system" ] && [ "$(id -u)" -eq 0 ]; then
echo -e "${BOLD}Systemd Service Commands:${NC}"
echo -e "  systemctl status plexi"
echo -e "  systemctl restart plexi\n"
fi

echo -e "${BOLD}Access your Plexi instance in your browser:${NC}"
echo -e "  🌐 Setup Wizard & Dashboard: ${CYAN}${BOLD}http://<your-server-ip>:8000${NC} (or ${CYAN}http://localhost:8000${NC})"
echo -e "  📚 Interactive API Docs:     ${CYAN}http://<your-server-ip>:8000/docs${NC}\n"
echo -e "${YELLOW}👉 Open http://<your-server-ip>:8000 to complete the First-Run Setup Wizard!${NC}\n"
