#!/bin/bash
# KZ Pool Scraper - One-Line Installation Script
# Usage: curl -sSL https://raw.githubusercontent.com/btcdcbuilds/KZ_Pool_Scraper/main/install.sh | bash
# Or with custom settings:
#   OBSERVER_URL="your-url" CLIENT_NAME="Your Client" bash install.sh

set -e

echo "=========================================="
echo "KZ Pool Scraper - Installation"
echo "=========================================="
echo ""

# Configuration
INSTALL_DIR="${INSTALL_DIR:-$HOME/kz-pool-scraper}"
OBSERVER_URL="${OBSERVER_URL:-}"
POOL_ID="${POOL_ID:-pool_001}"
POOL_NAME="${POOL_NAME:-Main KZ Pool}"
CLIENT_NAME="${CLIENT_NAME:-}"
COUNTRY="${COUNTRY:-Kazakhstan}"
COMPANY="${COMPANY:-BTCDC Builds}"
LOCATION="${LOCATION:-}"
CONTACT_EMAIL="${CONTACT_EMAIL:-}"
DB_PATH="${DB_PATH:-/data/btcpool_data.db}"
USE_DOCKER="${USE_DOCKER:-yes}"

echo "Configuration:"
echo "  Install Directory: $INSTALL_DIR"
echo "  Pool ID: $POOL_ID"
echo "  Pool Name: $POOL_NAME"
echo "  Client Name: $CLIENT_NAME"
echo "  Country: $COUNTRY"
echo "  Company: $COMPANY"
echo "  Use Docker: $USE_DOCKER"
echo ""

# Check if Docker should be used
if [ "$USE_DOCKER" = "yes" ]; then
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        echo "Docker not found. Installing Docker..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo sh /tmp/get-docker.sh
        sudo usermod -aG docker $USER
        echo "✓ Docker installed"
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        echo "Docker Compose not found. Installing..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        echo "✓ Docker Compose installed"
    fi
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "Step 1: Cloning repository..."
if [ -d ".git" ]; then
    echo "  Repository already exists, pulling latest changes..."
    git pull
else
    git clone https://github.com/btcdcbuilds/KZ_Pool_Scraper.git .
fi

echo "Step 2: Creating directories..."
mkdir -p data logs config

