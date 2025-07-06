#!/usr/bin/env python3
"""
Force unlock SQLite database by clearing any hanging connections
"""
import sqlite3
import time
from pathlib import Path

def force_unlock_database():
    """Force unlock the database by creating a quick connection and closing it"""
    try:
        # Get the project root directory (two levels up from this script)
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "processed" / "documents.db"
        
        print(f"Attempting to unlock database: {db_path}")
        
        # Try to connect with a very short timeout
        conn = sqlite3.connect(str(db_path), timeout=1.0)
        
        # Switch to WAL mode which allows better concurrent access
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        
        # Force checkpoint to clean up WAL files
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        
        conn.close()
        
        print("✓ Database unlocked successfully")
        return True
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("✗ Database is still locked")
            print("  Try closing any other applications that might be using the database")
            print("  Or restart your terminal/IDE")
            return False
        else:
            print(f"✗ Error: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("DATABASE UNLOCK UTILITY")
    print("=" * 30)
    
    if force_unlock_database():
        print("\n✓ You can now run the demo:")
        print("  python demo_simple.py")
        print("  python demo.py")
    else:
        print("\n✗ Manual intervention required:")
        print("  1. Close any database viewers/editors")
        print("  2. Restart VS Code/terminal")
        print("  3. Try running the demo again")
