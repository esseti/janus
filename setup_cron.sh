#!/bin/bash
# Script per configurare crontab per Janus
# Accetta PROJECT_DIR come parametro, altrimenti usa la directory corrente

PROJECT_DIR="${1:-.}"
LOG_FILE="$PROJECT_DIR/janus_cron.log"

# Path assoluti
UV_EXE=$(which uv)

# Se uv non è nel path, prova a cercarlo in posti comuni
if [ -z "$UV_EXE" ]; then
    UV_EXE="$HOME/.cargo/bin/uv"
fi

# Crea entry per crontab usando uv run
CRON_ENTRY_MAIN_WEEKDAY="*/5 8-18 * * 1-5 cd $PROJECT_DIR && $UV_EXE run python -m src.main >> $LOG_FILE 2>&1"
CRON_ENTRY_MAIN_WEEKEND="*/30 9-18 * * 0,6 cd $PROJECT_DIR && $UV_EXE run python -m src.main >> $LOG_FILE 2>&1"
CRON_ENTRY_REPORT="30 8,11,15,17 * * 1-5 cd $PROJECT_DIR && $UV_EXE run python -m src.report >> $LOG_FILE 2>&1"
CRON_ENTRY_MAILING_LIST="45 11,17 * * 1-5 cd $PROJECT_DIR && $UV_EXE run python -m src.report_mailing_list >> $LOG_FILE 2>&1"

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
echo "# Janus - Report messaggi processati alle 8:30, 11:30, 15:30, 17:30 (Lun-Ven)"
echo "$CRON_ENTRY_REPORT"
echo ""
echo "# Janus - Report mailing list alle 11:45 e 17:45 (Lun-Ven)"
echo "$CRON_ENTRY_MAILING_LIST"
echo ""
# Backup crontab esistente
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Rimuovi tutte le entry Janus esistenti (sia commenti che comandi)
# Usa grep -i per case-insensitive e filtra sia "# Janus" che righe con /janus
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null | grep -v -i "# Janus" | grep -v "/janus" > "$TEMP_CRON" || true

# Aggiungi le nuove entry
{
    cat "$TEMP_CRON"
    echo "# Janus - Elaborazione email ogni 5 minuti (Lun-Ven 8-18)"
    echo "$CRON_ENTRY_MAIN_WEEKDAY"
    echo "# Janus - Elaborazione email ogni 30 minuti (Sab-Dom 8-18)"
    echo "$CRON_ENTRY_MAIN_WEEKEND"
    echo "# Janus - Report messaggi processati alle 8:30, 11:30, 15:30, 17:30 (Lun-Ven)"
    echo "$CRON_ENTRY_REPORT"
    echo "# Janus - Report mailing list alle 11:45 e 17:45 (Lun-Ven)"
    echo "$CRON_ENTRY_MAILING_LIST"
} | crontab -

# Cleanup
rm -f "$TEMP_CRON"

echo "✅ Crontab configurato!"
echo "📋 Crontab attuale:"
crontab -l
