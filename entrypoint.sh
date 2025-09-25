#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready
echo "Waiting for database connection..."
while ! nc -z db 3306; do
  sleep 1
done
echo "Database is ready!"

# Run database migrations automatically
echo "Running database migrations..."
alembic upgrade head

# Start the main application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000