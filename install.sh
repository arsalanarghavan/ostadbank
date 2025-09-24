#!/bin/bash

# --- Check for root privileges ---
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ This script must be run with root or sudo privileges."
  exit 1
fi

echo "🚀 Starting the fully automated installation of OstadBank Bot using Docker..."

# --- Check for Docker and Docker Compose, and install if not present ---
if ! command -v docker &> /dev/null; then
    echo "🐳 Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker installed successfully."
else
    echo "✅ Docker is already installed."
fi

if ! command -v docker-compose &> /dev/null; then
    echo "🧩 Docker Compose not found. Installing Docker Compose..."
    apt-get update > /dev/null 2>&1
    apt-get install -y docker-compose-plugin > /dev/null 2>&1
     if ! command -v docker-compose &> /dev/null; then
        LATEST_COMPOSE=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep "tag_name" | cut -d'"' -f4)
        curl -L "https://github.com/docker/compose/releases/download/${LATEST_COMPOSE}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
     fi
    echo "✅ Docker Compose installed successfully."
else
    echo "✅ Docker Compose is already installed."
fi

# --- Clone the repository ---
if [ ! -d "/opt/ostadbank" ]; then
    echo "📂 Cloning the project from GitHub..."
    git clone https://github.com/arsalanarghavan/ostadbank.git /opt/ostadbank
fi
cd /opt/ostadbank
git pull origin main # Ensure the code is up-to-date

# --- Create .env file from user input ---
echo "📝 Please enter the following information to create the .env file..."
read -p "Enter your domain name (e.g., bot.yourdomain.com): " DOMAIN_NAME
read -p "Enter your email for Let's Encrypt SSL certificate: " LETSENCRYPT_EMAIL
read -p "Enter your Telegram Bot Token: " BOT_TOKEN
read -p "Enter the numeric ID of the bot's Owner: " OWNER_ID
read -p "Enter the main channel ID (starts with -100): " CHANNEL_ID
read -p "Enter the backup channel ID (starts with -100): " BACKUP_CHANNEL_ID
# --- START: بخش جدید برای توکن کلادفلر ---
read -p "Enter your Cloudflare API Token (for DNS Challenge): " CLOUDFLARE_API_TOKEN
# --- END: بخش جدید ---

# Generate strong, random passwords for the database if they don't exist
DB_PASSWORD=$(openssl rand -hex 16)
DB_ROOT_PASSWORD=$(openssl rand -hex 16)
DB_NAME="ostadbank_db"
DB_USER="ostadbank_user"

# Create the .env file for Docker Compose
cat > .env << EOF
# Webhook and SSL Settings
DOMAIN_NAME=$DOMAIN_NAME
LETSENCRYPT_EMAIL=$LETSENCRYPT_EMAIL

# Telegram Bot Settings
BOT_TOKEN=$BOT_TOKEN
OWNER_ID=$OWNER_ID
CHANNEL_ID=$CHANNEL_ID
BACKUP_CHANNEL_ID=$BACKUP_CHANNEL_ID

# Database Settings for Docker
# IMPORTANT: DB_HOST must be 'db' to connect to the Docker container
DB_HOST=db
DB_PORT=3306
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_ROOT_PASSWORD=$DB_ROOT_PASSWORD

# --- START: بخش جدید برای توکن کلادفلر ---
# Cloudflare API Token for DNS-01 Challenge
CLOUDFLARE_API_TOKEN=$CLOUDFLARE_API_TOKEN
# --- END: بخش جدید ---
EOF

echo "✅ .env file created successfully."

# --- Check for existing database ---
if [ ! -z "$(docker volume ls -q -f name=ostadbank_mariadb_data)" ]; then
    echo "ℹ️ An existing database was found and will be reused. Your data is safe."
fi

# --- Build and run the containers using Docker Compose ---
echo "🚀 Building images and running containers..."
# Clean up previous failed SSL attempts if they exist
docker volume rm ostadbank_letsencrypt_data > /dev/null 2>&1
# Pulling images first to ensure we have the latest base images
docker-compose pull
docker-compose up -d --build

# --- Final check ---
echo "⏳ Checking the final status of the containers..."
sleep 15 # Give Traefik some time to request the certificate

if docker-compose ps | grep "Up"; then
    echo -e "\n\n🎉 **Installation completed successfully!**"
    echo "✅ Your bot should now be active and running."
    echo "✅ An SSL certificate will be automatically configured using Cloudflare DNS."
    echo "To view the bot's logs, use the command:"
    echo "   cd /opt/ostadbank && docker-compose logs -f app"
    echo "To view Traefik's logs (for SSL issues), use:"
    echo "   cd /opt/ostadbank && docker-compose logs -f traefik"
    echo -e "\nList of running containers:"
    docker-compose ps
else
    echo -e "\n\n⚠️ **Error running containers!**"
    echo "Docker services could not be started. To investigate the issue, view the logs with:"
    echo "   cd /opt/ostadbank && docker-compose logs"
fi