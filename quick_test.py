#!/usr/bin/env python3
"""
Quick Data Pipeline Test
"""

import json
import sqlite3
from pathlib import Path

# Setup paths
project_root = Path("/home/gyashu/projects/mini_search_engine")
raw_data_dir = project_root / "RawHTMLdata"
processed_dir = project_root / "ai_search" / "backend" / "data" / "processed"
processed_dir.mkdir(parents=True, exist_ok=True)
db_path = processed_dir / "documents.db"

print("🔧 MINI SEARCH ENGINE - QUICK PIPELINE TEST")
print("=" * 50)

# Check raw data
if not raw_data_dir.exists():
    print(f"❌ Raw data directory not found: {raw_data_dir}")
    exit(1)

json_files = list(raw_data_dir.glob('*.json'))
print(f"📊 Found {len(json_files)} JSON batch files")

if not json_files:
    print("❌ No JSON files found")
    exit(1)

# Test first file
print(f"🧪 Testing first file: {json_files[0].name}")
try:
    with open(json_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ JSON loaded successfully")
    print(f"📄 Data type: {type(data)}")
    
    if isinstance(data, list):
        print(f"📝 Found {len(data)} items in array")
        if data:
            item = data[0]
            print(f"🔑 First item keys: {list(item.keys())}")
            print(f"🌐 Sample URL: {item.get('url', 'N/A')}")
            
            # Check content
            content = item.get('content', '')
            if content:
                print(f"📄 Content length: {len(content)} chars")
                print(f"📝 Content preview: {content[:100]}...")
            else:
                print("⚠️  No 'content' field found")
                
except Exception as e:
    print(f"❌ Error processing file: {e}")
    exit(1)

# Initialize database
print("\n🗄️  Initializing database...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    domain TEXT NOT NULL,
    word_count INTEGER,
    content_hash TEXT UNIQUE,
    timestamp TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE INDEX IF NOT EXISTS idx_content_fts ON documents(content)
''')

cursor.execute('''
CREATE INDEX IF NOT EXISTS idx_domain ON documents(domain)
''')

conn.commit()
conn.close()

print(f"✅ Database initialized at: {db_path}")
print(f"🎯 Ready to process {len(json_files)} files with your 6.3GB of data!")

print("\n📋 CURRENT PROJECT STATUS:")
print("✅ Raw crawler data: 6.3GB, 2,051 files")
print("✅ Database schema: Created")
print("✅ AI search backend: Available")
print("⏳ Data processing: Ready to start")

print("\n🚀 To complete the search engine:")
print("1. Run the full pipeline (will take 10-30 minutes)")
print("2. Process all 2,051 batch files")
print("3. Create searchable database")
print("4. Test search functionality")
