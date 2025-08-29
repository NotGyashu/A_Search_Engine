"""
HYBRID Rust/Python Document Processor - Performance Optimized

This is the high-performance version that uses Rust for HTML parsing,
content extraction, and text cleaning while maintaining Python for 
orchestration and other I/O operations.
"""

import hashlib
import time
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import re
from collections import defaultdict
import heapq



# Import the ultra-fast Rust core processor
try:
    from rust_core_processor import process_html, is_english_fast, detect_language_fast
    RUST_AVAILABLE = True
    print("🦀 Rust core processor loaded successfully!")
except ImportError as e:
    print(f"❌ Rust core processor not available: {e}")
    print("Falling back to Python-only processing...")
    RUST_AVAILABLE = False


# Set logging to WARNING to reduce verbosity
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Document:
    """Represents the metadata for a single document (OPTIMIZED for size reduction)."""
   
    document_id: str
    url: str
    title: str
    domain: str
    description: str
    content_type: str
    categories: List[str]
    keywords: List[str]
    
    # OPTIMIZED: Only store if different from URL
    canonical_url: Optional[str] = None
    published_date: Optional[str] = None
    modified_date: Optional[str] = None
    
    # OPTIMIZED: Simplified author info (just name)
    author_name: Optional[str] = None


    # OPTIMIZED: Only primary image and favicon
    primary_image: Optional[Dict[str, str]] = None
    favicon: Optional[str] = None
    
    # OPTIMIZED: Essential semantic info only
    semantic_info: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class DocumentChunk:
    """Represents an indexable chunk of a document (OPTIMIZED - no redundant fields)."""

    chunk_id: str
    document_id: str
    text_chunk: str
    relevant_headings: List[str]  # OPTIMIZED: Only relevant headings, not full JSON
    chunk_index: int
    word_count: int
    
    # REMOVED: domain_score, quality_score, content_categories, keywords
    # These are now only stored in the parent Document to avoid duplication


