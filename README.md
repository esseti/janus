# Janus — Gmail AI Triage Assistant

Janus monitors your Gmail, analyses every thread with an LLM (Gemini or Ollama), and sends you a consolidated digest on Google Chat. Low-urgency emails are archived automatically; high-urgency ones surface with a summary and a suggested reply.

It's vibecoder.

## How it works

1. Polls Gmail for unread messages under a specific label (default: `janus`).
2. Filters out mailing lists and emails where you are not a direct recipient.
3. Sends threads in batches to the LLM for classification, urgency scoring (1–5), and summarisation.
4. Notifies you on Google Chat for urgency ≥ 3, archives the rest.
5. Runs on a schedule via cron + Docker.

---

## Prerequisites

| What                                                     | Where to get it                                              |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| Google Cloud project with **Gmail API** enabled          | [console.cloud.google.com](https://console.cloud.google.com) |
| OAuth 2.0 credentials (Desktop app) → `credentials.json` | Cloud Console > APIs & Services > Credentials                |
| **Gemini API key**                                       | [aistudio.google.com](https://aistudio.google.com)           |
| **Google Chat incoming webhook**                         | Chat space > Apps & integrations > Webhooks                  |
| Docker + Docker Compose (on the server)                  | [docs.docker.com](https://docs.docker.com/engine/install/)   |

---

## Setup

You don't need to clone this repo. You just need a folder with the right files in it.

### 1. Create a working folder and download the bootstrap files

```bash
mkdir -p ~/janus && cd ~/janus
curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/docker-compose.yml
curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/.env.example
curl -fsSLO https://raw.githubusercontent.com/esseti/janus/main/server-setup.sh
mv .env.example .env
chmod +x server-setup.sh
```

### 2. Fill in `.env`

Edit `.env`. At minimum:

- `GEMINI_API_KEY`
- `GOOGLE_CHAT_WEBHOOK`
- `USER_EMAIL`

### 3. Add `credentials.json`

Janus uses OAuth 2.0 to access your Gmail. To generate the credentials file:

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services → Enabled APIs** and enable the **Gmail API**.
2. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
3. Set application type to **Desktop app**, give it a name, and click **Create**.
4. Click **Download JSON** and save the file as `credentials.json`.

Set its path in `.env`:

```bash
CREDENTIALS_FILE=/path/to/your/credentials.json
```

If you leave `CREDENTIALS_FILE` unset, Janus looks for `credentials.json` in the current folder.

### 4. Generate `token.json` via Docker

This runs the OAuth flow inside the container — no local Python install required.

```bash
docker compose run --rm --service-ports auth
```

When the container prints a URL, open it in your browser (on the same machine where you ran the command), authorize, and you'll be redirected to `http://localhost:8080/...`. The container catches that callback and writes `token.json` next to your other files.

**Running on a remote server?** Open an SSH tunnel from your laptop first:

```bash
ssh -L 8080:localhost:8080 user@server
# inside the SSH session:
cd ~/janus
docker compose run --rm --service-ports auth
```

Then open the printed URL on your laptop's browser — the callback to `localhost:8080` is tunnelled through SSH to the container on the server.

### 5. Run the setup script

```bash
./server-setup.sh
```

It pulls the image, initialises the state files, and installs the crontab.

### 6. (Optional) Configure sender filters

Drop these files into the same folder if you want extra control:

- **`excluded_senders.txt`** — patterns of senders to skip (newsletters, bots). One pattern per line, supports `*` globs.
- **`keep_senders.txt`** — senders that should never be skipped, even if they match an exclusion pattern.
- **`evaluation_rules.txt`** — extra rules passed to the LLM to guide classification.

### Updates

Push to `main` → GitHub Actions builds and pushes a new image to GHCR.  
The server's crontab already runs `docker compose pull` every night at 04:00, so it picks up new images automatically.

### Logs

```bash
ssh user@server 'tail -f /home/user/janus/janus_cron.log'
```

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

## Making the Docker image public

After the first GitHub Actions run, go to:  
**GitHub → your profile → Packages → janus → Package settings → Change visibility → Public**

This lets others pull the image without authentication.

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
