#!/bin/bash

# --- Check for root privileges ---
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ This script must be run with root or sudo privileges."
  exit 1
fi

echo "🚀 Starting the fully automated installation of OstadBank Bot using Docker..."

# --- Install Docker & Docker Compose ---
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh; sh get-docker.sh; rm get-docker.sh
fi
if ! command -v docker-compose &> /dev/null; then
    echo "🧩 Installing Docker Compose..."
    apt-get update > /dev/null 2>&1 && apt-get install -y docker-compose-plugin > /dev/null 2>&1
    if ! command -v docker-compose &> /dev/null; then
        LATEST_COMPOSE=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep "tag_name" | cut -d'"' -f4)
        curl -L "https://github.com/docker/compose/releases/download/${LATEST_COMPOSE}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
fi

# --- Clone or update the repository ---
if [ ! -d "/opt/ostadbank" ]; then
    echo "📂 Cloning the project from GitHub..."
    git clone https://github.com/arsalanarghavan/ostadbank.git /opt/ostadbank
fi
cd /opt/ostadbank
echo "🔄 Updating the project from GitHub..."
git pull origin main

# --- Create .env file ---
echo "📝 Please enter the following information:"
read -p "Enter your NEW domain name (e.g., bot.yourdomain.com): " DOMAIN_NAME
read -p "Enter your email for Let's Encrypt SSL certificate: " LETSENCRYPT_EMAIL
read -p "Enter your Telegram Bot Token: " BOT_TOKEN
read -p "Enter the numeric ID of the bot's Owner: " OWNER_ID
read -p "Enter the main channel ID (starts with -100): " CHANNEL_ID
read -p "Enter the backup channel ID (starts with -100): " BACKUP_CHANNEL_ID

DB_PASSWORD=$(openssl rand -hex 16)
DB_ROOT_PASSWORD=$(openssl rand -hex 16)

cat > .env << EOF
DOMAIN_NAME=$DOMAIN_NAME
LETSENCRYPT_EMAIL=$LETSENCRYPT_EMAIL
BOT_TOKEN=$BOT_TOKEN
OWNER_ID=$OWNER_ID
CHANNEL_ID=$CHANNEL_ID
BACKUP_CHANNEL_ID=$BACKUP_CHANNEL_ID
DB_HOST=db
DB_PORT=3306
DB_NAME=ostadbank_db
DB_USER=ostadbank_user
DB_PASSWORD=$DB_PASSWORD
DB_ROOT_PASSWORD=$DB_ROOT_PASSWORD
EOF
echo "✅ .env file created."

# --- Build and run containers ---
echo "🚀 Building images and running containers..."
docker-compose up -d --build

echo -e "\n\n🎉 **Installation completed successfully!**"
echo "✅ Your bot is now running inside Docker."
echo "ℹ️ Please ensure your HAProxy is configured to forward traffic for '$DOMAIN_NAME' to ports 8080 (HTTP) and 8443 (HTTPS)."