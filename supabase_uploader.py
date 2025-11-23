#!/usr/bin/env python3
"""
Supabase Uploader for BTC Pool Data
This script uploads data from local SQLite to Supabase
"""
import sqlite3
import json
import os
from datetime import datetime

# Note: Install supabase client with: pip install supabase
# from supabase import create_client, Client

class SupabaseUploader:
    def __init__(self, supabase_url, supabase_key, local_db_path="btcpool_data.db"):
        """
        Initialize Supabase connection
        
        Args:
            supabase_url: Your Supabase project URL
            supabase_key: Your Supabase API key
            local_db_path: Path to local SQLite database
        """
        self.local_db_path = local_db_path
        # Uncomment when ready to use:
        # self.supabase: Client = create_client(supabase_url, supabase_key)
        print("Supabase uploader initialized (currently in mock mode)")
    
    def setup_supabase_tables(self):
        """
        Create tables in Supabase (SQL to run in Supabase SQL editor)
        """
        sql_schema = """
        -- Pool Summary Table
        CREATE TABLE IF NOT EXISTS pool_summary (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            observer_url TEXT NOT NULL,
            current_hashrate TEXT,
            avg_hashrate_24h TEXT,
            online_workers INTEGER,
            offline_workers INTEGER,
            balance TEXT,
            last_income TEXT
        );
        
        -- Worker Status Table
        CREATE TABLE IF NOT EXISTS worker_status (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            observer_url TEXT NOT NULL,
            worker_name TEXT NOT NULL,
            status TEXT,
            hashrate_10m TEXT,
            hashrate_1h TEXT,
            hashrate_24h TEXT,
            last_exchange_time TEXT
        );
        
        -- Daily Earnings Table
        CREATE TABLE IF NOT EXISTS daily_earnings (
            id BIGSERIAL PRIMARY KEY,
            observer_url TEXT NOT NULL,
            date TEXT NOT NULL,
            total_income TEXT,
            hashrate TEXT,
            recorded_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(observer_url, date)
        );
        
        -- Anomaly Log Table
        CREATE TABLE IF NOT EXISTS anomaly_log (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            observer_url TEXT NOT NULL,
            anomaly_type TEXT,
            description TEXT,
            severity TEXT
        );
        
        -- Create indexes for better query performance
        CREATE INDEX IF NOT EXISTS idx_pool_summary_timestamp ON pool_summary(timestamp);
        CREATE INDEX IF NOT EXISTS idx_worker_status_timestamp ON worker_status(timestamp);
        CREATE INDEX IF NOT EXISTS idx_daily_earnings_date ON daily_earnings(date);
        CREATE INDEX IF NOT EXISTS idx_anomaly_log_timestamp ON anomaly_log(timestamp);
        """
        
        print("Run this SQL in your Supabase SQL Editor:")
        print("="*60)
        print(sql_schema)
        print("="*60)
        
        return sql_schema
    
    def upload_latest_data(self):
        """Upload the latest scrape data to Supabase"""
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest pool summary
        cursor.execute('''
            SELECT * FROM pool_summary 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        summary = cursor.fetchone()
        
        if summary:
            summary_data = {
                'timestamp': summary['timestamp'],
                'observer_url': summary['observer_url'],
                'current_hashrate': summary['current_hashrate'],
                'avg_hashrate_24h': summary['avg_hashrate_24h'],
                'online_workers': summary['online_workers'],
                'offline_workers': summary['offline_workers'],
                'balance': summary['balance'],
                'last_income': summary['last_income']
            }
            
            print(f"Would upload pool summary: {summary_data}")
            # Uncomment when ready:
            # self.supabase.table('pool_summary').insert(summary_data).execute()
        
        # Get latest worker status
        cursor.execute('''
            SELECT * FROM worker_status 
            WHERE timestamp = (SELECT MAX(timestamp) FROM worker_status)
        ''')
        workers = cursor.fetchall()
        
        worker_data = []
        for worker in workers:
            worker_data.append({
                'timestamp': worker['timestamp'],
                'observer_url': worker['observer_url'],
                'worker_name': worker['worker_name'],
                'status': worker['status'],
                'hashrate_10m': worker['hashrate_10m'],
                'hashrate_1h': worker['hashrate_1h'],
                'hashrate_24h': worker['hashrate_24h'],
                'last_exchange_time': worker['last_exchange_time']
            })
        
        print(f"Would upload {len(worker_data)} worker records")
        # Uncomment when ready:
        # if worker_data:
        #     self.supabase.table('worker_status').insert(worker_data).execute()
        
        # Get latest anomalies
        cursor.execute('''
            SELECT * FROM anomaly_log 
            WHERE timestamp > datetime('now', '-10 minutes')
        ''')
        anomalies = cursor.fetchall()
        
        anomaly_data = []
        for anomaly in anomalies:
            anomaly_data.append({
                'timestamp': anomaly['timestamp'],
                'observer_url': anomaly['observer_url'],
                'anomaly_type': anomaly['anomaly_type'],
                'description': anomaly['description'],
                'severity': anomaly['severity']
            })
        
        print(f"Would upload {len(anomaly_data)} anomaly records")
        # Uncomment when ready:
        # if anomaly_data:
        #     self.supabase.table('anomaly_log').insert(anomaly_data).execute()
        
        conn.close()
        
        return {
            'summary': summary_data if summary else None,
            'workers': len(worker_data),
            'anomalies': len(anomaly_data)
        }
    
    def sync_daily_earnings(self):
        """Sync all daily earnings to Supabase"""
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM daily_earnings')
        earnings = cursor.fetchall()
        
        earnings_data = []
        for earning in earnings:
            earnings_data.append({
                'observer_url': earning['observer_url'],
                'date': earning['date'],
                'total_income': earning['total_income'],
                'hashrate': earning['hashrate'],
                'recorded_at': earning['recorded_at']
            })
        
        print(f"Would sync {len(earnings_data)} daily earnings records")
        # Uncomment when ready:
        # if earnings_data:
        #     for earning in earnings_data:
        #         self.supabase.table('daily_earnings').upsert(earning).execute()
        
        conn.close()
        
        return len(earnings_data)


def main():
    """Example usage"""
    # These would come from environment variables in production
    SUPABASE_URL = os.getenv("SUPABASE_URL", "your-project-url.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
    
    uploader = SupabaseUploader(SUPABASE_URL, SUPABASE_KEY)
    
    # Show the SQL schema to create in Supabase
    print("\n1. First, create tables in Supabase:")
    uploader.setup_supabase_tables()
    
    print("\n2. Upload latest data:")
    result = uploader.upload_latest_data()
    print(f"Upload result: {result}")
    
    print("\n3. Sync daily earnings:")
    count = uploader.sync_daily_earnings()
    print(f"Synced {count} earnings records")


if __name__ == "__main__":
    main()
