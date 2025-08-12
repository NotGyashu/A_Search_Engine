"""
Document Processor - Main Processing Orchestrator

Coordinates all processing modules to transform raw HTML documents
into optimized, searchable content for OpenSearch indexing.
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

from extractor import ContentExtractor
from cleaner import ContentCleaner
from scorer import ContentScorer

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents the metadata for a single document."""
    document_id: str
    url: str
    title: str
    domain: str
    text_snippet: str
    timestamp: str
    content_type: str
    categories: List[str]
    keywords: List[str]


@dataclass
class DocumentChunk:
    """Represents an indexable chunk of a document."""
    chunk_id: str
    document_id: str
    text_chunk: str
    headings: str
    domain_score: float
    quality_score: float
    word_count: int
    content_categories: List[str]
    keywords: List[str]


class DocumentProcessor:
    """Advanced document processing with modular components."""
    
    def __init__(self, min_content_length: int = 600, max_chunk_size: int = 2000):
        self.min_content_length = min_content_length  # Increased from 400 to 600 for even better quality
        self.max_chunk_size = max_chunk_size
        
        # Initialize processing modules with improved settings
        self.extractor = ContentExtractor()
        self.cleaner = ContentCleaner(max_chunk_size=max_chunk_size, min_chunk_size=400)  # Increased from 300 to 400
        self.scorer = ContentScorer()
        
        # Processing statistics
        self.stats = {
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'total_processing_time': 0,
            'language_filtered': 0,
            'content_too_short': 0,
            'extraction_failed': 0
        }
    
    def process_document(self, raw_doc: Dict[str, Any]) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        Process a single raw document through the complete pipeline.
        
        Returns:
            Dict with 'documents' and 'chunks' lists, or None if processing failed
        """
        start_time = time.time()
        self.stats['processed_count'] += 1
        
        try:
            # Step 1: Basic validation
            url = str(raw_doc.get("url", "")).strip()
            if not url:
                logger.debug("Skipping document: No URL")
                self.stats['skipped_count'] += 1
                return None
            
            html_content = raw_doc.get("content", "")
            if not html_content:
                logger.debug(f"Skipping {url}: No HTML content")
                self.stats['skipped_count'] += 1
                return None
            
            if not LanguageDetector.is_english(html_content, url):
                logger.debug(f"Skipping {url}: Non-English content")
                self.stats['language_filtered'] += 1
                return None

            if len(html_content) < 50:  # Basic length check instead
                logger.debug(f"Skipping {url}: Content too short ({len(html_content)} chars)")
                self.stats['content_too_short'] += 1
                return None
            
            # Step 3: HTML parsing and content extraction (optimized)
            extracted_data = self.extractor.extract_content(html_content, url, raw_doc)
            
            main_content = extracted_data.get('main_content', '')
            if not main_content or len(main_content) < self.min_content_length:
                logger.debug(f"Skipping {url}: Content too short ({len(main_content) if main_content else 0} chars)")
                self.stats['content_too_short'] += 1
                return None
            
            # Prioritize crawler metadata
            title = raw_doc.get('title', '') 
            if not title or self._is_generic_title(title):
                title = extracted_data.get('title', '') or "Untitled Document"
                
            domain = raw_doc.get('domain', '') or extracted_data.get('domain', '') or self._extract_domain(url)
            text_snippet = raw_doc.get('text_snippet', '') or extracted_data.get('description', '') or self.cleaner.create_text_snippet(cleaned_content)
            timestamp = raw_doc.get('timestamp', '') or extracted_data.get('date', '')
            
            headings = extracted_data.get('headings', [])
            content_metrics = extracted_data.get('metrics', {})
            
            # Step 7: Content cleaning
            cleaned_content = self.cleaner.clean_text(main_content)
            if not cleaned_content:
                logger.debug(f"Skipping {url}: Content cleaning resulted in empty text")
                self.stats['content_too_short'] += 1
                return None
            
            # Step 8: Content analysis and scoring (using crawler + extracted data)
            content_type = extracted_data.get('content_type', 'article')
            categories = self.scorer.get_content_categories(cleaned_content, extracted_data)
            keywords = self.cleaner.extract_keywords(cleaned_content)
            
            domain_score = self.scorer.calculate_domain_score(url)
            quality_score = self.scorer.calculate_content_quality_score(
                cleaned_content, extracted_data, content_metrics
            )
            
            # Step 9: Create document record (using crawler data directly - no redundancy)
            document_id = hashlib.md5(url.encode()).hexdigest()
            
            document = Document(
                document_id=document_id,
                url=url,
                title=title,
                domain=domain,
                text_snippet=text_snippet,
                timestamp=timestamp,
                content_type=content_type,
                categories=categories,
                keywords=keywords[:10]  # Limit keywords for efficiency
            )
            
            # Step 10: Content chunking with quality filtering
            text_chunks = self.cleaner.intelligent_chunking(cleaned_content)
            if not text_chunks:
                logger.debug(f"Skipping {url}: No valid chunks created")
                self.stats['content_too_short'] += 1
                return None
            
            # Filter chunks by minimum word count for better quality
            quality_chunks = []
            for chunk in text_chunks:
                word_count = len(chunk.split())
                if word_count >= 75:  # Increased from 50 to 75 words per chunk for better quality
                    quality_chunks.append(chunk)
            
            if not quality_chunks:
                logger.debug(f"Skipping {url}: No chunks meet minimum quality requirements")
                self.stats['content_too_short'] += 1
                return None
            
            # Step 11: Create chunk records with quality filtering
            document_chunks = []
            formatted_headings = self.cleaner.format_headings_for_index(headings)
            
            for i, chunk in enumerate(quality_chunks):
                chunk_id = hashlib.md5(f"{document_id}_chunk_{i}".encode()).hexdigest()
                chunk_keywords = self.cleaner.extract_keywords(chunk, max_keywords=8)  # Increased from 5
                chunk_word_count = len(chunk.split())
                
                # Calculate individual chunk quality score
                chunk_quality_score = self.scorer.calculate_content_quality_score(
                    chunk, extracted_data, {'word_count': chunk_word_count}
                )
                
                doc_chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text_chunk=chunk,
                    headings=formatted_headings,
                    domain_score=domain_score,
                    quality_score=chunk_quality_score,  # Use individual chunk quality score
                    word_count=chunk_word_count,
                    content_categories=categories,
                    keywords=chunk_keywords
                )
                document_chunks.append(doc_chunk)
            
            # Step 12: Log processing metrics
            processing_time = time.time() - start_time
            self.stats['successful_count'] += 1
            self.stats['total_processing_time'] += processing_time
            
            raw_size_kb = len(html_content.encode("utf-8")) / 1024
            clean_size_kb = len(cleaned_content.encode("utf-8")) / 1024
            
            logger.info(
                f"[PROCESSED] {url} | "
                f"Raw: {raw_size_kb:.1f}KB → Clean: {clean_size_kb:.1f}KB → "
                f"Chunks: {len(text_chunks)} | "
                f"Quality: {quality_score:.2f} | "
                f"Time: {processing_time:.2f}s"
            )
            
            return {
                "documents": [asdict(document)],
                "chunks": [asdict(chunk) for chunk in document_chunks]
            }
            
        except Exception as e:
            self.stats['failed_count'] += 1
            processing_time = time.time() - start_time
            self.stats['total_processing_time'] += processing_time
            logger.error(f"Error processing document {url}: {e}")
            return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL as fallback."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown.domain"
    
    def _is_generic_title(self, title: str) -> bool:
        """Check if title is too generic or templated."""
        generic_patterns = [
            'untitled', 'home', 'index', 'main', 'welcome',
            'page not found', '404', 'error', 'loading'
        ]
        
        title_lower = title.lower()
        return any(pattern in title_lower for pattern in generic_patterns)
    
    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL."""
        try:
            # Remove protocol and www
            domain = url.split("://")[-1].split("/")[0]
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"
    
    def process_batch(self, documents: List[Dict[str, Any]], 
                     write_output: bool = True, 
                     output_dir: str = "processed_output",
                     batch_name: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """Process a batch of documents efficiently."""
        logger.info(f"Processing batch of {len(documents)} documents")
        
        all_documents = []
        all_chunks = []
        
        for raw_doc in documents:
            result = self.process_document(raw_doc)
            if result:
                all_documents.extend(result["documents"])
                all_chunks.extend(result["chunks"])
        
        logger.info(
            f"Batch processing complete: "
            f"{len(all_documents)} documents, {len(all_chunks)} chunks created"
        )
        
        # Write processed data for quality inspection
        if write_output and (all_documents or all_chunks):
            self.write_processed_documents(
                all_documents, 
                all_chunks, 
                output_dir=output_dir,
                batch_name=batch_name
            )
        
        return {
            "documents": all_documents,
            "chunks": all_chunks
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get detailed processing statistics."""
        total_processed = self.stats['processed_count']
        avg_processing_time = (
            self.stats['total_processing_time'] / max(total_processed, 1)
        )
        
        return {
            **self.stats,
            'success_rate': (self.stats['successful_count'] / max(total_processed, 1)) * 100,
            'avg_processing_time_seconds': avg_processing_time,
            'documents_per_second': 1 / max(avg_processing_time, 0.001)
        }
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'total_processing_time': 0,
            'language_filtered': 0,
            'content_too_short': 0,
            'extraction_failed': 0
        }

    def write_processed_documents(self, 
                                documents: List[Dict[str, Any]], 
                                chunks: List[Dict[str, Any]], 
                                output_dir: str = "processed_output",
                                batch_name: str = None) -> Dict[str, str]:
        """
        Write processed documents and chunks to files for quality inspection.
        
        Args:
            documents: List of processed document records
            chunks: List of processed chunk records  
            output_dir: Directory to write files to
            batch_name: Optional batch identifier for filename
            
        Returns:
            Dict with paths to written files
        """
        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_suffix = f"_{batch_name}" if batch_name else ""
            
            # Prepare output data with quality metrics
            output_data = {
                "processing_metadata": {
                    "timestamp": timestamp,
                    "total_documents": len(documents),
                    "total_chunks": len(chunks),
                    "batch_name": batch_name,
                    "processing_stats": self.get_processing_stats()
                },
                "documents": documents,
                "chunks": chunks,
                "quality_summary": self._generate_quality_summary(documents, chunks)
            }
            
            # Write comprehensive output file
            main_file = output_path / f"processed_data_{timestamp}{batch_suffix}.json"
            with open(main_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Write human-readable summary
            summary_file = output_path / f"quality_report_{timestamp}{batch_suffix}.txt"
            self._write_quality_report(summary_file, output_data)
            
            # Write sample documents for manual inspection
            sample_file = output_path / f"sample_documents_{timestamp}{batch_suffix}.txt"
            self._write_sample_documents(sample_file, documents, chunks)
            
            file_paths = {
                "main_file": str(main_file),
                "summary_file": str(summary_file), 
                "sample_file": str(sample_file)
            }
            
            logger.info(f"📁 Processed documents written to:")
            logger.info(f"   📄 Main data: {main_file}")
            logger.info(f"   📊 Quality report: {summary_file}")
            logger.info(f"   🔍 Sample documents: {sample_file}")
            
            return file_paths
            
        except Exception as e:
            logger.error(f"Failed to write processed documents: {e}")
            return {}
    
    def _generate_quality_summary(self, documents: List[Dict[str, Any]], 
                                chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate quality metrics summary for the processed data."""
        if not documents:
            return {"error": "No documents to analyze"}
        
        # Document quality metrics
        doc_metrics = {
            "avg_title_length": sum(len(d.get('title', '')) for d in documents) / len(documents),
            "domains": list(set(d.get('domain', '') for d in documents)),
            "content_types": list(set(d.get('content_type', '') for d in documents)),
            "avg_keywords_per_doc": sum(len(d.get('keywords', [])) for d in documents) / len(documents),
            "documents_with_categories": sum(1 for d in documents if d.get('categories')),
        }
        
        # Chunk quality metrics
        if chunks:
            chunk_metrics = {
                "avg_chunk_length": sum(len(c.get('text_chunk', '')) for c in chunks) / len(chunks),
                "avg_word_count": sum(c.get('word_count', 0) for c in chunks) / len(chunks),
                "avg_quality_score": sum(c.get('quality_score', 0) for c in chunks) / len(chunks),
                "avg_domain_score": sum(c.get('domain_score', 0) for c in chunks) / len(chunks),
                "chunks_per_document": len(chunks) / len(documents)
            }
        else:
            chunk_metrics = {"error": "No chunks to analyze"}
        
        return {
            "document_metrics": doc_metrics,
            "chunk_metrics": chunk_metrics
        }
    
    def _write_quality_report(self, file_path: Path, data: Dict[str, Any]):
        """Write a human-readable quality report."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("🔍 DOCUMENT PROCESSING QUALITY REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Processing metadata
            meta = data["processing_metadata"]
            f.write(f"📊 Processing Summary:\n")
            f.write(f"   Timestamp: {meta['timestamp']}\n")
            f.write(f"   Documents: {meta['total_documents']}\n")
            f.write(f"   Chunks: {meta['total_chunks']}\n")
            f.write(f"   Batch: {meta.get('batch_name', 'N/A')}\n\n")
            
            # Processing stats
            stats = meta["processing_stats"]
            f.write(f"⚡ Performance Metrics:\n")
            f.write(f"   Success Rate: {stats.get('success_rate', 0):.1f}%\n")
            f.write(f"   Avg Processing Time: {stats.get('avg_processing_time_seconds', 0):.2f}s\n")
            f.write(f"   Documents/Second: {stats.get('documents_per_second', 0):.1f}\n\n")
            
            # Quality summary
            quality = data["quality_summary"]
            if "document_metrics" in quality:
                doc_m = quality["document_metrics"]
                f.write(f"📄 Document Quality:\n")
                f.write(f"   Avg Title Length: {doc_m.get('avg_title_length', 0):.1f} chars\n")
                f.write(f"   Unique Domains: {len(doc_m.get('domains', []))}\n")
                f.write(f"   Content Types: {', '.join(doc_m.get('content_types', []))}\n")
                f.write(f"   Avg Keywords/Doc: {doc_m.get('avg_keywords_per_doc', 0):.1f}\n")
                f.write(f"   Docs with Categories: {doc_m.get('documents_with_categories', 0)}\n\n")
            
            if "chunk_metrics" in quality:
                chunk_m = quality["chunk_metrics"]
                if "error" not in chunk_m:
                    f.write(f"📝 Chunk Quality:\n")
                    f.write(f"   Avg Chunk Length: {chunk_m.get('avg_chunk_length', 0):.0f} chars\n")
                    f.write(f"   Avg Word Count: {chunk_m.get('avg_word_count', 0):.0f} words\n")
                    f.write(f"   Avg Quality Score: {chunk_m.get('avg_quality_score', 0):.2f}\n")
                    f.write(f"   Avg Domain Score: {chunk_m.get('avg_domain_score', 0):.2f}\n")
                    f.write(f"   Chunks per Document: {chunk_m.get('chunks_per_document', 0):.1f}\n\n")
            
            # Domain breakdown
            if "document_metrics" in quality and quality["document_metrics"].get("domains"):
                f.write(f"🌐 Domain Breakdown:\n")
                domains = quality["document_metrics"]["domains"]
                for domain in sorted(domains):
                    if domain:
                        f.write(f"   - {domain}\n")
                f.write("\n")
    
    def _write_sample_documents(self, file_path: Path, documents: List[Dict[str, Any]], 
                              chunks: List[Dict[str, Any]], sample_size: int = 3):
        """Write sample documents for manual inspection."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("🔍 SAMPLE PROCESSED DOCUMENTS\n")
            f.write("=" * 40 + "\n\n")
            
            # Sample documents
            for i, doc in enumerate(documents[:sample_size]):
                f.write(f"📄 DOCUMENT {i+1}\n")
                f.write("-" * 20 + "\n")
                f.write(f"URL: {doc.get('url', 'N/A')}\n")
                f.write(f"Title: {doc.get('title', 'N/A')}\n")
                f.write(f"Domain: {doc.get('domain', 'N/A')}\n")
                f.write(f"Content Type: {doc.get('content_type', 'N/A')}\n")
                f.write(f"Categories: {', '.join(doc.get('categories', []))}\n")
                f.write(f"Keywords: {', '.join(doc.get('keywords', []))}\n")
                f.write(f"Snippet: {doc.get('text_snippet', 'N/A')[:200]}...\n")
                f.write("\n")
                
                # Related chunks
                doc_chunks = [c for c in chunks if c.get('document_id') == doc.get('document_id')]
                f.write(f"📝 CHUNKS ({len(doc_chunks)} total):\n")
                for j, chunk in enumerate(doc_chunks[:2]):  # Show first 2 chunks
                    f.write(f"  Chunk {j+1}:\n")
                    f.write(f"    Quality: {chunk.get('quality_score', 0):.2f}\n")
                    f.write(f"    Domain Score: {chunk.get('domain_score', 0):.2f}\n")
                    f.write(f"    Words: {chunk.get('word_count', 0)}\n")
                    f.write(f"    Text: {chunk.get('text_chunk', 'N/A')[:150]}...\n")
                    
                    # Parse and display headings properly
                    headings_str = chunk.get('headings', '[]')
                    try:
                        import json
                        headings_list = json.loads(headings_str) if isinstance(headings_str, str) else headings_str
                        if headings_list and isinstance(headings_list, list):
                            f.write(f"    Headings:\n")
                            for heading in headings_list[:3]:  # Show first 3 headings
                                level = heading.get('level', 1)
                                text = heading.get('text', '')
                                f.write(f"      H{level}: {text}\n")
                        else:
                            f.write(f"    Headings: None\n")
                    except:
                        f.write(f"    Headings: {headings_str[:200]}...\n")
                    f.write("\n")
                
                f.write("\n" + "="*40 + "\n\n")
