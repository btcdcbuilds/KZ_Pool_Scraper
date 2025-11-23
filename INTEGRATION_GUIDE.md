# Integration Guide

How to integrate KZ Pool Scraper with other mining pool scrapers and monitoring systems.

---

## Overview

The KZ Pool Scraper is designed to work alongside other pool scrapers (Antpool, F2Pool, etc.) by sharing a common database schema with client/company metadata tracking.

---

## Integration Patterns

### Pattern 1: Shared Database

Multiple scrapers write to the same SQLite database, using `pool_id` as the linking key.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  KZ Pool        │     │  Antpool        │     │  F2Pool         │
│  Scraper        │────▶│  Scraper        │────▶│  Scraper        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │  Shared SQLite  │
                         │   Database      │
                         └─────────────────┘
```

**Advantages:**
- Simple setup
- No API needed
- Direct SQL queries
- Real-time data

**Disadvantages:**
- File locking issues if not careful
- Single point of failure
- Limited scalability

---

### Pattern 2: Supabase Cloud Database

All scrapers sync to a cloud PostgreSQL database via Supabase.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  KZ Pool        │     │  Antpool        │     │  F2Pool         │
│  Scraper        │     │  Scraper        │     │  Scraper        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │   Local SQLite        │                       │
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │   Supabase      │
                         │  (PostgreSQL)   │
                         └─────────────────┘
```

**Advantages:**
- Scalable
- Remote access
- Built-in API
- Real-time subscriptions
- Row Level Security

**Disadvantages:**
- Requires internet
- Additional cost
- More complex setup

---

### Pattern 3: API Gateway

Each scraper has its own database, exposed via REST API, with a central aggregator.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  KZ Pool        │     │  Antpool        │     │  F2Pool         │
│  Scraper + API  │     │  Scraper + API  │     │  Scraper + API  │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │   API Gateway   │
                         │   / Dashboard   │
                         └─────────────────┘
```

**Advantages:**
- Decoupled services
- Independent scaling
- Service isolation
- Easy to add/remove scrapers

**Disadvantages:**
- More infrastructure
- Network overhead
- Complex deployment

---

## Implementation Examples

### Example 1: Shared SQLite Database

#### Docker Compose Setup

```yaml
version: '3.8'

services:
  kz-pool-scraper:
    image: btcdcbuilds/kz-pool-scraper
    volumes:
      - shared-data:/data
    environment:
      - OBSERVER_URL=https://btcpool.kz/observer-link/YOUR_ID
      - POOL_ID=kzpool_001
      - CLIENT_NAME=Client Company Ltd
      - COUNTRY=Kazakhstan
      - COMPANY=BTCDC Builds
  
  antpool-scraper:
    image: btcdcbuilds/antpool-scraper
    volumes:
      - shared-data:/data
    environment:
      - API_KEY=your_antpool_key
      - POOL_ID=antpool_001
      - CLIENT_NAME=Client Company Ltd
      - COUNTRY=China
      - COMPANY=BTCDC Builds
  
  dashboard:
    image: btcdcbuilds/mining-dashboard
    volumes:
      - shared-data:/data:ro  # Read-only
    ports:
      - "8080:8080"

volumes:
  shared-data:
```

#### Query All Pools for a Client

```python
import sqlite3

