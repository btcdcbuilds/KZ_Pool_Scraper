# Database Schema Documentation

Complete database schema for KZ Pool Scraper with cross-repository integration support.

---

## Overview

The database uses **SQLite** with a normalized schema designed for:
- Multi-pool monitoring
- Client/company metadata tracking
- Cross-repository integration
- Time-series data storage
- Foreign key relationships

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│   pool_metadata     │
│  (Client/Company)   │
└──────────┬──────────┘
           │
           │ pool_id (FK)
           │
    ┌──────┴──────┬──────────┬──────────┐
    │             │          │          │
┌───▼────────┐ ┌──▼──────┐ ┌▼────────┐ ┌▼──────────┐
│pool_summary│ │worker_  │ │daily_   │ │anomaly_   │
│            │ │status   │ │earnings │ │log        │
└────────────┘ └─────────┘ └─────────┘ └───────────┘
```

---

## Table Definitions

### 1. `pool_metadata`

**Purpose**: Store client and company information for each pool.

**Schema**:

```sql
CREATE TABLE pool_metadata (
    pool_id TEXT PRIMARY KEY,
    pool_name TEXT,
    observer_url TEXT,
    client_name TEXT,
    country TEXT,
    company TEXT,
    location TEXT,
    contact_email TEXT,
    tags TEXT,
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `pool_id` | TEXT | PRIMARY KEY | Unique identifier (e.g., "pool_001") |
| `pool_name` | TEXT | | Human-readable name |
| `observer_url` | TEXT | | BTC Pool observer link |
| `client_name` | TEXT | | Client company name |
| `country` | TEXT | | Country of operation |
| `company` | TEXT | | Operating company |
| `location` | TEXT | | City or specific location |
| `contact_email` | TEXT | | Contact email address |
| `tags` | TEXT | | JSON array of tags |
| `active` | INTEGER | DEFAULT 1 | 1=active, 0=inactive |
| `created_at` | DATETIME | AUTO | Record creation time |
| `updated_at` | DATETIME | AUTO | Last update time |

**Example Data**:

```sql
INSERT INTO pool_metadata VALUES (
    'pool_001',
    'Main KZ Pool',
    'https://btcpool.kz/observer-link/4828a3fecdaa48eebfa475021b4e8d8d',
    'Client Company Ltd',
    'Kazakhstan',
    'BTCDC Builds',
    'Almaty',
    'client@example.com',
    '["production","high-priority"]',
    1,
    '2025-11-23 00:00:00',
    '2025-11-23 00:00:00'
);
```

**Indexes**: None (PRIMARY KEY is indexed by default)

---

### 2. `pool_summary`

**Purpose**: Store operational metrics collected every 10 minutes.

**Schema**:

```sql
CREATE TABLE pool_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    pool_id TEXT,
    observer_url TEXT,
    current_hashrate TEXT,
    avg_hashrate_24h TEXT,
    online_workers INTEGER,
    offline_workers INTEGER,
    balance TEXT,
    last_income TEXT,
    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
);

CREATE INDEX idx_pool_summary_timestamp ON pool_summary(timestamp);
CREATE INDEX idx_pool_summary_pool_id ON pool_summary(pool_id);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTO | Unique record ID |
| `timestamp` | DATETIME | AUTO | Collection time (UTC) |
| `pool_id` | TEXT | FOREIGN KEY | Links to pool_metadata |
| `observer_url` | TEXT | | Observer link |
| `current_hashrate` | TEXT | | Current pool hashrate (e.g., "37.405 PH/s") |
| `avg_hashrate_24h` | TEXT | | 24-hour average hashrate |
| `online_workers` | INTEGER | | Number of online devices |
| `offline_workers` | INTEGER | | Number of offline devices |
| `balance` | TEXT | | Current BTC balance |
| `last_income` | TEXT | | Last payment received |

**Example Data**:

```sql
INSERT INTO pool_summary VALUES (
    1,
    '2025-11-23 04:47:34',
    'pool_001',
    'https://btcpool.kz/observer-link/4828a3fecdaa48eebfa475021b4e8d8d',
    '37.405 PH/s',
    '38.210 PH/s',
    200,
    2,
    '0.01864218BTC',
    '0.01570138BTC'
);
```

**Indexes**:
- `idx_pool_summary_timestamp` - For time-based queries
- `idx_pool_summary_pool_id` - For pool-specific queries

**Typical Queries**:

```sql
-- Latest status for all pools
SELECT ps.*, pm.client_name, pm.country
FROM pool_summary ps
JOIN pool_metadata pm ON ps.pool_id = pm.pool_id
WHERE ps.timestamp = (
    SELECT MAX(timestamp) 
    FROM pool_summary 
    WHERE pool_id = ps.pool_id
);

-- Hashrate trend for last 24 hours
SELECT timestamp, current_hashrate, online_workers
FROM pool_summary
WHERE pool_id = 'pool_001'
  AND timestamp > datetime('now', '-24 hours')
ORDER BY timestamp DESC;
```

---

### 3. `worker_status`

**Purpose**: Track individual device status every 10 minutes.

**Schema**:

```sql
CREATE TABLE worker_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    pool_id TEXT,
    observer_url TEXT,
    worker_name TEXT,
    status TEXT,
    hashrate_10m TEXT,
    hashrate_1h TEXT,
    hashrate_24h TEXT,
    last_exchange_time TEXT,
    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
);

