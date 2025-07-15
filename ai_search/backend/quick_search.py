#!/usr/bin/env python3
"""
Quick Search Command - One-shot search without interactive mode
===============================================================

Usage: python3 quick_search.py "your search query"
"""

import sqlite3
import time
import sys
from pathlib import Path

def search_documents(query, limit=10):
    """Search through documents"""
    project_root = Path(__file__).parent.parent.parent
    db_path = Path(__file__).parent / "data" / "processed" / "documents.db"
    
    try:
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        cursor = conn.cursor()
        
        search_pattern = f"%{query.lower()}%"
        start_time = time.time()
        
        cursor.execute('''
            SELECT title, domain, word_count, url,
                   CASE 
                       WHEN LOWER(title) LIKE ? THEN 3
                       WHEN LOWER(content) LIKE ? THEN 1
                       ELSE 0
                   END as relevance_score
            FROM documents 
            WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ?
            ORDER BY relevance_score DESC, word_count DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, search_pattern, search_pattern, limit))
        
        results = cursor.fetchall()
        search_time = time.time() - start_time
        
        conn.close()
        return results, search_time
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return [], 0

def main():
    if len(sys.argv) < 2:
        print("🔍 AI SEARCH ENGINE - QUICK SEARCH")
        print("=" * 35)
        print("Usage:")
        print("  python3 quick_search.py \"python programming\"")
        print("  python3 quick_search.py \"machine learning\"")
        print("  python3 quick_search.py \"web development\"")
        print()
        print("Or use interactive mode:")
        print("  python3 search_terminal.py")
        return
    
    query = " ".join(sys.argv[1:])
    print(f"🔍 Searching for: '{query}'")
    print("=" * 50)
    
    results, search_time = search_documents(query)
    
    if not results:
        print(f"❌ No results found for '{query}'")
        print("💡 Try different keywords")
        return
    
    print(f"⚡ Found {len(results)} results in {search_time:.3f}s")
    print()
    
    for i, (title, domain, word_count, url, relevance) in enumerate(results, 1):
        print(f"🔍 {i}. {title[:70]}{'...' if len(title) > 70 else ''}")
        print(f"   🌐 {domain} | 📄 {word_count:,} words")
        
        if relevance >= 3:
            print("   ⭐ Title match")
        
        print(f"   🔗 {url}")
        print()

if __name__ == "__main__":
    main()
