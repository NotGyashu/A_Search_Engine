#!/usr/bin/env python3
"""
Database repair and optimization script
"""
import sqlite3
import shutil
import time
from pathlib import Path

def repair_database():
    """Repair and optimize the database"""
    try:
        # Get the project root directory (two levels up from this script)
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "processed" / "documents.db"
        backup_path = project_root / "data" / "processed" / "documents_backup.db"
        
        print(f"Repairing database: {db_path}")
        
        # Create backup
        print("Creating backup...")
        shutil.copy2(str(db_path), str(backup_path))
        print(f"✓ Backup created: {backup_path}")
        
        # Connect and repair
        print("Connecting to database...")
        conn = sqlite3.connect(str(db_path), timeout=1.0)
        
        print("Running database maintenance...")
        
        # Check integrity
        cursor = conn.cursor()
        cursor.execute('PRAGMA integrity_check')
        integrity = cursor.fetchone()[0]
        print(f"Integrity check: {integrity}")
        
        # Optimize database
        cursor.execute('PRAGMA optimize')
        cursor.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        
        # Switch to WAL mode for better concurrency
        cursor.execute('PRAGMA journal_mode=WAL')
        
        # Set optimal pragma settings
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA cache_size=10000')
        cursor.execute('PRAGMA temp_store=memory')
        cursor.execute('PRAGMA mmap_size=268435456')  # 256MB
        
        # Test basic operations
        cursor.execute('SELECT COUNT(*) FROM documents')
        count = cursor.fetchone()[0]
        print(f"✓ Document count: {count:,}")
        
        cursor.execute('SELECT COUNT(DISTINCT domain) FROM documents')
        domains = cursor.fetchone()[0]
        print(f"✓ Unique domains: {domains}")
        
        conn.close()
        
        print("✓ Database repair completed successfully")
        print(f"✓ Backup available at: {backup_path}")
        return True
        
    except Exception as e:
        print(f"✗ Error during repair: {e}")
        return False

if __name__ == "__main__":
    print("DATABASE REPAIR UTILITY")
    print("=" * 30)
    
    if repair_database():
        print("\n✓ Database is ready!")
        print("✓ You can now run:")
        print("  python demo_simple.py")
        print("  python demo.py")
    else:
        print("\n✗ Repair failed")
        print("Please check the error messages above")
