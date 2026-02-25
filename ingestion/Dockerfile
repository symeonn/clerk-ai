FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app app

# Copy configuration
COPY config-docker.yaml config.yaml

# Copy crontab template
COPY cron/crontab /tmp/crontab.template

WORKDIR /app/app

# Create entrypoint script that injects env vars into crontab
RUN echo '#!/bin/bash\n\
\n\
# Export all environment variables so cron can access them\n\
printenv > /etc/environment\n\
\n\
# Install cron job for root user\n\
crontab /tmp/crontab.template\n\
\n\
# Prepare log file\n\
touch /var/log/cron.log\n\
\n\
# Start cron daemon\n\
cron\n\
echo "Cron daemon started for INGESTION. Tailing logs..."\n\
tail -f /var/log/cron.log\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh


CMD ["/entrypoint.sh"]