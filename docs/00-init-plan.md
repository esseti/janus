# Piano di Implementazione Janus

## Obiettivo
Creare un sistema automatizzato in Python che monitora una label specifica di Gmail ("janus"), analizza i thread completi utilizzando l'LLM Gemini (via LangChain), crea bozze di risposta se necessario e invia notifiche a Google Chat via Webhook.

## Architettura del Progetto
```text
janus/
├── pyproject.toml          # Gestione dipendenze (Poetry)
├── .env                    # Configurazioni sensibili (API Key, Webhook)
├── credentials.json        # Credenziali Google Cloud (già presente)
├── docs/
│   └── 00-init-plan.md     # Questo documento
├── src/
│   ├── __init__.py
│   ├── config.py           # Caricamento variabili d'ambiente
│   ├── gmail_client.py     # Interfaccia Gmail API (OAuth2, Search, Fetch, Draft, Label)
│   ├── llm_processor.py    # Logica LangChain + Gemini con Pydantic Output
│   ├── notifier.py         # Client per Google Chat Webhook
│   └── main.py             # Orchestratore del workflow
└── README.md               # Istruzioni per l'avvio e l'autenticazione
```

## Dettagli Tecnici
1. **Gmail Client**: Gestione OAuth2, ricerca thread (`label:janus is:unread`), recupero thread completo, creazione bozze e segna come letto (rimozione label UNREAD).
2. **LLM Processor**: Utilizzo di Gemini-1.5-Flash via LangChain per analisi strutturata (Pydantic).
3. **Notifier**: Invio di messaggi formattati a Google Chat.
4. **Main**: Script per l'esecuzione del workflow.

## Dipendenze
- google-api-python-client
- google-auth-oauthlib
- langchain-google-genai
- pydantic
- python-dotenv
- requests
