#!/bin/bash
# Script per configurare crontab per Janus
# Esegue il comando ogni 5 minuti

# Path assoluti
PROJECT_DIR="/Users/stefano/sw/chino/janus"
VENV_PYTHON="/Users/stefano/.virtualenvs/janus/bin/python"
LOG_FILE="$PROJECT_DIR/janus_cron.log"

# Crea entry per crontab usando direttamente il python del virtualenv
CRON_ENTRY_MAIN="*/5 * * * * cd $PROJECT_DIR && $VENV_PYTHON -m src.main >> $LOG_FILE 2>&1"
CRON_ENTRY_REPORT="30 8,11,15,17 * * * cd $PROJECT_DIR && $VENV_PYTHON -m src.report >> $LOG_FILE 2>&1"

echo "📝 Configurazione Crontab per Janus"
echo "=================================="
echo ""
echo "Entry da aggiungere a crontab:"
echo ""
echo "# Janus - Elaborazione email ogni 5 minuti"
echo "$CRON_ENTRY_MAIN"
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
    (crontab -l 2>/dev/null | grep -v "janus"; echo "# Janus - Elaborazione email ogni 5 minuti"; echo "$CRON_ENTRY_MAIN"; echo "# Janus - Report messaggi processati ogni ora"; echo "$CRON_ENTRY_REPORT") | crontab -
    
    echo "✅ Crontab configurato!"
    echo "📋 Crontab attuale:"
    crontab -l
else
    echo "❌ Configurazione annullata. Aggiungi manualmente le righe sopra."
fi
