#!/bin/bash

# Local deploy config file
CONFIG_FILE=".deploy_config"

# Load saved config or prompt for it
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "Loaded config from $CONFIG_FILE"
else
    echo "⚙️  First-time remote deploy setup..."
    read -p "SSH server address (e.g. pi@192.168.1.50): " REMOTE_HOST
    read -p "Destination folder on server (e.g. /home/pi/janus): " REMOTE_DIR
    read -p "Git repository URL (e.g. https://github.com/esseti/janus.git): " GIT_REPO
    read -p "Git branch to use (e.g. main): " GIT_BRANCH

    echo "REMOTE_HOST=$REMOTE_HOST" > "$CONFIG_FILE"
    echo "REMOTE_DIR=$REMOTE_DIR" >> "$CONFIG_FILE"
    echo "GIT_REPO=$GIT_REPO" >> "$CONFIG_FILE"
    echo "GIT_BRANCH=$GIT_BRANCH" >> "$CONFIG_FILE"

    echo "✅ Config saved to $CONFIG_FILE"
fi

GIT_BRANCH=${GIT_BRANCH:-master}

echo "🚀 Starting remote deployment to $REMOTE_HOST:$REMOTE_DIR"

# 1. Clone or update the repo on the remote server
echo "📦 Cloning/updating repository on remote server..."
ssh "$REMOTE_HOST" << EOF
    if [ ! -d "$REMOTE_DIR" ]; then
        echo "Directory does not exist. Cloning from git..."
        git clone "$GIT_REPO" "$REMOTE_DIR"
    else
        echo "Directory exists. Updating with git pull..."
        cd "$REMOTE_DIR"
        git reset --hard
        git pull origin $GIT_BRANCH
    fi
EOF

if [ $? -ne 0 ]; then
    echo "❌ Error interacting with git on the server."
    exit 1
fi

# 2. Copy secret files (not in git) from local to server
echo "🔑 Copying secret and state files to server..."
for file in .env credentials.json token.json; do
    if [ -f "$file" ]; then
        echo "   -> Copying $file"
        scp "$file" "$REMOTE_HOST:$REMOTE_DIR/"
    else
        echo "   ⚠️  Warning: $file not found locally!"
    fi
done

# 3. Run the deploy script on the server
echo "⚙️  Running server-side setup (uv + cron)..."
ssh "$REMOTE_HOST" << EOF
    cd "$REMOTE_DIR"
    chmod +x deploy_on_server.sh setup_cron.sh
    ./deploy_on_server.sh
EOF

echo ""
echo "🎉 Remote deployment complete!"
