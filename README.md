# Janus - Gmail LLM Assistant

Janus è un assistente intelligente che monitora le tue email Gmail, le analizza con Gemini (via LangChain) e ti aiuta a gestirle.

## Funzionalità
- Monitoraggio della label `janus`.
- Estrazione completa dei thread.
- Analisi strutturata (classificazione, urgenza, riassunto).
- Creazione automatica di bozze di risposta (solo se necessario).
- Notifiche in tempo reale su Google Chat.

## Prerequisiti
1. Python 3.10+ e Poetry.
2. File `credentials.json` nella root (da Google Cloud Console).
3. Google Chat Webhook URL.
4. Gemini API Key.

## Installazione
```bash
uv sync
```

## Configurazione
Crea o modifica il file `.env` con i tuoi dati:
```env
GEMINI_API_KEY=tua_chiave
GOOGLE_CHAT_WEBHOOK=tuo_webhook
TARGET_LABEL=janus
PROCESSED_LABEL=janus-processed
POLLING_INTERVAL=600
```

## Avvio
```bash
uv run python -m src.main
```

## Preview Template
Per vedere come appaiono i messaggi in chat senza inviarli:
```bash
uv run python -m src.preview
```
**Nota:** Al primo avvio si aprirà il browser per l'autenticazione OAuth2. Il token verrà salvato in `token.json`.