CREATE INDEX idx_worker_status_timestamp ON worker_status(timestamp);
CREATE INDEX idx_worker_status_pool_id ON worker_status(pool_id);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTO | Unique record ID |
| `timestamp` | DATETIME | AUTO | Collection time (UTC) |
| `pool_id` | TEXT | FOREIGN KEY | Links to pool_metadata |
| `observer_url` | TEXT | | Observer link |
| `worker_name` | TEXT | | Device identifier |
| `status` | TEXT | | "ONLINE" or "OFFLINE" |
| `hashrate_10m` | TEXT | | 10-minute hashrate |
| `hashrate_1h` | TEXT | | 1-hour hashrate |
| `hashrate_24h` | TEXT | | 24-hour hashrate |
| `last_exchange_time` | TEXT | | Last communication time |

**Example Data**:

```sql
INSERT INTO worker_status VALUES (
    1,
    '2025-11-23 04:47:34',
    'pool_001',
    'https://btcpool.kz/observer-link/4828a3fecdaa48eebfa475021b4e8d8d',
    '139x17.10X16X139X17',
    'ONLINE',
    '187.650 TH/s',
    '177.020 TH/s',
    '194.180 TH/s',
    '2025-11-23 04:45:00'
);
```

**Indexes**:
- `idx_worker_status_timestamp` - For time-based queries
- `idx_worker_status_pool_id` - For pool-specific queries

**Typical Queries**:

```sql
-- Current status of all workers
SELECT worker_name, status, hashrate_24h
FROM worker_status
WHERE pool_id = 'pool_001'
  AND timestamp = (
      SELECT MAX(timestamp) 
      FROM worker_status 
      WHERE pool_id = 'pool_001'
  )
ORDER BY status, worker_name;

-- Offline workers
SELECT worker_name, last_exchange_time
FROM worker_status
WHERE pool_id = 'pool_001'
  AND status = 'OFFLINE'
  AND timestamp = (SELECT MAX(timestamp) FROM worker_status WHERE pool_id = 'pool_001');

-- Worker performance over time
SELECT timestamp, hashrate_10m, hashrate_1h, hashrate_24h
FROM worker_status
WHERE pool_id = 'pool_001'
  AND worker_name = '139x17.10X16X139X17'
  AND timestamp > datetime('now', '-24 hours')
ORDER BY timestamp DESC;
```

---

### 4. `daily_earnings`

**Purpose**: Store daily statistics (one record per day per pool).

**Schema**:

```sql
CREATE TABLE daily_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pool_id TEXT,
    observer_url TEXT,
    date TEXT,
    total_income TEXT,
    hashrate TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pool_id, date),
    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
);

CREATE INDEX idx_daily_earnings_pool_id ON daily_earnings(pool_id);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTO | Unique record ID |
| `pool_id` | TEXT | FOREIGN KEY | Links to pool_metadata |
| `observer_url` | TEXT | | Observer link |
| `date` | TEXT | UNIQUE with pool_id | Earnings date (MM/DD/YYYY) |
| `total_income` | TEXT | | BTC earned that day |
| `hashrate` | TEXT | | Average hashrate for the day |
| `recorded_at` | DATETIME | AUTO | When record was created |

**Unique Constraint**: `(pool_id, date)` - Prevents duplicate daily records

**Example Data**:

```sql
INSERT INTO daily_earnings VALUES (
    1,
    'pool_001',
    'https://btcpool.kz/observer-link/4828a3fecdaa48eebfa475021b4e8d8d',
    '11/22/2025 12:00:00 AM',
    '0.01570138',
    '38.187 PH/s',
    '2025-11-23 04:47:34'
);
```

**Indexes**:
- `idx_daily_earnings_pool_id` - For pool-specific queries

**Typical Queries**:

```sql
-- Last 30 days earnings
SELECT date, total_income, hashrate
FROM daily_earnings
WHERE pool_id = 'pool_001'
ORDER BY date DESC
LIMIT 30;

