#!/usr/bin/env python3
"""
WSL-compatible database access script that bypasses file locking issues
"""
import sqlite3
import shutil
import time
from pathlib import Path

def create_memory_database():
    """Create an in-memory copy of the database to bypass file locks"""
    try:
        # Get the project root directory (two levels up from this script)
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "processed" / "documents.db"
        
        print(f"Copying database to memory: {db_path}")
        
        # Create in-memory database
        memory_conn = sqlite3.connect(':memory:')
        
        # Try to copy from file database with minimal timeout
        try:
            file_conn = sqlite3.connect(str(db_path), timeout=0.1)
            file_conn.backup(memory_conn)
            file_conn.close()
            print("✓ Successfully copied database to memory")
        except sqlite3.OperationalError:
            # If file is locked, try to read it directly and recreate
            print("File locked, attempting alternative approach...")
            return None
        
        return memory_conn
        
    except Exception as e:
        print(f"✗ Error creating memory database: {e}")
        return None

def get_stats_from_memory():
    """Get statistics using in-memory database"""
    memory_conn = create_memory_database()
    if not memory_conn:
        return None, None
    
    try:
        cursor = memory_conn.cursor()
        
        # Get comprehensive stats
        cursor.execute('SELECT COUNT(*) FROM documents')
        total_docs = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT domain) FROM documents')
        unique_domains = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(word_count) FROM documents')
        total_words = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(word_count) FROM documents')
        avg_words = cursor.fetchone()[0]
        
        cursor.execute('SELECT domain, COUNT(*) as count FROM documents GROUP BY domain ORDER BY count DESC LIMIT 10')
        top_domains = cursor.fetchall()
        
        memory_conn.close()
        
        return {
            'total_docs': total_docs,
            'unique_domains': unique_domains,
            'total_words': total_words,
            'avg_words': avg_words,
            'top_domains': top_domains
        }, True
        
    except Exception as e:
        print(f"✗ Error getting stats: {e}")
        if memory_conn:
            memory_conn.close()
        return None, False

def search_in_memory(query):
    """Perform search using in-memory database"""
    memory_conn = create_memory_database()
    if not memory_conn:
        return []
    
    try:
        cursor = memory_conn.cursor()
        search_pattern = f"%{query.lower()}%"
        
        cursor.execute('''
            SELECT title, domain, word_count, url
            FROM documents 
            WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ?
            ORDER BY word_count DESC
            LIMIT 3
        ''', (search_pattern, search_pattern))
        
        results = cursor.fetchall()
        memory_conn.close()
        return results
        
    except Exception as e:
        print(f"✗ Error searching: {e}")
        if memory_conn:
            memory_conn.close()
        return []

if __name__ == "__main__":
    print("TESTING MEMORY DATABASE APPROACH")
    print("=" * 40)
    
    # Test stats
    stats, success = get_stats_from_memory()
    if success and stats:
        print(f"✓ Found {stats['total_docs']:,} documents")
        print(f"✓ Found {stats['unique_domains']} unique domains")
        print(f"✓ Total words: {stats['total_words']:,}")
    else:
        print("✗ Failed to get stats")
    
    # Test search
    results = search_in_memory("python")
    if results:
        print(f"✓ Search found {len(results)} results")
    else:
        print("✗ Search failed")
