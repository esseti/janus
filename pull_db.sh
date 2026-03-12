#!/bin/bash
# Script per esportare il feedback template dal server e copiarlo in locale
# Uso: ./pull_db.sh

set -e

# Carica configurazione
source .deploy_config

# Directory locale per gli export
EXPORT_DIR="./exports"
EXPORT_FILE="feedback_template.csv"
LOCAL_PATH="${EXPORT_DIR}/${EXPORT_FILE}"


# Crea directory se non esiste
mkdir -p "${EXPORT_DIR}"

echo "🔄 Connessione al server ${REMOTE_HOST}..."

# Esegue export sul server (crea il file in exports/)
echo "📦 Esportazione feedback template dal server..."
ssh "${REMOTE_HOST}" "cd ${REMOTE_DIR} && /root/.local/bin/uv run python -m src.feedback --export"

# Copia il file dal server in locale
echo "⬇️  Download file in locale..."
scp "${REMOTE_HOST}:${REMOTE_DIR}/exports/${EXPORT_FILE}" "${LOCAL_PATH}"

# Rimuove il file dal server
echo "🧹 Pulizia file sul server..."
ssh "${REMOTE_HOST}" "rm ${REMOTE_DIR}/exports/${EXPORT_FILE}"

echo "✅ Export completato: ${LOCAL_PATH}"
echo ""
echo "📝 Puoi ora modificare il file CSV localmente."
echo "   Quando hai finito, usa: ./push_db.sh"
