#!/bin/bash

# Run this script ON THE SERVER after copying the project files.

echo "🚀 Starting Janus deployment on server (via uv)..."

PROJECT_DIR=$(pwd)

# 1. Check for required secret files
if [ ! -f "$PROJECT_DIR/.env" ] || [ ! -f "$PROJECT_DIR/credentials.json" ] || [ ! -f "$PROJECT_DIR/token.json" ]; then
    echo "❌ ERROR: Missing required files!"
    echo "Make sure you have copied .env, credentials.json and token.json to this directory."
    exit 1
fi

# 2. Check for uv
if ! command -v uv &> /dev/null; then
    echo "📦 uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# 3. Sync dependencies
echo "📦 Syncing dependencies with uv..."
uv sync

# 4. Initialise state files if missing
echo "📁 Initialising state and log files..."
touch "$PROJECT_DIR/last_run.txt"
if [ ! -f "$PROJECT_DIR/processed_not_notified.json" ]; then echo "[]" > "$PROJECT_DIR/processed_not_notified.json"; fi
if [ ! -f "$PROJECT_DIR/processed_notified.json" ]; then echo "[]" > "$PROJECT_DIR/processed_notified.json"; fi
if [ ! -f "$PROJECT_DIR/feedback.json" ]; then echo "[]" > "$PROJECT_DIR/feedback.json"; fi
if [ ! -f "$PROJECT_DIR/mailing_list.json" ]; then echo "[]" > "$PROJECT_DIR/mailing_list.json"; fi

# 5. Configure crontab
echo "🕒 Configuring crontab..."
./setup_cron.sh "$PROJECT_DIR"

# 6. Configure logrotate in user space
echo "🔄 Configuring logrotate..."
LOGROTATE_CONF="$PROJECT_DIR/logrotate.conf"
LOGROTATE_STATE="$PROJECT_DIR/logrotate.state"

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

(crontab -l 2>/dev/null | grep -v "logrotate.conf"; \
echo "# Janus - daily log rotation"; \
echo "$CRON_ENTRY_LOGROTATE") | crontab -

echo ""
echo "✅ Deployment complete!"
echo "The crontab is now set up to run Janus on schedule."
echo ""
echo "To follow the logs:"
echo "tail -f $PROJECT_DIR/janus_cron.log"
