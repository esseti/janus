#!/bin/bash
# One-time server setup for Janus.
# Run this after copying the data files to the server.
#
# Expected files in the current directory before running:
#   .env, credentials.json, token.json, docker-compose.yml
#   (optionally: excluded_senders.txt, keep_senders.txt, evaluation_rules.txt)
#
# Quick bootstrap (no git clone needed):
#   mkdir -p ~/janus && cd ~/janus
#   curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/docker-compose.yml
#   curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/.env.example
#   curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/server-setup.sh
#   mv .env.example .env       # then edit .env with your secrets
#   # copy credentials.json + token.json into this folder, then run this script

set -e

if ! docker info &>/dev/null; then
  echo "ERROR: Docker daemon is not running. Start it with: systemctl start docker"
  exit 1
fi

DATA_DIR=$(pwd)
LOG="$DATA_DIR/janus_cron.log"

echo "Setting up Janus in: $DATA_DIR"

# ── Verify required files ────────────────────────────────────────────────────
for f in .env credentials.json token.json docker-compose.yml; do
    if [ ! -f "$DATA_DIR/$f" ]; then
        echo "ERROR: missing required file: $f"
        exit 1
    fi
done

# ── Initialize state files ───────────────────────────────────────────────────
touch "$DATA_DIR/last_run.txt"
[ -f "$DATA_DIR/processed_not_notified.json" ] || echo "[]" > "$DATA_DIR/processed_not_notified.json"
[ -f "$DATA_DIR/processed_notified.json" ]     || echo "[]" > "$DATA_DIR/processed_notified.json"
[ -f "$DATA_DIR/feedback.json" ]               || echo "[]" > "$DATA_DIR/feedback.json"
[ -f "$DATA_DIR/mailing_list.json" ]           || echo "[]" > "$DATA_DIR/mailing_list.json"

# ── Pull Docker image ────────────────────────────────────────────────────────
echo "Pulling Docker image..."
docker compose pull

# ── Configure crontab ────────────────────────────────────────────────────────
echo "Configuring crontab..."
RUN="cd $DATA_DIR && docker compose run --rm janus"

# Remove existing Janus entries, then append new ones
(crontab -l 2>/dev/null | grep -v "# Janus" | grep -v "$DATA_DIR"; cat << EOF
# Janus - process emails every 5 min, Mon-Fri 8-18
*/5 8-18 * * 1-5 $RUN >> $LOG 2>&1
# Janus - process emails every 30 min, weekends 9-18
*/30 9-18 * * 0,6 $RUN >> $LOG 2>&1
# Janus - digest report Mon-Fri at 8:30, 11:30, 15:30, 17:30
30 8,11,15,17 * * 1-5 $RUN python -m src.report >> $LOG 2>&1
# Janus - mailing list report Mon-Fri at 11:45, 17:45
45 11,17 * * 1-5 $RUN python -m src.report_mailing_list >> $LOG 2>&1
# Janus - pull latest image daily at 4am
0 4 * * * cd $DATA_DIR && docker compose pull >> $LOG 2>&1
EOF
) | crontab -

echo ""
echo "Done. Crontab:"
crontab -l
echo ""
echo "Test run: cd $DATA_DIR && docker compose run --rm janus"
echo "Logs:     tail -f $LOG"
