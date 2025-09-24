# config.py

import os
from dotenv import load_dotenv

load_dotenv()

# --- Critical Configurations ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("ERROR: BOT_TOKEN is not set in environment variables or .env file.")

OWNER_ID_STR = os.getenv("OWNER_ID")
if not OWNER_ID_STR:
    raise ValueError("ERROR: OWNER_ID is not set.")
OWNER_ID = int(OWNER_ID_STR)

CHANNEL_ID_STR = os.getenv("CHANNEL_ID")
if not CHANNEL_ID_STR:
    raise ValueError("ERROR: CHANNEL_ID is not set.")
CHANNEL_ID = int(CHANNEL_ID_STR)

BACKUP_CHANNEL_ID_STR = os.getenv("BACKUP_CHANNEL_ID")
if not BACKUP_CHANNEL_ID_STR:
    raise ValueError("ERROR: BACKUP_CHANNEL_ID is not set in .env file.")
BACKUP_CHANNEL_ID = int(BACKUP_CHANNEL_ID_STR)


# --- Webhook Configurations (Added) ---
DOMAIN_NAME = os.getenv("DOMAIN_NAME", None)
LETSENCRYPT_EMAIL = os.getenv("LETSENCRYPT_EMAIL", None)
# پورت عمومی برای وبهوک را می‌خواند
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 443))


# --- Database Configurations ---
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "db") # Changed for Docker
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "ostadbank_db")

# Ensure database name is provided for production
if not os.getenv("DB_NAME"):
    print("WARNING: DB_NAME is not set, using default 'ostadbank_db'.")


DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"