class HybridDocumentProcessor:
    """High-performance hybrid Rust/Python document processor."""
    _TOKENIZER = re.compile(r"\b\w+\b").findall  # precompiled regex

    # precomputed stopwords set (same as yours, just defined once)
    _STOPWORDS = {
        "a","an","the","and","or","but","if","then","else","when","while","because",
        "as","until","since","than","though","although","unless","once","where","whereas",
        "at","from","by","with","for","to","into","onto","upon","about","of","in","on",
        "off","over","under","out","up","down","near","away","across","through","after",
        "before","between","among","during","without","within","against","along","per",
        "i","me","my","myself","we","our","ours","ourselves","you","your","yours",
        "yourself","yourselves","he","him","his","himself","she","her","hers","herself",
        "it","its","itself","they","them","their","theirs","themselves","one","ones",
        "anyone","everyone","someone","nobody","everybody","somebody",
        "is","am","are","was","were","be","been","being","have","has","had","having",
        "do","does","did","doing","can","cannot","could","should","would","will","shall",
        "must","may","might","ought",
        "i'm","you're","he's","she's","it's","we're","they're","i've","you've","we've",
        "they've","i'd","you'd","he'd","she'd","we'd","they'd","i'll","you'll","he'll",
        "she'll","we'll","they'll","isn't","aren't","wasn't","weren't","hasn't","haven't",
        "hadn't","doesn't","don't","didn't","won't","wouldn't","shan't","shouldn't","can't",
        "couldn't","mustn't","let's","that's","who's","what's","here's","there's","when's",
        "where's","why's","how's",
        "yes","no","not","nor","so","too","very","also","just","only","same","own","each",
        "few","more","most","some","any","all","other","another","many","much","both",
        "such","yet","ever","never","always","sometimes","often","rarely","hardly",
        "home","page","pages","article","post","blog","entry","story","news","update",
        "archive","category","categories","tag","tags","topic","topics","section","sections",
        "content","feature","features","search","query","results","index","feed","rss",
        "comment","comments","reply","replies","share","shares","like","likes","view","views",
        "read","reading","click","clicked","submit","posted","updated",
        "menu","navigation","nav","header","footer","sidebar","widget","login","logout",
        "signup","register","profile","account","settings","contact","about","help","support",
        "privacy","terms","policy","cookie","copyright",
        "html","htm","php","asp","aspx","jsp","cfm","cgi","www","com","net","org","info",
        "index","main","default",
        "day","days","week","weeks","month","months","year","years","today","yesterday","tomorrow",
        "monday","tuesday","wednesday","thursday","friday","saturday","sunday"
    }

    def __init__(self):
        """Initialize the Rust-powered document processor."""
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust core processor is required but not available. Run: cd rust_core_processor && maturin develop --release")
        
        # Use Rust for ultra-fast processing (log only on debug level)
        logger.debug("Using hybrid Rust/Python processing (ultra-fast)")
        
    def process_document(self, html_content: str, url: str, domain: str = None) -> tuple[Document, List[DocumentChunk]]:
        return self._process_with_rust(html_content, url, domain)
        


    def _process_with_rust(self, html_content: str, url: str, domain: str = None) -> tuple[Document, List[DocumentChunk]]:
        """Process document using the ultra-fast Rust core."""
        
        if not is_english_fast(html_content[:2000], url):  # Check first 2K chars for speed
            logger.info(f"Filtering out non-English page: {url}")
            return None, []  # Skip non-English pages entirely
        
        # Call the Rust core processor - now includes ultra-fast language detection
        rust_result = process_html(html_content, url)
        
        
        if 'error' in rust_result:
            logger.error(f"Rust processing failed for {url}: {rust_result['error']}")
            # Return empty result if Rust processing fails
            return None, []
        

        # Create document from Rust results
        document = self._create_document_from_rust_result(rust_result, url, domain)
        
        # Create chunks from the already-processed text
        chunks = self._create_chunks_from_rust_result(rust_result, document.document_id)
        
        return document, chunks

    def _create_document_from_rust_result(self, rust_result: Dict, url: str, domain: str = None) -> Document:
        """Create a Document object from Rust processing results (OPTIMIZED)."""
        if domain is None:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
        
        # Generate document ID
        content_hash = hashlib.sha256(rust_result['main_content'].encode()).hexdigest()[:12]
        document_id = f"doc_{content_hash}_{int(time.time())}"
        
        # OPTIMIZED: Get content categories using centralized logic from scorer
        main_content = rust_result.get('main_content', '')
        title = rust_result.get('title', '')
        description = rust_result.get('description', '')
        
        # OPTIMIZED: Only store canonical URL if different from URL
        canonical_url = rust_result.get('canonical_url')
        if canonical_url == url:
            canonical_url = None

        keywords = rust_result.get('keywords', [])
        if not keywords:  # catches empty list or empty string
            keywords = self.extract_keywords(rust_result.get('main_content', ''), 10)
        else:
            keywords = keywords[:10]  # limit only if keywords came from Rust


        return Document(
            document_id=document_id,
            url=url,
            title=rust_result.get('title', ''),
            domain=domain,
            description=rust_result.get('description', ''),
            content_type=rust_result.get('content_type', ''),
            categories=rust_result.get('content_categories', ''),
            keywords=keywords,
            canonical_url=canonical_url,
            published_date=rust_result.get('published_date'),
            modified_date=rust_result.get('modified_date'),
            author_name=rust_result.get('author_name'),
            primary_image=rust_result.get('primary_image'),
            favicon=rust_result.get('favicon'),
            semantic_info={
                'word_count': rust_result.get('word_count', 0),
                'content_quality_score': rust_result.get('content_quality_score', 0.0),
                'is_technical_content': rust_result.get('is_technical_content', False),
                'domain_score': rust_result.get('domain_score', 0.0)
            }
        )

    def _create_chunks_from_rust_result(self, rust_result: Dict, document_id: str) -> List[DocumentChunk]:
        """Create DocumentChunk objects from Rust processing results (OPTIMIZED)."""
        chunks = []
        chunks_with_context = rust_result.get('text_chunks_with_context', [])
        
        for chunk_data in chunks_with_context:
            chunk_id = f"{document_id}_chunk_{chunk_data['chunk_index']}"
            word_count = len(chunk_data['text_chunk'].split())
            
            # These are stored only in the parent Document
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                text_chunk=chunk_data['text_chunk'],
                relevant_headings=chunk_data['relevant_headings'],  # OPTIMIZED: Only relevant headings
                chunk_index=chunk_data['chunk_index'],
                word_count=word_count
            )
            chunks.append(chunk)
        
        return chunks
        

    def _create_chunks_from_content(self, text_chunks: List[str], document_id: str) -> List[DocumentChunk]:
        """Create chunks from text content (fallback method)."""
        chunks = []
        for i, chunk_content in enumerate(text_chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=i,
                content=chunk_content,
                chunk_type="main_content"
            )
            chunks.append(chunk)
        return chunks

    @staticmethod
    def extract_keywords(text: str, top_n: int = 10):
        """
        Super-fast RAKE-inspired keyword extractor.
        Optimized to minimize CPU/memory overhead.
        """
        words = HybridDocumentProcessor._TOKENIZER(text.lower())
        stopwords = HybridDocumentProcessor._STOPWORDS
        freq, degree = defaultdict(int), defaultdict(int)

        current_phrase = []
        for word in words:
            if word in stopwords:
                if current_phrase:
                    d = len(current_phrase) - 1
                    for w in current_phrase:
                        freq[w] += 1
                        degree[w] += d
                    current_phrase = []
            else:
                current_phrase.append(word)

        if current_phrase:  # flush last phrase
            d = len(current_phrase) - 1
            for w in current_phrase:
                freq[w] += 1
                degree[w] += d

        # compute score
        scores = {w: (degree[w] + freq[w]) / freq[w] for w in freq if len(w) > 2}

        # top_n keywords using heapq (faster than full sort for small n)
        return [w for w, _ in heapq.nlargest(top_n, scores.items(), key=lambda x: x[1])]