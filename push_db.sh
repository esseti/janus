#!/bin/bash
# Script per caricare il feedback CSV modificato sul server
# Uso: ./push_db.sh

set -e

# Carica configurazione
source .deploy_config

# Path del file
EXPORT_DIR="./exports"
EXPORT_FILE="feedback_template.csv"
LOCAL_PATH="${EXPORT_DIR}/${EXPORT_FILE}"

# Verifica esistenza file
if [ ! -f "${LOCAL_PATH}" ]; then
    echo "❌ Errore: file ${LOCAL_PATH} non trovato"
    echo ""
    echo "Esegui prima: ./pull_db.sh"
    exit 1
fi

echo "📤 Caricamento file sul server..."

# Copia il file sul server in exports/
scp "${LOCAL_PATH}" "${REMOTE_HOST}:${REMOTE_DIR}/exports/${EXPORT_FILE}"

# Esegue import sul server
echo "📥 Import feedback sul server..."
ssh "${REMOTE_HOST}" "cd ${REMOTE_DIR} && /root/.local/bin/uv run python -m src.feedback --import ${EXPORT_FILE}"

# Rimuove il file dal server
echo "🧹 Pulizia file sul server..."
ssh "${REMOTE_HOST}" "rm ${REMOTE_DIR}/exports/${EXPORT_FILE}"

echo "✅ Import completato con successo!"
