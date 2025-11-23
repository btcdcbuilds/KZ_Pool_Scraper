#!/usr/bin/env python3
"""
Upload KZ Pool data from SQLite to Supabase
Reads data from the working scraper's SQLite database and uploads to Supabase
"""
import os
import sqlite3
import requests
import logging
from datetime import datetime, timezone
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SupabaseUploader:
    def __init__(self, account_name, company="BTCDC Builds", client_name=None, 
                 country="Kazakhstan", site="KZ Pool", db_path="btcpool_data.db"):
        self.account_name = account_name
        self.company = company
        self.client_name = client_name or account_name
        self.country = country
        self.site = site
        self.db_path = db_path
        
        # Supabase config
        self.supabase_url = os.getenv('SUPABASE_URL').rstrip('/')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.api_url = f"{self.supabase_url}/rest/v1"
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def upsert(self, table, data):
        try:
            headers = self.headers.copy()
            headers['Prefer'] = 'resolution=merge-duplicates'
            response = requests.post(f"{self.api_url}/{table}", headers=headers, json=data)
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error upserting: {e}")
            return False
    
    def insert_batch(self, table, data_list):
        try:
            response = requests.post(f"{self.api_url}/{table}", headers=self.headers, json=data_list)
            if response.status_code in [200, 201]:
                logger.info(f"✓ Inserted {len(data_list)} records into {table}")
                return True
            else:
                logger.error(f"Failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
    
    def parse_hashrate(self, hashrate_str):
        """Convert hashrate string to TH/s integer"""
        if not hashrate_str:
            return 0
        match = re.search(r'([\d.]+)\s*([TGMP]?H/s)', hashrate_str)
        if not match:
            return 0
        value = float(match.group(1))
        unit = match.group(2)
        conversions = {'PH/s': 1000, 'TH/s': 1, 'GH/s': 0.001, 'MH/s': 0.000001}
        return int(value * conversions.get(unit, 1))
    
    def upload_latest(self):
        """Upload latest data from SQLite to Supabase"""
        logger.info(f"📤 Uploading data from {self.db_path}...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest summary
        cursor.execute('SELECT * FROM pool_summary ORDER BY timestamp DESC LIMIT 1')
        summary = cursor.fetchone()
        
        if not summary:
            logger.error("No summary data found")
            return False
        
        # 1. Upsert account
        account_data = {
            'account_name': self.account_name,
            'coin_type': 'BTC',
            'is_active': True,
            'company': self.company,
            'site': self.site,
            'account_type': 'kzpool',
            'group_name': self.client_name,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if summary['balance']:
            try:
                account_data['balance'] = float(summary['balance'].replace('BTC', '').strip())
            except:
                pass
        
        if summary['last_income']:
            try:
                account_data['earn_24_hours'] = float(summary['last_income'].replace('BTC', '').strip())
            except:
                pass
        
        self.upsert('accounts', account_data)
        logger.info(f"✓ Upserted account: {self.account_name}")
        
        # 2. Insert hashrate
        hashrate_data = {
            'account_name': self.account_name,
            'hashrate_10m': self.parse_hashrate(summary['current_hashrate']),
            'hashrate_1h': self.parse_hashrate(summary['current_hashrate']),
            'hashrate_1d': self.parse_hashrate(summary['avg_hashrate_24h']),
            'worker_count': int(summary['online_workers']) + int(summary['offline_workers']),
            'active_workers': int(summary['online_workers']),
            'reject_rate': 0.0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.upsert('hashrates', hashrate_data)
        logger.info(f"✓ Inserted hashrate data")
        
        # 3. Insert devices (workers)
        cursor.execute('''
            SELECT * FROM worker_status 
            WHERE timestamp = (SELECT MAX(timestamp) FROM worker_status)
        ''')
        workers = cursor.fetchall()
        
        if workers:
            device_records = []
            for worker in workers[:200]:
                # Generate device_id from account_name and worker_name
                device_id = f"KZ_{self.account_name}_{worker['worker_name']}".replace(' ', '_')
                
                device_data = {
                    'device_id': device_id,
                    'serial_number': worker['worker_name'],  # Use worker name as serial
                    'account_name': self.account_name,
                    'worker_name': worker['worker_name'],
                    'device_type': 'ASIC',
                    'status': worker['status'].lower(),
                    'manufacturer': 'Unknown',
                    'model': 'Unknown',
                    'site': self.site,
                    'location': self.country,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                device_records.append(device_data)
            
            # Insert in batches
            for i in range(0, len(device_records), 50):
                batch = device_records[i:i+50]
                self.insert_batch('devices', batch)
        
        # 4. Insert income tracking
        cursor.execute('SELECT * FROM daily_earnings ORDER BY date DESC LIMIT 30')
        earnings = cursor.fetchall()
        
        if earnings:
            income_records = []
            for earning in earnings:
                try:
                    income_data = {
                        'account_name': self.account_name,
                        'date': earning['date'],
                        'btc_amount': float(earning['total_income'].replace('BTC', '').strip()),
                        'usd_value': 0.0,
                        'source': 'KZ Pool',
                        'transaction_type': 'mining_reward',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    income_records.append(income_data)
                except:
                    continue
            
            if income_records:
                self.insert_batch('income_tracking', income_records)
        
        # 5. Insert alerts for offline workers
        if int(summary['offline_workers']) > 0:
            alert_data = {
                'account_name': self.account_name,
                'alert_type': 'offline_workers',
                'severity': 'high' if int(summary['offline_workers']) > 5 else 'medium',
                'message': f"{summary['offline_workers']} workers offline",
                'resolved': False,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            self.upsert('alerts', alert_data)
            logger.info(f"⚠ Logged alert: {summary['offline_workers']} offline workers")
        
        conn.close()
        logger.info("✅ Upload completed successfully!")
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload KZ Pool data to Supabase')
    parser.add_argument('--account', required=True, help='Account name')
    parser.add_argument('--company', default='BTCDC Builds', help='Company name')
    parser.add_argument('--client', help='Client name')
    parser.add_argument('--country', default='Kazakhstan', help='Country')
    parser.add_argument('--site', default='KZ Pool', help='Site name')
    parser.add_argument('--db', default='btcpool_data.db', help='SQLite database path')
    
    args = parser.parse_args()
    
    uploader = SupabaseUploader(
        account_name=args.account,
        company=args.company,
        client_name=args.client,
        country=args.country,
        site=args.site,
        db_path=args.db
    )
    
    uploader.upload_latest()


if __name__ == '__main__':
    main()
