#!/bin/bash
#
# KZ Pool Scraper - Combined Scrape and Upload Script
# Runs scraper then uploads to Supabase
#

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source scraper_env/bin/activate 2>/dev/null || source ../scraper_env/bin/activate

# Set Supabase credentials (replace with your values or use environment variables)
export SUPABASE_URL="${SUPABASE_URL:-https://your-project.supabase.co}"
export SUPABASE_SERVICE_KEY="${SUPABASE_SERVICE_KEY:-your-service-role-key}"

# Pool configuration (modify these for your setup)
ACCOUNT_NAME="${ACCOUNT_NAME:-KZPool_001}"
CLIENT_NAME="${CLIENT_NAME:-Client Name}"
COMPANY="${COMPANY:-BTCDC Builds}"
COUNTRY="${COUNTRY:-Kazakhstan}"
SITE="${SITE:-KZ Pool}"
DB_PATH="${DB_PATH:-btcpool_data.db}"

# Log file
LOG_FILE="${LOG_FILE:-/var/log/kzpool_scraper.log}"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================="
log "Starting KZ Pool Scraper"
log "========================================="

# Step 1: Run scraper
log "Step 1: Scraping KZ Pool data..."
if python btcpool_scraper.py >> "$LOG_FILE" 2>&1; then
    log "✓ Scraping completed successfully"
else
    log "✗ Scraping failed with exit code $?"
    exit 1
fi

# Step 2: Upload to Supabase
log "Step 2: Uploading to Supabase..."
if python upload_to_supabase.py \
    --account "$ACCOUNT_NAME" \
    --client "$CLIENT_NAME" \
    --company "$COMPANY" \
    --country "$COUNTRY" \
    --site "$SITE" \
    --db "$DB_PATH" >> "$LOG_FILE" 2>&1; then
    log "✓ Upload completed successfully"
else
    log "✗ Upload failed with exit code $?"
    exit 1
fi

log "========================================="
log "KZ Pool Scraper completed successfully"
log "========================================="
