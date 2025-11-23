# KZ Pool Scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

Automated web scraping system for monitoring Bitcoin mining pool operations from btcpool.kz observer links with client/company metadata tracking.

## 🎯 Features

- **Automated Monitoring**: Scrapes device status every 10 minutes
- **Comprehensive Tracking**: 
  - Pool summary (hashrate, balance, earnings)
  - Individual worker status (200+ devices)
  - Worker hashrates (10m, 1h, 24h intervals)
  - Daily earnings history
- **Metadata Management**: Track client names, countries, companies, locations
- **Anomaly Detection**: Offline workers, hashrate drops, with severity levels
- **Multi-Pool Support**: Monitor multiple pools with different configurations
- **Database Integration**: SQLite with foreign keys for cross-repository compatibility
- **Docker Ready**: Isolated containers for easy VPS deployment
- **Supabase Integration**: Cloud database sync ready

## 📊 Use Cases

- Mining operation monitoring
- Client portfolio management
- Multi-location tracking
- Performance analytics
- Anomaly alerting
- Historical data analysis

## 🚀 Quick Start

### One-Line Installation (VPS)

```bash
curl -sSL https://raw.githubusercontent.com/btcdcbuilds/KZ_Pool_Scraper/main/install.sh | bash
```

### Docker Deployment

```bash
git clone https://github.com/btcdcbuilds/KZ_Pool_Scraper.git
cd KZ_Pool_Scraper
docker-compose up -d
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/btcdcbuilds/KZ_Pool_Scraper.git
cd KZ_Pool_Scraper

# Install dependencies
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Configure pools
cp pools_config.example.json pools_config.json
nano pools_config.json

# Run scraper
python btcpool_scraper.py
```

## ⚙️ Configuration

### Pool Configuration File

Edit `pools_config.json` to add your pools:

```json
{
  "pools": [
    {
      "pool_id": "pool_001",
      "pool_name": "Main KZ Pool",
      "observer_url": "https://btcpool.kz/observer-link/YOUR_OBSERVER_ID",
      "client_name": "Client Company Ltd",
      "country": "Kazakhstan",
      "company": "BTCDC Builds",
      "location": "Almaty",
      "contact_email": "client@example.com",
      "active": true,
      "scrape_interval_minutes": 10,
      "notes": "Primary mining operation",
      "tags": ["production", "high-priority"]
    }
  ]
}
```

### Environment Variables (Docker)

```bash
OBSERVER_URL=https://btcpool.kz/observer-link/YOUR_ID
POOL_ID=pool_001
POOL_NAME=Main Pool
CLIENT_NAME=Client Company
COUNTRY=Kazakhstan
COMPANY=BTCDC Builds
LOCATION=Almaty
DB_PATH=/data/btcpool_data.db
```

## 📁 Project Structure

```
KZ_Pool_Scraper/
├── btcpool_scraper.py          # Main scraper with metadata support
├── pools_config.json           # Pool configurations
├── view_data.py                # Data viewer utility
├── manage_pools.py             # Pool management CLI
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container definition
├── docker-compose.yml          # Single pool deployment
├── docker-compose.multi.yml    # Multiple pools deployment
├── install.sh                  # One-line VPS installation
├── README.md                   # This file
├── INSTALLATION.md             # Detailed installation guide
├── DATABASE_SCHEMA.md          # Database schema documentation
├── INTEGRATION_GUIDE.md        # Cross-repository integration
└── docs/                       # Additional documentation
    ├── API.md                  # API documentation
    ├── TROUBLESHOOTING.md      # Common issues and solutions
    └── EXAMPLES.md             # Usage examples
```

## 🗄️ Database Schema

### Core Tables

#### `pool_metadata`
Stores client and company information for each pool.

| Column | Type | Description |
|--------|------|-------------|
| pool_id | TEXT | Unique pool identifier (PRIMARY KEY) |
| pool_name | TEXT | Human-readable pool name |
| observer_url | TEXT | BTC Pool observer link |
| client_name | TEXT | Client company name |
| country | TEXT | Country location |
| company | TEXT | Operating company |
| location | TEXT | Specific location/city |
| contact_email | TEXT | Contact email |
| tags | TEXT | JSON array of tags |
| active | INTEGER | 1=active, 0=inactive |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

#### `pool_summary`
Operational metrics collected every 10 minutes.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PRIMARY KEY |
| timestamp | DATETIME | Collection time |
| pool_id | TEXT | FOREIGN KEY → pool_metadata |
| observer_url | TEXT | Observer link |
| current_hashrate | TEXT | Current pool hashrate |
| avg_hashrate_24h | TEXT | 24-hour average |
| online_workers | INTEGER | Number online |
| offline_workers | INTEGER | Number offline |
| balance | TEXT | BTC balance |
| last_income | TEXT | Last payment |

#### `worker_status`
Individual device status every 10 minutes.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PRIMARY KEY |
| timestamp | DATETIME | Collection time |
| pool_id | TEXT | FOREIGN KEY → pool_metadata |
| observer_url | TEXT | Observer link |
| worker_name | TEXT | Device identifier |
| status | TEXT | ONLINE or OFFLINE |
| hashrate_10m | TEXT | 10-minute hashrate |
| hashrate_1h | TEXT | 1-hour hashrate |
| hashrate_24h | TEXT | 24-hour hashrate |
| last_exchange_time | TEXT | Last communication |

#### `daily_earnings`
Daily statistics (one record per day per pool).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PRIMARY KEY |
| pool_id | TEXT | FOREIGN KEY → pool_metadata |
| observer_url | TEXT | Observer link |
| date | TEXT | Earnings date |
| total_income | TEXT | BTC earned |
| hashrate | TEXT | Average hashrate |
| recorded_at | DATETIME | Record creation |

