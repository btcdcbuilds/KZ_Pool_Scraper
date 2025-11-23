#!/usr/bin/env python3
"""
BTC Pool Watcher Scraper v2
Improved version with better data extraction using table selectors
"""
from playwright.sync_api import sync_playwright
import time
import sqlite3
from datetime import datetime
import re

class BTCPoolScraperV2:
    def __init__(self, observer_url, db_path="btcpool_data.db"):
        self.observer_url = observer_url
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pool account summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pool_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                observer_url TEXT,
                current_hashrate TEXT,
                avg_hashrate_24h TEXT,
                online_workers INTEGER,
                offline_workers INTEGER,
                balance TEXT,
                last_income TEXT
            )
        ''')
        
        # Worker/Device status table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS worker_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                observer_url TEXT,
                worker_name TEXT,
                status TEXT,
                hashrate_10m TEXT,
                hashrate_1h TEXT,
                hashrate_24h TEXT,
                last_exchange_time TEXT
            )
        ''')
        
        # Daily earnings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observer_url TEXT,
                date TEXT,
                total_income TEXT,
                hashrate TEXT,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(observer_url, date)
            )
        ''')
        
        # Anomaly log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomaly_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                observer_url TEXT,
                anomaly_type TEXT,
                description TEXT,
                severity TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def scrape_data(self):
        """Main scraping function using direct table extraction"""
        print(f"\n{'='*60}")
        print(f"Starting scrape at {datetime.now()}")
        print(f"{'='*60}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"Navigating to {self.observer_url}...")
            page.goto(self.observer_url, wait_until="networkidle", timeout=60000)
            
            # Wait for tables to load
            time.sleep(5)
            
            # Extract data using JavaScript
            data = page.evaluate('''() => {
                const result = {
                    summary: {},
                    workers: [],
                    daily_earnings: []
                };
                
                // Extract summary from cards
                const cards = document.querySelectorAll('.home-cards_card__img__y9Us5, [class*="card"]');
                const bodyText = document.body.innerText;
                
                // Parse summary data from text
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
                
                // Extract workers from table
                const tables = document.querySelectorAll('table');
                for (const table of tables) {
                    const rows = table.querySelectorAll('tbody tr');
                    if (rows.length > 0) {
                        // Check if this is the workers table
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
                        // Check if this is the earnings table
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
            
        print(f"\nExtracted Data Summary:")
        print(f"  - Summary fields: {len(data['summary'])}")
        print(f"  - Workers found: {len(data['workers'])}")
        print(f"  - Daily earnings records: {len(data['daily_earnings'])}")
        
        # Save to database
        self.save_to_database(data)
        
        # Check for anomalies
        self.check_anomalies(data)
        
        print(f"\nScrape completed successfully!")
        return data
    
    def save_to_database(self, data):
        """Save scraped data to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save summary
        if data['summary']:
            cursor.execute('''
                INSERT INTO pool_summary 
                (observer_url, current_hashrate, avg_hashrate_24h, online_workers, 
                 offline_workers, balance, last_income)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.observer_url,
                data['summary'].get('current_hashrate', ''),
                data['summary'].get('avg_hashrate_24h', ''),
                data['summary'].get('online_workers', 0),
                data['summary'].get('offline_workers', 0),
                data['summary'].get('balance', ''),
                data['summary'].get('last_income', '')
            ))
            print(f"  ✓ Saved pool summary")
        
        # Save workers
        for worker in data['workers']:
            cursor.execute('''
                INSERT INTO worker_status 
                (observer_url, worker_name, status, hashrate_10m, hashrate_1h, 
                 hashrate_24h, last_exchange_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.observer_url,
                worker['name'],
                worker['status'],
                worker['hashrate_10m'],
                worker['hashrate_1h'],
                worker['hashrate_24h'],
                worker['last_exchange_time']
            ))
        print(f"  ✓ Saved {len(data['workers'])} worker records")
        
        # Save daily earnings
        for earning in data['daily_earnings']:
            cursor.execute('''
                INSERT OR REPLACE INTO daily_earnings 
                (observer_url, date, total_income, hashrate)
                VALUES (?, ?, ?, ?)
            ''', (
                self.observer_url,
                earning['date'],
                earning['total_income'],
                earning['hashrate']
            ))
        print(f"  ✓ Saved {len(data['daily_earnings'])} daily earnings records")
        
        conn.commit()
        conn.close()
    
    def check_anomalies(self, data):
        """Check for anomalies and log them"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        anomalies = []
        
        # Check for offline workers
        offline_count = int(data['summary'].get('offline_workers', 0))
        if offline_count > 0:
            offline_workers = [w['name'] for w in data['workers'] if w['status'] == 'OFFLINE']
            anomalies.append({
                'type': 'OFFLINE_WORKERS',
                'description': f"{offline_count} worker(s) offline: {', '.join(offline_workers) if offline_workers else 'Unknown'}",
                'severity': 'HIGH' if offline_count > 5 else 'MEDIUM'
            })
        
        # Check for hashrate drops
        cursor.execute('''
            SELECT current_hashrate FROM pool_summary 
            WHERE observer_url = ? 
            ORDER BY timestamp DESC LIMIT 10
        ''', (self.observer_url,))
        
        historical_hashrates = cursor.fetchall()
        if len(historical_hashrates) > 1:
            current_hr = data['summary'].get('current_hashrate', '0')
            current_value = self.parse_hashrate_to_ths(current_hr)
            
            avg_value = 0
            for hr in historical_hashrates[1:]:
                avg_value += self.parse_hashrate_to_ths(hr[0])
            avg_value = avg_value / len(historical_hashrates[1:]) if len(historical_hashrates) > 1 else current_value
            
            if current_value < avg_value * 0.8:
                drop_percent = ((avg_value - current_value) / avg_value) * 100
                anomalies.append({
                    'type': 'HASHRATE_DROP',
                    'description': f"Hashrate dropped {drop_percent:.1f}% (Current: {current_hr}, Avg: {avg_value:.2f} TH/s)",
                    'severity': 'HIGH' if drop_percent > 30 else 'MEDIUM'
                })
        
        # Save anomalies
        for anomaly in anomalies:
            cursor.execute('''
                INSERT INTO anomaly_log (observer_url, anomaly_type, description, severity)
                VALUES (?, ?, ?, ?)
            ''', (self.observer_url, anomaly['type'], anomaly['description'], anomaly['severity']))
            print(f"  ⚠ ANOMALY: {anomaly['description']} (Severity: {anomaly['severity']})")
        
        conn.commit()
        conn.close()
        
        return anomalies
    
    def parse_hashrate_to_ths(self, hashrate_str):
        """Convert hashrate string to TH/s"""
        if not hashrate_str:
            return 0
        
        match = re.search(r'([\d.]+)\s*([TGMP]?H/s)', hashrate_str)
        if not match:
            return 0
        
        value = float(match.group(1))
        unit = match.group(2)
        
        conversions = {
            'PH/s': 1000,
            'TH/s': 1,
            'GH/s': 0.001,
            'MH/s': 0.000001
        }
        
        return value * conversions.get(unit, 1)


def main():
    """Main function"""
    observer_url = "https://btcpool.kz/observer-link/4828a3fecdaa48eebfa475021b4e8d8d"
    
    scraper = BTCPoolScraperV2(observer_url)
    data = scraper.scrape_data()
    
    # Display results
    print(f"\n{'='*60}")
    print("SCRAPE RESULTS")
    print(f"{'='*60}")
    
    print("\n📊 Pool Summary:")
    for key, value in data['summary'].items():
        print(f"  {key}: {value}")
    
    print(f"\n👷 Workers ({len(data['workers'])} total):")
    online = [w for w in data['workers'] if w['status'] == 'ONLINE']
    offline = [w for w in data['workers'] if w['status'] == 'OFFLINE']
    print(f"  Online: {len(online)}")
    print(f"  Offline: {len(offline)}")
    
    if offline:
        print(f"\n  ⚠ Offline Workers:")
        for w in offline[:10]:  # Show first 10
            print(f"    - {w['name']}: {w['hashrate_24h']}")
    
    print(f"\n💰 Daily Earnings ({len(data['daily_earnings'])} records):")
    for earning in data['daily_earnings'][:5]:
        print(f"  {earning['date']}: {earning['total_income']} @ {earning['hashrate']}")


if __name__ == "__main__":
    main()
