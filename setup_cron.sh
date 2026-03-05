#!/bin/bash
# Script per configurare crontab per Janus
# Esegue il comando ogni 5 minuti

# Path assoluti
PROJECT_DIR="/Users/stefano/sw/chino/janus"
UV_EXE=$(which uv)
LOG_FILE="$PROJECT_DIR/janus_cron.log"

# Se uv non è nel path, prova a cercarlo in posti comuni
if [ -z "$UV_EXE" ]; then
    UV_EXE="$HOME/.cargo/bin/uv"
fi

# Crea entry per crontab usando uv run
CRON_ENTRY_MAIN_WEEKDAY="*/5 8-18 * * 1-5 cd $PROJECT_DIR && $UV_EXE run python -m src.main >> $LOG_FILE 2>&1"
CRON_ENTRY_MAIN_WEEKEND="*/30 8-18 * * 0,6 cd $PROJECT_DIR && $UV_EXE run python -m src.main >> $LOG_FILE 2>&1"
CRON_ENTRY_REPORT="30 8,11,15,17 * * * cd $PROJECT_DIR && $UV_EXE run python -m src.report >> $LOG_FILE 2>&1"

echo "📝 Configurazione Crontab per Janus"
echo "=================================="
echo ""
echo "Entry da aggiungere a crontab:"
echo ""
echo "# Janus - Elaborazione email ogni 5 minuti (Lun-Ven 8-18)"
echo "$CRON_ENTRY_MAIN_WEEKDAY"
echo ""
echo "# Janus - Elaborazione email ogni 30 minuti (Sab-Dom 8-18)"
echo "$CRON_ENTRY_MAIN_WEEKEND"
echo ""
echo "# Janus - Report messaggi processati alle 8:30, 11:30, 15:30, 17:30"
echo "$CRON_ENTRY_REPORT"
echo ""
echo "Per installare:"
echo "1. Apri crontab: crontab -e"
echo "2. Aggiungi le righe sopra"
echo "3. Salva e chiudi"
echo ""
echo "Per verificare: crontab -l"
echo "Per vedere i log: tail -f $LOG_FILE"
echo ""
echo "Vuoi aggiungere automaticamente? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    # Backup crontab esistente
    crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    
    # Aggiungi entry se non esistono già
    (crontab -l 2>/dev/null | grep -v "janus"; echo "# Janus - Elaborazione email ogni 5 minuti (Lun-Ven 8-18)"; echo "$CRON_ENTRY_MAIN_WEEKDAY"; echo "# Janus - Elaborazione email ogni 30 minuti (Sab-Dom 8-18)"; echo "$CRON_ENTRY_MAIN_WEEKEND"; echo "# Janus - Report messaggi processati alle 8:30, 11:30, 15:30, 17:30"; echo "$CRON_ENTRY_REPORT") | crontab -
    
    echo "✅ Crontab configurato!"
    echo "📋 Crontab attuale:"
    crontab -l
else
    echo "❌ Configurazione annullata. Aggiungi manualmente le righe sopra."
fi
