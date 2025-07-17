import re
import json
import sqlite3
import hashlib
import multiprocessing
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Generator, Dict, List, Tuple, Optional
import base64
import traceback
import time
import logging

from language_detector import LanguageDetector  # Add language detection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("preprocessor.log"),
        logging.StreamHandler()
    ]
)

# Configuration
MAX_WORKERS = multiprocessing.cpu_count()
BATCH_SIZE = 50_000
MAX_DOC_SIZE = 10_000_000
MIN_CONTENT_LENGTH =    200
BLOCKED_DOMAINS = {"adserver.com", "tracking.net", "analytics.pro"}
MAX_QUEUE_SIZE = 100_000

@dataclass
class Document:
    url: str
    content: str
    domain: str
    content_hash: str
    timestamp: str = ""
    title: str = ""
    word_count: int = 0

class FastDataCleaner:
    """Optimized HTML cleaner with format handling"""
    
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    SCRIPT_STYLE_PATTERN = re.compile(
        r'<(script|style|noscript|footer|header|nav)[^>]*>.*?</\1>',
        re.DOTALL | re.IGNORECASE
    )
    EXTRA_SPACES_PATTERN = re.compile(r'\s+')
    TITLE_PATTERN = re.compile(
        r'<title[^>]*>(.*?)</title>', 
        re.DOTALL | re.IGNORECASE
    )
    URL_PATTERN = re.compile(
        r'https?://([^/]+)',
        re.IGNORECASE
    )
    
    @classmethod
    def extract_title(cls, html: str) -> str:
        """Extract document title"""
        match = cls.TITLE_PATTERN.search(html)
        return cls.clean_text(match.group(1).strip()[:500]) if match else ""
    
    @classmethod
    def extract_domain(cls, url: str) -> str:
        """Extract domain from URL"""
        match = cls.URL_PATTERN.search(url)
        if match:
            domain = match.group(1).lower()
            return domain[4:] if domain.startswith("www.") else domain
        return "unknown"
    
    @classmethod
    def clean_html(cls, html: str) -> str:
        """Clean HTML content"""
        cleaned = cls.SCRIPT_STYLE_PATTERN.sub(' ', html)
        cleaned = cls.HTML_TAG_PATTERN.sub(' ', cleaned)
        return cls.EXTRA_SPACES_PATTERN.sub(' ', cleaned).strip()
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        """Clean and normalize text"""
        return cls.EXTRA_SPACES_PATTERN.sub(' ', text).strip()

def read_json_file(file_path: Path) -> Generator[dict, None, None]:
    """Flexible JSON reader with robust encoding handling"""
    # Try reading as JSON array
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
            if isinstance(data, list):
                yield from data
                return
            elif "pages" in data:  # Common crawler format
                yield from data["pages"]
                return
    except Exception as e:
        logging.debug(f"JSON array read failed for {file_path.name}: {str(e)}")

    # Fallback to JSON lines format
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logging.debug(f"JSON lines read failed for {file_path.name}: {str(e)}")

    # Final fallback: binary mode with error replacement
    try:
        with open(file_path, "rb") as f:
            for line in f:
                try:
                    decoded = line.decode("utf-8", errors="replace")
                    yield json.loads(decoded)
                except:
                    continue
    except Exception as e:
        logging.error(f"Critical error reading {file_path.name}: {str(e)}")