echo "Step 3: Creating pool configuration..."
cat > pools_config.json << EOF
{
  "pools": [
    {
      "pool_id": "$POOL_ID",
      "pool_name": "$POOL_NAME",
      "observer_url": "$OBSERVER_URL",
      "client_name": "$CLIENT_NAME",
      "country": "$COUNTRY",
      "company": "$COMPANY",
      "location": "$LOCATION",
      "contact_email": "$CONTACT_EMAIL",
      "active": true,
      "scrape_interval_minutes": 10,
      "notes": "Installed via install.sh",
      "tags": ["production"],
      "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
      "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    }
  ],
  "metadata": {
    "version": "1.0",
    "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_pools": 1
  }
}
EOF

if [ "$USE_DOCKER" = "yes" ]; then
    echo "Step 4: Creating docker-compose.yml..."
    cat > docker-compose.yml << EOF
version: '3.8'

services:
  kz-pool-scraper:
    build: .
    container_name: kz-pool-scraper-${POOL_ID}
    restart: unless-stopped
    
    environment:
      - POOLS_CONFIG=/app/pools_config.json
      - DB_PATH=/data/btcpool_data.db
      - TZ=UTC
    
    volumes:
      - ./data:/data
      - ./logs:/logs
      - ./pools_config.json:/app/pools_config.json:ro
    
    command: >
      sh -c "
        echo '[${POOL_ID}] KZ Pool Scraper started at \$(date)';
        while true; do
          echo '[${POOL_ID}] Running scrape at \$(date)';
          python -u btcpool_scraper.py 2>&1 | tee -a /logs/scraper.log;
          echo '[${POOL_ID}] Waiting 10 minutes...';
          sleep 600;
        done
      "
    
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

networks:
  default:
    name: mining-network
EOF

    echo "Step 5: Building Docker image..."
    docker-compose build

    echo "Step 6: Starting container..."
    docker-compose up -d

    echo ""
    echo "=========================================="
    echo "✓ Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo "Database: $INSTALL_DIR/data/btcpool_data.db"
    echo "Logs: $INSTALL_DIR/logs/scraper.log"
    echo "Config: $INSTALL_DIR/pools_config.json"
    echo ""
    echo "The scraper is now running in Docker and will collect data every 10 minutes."
    echo ""
    echo "Useful commands:"
    echo "  cd $INSTALL_DIR"
    echo "  docker-compose logs -f                    # View logs"
    echo "  docker-compose exec kz-pool-scraper-${POOL_ID} python view_data.py  # View data"
    echo "  docker-compose restart                    # Restart"
    echo "  docker-compose down                       # Stop"
    echo "  docker-compose up -d                      # Start"
    echo ""
    echo "To add more pools:"
    echo "  1. Edit pools_config.json"
    echo "  2. Run: docker-compose restart"
    echo ""

else
    # Non-Docker installation
    echo "Step 4: Setting up Python environment..."
    
    # Check Python version
    if ! command -v python3.11 &> /dev/null; then
        echo "Python 3.11+ not found. Please install Python 3.11 or higher."
        exit 1
    fi
    
    # Create virtual environment
    python3.11 -m venv venv
    source venv/bin/activate
    
    echo "Step 5: Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "Step 6: Installing Playwright browsers..."
    playwright install chromium
    
    echo "Step 7: Creating systemd service..."
    sudo tee /etc/systemd/system/kz-pool-scraper.service > /dev/null << EOF
[Unit]
Description=KZ Pool Scraper
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="POOLS_CONFIG=$INSTALL_DIR/pools_config.json"
Environment="DB_PATH=$INSTALL_DIR/data/btcpool_data.db"
ExecStart=/bin/bash -c 'while true; do $INSTALL_DIR/venv/bin/python $INSTALL_DIR/btcpool_scraper.py; sleep 600; done'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    echo "Step 8: Starting service..."
    sudo systemctl daemon-reload
    sudo systemctl enable kz-pool-scraper
    sudo systemctl start kz-pool-scraper
    
    echo ""
    echo "=========================================="
    echo "✓ Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo "Database: $INSTALL_DIR/data/btcpool_data.db"
    echo "Config: $INSTALL_DIR/pools_config.json"
    echo ""
    echo "The scraper is now running as a systemd service."
    echo ""
    echo "Useful commands:"
    echo "  cd $INSTALL_DIR"
    echo "  sudo systemctl status kz-pool-scraper    # Check status"
    echo "  sudo journalctl -u kz-pool-scraper -f    # View logs"
    echo "  source venv/bin/activate && python view_data.py  # View data"
    echo "  sudo systemctl restart kz-pool-scraper   # Restart"
    echo "  sudo systemctl stop kz-pool-scraper      # Stop"
    echo ""
    echo "To add more pools:"
    echo "  1. Edit pools_config.json"
    echo "  2. Run: sudo systemctl restart kz-pool-scraper"
    echo ""
fi

# Check if OBSERVER_URL was provided
if [ -z "$OBSERVER_URL" ]; then
    echo "⚠️  WARNING: No OBSERVER_URL provided!"
    echo ""
    echo "Please edit the configuration file and add your observer URL:"
    echo "  nano $INSTALL_DIR/pools_config.json"
    echo ""
    echo "Then restart the service:"
    if [ "$USE_DOCKER" = "yes" ]; then
        echo "  cd $INSTALL_DIR && docker-compose restart"
    else
        echo "  sudo systemctl restart kz-pool-scraper"
    fi
    echo ""
fi

echo "Documentation:"
echo "  README: https://github.com/btcdcbuilds/KZ_Pool_Scraper"
echo "  Database Schema: $INSTALL_DIR/DATABASE_SCHEMA.md"
echo "  Installation Guide: $INSTALL_DIR/INSTALLATION.md"
echo ""
echo "For support, visit: https://github.com/btcdcbuilds/KZ_Pool_Scraper/issues"
echo ""
