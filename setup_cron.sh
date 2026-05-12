#!/bin/bash
# Configure crontab for Janus.
# Accepts PROJECT_DIR as argument, defaults to current directory.

PROJECT_DIR="${1:-.}"
LOG_FILE="$PROJECT_DIR/janus_cron.log"

UV_EXE=$(which uv)

# Fall back to common install location if uv is not in PATH
if [ -z "$UV_EXE" ]; then
    UV_EXE="$HOME/.cargo/bin/uv"
fi

CRON_ENTRY_MAIN_WEEKDAY="*/5 8-18 * * 1-5 cd $PROJECT_DIR && $UV_EXE run python -m src.main >> $LOG_FILE 2>&1"
CRON_ENTRY_MAIN_WEEKEND="*/30 9-18 * * 0,6 cd $PROJECT_DIR && $UV_EXE run python -m src.main >> $LOG_FILE 2>&1"
CRON_ENTRY_REPORT="30 8,11,15,17 * * 1-5 cd $PROJECT_DIR && $UV_EXE run python -m src.report >> $LOG_FILE 2>&1"
CRON_ENTRY_MAILING_LIST="45 11,17 * * 1-5 cd $PROJECT_DIR && $UV_EXE run python -m src.report_mailing_list >> $LOG_FILE 2>&1"

echo "📝 Configuring Janus crontab"
echo "=================================="
echo ""
echo "Entries to add:"
echo ""
echo "# Janus - process emails every 5 min (Mon-Fri 8-18)"
echo "$CRON_ENTRY_MAIN_WEEKDAY"
echo ""
echo "# Janus - process emails every 30 min (Sat-Sun 9-18)"
echo "$CRON_ENTRY_MAIN_WEEKEND"
echo ""
echo "# Janus - digest report at 8:30, 11:30, 15:30, 17:30 (Mon-Fri)"
echo "$CRON_ENTRY_REPORT"
echo ""
echo "# Janus - mailing list report at 11:45 and 17:45 (Mon-Fri)"
echo "$CRON_ENTRY_MAILING_LIST"
echo ""

# Back up existing crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Remove existing Janus entries
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null | grep -v -i "# Janus" | grep -v "/janus" > "$TEMP_CRON" || true

# Add new entries
{
    cat "$TEMP_CRON"
    echo "# Janus - process emails every 5 min (Mon-Fri 8-18)"
    echo "$CRON_ENTRY_MAIN_WEEKDAY"
    echo "# Janus - process emails every 30 min (Sat-Sun 9-18)"
    echo "$CRON_ENTRY_MAIN_WEEKEND"
    echo "# Janus - digest report at 8:30, 11:30, 15:30, 17:30 (Mon-Fri)"
    echo "$CRON_ENTRY_REPORT"
    echo "# Janus - mailing list report at 11:45 and 17:45 (Mon-Fri)"
    echo "$CRON_ENTRY_MAILING_LIST"
} | crontab -

rm -f "$TEMP_CRON"

echo "✅ Crontab configured!"
echo "📋 Current crontab:"
crontab -l
