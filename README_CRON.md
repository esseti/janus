# Crontab Configuration for Janus

## Automatic execution every 5 minutes

### Method 1: Setup script (recommended)

```bash
./setup_cron.sh
```

The script will configure and install the crontab entries automatically.

### Method 2: Manual configuration

1. Open crontab:

```bash
crontab -e
```

2. Add these lines:

```bash
# Janus - process emails every 5 minutes
*/5 * * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.main >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Janus - digest report every hour
0 * * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.report >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1
```

3. Save and close (`:wq` in vim)

### Verify configuration

```bash
# Show current crontab
crontab -l

# Follow logs in real time
tail -f /Users/stefano/sw/chino/janus/janus_cron.log
```

### Crontab format

```
*/5 * * * *  = Every 5 minutes
│   │ │ │ │
│   │ │ │ └─── Day of week (0-7, 0 and 7 = Sunday)
│   │ │ └───── Month (1-12)
│   │ └─────── Day of month (1-31)
│   └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Default schedule

- **Email processing**: every 5 minutes
- **Digest report**: every hour (sent via Google Chat)

### Other useful intervals

```bash
# Process every 10 minutes instead of 5
*/10 * * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.main >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Report every 2 hours instead of 1
0 */2 * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.report >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Report only at 9, 13, 17 (business hours)
0 9,13,17 * * 1-5 cd /Users/stefano/sw/chino/janus && uv run python -m src.report >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Business hours only (9-18, Mon-Fri)
*/5 9-18 * * 1-5 cd /Users/stefano/sw/chino/janus && uv run python -m src.main >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1
```

### Remove crontab entries

```bash
# Remove a specific entry
crontab -e
# Delete the Janus line and save

# Remove the entire crontab
crontab -r
```

### Log Rotation

To prevent the log file from growing indefinitely:

```bash
./setup_logrotate.sh
```

The script configures **newsyslog** (built-in on macOS) to:

- Rotate daily
- Keep 7 files (1 week)
- Compress automatically
- Rotate when the file exceeds 10 MB

See `logrotate.conf` for an alternative configuration using logrotate (Homebrew).

### Troubleshooting

**Cron not running?**

1. Check Full Disk Access permission for `cron` in System Preferences > Privacy & Security
2. Check the logs: `tail -f /Users/stefano/sw/chino/janus/janus_cron.log`
3. Test the command manually:

```bash
cd /Users/stefano/sw/chino/janus && /Users/stefano/.virtualenvs/janus/bin/python -m src.main
```

**ModuleNotFoundError?**

If you see `ModuleNotFoundError: No module named 'dotenv'`, cron is not using the correct virtualenv. Use `uv run python` instead of calling `python` directly — `uv` will create and activate the virtualenv automatically.

**Verify log rotation:**

```bash
# Test newsyslog
sudo newsyslog -v

# List rotated files
ls -lh janus_cron.log*
```

### Important notes

- The timestamp system (`last_run.txt`) prevents duplicate processing
- Janus only processes emails newer than the last run
- Logs are written to `janus_cron.log` for debugging
- Notifications are sent only for emails with urgency > 2
