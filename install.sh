#!/usr/bin/env bash
# ==============================================================================
# Plexi AI (plexi.ai / plexi.fyi) - Single-Line Automated Installer
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

# 1. Determine Install Location
INSTALL_DIR="${PLEXI_DIR:-$HOME/.plexi}"
REPO_URL="https://github.com/alteredgenome/plexi.ai.git"

echo -e "${CYAN}==>${NC} Installation target directory: ${BOLD}${INSTALL_DIR}${NC}"

# 2. Check System Dependencies
echo -e "${CYAN}==>${NC} Checking system requirements..."

MISSING_PKGS=""
command -v python3 >/dev/null 2>&1 || MISSING_PKGS="${MISSING_PKGS} python3"
command -v git >/dev/null 2>&1 || MISSING_PKGS="${MISSING_PKGS} git"
command -v curl >/dev/null 2>&1 || MISSING_PKGS="${MISSING_PKGS} curl"

if [ -n "$MISSING_PKGS" ]; then
    echo -e "${YELLOW}Missing required tools:${MISSING_PKGS}${NC}"
    echo -e "${CYAN}Attempting automatic installation...${NC}"
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip git curl
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip git curl
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm python python-pip git curl
    elif command -v brew >/dev/null 2>&1; then
        brew install python git curl
    else
        echo -e "${RED}Please install Python 3.10+, git, and curl manually.${NC}"
        exit 1
    fi
fi

# 3. Clone or Update Repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${CYAN}==>${NC} Existing Plexi installation detected. Updating..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    echo -e "${CYAN}==>${NC} Downloading Plexi repository..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    if ! git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null; then
        echo -e "${YELLOW}Notice: Preparing installation directory...${NC}"
        mkdir -p "$INSTALL_DIR"
    fi
fi

cd "$INSTALL_DIR"

# 4. Setup Isolated Python Virtual Environment
echo -e "${CYAN}==>${NC} Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo -e "${CYAN}==>${NC} Installing production dependencies..."
.venv/bin/pip install --upgrade pip >/dev/null 2>&1 || true
.venv/bin/pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings email-validator python-multipart httpx openai python-dotenv wyoming websockets >/dev/null

# 5. Generate Cryptographic Secret Key in .env
if [ ! -f ".env" ]; then
    echo -e "${CYAN}==>${NC} Generating secure configuration..."
    RANDOM_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    cat << ENVFILE > .env
PROJECT_NAME="Plexi"
SECRET_KEY="${RANDOM_SECRET}"
DATABASE_URL="sqlite+aiosqlite:///./plexi.db"
OPENROUTER_MODEL="google/gemma-2-9b-it:free"
ENVFILE
fi

# 6. Success Output & Launch
echo -e "\n${GREEN}${BOLD}✔ Plexi successfully installed!${NC}\n"
echo -e "${BOLD}To start Plexi manually:${NC}"
echo -e "  cd ${INSTALL_DIR}"
echo -e "  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2\n"

echo -e "${BOLD}Accessing your instance:${NC}"
echo -e "  🌐 Web Dashboard & Setup Wizard: ${CYAN}${BOLD}http://localhost:8000${NC}"
echo -e "  📚 Interactive API Docs:          ${CYAN}http://localhost:8000/docs${NC}"
echo -e "\n${YELLOW}👉 Open http://localhost:8000 in your browser to complete the first-run setup wizard!${NC}\n"
