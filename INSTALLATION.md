# Installation Guide

Complete installation instructions for KZ Pool Scraper on your VPS.

---

## Quick Install (Recommended)

### One-Line Installation

```bash
curl -sSL https://raw.githubusercontent.com/btcdcbuilds/KZ_Pool_Scraper/main/install.sh | bash
```

### With Custom Configuration

```bash
OBSERVER_URL="https://btcpool.kz/observer-link/YOUR_ID" \
CLIENT_NAME="Your Client Name" \
COUNTRY="Kazakhstan" \
COMPANY="Your Company" \
bash <(curl -sSL https://raw.githubusercontent.com/btcdcbuilds/KZ_Pool_Scraper/main/install.sh)
```

---

## Manual Installation

### Prerequisites

- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **Docker**: 20.10+ (recommended) OR Python 3.11+
- **RAM**: 512MB minimum, 1GB recommended
- **Disk**: 1GB free space
- **Network**: Internet access to btcpool.kz

### Option 1: Docker Installation (Recommended)

#### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### Step 2: Clone Repository

```bash
git clone https://github.com/btcdcbuilds/KZ_Pool_Scraper.git
cd KZ_Pool_Scraper
```

#### Step 3: Configure Pools

```bash
# Copy example configuration
cp pools_config.example.json pools_config.json

# Edit configuration
nano pools_config.json
```

Update the `observer_url` and other fields:

```json
{
  "pools": [
    {
      "pool_id": "pool_001",
      "pool_name": "Main KZ Pool",
      "observer_url": "https://btcpool.kz/observer-link/YOUR_OBSERVER_ID",
      "client_name": "Your Client Name",
      "country": "Kazakhstan",
      "company": "Your Company",
      "location": "Almaty",
      "contact_email": "client@example.com",
      "active": true,
      "scrape_interval_minutes": 10,
      "tags": ["production"]
    }
  ]
}
```

#### Step 4: Create Directories

```bash
mkdir -p data logs
```

#### Step 5: Build and Start

```bash
# Build Docker image
docker-compose build

# Start container
docker-compose up -d

# Check logs
docker-compose logs -f
```

#### Step 6: Verify Installation

```bash
# Check if container is running
docker-compose ps

# View collected data
docker-compose exec kz-pool-scraper python view_data.py
```

---

### Option 2: Python Installation (Without Docker)

#### Step 1: Install Python 3.11+

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip

# Verify
python3.11 --version
```

#### Step 2: Clone Repository

```bash
git clone https://github.com/btcdcbuilds/KZ_Pool_Scraper.git
cd KZ_Pool_Scraper
```

#### Step 3: Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

#### Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Install Playwright Browsers

```bash
playwright install chromium
playwright install-deps chromium
```

#### Step 6: Configure Pools

```bash
cp pools_config.example.json pools_config.json
nano pools_config.json
```

#### Step 7: Create Directories

```bash
mkdir -p data logs
```

#### Step 8: Test Run

```bash
# Set database path
export DB_PATH="$(pwd)/data/btcpool_data.db"

# Run scraper once
python btcpool_scraper.py

# View data
python view_data.py
```

#### Step 9: Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/kz-pool-scraper.service
```

Add this content (replace `/path/to` with your actual path):

```ini
[Unit]
Description=KZ Pool Scraper
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/KZ_Pool_Scraper
Environment="PATH=/path/to/KZ_Pool_Scraper/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="DB_PATH=/path/to/KZ_Pool_Scraper/data/btcpool_data.db"
Environment="POOLS_CONFIG=/path/to/KZ_Pool_Scraper/pools_config.json"
ExecStart=/bin/bash -c 'while true; do /path/to/KZ_Pool_Scraper/venv/bin/python /path/to/KZ_Pool_Scraper/btcpool_scraper.py; sleep 600; done'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kz-pool-scraper
sudo systemctl start kz-pool-scraper

# Check status
sudo systemctl status kz-pool-scraper

# View logs
sudo journalctl -u kz-pool-scraper -f
```

---

## Configuration

### Environment Variables

You can use environment variables instead of the config file:

```bash
export OBSERVER_URL="https://btcpool.kz/observer-link/YOUR_ID"
export POOL_ID="pool_001"
export POOL_NAME="Main Pool"
export CLIENT_NAME="Your Client"
export COUNTRY="Kazakhstan"
export COMPANY="Your Company"
export DB_PATH="/data/btcpool_data.db"
```

### Docker Environment Variables

Edit `docker-compose.yml`:

```yaml
environment:
  - OBSERVER_URL=https://btcpool.kz/observer-link/YOUR_ID
  - POOL_ID=pool_001
  - CLIENT_NAME=Your Client
  - COUNTRY=Kazakhstan
  - COMPANY=Your Company
```

---

## Multiple Pools Setup

### Using Config File (Recommended)

Edit `pools_config.json` and add multiple pools:

```json
{
  "pools": [
    {
      "pool_id": "pool_001",
      "pool_name": "Main Pool",
      "observer_url": "https://btcpool.kz/observer-link/ID_1",
      "client_name": "Client A",
      "country": "Kazakhstan",
      "active": true
    },
    {
      "pool_id": "pool_002",
      "pool_name": "Secondary Pool",
      "observer_url": "https://btcpool.kz/observer-link/ID_2",
      "client_name": "Client B",
      "country": "Kazakhstan",
      "active": true
    }
  ]
}
```

