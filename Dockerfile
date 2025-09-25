# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    mariadb-client \
    git \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .
# First, uninstall any potentially cached or incorrect version of the library
RUN pip uninstall -y python-telegram-bot

# Now, install all other requirements
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir "fastapi" "python-telegram-bot[job-queue,webhooks]==21.1.1"

# Verify the installed version
RUN pip show python-telegram-bot

# Copy the rest of the application's code into the container
COPY . .

# --- START: NEW LINE ---
# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh
# --- END: NEW LINE ---


# The CMD is now superseded by the entrypoint in docker-compose.yml,
# but we leave it here for clarity.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]