#!/bin/bash

# مسیر پروژه
PROJECT_DIR="/opt/ostadbank"
GIT_REPO_URL="https://github.com/arsalanarghavan/ostadbank.git"

# بررسی دسترسی root
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ این اسکریپت باید با دسترسی root یا sudo اجرا شود."
  exit 1
fi

echo "🚀 شروع فرآیند دانلود/آپدیت ربات..."

# بررسی وجود پوشه پروژه
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📂 پوشه پروژه یافت نشد. در حال کلون کردن از گیت‌هاب..."
    git clone $GIT_REPO_URL $PROJECT_DIR
    if [ $? -ne 0 ]; then
        echo "❌ خطا در کلون کردن پروژه."
        exit 1
    fi
    echo "✅ پروژه با موفقیت کلون شد."
else
    echo "🔄 پوشه پروژه وجود دارد. در حال آپدیت کردن با git pull..."
    cd $PROJECT_DIR
    git pull origin main # یا هر شاخه دیگری که مد نظرتان است
    if [ $? -ne 0 ]; then
        echo "⚠️ هشداری در هنگام git pull رخ داد (ممکن است به دلیل وجود تغییرات локальный باشد). تلاش برای ریست کردن..."
        git fetch --all
        git reset --hard origin/main
    fi
    echo "✅ پروژه با موفقیت آپدیت شد."
fi

# نصب یا آپدیت پکیج‌های پایتون
echo "🐍 آپدیت کردن پکیج‌های مورد نیاز..."
cd $PROJECT_DIR
source venv/bin/activate
pip install -r requirements.txt
deactivate

# ری‌استارت کردن سرویس ربات
echo "⚙️ راه‌اندازی مجدد سرویس ربات..."
systemctl restart ostadbank.service

# بررسی وضعیت نهایی سرویس
echo "⏳ بررسی وضعیت نهایی سرویس..."
sleep 3
STATUS=$(systemctl is-active ostadbank.service)

if [ "$STATUS" = "active" ]; then
    echo -e "\n🎉 **عملیات با موفقیت انجام شد!**"
    echo "✅ ربات شما اکنون با آخرین تغییرات در حال اجرا است."
else
    echo -e "\n\n⚠️ **خطا در اجرای ربات!**"
    echo "سرویس ربات نتوانست اجرا شود. لاگ‌ها را بررسی کنید:"
    echo "   journalctl -u ostadbank -f"
fi