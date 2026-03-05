# Configurazione Crontab per Janus

## Esecuzione automatica ogni 5 minuti

### Metodo 1: Script automatico (consigliato)

```bash
./setup_cron.sh
```

Lo script ti guiderà nella configurazione e aggiungerà automaticamente l'entry a crontab.

### Metodo 2: Configurazione manuale

1. Apri crontab:

```bash
crontab -e
```

2. Aggiungi queste righe:

```bash
# Janus - Elaborazione email ogni 5 minuti
*/5 * * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.main >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Janus - Report messaggi processati ogni ora
0 * * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.report >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1
```

3. Salva e chiudi (`:wq` in vim)

### Verifica configurazione

```bash
# Vedi crontab attuale
crontab -l

# Monitora i log in tempo reale
tail -f /Users/stefano/sw/chino/janus/janus_cron.log
```

### Formato crontab

```
*/5 * * * *  = Ogni 5 minuti
│   │ │ │ │
│   │ │ │ └─── Giorno della settimana (0-7, 0 e 7 = domenica)
│   │ │ └───── Mese (1-12)
│   │ └─────── Giorno del mese (1-31)
│   └───────── Ora (0-23)
└─────────── Minuto (0-59)
```

### Configurazione consigliata

La configurazione di default include:

- **Elaborazione email**: ogni 5 minuti
- **Report messaggi processati**: ogni ora (inviato via Google Chat)

### Altri intervalli utili

```bash
# Elaborazione ogni 10 minuti invece di 5
*/10 * * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.main >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Report ogni 2 ore invece di 1
0 */2 * * * cd /Users/stefano/sw/chino/janus && uv run python -m src.report >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Report solo alle 9, 13, 17 (orario lavorativo)
0 9,13,17 * * 1-5 cd /Users/stefano/sw/chino/janus && uv run python -m src.report >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1

# Solo in orario lavorativo (9-18, lun-ven)
*/5 9-18 * * 1-5 cd /Users/stefano/sw/chino/janus && uv run python -m src.main >> /Users/stefano/sw/chino/janus/janus_cron.log 2>&1
```

### Rimuovere crontab

```bash
# Rimuovi entry specifica
crontab -e
# Cancella la riga di Janus e salva

# Rimuovi tutto il crontab
crontab -r
```

### Log Rotation

Per evitare che il file di log cresca troppo, configura la rotazione automatica:

```bash
./setup_logrotate.sh
```

Lo script configura **newsyslog** (built-in su macOS) per:

- Rotazione giornaliera
- Mantiene 7 file (1 settimana)
- Compressione automatica
- Rotazione quando supera 10MB

Vedi `logrotate.conf` per configurazione alternativa con logrotate (Homebrew).

### Troubleshooting

**Cron non funziona?**

1. Verifica permessi Full Disk Access per `cron` in System Preferences > Privacy & Security
2. Controlla i log: `tail -f /Users/stefano/sw/chino/janus/janus_cron.log`
3. Testa il comando manualmente:

```bash
cd /Users/stefano/sw/chino/janus && /Users/stefano/.virtualenvs/janus/bin/python -m src.main
```

**ModuleNotFoundError?**

Se vedi errori come `ModuleNotFoundError: No module named 'dotenv'`, significa che cron non sta usando il virtualenv corretto. Assicurati di usare `uv run python` invece di chiamare direttamente `python`. `uv` si occuperà di creare e attivare il virtualenv automaticamente.

**Verifica log rotation:**

```bash
# Test newsyslog
sudo newsyslog -v

# Vedi file ruotati
ls -lh janus_cron.log*
```

### Note importanti

- Il sistema di timestamp (`last_run.txt`) previene elaborazioni duplicate
- Janus processa solo email più recenti dell'ultima esecuzione
- I log vengono salvati in `janus_cron.log` per debugging
- Le notifiche vengono inviate solo per email con urgenza > 2
