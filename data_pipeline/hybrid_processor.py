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

# Import the ultra-fast Rust core processor
try:
    from rust_core_processor import process_html, is_english_fast, detect_language_fast
    RUST_AVAILABLE = True
    print("🦀 Rust core processor loaded successfully!")
except ImportError as e:
    print(f"❌ Rust core processor not available: {e}")
    print("Falling back to Python-only processing...")
    RUST_AVAILABLE = False

from scorer import ContentScorer

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
    
    # OPTIMIZED: Essential structured data only
    structured_meta: Optional[Dict[str, Any]] = None
    
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
    
    def __init__(self):
        """Initialize the Rust-powered document processor."""
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust core processor is required but not available. Run: cd rust_core_processor && maturin develop --release")
        
        # Use Rust for ultra-fast processing (log only on debug level)
        logger.debug("Using hybrid Rust/Python processing (ultra-fast)")
        
        # Initialize Python components for enhancement
        self.scorer = ContentScorer()
        # Note: language_detector is now handled by Rust for maximum performance
        
        # Performance tracking
        self.processing_stats = {
            'total_processed': 0,
            'total_time': 0.0,
            'rust_time': 0.0,
            'python_time': 0.0,
            'average_time_per_doc': 0.0
        }

    def process_document(self, html_content: str, url: str, domain: str = None) -> tuple[Document, List[DocumentChunk]]:
        """
        Process a document using the hybrid Rust/Python approach.
        
        Returns:
            tuple: (Document metadata, List of content chunks)
        """
        start_time = time.time()
        
        try:
            # Process with Rust core (only option in production)
            return self._process_with_rust(html_content, url, domain)
        finally:
            total_time = time.time() - start_time
            self._update_stats(total_time)

    def _process_with_rust(self, html_content: str, url: str, domain: str = None) -> tuple[Document, List[DocumentChunk]]:
        """Process document using the ultra-fast Rust core."""
        
        # Ultra-fast language filtering using Rust (bypasses Python entirely)
        # This is now handled at the Rust level for maximum performance
        if not is_english_fast(html_content[:2000], url):  # Check first 2K chars for speed
            logger.info(f"Filtering out non-English page: {url}")
            return None, []  # Skip non-English pages entirely
        
        rust_start = time.time()
        
        # Call the Rust core processor - now includes ultra-fast language detection
        rust_result = process_html(html_content, url)
        
        rust_time = time.time() - rust_start
        self.processing_stats['rust_time'] += rust_time
        
        if 'error' in rust_result:
            logger.error(f"Rust processing failed for {url}: {rust_result['error']}")
            # Return empty result if Rust processing fails
            return None, []
        
        python_start = time.time()
        
        # Create document from Rust results
        document = self._create_document_from_rust_result(rust_result, url, domain)
        
        # Create chunks from the already-processed text
        chunks = self._create_chunks_from_rust_result(rust_result, document.document_id)
        
        # Python-based scoring and enhancement (language detection now in Rust)
        document = self._enhance_document_with_python(document, rust_result)
        
        python_time = time.time() - python_start
        self.processing_stats['python_time'] += python_time
        
        logger.debug(f"Rust processing: {rust_time:.3f}s, Python enhancement: {python_time:.3f}s")
        
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
        
        categories = self.scorer.get_content_categories(
            f"{title} {description} {main_content}", 
            rust_result
        )[:3]  # Limit to top 3 categories
        
        # OPTIMIZED: Only store canonical URL if different from URL
        canonical_url = rust_result.get('canonical_url')
        if canonical_url == url:
            canonical_url = None
        
        return Document(
            document_id=document_id,
            url=url,
            title=rust_result.get('title', ''),
            domain=domain,
            description=rust_result.get('description', ''),
            content_type=self._determine_content_type(url, rust_result),
            categories=categories,
            keywords=rust_result.get('keywords', [])[:10],  # Limit to 10 keywords
            canonical_url=canonical_url,
            published_date=rust_result.get('published_date'),
            modified_date=rust_result.get('modified_date'),
            author_name=rust_result.get('author_name'),
            structured_meta=rust_result.get('structured_meta'),
            primary_image=rust_result.get('primary_image'),
            favicon=rust_result.get('favicon'),
            semantic_info={
                'word_count': rust_result.get('word_count', 0),
                'content_quality_score': rust_result.get('content_quality_score', 0.0),
                'is_technical_content': rust_result.get('is_technical_content', False),
                'domain_score': self.scorer.calculate_domain_score(url)
            }
        )

    def _create_chunks_from_rust_result(self, rust_result: Dict, document_id: str) -> List[DocumentChunk]:
        """Create DocumentChunk objects from Rust processing results (OPTIMIZED)."""
        chunks = []
        chunks_with_context = rust_result.get('text_chunks_with_context', [])
        
        for chunk_data in chunks_with_context:
            chunk_id = f"{document_id}_chunk_{chunk_data['chunk_index']}"
            word_count = len(chunk_data['text_chunk'].split())
            
            # OPTIMIZED: No redundant domain_score, quality_score, content_categories, keywords
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
        
        return chunks

    def _enhance_document_with_python(self, document: Document, rust_result: Dict) -> Document:
        """Enhance the document with Python-based analysis."""
        try:
            # Language detection is now handled in Rust for maximum performance
            # No need for additional Python language detection
            
            # Content scoring and categorization
            score_result = self.scorer.calculate_content_quality_score(
                content=rust_result.get('main_content', ''),
                metadata={
                    'title': document.title,
                    'description': document.description,
                    'url': document.url
                },
                content_metrics={
                    'word_count': rust_result.get('word_count', 0)
                }
            )
            
            # Simple category assignment based on content
            categories = []
            content_lower = rust_result.get('main_content', '').lower()
            if any(tech_word in content_lower for tech_word in ['code', 'programming', 'api', 'software']):
                categories.append('technology')
            if any(news_word in content_lower for news_word in ['news', 'breaking', 'update']):
                categories.append('news')
            
            # Update categories
            document.categories = categories
            
            # Update semantic info with quality score
            if document.semantic_info:
                document.semantic_info.update({
                    'content_quality_score': score_result if isinstance(score_result, (int, float)) else 0.0,
                    'domain_score': self.scorer.calculate_domain_score(document.url)
                })
            
        except Exception as e:
            logger.warning(f"Error in Python enhancement: {e}")
        
        return document

    def _determine_content_type(self, url: str, rust_result: Dict) -> str:
        """Determine content type from URL and metadata."""
        content_type = "article"  # default
        
        description = rust_result.get('description', '').lower()
        
        # Check for blog indicators
        if (any(indicator in url.lower() for indicator in ['blog', 'news', 'post']) or
            any(indicator in description for indicator in ['blog', 'post', 'article'])):
            content_type = "blog"
        
        return content_type

    def _create_document_from_python_data(self, processed_data: Dict, content: str, url: str, domain: str) -> Document:
        """Create Document from Python processing (fallback method)."""
        # This would be the original implementation
        # Simplified for brevity - use existing logic from processor.py
        pass

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

    def _update_stats(self, total_time: float):
        """Update processing statistics."""
        self.processing_stats['total_processed'] += 1
        self.processing_stats['total_time'] += total_time
        self.processing_stats['average_time_per_doc'] = (
            self.processing_stats['total_time'] / self.processing_stats['total_processed']
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        stats = self.processing_stats.copy()
        stats['using_rust'] = self.use_rust
        stats['rust_percentage'] = (
            (self.processing_stats['rust_time'] / self.processing_stats['total_time'] * 100)
            if self.processing_stats['total_time'] > 0 else 0
        )
        return stats

    def _extract_all_from_soup(self, soup):
        """Fallback method for Python-only processing."""
        # Original implementation would go here
        return {}

    def _process_raw_data(self, raw_data: Dict, url: str) -> Dict:
        """Fallback method for Python-only processing.""" 
        # Original implementation would go here
        return {}


# Maintain backward compatibility
DocumentProcessor = HybridDocumentProcessor

if __name__ == "__main__":
    # Test the hybrid processor
    processor = HybridDocumentProcessor()
    
    # Test with sample HTML
    test_html = """
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="This is a test page for the hybrid processor">
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>This is the main content of the test page. It should be processed quickly by the Rust core.</p>
        <h2>Secondary Heading</h2>
        <p>More content here with <a href="/link">some links</a> and other elements.</p>
    </body>
    </html>
    """
    
    start_time = time.time()
    document, chunks = processor.process_document(test_html, "https://example.com/test")
    processing_time = time.time() - start_time
    
    print(f"\n🚀 Processing completed in {processing_time:.4f} seconds")
    print(f"📄 Document: {document.title}")
    print(f"📝 Description: {document.description}")
    print(f"🔤 Word count: {document.semantic_info['word_count'] if document.semantic_info else 'N/A'}")
    print(f"📊 Chunks created: {len(chunks)}")
    print(f"⚡ Using Rust: {processor.use_rust}")
    
    stats = processor.get_performance_stats()
    print(f"\n📈 Performance Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
