#!/bin/bash

# Questo script va eseguito SUL SERVER / Raspberry Pi dopo aver copiato i file del progetto.

echo "🚀 Inizio deployment di Janus sul server..."

PROJECT_DIR=$(pwd)

# 1. Verifica la presenza dei file sensibili (che devi aver copiato a mano)
if [ ! -f "$PROJECT_DIR/.env" ] || [ ! -f "$PROJECT_DIR/credentials.json" ] || [ ! -f "$PROJECT_DIR/token.json" ]; then
    echo "❌ ERRORE: Mancano file critici!"
    echo "Assicurati di aver copiato dal tuo Mac i file: .env, credentials.json e token.json"
    exit 1
fi

# 2. Crea i file vuoti necessari se non esistono
# Questo evita che Docker crei erroneamente delle directory al posto dei file durante il mount dei volumi
echo "📁 Inizializzazione dei file di stato e log..."
touch "$PROJECT_DIR/last_run.txt"
if [ ! -f "$PROJECT_DIR/processed_not_notified.json" ]; then echo "[]" > "$PROJECT_DIR/processed_not_notified.json"; fi
if [ ! -f "$PROJECT_DIR/processed_notified.json" ]; then echo "[]" > "$PROJECT_DIR/processed_notified.json"; fi
if [ ! -f "$PROJECT_DIR/feedback.json" ]; then echo "[]" > "$PROJECT_DIR/feedback.json"; fi

# 3. Avvia il container tramite Docker Compose in background
echo "🐳 Avvio del container Docker in background..."
docker compose up -d

# 4. Configura il crontab per interagire col container
echo "🕒 Configurazione del Crontab (Cron job)..."

CRON_ENTRY_MAIN="*/5 8-18 * * 1-5 docker exec janus_bot python -m src.main >> $PROJECT_DIR/janus_cron.log 2>&1"
CRON_ENTRY_REPORT="0 8-18 * * 1-5 docker exec janus_bot python -m src.report >> $PROJECT_DIR/janus_cron.log 2>&1"

# 5. Configurazione Logrotate nello spazio utente
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

# Effettua un backup del cron attuale e aggiorna
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Rimuove le vecchie entry (se esistenti) e aggiunge le nuove che usano \`docker exec\` e \`logrotate\`
(crontab -l 2>/dev/null | grep -v "janus_bot" | grep -v "janus_cron.log" | grep -v "src.main" | grep -v "src.report" | grep -v "logrotate.conf"; \
echo "# Janus Docker - Elaborazione email ogni 5 minuti"; \
echo "$CRON_ENTRY_MAIN"; \
echo "# Janus Docker - Report messaggi processati ogni ora"; \
echo "$CRON_ENTRY_REPORT"; \
echo "# Janus Docker - Rotazione log giornaliera"; \
echo "$CRON_ENTRY_LOGROTATE") | crontab -

echo ""
echo "✅ Deployment completato con successo!"
echo "Il container 'janus_bot' è in esecuzione in background e dormirà in attesa dei comandi cron."
echo "Il cron del server è stato istruito per risvegliarlo ogni 5 minuti e ogni ora."
echo ""
echo "Per visualizzare i log di esecuzione puoi usare:"
echo "tail -f $PROJECT_DIR/janus_cron.log"
