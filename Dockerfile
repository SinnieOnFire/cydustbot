FROM python:3.9-slim

# Set timezone to Cyprus (EEST)
ENV TZ=Asia/Nicosia
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python files
COPY cydust.py .
COPY scraper.py .

# Copy Supervisor configuration
COPY supervisord.conf .

# Run supervisor as the entrypoint
CMD ["supervisord", "-c", "supervisord.conf"]