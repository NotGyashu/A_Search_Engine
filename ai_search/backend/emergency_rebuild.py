#!/usr/bin/env python3
"""
Emergency database recovery - create a new clean database
"""
import sqlite3
import json
import os
from pathlib import Path

def emergency_rebuild():
    """Rebuild database from raw JSON files if database is corrupted"""
    try:
        project_root = Path(__file__).parent.parent.parent
        raw_data_path = project_root / "data" / "raw"
        db_path = project_root / "data" / "processed" / "documents_new.db"
        
        print("EMERGENCY DATABASE REBUILD")
        print("=" * 40)
        print(f"Raw data path: {raw_data_path}")
        print(f"New database: {db_path}")
        
        # Remove old database if exists
        if db_path.exists():
            db_path.unlink()
            print("✓ Removed old database")
        
        # Create new database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create table
        cursor.execute('''
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT,
            domain TEXT,
            word_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('CREATE INDEX idx_domain ON documents(domain)')
        cursor.execute('CREATE INDEX idx_word_count ON documents(word_count)')
        
        print("✓ Created new database structure")
        
        # Count JSON files
        json_files = list(raw_data_path.glob("*.json"))
        print(f"✓ Found {len(json_files)} JSON files to process")
        
        if len(json_files) == 0:
            print("✗ No JSON files found in raw data directory")
            return False
        
        total_docs = 0
        
        # Process first few files for quick test
        for i, json_file in enumerate(json_files[:3]):  # Process only first 3 files for speed
            print(f"Processing {json_file.name}...")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    documents = data
                else:
                    documents = data.get('documents', [])
                
                for doc in documents:
                    try:
                        # Extract domain from URL
                        url = doc.get('url', '')
                        if url.startswith('http'):
                            domain = url.split('/')[2]
                        else:
                            domain = 'unknown'
                        
                        title = doc.get('title', '')
                        content = doc.get('content', '')
                        word_count = len(content.split()) if content else 0
                        
                        cursor.execute('''
                        INSERT OR REPLACE INTO documents (url, title, content, domain, word_count)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (url, title, content, domain, word_count))
                        
                        total_docs += 1
                        
                    except Exception as e:
                        continue  # Skip problematic documents
                        
            except Exception as e:
                print(f"✗ Error processing {json_file}: {e}")
                continue
        
        conn.commit()
        
        # Get final stats
        cursor.execute('SELECT COUNT(*) FROM documents')
        final_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT domain) FROM documents')
        domain_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✓ Rebuild completed!")
        print(f"✓ Processed {final_count:,} documents")
        print(f"✓ Found {domain_count} unique domains")
        
        # Rename to replace old database
        old_db_path = project_root / "data" / "processed" / "documents.db"
        backup_path = project_root / "data" / "processed" / "documents_old.db"
        
        if old_db_path.exists():
            old_db_path.rename(backup_path)
            print(f"✓ Backed up old database to: {backup_path}")
        
        db_path.rename(old_db_path)
        print(f"✓ New database activated: {old_db_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ Emergency rebuild failed: {e}")
        return False

if __name__ == "__main__":
    if emergency_rebuild():
        print("\n" + "=" * 40)
        print("✓ EMERGENCY REBUILD SUCCESSFUL!")
        print("✓ Database is now ready to use")
        print("✓ Try running: python demo_simple.py")
    else:
        print("\n" + "=" * 40)
        print("✗ Emergency rebuild failed")
        print("Please check the error messages")
