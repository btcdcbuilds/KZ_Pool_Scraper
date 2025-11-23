# BTC Pool Scraper - Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    sqlite3 \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application files
COPY btcpool_scraper_v2.py .
COPY view_data.py .
COPY supabase_uploader.py .

# Create data directory
RUN mkdir -p /data

# Environment variables
ENV OBSERVER_URL="https://btcpool.kz/observer-link/4828a3fecdaa48eebfa475021b4e8d8d"
ENV DB_PATH="/data/btcpool_data.db"
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "import sqlite3; conn = sqlite3.connect('${DB_PATH}'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM pool_summary WHERE timestamp > datetime(\"now\", \"-15 minutes\")'); result = cursor.fetchone()[0]; exit(0 if result > 0 else 1)"

# Run the scraper
CMD ["python", "-u", "btcpool_scraper_v2.py"]
