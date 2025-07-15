#!/usr/bin/env python3
"""
Interactive Terminal Search Interface
=====================================

Use your AI search engine directly from the command line!
"""

import sqlite3
import time
import sys
from pathlib import Path

def get_db_connection(db_path):
    """Get database connection"""
    try:
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        return conn
    except sqlite3.OperationalError as e:
        print(f"❌ Database error: {e}")
        return None

def search_documents(query, limit=10):
    """Search through documents using keyword matching"""
    db_path = Path(__file__).parent / "data" / "processed" / "documents.db"
    
    conn = get_db_connection(db_path)
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        search_pattern = f"%{query.lower()}%"
        
        start_time = time.time()
        
        # Search in title and content
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
        
        return results, search_time
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return [], 0
    finally:
        if conn:
            conn.close()

def display_results(results, search_time, query):
    """Display search results in a nice format"""
    if not results:
        print(f"❌ No results found for '{query}'")
        print("💡 Try different keywords or check spelling")
        return
    
    print(f"⚡ Found {len(results)} results in {search_time:.3f}s for '{query}'")
    print("=" * 60)
    
    for i, (title, domain, word_count, url, relevance) in enumerate(results, 1):
        # Truncate title if too long
        display_title = title[:70] + "..." if len(title) > 70 else title
        
        print(f"🔍 {i}. {display_title}")
        print(f"   🌐 Domain: {domain}")
        print(f"   📄 Words: {word_count:,}")
        print(f"   🔗 URL: {url[:80]}{'...' if len(url) > 80 else ''}")
        
        if relevance >= 3:
            print("   ⭐ Title match (high relevance)")
        
        print()

def get_database_stats():
    """Get quick database statistics"""
    db_path = Path(__file__).parent / "data" / "processed" / "documents.db"
    
    conn = get_db_connection(db_path)
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM documents')
        total_docs = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT domain) FROM documents')
        unique_domains = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(word_count) FROM documents')
        total_words = cursor.fetchone()[0]
        
        return {
            'docs': total_docs,
            'domains': unique_domains,
            'words': total_words
        }
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def show_help():
    """Show help information"""
    print("🔍 AI SEARCH ENGINE - TERMINAL INTERFACE")
    print("=" * 40)
    print("Commands:")
    print("  search <query>    - Search for documents")
    print("  stats            - Show database statistics")
    print("  help             - Show this help")
    print("  quit/exit        - Exit the search engine")
    print()
    print("Examples:")
    print("  search python programming")
    print("  search machine learning")
    print("  search web development")
    print()

def main():
    """Main interactive search loop"""
    print("🎉 WELCOME TO YOUR AI SEARCH ENGINE!")
    print("🔍 Interactive Terminal Search Interface")
    print()
    
    # Show database stats
    stats = get_database_stats()
    if stats:
        print(f"📊 Database: {stats['docs']:,} documents, {stats['domains']} domains, {stats['words']:,} words")
    
    print("💡 Type 'help' for commands or 'quit' to exit")
    print("=" * 60)
    
    while True:
        try:
            # Get user input
            user_input = input("\n🔍 Search> ").strip()
            
            if not user_input:
                continue
                
            # Parse command
            parts = user_input.lower().split()
            command = parts[0] if parts else ""
            
            if command in ['quit', 'exit', 'q']:
                print("👋 Thanks for using your AI search engine!")
                break
                
            elif command == 'help' or command == '?':
                show_help()
                
            elif command == 'stats':
                stats = get_database_stats()
                if stats:
                    print(f"📊 SEARCH ENGINE STATISTICS")
                    print(f"   📄 Total documents: {stats['docs']:,}")
                    print(f"   🌐 Unique domains: {stats['domains']}")
                    print(f"   📝 Total words: {stats['words']:,}")
                    print(f"   💰 Operating cost: $0.00/month")
                
            elif command == 'search' or not command.startswith(('help', 'stats', 'quit', 'exit')):
                # Extract search query
                if command == 'search':
                    query = ' '.join(parts[1:]) if len(parts) > 1 else ""
                else:
                    query = user_input
                
                if not query:
                    print("❌ Please provide a search query")
                    print("💡 Example: search python programming")
                    continue
                
                # Perform search
                print(f"🔍 Searching for '{query}'...")
                results, search_time = search_documents(query)
                display_results(results, search_time, query)
                
            else:
                print(f"❌ Unknown command: '{command}'")
                print("💡 Type 'help' for available commands")
                
        except KeyboardInterrupt:
            print("\n👋 Thanks for using your AI search engine!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