-- Total earnings for a client
SELECT pm.client_name, SUM(CAST(de.total_income AS REAL)) as total_btc
FROM daily_earnings de
JOIN pool_metadata pm ON de.pool_id = pm.pool_id
WHERE pm.client_name = 'Client Company Ltd'
GROUP BY pm.client_name;

-- Monthly earnings summary
SELECT 
    strftime('%Y-%m', date) as month,
    COUNT(*) as days,
    SUM(CAST(total_income AS REAL)) as total_btc
FROM daily_earnings
WHERE pool_id = 'pool_001'
GROUP BY month
ORDER BY month DESC;
```

---

### 5. `anomaly_log`

**Purpose**: Track detected issues and anomalies.

**Schema**:

```sql
CREATE TABLE anomaly_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    pool_id TEXT,
    observer_url TEXT,
    anomaly_type TEXT,
    description TEXT,
    severity TEXT,
    resolved INTEGER DEFAULT 0,
    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
);

CREATE INDEX idx_anomaly_log_pool_id ON anomaly_log(pool_id);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTO | Unique record ID |
| `timestamp` | DATETIME | AUTO | Detection time (UTC) |
| `pool_id` | TEXT | FOREIGN KEY | Links to pool_metadata |
| `observer_url` | TEXT | | Observer link |
| `anomaly_type` | TEXT | | Type of anomaly |
| `description` | TEXT | | Detailed description |
| `severity` | TEXT | | "HIGH", "MEDIUM", or "LOW" |
| `resolved` | INTEGER | DEFAULT 0 | 0=open, 1=resolved |

**Anomaly Types**:
- `OFFLINE_WORKERS` - Devices went offline
- `HASHRATE_DROP` - Significant hashrate decrease
- `BALANCE_ANOMALY` - Unexpected balance change
- `PAYMENT_DELAY` - Expected payment not received

**Severity Levels**:
- `HIGH` - Requires immediate attention (>5 offline workers, >30% hashrate drop)
- `MEDIUM` - Should be investigated (1-5 offline workers, 20-30% hashrate drop)
- `LOW` - Informational only

**Example Data**:

```sql
INSERT INTO anomaly_log VALUES (
    1,
    '2025-11-23 04:47:34',
    'pool_001',
    'https://btcpool.kz/observer-link/4828a3fecdaa48eebfa475021b4e8d8d',
    'OFFLINE_WORKERS',
    '2 worker(s) offline: 139x17.10X16X139X17, 139x18.10X16X139X18',
    'MEDIUM',
    0
);
```

**Indexes**:
- `idx_anomaly_log_pool_id` - For pool-specific queries

**Typical Queries**:

```sql
-- Unresolved anomalies
SELECT timestamp, anomaly_type, description, severity
FROM anomaly_log
WHERE pool_id = 'pool_001'
  AND resolved = 0
ORDER BY severity DESC, timestamp DESC;

-- Anomaly history for last 7 days
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_anomalies,
    SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) as high_severity,
    SUM(CASE WHEN severity = 'MEDIUM' THEN 1 ELSE 0 END) as medium_severity
FROM anomaly_log
WHERE pool_id = 'pool_001'
  AND timestamp > datetime('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Mark anomaly as resolved
UPDATE anomaly_log
SET resolved = 1
WHERE id = 1;
```

---

## Cross-Repository Integration

### Shared Database Pattern

Multiple scrapers can share the same database by using `pool_id` as a foreign key.

**Example**: Integrating with Antpool scraper

