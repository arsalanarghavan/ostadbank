#!/bin/bash

# --- Check for root privileges ---
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ این اسکریپت باید با دسترسی root یا sudo اجرا شود."
  exit 1
fi

echo "🚀 شروع فرآیند نصب تمام خودکار ربات OstadBank..."

# --- Update system and install dependencies ---
echo "🔄 آپدیت کردن پکیج‌ها و نصب پیش‌نیازها (Python, pip, venv, MariaDB)..."
apt-get update > /dev/null 2>&1
apt-get install -y python3 python3-pip python3-venv mariadb-server curl git > /dev/null 2>&1

# --- Configure and Secure MariaDB, and create the database automatically ---
echo "🔐 راه‌اندازی و امن‌سازی خودکار دیتابیس..."

# Generate a strong random password for the database user
DB_PASSWORD=$(openssl rand -base64 16)
DB_NAME="ostadbank_db"
DB_USER="ostadbank_user"

# Run mysql_secure_installation non-interactively
mysql -u root <<MYSQL_SECURE_SCRIPT
ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
MYSQL_SECURE_SCRIPT

# Create database and user with the generated password
mysql -u root -p"${DB_PASSWORD}" <<MYSQL_SCRIPT
CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

echo "✅ دیتابیس و کاربر به صورت خودکار ساخته شدند."

# --- Clone the repository ---
echo "📂 کلون کردن پروژه از گیت‌هاب..."
git clone https://github.com/arsalanarghavan/ostadbank.git /opt/ostadbank
cd /opt/ostadbank

# --- Create .env file from user input ---
echo "📝 لطفا اطلاعات زیر را برای ساخت فایل .env وارد کنید..."
read -p "لطفا توکن ربات تلگرام خود را وارد کنید: " BOT_TOKEN
read -p "لطفا آیدی عددی ادمین اصلی ربات (Owner ID) را وارد کنید: " OWNER_ID
read -p "لطفا آیدی کانال اصلی (برای ارسال تجربیات) را وارد کنید (با -100 شروع می‌شود): " CHANNEL_ID
read -p "لطفا آیدی کانال بکاپ (برای ارسال بکاپ دیتابیس) را وارد کنید (با -100 شروع می‌شود): " BACKUP_CHANNEL_ID

# Create the .env file with automated DB credentials
cat > .env << EOF
BOT_TOKEN=$BOT_TOKEN
OWNER_ID=$OWNER_ID
CHANNEL_ID=$CHANNEL_ID
BACKUP_CHANNEL_ID=$BACKUP_CHANNEL_ID

DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=$DB_NAME
EOF

echo "✅ فایل .env با موفقیت ساخته شد."

# --- Setup Python environment and install packages ---
echo "🐍 ساخت محیط مجازی پایتون و نصب پکیج‌های مورد نیاز..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
deactivate

echo "✅ پکیج‌های پایتون با موفقیت نصب شدند."

# --- Create systemd service for auto-start ---
echo "⚙️ ایجاد سرویس systemd برای اجرای خودکار ربات..."

SERVICE_FILE="/etc/systemd/system/ostadbank.service"

cat > $SERVICE_FILE << EOF
[Unit]
Description=OstadBank Telegram Bot
After=network.target mariadb.service

[Service]
User=root
Group=root
WorkingDirectory=/opt/ostadbank
ExecStart=/opt/ostadbank/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ فایل سرویس با موفقیت ایجاد شد."

# --- Enable and start the service ---
echo "▶️ فعال‌سازی و راه‌اندازی سرویس ربات..."
systemctl daemon-reload
systemctl enable ostadbank.service
systemctl start ostadbank.service

# --- Final check ---
echo "⏳ بررسی وضعیت نهایی سرویس..."
sleep 5
STATUS=$(systemctl is-active ostadbank.service)

if [ "$STATUS" = "active" ]; then
    echo -e "\n\n🎉 **نصب با موفقیت به پایان رسید!**"
    echo "✅ ربات شما اکنون فعال و در حال اجرا است."
    echo "برای مشاهده لاگ‌های ربات می‌توانید از دستور زیر استفاده کنید:"
    echo "   journalctl -u ostadbank -f"
else
    echo -e "\n\n⚠️ **خطا در اجرای ربات!**"
    echo "سرویس ربات نتوانست اجرا شود. برای بررسی مشکل، لاگ‌های آن را با دستور زیر مشاهده کنید:"
    echo "   journalctl -u ostadbank --no-pager"
fi