**Unique Constraint**: `(pool_id, date)`

#### `anomaly_log`
Detected issues and anomalies.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PRIMARY KEY |
| timestamp | DATETIME | Detection time |
| pool_id | TEXT | FOREIGN KEY → pool_metadata |
| observer_url | TEXT | Observer link |
| anomaly_type | TEXT | Type of anomaly |
| description | TEXT | Detailed description |
| severity | TEXT | HIGH, MEDIUM, or LOW |
| resolved | INTEGER | 0=open, 1=resolved |

## 🔗 Cross-Repository Integration

This scraper is designed to integrate with other mining pool scrapers. The database schema uses `pool_id` as a foreign key to link all data.

### Integration Pattern

```python
# In your other scraper (e.g., Antpool)
import sqlite3

# Connect to shared database
conn = sqlite3.connect('/data/btcpool_data.db')

# Query KZ Pool data by client
cursor.execute('''
    SELECT ps.*, pm.client_name, pm.country, pm.company
    FROM pool_summary ps
    JOIN pool_metadata pm ON ps.pool_id = pm.pool_id
    WHERE pm.client_name = ?
    ORDER BY ps.timestamp DESC
''', ('Client Company Ltd',))

# Get all pools for a company
cursor.execute('''
    SELECT * FROM pool_metadata
    WHERE company = ?
''', ('BTCDC Builds',))
```

### Shared Database Example

```yaml
# docker-compose.yml for multiple scrapers
version: '3.8'

services:
  kz-pool-scraper:
    image: btcdcbuilds/kz-pool-scraper
    volumes:
      - shared-data:/data
  
  antpool-scraper:
    image: btcdcbuilds/antpool-scraper
    volumes:
      - shared-data:/data
  
  dashboard:
    image: btcdcbuilds/mining-dashboard
    volumes:
      - shared-data:/data:ro

volumes:
  shared-data:
```

## 📈 Usage Examples

### View Latest Status

```bash
python view_data.py summary
```

### Check Offline Workers

```bash
python view_data.py offline
```

### View Specific Client Data

```bash
python view_data.py --client "Client Company Ltd"
```

### Export Data

```bash
# Export to CSV
python view_data.py export --format csv --output data.csv

# Export to JSON
python view_data.py export --format json --output data.json
```

### Manage Pools

```bash
# List all pools
python manage_pools.py list

# Add new pool
python manage_pools.py add \
  --pool-id pool_002 \
  --name "Secondary Pool" \
  --url "https://btcpool.kz/observer-link/OBSERVER_ID" \
  --client "Client Name" \
  --country "Kazakhstan"

# Deactivate pool
python manage_pools.py deactivate pool_002

# Update pool metadata
python manage_pools.py update pool_001 --client "New Client Name"
```

## 🐳 Docker Deployment

### Single Pool

```bash
docker-compose up -d
```

### Multiple Pools

```bash
docker-compose -f docker-compose.multi.yml up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Access Data

```bash
docker-compose exec kz-pool-scraper python view_data.py
```

## 🔧 Development

### Setup Development Environment

```bash
git clone https://github.com/btcdcbuilds/KZ_Pool_Scraper.git
cd KZ_Pool_Scraper
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Testing dependencies
```

### Run Tests

```bash
pytest tests/
```

### Code Style

```bash
black btcpool_scraper.py
flake8 btcpool_scraper.py
```

## 📊 Performance

- **Execution Time**: ~15 seconds per scrape
- **Memory Usage**: ~200MB per container
- **Disk Usage**: ~1.4MB per day (200 workers, 10-min intervals)
- **Monthly Storage**: ~42MB per pool

## 🔒 Security

- Database credentials via environment variables
- Read-only volumes where appropriate
- No hardcoded secrets
- Docker isolation
- Supabase RLS support

## 🆘 Troubleshooting

### Container Won't Start

```bash
docker-compose logs
docker-compose build --no-cache
```

### No Data Being Collected

```bash
# Check if scraper is running
docker-compose exec kz-pool-scraper ps aux

# Test manually
docker-compose exec kz-pool-scraper python btcpool_scraper.py
```

### Database Issues

```bash
# Check database
docker-compose exec kz-pool-scraper sqlite3 /data/btcpool_data.db ".tables"

# Vacuum database
docker-compose exec kz-pool-scraper sqlite3 /data/btcpool_data.db "VACUUM;"
```

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more solutions.

## 📚 Documentation

- [Installation Guide](INSTALLATION.md) - Detailed installation instructions
- [Database Schema](DATABASE_SCHEMA.md) - Complete schema documentation
- [Integration Guide](INTEGRATION_GUIDE.md) - Cross-repository integration
- [API Documentation](docs/API.md) - API reference
- [Examples](docs/EXAMPLES.md) - Usage examples

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for BTCDC Builds mining operations
- Playwright for browser automation
- SQLite for reliable data storage

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/btcdcbuilds/KZ_Pool_Scraper/issues)
- **Email**: support@btcdcbuilds.com
- **Documentation**: [Wiki](https://github.com/btcdcbuilds/KZ_Pool_Scraper/wiki)

## 🗺️ Roadmap

- [ ] Telegram bot integration for alerts
- [ ] Web dashboard for visualization
- [ ] REST API for data access
- [ ] Prometheus metrics export
- [ ] Multi-language support
- [ ] Mobile app

## 📈 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Made with ❤️ by BTCDC Builds**