def process_document(raw_doc: dict) -> Tuple[Optional[Document], Optional[str]]:
    skip_reason = None
    try:
        # Robust URL extraction
        url = ""
        for key in ["url", "page_url", "uri", "link"]:
            if key in raw_doc:
                url = str(raw_doc[key]).strip()
                if url:
                    break
        
        if not url:
            skip_reason = "Missing URL"
            return None, skip_reason
        
        # Robust content extraction
        html = ""
        for key in ["content", "html", "body", "text"]:
            if key in raw_doc:
                content = raw_doc[key]
                if isinstance(content, str):
                    html = content
                elif isinstance(content, bytes):
                    try:
                        html = content.decode("utf-8", errors="replace")
                    except:
                        pass
                if html:
                    break
                    
        # Handle base64 content
        if not html and "html_base64" in raw_doc:
            try:
                html = base64.b64decode(raw_doc["html_base64"]).decode("utf-8", errors="replace")
            except:
                pass
        
        if not html:
            skip_reason = "Missing content"
            return None, skip_reason
        
        # 🌐 LANGUAGE DETECTION: Skip non-English content
        if not LanguageDetector.is_english(html, url):
            skip_reason = "Non-English content"
            return None, skip_reason
        
        # Handle large documents (truncate instead of skip)
        if len(html) > MAX_DOC_SIZE:
            original_size = len(html)
            html = html[:MAX_DOC_SIZE]
            skip_reason = f"Document truncated ({original_size} > {MAX_DOC_SIZE})"
        
        # Clean content and generate metadata
        cleaned_content = FastDataCleaner.clean_html(html)
        content_hash = hashlib.md5(cleaned_content.encode()).hexdigest()
        word_count = len(cleaned_content.split())
        
        # Create document structure with ALL fields
        doc = Document(
            url=url,
            content=cleaned_content,
            domain=FastDataCleaner.extract_domain(url),
            content_hash=content_hash,
            timestamp=raw_doc.get("timestamp", raw_doc.get("crawl_time", "")),
            title=FastDataCleaner.extract_title(html),
            word_count=word_count
        )
        
        # Skip if content is too short
        if len(doc.content) < MIN_CONTENT_LENGTH:
            skip_reason = f"Content too short ({len(doc.content)} < {MIN_CONTENT_LENGTH})"
            return None, skip_reason
        
        # Skip blocked domains
        if doc.domain in BLOCKED_DOMAINS:
            skip_reason = f"Blocked domain ({doc.domain})"
            return None, skip_reason
        
        return doc, skip_reason  # Return doc even if truncated (with reason)
    except Exception as e:
        skip_reason = f"Processing error: {str(e)}"
        logging.debug(f"Error processing document: {traceback.format_exc()}")
        return None, skip_reason

def file_processor(file_path: Path, result_queue: multiprocessing.Queue):
    """Process a single file and put results in queue"""
    stats = defaultdict(int)
    processed = 0
    skip_reasons = defaultdict(int)
    sample_skipped_doc = None
    
    try:
        for i, raw_doc in enumerate(read_json_file(file_path)):
            stats["total_docs"] += 1
            doc, skip_reason = process_document(raw_doc)
            
            if doc:
                result_queue.put(doc)
                processed += 1
                stats["processed"] += 1
            else:
                stats["skipped"] += 1
                if skip_reason:
                    skip_reasons[skip_reason] += 1
                
                # Save first skipped document for analysis
                if sample_skipped_doc is None:
                    sample_skipped_doc = raw_doc
    except Exception as e:
        stats["errors"] += 1
        logging.error(f"Error processing {file_path.name}: {str(e)}")
    
    stats["processed_docs"] = processed
    stats["skip_reasons"] = dict(skip_reasons)
    
    # Include sample document for diagnostics
    stats["sample_skipped"] = sample_skipped_doc
    result_queue.put(("STATS", stats, file_path.name))

