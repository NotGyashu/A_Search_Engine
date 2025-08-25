#!/usr/bin/env python3
"""
Quality Analysis Pipeline for Search Engine Data
===============================================

This pipeline processes documents and generates comprehensive quality reports
instead of indexing to OpenSearch. It creates:
1. Quality metrics report
2. Human-readable sample data
3. JSON file showing what would be indexed
4. Data quality issues and recommendations

Usage:
    python run_quality_analysis.py <input_file.json>
"""

import os
import sys
import json
import time
import signal
import logging
import multiprocessing as mp
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor, as_completed

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    print(f"\n🛑 Shutdown signal received ({signum}). Finishing current batch...")
    shutdown_requested = True

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_reader import FileReader
from hybrid_processor import HybridDocumentProcessor
from scorer import ContentScorer
from config import PipelineConfig

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduced verbosity
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_document_for_quality(doc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Worker function for parallel quality analysis processing."""
    try:
        from hybrid_processor import HybridDocumentProcessor
        from scorer import ContentScorer
        
        
        # Initialize processor in each worker process
        processor = HybridDocumentProcessor()
        scorer = ContentScorer()
        analyzer = QualityAnalyzer()
        
        # Extract required fields
        html_content = doc_data.get('content', '')
        url = doc_data.get('url', '')
        domain = doc_data.get('domain', '')
        
        if not html_content or not url:
            return None
        
        # Process with hybrid processor
        processed_doc, chunks = processor.process_document(html_content, url, domain)
        
        # Skip if processing failed
        if not processed_doc or not chunks:
            return None
        
        # Convert Document object to dictionary for easier handling
        try:
            doc_dict = asdict(processed_doc)
        except:
            if hasattr(processed_doc, '__dict__'):
                doc_dict = dict(processed_doc.__dict__)
            else:
                if isinstance(processed_doc, dict):
                    doc_dict = processed_doc
                else:
                    return None
        
        # Add FAST quality scoring
        main_content = doc_dict.get('main_content', '')
        doc_dict['content_quality_score'] = analyzer._fast_quality_score(
            main_content,
            doc_dict.get('title', ''),
            len(doc_dict.get('keywords', []))
        )
        
        
        # Convert chunks to dictionaries
        chunk_dicts = []
        for chunk in chunks:
            try:
                chunk_dict = asdict(chunk)
            except:
                if hasattr(chunk, '__dict__'):
                    chunk_dict = dict(chunk.__dict__)
                else:
                    chunk_dict = chunk
            chunk_dicts.append(chunk_dict)
        
        return {
            'document': doc_dict,
            'chunks': chunk_dicts
        }
        
    except Exception as e:
        logger.error(f"Error processing document {doc_data.get('url', 'unknown')}: {e}")
        return None


class QualityAnalyzer:
    """Analyzes data quality and generates comprehensive reports"""
    
    def __init__(self):
        self.quality_issues = []
        self.metrics = defaultdict(list)
        self.sample_documents = []
        self.indexing_preview = []
    
    def _fast_quality_score(self, content: str, title: str, keyword_count: int) -> float:
        """Fast quality scoring without CPU-intensive operations"""
        score = 0.0
        
        # Content length (40% of score)
        content_len = len(content.strip())
        if content_len > 1000:
            score += 40.0
        elif content_len > 500:
            score += 30.0
        elif content_len > 100:
            score += 20.0
        elif content_len > 20:
            score += 10.0
        
        # Title quality (30% of score)
        title_len = len(title.strip())
        if 20 <= title_len <= 100:
            score += 30.0
        elif 10 <= title_len <= 150:
            score += 20.0
        elif title_len > 0:
            score += 10.0
        
        # Keywords (20% of score)
        if keyword_count >= 5:
            score += 20.0
        elif keyword_count >= 3:
            score += 15.0
        elif keyword_count >= 1:
            score += 10.0
        
        # Basic content quality (10% of score)
        if content_len > 0:
            words = content.split()
            if len(words) > 50:
                score += 10.0
            elif len(words) > 10:
                score += 5.0
        
        return min(score, 100.0)
        
    def analyze_document_quality(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality metrics for a single document"""
        quality_report = {
            'document_id': document.get('document_id', 'unknown'),
            'url': document.get('url', ''),
            'quality_score': 0.0,
            'issues': [],
            'strengths': [],
            'metadata_completeness': 0.0,
            'content_richness': 0.0,
            'technical_quality': 0.0
        }
        
        # Check basic metadata completeness
        metadata_fields = ['title', 'description', 'author_info', 'published_date', 'canonical_url']
        completed_fields = sum(1 for field in metadata_fields if document.get(field))
        quality_report['metadata_completeness'] = (completed_fields / len(metadata_fields)) * 100
        
        # Check content richness
        content_metrics = {
            'has_content': bool(document.get('main_content', '').strip()),
            'has_keywords': bool(document.get('keywords', [])),
            'has_images': bool(document.get('images', [])),
            'has_headings': bool(document.get('headings', [])),
            'has_structured_data': bool(document.get('structured_data', {}) and 
                                      document.get('structured_data', {}).get('json_ld', []))
        }
        quality_report['content_richness'] = (sum(content_metrics.values()) / len(content_metrics)) * 100
        
        # Technical quality assessment
        tech_quality = 0
        if document.get('word_count', 0) > 100:
            tech_quality += 20
        if document.get('content_quality_score', 0) > 5:
            tech_quality += 20
        if document.get('semantic_info', {}).get('technical_score', 0) > 2:
            tech_quality += 20
        if len(document.get('keywords', [])) >= 5:
            tech_quality += 20
        if document.get('semantic_info', {}).get('headings_count', 0) > 0:
            tech_quality += 20
        quality_report['technical_quality'] = tech_quality
        
        # Overall quality score
        quality_report['quality_score'] = (
            quality_report['metadata_completeness'] * 0.3 +
            quality_report['content_richness'] * 0.4 +
            quality_report['technical_quality'] * 0.3
        )
        
        # Identify specific issues
        if not document.get('title', '').strip():
            quality_report['issues'].append('Missing or empty title')
        if not document.get('description', '').strip():
            quality_report['issues'].append('Missing description')
        if not document.get('keywords', []):
            quality_report['issues'].append('No keywords extracted')
        
        author_info = document.get('author_info') or {}
        if not author_info.get('name'):
            quality_report['issues'].append('Missing author information')
            
        if not document.get('published_date'):
            quality_report['issues'].append('Missing publication date')
        if len(document.get('main_content', '')) < 100:
            quality_report['issues'].append('Very short content (< 100 characters)')
        if not document.get('images', []):
            quality_report['issues'].append('No images found')
        
        # Identify strengths
        if len(document.get('main_content', '')) > 1000:
            quality_report['strengths'].append('Rich content (> 1000 characters)')
        if len(document.get('keywords', [])) >= 10:
            quality_report['strengths'].append('Comprehensive keywords')
        
        structured_data = document.get('structured_data') or {}
        if structured_data.get('json_ld'):
            quality_report['strengths'].append('Has structured data (JSON-LD)')
            
        if len(document.get('headings', [])) >= 3:
            quality_report['strengths'].append('Well-structured with headings')
        
        semantic_info = document.get('semantic_info') or {}
        if semantic_info.get('is_technical_content'):
            quality_report['strengths'].append('Technical content detected')
        
        return quality_report
    
    def analyze_chunk_quality(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality metrics for a single chunk"""
        quality_report = {
            'chunk_id': chunk.get('chunk_id', 'unknown'),
            'quality_score': 0.0,
            'issues': [],
            'strengths': []
        }
        
        content = chunk.get('content', '')
        keywords = chunk.get('keywords', [])
        
        # Basic quality checks
        if len(content) < 50:
            quality_report['issues'].append('Very short chunk (< 50 characters)')
        elif len(content) > 500:
            quality_report['strengths'].append('Substantial content')
        
        if not keywords:
            quality_report['issues'].append('No keywords in chunk')
        elif len(keywords) >= 5:
            quality_report['strengths'].append('Rich keyword coverage')
        
        # Calculate quality score
        content_score = min(len(content) / 200, 1.0) * 50  # Max 50 points for content
        keyword_score = min(len(keywords) / 5, 1.0) * 50   # Max 50 points for keywords
        
        quality_report['quality_score'] = content_score + keyword_score
        
        return quality_report
    
    def generate_human_readable_sample(self, documents: List[Dict], chunks: List[Dict]) -> str:
        """Generate human-readable sample of processed data"""
        report = []
        report.append("=" * 80)
        report.append("SEARCH ENGINE DATA PIPELINE - SAMPLE OUTPUT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Documents: {len(documents)}")
        report.append(f"Total Chunks: {len(chunks)}")
        report.append("")
        
        # Show sample documents
        report.append("📄 SAMPLE DOCUMENTS")
        report.append("=" * 50)
        
        for i, doc in enumerate(documents[:3]):  # Show first 3 documents
            report.append(f"\n📖 Document {i+1}")
            report.append("-" * 30)
            report.append(f"Title: {doc.get('title', 'N/A')}")
            report.append(f"URL: {doc.get('url', 'N/A')}")
            report.append(f"Domain: {doc.get('domain', 'N/A')}")
            report.append(f"Content Type: {doc.get('content_type', 'N/A')}")
            report.append(f"Language: {doc.get('language', 'N/A')}")
            report.append(f"Description: {doc.get('description', 'N/A')[:200]}...")
            
            # Author info
            author = doc.get('author_info', {})
            if isinstance(author, dict):
                author_name = author.get('name', author.get('meta_author', 'N/A'))
            else:
                author_name = str(author) if author else 'N/A'
            report.append(f"Author: {author_name}")
            
            # Keywords
            keywords = doc.get('keywords', [])
            report.append(f"Keywords: {', '.join(keywords[:10])}...")
            
            # Categories
            categories = doc.get('categories', [])
            if categories:
                report.append(f"Categories: {', '.join(categories)}")
            
            # Quality metrics
            semantic_info = doc.get('semantic_info', {})
            report.append(f"Word Count: {semantic_info.get('word_count', 0)}")
            report.append(f"Quality Score: {semantic_info.get('content_quality_score', 0):.2f}")
            report.append(f"Technical Content: {'Yes' if semantic_info.get('is_technical_content') else 'No'}")
            
            # Dates
            if doc.get('published_date'):
                report.append(f"Published: {doc.get('published_date')}")
            if doc.get('modified_date'):
                report.append(f"Modified: {doc.get('modified_date')}")
            
            # Images count
            images_count = len(doc.get('images', []))
            report.append(f"Images: {images_count}")
            
            # Headings count
            headings_count = len(doc.get('headings', []))
            report.append(f"Headings: {headings_count}")
            
            # Content preview
            content = doc.get('main_content', '')
            if content:
                preview = content[:300].replace('\n', ' ').strip()
                report.append(f"Content Preview: {preview}...")
        
        # Show sample chunks
        report.append(f"\n\n📝 SAMPLE CHUNKS")
        report.append("=" * 50)
        
        for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
            report.append(f"\n🧩 Chunk {i+1}")
            report.append("-" * 20)
            report.append(f"Document ID: {chunk.get('document_id', 'N/A')}")
            report.append(f"Chunk ID: {chunk.get('chunk_id', 'N/A')}")
            report.append(f"Position: {chunk.get('position', 'N/A')}")
            
            # Keywords
            keywords = chunk.get('keywords', [])
            report.append(f"Keywords: {', '.join(keywords)}")
            
            # Content
            content = chunk.get('content', '')
            preview = content[:200].replace('\n', ' ').strip()
            report.append(f"Content: {preview}...")
            
            # Quality score
            quality_score = chunk.get('quality_score', 0)
            report.append(f"Quality Score: {quality_score:.2f}")
        
        return '\n'.join(report)
    
    def generate_indexing_preview(self, documents: List[Dict], chunks: List[Dict]) -> Dict[str, Any]:
        """Generate JSON showing exactly what would be indexed to OpenSearch"""
        indexing_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_documents": len(documents),
                "total_chunks": len(chunks),
                "index_structure": {
                    "documents_index": "search_documents",
                    "chunks_index": "search_chunks"
                }
            },
            "documents_index_preview": [],
            "chunks_index_preview": []
        }
        
        # Prepare documents for indexing
        for doc in documents[:5]:  # Show first 5 documents
            index_doc = {
                "_index": "search_documents",
                "_id": doc.get('document_id'),
                "_source": {
                    "document_id": doc.get('document_id'),
                    "url": doc.get('url'),
                    "title": doc.get('title', ''),
                    "description": doc.get('description', ''),
                    "domain": doc.get('domain', ''),
                    "content_type": doc.get('content_type', 'article'),
                    "language": doc.get('language', 'en'),
                    "categories": doc.get('categories', []),
                    "keywords": doc.get('keywords', []),
                    "canonical_url": doc.get('canonical_url', ''),
                    "published_date": doc.get('published_date'),
                    "modified_date": doc.get('modified_date'),
                    "author_info": doc.get('author_info', {}),
                    "main_content": doc.get('main_content', ''),
                    "semantic_info": doc.get('semantic_info', {}),
                    "structured_data": doc.get('structured_data', {}),
                    "images_count": len(doc.get('images', [])),
                    "headings_count": len(doc.get('headings', [])),
                    "links_count": len(doc.get('links', [])),
                    "indexed_at": datetime.now().isoformat()
                }
            }
            indexing_data["documents_index_preview"].append(index_doc)
        
        # Prepare chunks for indexing
        for chunk in chunks[:10]:  # Show first 10 chunks
            index_chunk = {
                "_index": "search_chunks",
                "_id": chunk.get('chunk_id'),
                "_source": {
                    "chunk_id": chunk.get('chunk_id'),
                    "document_id": chunk.get('document_id'),
                    "content": chunk.get('content', ''),
                    "keywords": chunk.get('keywords', []),
                    "position": chunk.get('position', 0),
                    "chunk_type": chunk.get('chunk_type', 'content'),
                    "quality_score": chunk.get('quality_score', 0),
                    "url": chunk.get('url', ''),
                    "title": chunk.get('title', ''),
                    "domain": chunk.get('domain', ''),
                    "indexed_at": datetime.now().isoformat()
                }
            }
            indexing_data["chunks_index_preview"].append(index_chunk)
        
        return indexing_data
    
    def generate_quality_report(self, documents: List[Dict], chunks: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive quality metrics report"""
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_documents": len(documents),
                "total_chunks": len(chunks),
                "analysis_version": "1.0"
            },
            "overall_quality": {
                "average_document_quality": 0.0,
                "average_chunk_quality": 0.0,
                "total_issues": 0,
                "quality_distribution": {
                    "excellent": 0,  # 90-100%
                    "good": 0,       # 70-89%
                    "fair": 0,       # 50-69%
                    "poor": 0        # <50%
                }
            },
            "content_analysis": {
                "languages_detected": Counter(),
                "domains_processed": Counter(),
                "content_types": Counter(),
                "average_word_count": 0,
                "technical_content_ratio": 0.0
            },
            "metadata_analysis": {
                "fields_completion_rate": {},
                "structured_data_coverage": 0.0,
                "author_coverage": 0.0,
                "date_coverage": 0.0
            },
            "keyword_analysis": {
                "average_keywords_per_document": 0.0,
                "top_keywords": Counter(),
                "keyword_quality_distribution": {}
            },
            "quality_issues": {
                "common_issues": Counter(),
                "critical_issues": [],
                "recommendations": []
            },
            "sample_quality_scores": []
        }
        
        # Analyze each document
        document_qualities = []
        for doc in documents:
            doc_quality = self.analyze_document_quality(doc)
            document_qualities.append(doc_quality)
            
            # Update counters
            quality_score = doc_quality['quality_score']
            if quality_score >= 90:
                report["overall_quality"]["quality_distribution"]["excellent"] += 1
            elif quality_score >= 70:
                report["overall_quality"]["quality_distribution"]["good"] += 1
            elif quality_score >= 50:
                report["overall_quality"]["quality_distribution"]["fair"] += 1
            else:
                report["overall_quality"]["quality_distribution"]["poor"] += 1
            
            # Track issues
            for issue in doc_quality['issues']:
                report["quality_issues"]["common_issues"][issue] += 1
            
            # Content analysis
            if doc.get('language'):
                report["content_analysis"]["languages_detected"][doc['language']] += 1
            if doc.get('domain'):
                report["content_analysis"]["domains_processed"][doc['domain']] += 1
            if doc.get('content_type'):
                report["content_analysis"]["content_types"][doc['content_type']] += 1
        
        # Calculate averages
        if document_qualities:
            report["overall_quality"]["average_document_quality"] = sum(q['quality_score'] for q in document_qualities) / len(document_qualities)
            report["overall_quality"]["total_issues"] = sum(len(q['issues']) for q in document_qualities)
        
        # Analyze chunks
        chunk_qualities = []
        for chunk in chunks:
            chunk_quality = self.analyze_chunk_quality(chunk)
            chunk_qualities.append(chunk_quality)
        
        if chunk_qualities:
            report["overall_quality"]["average_chunk_quality"] = sum(q['quality_score'] for q in chunk_qualities) / len(chunk_qualities)
        
        # Content analysis details
        word_counts = []
        for doc in documents:
            semantic_info = doc.get('semantic_info') or {}
            word_count = semantic_info.get('word_count', 0)
            word_counts.append(word_count)
            
        if word_counts:
            report["content_analysis"]["average_word_count"] = sum(word_counts) / len(word_counts)
        
        technical_docs = 0
        for doc in documents:
            semantic_info = doc.get('semantic_info') or {}
            if semantic_info.get('is_technical_content'):
                technical_docs += 1
                
        report["content_analysis"]["technical_content_ratio"] = technical_docs / len(documents) if documents else 0
        
        # Metadata analysis
        metadata_fields = ['title', 'description', 'author_info', 'published_date', 'canonical_url']
        for field in metadata_fields:
            completed = sum(1 for doc in documents if doc.get(field))
            report["metadata_analysis"]["fields_completion_rate"][field] = (completed / len(documents)) * 100 if documents else 0
        
        # Structured data coverage
        with_structured_data = 0
        for doc in documents:
            structured_data = doc.get('structured_data') or {}
            if structured_data.get('json_ld'):
                with_structured_data += 1
                
        report["metadata_analysis"]["structured_data_coverage"] = (with_structured_data / len(documents)) * 100 if documents else 0
        
        # Author coverage
        with_authors = 0
        for doc in documents:
            author_info = doc.get('author_info') or {}
            if author_info.get('name') or author_info.get('meta_author'):
                with_authors += 1
                
        report["metadata_analysis"]["author_coverage"] = (with_authors / len(documents)) * 100 if documents else 0
        
        # Date coverage
        with_dates = sum(1 for doc in documents if doc.get('published_date') or doc.get('modified_date'))
        report["metadata_analysis"]["date_coverage"] = (with_dates / len(documents)) * 100 if documents else 0
        
        # Keyword analysis
        all_keywords = []
        for doc in documents:
            keywords = doc.get('keywords', [])
            all_keywords.extend(keywords)
            
        if documents:
            report["keyword_analysis"]["average_keywords_per_document"] = len(all_keywords) / len(documents)
        
        report["keyword_analysis"]["top_keywords"] = dict(Counter(all_keywords).most_common(20))
        
        # Sample quality scores
        report["sample_quality_scores"] = [
            {
                "document_id": q['document_id'],
                "url": q['url'],
                "quality_score": round(q['quality_score'], 2),
                "metadata_completeness": round(q['metadata_completeness'], 1),
                "content_richness": round(q['content_richness'], 1),
                "technical_quality": round(q['technical_quality'], 1),
                "issues_count": len(q['issues']),
                "strengths_count": len(q['strengths'])
            }
            for q in document_qualities[:10]
        ]
        
        # Generate recommendations
        recommendations = []
        
        avg_quality = report["overall_quality"]["average_document_quality"]
        if avg_quality < 70:
            recommendations.append("Overall data quality is below good standards. Focus on improving metadata completeness.")
        
        missing_authors = 100 - report["metadata_analysis"]["author_coverage"]
        if missing_authors > 50:
            recommendations.append(f"Author information is missing for {missing_authors:.1f}% of documents. Enhance author extraction.")
        
        missing_dates = 100 - report["metadata_analysis"]["date_coverage"]
        if missing_dates > 60:
            recommendations.append(f"Publication dates are missing for {missing_dates:.1f}% of documents. Improve date extraction.")
        
        if report["keyword_analysis"]["average_keywords_per_document"] < 5:
            recommendations.append("Low keyword density. Consider enhancing keyword extraction algorithms.")
        
        poor_quality_docs = report["overall_quality"]["quality_distribution"]["poor"]
        if poor_quality_docs > len(documents) * 0.2:
            recommendations.append(f"{poor_quality_docs} documents have poor quality scores. Review content extraction methods.")
        
        report["quality_issues"]["recommendations"] = recommendations
        
        return report


