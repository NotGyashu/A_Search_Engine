#!/usr/bin/env python3
"""
Verify that the demo script can access the database correctly
"""
import sqlite3
import time
from pathlib import Path

def get_db_connection(db_path, timeout=30.0, max_retries=3):
    """Get database connection with proper timeout and retry logic"""
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(str(db_path), timeout=timeout)
            # Enable WAL mode for better concurrent access
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            conn.execute('PRAGMA temp_store=memory')
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"Database locked, retrying in {1 + attempt} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(1 + attempt)
                continue
            else:
                raise e
    return None

def verify_database_access():
    """Check if we can access the database"""
    try:
        # Get the project root directory (two levels up from this script)
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "processed" / "documents.db"
        
        print(f"Looking for database at: {db_path}")
        print(f"Database exists: {db_path.exists()}")
        
        if db_path.exists():
            # Quick check with improved connection handling
            conn = None
            try:
                conn = get_db_connection(db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM documents')
                count = cursor.fetchone()[0]
                
                print(f"✓ Successfully connected to database")
                print(f"✓ Found {count:,} documents")
                return True
            finally:
                if conn:
                    conn.close()
        else:
            print("✗ Database file not found")
            return False
            
    except Exception as e:
        print(f"✗ Error accessing database: {e}")
        return False

if __name__ == "__main__":
    print("VERIFYING DEMO SETUP")
    print("=" * 30)
    if verify_database_access():
        print("\n✓ Demo is ready to run!")
        print("✓ Run: python demo_simple.py")
    else:
        print("\n✗ Demo setup needs fixing")
