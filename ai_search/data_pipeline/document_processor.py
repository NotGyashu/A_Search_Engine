#!/usr/bin/env python3
"""
AI Search Engine - Document Processor
Processes crawler JSON files into clean, searchable documents

This script:
1. Reads crawler JSON files
2. Extracts and cleans HTML content
3. Removes duplicates and spam
4. Saves clean documents for indexing

Cost: $0 (all local processing)
Speed: ~1000 docs/second
"""

import json
import os
import sqlite3
import hashlib
import re
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse
import sys

# Add the project root to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from bs4 import BeautifulSoup
    print("✅ BeautifulSoup imported successfully")
except ImportError as e:
    print(f"❌ Error importing BeautifulSoup: {e}")
    print("Run: source ai_search/backend/venv/bin/activate && pip install beautifulsoup4")
    sys.exit(1)

@dataclass
class Document:
    """Clean document structure"""
    url: str
    title: str
    content: str
    domain: str
    word_count: int
    content_hash: str
    crawl_timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'title': self.title,
            'content': self.content,
            'domain': self.domain,
            'word_count': self.word_count,
            'content_hash': self.content_hash,
            'crawl_timestamp': self.crawl_timestamp
        }

class DocumentProcessor:
    """Processes crawler data into clean, searchable documents"""
    
    def __init__(self, data_dir: str = "data", output_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.output_dir / "documents.db"
        self.init_database()
        
        # Stats
        self.stats = {
            'total_files': 0,
            'total_pages': 0,
            'processed_docs': 0,
            'duplicates_removed': 0,
            'empty_content_removed': 0,
            'total_words': 0
        }
        
    def init_database(self):
        """Initialize SQLite database for documents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                domain TEXT,
                word_count INTEGER,
                content_hash TEXT UNIQUE,
                crawl_timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for fast searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON documents(domain)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON documents(content_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_words ON documents(word_count)')
        
        conn.commit()
        conn.close()
        
    def clean_html_content(self, html: str) -> Tuple[str, str]:
        """Extract clean text and title from HTML"""
        if not html or html.strip() == '':
            return '', ''
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Extract title
            title = ''
            if soup.title:
                title = soup.title.get_text().strip()
            elif soup.h1:
                title = soup.h1.get_text().strip()
            
            # Extract main content
            content = soup.get_text()
            
            # Clean up text
            content = re.sub(r'\s+', ' ', content)  # Multiple spaces to single
            content = re.sub(r'\n+', '\n', content)  # Multiple newlines to single
            content = content.strip()
            
            # Remove very short content (likely navigation/spam)
            if len(content.split()) < 50:  # Less than 50 words
                return '', title
                
            return content, title
            
        except Exception as e:
            print(f"⚠️  Error processing HTML: {e}")
            return '', ''
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate hash for duplicate detection"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, content_hash: str) -> bool:
        """Check if document already exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM documents WHERE content_hash = ?', (content_hash,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def save_document(self, doc: Document) -> bool:
        """Save document to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO documents (url, title, content, domain, word_count, content_hash, crawl_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (doc.url, doc.title, doc.content, doc.domain, doc.word_count, doc.content_hash, doc.crawl_timestamp))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            # Duplicate URL or hash
            return False
        finally:
            conn.close()
    
    def process_crawler_file(self, file_path: Path) -> int:
        """Process a single crawler JSON file"""
        print(f"📄 Processing: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return 0
        
        processed_count = 0
        
        # Handle different JSON structures
        pages = []
        if isinstance(data, list):
            pages = data
        elif isinstance(data, dict) and 'pages' in data:
            pages = data['pages']
        elif isinstance(data, dict):
            # Single page
            pages = [data]
        
        for page_data in pages:
            self.stats['total_pages'] += 1
            
            # Extract fields - handle base64 encoded HTML
            url = page_data.get('url', '')
            html_b64 = page_data.get('html_base64', '')
            html = page_data.get('html', page_data.get('content', ''))
            timestamp = page_data.get('timestamp', page_data.get('crawl_time', ''))
            
            # Decode base64 HTML if present
            if html_b64 and not html:
                try:
                    html = base64.b64decode(html_b64).decode('utf-8')
                except Exception as e:
                    print(f"⚠️  Error decoding base64 HTML for {url}: {e}")
                    continue
            
            if not url or not html:
                continue
            
            # Clean content
            content, title = self.clean_html_content(html)
            
            if not content:
                self.stats['empty_content_removed'] += 1
                continue
            
            # Create document
            domain = urlparse(url).netloc
            word_count = len(content.split())
            content_hash = self.calculate_content_hash(content)
            
            # Check for duplicates
            if self.is_duplicate(content_hash):
                self.stats['duplicates_removed'] += 1
                continue
            
            doc = Document(
                url=url,
                title=title,
                content=content,
                domain=domain,
                word_count=word_count,
                content_hash=content_hash,
                crawl_timestamp=timestamp
            )
            
            # Save document
            if self.save_document(doc):
                processed_count += 1
                self.stats['processed_docs'] += 1
                self.stats['total_words'] += word_count
        
        return processed_count
    
    def process_all_files(self):
        """Process all crawler JSON files"""
        print("🚀 Starting document processing...")
        print(f"📂 Input directory: {self.data_dir}")
        print(f"💾 Output directory: {self.output_dir}")
        
        # Find all JSON files
        json_files = list((self.data_dir / "raw").glob("*.json"))
        
        if not json_files:
            print("❌ No JSON files found in data/raw/")
            return
        
        print(f"📊 Found {len(json_files)} JSON files")
        self.stats['total_files'] = len(json_files)
        
        # Process each file
        for file_path in json_files:
            count = self.process_crawler_file(file_path)
            print(f"   ✅ Processed {count} documents from {file_path.name}")
        
        self.print_final_stats()
    
    def print_final_stats(self):
        """Print processing statistics"""
        print("\n" + "="*50)
        print("📊 PROCESSING COMPLETE!")
        print("="*50)
        print(f"📁 Files processed: {self.stats['total_files']}")
        print(f"📄 Total pages found: {self.stats['total_pages']}")
        print(f"✅ Clean documents saved: {self.stats['processed_docs']}")
        print(f"🗑️  Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"❌ Empty content removed: {self.stats['empty_content_removed']}")
        print(f"📝 Total words indexed: {self.stats['total_words']:,}")
        print(f"💾 Database: {self.db_path}")
        
        if self.stats['processed_docs'] > 0:
            avg_words = self.stats['total_words'] / self.stats['processed_docs']
            print(f"📈 Average words per document: {avg_words:.0f}")
        
        print("\n🎯 Next steps:")
        print("1. Run: python ai_search/data_pipeline/free_search.py")
        print("2. This will create the searchable AI index!")

def main():
    """Main entry point"""
    print("🔍 AI Search Engine - Document Processor")
    print("=========================================")
    
    processor = DocumentProcessor()
    processor.process_all_files()

if __name__ == "__main__":
    main()