def database_writer(db_path: Path, input_queue: multiprocessing.Queue, stats_queue: multiprocessing.Queue):
    """Dedicated database writer process"""
    conn = sqlite3.connect(db_path, timeout=60)
    cursor = conn.cursor()
    
    # Set performance optimizations
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA cache_size=-10000;")
    cursor.execute("PRAGMA busy_timeout=30000;")
    
    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY,
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
    conn.commit()
    
    batch = []
    processed_count = 0
    start_time = time.time()
    
    logging.info("Database writer started...")
    
    while True:
        try:
            item = input_queue.get(timeout=300)
            
            if item == "DONE":
                break
                
            if isinstance(item, tuple) and item[0] == "STATS":
                _, stats, filename = item
                stats_queue.put((filename, stats))
                continue
                
            batch.append(item)
            
            if len(batch) >= BATCH_SIZE:
                try:
                    cursor.executemany('''
                    INSERT OR IGNORE INTO documents 
                    (url, title, content, domain, word_count, content_hash, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', [
                        (
                            doc.url, doc.title, doc.content, doc.domain, 
                            doc.word_count, doc.content_hash, doc.timestamp
                        ) for doc in batch
                    ])
                    conn.commit()
                    processed_count += len(batch)
                    batch = []
                except sqlite3.Error as e:
                    logging.error(f"Database error: {str(e)}")
        except Exception as e:
            logging.error(f"Queue error: {str(e)}")
    
    # Process final batch
    if batch:
        try:
            cursor.executemany('''
            INSERT OR IGNORE INTO documents 
            (url, title, content, domain, word_count, content_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [
                (
                    doc.url, doc.title, doc.content, doc.domain, 
                    doc.word_count, doc.content_hash, doc.timestamp
                ) for doc in batch
            ])
            conn.commit()
            processed_count += len(batch)
        except sqlite3.Error as e:
            logging.error(f"Final database error: {str(e)}")
    
    # Create indexes
    logging.info("Creating database indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON documents(domain)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON documents(content_hash)")
    conn.commit()
    conn.close()
    
    duration = time.time() - start_time
    logging.info(f"Writer finished: {processed_count} documents in {duration:.1f} seconds")

def main(input_dir: Path, output_dir: Path):
    """Main processing pipeline with queue-based architecture"""
    logging.info(f"MASSIVE DATA PREPROCESSOR [20GB+ MODE]")
    logging.info(f"Workers: {MAX_WORKERS} | Batch size: {BATCH_SIZE:,}")
    logging.info(f"Input: {input_dir} | Output: {output_dir}")
    
    # Prepare output
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "documents.db"
    
    # Find all JSON files
    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        logging.error("No JSON files found")
        return
    
    logging.info(f"Found {len(json_files)} files to process")
    
    # Create communication queues
    manager = multiprocessing.Manager()
    document_queue = manager.Queue(maxsize=MAX_QUEUE_SIZE)
    stats_queue = manager.Queue()
    
    # Start database writer process
    writer_process = multiprocessing.Process(
        target=database_writer,
        args=(db_path, document_queue, stats_queue)
    )
    writer_process.start()
    
    # Process files in parallel
    start_time = time.time()
    with multiprocessing.Pool(processes=MAX_WORKERS) as pool:
        tasks = [(f, document_queue) for f in json_files]
        pool.starmap(file_processor, tasks)
    
    # Signal writer to finish
    document_queue.put("DONE")
    writer_process.join()
    
    # Collect statistics
    total_stats = defaultdict(int)
    file_stats = {}
    skip_reasons = defaultdict(int)
    sample_skipped_doc = None
    
    while not stats_queue.empty():
        filename, stats = stats_queue.get()
        file_stats[filename] = stats
        
        # Aggregate statistics
        for k, v in stats.items():
            if k == "skip_reasons":
                for reason, count in v.items():
                    skip_reasons[reason] += count
            elif k not in {"sample_skipped", "skip_reasons"}:
                total_stats[k] += v
        
        # Save first sample skipped document
        if "sample_skipped" in stats and stats["sample_skipped"] and sample_skipped_doc is None:
            sample_skipped_doc = stats["sample_skipped"]
    
    # Print final report
    duration = time.time() - start_time
    logging.info("\nPROCESSING COMPLETE!")
    logging.info("="*60)
    logging.info(f"Total time: {duration:.1f} seconds")
    logging.info(f"Files processed: {len(json_files)}")
    logging.info(f"Total documents: {total_stats.get('total_docs', 0):,}")
    logging.info(f"Processed documents: {total_stats.get('processed', 0):,}")
    logging.info(f"Skipped documents: {total_stats.get('skipped', 0):,}")
    
    # Log skip reasons
    if skip_reasons:
        logging.info("\nSKIP REASONS:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
            logging.info(f"  {reason}: {count:,}")
    
    # Log sample skipped document
    if sample_skipped_doc:
        try:
            with open(output_dir / "sample_skipped_doc.json", "w") as f:
                json.dump(sample_skipped_doc, f, indent=2)
            logging.info(f"\nSample skipped document saved to: {output_dir / 'sample_skipped_doc.json'}")
        except:
            logging.warning("Failed to save sample skipped document")
    
    # Database info
    if db_path.exists():
        db_size = db_path.stat().st_size
        logging.info(f"\nDatabase size: {db_size/(1024**2):.2f} MB")
        logging.info(f"Location: {db_path}")

if __name__ == "__main__":
    input_path = Path("../../RawHTMLdata")
    output_path = Path("../backend/data/processed/")
    
    output_path.mkdir(parents=True, exist_ok=True)
    main(input_path, output_path)