```sql
-- Antpool scraper creates its own metadata
INSERT INTO pool_metadata VALUES (
    'antpool_001',
    'Antpool Main',
    'https://antpool.com/account/overview',
    'Client Company Ltd',  -- Same client
    'China',
    'BTCDC Builds',        -- Same company
    'Beijing',
    'client@example.com',
    '["antpool","production"]',
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Query all pools for a client
SELECT 
    pm.pool_id,
    pm.pool_name,
    pm.country,
    ps.current_hashrate,
    ps.online_workers
FROM pool_metadata pm
LEFT JOIN pool_summary ps ON pm.pool_id = ps.pool_id
WHERE pm.client_name = 'Client Company Ltd'
  AND ps.timestamp = (
      SELECT MAX(timestamp) 
      FROM pool_summary 
      WHERE pool_id = pm.pool_id
  );
```

### Naming Convention

**Pool IDs should follow this pattern**:
- KZ Pool: `kzpool_XXX`
- Antpool: `antpool_XXX`
- F2Pool: `f2pool_XXX`
- Custom: `custom_XXX`

Where `XXX` is a 3-digit number (001, 002, etc.)

---

## Data Retention

### Recommended Retention Policies

```sql
-- Keep detailed worker status for 30 days
DELETE FROM worker_status 
WHERE timestamp < datetime('now', '-30 days');

-- Keep pool summary for 90 days
DELETE FROM pool_summary 
WHERE timestamp < datetime('now', '-90 days');

-- Keep daily earnings forever (small data)
-- No deletion

-- Keep anomaly log for 1 year
DELETE FROM anomaly_log 
WHERE timestamp < datetime('now', '-365 days')
  AND resolved = 1;
```

### Storage Estimates

| Table | Records/Day | Size/Record | Daily Growth |
|-------|-------------|-------------|--------------|
| pool_summary | 144 (10min) | 200 bytes | 28.8 KB |
| worker_status | 28,800 (200 workers × 144) | 150 bytes | 4.3 MB |
| daily_earnings | 1 | 100 bytes | 100 bytes |
| anomaly_log | ~5 | 200 bytes | 1 KB |

**Total**: ~4.4 MB per day per pool

---

## Backup & Restore

### Backup

```bash
# Full database backup
sqlite3 btcpool_data.db ".backup backup_$(date +%Y%m%d).db"

# Export to SQL
sqlite3 btcpool_data.db .dump > backup_$(date +%Y%m%d).sql

# Compress
gzip backup_$(date +%Y%m%d).sql
```

### Restore

```bash
# From backup file
cp backup_20251123.db btcpool_data.db

# From SQL dump
sqlite3 btcpool_data.db < backup_20251123.sql
```

---

## Performance Optimization

### Vacuum Database

```sql
VACUUM;
```

### Analyze for Query Optimization

```sql
ANALYZE;
```

### Check Database Size

```sql
SELECT page_count * page_size as size 
FROM pragma_page_count(), pragma_page_size();
```

---

## Migration Scripts

### Add New Column

```sql
-- Add notes column to pool_metadata
ALTER TABLE pool_metadata ADD COLUMN notes TEXT;
```

### Create View for Latest Status

```sql
CREATE VIEW latest_pool_status AS
SELECT 
    pm.pool_id,
    pm.pool_name,
    pm.client_name,
    pm.country,
    pm.company,
    ps.current_hashrate,
    ps.online_workers,
    ps.offline_workers,
    ps.balance,
    ps.timestamp
FROM pool_metadata pm
LEFT JOIN pool_summary ps ON pm.pool_id = ps.pool_id
WHERE ps.timestamp = (
    SELECT MAX(timestamp) 
    FROM pool_summary 
    WHERE pool_id = pm.pool_id
)
OR ps.timestamp IS NULL;
```

---

## API Integration Examples

### Python

```python
import sqlite3

conn = sqlite3.connect('btcpool_data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get latest status
cursor.execute('''
    SELECT * FROM latest_pool_status
    WHERE client_name = ?
''', ('Client Company Ltd',))

pools = [dict(row) for row in cursor.fetchall()]
```

### Node.js

```javascript
const sqlite3 = require('sqlite3').verbose();
const db = new sqlite3.Database('btcpool_data.db');

db.all(`
    SELECT * FROM latest_pool_status
    WHERE client_name = ?
`, ['Client Company Ltd'], (err, rows) => {
    console.log(rows);
});
```

---

**Schema Version**: 1.0  
**Last Updated**: 2025-11-23  
**Maintained by**: BTCDC Builds
