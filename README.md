# Janus — Gmail AI Triage Assistant

Janus monitors your Gmail, analyses every thread with an LLM (Gemini or Ollama), and sends you a consolidated digest on Google Chat. Low-urgency emails are archived automatically; high-urgency ones surface with a summary and a suggested reply.

It's vibecoder.

---

## Quick start — I'm lazy

If you have Docker, `ssh`, and `scp` on your laptop, one script does everything:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/esseti/janus/main/setup.sh)
```

It walks you through the whole process interactively: downloads config files, opens Google Cloud Console so you can create OAuth credentials, asks for your API keys, runs the auth flow, then SSHs into your server, installs Docker if needed, and starts Janus automatically.

> **That's it.** Skip the rest of this README unless something goes wrong.

---

## How it works

1. Polls Gmail for unread messages under a specific label (default: `janus`).
2. Filters out mailing lists and emails where you are not a direct recipient.
3. Sends threads in batches to the LLM for classification, urgency scoring (1–5), and summarisation.
4. Notifies you on Google Chat for urgency ≥ 3, archives the rest.
5. Runs on a schedule via cron + Docker.

---

## Setup overview

Setup has two phases:

- **On your laptop** — generate the OAuth token (requires a browser)
- **On the server** — deploy and run Janus

---

## Phase 1 — On your laptop

### 1. Get the bootstrap files

```bash
mkdir -p ~/janus && cd ~/janus
curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/docker-compose.yml
curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/.env.example
mv .env.example .env
```

### 2. Create Google OAuth credentials

Janus needs OAuth 2.0 access to your Gmail:

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services → Enabled APIs** → enable the **Gmail API**.
2. Go to **Credentials → Create Credentials → OAuth client ID**.
3. Set application type to **Desktop app**, give it a name, click **Create**.
4. Click **Download JSON** and save it as `credentials.json` in `~/janus/`.

### 3. Fill in `.env`

Edit `~/janus/.env`. At minimum:

```bash
GEMINI_API_KEY=...
GOOGLE_CHAT_WEBHOOK=...
USER_EMAIL=you@example.com
```

### 4. Generate `token.json`

This step requires a browser — run it on your laptop. Docker is the only requirement.

```bash
docker compose run --rm --service-ports auth
```

Open the URL printed in the terminal, sign in with your Google account, and authorise Janus. The container writes `token.json` in `~/janus/`.

---

## Phase 2 — On the server

### 5. Install Docker and Docker Compose

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # then log out and back in
```

Docker Compose is included in Docker Engine since v20.10. Verify with:

```bash
docker compose version
```

### 6. Create the Janus folder and copy files from your laptop

```bash
# run these on your laptop
ssh user@server 'mkdir -p ~/janus'
scp ~/janus/docker-compose.yml user@server:~/janus/
scp ~/janus/.env               user@server:~/janus/
scp ~/janus/token.json         user@server:~/janus/
```

> `credentials.json` does **not** need to be copied — it is only needed for the auth step.

### 7. Download the setup script and run it

```bash
# run on the server
cd ~/janus
curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/server-setup.sh
chmod +x server-setup.sh
./server-setup.sh
```

The script pulls the Docker image, initialises state files, and installs the crontab. Janus will now run automatically on schedule.

### 8. (Optional) Configure sender filters

Drop these files into `~/janus/` on the server:

- **`excluded_senders.txt`** — senders to skip (newsletters, bots). One glob pattern per line.
- **`keep_senders.txt`** — senders that are never skipped even if they match an exclusion.
- **`evaluation_rules.txt`** — extra rules passed to the LLM to guide classification.

### 9. (Optional) Give feedback via Gmail labels

If Janus scores an email wrong, you can correct it directly from Gmail — no CLI needed.

Apply one of these labels to the email in Gmail:

| Label | Meaning |
|---|---|
| `janus/urgent` | This email should have been flagged as urgent |
| `janus/not-urgent` | This email should not have been flagged |

On the next run, Janus reads both labels, saves a feedback entry to `feedback.json`, and removes the label from the thread. Over time, run `uv run python -m src.feedback --analyze` to turn the accumulated feedback into updated evaluation rules.

---

## Logs

```bash
ssh user@server 'tail -f ~/janus/janus_cron.log'
```

## Updates

The server's crontab runs `docker compose pull` every night at 04:00, so new images are picked up automatically.

---

## Develop locally (without Docker)

Only needed if you want to hack on the code.

```bash
uv sync
uv run python -m src.main          # process emails
uv run python -m src.report        # send digest report
uv run python -m src.preview       # preview notifications without sending
```

---

## Project layout

```
src/
├── main.py              # main processing loop
├── auth.py              # one-time OAuth helper
├── config.py            # all configuration (reads from .env + JANUS_DATA_DIR)
├── gmail_client.py      # Gmail API wrapper
├── llm_processor.py     # LangChain + Gemini/Ollama
├── notifier.py          # Google Chat notifications
├── report.py            # digest report
├── report_mailing_list.py
└── templates/           # Jinja2 templates for Chat messages
```

Runtime data (secrets, state files, logs) lives in `JANUS_DATA_DIR` (default: `.`, mounted as `/data` in Docker).
