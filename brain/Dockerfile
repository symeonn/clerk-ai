FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir openai python-dotenv pyyaml

# Copy application code
COPY workflow_manager /app/workflow_manager
COPY cognitive_engine /app/cognitive_engine

# Copy configuration
COPY config.yaml /app/config.yaml

# Copy crontab template
COPY cron/crontab /tmp/crontab.template

WORKDIR /app

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
echo "Cron daemon started for BRAIN. Tailing logs..."\n\
tail -f /var/log/cron.log\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

RUN sed -i 's/\r$//' /tmp/crontab.template

CMD ["/entrypoint.sh"]