### Using Docker Compose

Use `docker-compose.multi.yml`:

```bash
# Edit file to add your pools
nano docker-compose.multi.yml

# Start all pools
docker-compose -f docker-compose.multi.yml up -d
```

---

## Verification

### Check if Scraper is Running

**Docker:**
```bash
docker-compose ps
docker-compose logs --tail=50
```

**Systemd:**
```bash
sudo systemctl status kz-pool-scraper
sudo journalctl -u kz-pool-scraper --tail=50
```

### View Collected Data

**Docker:**
```bash
docker-compose exec kz-pool-scraper python view_data.py
```

**Python:**
```bash
source venv/bin/activate
python view_data.py
```

### Check Database

```bash
# Docker
docker-compose exec kz-pool-scraper sqlite3 /data/btcpool_data.db ".tables"

# Python
sqlite3 data/btcpool_data.db ".tables"
```

Expected tables:
- `pool_metadata`
- `pool_summary`
- `worker_status`
- `daily_earnings`
- `anomaly_log`

---

## Updating

### Docker

```bash
cd KZ_Pool_Scraper
git pull
docker-compose build
docker-compose up -d
```

### Python

```bash
cd KZ_Pool_Scraper
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart kz-pool-scraper
```

---

## Uninstallation

### Docker

```bash
cd KZ_Pool_Scraper
docker-compose down
cd ..
rm -rf KZ_Pool_Scraper
```

### Python

```bash
# Stop service
sudo systemctl stop kz-pool-scraper
sudo systemctl disable kz-pool-scraper
sudo rm /etc/systemd/system/kz-pool-scraper.service
sudo systemctl daemon-reload

# Remove files
cd ..
rm -rf KZ_Pool_Scraper
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### No Data Being Collected

```bash
# Test scraper manually
docker-compose exec kz-pool-scraper python btcpool_scraper.py

# Check network connectivity
docker-compose exec kz-pool-scraper ping -c 3 btcpool.kz

# Check observer URL
docker-compose exec kz-pool-scraper curl -I https://btcpool.kz/observer-link/YOUR_ID
```

### Database Errors

```bash
# Check database file
ls -lh data/btcpool_data.db

# Check database integrity
sqlite3 data/btcpool_data.db "PRAGMA integrity_check;"

# Backup and recreate
mv data/btcpool_data.db data/btcpool_data.db.backup
docker-compose restart
```

### Python Version Issues

```bash
# Check Python version
python3.11 --version

# If not available, install
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv
```

### Playwright Issues

```bash
# Reinstall browsers
playwright install chromium
playwright install-deps chromium

# Or in Docker
docker-compose exec kz-pool-scraper playwright install chromium
```

---

## Security

### Protect Configuration Files

```bash
# Restrict permissions
chmod 600 pools_config.json
chmod 600 .env

# Don't commit sensitive data
echo "pools_config.json" >> .gitignore
echo ".env" >> .gitignore
```

### Use Environment Variables for Secrets

Instead of storing in config files:

```bash
# Create .env file
cat > .env << EOF
OBSERVER_URL=https://btcpool.kz/observer-link/YOUR_ID
CLIENT_NAME=Your Client
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-secret-key
EOF

chmod 600 .env
```

Update `docker-compose.yml`:

```yaml
env_file:
  - .env
```

---

## Performance Tuning

### Adjust Scraping Interval

Edit `docker-compose.yml`:

```yaml
command: >
  sh -c "
    while true; do
      python -u btcpool_scraper.py;
      sleep 1800;  # 30 minutes instead of 10
    done
  "
```

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 256M
```

### Database Optimization

```bash
# Vacuum database periodically
sqlite3 data/btcpool_data.db "VACUUM;"

# Clean old data
sqlite3 data/btcpool_data.db "
DELETE FROM worker_status WHERE timestamp < datetime('now', '-30 days');
DELETE FROM pool_summary WHERE timestamp < datetime('now', '-90 days');
"
```

---

## Backup

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/kz-pool-scraper"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp data/btcpool_data.db $BACKUP_DIR/btcpool_$DATE.db

# Backup configuration
cp pools_config.json $BACKUP_DIR/pools_config_$DATE.json

# Compress
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz \
    $BACKUP_DIR/btcpool_$DATE.db \
    $BACKUP_DIR/pools_config_$DATE.json

# Clean up
rm $BACKUP_DIR/btcpool_$DATE.db
rm $BACKUP_DIR/pools_config_$DATE.json

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/backup_$DATE.tar.gz"
```

Schedule with cron:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

---

## Next Steps

After installation:

1. **Verify Data Collection**: Wait 10-15 minutes and check if data is being collected
2. **Set Up Monitoring**: Configure alerts for anomalies
3. **Configure Backup**: Set up automated backups
4. **Add More Pools**: Edit config file to add additional pools
5. **Integrate with Dashboard**: Connect to your monitoring dashboard
6. **Set Up Supabase** (optional): For cloud database sync

---

## Support

- **Documentation**: https://github.com/btcdcbuilds/KZ_Pool_Scraper
- **Issues**: https://github.com/btcdcbuilds/KZ_Pool_Scraper/issues
- **Email**: support@btcdcbuilds.com

---

**Installation Guide Version**: 1.0  
**Last Updated**: 2025-11-23
