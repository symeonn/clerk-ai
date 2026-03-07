FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY config-docker.yaml ./config.yaml
COPY credentials.json .
COPY token.json .

# Run the sync script
CMD ["python", "-u", "app/sync.py"]
