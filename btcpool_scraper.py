#!/usr/bin/env python3
"""
BTC Pool KZ Scraper with Metadata Management
Supports client tracking, country/company metadata, and cross-repository integration
"""
from playwright.sync_api import sync_playwright
import time
import sqlite3
from datetime import datetime
import re
import os
import sys
import json

class BTCPoolScraper:
    def __init__(self, pool_config=None, observer_url=None, db_path=None):
        """
        Initialize scraper with pool configuration
        
        Args:
            pool_config: Dictionary with pool metadata (client, country, company, etc.)
            observer_url: Direct observer URL (if not using pool_config)
            db_path: Database path (default: from env or /data/btcpool_data.db)
        """
        if pool_config:
            self.pool_id = pool_config.get('pool_id', 'unknown')
            self.pool_name = pool_config.get('pool_name', 'Unknown Pool')
            self.observer_url = pool_config.get('observer_url')
            self.client_name = pool_config.get('client_name', '')
            self.country = pool_config.get('country', '')
            self.company = pool_config.get('company', '')
            self.location = pool_config.get('location', '')
            self.contact_email = pool_config.get('contact_email', '')
            self.tags = pool_config.get('tags', [])
        else:
            # Fallback to environment variables or direct parameters
            self.pool_id = os.getenv('POOL_ID', 'default')
            self.pool_name = os.getenv('POOL_NAME', 'Default Pool')
            self.observer_url = observer_url or os.getenv('OBSERVER_URL')
            self.client_name = os.getenv('CLIENT_NAME', '')
            self.country = os.getenv('COUNTRY', '')
            self.company = os.getenv('COMPANY', '')
            self.location = os.getenv('LOCATION', '')
            self.contact_email = os.getenv('CONTACT_EMAIL', '')
            self.tags = []
        
        self.db_path = db_path or os.getenv('DB_PATH', '/data/btcpool_data.db')
        
        print(f"[{self.pool_id.upper()}] Initializing scraper")
        print(f"  Pool Name: {self.pool_name}")
        print(f"  Client: {self.client_name}")
        print(f"  Country: {self.country}")
        print(f"  Company: {self.company}")
        print(f"  Observer URL: {self.observer_url}")
        print(f"  Database: {self.db_path}")
        
        self.setup_database()
    
    def setup_database(self):
        """Create database tables with metadata support"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Pool metadata table - stores client/company information
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pool_metadata (
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
                )
            ''')
            
            # Pool summary table - operational data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pool_summary (
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
                )
            ''')
            
            # Worker status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_status (
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
                )
            ''')
            
            # Daily earnings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_earnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pool_id TEXT,
                    observer_url TEXT,
                    date TEXT,
                    total_income TEXT,
                    hashrate TEXT,
                    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pool_id, date),
                    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
                )
            ''')
            
            # Anomaly log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS anomaly_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    pool_id TEXT,
                    observer_url TEXT,
                    anomaly_type TEXT,
                    description TEXT,
                    severity TEXT,
                    resolved INTEGER DEFAULT 0,
                    FOREIGN KEY (pool_id) REFERENCES pool_metadata(pool_id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pool_summary_timestamp ON pool_summary(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pool_summary_pool_id ON pool_summary(pool_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_worker_status_timestamp ON worker_status(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_worker_status_pool_id ON worker_status(pool_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_earnings_pool_id ON daily_earnings(pool_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_anomaly_log_pool_id ON anomaly_log(pool_id)')
            
            # Insert or update pool metadata
            cursor.execute('''
                INSERT OR REPLACE INTO pool_metadata 
                (pool_id, pool_name, observer_url, client_name, country, company, location, contact_email, tags, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                self.pool_id,
                self.pool_name,
                self.observer_url,
                self.client_name,
                self.country,
                self.company,
                self.location,
                self.contact_email,
                json.dumps(self.tags)
            ))
            
            conn.commit()
            conn.close()
            print(f"[{self.pool_id.upper()}] Database initialized successfully")
        except Exception as e:
            print(f"[{self.pool_id.upper()}] ❌ Database setup error: {e}", file=sys.stderr)
            raise
    
    def scrape_data(self):
        """Main scraping function"""
        print(f"\n[{self.pool_id.upper()}] {'='*60}")
        print(f"[{self.pool_id.upper()}] Starting scrape at {datetime.now()}")
        print(f"[{self.pool_id.upper()}] {'='*60}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                print(f"[{self.pool_id.upper()}] Navigating to {self.observer_url}...")
                page.goto(self.observer_url, wait_until="networkidle", timeout=60000)
                
                time.sleep(5)
                
                # Extract data using JavaScript
                data = page.evaluate('''() => {
                    const result = {summary: {}, workers: [], daily_earnings: []};
                    const bodyText = document.body.innerText;
                    const lines = bodyText.split('\\n');
                    
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i].trim();
                        if (line.includes('Текущий хешрейт') || line.includes('Current hashrate')) {
                            if (i + 1 < lines.length) result.summary.current_hashrate = lines[i + 1].trim();
                        } else if (line.includes('Средний хешрейт за 24ч')) {
                            if (i + 1 < lines.length) result.summary.avg_hashrate_24h = lines[i + 1].trim();
                        } else if (line.includes('Онлайн воркеры')) {
                            if (i + 1 < lines.length) result.summary.online_workers = lines[i + 1].trim();
                        } else if (line.includes('Оффлайн воркеры')) {
                            if (i + 1 < lines.length) result.summary.offline_workers = lines[i + 1].trim();
                        } else if (line === 'Баланс' && i + 1 < lines.length && lines[i + 1].includes('BTC')) {
                            result.summary.balance = lines[i + 1].trim();
                        } else if (line.includes('Последний доход')) {
                            if (i + 1 < lines.length) result.summary.last_income = lines[i + 1].trim();
                        }
                    }
                    
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const rows = table.querySelectorAll('tbody tr');
                        if (rows.length > 0) {
                            const headerText = table.querySelector('thead')?.innerText || '';
                            if (headerText.includes('Воркеры') || headerText.includes('Статус') || 
                                table.innerText.includes('ONLINE') || table.innerText.includes('OFFLINE')) {
                                
                                for (const row of rows) {
                                    const cells = row.querySelectorAll('td');
                                    if (cells.length >= 5) {
                                        const worker = {
                                            name: cells[0]?.innerText.trim() || '',
                                            status: cells[1]?.innerText.trim() || '',
                                            hashrate_10m: cells[2]?.innerText.trim() || '',
                                            hashrate_1h: cells[3]?.innerText.trim() || '',
                                            hashrate_24h: cells[4]?.innerText.trim() || '',
                                            last_exchange_time: cells[5]?.innerText.trim() || ''
                                        };
                                        
                                        if (worker.name && (worker.status === 'ONLINE' || worker.status === 'OFFLINE')) {
                                            result.workers.push(worker);
                                        }
                                    }
                                }
                            }
                            else if (headerText.includes('Доходы') || headerText.includes('Дата') || 
                                     headerText.includes('Общий доход')) {
                                
                                for (const row of rows) {
                                    const cells = row.querySelectorAll('td');
                                    if (cells.length >= 3) {
                                        const earning = {
                                            date: cells[0]?.innerText.trim() || '',
                                            total_income: cells[1]?.innerText.trim() || '',
                                            hashrate: cells[2]?.innerText.trim() || ''
                                        };
                                        
                                        if (earning.date && earning.date.match(/\\d{1,2}\\/\\d{1,2}\\/\\d{4}/)) {
                                            result.daily_earnings.push(earning);
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    return result;
                }''')
                
                browser.close()
                
            print(f"[{self.pool_id.upper()}] Extracted Data Summary:")
            print(f"  - Summary fields: {len(data['summary'])}")
            print(f"  - Workers found: {len(data['workers'])}")
            print(f"  - Daily earnings records: {len(data['daily_earnings'])}")
            
            self.save_to_database(data)
            self.check_anomalies(data)
            
            print(f"[{self.pool_id.upper()}] Scrape completed successfully!")
            return data
            
        except Exception as e:
            print(f"[{self.pool_id.upper()}] ❌ Scrape error: {e}", file=sys.stderr)
            raise
    
    def save_to_database(self, data):
        """Save scraped data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data['summary']:
                cursor.execute('''
                    INSERT INTO pool_summary 
                    (pool_id, observer_url, current_hashrate, avg_hashrate_24h, online_workers, 
                     offline_workers, balance, last_income)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.pool_id,
                    self.observer_url,
                    data['summary'].get('current_hashrate', ''),
                    data['summary'].get('avg_hashrate_24h', ''),
                    data['summary'].get('online_workers', 0),
                    data['summary'].get('offline_workers', 0),
                    data['summary'].get('balance', ''),
                    data['summary'].get('last_income', '')
                ))
                print(f"  ✓ Saved pool summary")
            
            for worker in data['workers']:
                cursor.execute('''
                    INSERT INTO worker_status 
                    (pool_id, observer_url, worker_name, status, hashrate_10m, hashrate_1h, 
                     hashrate_24h, last_exchange_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.pool_id,
                    self.observer_url,
                    worker['name'],
                    worker['status'],
                    worker['hashrate_10m'],
                    worker['hashrate_1h'],
                    worker['hashrate_24h'],
                    worker['last_exchange_time']
                ))
            print(f"  ✓ Saved {len(data['workers'])} worker records")
            
            for earning in data['daily_earnings']:
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_earnings 
                    (pool_id, observer_url, date, total_income, hashrate)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    self.pool_id,
                    self.observer_url,
                    earning['date'],
                    earning['total_income'],
                    earning['hashrate']
                ))
            print(f"  ✓ Saved {len(data['daily_earnings'])} daily earnings records")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[{self.pool_id.upper()}] ❌ Database save error: {e}", file=sys.stderr)
            raise
    
    def check_anomalies(self, data):
        """Check for anomalies and log them"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            anomalies = []
            
            offline_count = int(data['summary'].get('offline_workers', 0))
            if offline_count > 0:
                offline_workers = [w['name'] for w in data['workers'] if w['status'] == 'OFFLINE']
                severity = 'HIGH' if offline_count > 5 else 'MEDIUM'
                anomalies.append({
                    'type': 'OFFLINE_WORKERS',
                    'description': f"{offline_count} worker(s) offline: {', '.join(offline_workers[:5])}",
                    'severity': severity
                })
            
            cursor.execute('''
                SELECT current_hashrate FROM pool_summary 
                WHERE pool_id = ?
                ORDER BY timestamp DESC LIMIT 10
            ''', (self.pool_id,))
            
            historical_hashrates = cursor.fetchall()
            if len(historical_hashrates) > 1:
                current_hr = data['summary'].get('current_hashrate', '0')
                current_value = self.parse_hashrate_to_ths(current_hr)
                
                avg_value = sum(self.parse_hashrate_to_ths(hr[0]) for hr in historical_hashrates[1:])
                avg_value = avg_value / len(historical_hashrates[1:]) if len(historical_hashrates) > 1 else current_value
                
                if current_value < avg_value * 0.8:
                    drop_percent = ((avg_value - current_value) / avg_value) * 100
                    severity = 'HIGH' if drop_percent > 30 else 'MEDIUM'
                    anomalies.append({
                        'type': 'HASHRATE_DROP',
                        'description': f"Hashrate dropped {drop_percent:.1f}% (Current: {current_hr}, Avg: {avg_value:.2f} TH/s)",
                        'severity': severity
                    })
            
            for anomaly in anomalies:
                cursor.execute('''
                    INSERT INTO anomaly_log (pool_id, observer_url, anomaly_type, description, severity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (self.pool_id, self.observer_url, anomaly['type'], anomaly['description'], anomaly['severity']))
                print(f"  ⚠ ANOMALY: {anomaly['description']} (Severity: {anomaly['severity']})")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[{self.pool_id.upper()}] ❌ Anomaly check error: {e}", file=sys.stderr)
    
    def parse_hashrate_to_ths(self, hashrate_str):
        """Convert hashrate string to TH/s"""
        if not hashrate_str:
            return 0
        
        match = re.search(r'([\d.]+)\s*([TGMP]?H/s)', hashrate_str)
        if not match:
            return 0
        
        value = float(match.group(1))
        unit = match.group(2)
        
        conversions = {'PH/s': 1000, 'TH/s': 1, 'GH/s': 0.001, 'MH/s': 0.000001}
        return value * conversions.get(unit, 1)


def load_pools_config(config_path='pools_config.json'):
    """Load pool configurations from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config.get('pools', [])
    except FileNotFoundError:
        print(f"⚠ Config file not found: {config_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return []


def main():
    """Main function - supports both config file and environment variables"""
    try:
        # Try to load from config file first
        config_path = os.getenv('POOLS_CONFIG', 'pools_config.json')
        pools = load_pools_config(config_path)
        
        if pools:
            # Run all active pools
            for pool_config in pools:
                if pool_config.get('active', True):
                    print(f"\n{'='*70}")
                    print(f"Processing pool: {pool_config.get('pool_name')}")
                    print(f"{'='*70}")
                    
                    scraper = BTCPoolScraper(pool_config=pool_config)
                    scraper.scrape_data()
        else:
            # Fallback to environment variables
            print("No config file found, using environment variables...")
            scraper = BTCPoolScraper()
            scraper.scrape_data()
        
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
