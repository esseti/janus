#!/bin/bash
# Script per configurare logrotate per Janus su macOS
# macOS non ha logrotate di default, quindi usiamo newsyslog (built-in)

PROJECT_DIR="/Users/stefano/sw/chino/janus"
LOG_FILE="$PROJECT_DIR/janus_cron.log"
NEWSYSLOG_CONF="/etc/newsyslog.d/janus.conf"

echo "📝 Configurazione Log Rotation per Janus"
echo "========================================"
echo ""

# Verifica se logrotate è installato (opzionale via Homebrew)
if command -v logrotate &> /dev/null; then
    echo "✅ logrotate trovato (Homebrew)"
    echo ""
    echo "Configurazione logrotate:"
    cat "$PROJECT_DIR/logrotate.conf"
    echo ""
    echo "Per usare logrotate (richiede installazione via Homebrew):"
    echo "1. brew install logrotate"
    echo "2. Aggiungi a crontab:"
    echo "   0 0 * * * /opt/homebrew/bin/logrotate $PROJECT_DIR/logrotate.conf --state $PROJECT_DIR/logrotate.state"
    echo ""
else
    echo "ℹ️  logrotate non installato (opzionale)"
    echo ""
fi

# Usa newsyslog (built-in su macOS)
echo "📋 Configurazione newsyslog (consigliato per macOS):"
echo ""
echo "File: $NEWSYSLOG_CONF"
echo "Contenuto:"
echo "# logfilename          [owner:group]    mode count size when  flags [/pid_file] [sig_num]"
echo "$LOG_FILE  stefano:staff  644  7     10240  *     GJ"
echo ""
echo "Spiegazione:"
echo "  - Rotazione giornaliera (*)"
echo "  - Mantiene 7 file (1 settimana)"
echo "  - Rotazione quando supera 10MB (10240 KB)"
echo "  - G = compressione gzip"
echo "  - J = compressione bzip2"
echo ""
echo "Vuoi creare la configurazione newsyslog? (richiede sudo) (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "# Janus log rotation" | sudo tee "$NEWSYSLOG_CONF" > /dev/null
    echo "# logfilename          [owner:group]    mode count size when  flags [/pid_file] [sig_num]" | sudo tee -a "$NEWSYSLOG_CONF" > /dev/null
    echo "$LOG_FILE  stefano:staff  644  7     10240  *     GJ" | sudo tee -a "$NEWSYSLOG_CONF" > /dev/null
    
    echo "✅ Configurazione newsyslog creata!"
    echo ""
    echo "📋 File creato: $NEWSYSLOG_CONF"
    cat "$NEWSYSLOG_CONF"
    echo ""
    echo "🔄 newsyslog viene eseguito automaticamente da macOS ogni giorno"
    echo "   Per testare manualmente: sudo newsyslog -v"
else
    echo "❌ Configurazione annullata."
    echo ""
    echo "Alternativa: Rotazione manuale via crontab"
    echo "Aggiungi a crontab:"
    echo "0 0 * * * [ -f $LOG_FILE ] && tail -10000 $LOG_FILE > $LOG_FILE.tmp && mv $LOG_FILE.tmp $LOG_FILE && gzip -c $LOG_FILE > $LOG_FILE.\$(date +\\%Y\\%m\\%d).gz"
fi

echo ""
echo "✅ Setup completato!"
