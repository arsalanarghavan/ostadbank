#!/bin/bash

# --- Check for root privileges ---
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ This script must be run with root or sudo privileges."
  exit 1
fi

# --- Navigate to the project directory ---
PROJECT_DIR="/opt/ostadbank"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory not found at $PROJECT_DIR. Please run the install script first."
    exit 1
fi
cd $PROJECT_DIR

echo "🚀 Starting the bot update process..."

# --- Fetch the latest code from GitHub ---
echo "🔄 Pulling the latest changes from the 'main' branch..."
git fetch --all
git reset --hard origin/main # This command discards any local changes and ensures a clean update
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Failed to pull updates from GitHub. Please check for errors."
    exit 1
fi
echo "✅ Code updated successfully."

# --- Rebuild and restart the Docker containers ---
echo "⚙️ Rebuilding and restarting the Docker containers..."
docker-compose up -d --build
if [ $? -ne 0 ]; then
    echo "❌ Failed to rebuild or start the containers. Please check Docker logs."
    exit 1
fi

# --- Final check ---
echo "⏳ Checking the final status of the containers..."
sleep 5

if docker-compose ps | grep "Up"; then
    echo -e "\n\n🎉 **Update completed successfully!**"
    echo "✅ Your bot is now running with the latest code."
    echo "To view the bot's logs, use the command:"
    echo "   cd /opt/ostadbank && docker-compose logs -f app"
else
    echo -e "\n\n⚠️ **Error running containers after update!**"
    echo "To investigate the issue, view the logs with:"
    echo "   cd /opt/ostadbank && docker-compose logs"
fi