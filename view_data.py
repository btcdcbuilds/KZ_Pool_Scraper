#!/usr/bin/env python3
"""
Database Viewer for BTC Pool Data
Quick tool to view collected data
"""
import sqlite3
from datetime import datetime, timedelta

def view_summary(db_path="btcpool_data.db"):
    """View pool summary statistics"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("POOL SUMMARY - LATEST")
    print("="*70)
    
    cursor.execute('''
        SELECT timestamp, current_hashrate, avg_hashrate_24h, 
               online_workers, offline_workers, balance, last_income
        FROM pool_summary 
        ORDER BY timestamp DESC LIMIT 1
    ''')
    
    result = cursor.fetchone()
    if result:
        print(f"Timestamp:           {result[0]}")
        print(f"Current Hashrate:    {result[1]}")
        print(f"24h Avg Hashrate:    {result[2]}")
        print(f"Online Workers:      {result[3]}")
        print(f"Offline Workers:     {result[4]}")
        print(f"Balance:             {result[5]}")
        print(f"Last Income:         {result[6]}")
    else:
        print("No data found")
    
    conn.close()

def view_workers(db_path="btcpool_data.db", show_offline_only=False):
    """View worker status"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("WORKER STATUS - LATEST")
    print("="*70)
    
    query = '''
        SELECT worker_name, status, hashrate_10m, hashrate_1h, hashrate_24h
        FROM worker_status 
        WHERE timestamp = (SELECT MAX(timestamp) FROM worker_status)
    '''
    
    if show_offline_only:
        query += " AND status = 'OFFLINE'"
    
    query += " ORDER BY status DESC, worker_name"
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    if results:
        print(f"\n{'Worker Name':<30} {'Status':<10} {'10m':<15} {'1h':<15} {'24h':<15}")
        print("-"*90)
        for row in results:
            print(f"{row[0]:<30} {row[1]:<10} {row[2]:<15} {row[3]:<15} {row[4]:<15}")
        print(f"\nTotal: {len(results)} workers")
    else:
        print("No workers found")
    
    conn.close()

def view_earnings(db_path="btcpool_data.db", days=7):
    """View daily earnings"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print(f"DAILY EARNINGS - LAST {days} DAYS")
    print("="*70)
    
    cursor.execute('''
        SELECT date, total_income, hashrate
        FROM daily_earnings 
        ORDER BY date DESC
        LIMIT ?
    ''', (days,))
    
    results = cursor.fetchall()
    
    if results:
        print(f"\n{'Date':<30} {'Income':<20} {'Hashrate':<20}")
        print("-"*70)
        total_income = 0
        for row in results:
            print(f"{row[0]:<30} {row[1]:<20} {row[2]:<20}")
            # Try to extract numeric value for total
            try:
                income_val = float(row[1].replace('BTC', '').strip())
                total_income += income_val
            except:
                pass
        
        if total_income > 0:
            print("-"*70)
            print(f"{'TOTAL':<30} {total_income:.8f} BTC")
    else:
        print("No earnings data found")
    
    conn.close()

def view_anomalies(db_path="btcpool_data.db", hours=24):
    """View recent anomalies"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print(f"ANOMALIES - LAST {hours} HOURS")
    print("="*70)
    
    cursor.execute('''
        SELECT timestamp, anomaly_type, description, severity
        FROM anomaly_log 
        WHERE timestamp > datetime('now', '-' || ? || ' hours')
        ORDER BY timestamp DESC
    ''', (hours,))
    
    results = cursor.fetchall()
    
    if results:
        print(f"\n{'Timestamp':<25} {'Type':<20} {'Severity':<10} {'Description':<30}")
        print("-"*90)
        for row in results:
            print(f"{row[0]:<25} {row[1]:<20} {row[3]:<10} {row[2][:30]:<30}")
        print(f"\nTotal: {len(results)} anomalies")
    else:
        print("No anomalies detected")
    
    conn.close()

def view_stats(db_path="btcpool_data.db"):
    """View database statistics"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)
    
    # Count records in each table
    cursor.execute("SELECT COUNT(*) FROM pool_summary")
    summary_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM worker_status")
    worker_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_earnings")
    earnings_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM anomaly_log")
    anomaly_count = cursor.fetchone()[0]
    
    # Get date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM pool_summary")
    date_range = cursor.fetchone()
    
    print(f"\nTotal Records:")
    print(f"  Pool Summary:     {summary_count}")
    print(f"  Worker Status:    {worker_count}")
    print(f"  Daily Earnings:   {earnings_count}")
    print(f"  Anomalies:        {anomaly_count}")
    
    if date_range[0]:
        print(f"\nData Range:")
        print(f"  First Record:     {date_range[0]}")
        print(f"  Latest Record:    {date_range[1]}")
    
    conn.close()

def main():
    """Main viewer interface"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "summary":
            view_summary()
        elif command == "workers":
            view_workers()
        elif command == "offline":
            view_workers(show_offline_only=True)
        elif command == "earnings":
            view_earnings()
        elif command == "anomalies":
            view_anomalies()
        elif command == "stats":
            view_stats()
        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        # Show everything
        view_stats()
        view_summary()
        view_workers(show_offline_only=True)
        view_earnings(days=7)
        view_anomalies(hours=24)

def print_usage():
    print("\nUsage: python view_data.py [command]")
    print("\nCommands:")
    print("  summary     - View latest pool summary")
    print("  workers     - View all workers")
    print("  offline     - View offline workers only")
    print("  earnings    - View daily earnings")
    print("  anomalies   - View recent anomalies")
    print("  stats       - View database statistics")
    print("  (no args)   - View all data")

if __name__ == "__main__":
    main()
