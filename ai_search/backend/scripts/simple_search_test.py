#!/usr/bin/env python3
"""Simple search test"""

import sqlite3
import re
from pathlib import Path

def simple_search(query, limit=5):
    """Simple keyword search"""
    # Get the project root directory (three levels up from this script)
    project_root = Path(__file__).parent.parent.parent.parent
    db_path = project_root / "data" / "processed" / "documents.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Search in title and content
    search_query = f"%{query.lower()}%"
    
    cursor.execute('''
        SELECT url, title, content, domain, word_count 
        FROM documents 
        WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ?
        ORDER BY word_count DESC
        LIMIT ?
    ''', (search_query, search_query, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

# Test search
query = "python programming"
print(f"🔍 Searching for: '{query}'")
print("=" * 50)

results = simple_search(query, 5)

if results:
    print(f"Found {len(results)} results:")
    
    for i, (url, title, content, domain, word_count) in enumerate(results, 1):
        print(f"\n{i}. {title}")
        print(f"   URL: {url}")
        print(f"   Domain: {domain}")
        print(f"   Words: {word_count:,}")
        
        # Show content preview with highlighted query
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"   Preview: {preview}")

else:
    print("No results found!")

# Test with another query
print("\n" + "="*50)
query2 = "machine learning"
print(f"🔍 Searching for: '{query2}'")

results2 = simple_search(query2, 3)
print(f"Found {len(results2)} results")

for i, (url, title, content, domain, word_count) in enumerate(results2, 1):
    print(f"{i}. {title[:60]}... ({domain}) - {word_count} words")
