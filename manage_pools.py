#!/usr/bin/env python3
"""
Pool Management CLI Tool
Manage pool configurations and metadata
"""
import sqlite3
import json
import sys
import os
from datetime import datetime
import argparse

class PoolManager:
    def __init__(self, db_path='/data/btcpool_data.db'):
        self.db_path = db_path
        self.ensure_database()
    
    def ensure_database(self):
        """Ensure database and tables exist"""
        if not os.path.exists(self.db_path):
            print(f"⚠️  Database not found: {self.db_path}")
            print("Creating new database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
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
        conn.commit()
        conn.close()
    
    def list_pools(self, active_only=False):
        """List all pools"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM pool_metadata'
        if active_only:
            query += ' WHERE active = 1'
        query += ' ORDER BY pool_id'
        
        cursor.execute(query)
        pools = cursor.fetchall()
        conn.close()
        
        if not pools:
            print("No pools found.")
            return
        
        print(f"\n{'='*80}")
        print(f"{'Pool ID':<15} {'Name':<20} {'Client':<20} {'Country':<15} {'Status':<10}")
        print(f"{'='*80}")
        
        for pool in pools:
            status = "ACTIVE" if pool['active'] else "INACTIVE"
            print(f"{pool['pool_id']:<15} {pool['pool_name']:<20} {pool['client_name']:<20} {pool['country']:<15} {status:<10}")
        
        print(f"{'='*80}")
        print(f"Total pools: {len(pools)}")
        print()
    
    def show_pool(self, pool_id):
        """Show detailed information about a pool"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM pool_metadata WHERE pool_id = ?', (pool_id,))
        pool = cursor.fetchone()
        conn.close()
        
        if not pool:
            print(f"❌ Pool not found: {pool_id}")
            return
        
        print(f"\n{'='*60}")
        print(f"Pool Details: {pool_id}")
        print(f"{'='*60}")
        print(f"Pool Name:       {pool['pool_name']}")
        print(f"Observer URL:    {pool['observer_url']}")
        print(f"Client Name:     {pool['client_name']}")
        print(f"Country:         {pool['country']}")
        print(f"Company:         {pool['company']}")
        print(f"Location:        {pool['location']}")
        print(f"Contact Email:   {pool['contact_email']}")
        print(f"Tags:            {pool['tags']}")
        print(f"Active:          {'Yes' if pool['active'] else 'No'}")
        print(f"Created:         {pool['created_at']}")
        print(f"Updated:         {pool['updated_at']}")
        print(f"{'='*60}\n")
    
    def add_pool(self, pool_id, pool_name, observer_url, client_name='', 
                 country='', company='', location='', contact_email='', tags=None):
        """Add a new pool"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO pool_metadata 
                (pool_id, pool_name, observer_url, client_name, country, company, 
                 location, contact_email, tags, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (pool_id, pool_name, observer_url, client_name, country, company,
                  location, contact_email, json.dumps(tags or [])))
            
            conn.commit()
            print(f"✓ Pool added successfully: {pool_id}")
        except sqlite3.IntegrityError:
            print(f"❌ Pool already exists: {pool_id}")
        finally:
            conn.close()
    
    def update_pool(self, pool_id, **kwargs):
        """Update pool metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build update query
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if value is not None:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            print("No updates provided.")
            conn.close()
            return
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(pool_id)
        
        query = f"UPDATE pool_metadata SET {', '.join(updates)} WHERE pool_id = ?"
        
        cursor.execute(query, values)
        
        if cursor.rowcount == 0:
            print(f"❌ Pool not found: {pool_id}")
        else:
            conn.commit()
            print(f"✓ Pool updated successfully: {pool_id}")
        
        conn.close()
    
    def activate_pool(self, pool_id):
        """Activate a pool"""
        self.update_pool(pool_id, active=1)
    
    def deactivate_pool(self, pool_id):
        """Deactivate a pool"""
        self.update_pool(pool_id, active=0)
    
    def delete_pool(self, pool_id, confirm=False):
        """Delete a pool (requires confirmation)"""
        if not confirm:
            print(f"⚠️  This will permanently delete pool '{pool_id}' and all its data!")
            response = input("Type 'DELETE' to confirm: ")
            if response != 'DELETE':
                print("Deletion cancelled.")
                return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete from all tables
        cursor.execute('DELETE FROM pool_metadata WHERE pool_id = ?', (pool_id,))
        cursor.execute('DELETE FROM pool_summary WHERE pool_id = ?', (pool_id,))
        cursor.execute('DELETE FROM worker_status WHERE pool_id = ?', (pool_id,))
        cursor.execute('DELETE FROM daily_earnings WHERE pool_id = ?', (pool_id,))
        cursor.execute('DELETE FROM anomaly_log WHERE pool_id = ?', (pool_id,))
        
        if cursor.rowcount == 0:
            print(f"❌ Pool not found: {pool_id}")
        else:
            conn.commit()
            print(f"✓ Pool deleted successfully: {pool_id}")
        
        conn.close()
    
    def export_config(self, output_file='pools_config.json'):
        """Export pools to JSON config file"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM pool_metadata ORDER BY pool_id')
        pools = cursor.fetchall()
        conn.close()
        
        config = {
            "pools": [],
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "total_pools": len(pools)
            }
        }
        
        for pool in pools:
            config["pools"].append({
                "pool_id": pool['pool_id'],
                "pool_name": pool['pool_name'],
                "observer_url": pool['observer_url'],
                "client_name": pool['client_name'],
                "country": pool['country'],
                "company": pool['company'],
                "location": pool['location'],
                "contact_email": pool['contact_email'],
                "active": bool(pool['active']),
                "scrape_interval_minutes": 10,
                "tags": json.loads(pool['tags']) if pool['tags'] else [],
                "created_at": pool['created_at'],
                "updated_at": pool['updated_at']
            })
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Configuration exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='KZ Pool Scraper - Pool Management')
    parser.add_argument('--db', default=os.getenv('DB_PATH', '/data/btcpool_data.db'),
                        help='Database path')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all pools')
    list_parser.add_argument('--active-only', action='store_true', help='Show only active pools')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show pool details')
    show_parser.add_argument('pool_id', help='Pool ID')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add new pool')
    add_parser.add_argument('--pool-id', required=True, help='Pool ID')
    add_parser.add_argument('--name', required=True, help='Pool name')
    add_parser.add_argument('--url', required=True, help='Observer URL')
    add_parser.add_argument('--client', default='', help='Client name')
    add_parser.add_argument('--country', default='', help='Country')
    add_parser.add_argument('--company', default='', help='Company')
    add_parser.add_argument('--location', default='', help='Location')
    add_parser.add_argument('--email', default='', help='Contact email')
    add_parser.add_argument('--tags', nargs='*', help='Tags')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update pool metadata')
    update_parser.add_argument('pool_id', help='Pool ID')
    update_parser.add_argument('--name', help='Pool name')
    update_parser.add_argument('--url', help='Observer URL')
    update_parser.add_argument('--client', help='Client name')
    update_parser.add_argument('--country', help='Country')
    update_parser.add_argument('--company', help='Company')
    update_parser.add_argument('--location', help='Location')
    update_parser.add_argument('--email', help='Contact email')
    
    # Activate command
    activate_parser = subparsers.add_parser('activate', help='Activate pool')
    activate_parser.add_argument('pool_id', help='Pool ID')
    
    # Deactivate command
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate pool')
    deactivate_parser.add_argument('pool_id', help='Pool ID')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete pool')
    delete_parser.add_argument('pool_id', help='Pool ID')
    delete_parser.add_argument('--yes', action='store_true', help='Skip confirmation')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export pools to JSON')
    export_parser.add_argument('--output', default='pools_config.json', help='Output file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = PoolManager(args.db)
    
    if args.command == 'list':
        manager.list_pools(args.active_only)
    
    elif args.command == 'show':
        manager.show_pool(args.pool_id)
    
    elif args.command == 'add':
        manager.add_pool(
            args.pool_id,
            args.name,
            args.url,
            args.client,
            args.country,
            args.company,
            args.location,
            args.email,
            args.tags
        )
    
    elif args.command == 'update':
        updates = {}
        if args.name: updates['pool_name'] = args.name
        if args.url: updates['observer_url'] = args.url
        if args.client: updates['client_name'] = args.client
        if args.country: updates['country'] = args.country
        if args.company: updates['company'] = args.company
        if args.location: updates['location'] = args.location
        if args.email: updates['contact_email'] = args.email
        
        manager.update_pool(args.pool_id, **updates)
    
    elif args.command == 'activate':
        manager.activate_pool(args.pool_id)
    
    elif args.command == 'deactivate':
        manager.deactivate_pool(args.pool_id)
    
    elif args.command == 'delete':
        manager.delete_pool(args.pool_id, args.yes)
    
    elif args.command == 'export':
        manager.export_config(args.output)


if __name__ == '__main__':
    main()
