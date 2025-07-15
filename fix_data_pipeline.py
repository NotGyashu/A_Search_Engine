#!/usr/bin/env python3
"""
Emergency Data Pipeline Fix
Processes your 6.3GB of raw crawler data into a working search engine
"""

import json
import sqlite3
import base64
import re
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import sys
from datetime import datetime

class DataPipelineFixer:
    """Fixes the broken data pipeline by processing RawHTMLdata"""
    
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
            'errors': 0,
            'duplicates_removed': 0,
            'empty_content_removed': 0
        }
        
    def init_database(self):
        """Initialize SQLite database for documents"""
        print("🗄️  Initializing database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create documents table
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
        
        # Create index for fast searching
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_content_fts ON documents(content)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_domain ON documents(domain)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized")
        
    def clean_html_content(self, html: str) -> tuple[str, str]:
        """Extract clean text and title from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else ""
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Basic content quality check
            if len(text) < 100:  # Too short
                return "", title
                
            return text, title
            
        except Exception as e:
            print(f"⚠️  HTML parsing error: {e}")
            return "", ""
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate hash for duplicate detection"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_duplicate(self, content_hash: str, conn) -> bool:
        """Check if document already exists"""
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM documents WHERE content_hash = ?", (content_hash,))
        return cursor.fetchone() is not None
    
    def save_document(self, doc_data: dict, conn) -> bool:
        """Save document to database"""
        try:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO documents (url, title, content, domain, word_count, content_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_data['url'],
                doc_data['title'],
                doc_data['content'],
                doc_data['domain'],
                doc_data['word_count'],
                doc_data['content_hash'],
                doc_data['timestamp']
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate
        except Exception as e:
            print(f"❌ Error saving document: {e}")
            return False
    
    def process_batch_file(self, file_path: Path, conn) -> int:
        """Process a single batch JSON file"""
        print(f"📄 Processing: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            self.stats['errors'] += 1
            return 0
        
        processed_count = 0
        
        # Handle different JSON structures
        pages = []
        if isinstance(data, list):
            pages = data
        elif isinstance(data, dict) and 'pages' in data:
            pages = data['pages']
        elif isinstance(data, dict):
            pages = [data]
        
        for page_data in pages:
            self.stats['total_pages'] += 1
            
            # Extract fields
            url = page_data.get('url', '')
            html_content = page_data.get('content', '')
            timestamp = page_data.get('timestamp', '')
            
            # Handle base64 encoded content if present
            if not html_content and 'html_base64' in page_data:
                try:
                    html_content = base64.b64decode(page_data['html_base64']).decode('utf-8')
                except Exception as e:
                    print(f"⚠️  Error decoding base64 for {url}: {e}")
                    continue
            
            if not url or not html_content:
                continue
            
            # Clean content
            content, title = self.clean_html_content(html_content)
            
            if not content:
                self.stats['empty_content_removed'] += 1
                continue
            
            # Create document
            domain = urlparse(url).netloc
            content_hash = self.calculate_content_hash(content)
            
            # Check for duplicates
            if self.is_duplicate(content_hash, conn):
                self.stats['duplicates_removed'] += 1
                continue
            
            doc_data = {
                'url': url,
                'title': title,
                'content': content,
                'domain': domain,
                'word_count': len(content.split()),
                'content_hash': content_hash,
                'timestamp': timestamp
            }
            
            if self.save_document(doc_data, conn):
                processed_count += 1
                self.stats['processed_docs'] += 1
                
                if processed_count % 100 == 0:
                    print(f"   ✅ Processed {processed_count} documents from {file_path.name}")
        
        return processed_count
    
    def process_all_files(self):
        """Process all crawler JSON files"""
        print(f"🚀 Starting to process {len(list(self.raw_data_dir.glob('*.json')))} batch files...")
        print(f"📁 Raw data: {self.raw_data_dir}")
        print(f"📁 Output: {self.db_path}")
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        
        batch_files = sorted(self.raw_data_dir.glob('*.json'))
        
        for i, file_path in enumerate(batch_files, 1):
            self.stats['total_files'] += 1
            processed = self.process_batch_file(file_path, conn)
            
            if i % 50 == 0 or i == len(batch_files):
                print(f"📊 Progress: {i}/{len(batch_files)} files | {self.stats['processed_docs']} docs processed")
        
        conn.close()
        self.print_final_stats()
    
    def print_final_stats(self):
        """Print processing statistics"""
        print("\n" + "="*60)
        print("🎉 DATA PIPELINE PROCESSING COMPLETE!")
        print("="*60)
        print(f"📁 Total batch files processed: {self.stats['total_files']}")
        print(f"📄 Total pages found: {self.stats['total_pages']}")
        print(f"✅ Documents successfully processed: {self.stats['processed_docs']}")
        print(f"🗑️  Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"📝 Empty content removed: {self.stats['empty_content_removed']}")
        print(f"❌ Errors encountered: {self.stats['errors']}")
        print(f"🗄️  Database location: {self.db_path}")
        print(f"📊 Database size: {self.db_path.stat().st_size / (1024*1024):.1f} MB")
        
        # Test database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT domain) FROM documents")
        total_domains = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(word_count) FROM documents")
        total_words = cursor.fetchone()[0] or 0
        
        print(f"🔍 Final database stats:")
        print(f"   • {total_docs:,} documents indexed")
        print(f"   • {total_domains:,} unique domains")
        print(f"   • {total_words:,} total words")
        
        conn.close()

def main():
    print("🔧 MINI SEARCH ENGINE - DATA PIPELINE FIXER")
    print("=" * 50)
    
    fixer = DataPipelineFixer()
    
    # Check if raw data exists
    if not fixer.raw_data_dir.exists():
        print(f"❌ Raw data directory not found: {fixer.raw_data_dir}")
        return
    
    # Count files
    json_files = list(fixer.raw_data_dir.glob('*.json'))
    if not json_files:
        print(f"❌ No JSON files found in {fixer.raw_data_dir}")
        return
    
    print(f"📊 Found {len(json_files)} JSON batch files")
    print(f"💾 Total raw data size: 6.3GB")
    
    # Initialize and process
    fixer.init_database()
    fixer.process_all_files()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Run: python3 demo.py")
    print("2. Test search: python3 quick_search.py 'python programming'")
    print("3. Interactive mode: python3 search_terminal.py")

if __name__ == "__main__":
    main()
