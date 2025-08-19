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
from language_detector import LanguageDetector
from enhanced_metadata_extractor import EnhancedMetadataExtractor

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents the metadata for a single document."""
    document_id: str
    url: str
    title: str
    domain: str
    description: str  # Consolidated from text_snippet and original_meta_description
    content_type: str
    categories: List[str]
    keywords: List[str]  # Consolidated from keywords and original_keywords
    # Enhanced metadata fields
    canonical_url: Optional[str] = None
    published_date: Optional[str] = None
    modified_date: Optional[str] = None
    author_info: Optional[Dict[str, Any]] = None
    structured_data: Optional[Dict[str, Any]] = None
    images: Optional[List[Dict[str, Any]]] = None
    table_of_contents: Optional[List[Dict[str, Any]]] = None
    semantic_info: Optional[Dict[str, Any]] = None
    icons: Optional[Dict[str, str]] = None


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
        self.enhanced_extractor = EnhancedMetadataExtractor()
        
        # Processing statistics
        self.stats = {
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'low_quality_count': 0,
            'duplicate_count': 0,
            'total_chunks': 0,
            'high_quality_chunks': 0,
            'skipped_count': 0,
            'total_processing_time': 0,
            'language_filtered': 0,
            'content_too_short': 0,
            'extraction_failed': 0
        }
    
    def _score_description_quality(self, description: str, source_type: str) -> float:
        """Score description quality based on content and source."""
        score = 0.0
        
        # Length scoring (optimal 120-300 characters)
        length = len(description)
        if 120 <= length <= 300:
            score += 3.0
        elif 80 <= length <= 400:
            score += 2.0
        elif 50 <= length <= 500:
            score += 1.0
        
        # Source type scoring (prefer authored content)
        source_scores = {
            'og_description': 2.5,  # Open Graph is usually well-crafted
            'meta_description': 2.0,  # Standard meta description
            'json_ld_description': 1.5,  # Structured data description
            'microdata_description': 1.0   # Microdata description
        }
        score += source_scores.get(source_type, 0.0)
        
        # Content quality indicators
        if description.count('.') >= 1:  # Has sentence structure
            score += 0.5
        
        if any(word in description.lower() for word in ['and', 'or', 'with', 'about', 'the']):
            score += 0.3  # Natural language indicators
        
        # Penalties for low-quality descriptions
        if description.lower().startswith(('click', 'welcome', 'home', 'menu')):
            score -= 1.0  # Navigation text
        
        if len(description.split()) < 5:
            score -= 1.0  # Too short
        
        if description.count(description.split()[0]) > 3:  # Repetitive
            score -= 0.5
        
        return max(0.0, score)
    
    def _determine_content_type(self, url: str, enhanced_metadata: Dict) -> str:
        """Determine the content type based on URL and metadata."""
        content_type = "article"  # default
        
        if enhanced_metadata:
            # Check for blog indicators
            if (any(indicator in url.lower() for indicator in ['blog', 'news', 'post']) or
                any(indicator in enhanced_metadata.get('description', '').lower() for indicator in ['blog', 'post', 'article'])):
                content_type = "blog"
            
            # Check for technical content
            elif any(keyword in enhanced_metadata.get('description', '').lower() for keyword in 
                    ['tutorial', 'guide', 'documentation', 'api', 'code', 'programming']):
                content_type = "documentation"
        
        return content_type
        
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
                # Step 2.5: Language filtering using the proven original method
                if not LanguageDetector.is_english(html_content, url):
                    logger.debug(f"Skipping {url}: Not English content")
                    self.stats['language_filtered'] += 1
                    return None

            if len(html_content) < 50:  # Basic length check instead
                logger.debug(f"Skipping {url}: Content too short ({len(html_content)} chars)")
                self.stats['content_too_short'] += 1
                return None
            
            # Step 3: HTML parsing and content extraction (simplified)
            extracted_data = self.extractor.extract_content(html_content, url, raw_doc)
            
            # Step 3.5: Enhanced metadata extraction
            enhanced_metadata = self.enhanced_extractor.extract_enhanced_metadata(html_content, url)
            
            main_content = extracted_data.get('main_content', '')
            code_blocks = extracted_data.get('code_blocks', [])
            
            if not main_content or len(main_content) < self.min_content_length:
                logger.debug(f"Skipping {url}: Content too short ({len(main_content) if main_content else 0} chars)")
                self.stats['content_too_short'] += 1
                return None
            
            # Use enhanced metadata for all document fields
            json_ld_data = enhanced_metadata.get('structured_data', {}).get('json_ld', [])
            microdata = enhanced_metadata.get('structured_data', {}).get('microdata', [])
            open_graph = enhanced_metadata.get('structured_data', {}).get('open_graph', {})
            
            # FIXED: Proper title extraction hierarchy
            crawler_title = raw_doc.get('title', '')
            # Filter out "N/A" and other invalid titles from crawler
            if crawler_title in ['N/A', 'n/a', 'None', 'null', '']:
                crawler_title = ''
            
            title = (
                # 1. First priority: Open Graph title (og:title) - most reliable for sharing
                open_graph.get('title') or
                # 2. Second priority: JSON-LD headline
                (json_ld_data[0].get('headline') if json_ld_data else None) or
                # 3. Third priority: Microdata headline  
                (microdata[0].get('headline') if microdata else None) or
                # 4. Fourth priority: Meta title or page title from HTML <title> tag
                enhanced_metadata.get('page_metadata', {}).get('title', '') or
                # 5. Last resort: Raw doc title from crawler (if valid)
                crawler_title or
                # 6. Fallback only if everything else fails
                "Untitled Document"
            )
            
            # Clean and validate the title
            if title and title.strip():
                title = title.strip()
                # Only mark as untitled if it's actually generic/empty
                if self._is_generic_title(title) or len(title) < 3:
                    title = "Untitled Document"
            else:
                title = "Untitled Document"
                
            domain = raw_doc.get('domain', '') or self._extract_domain(url)
            
            headings = enhanced_metadata.get('toc_structure', [])
            if not headings:
                # Fallback to any headings we can find
                headings = self._extract_headings_from_content(main_content)
            
            # Step 7: Content cleaning
            cleaned_content = self.cleaner.clean_text(main_content)
            if not cleaned_content:
                logger.debug(f"Skipping {url}: Content cleaning resulted in empty text")
                self.stats['content_too_short'] += 1
                return None
            
            # Step 7.5: Enhanced description consolidation with better preservation
            page_meta = enhanced_metadata.get('page_metadata', {})
            structured_data = enhanced_metadata.get('structured_data', {})
            
            # Extract all available descriptions for better fallback
            descriptions = {
                'og_description': structured_data.get('rdfa', [{}])[0].get('og:description') if structured_data.get('rdfa') else None,
                'meta_description': page_meta.get('description'),
                'json_ld_description': None,
                'microdata_description': None
            }
            
            # Extract from JSON-LD
            json_ld_data = structured_data.get('json_ld', [])
            for item in json_ld_data:
                if 'description' in item:
                    descriptions['json_ld_description'] = item['description']
                    break
            
            # Extract from microdata
            microdata = structured_data.get('microdata', [])
            for item in microdata:
                if 'description' in item:
                    descriptions['microdata_description'] = item['description']
                    break
            
            # Enhanced description selection with quality scoring
            best_description = None
            best_score = 0
            
            for desc_type, desc_value in descriptions.items():
                if desc_value and isinstance(desc_value, str) and len(desc_value.strip()) > 10:
                    # Score descriptions based on quality indicators
                    score = self._score_description_quality(desc_value, desc_type)
                    if score > best_score:
                        best_score = score
                        best_description = desc_value.strip()
            
            # Final description decision
            if best_description:
                description = self.cleaner._clean_snippet_text(best_description)
                logger.debug(f"Using authored description from {url} (score: {best_score:.2f})")
            else:
                description = self.cleaner.create_description(cleaned_content)
                logger.debug(f"Generated description for {url} (no authored description found)")
            
            # Step 7.6: Enhanced keywords consolidation with debugging
            # Get original keywords from meta tags (author-provided)
            original_keywords = page_meta.get('keywords', [])
            
            # Log metadata extraction success for debugging
            if original_keywords:
                logger.debug(f"Preserved {len(original_keywords)} original keywords from {url}")
            
            if page_meta.get('description'):
                logger.debug(f"Preserved original meta description from {url}")
            
            # Generate additional keywords from content
            generated_keywords = self.cleaner.extract_keywords(cleaned_content)
            # Combine with priority to original keywords
            combined_keywords = self.cleaner.combine_keywords(original_keywords, generated_keywords, max_keywords=12)  # Increased limit
            
            # Step 8: Content analysis and scoring (using enhanced metadata)
            content_type = self._determine_content_type(url, enhanced_metadata)
            # Use enhanced metadata for categories instead of basic extracted_data
            enhanced_metadata_for_categories = {
                'title': title,
                'description': enhanced_metadata.get('description', ''),
                'author_info': enhanced_metadata.get('author_info', {}),
                'structured_data': enhanced_metadata.get('structured_data', {})
            }
            categories = self.scorer.get_content_categories(cleaned_content, enhanced_metadata_for_categories)
            
            domain_score = self.scorer.calculate_domain_score(url)
            quality_score = self.scorer.calculate_content_quality_score(
                cleaned_content, enhanced_metadata_for_categories, {}, html_content=html_content
            )
            
            # Step 9: Create document record with original metadata preservation
            document_id = hashlib.md5(url.encode()).hexdigest()
            
            document = Document(
                document_id=document_id,
                url=url,
                title=title,
                domain=domain,
                description=description,  # Consolidated field
                content_type=content_type,
                categories=categories,
                keywords=combined_keywords,  # Already limited to 10 in combine_keywords
                # Enhanced metadata
                canonical_url=enhanced_metadata.get('canonical_url'),
                published_date=enhanced_metadata.get('published_date'),
                modified_date=enhanced_metadata.get('modified_date'),
                author_info=enhanced_metadata.get('author_info'),
                structured_data=enhanced_metadata.get('structured_data'),
                images=enhanced_metadata.get('images'),
                table_of_contents=enhanced_metadata.get('table_of_contents'),
                semantic_info=enhanced_metadata.get('semantic_info'),
                icons=page_meta.get('icons')
            )
            
            # Step 10: Enhanced content chunking with improved content preservation
            text_chunks = self.cleaner.intelligent_chunking(
                cleaned_content, 
                preserve_context=True, 
                html_content=html_content,
                content_importance_threshold=0.25  # Lower threshold to preserve more content
            )
            if not text_chunks:
                logger.debug(f"Skipping {url}: No valid chunks created")
                self.stats['content_too_short'] += 1
                return None
            
            # Enhanced chunk quality filtering with better metrics
            quality_chunks = []
            for chunk in text_chunks:
                word_count = len(chunk.split())
                # More flexible quality requirements for different content types
                min_words = 50 if content_type in ['article', 'blog', 'documentation'] else 30
                
                if word_count >= min_words:
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
                
                # Combine chunk-specific keywords with document keywords for richer search
                chunk_combined_keywords = list(dict.fromkeys(
                    chunk_keywords + combined_keywords[:5]  # Top 5 document keywords
                ))[:10]  # Limit to 10 total
                
                chunk_word_count = len(chunk.split())
                
                # Calculate individual chunk quality score
                chunk_quality_score = self.scorer.calculate_content_quality_score(
                    chunk, enhanced_metadata_for_categories, {'word_count': chunk_word_count}
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
                    keywords=chunk_combined_keywords
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
            # COMMENTED OUT: JSON writing to save disk space and improve performance
            main_file = output_path / f"processed_data_{timestamp}{batch_suffix}.json"
            with open(main_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Write human-readable summary
            summary_file = output_path / f"quality_report_{timestamp}{batch_suffix}.txt"
            self._write_quality_report(summary_file, output_data)
            
            # Write sample documents for manual inspection (increased to 500 samples)
            sample_file = output_path / f"sample_documents_{timestamp}{batch_suffix}.txt"
            self._write_sample_documents(sample_file, documents, chunks, sample_size=500)
            
            file_paths = {
                # "main_file": str(main_file),  # COMMENTED OUT
                "summary_file": str(summary_file), 
                "sample_file": str(sample_file)
            }
            
            logger.info(f"📁 Processed documents written to:")
            # logger.info(f"   📄 Main data: {main_file}")  # COMMENTED OUT
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
                              chunks: List[Dict[str, Any]], sample_size: int = 500):
        """Write sample documents for manual inspection."""
        with open(file_path, 'w', encoding='utf-8') as f:
            total_docs = len(documents)
            actual_sample_size = min(sample_size, total_docs)
            
            f.write("🔍 SAMPLE PROCESSED DOCUMENTS\n")
            f.write("=" * 40 + "\n")
            f.write(f"Showing {actual_sample_size} out of {total_docs} total documents\n")
            f.write("=" * 40 + "\n\n")
            
            # Sample documents
            for i, doc in enumerate(documents[:actual_sample_size]):
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

    def _extract_headings_from_content(self, content: str) -> List[dict]:
        """Extract headings from content as fallback when enhanced metadata doesn't provide them."""
        import re
        headings = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for markdown-style headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                text = line.lstrip('#').strip()
                if text:
                    headings.append({'level': level, 'text': text})
            # Look for common heading patterns
            elif re.match(r'^[A-Z][^.]*:$', line) and len(line) < 100:
                headings.append({'level': 2, 'text': line.rstrip(':')})
                
        return headings[:10]  # Limit to 10 headings