conn = sqlite3.connect('/data/btcpool_data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all pools for a client
cursor.execute('''
    SELECT 
        pm.pool_id,
        pm.pool_name,
        pm.country,
        ps.current_hashrate,
        ps.online_workers,
        ps.offline_workers,
        ps.balance
    FROM pool_metadata pm
    LEFT JOIN pool_summary ps ON pm.pool_id = ps.pool_id
    WHERE pm.client_name = ?
      AND ps.timestamp = (
          SELECT MAX(timestamp) 
          FROM pool_summary 
          WHERE pool_id = pm.pool_id
      )
    ORDER BY pm.pool_id
''', ('Client Company Ltd',))

pools = [dict(row) for row in cursor.fetchall()]

for pool in pools:
    print(f"{pool['pool_name']}: {pool['current_hashrate']} - {pool['online_workers']} online")
```

---

### Example 2: Supabase Integration

#### Setup Supabase Tables

```sql
-- Create tables in Supabase (PostgreSQL)
CREATE TABLE pool_metadata (
    pool_id TEXT PRIMARY KEY,
    pool_name TEXT,
    observer_url TEXT,
    client_name TEXT,
    country TEXT,
    company TEXT,
    location TEXT,
    contact_email TEXT,
    tags JSONB,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pool_summary (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    pool_id TEXT REFERENCES pool_metadata(pool_id),
    observer_url TEXT,
    current_hashrate TEXT,
    avg_hashrate_24h TEXT,
    online_workers INTEGER,
    offline_workers INTEGER,
    balance TEXT,
    last_income TEXT
);

CREATE INDEX idx_pool_summary_timestamp ON pool_summary(timestamp);
CREATE INDEX idx_pool_summary_pool_id ON pool_summary(pool_id);

-- Enable Row Level Security
ALTER TABLE pool_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_summary ENABLE ROW LEVEL SECURITY;

-- Create policies (example: read-only for anon users)
CREATE POLICY "Allow read access" ON pool_metadata
    FOR SELECT USING (true);

CREATE POLICY "Allow read access" ON pool_summary
    FOR SELECT USING (true);
```

#### Python Sync Script

```python
from supabase import create_client, Client
import sqlite3
import os

# Initialize Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# Read from local SQLite
conn = sqlite3.connect('/data/btcpool_data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get latest pool summary
cursor.execute('''
    SELECT * FROM pool_summary 
    WHERE timestamp > datetime('now', '-15 minutes')
''')

records = [dict(row) for row in cursor.fetchall()]

# Upload to Supabase
for record in records:
    supabase.table('pool_summary').insert(record).execute()

print(f"Synced {len(records)} records to Supabase")
```

---

### Example 3: Cross-Scraper Queries

#### Get Total Hashrate Across All Pools

```sql
SELECT 
    pm.client_name,
    pm.company,
    COUNT(DISTINCT pm.pool_id) as total_pools,
    SUM(ps.online_workers) as total_workers,
    SUM(ps.offline_workers) as total_offline
FROM pool_metadata pm
JOIN pool_summary ps ON pm.pool_id = ps.pool_id
WHERE ps.timestamp = (
    SELECT MAX(timestamp) 
    FROM pool_summary 
    WHERE pool_id = pm.pool_id
)
GROUP BY pm.client_name, pm.company;
```

#### Get All Offline Workers Across Pools

```sql
SELECT 
    pm.pool_name,
    pm.country,
    ws.worker_name,
    ws.status,
    ws.last_exchange_time
FROM worker_status ws
JOIN pool_metadata pm ON ws.pool_id = pm.pool_id
WHERE ws.status = 'OFFLINE'
  AND ws.timestamp = (
      SELECT MAX(timestamp) 
      FROM worker_status 
      WHERE pool_id = ws.pool_id
  )
ORDER BY pm.pool_name, ws.worker_name;
```

#### Daily Earnings by Country

```sql
SELECT 
    pm.country,
    de.date,
    SUM(CAST(de.total_income AS REAL)) as total_btc
FROM daily_earnings de
JOIN pool_metadata pm ON de.pool_id = pm.pool_id
WHERE de.date >= date('now', '-30 days')
GROUP BY pm.country, de.date
ORDER BY de.date DESC, pm.country;
```

---

## Database Schema Mapping

### Standard Fields Across All Scrapers

All scrapers should implement these standard fields in `pool_metadata`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pool_id` | TEXT | Yes | Unique identifier (format: `<pool>_<number>`) |
| `pool_name` | TEXT | Yes | Human-readable name |
| `observer_url` | TEXT | Yes | Pool monitoring URL |
| `client_name` | TEXT | Yes | Client company name |
| `country` | TEXT | Yes | Country of operation |
| `company` | TEXT | Yes | Operating company |
| `location` | TEXT | No | City/specific location |
| `contact_email` | TEXT | No | Contact email |
| `tags` | TEXT/JSONB | No | JSON array of tags |
| `active` | INTEGER/BOOLEAN | Yes | Active status |

### Pool ID Naming Convention

```
<pool_type>_<sequential_number>

Examples:
- kzpool_001, kzpool_002, ...
- antpool_001, antpool_002, ...
- f2pool_001, f2pool_002, ...
- custom_001, custom_002, ...
```

### Timestamp Format

All timestamps should be in **UTC** and use ISO 8601 format:
- SQLite: `DATETIME DEFAULT CURRENT_TIMESTAMP`
- PostgreSQL: `TIMESTAMPTZ DEFAULT NOW()`
- Format: `2025-11-23 04:47:34` or `2025-11-23T04:47:34Z`

---

## Antpool Integration Example

### Antpool Scraper Schema

```sql
-- Antpool uses same base tables
CREATE TABLE pool_metadata (...);  -- Same as KZ Pool

-- Antpool-specific summary table
CREATE TABLE pool_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    pool_id TEXT,
    observer_url TEXT,  -- Antpool API endpoint
    current_hashrate TEXT,
    avg_hashrate_24h TEXT,
    online_workers INTEGER,
    offline_workers INTEGER,
    balance TEXT,
    last_income TEXT,
    -- Antpool-specific fields
    pool_luck TEXT,
    network_difficulty TEXT,
    estimated_earnings TEXT,
    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
);
```

### Unified Dashboard Query

```python
def get_all_pools_status():
    """Get status from all pool types"""
    conn = sqlite3.connect('/data/btcpool_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            pm.pool_id,
            pm.pool_name,
            pm.client_name,
            pm.country,
            CASE 
                WHEN pm.pool_id LIKE 'kzpool_%' THEN 'KZ Pool'
                WHEN pm.pool_id LIKE 'antpool_%' THEN 'Antpool'
                WHEN pm.pool_id LIKE 'f2pool_%' THEN 'F2Pool'
                ELSE 'Other'
            END as pool_type,
            ps.current_hashrate,
            ps.online_workers,
            ps.offline_workers,
            ps.balance,
            ps.timestamp
        FROM pool_metadata pm
        LEFT JOIN pool_summary ps ON pm.pool_id = ps.pool_id
        WHERE pm.active = 1
          AND (ps.timestamp IS NULL OR ps.timestamp = (
              SELECT MAX(timestamp) 
              FROM pool_summary 
              WHERE pool_id = pm.pool_id
          ))
        ORDER BY pm.client_name, pool_type, pm.pool_name
    ''')
    
    return [dict(row) for row in cursor.fetchall()]
```

---

## Migration from Existing Systems

### Step 1: Export Existing Data

```python
# Export from your existing Antpool scraper
import sqlite3
import json

conn = sqlite3.connect('antpool_data.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM pools')
pools = cursor.fetchall()

# Convert to new format
for pool in pools:
    new_pool = {
        'pool_id': f'antpool_{pool[0]:03d}',
        'pool_name': pool[1],
        'observer_url': pool[2],
        'client_name': pool[3],
        'country': pool[4],
        'company': pool[5],
        # ... map other fields
    }
    
    # Insert into new database
    # ...
```

### Step 2: Migrate Historical Data

```python
# Migrate historical summary data
cursor.execute('''
    SELECT * FROM pool_summary 
    WHERE timestamp > datetime('now', '-90 days')
''')

historical_data = cursor.fetchall()

# Insert into new database with updated pool_id
# ...
```

### Step 3: Update Scraper Code

```python
# Old code
def save_data(data):
    conn = sqlite3.connect('antpool_data.db')
    # ...

# New code
def save_data(data):
    conn = sqlite3.connect('/data/btcpool_data.db')  # Shared database
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO pool_summary 
        (pool_id, observer_url, current_hashrate, ...)
        VALUES (?, ?, ?, ...)
    ''', (self.pool_id, self.observer_url, data['hashrate'], ...))
```

---

## API Endpoints (Optional)

If you want to expose data via REST API:

### FastAPI Example

```python
from fastapi import FastAPI
import sqlite3

app = FastAPI()

@app.get("/api/pools")
def get_pools(client: str = None):
    """Get all pools, optionally filtered by client"""
    conn = sqlite3.connect('/data/btcpool_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM pool_metadata WHERE active = 1'
    params = []
    
    if client:
        query += ' AND client_name = ?'
        params.append(client)
    
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

@app.get("/api/pools/{pool_id}/status")
def get_pool_status(pool_id: str):
    """Get latest status for a pool"""
    conn = sqlite3.connect('/data/btcpool_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM pool_summary 
        WHERE pool_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (pool_id,))
    
    return dict(cursor.fetchone())

@app.get("/api/clients/{client_name}/summary")
def get_client_summary(client_name: str):
    """Get summary for all pools of a client"""
    conn = sqlite3.connect('/data/btcpool_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            pm.pool_id,
            pm.pool_name,
            pm.country,
            ps.current_hashrate,
            ps.online_workers,
            ps.offline_workers,
            ps.balance
        FROM pool_metadata pm
        LEFT JOIN pool_summary ps ON pm.pool_id = ps.pool_id
        WHERE pm.client_name = ?
          AND ps.timestamp = (
              SELECT MAX(timestamp) 
              FROM pool_summary 
              WHERE pool_id = pm.pool_id
          )
    ''', (client_name,))
    
    return [dict(row) for row in cursor.fetchall()]
```

---

## Testing Integration

### Test Shared Database

```bash
# Terminal 1: Start KZ Pool scraper
cd kz-pool-scraper
docker-compose up

# Terminal 2: Start Antpool scraper
cd antpool-scraper
docker-compose up

# Terminal 3: Query shared database
sqlite3 data/btcpool_data.db "
    SELECT pool_id, pool_name, client_name 
    FROM pool_metadata;
"
```

### Test Cross-Scraper Queries

```bash
# Get all pools for a client
sqlite3 data/btcpool_data.db "
    SELECT pm.pool_name, ps.current_hashrate, ps.online_workers
    FROM pool_metadata pm
    JOIN pool_summary ps ON pm.pool_id = ps.pool_id
    WHERE pm.client_name = 'Client Company Ltd'
      AND ps.timestamp = (
          SELECT MAX(timestamp) 
          FROM pool_summary 
          WHERE pool_id = pm.pool_id
      );
"
```

---

## Best Practices

### 1. Use Consistent Pool IDs

```python
# Good
pool_id = f"{pool_type}_{number:03d}"  # antpool_001

# Bad
pool_id = "pool1"  # Ambiguous
```

### 2. Always Set Metadata

```python
# Always populate client/company fields
cursor.execute('''
    INSERT INTO pool_metadata 
    (pool_id, pool_name, client_name, country, company, ...)
    VALUES (?, ?, ?, ?, ?, ...)
''', (pool_id, name, client, country, company, ...))
```

### 3. Use Foreign Keys

```sql
CREATE TABLE pool_summary (
    ...
    pool_id TEXT,
    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
);
```

### 4. Index Common Queries

```sql
CREATE INDEX idx_pool_metadata_client ON pool_metadata(client_name);
CREATE INDEX idx_pool_metadata_company ON pool_metadata(company);
CREATE INDEX idx_pool_summary_timestamp ON pool_summary(timestamp);
```

### 5. Handle Time Zones

```python
from datetime import datetime, timezone

# Always use UTC
timestamp = datetime.now(timezone.utc).isoformat()
```

---

## Troubleshooting

### Database Locked Error

```python
# Use WAL mode for better concurrency
conn = sqlite3.connect('/data/btcpool_data.db')
conn.execute('PRAGMA journal_mode=WAL')
```

### Duplicate Pool IDs

```python
# Check for conflicts before inserting
cursor.execute('SELECT pool_id FROM pool_metadata WHERE pool_id = ?', (pool_id,))
if cursor.fetchone():
    print(f"Pool ID already exists: {pool_id}")
    # Use a different ID or update existing
```

### Missing Foreign Key Data

```python
# Always insert metadata first
cursor.execute('INSERT INTO pool_metadata (...) VALUES (...)')
cursor.execute('INSERT INTO pool_summary (...) VALUES (...)')
```

---

## Support

For integration help:
- GitHub Issues: https://github.com/btcdcbuilds/KZ_Pool_Scraper/issues
- Email: support@btcdcbuilds.com
- Documentation: https://github.com/btcdcbuilds/KZ_Pool_Scraper/wiki

---

**Version**: 1.0  
**Last Updated**: 2025-11-23  
**Maintained by**: BTCDC Builds
