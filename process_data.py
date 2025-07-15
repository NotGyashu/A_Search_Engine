#!/usr/bin/env python3
"""
Mini Search Engine - Data Processing Pipeline
Processes 6.3GB of crawler data into searchable database
"""

import json
import sqlite3
import re
import hashlib
from pathlib import Path
import time
import sys

class SearchEngineProcessor:
    def __init__(self):
        self.project_root = Path("/home/gyashu/projects/mini_search_engine")
        self.raw_data_dir = self.project_root / "RawHTMLdata"
        self.processed_dir = self.project_root / "ai_search" / "backend" / "data" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.processed_dir / "documents.db"
        
        self.stats = {
            'total_files': 0,
            'total_pages': 0,
            'processed_docs': 0,
            'duplicates_removed': 0,
            'empty_content_removed': 0,
            'errors': 0
        }
        
    def init_database(self):
        """Initialize the search database"""
        print("🗄️  Initializing search database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop existing table if it exists (fresh start)
        cursor.execute('DROP TABLE IF EXISTS documents')
        
        cursor.execute('''
        CREATE TABLE documents (
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
        
        # Create indexes for fast searching
        cursor.execute('CREATE INDEX idx_content ON documents(content)')
        cursor.execute('CREATE INDEX idx_domain ON documents(domain)')
        cursor.execute('CREATE INDEX idx_url ON documents(url)')
        
        conn.commit()
        conn.close()
        print("✅ Database schema created")
        
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            if '://' in url:
                domain = url.split('://')[1].split('/')[0]
            else:
                domain = url.split('/')[0]
            return domain.lower()
        except:
            return "unknown"
    
    def clean_html(self, html: str) -> tuple[str, str]:
        """Clean HTML and extract title and content"""
        try:
            # Extract title
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = ""
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'<[^>]+>', '', title)  # Remove HTML tags from title
                title = re.sub(r'\s+', ' ', title).strip()
            
            # Remove unwanted elements
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
            
            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            
            # Clean up text
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Quality check
            if len(text) < 50:  # Too short
                return "", title
                
            return text, title
            
        except Exception as e:
            return "", ""
    
    def process_batch_file(self, file_path: Path, conn) -> int:
        """Process a single JSON batch file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stats['errors'] += 1
            return 0
        
        processed_count = 0
        cursor = conn.cursor()
        
        # Prepare batch insert
        documents_to_insert = []
        
        if isinstance(data, list):
            pages = data
        else:
            pages = [data] if isinstance(data, dict) else []
        
        for page_data in pages:
            self.stats['total_pages'] += 1
            
            url = page_data.get('url', '').strip()
            html_content = page_data.get('content', '').strip()
            timestamp = page_data.get('timestamp', '')
            
            if not url or not html_content:
                continue
                
            # Clean content
            content, title = self.clean_html(html_content)
            
            if not content:
                self.stats['empty_content_removed'] += 1
                continue
            
            # Extract domain
            domain = self.extract_domain(url)
            
            # Calculate hash for duplicate detection
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Prepare document data
            doc_data = (
                url,
                title,
                content,
                domain,
                len(content.split()),
                content_hash,
                timestamp
            )
            
            documents_to_insert.append(doc_data)
        
        # Batch insert documents
        if documents_to_insert:
            try:
                cursor.executemany('''
                INSERT OR IGNORE INTO documents 
                (url, title, content, domain, word_count, content_hash, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', documents_to_insert)
                
                processed_count = cursor.rowcount
                self.stats['processed_docs'] += processed_count
                self.stats['duplicates_removed'] += len(documents_to_insert) - processed_count
                
                conn.commit()
                
            except Exception as e:
                self.stats['errors'] += 1
                
        return processed_count
    
    def process_all_files(self):
        """Process all batch files"""
        batch_files = sorted(self.raw_data_dir.glob('*.json'))
        total_files = len(batch_files)
        
        print(f"🚀 Processing {total_files} batch files...")
        print(f"📁 Source: {self.raw_data_dir}")
        print(f"🎯 Target: {self.db_path}")
        
        start_time = time.time()
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        
        for i, file_path in enumerate(batch_files, 1):
            self.stats['total_files'] += 1
            
            # Process file
            processed = self.process_batch_file(file_path, conn)
            
            # Progress update
            if i % 100 == 0 or i == total_files:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (total_files - i) / rate if rate > 0 else 0
                
                print(f"📊 Progress: {i:4d}/{total_files} files | "
                      f"{self.stats['processed_docs']:6d} docs | "
                      f"{rate:.1f} files/sec | "
                      f"ETA: {eta/60:.1f}m")
        
        conn.close()
        self.print_final_stats(time.time() - start_time)
    
    def print_final_stats(self, elapsed_time: float):
        """Print final processing statistics"""
        print("\n" + "="*70)
        print("🎉 SEARCH ENGINE DATA PROCESSING COMPLETE!")
        print("="*70)
        
        print(f"⏱️  Processing time: {elapsed_time/60:.1f} minutes")
        print(f"📁 Files processed: {self.stats['total_files']:,}")
        print(f"📄 Pages found: {self.stats['total_pages']:,}")
        print(f"✅ Documents indexed: {self.stats['processed_docs']:,}")
        print(f"🗑️  Duplicates removed: {self.stats['duplicates_removed']:,}")
        print(f"📝 Empty content removed: {self.stats['empty_content_removed']:,}")
        print(f"❌ Errors: {self.stats['errors']:,}")
        
        # Database statistics
        if self.db_path.exists():
            db_size = self.db_path.stat().st_size / (1024*1024)
            print(f"💾 Database size: {db_size:.1f} MB")
            
            # Query database for stats
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT domain) FROM documents")
            total_domains = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(word_count) FROM documents")
            total_words = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT AVG(word_count) FROM documents")
            avg_words = cursor.fetchone()[0] or 0
            
            print(f"\n🔍 SEARCH ENGINE DATABASE STATS:")
            print(f"   📑 {total_docs:,} documents ready for search")
            print(f"   🌐 {total_domains:,} unique domains crawled")
            print(f"   📝 {total_words:,} total words indexed")
            print(f"   📊 {avg_words:.0f} average words per document")
            
            # Sample some domains
            cursor.execute("SELECT domain, COUNT(*) FROM documents GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 10")
            top_domains = cursor.fetchall()
            
            print(f"\n🏆 TOP DOMAINS:")
            for domain, count in top_domains:
                print(f"   • {domain}: {count:,} pages")
            
            conn.close()

def main():
    print("🔧 MINI SEARCH ENGINE - DATA PROCESSOR")
    print("Converting 6.3GB of crawler data into searchable database")
    print("="*70)
    
    processor = SearchEngineProcessor()
    
    # Verify raw data
    if not processor.raw_data_dir.exists():
        print(f"❌ Raw data directory not found: {processor.raw_data_dir}")
        return
    
    json_files = list(processor.raw_data_dir.glob('*.json'))
    if not json_files:
        print(f"❌ No JSON files found in {processor.raw_data_dir}")
        return
    
    print(f"📊 Found {len(json_files)} batch files to process")
    print(f"💾 Raw data size: 6.3GB")
    
    # Confirm processing
    response = input("\n🚀 Start processing? This will take 10-30 minutes. (y/N): ")
    if response.lower() != 'y':
        print("👋 Processing cancelled.")
        return
    
    # Process data
    processor.init_database()
    processor.process_all_files()
    
    print("\n🎯 YOUR SEARCH ENGINE IS READY!")
    print("Next steps:")
    print("1. cd ai_search/backend && source venv/bin/activate")
    print("2. python3 demo.py")
    print("3. python3 quick_search.py 'your search query'")
    print("4. python3 search_terminal.py")

if __name__ == "__main__":
    main()
