import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv
from alembic import context

# --- START: Add project root to Python path ---
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
# --- END: Add project root to Python path ---

# this is the Alembic Config object
config = context.config

# Load environment variables from .env file
load_dotenv()

# Set database URL from environment variables for Alembic
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "")
db_host = os.getenv("DB_HOST", "db")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME", "ostadbank_db")
database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
config.set_main_option('sqlalchemy.url', database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your models' Base object for autogenerate support
from models import Base
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()