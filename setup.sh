#!/usr/bin/env bash
set -euo pipefail

# ── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}${BOLD}▶ $*${RESET}"; }
success() { echo -e "${GREEN}✔ $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $*${RESET}"; }
ask()     { echo -e "${BOLD}$*${RESET}"; }

# ── helpers ───────────────────────────────────────────────────────────────────
open_url() {
  if command -v xdg-open &>/dev/null; then xdg-open "$1"
  elif command -v open &>/dev/null;     then open "$1"
  else warn "Open this URL manually: $1"; fi
}

require() {
  if ! command -v "$1" &>/dev/null; then
    echo -e "${RED}✘ '$1' not found. Please install it and re-run.${RESET}"; exit 1
  fi
}

# ── banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       Janus — Setup Wizard           ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════╝${RESET}"
echo ""

require docker
require curl
require ssh
require scp

if ! docker info &>/dev/null; then
  echo -e "${RED}✘ Docker daemon is not running. Please start Docker and re-run.${RESET}"
  exit 1
fi

BASE_URL="https://raw.githubusercontent.com/esseti/janus/main"
JANUS_DIR="${JANUS_DIR:-$HOME/janus}"

# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BOLD}━━━ PHASE 1: LOCAL SETUP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
# ═══════════════════════════════════════════════════════════════════════════════

# ── Step 1: Create working folder ─────────────────────────────────────────────
info "Step 1/6 — Creating local folder: $JANUS_DIR"
mkdir -p "$JANUS_DIR"
cd "$JANUS_DIR"

curl -fsSLO "$BASE_URL/docker-compose.yml"
curl -fsSLO "$BASE_URL/.env.example"
[ -f .env ] || mv .env.example .env
success "Files downloaded to $JANUS_DIR"

# ── Step 2: Google OAuth credentials ──────────────────────────────────────────
echo ""
info "Step 2/6 — Google OAuth credentials"
echo ""
echo "  Janus needs a 'credentials.json' file from Google Cloud Console."
echo "  We'll open the page for you. Steps to follow:"
echo ""
echo "    1. Enable the Gmail API"
echo "    2. Go to Credentials → Create Credentials → OAuth client ID"
echo "    3. Choose 'Desktop app', give it a name, click Create"
echo "    4. Click 'Download JSON' and save the file as 'credentials.json'"
echo "       in this folder: ${BOLD}$JANUS_DIR/${RESET}"
echo ""
ask "Press ENTER to open Google Cloud Console..."
read -r
open_url "https://console.cloud.google.com/apis/credentials"

echo ""
warn "Save credentials.json in: $JANUS_DIR/"
ask "Once saved, press ENTER to continue..."
read -r

while [ ! -f "$JANUS_DIR/credentials.json" ]; do
  warn "credentials.json not found in $JANUS_DIR/"
  ask "Save the file there, then press ENTER to retry..."
  read -r
done
success "credentials.json found."

# ── Step 3: Fill .env ─────────────────────────────────────────────────────────
echo ""
info "Step 3/6 — Configuration"
echo ""

ask "Gemini API key (from https://aistudio.google.com): "
read -r GEMINI_API_KEY

ask "Google Chat webhook URL: "
read -r GOOGLE_CHAT_WEBHOOK

ask "Your Gmail address: "
read -r USER_EMAIL

ask "Your display name (e.g. John): "
read -r USER_NAME

sed -i.bak \
  -e "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_API_KEY|" \
  -e "s|^GOOGLE_CHAT_WEBHOOK=.*|GOOGLE_CHAT_WEBHOOK=$GOOGLE_CHAT_WEBHOOK|" \
  -e "s|^USER_EMAIL=.*|USER_EMAIL=$USER_EMAIL|" \
  -e "s|^USER_NAME=.*|USER_NAME=$USER_NAME|" \
  "$JANUS_DIR/.env"
rm -f "$JANUS_DIR/.env.bak"
success ".env configured."

# ── Step 4: Generate token.json ────────────────────────────────────────────────
echo ""
info "Step 4/6 — Gmail authorisation (OAuth)"
echo ""
echo "  A browser tab will open. Sign in with your Google account and authorise Janus."
echo "  The container will catch the callback and write token.json automatically."
echo ""
ask "Press ENTER to start the auth flow..."
read -r

docker compose run --rm --service-ports auth

if [ ! -f "$JANUS_DIR/token.json" ]; then
  echo -e "${RED}✘ token.json was not created. Authentication may have failed.${RESET}"
  exit 1
fi
success "token.json generated."

# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BOLD}━━━ PHASE 2: SERVER SETUP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
# ═══════════════════════════════════════════════════════════════════════════════

ask "Server username (e.g. ubuntu): "
read -r SERVER_USER

ask "Server IP or hostname: "
read -r SERVER_HOST

SSH_TARGET="$SERVER_USER@$SERVER_HOST"

# ── Step 5: Copy files to server ───────────────────────────────────────────────
echo ""
info "Step 5/6 — Copying files to $SSH_TARGET"

ssh "$SSH_TARGET" 'mkdir -p ~/janus'
scp "$JANUS_DIR/docker-compose.yml" "$SSH_TARGET:~/janus/"
scp "$JANUS_DIR/.env"               "$SSH_TARGET:~/janus/"
scp "$JANUS_DIR/token.json"         "$SSH_TARGET:~/janus/"
scp "$JANUS_DIR/credentials.json"   "$SSH_TARGET:~/janus/"
success "Files copied. (credentials.json stays local — not needed on the server)"

# ── Step 6: Install Docker + run setup on server ───────────────────────────────
echo ""
info "Step 6/6 — Server setup"
echo ""

ssh "$SSH_TARGET" bash <<'REMOTE'
set -euo pipefail

# Install Docker if missing
if ! command -v docker &>/dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed. Re-running commands via sudo..."
  DOCKER="sudo docker"
else
  DOCKER="docker"
fi

cd ~/janus

# Download and run setup script
curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/server-setup.sh
chmod +x server-setup.sh
./server-setup.sh
REMOTE

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║   Janus is running on your server!   ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${RESET}"
echo ""
echo "  Logs:    ssh $SSH_TARGET 'tail -f ~/janus/janus_cron.log'"
echo "  Updates: automatic every night at 04:00"
echo ""
