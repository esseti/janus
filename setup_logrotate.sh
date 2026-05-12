#!/bin/bash
# Configure log rotation for Janus on macOS.
# macOS does not ship logrotate by default, so we use newsyslog (built-in).

PROJECT_DIR="/Users/stefano/sw/chino/janus"
LOG_FILE="$PROJECT_DIR/janus_cron.log"
NEWSYSLOG_CONF="/etc/newsyslog.d/janus.conf"

echo "📝 Configuring Log Rotation for Janus"
echo "========================================"
echo ""

# Check if logrotate is available (optional, via Homebrew)
if command -v logrotate &> /dev/null; then
    echo "✅ logrotate found (Homebrew)"
    echo ""
    echo "logrotate config:"
    cat "$PROJECT_DIR/logrotate.conf"
    echo ""
    echo "To use logrotate (requires Homebrew install):"
    echo "1. brew install logrotate"
    echo "2. Add to crontab:"
    echo "   0 0 * * * /opt/homebrew/bin/logrotate $PROJECT_DIR/logrotate.conf --state $PROJECT_DIR/logrotate.state"
    echo ""
else
    echo "ℹ️  logrotate not installed (optional)"
    echo ""
fi

# Use newsyslog (built-in on macOS)
echo "📋 newsyslog configuration (recommended for macOS):"
echo ""
echo "File: $NEWSYSLOG_CONF"
echo "Content:"
echo "# logfilename          [owner:group]    mode count size when  flags [/pid_file] [sig_num]"
echo "$LOG_FILE  stefano:staff  644  7     10240  *     GJ"
echo ""
echo "Notes:"
echo "  - Daily rotation (*)"
echo "  - Keep 7 files (1 week)"
echo "  - Rotate when file exceeds 10 MB (10240 KB)"
echo "  - G = gzip compression"
echo "  - J = bzip2 compression"
echo ""
echo "Create the newsyslog configuration? (requires sudo) (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "# Janus log rotation" | sudo tee "$NEWSYSLOG_CONF" > /dev/null
    echo "# logfilename          [owner:group]    mode count size when  flags [/pid_file] [sig_num]" | sudo tee -a "$NEWSYSLOG_CONF" > /dev/null
    echo "$LOG_FILE  stefano:staff  644  7     10240  *     GJ" | sudo tee -a "$NEWSYSLOG_CONF" > /dev/null

    echo "✅ newsyslog configuration created!"
    echo ""
    echo "📋 File created: $NEWSYSLOG_CONF"
    cat "$NEWSYSLOG_CONF"
    echo ""
    echo "🔄 newsyslog runs automatically on macOS every day."
    echo "   To test manually: sudo newsyslog -v"
else
    echo "❌ Configuration cancelled."
    echo ""
    echo "Alternative: manual rotation via crontab"
    echo "Add to crontab:"
    echo "0 0 * * * [ -f $LOG_FILE ] && tail -10000 $LOG_FILE > $LOG_FILE.tmp && mv $LOG_FILE.tmp $LOG_FILE && gzip -c $LOG_FILE > $LOG_FILE.\$(date +\\%Y\\%m\\%d).gz"
fi

echo ""
echo "✅ Setup complete!"
