#!/bin/bash

# Questo script va eseguito SUL SERVER / Raspberry Pi dopo aver copiato i file del progetto.

echo "🚀 Inizio deployment di Janus sul server (via uv)..."

PROJECT_DIR=$(pwd)

# 1. Verifica la presenza dei file sensibili
if [ ! -f "$PROJECT_DIR/.env" ] || [ ! -f "$PROJECT_DIR/credentials.json" ] || [ ! -f "$PROJECT_DIR/token.json" ]; then
    echo "❌ ERRORE: Mancano file critici!"
    echo "Assicurati di aver copiato dal tuo Mac i file: .env, credentials.json e token.json"
    exit 1
fi

# 2. Verifica la presenza di uv
if ! command -v uv &> /dev/null; then
    echo "📦 uv non trovato. Installazione di uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# 3. Sincronizzazione dipendenze
echo "📦 Sincronizzazione dipendenze con uv..."
uv sync

# 4. Crea i file vuoti necessari se non esistono
echo "📁 Inizializzazione dei file di stato e log..."
touch "$PROJECT_DIR/last_run.txt"
if [ ! -f "$PROJECT_DIR/processed_not_notified.json" ]; then echo "[]" > "$PROJECT_DIR/processed_not_notified.json"; fi
if [ ! -f "$PROJECT_DIR/processed_notified.json" ]; then echo "[]" > "$PROJECT_DIR/processed_notified.json"; fi
if [ ! -f "$PROJECT_DIR/feedback.json" ]; then echo "[]" > "$PROJECT_DIR/feedback.json"; fi

# 5. Configura il crontab
echo "🕒 Configurazione del Crontab..."
./setup_cron.sh

# 6. Configurazione Logrotate nello spazio utente
echo "🔄 Configurazione Logrotate..."
LOGROTATE_CONF="$PROJECT_DIR/logrotate.conf"
LOGROTATE_STATE="$PROJECT_DIR/logrotate.state"

# Crea il file di configurazione logrotate se non esiste
cat <<EOF > "$LOGROTATE_CONF"
$PROJECT_DIR/janus_cron.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $USER $USER
    size 10M
}
EOF

CRON_ENTRY_LOGROTATE="0 0 * * * /usr/sbin/logrotate -s $LOGROTATE_STATE $LOGROTATE_CONF"

# Effettua un backup del cron attuale e aggiorna per logrotate
(crontab -l 2>/dev/null | grep -v "logrotate.conf"; \
echo "# Janus - Rotazione log giornaliera"; \
echo "$CRON_ENTRY_LOGROTATE") | crontab -

echo ""
echo "✅ Deployment completato con successo!"
echo "Il cron del server è stato istruito per eseguire Janus periodicamente."
echo ""
echo "Per visualizzare i log di esecuzione puoi usare:"
echo "tail -f $PROJECT_DIR/janus_cron.log"
