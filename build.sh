#!/bin/bash

echo "🔨 Costruzione dell'immagine Docker per Janus..."

# Verifica se si sta buildando dal Mac per un server Raspberry Pi (architettura ARM64)
# Se stai eseguendo questo script direttamente sul Raspberry Pi, `docker compose build` basta e avanza.

echo "Scegli un'opzione di build:"
echo "1) Build standard (usa questa se stai eseguendo lo script direttamente sul server di destinazione o se il server ha la stessa architettura del tuo Mac)"
echo "2) Build incrociata per Raspberry Pi (linux/arm64) (usa questa se stai buildando dal Mac per esportare l'immagine)"
read -p "Scelta [1/2]: " BUILD_CHOICE

if [ "$BUILD_CHOICE" == "2" ]; then
    echo "Costruisco per linux/arm64..."
    # Richiede buildx abilitato
    docker buildx build --platform linux/arm64 -t janus-bot:latest --load .
    echo "✅ Build arm64 completata! Ora puoi salvare l'immagine con:"
    echo "docker save -o janus-bot.tar janus-bot:latest"
    echo "E copiarla sul server usando scp."
else
    echo "Costruisco l'immagine localmente..."
    docker compose build
    echo "✅ Build completata!"
fi
