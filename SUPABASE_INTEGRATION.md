# Supabase Integration Guide

This guide explains how the KZ Pool Scraper integrates with your existing Supabase database schema used by the Antpool scraper.

## Overview

The KZ Pool Scraper uses a **two-step process**:
1. **Scrape**: Collect data from KZ Pool observer page and save to local SQLite
2. **Upload**: Read from SQLite and upload to Supabase cloud database

This design keeps the scraper simple and reliable, while allowing flexible cloud sync.

---

## Database Schema

The scraper uses your existing Supabase tables:

### 1. `accounts` Table
Stores pool account information.

```sql
- account_name (text, primary key)
- coin_type (text) - Always 'BTC'
- is_active (boolean)
- company (text) - Your company name
- site (text) - Pool site name
- account_type (text) - Set to 'kzpool'
- group_name (text) - Client name
- balance (numeric)
- earn_24_hours (numeric)
- updated_at (timestamp)
```

### 2. `hashrates` Table
Tracks hashrate metrics over time.

```sql
- account_name (text, foreign key)
- hashrate_10m (integer) - in TH/s
- hashrate_1h (integer) - in TH/s
- hashrate_1d (integer) - in TH/s
- worker_count (integer)
- active_workers (integer)
- reject_rate (numeric)
- timestamp (timestamp)
- created_at (timestamp)
```

### 3. `devices` Table
Individual worker/device status.

```sql
- device_id (text, primary key) - Format: "KZ_{account}_{worker}"
- serial_number (text) - Worker name
- account_name (text, foreign key)
- worker_name (text)
- device_type (text) - 'ASIC'
- status (text) - 'online' or 'offline'
- manufacturer (text)
- model (text)
- site (text)
- location (text)
- created_at (timestamp)
- updated_at (timestamp)
```

### 4. `income_tracking` Table
Daily earnings history.

```sql
- account_name (text, foreign key)
- date (text) - Format: MM/DD/YYYY
- btc_amount (numeric)
- usd_value (numeric)
- source (text) - 'KZ Pool'
- transaction_type (text) - 'mining_reward'
- created_at (timestamp)
```

### 5. `alerts` Table
Anomaly and alert logging.

```sql
- account_name (text, foreign key)
- alert_type (text) - 'offline_workers', 'hashrate_drop'
- severity (text) - 'high', 'medium', 'low'
- message (text)
- resolved (boolean)
- created_at (timestamp)
```

---

## Usage

### Step 1: Scrape Data

```bash
python btcpool_scraper.py
```

This will:
- Navigate to the KZ Pool observer page
- Extract summary, workers, and earnings data
- Save to `btcpool_data.db` SQLite database
- Detect anomalies (offline workers, hashrate drops)

### Step 2: Upload to Supabase

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-role-key"

python upload_to_supabase.py \
  --account "KZPool_001" \
  --client "Client Name" \
  --company "BTCDC Builds" \
  --country "Kazakhstan" \
  --site "KZ Main Pool"
```

This will:
- Read latest data from SQLite
- Upsert account information
- Insert hashrate snapshot
- Batch insert 200 worker devices
- Insert daily earnings records
- Log alerts for offline workers

---

## Automation

### Cron Job (Every 10 Minutes)

```bash
*/10 * * * * cd /path/to/scraper && /path/to/run_scraper_and_upload.sh >> /var/log/kzpool.log 2>&1
```

### Combined Script

Create `run_scraper_and_upload.sh`:

```bash
#!/bin/bash
cd /home/ubuntu/KZ_Pool_Scraper
source scraper_env/bin/activate

# Set Supabase credentials
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-role-key"

# Run scraper
python btcpool_scraper.py

# Upload to Supabase
python upload_to_supabase.py \
  --account "KZPool_001" \
  --client "Your Client" \
  --company "BTCDC Builds"
```

---

## Data Flow

```
┌─────────────────┐
│  KZ Pool        │
│  Observer Page  │
└────────┬────────┘
         │ Playwright scrapes
         ▼
┌─────────────────┐
│  SQLite DB      │
│  (Local Cache)  │
└────────┬────────┘
         │ Upload script reads
         ▼
┌─────────────────┐
│  Supabase       │
│  (Cloud DB)     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Dashboard      │
│  Telegram Bot   │
│  Analytics      │
└─────────────────┘
```

---

## Integration with Antpool Scraper

Both scrapers use the **same Supabase schema**, allowing unified dashboards and analytics.

### Querying Across Pools

```sql
-- Get all accounts (Antpool + KZ Pool)
SELECT account_name, account_type, balance, earn_24_hours
FROM accounts
WHERE is_active = true;

-- Compare hashrates
SELECT account_name, hashrate_1d, active_workers
FROM hashrates
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY hashrate_1d DESC;

-- Get all offline devices
SELECT account_name, worker_name, status, location
FROM devices
WHERE status = 'offline';

-- Total earnings by source
SELECT source, SUM(btc_amount) as total_btc
FROM income_tracking
GROUP BY source;
```

### Account Naming Convention

- **Antpool**: `antpool_001`, `antpool_002`, etc.
- **KZ Pool**: `KZPool_001`, `KZPool_002`, etc.

This allows easy filtering and grouping by pool type.

---

## Environment Variables

Required for Supabase upload:

```bash
export SUPABASE_URL="https://idlmoqiftasxyuekeyjm.supabase.co"
export SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Security Note**: Never commit these to Git. Use `.env` files or system environment variables.

---

## Troubleshooting

### Upload Fails with "Invalid API Key"

- Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set correctly
- Verify the service role key (not anon key) is being used

### Devices Not Inserting

- Ensure `device_id` and `serial_number` are provided
- Check for duplicate `device_id` values
- Verify foreign key `account_name` exists in `accounts` table

### No Data in Supabase

- Run scraper first to populate SQLite
- Check SQLite has data: `sqlite3 btcpool_data.db "SELECT COUNT(*) FROM worker_status"`
- Verify upload script can read the database file

### Hashrate Values Incorrect

- Scraper converts PH/s to TH/s automatically
- 1 PH/s = 1000 TH/s
- Check `parse_hashrate()` function if values seem off

---

## Testing

### Test Scraper Only

```bash
python btcpool_scraper.py
sqlite3 btcpool_data.db "SELECT * FROM pool_summary ORDER BY timestamp DESC LIMIT 1"
```

### Test Upload Only

```bash
python upload_to_supabase.py --account "Test" --client "Test" --db "btcpool_data.db"
```

### Verify in Supabase

```bash
curl -X GET "https://your-project.supabase.co/rest/v1/accounts?account_name=eq.Test" \
  -H "apikey: YOUR_KEY" \
  -H "Authorization: Bearer YOUR_KEY"
```

---

## Performance

- **Scrape time**: ~15 seconds
- **Upload time**: ~5 seconds (200 workers)
- **Database size**: ~1.4 MB per day (10-min intervals)
- **Supabase calls**: 5-10 per upload (batched inserts)

---

## Next Steps

1. **Telegram Bot**: Add alerts for offline workers and hashrate drops
2. **Dashboard**: Build unified view of all pools (Antpool + KZ Pool)
3. **Analytics**: Historical trends, earnings projections
4. **Multi-Pool**: Scale to monitor multiple KZ Pool accounts

---

## Support

For issues or questions:
- Check logs: `tail -f /var/log/kzpool.log`
- Review SQLite data: `sqlite3 btcpool_data.db`
- Test Supabase connection: `curl https://your-project.supabase.co/rest/v1/`