def main():
    """Main pipeline execution"""
    # Auto-discover JSON files from RawHTMLdata directory
    raw_data_dir = Path("../RawHTMLdata")
    if not raw_data_dir.exists():
        # Try alternative path in case we're in different directory
        raw_data_dir = Path("RawHTMLdata")
        if not raw_data_dir.exists():
            logger.error("RawHTMLdata directory not found. Please ensure it exists.")
            print("Error: RawHTMLdata directory not found!")
            print("Expected locations:")
            print("  - ../RawHTMLdata (relative to data_pipeline/)")
            print("  - RawHTMLdata (in current directory)")
            sys.exit(1)
    
    # Discover all JSON files
    json_files = list(raw_data_dir.glob("*.json"))
    if not json_files:
        logger.error(f"No JSON files found in {raw_data_dir}")
        print(f"Error: No JSON files found in {raw_data_dir}")
        sys.exit(1)
    
    logger.warning(f"📁 Auto-discovered {len(json_files)} JSON files in {raw_data_dir}")
    # Only log first few files for debugging
    for json_file in sorted(json_files)[:3]:
        logger.debug(f"    📄 {json_file.name}")
    
    input_files = json_files
    
    # Generate batch name
    timestamp = int(time.time())
    batch_name = f"quality_analysis_{timestamp}"
    
    # Create output directories
    # Use configuration for output directory
    output_dir = Path(PipelineConfig.QUALITY_REPORTS_DIR)
    output_dir.mkdir(exist_ok=True)
    
    # Initialize quality analysis
    logger.warning("� Quality Analysis Pipeline initialized")
    
    start_time = time.time()
    
    # Initialize components
    analyzer = QualityAnalyzer()
    file_reader = FileReader()
    
    # Determine optimal number of worker processes (max 2 for Azure VM B2 standard)
    max_workers = min(2, max(1, mp.cpu_count() - 1))
    logger.warning(f"🚀 Parallel processing: {max_workers} workers (Azure VM optimized)")
    
    logger.warning(f"📊 Input: {len(input_files)} files")
    
    # Collect all documents for parallel processing
    all_raw_documents = []
    for input_file in sorted(input_files):
        logger.debug(f"📖 Reading documents from {input_file.name}")
        
        for document_data in file_reader.read_json_file(input_file):
            all_raw_documents.append(document_data)
    
    logger.warning(f"📊 Processing {len(all_raw_documents)} documents")
    
    # Process documents in parallel
    all_documents = []
    all_chunks = []
    
    batch_size = 100  # Process in batches to manage memory
    total_batches = (len(all_raw_documents) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(all_raw_documents))
        batch_docs = all_raw_documents[start_idx:end_idx]
        
        # Check for shutdown signal before processing
        if shutdown_requested:
            logger.warning("🛑 Shutdown requested, stopping processing...")
            break
        
        batch_start_time = time.time()
        logger.warning(f"⚡ Processing batch {batch_idx + 1}/{total_batches} ({len(batch_docs)} documents)")
        
        # Process batch in parallel with graceful shutdown
        executor = None
        try:
            executor = ProcessPoolExecutor(max_workers=max_workers)
            future_to_doc = {
                executor.submit(process_document_for_quality, doc): doc 
                for doc in batch_docs
            }
            
            batch_results = []
            for future in as_completed(future_to_doc):
                # Check for shutdown signal during processing
                if shutdown_requested:
                    logger.warning("🛑 Shutdown requested, cancelling remaining tasks...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                    
                try:
                    result = future.result()
                    if result:
                        batch_results.append(result)
                except Exception as e:
                    logger.error(f"Parallel processing error: {e}")
                    
        finally:
            if executor:
                executor.shutdown(wait=True)
        
        # Collect results from this batch
        for result in batch_results:
            all_documents.append(result['document'])
            all_chunks.extend(result['chunks'])
            
        batch_time = time.time() - batch_start_time
        batch_speed = len(batch_results) / batch_time if batch_time > 0 else 0
        processed_so_far = len(all_documents)
        total_progress = (processed_so_far / len(all_raw_documents)) * 100
        
        logger.warning(f"✅ Batch {batch_idx + 1} complete: {len(batch_results)}/{len(batch_docs)} docs | "
                      f"{batch_speed:.1f} docs/sec | Progress: {total_progress:.1f}%")
        
        # Break out of loop if shutdown requested
        if shutdown_requested:
            break
    
    processing_time = time.time() - start_time
    
    logger.warning(f"✅ Processing completed:")
    logger.warning(f"    📄 Documents: {len(all_documents)}")
    logger.warning(f"    📝 Chunks: {len(all_chunks)}")
    logger.warning(f"    ⏱️  Time: {processing_time:.2f}s")
    logger.warning(f"    🚀 Speed: {len(all_documents)/processing_time:.1f} docs/sec")
    
    # Generate reports
    logger.info("📊 Generating quality analysis reports...")
    
    # 1. Quality metrics report
    quality_report = analyzer.generate_quality_report(all_documents, all_chunks)
    quality_file = output_dir / f"{batch_name}_quality_report.json"
    with open(quality_file, 'w', encoding='utf-8') as f:
        json.dump(quality_report, f, indent=2, ensure_ascii=False)
    logger.info(f"📈 Quality report saved: {quality_file}")
    
    # 2. Human-readable sample
    sample_text = analyzer.generate_human_readable_sample(all_documents, all_chunks)
    sample_file = output_dir / f"{batch_name}_sample_data.txt"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_text)
    logger.info(f"📄 Sample data saved: {sample_file}")
    
    # 3. Indexing preview
    indexing_preview = analyzer.generate_indexing_preview(all_documents, all_chunks)
    indexing_file = output_dir / f"{batch_name}_indexing_preview.json"
    with open(indexing_file, 'w', encoding='utf-8') as f:
        json.dump(indexing_preview, f, indent=2, ensure_ascii=False)
    logger.info(f"🗄️  Indexing preview saved: {indexing_file}")
    
    # 4. Complete processed data
    complete_data = {
        "batch_metadata": {
            "name": batch_name,
            "processed_at": time.time(),
            "input_files": [str(f) for f in input_files],
            "total_documents": len(all_documents),
            "total_chunks": len(all_chunks),
            "processing_time": processing_time,
            "documents_per_second": len(all_documents) / processing_time if processing_time > 0 else 0,
            "indexing_enabled": False,
            "analysis_mode": True
        },
        "documents": all_documents,
        "chunks": all_chunks
    }
    
    complete_file = output_dir / f"{batch_name}_complete_data.json"
    with open(complete_file, 'w', encoding='utf-8') as f:
        json.dump(complete_data, f, indent=2, ensure_ascii=False)
    logger.info(f"📁 Complete data saved: {complete_file}")
    
    # Print summary
    logger.info("🏁 Quality Analysis completed:")
    logger.info(f"    📊 Quality Score: {quality_report['overall_quality']['average_document_quality']:.1f}/100")
    logger.info(f"    ✅ Excellent Quality: {quality_report['overall_quality']['quality_distribution']['excellent']} docs")
    logger.info(f"    👍 Good Quality: {quality_report['overall_quality']['quality_distribution']['good']} docs") 
    logger.info(f"    ⚠️  Issues Found: {quality_report['overall_quality']['total_issues']}")
    logger.info(f"    📝 Reports Generated: 4 files")
    logger.info(f"    📁 Output Directory: {output_dir}")
    
    print(f"\n🎯 QUALITY ANALYSIS SUMMARY")
    print(f"{'='*50}")
    print(f"Documents Processed: {len(all_documents)}")
    print(f"Chunks Generated: {len(all_chunks)}")
    print(f"Average Quality Score: {quality_report['overall_quality']['average_document_quality']:.1f}/100")
    print(f"Processing Speed: {len(all_documents)/processing_time:.1f} docs/sec")
    print(f"\nReports Generated:")
    print(f"  📈 Quality Report: {quality_file}")
    print(f"  📄 Sample Data: {sample_file}")
    print(f"  🗄️  Indexing Preview: {indexing_file}")
    print(f"  📁 Complete Data: {complete_file}")


if __name__ == "__main__":
    main()
