#!/bin/bash

# --- Check for root privileges ---
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ این اسکریپت باید با دسترسی root یا sudo اجرا شود."
  exit 1
fi

echo "🚀 شروع فرآیند نصب ربات OstadBank..."

# --- Update system and install dependencies ---
echo "🔄 آپدیت کردن پکیج‌ها و نصب پیش‌نیازها (Python, pip, venv, MariaDB)..."
apt-get update
apt-get install -y python3 python3-pip python3-venv mariadb-server curl git

# --- Secure MariaDB installation and create database ---
echo "🔑 امن‌سازی نصب MariaDB..."
mysql_secure_installation

echo "💾 راه‌اندازی دیتابیس..."
read -p "لطفا یک نام برای دیتابیس وارد کنید (مثال: ostadbank_db): " DB_NAME
read -p "لطفا یک نام کاربری برای دیتابیس وارد کنید (مثال: ostadbank_user): " DB_USER
read -sp "لطفا یک رمز عبور قوی برای کاربر دیتابیس وارد کنید: " DB_PASSWORD
echo

# Create database and user
mysql -u root -p <<MYSQL_SCRIPT
CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

echo "✅ دیتابیس و کاربر با موفقیت ساخته شدند."

# --- Clone the repository ---
echo "📂 کلون کردن پروژه از گیت‌هاب..."
git clone https://github.com/arsalanarghavan/ostadbank.git /opt/ostadbank
cd /opt/ostadbank

# --- Create .env file ---
echo "📝 ایجاد فایل .env برای تنظیمات..."
read -p "لطفا توکن ربات تلگرام خود را وارد کنید: " BOT_TOKEN
read -p "لطفا آیدی عددی ادمین اصلی ربات (Owner ID) را وارد کنید: " OWNER_ID
read -p "لطفا آیدی کانال اصلی (برای ارسال تجربیات) را وارد کنید (با -100 شروع می‌شود): " CHANNEL_ID
read -p "لطفا آیدی کانال بکاپ (برای ارسال بکاپ دیتابیس) را وارد کنید (با -100 شروع می‌شود): " BACKUP_CHANNEL_ID

# Create the .env file with the collected data
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
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "✅ پکیج‌های پایتون با موفقیت نصب شدند."

# --- Create systemd service for auto-start ---
echo "⚙️ ایجاد سرویس systemd برای اجرای خودکار ربات..."

SERVICE_FILE="/etc/systemd/system/ostadbank.service"

cat > $SERVICE_FILE << EOF
[Unit]
Description=OstadBank Telegram Bot
After=network.target mysql.service

[Service]
User=root
Group=root
WorkingDirectory=/opt/ostadbank
ExecStart=/opt/ostadbank/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "✅ فایل سرویس با موفقیت در مسیر $SERVICE_FILE ایجاد شد."

# --- Enable and start the service ---
echo "▶️ فعال‌سازی و راه‌اندازی سرویس ربات..."
systemctl daemon-reload
systemctl enable ostadbank.service
systemctl start ostadbank.service

# --- Final check ---
echo "⏳ چند ثانیه صبر برای اطمینان از اجرای سرویس..."
sleep 5
systemctl status ostadbank.service --no-pager

echo -e "\n\n🎉 **نصب با موفقیت به پایان رسید!**"
echo "ربات شما اکنون در حال اجرا است و پس از هر بار ری‌استارت سرور به طور خودکار اجرا خواهد شد."
echo "برای مشاهده لاگ‌های ربات می‌توانید از دستور زیر استفاده کنید:"
echo "journalctl -u ostadbank -f"
echo "برای متوقف کردن ربات از دستور 'systemctl stop ostadbank' و برای اجرای مجدد از 'systemctl start ostadbank' استفاده کنید."