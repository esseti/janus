#!/bin/bash

# File di configurazione locale
CONFIG_FILE=".deploy_config"

# Carica la configurazione se esiste, altrimenti la chiede e la salva
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "Caricata configurazione da $CONFIG_FILE"
else
    echo "⚙️  Prima configurazione del deploy remoto..."
    read -p "Indirizzo del server SSH (es. pi@192.168.1.50): " REMOTE_HOST
    read -p "Cartella di destinazione sul server (es. /home/pi/janus): " REMOTE_DIR
    read -p "URL del repository Git (es. https://github.com/tuo-utente/janus.git): " GIT_REPO
    read -p "Branch Git da usare (es. main): " GIT_BRANCH
    
    echo "REMOTE_HOST=$REMOTE_HOST" > "$CONFIG_FILE"
    echo "REMOTE_DIR=$REMOTE_DIR" >> "$CONFIG_FILE"
    echo "GIT_REPO=$GIT_REPO" >> "$CONFIG_FILE"
    echo "GIT_BRANCH=$GIT_BRANCH" >> "$CONFIG_FILE"
    
    echo "✅ Configurazione salvata in $CONFIG_FILE"
fi

# Usa il branch da config, o default a "main" se non specificato
GIT_BRANCH=${GIT_BRANCH:-master}

echo "🚀 Inizio deployment remoto verso $REMOTE_HOST:$REMOTE_DIR"

# 1. Clona o aggiorna il repository Git sul server remoto
echo "📦 Clonazione/Aggiornamento del repository sul server remoto..."
ssh "$REMOTE_HOST" << EOF
    if [ ! -d "$REMOTE_DIR" ]; then
        echo "La directory non esiste. Clonazione da git..."
        git clone "$GIT_REPO" "$REMOTE_DIR"
    else
        echo "La directory esiste. Aggiornamento con git pull..."
        cd "$REMOTE_DIR"
        # Scarta eventuali modifiche locali non committate per evitare conflitti
        git reset --hard
        git pull origin $GIT_BRANCH
    fi
EOF

# Verifica se il comando SSH precedente è andato a buon fine
if [ $? -ne 0 ]; then
    echo "❌ Errore durante l'interazione con Git sul server."
    exit 1
fi

# 2. Copia i file sensibili (che non sono su Git) dal tuo computer locale al server
echo "🔑 Copia dei file sensibili e di stato dal Mac al Server..."
for file in .env credentials.json token.json; do
    if [ -f "$file" ]; then
        echo "   -> Copio $file"
        scp "$file" "$REMOTE_HOST:$REMOTE_DIR/"
    else
        echo "   ⚠️  Attenzione: il file $file non esiste localmente!"
    fi
done

# 3. Esegui lo script di deploy direttamente sul server
echo "⚙️  Avvio della configurazione di uv e Cron sul server..."
ssh "$REMOTE_HOST" << EOF
    cd "$REMOTE_DIR"
    chmod +x deploy_on_server.sh setup_cron.sh
    ./deploy_on_server.sh
EOF

echo ""
echo "🎉 Deploy remoto completato con successo!"
