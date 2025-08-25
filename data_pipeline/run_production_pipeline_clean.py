#!/usr/bin/env python3
"""
Production Data Pipeline - Pure Processing Only

Ultra-fast hybrid Rust/Python document processing pipeline with multiprocessing.
Processes raw HTML data and outputs clean JSON files to toIndex folder.
No indexing or OpenSearch dependencies - purely CPU-bound processing.
"""

import json
import logging
import time
import signal
import multiprocessing as mp
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

from hybrid_processor import HybridDocumentProcessor
from file_reader import FileReader
from scorer import ContentScorer
from config import PipelineConfig

# Configure logging with better configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Override any existing logging configuration
)

logger = logging.getLogger(__name__)

# Also configure the root logger to ensure all messages show
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

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

def process_document_worker(doc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Worker function for parallel document processing."""
    try:
        # Initialize processor in each worker process
        processor = HybridDocumentProcessor()
        scorer = ContentScorer()
        
        # Extract required fields
        html_content = doc_data.get('content', '')
        url = doc_data.get('url', '')
        domain = doc_data.get('domain', '')
        
        if not html_content or not url:
            logger.warning(f"Skipping document with missing content or URL")
            return None
        
        # Process with hybrid Rust/Python processor
        document, chunks = processor.process_document(html_content, url, domain)
        
        if not document:
            logger.warning(f"Failed to process document: {url}")
            return None
        
        # Score document
        try:
            score = scorer.calculate_content_quality_score(
                document.content if hasattr(document, 'content') else '',
                asdict(document),
                {}  # content_metrics
            )
            # Add score to document
            if hasattr(document, '__dict__'):
                document.__dict__['score'] = score
        except Exception as e:
            logger.warning(f"Failed to score document {url}: {e}")
        
        # Convert to serializable format
        result = {
            'documents': [asdict(document)],
            'chunks': [asdict(chunk) for chunk in chunks] if chunks else []
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing {doc_data.get('url', 'unknown')}: {e}")
        return None


class ProductionPipeline:
    """High-performance parallel production data pipeline - Processing Only."""
    
    def __init__(self, output_dir: str = None, score_documents: bool = True, 
                 max_workers: int = None, to_index_dir: str = None):
        """Initialize the production pipeline for pure processing."""
        self.file_reader = FileReader()
        
        # Use config for output directory if not specified
        output_dir_str = output_dir or PipelineConfig.OUTPUT_DIR
        self.output_dir = Path(output_dir_str)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create toIndex directory for processed files
        if to_index_dir:
            self.to_index_dir = Path(to_index_dir)
        else:
            # Default: create toIndex folder in the root project directory
            self.to_index_dir = Path("/home/gyashu/projects/A_Search_Engine/toIndex")
        self.to_index_dir.mkdir(exist_ok=True)
        
        # Determine optimal number of worker processes
        if max_workers is None:
            self.max_workers = min(4, max(1, mp.cpu_count() - 1))  # Use more workers since no indexing bottleneck
        else:
            self.max_workers = max_workers
            
        logger.info(f"🚀 Parallel processing enabled with {self.max_workers} worker processes")
        
        self.score_documents = score_documents
        
        # Initialize processor and scorer
        self.processor = HybridDocumentProcessor()
        self.scorer = ContentScorer() if score_documents else None
        
        self.stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'total_time': 0,
            'avg_time': 0
        }
        
        logger.info("🚀 Processing Pipeline initialized:")
        logger.info(f"   📁 Output directory: {self.output_dir}")
        logger.info(f"   📤 toIndex directory: {self.to_index_dir}")
        logger.info(f"   🔄 Max workers: {self.max_workers}")
        logger.info("   ⚡ Processing only - no indexing dependencies")
    
    def process_document(self, raw_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single document through the optimized pipeline."""
        start_time = time.perf_counter()
        
        try:
            # Extract required fields
            html_content = raw_doc.get('content', '')
            url = raw_doc.get('url', '')
            domain = raw_doc.get('domain', '')
            
            if not html_content or not url:
                logger.warning(f"Skipping document with missing content or URL")
                return None
            
            # Process with hybrid Rust/Python processor
            document, chunks = self.processor.process_document(html_content, url, domain)
            
            if not document:
                logger.warning(f"Failed to process document: {url}")
                return None
            
            # Score document
            if self.scorer:
                try:
                    score = self.scorer.calculate_content_quality_score(
                        document.content if hasattr(document, 'content') else '',
                        asdict(document),
                        {}  # content_metrics
                    )
                    # Add score to document
                    if hasattr(document, '__dict__'):
                        document.__dict__['score'] = score
                except Exception as e:
                    logger.warning(f"Failed to score document {url}: {e}")
            
            # Convert to serializable format
            result = {
                'documents': [asdict(document)],
                'chunks': [asdict(chunk) for chunk in chunks] if chunks else []
            }
            
            processing_time = time.perf_counter() - start_time
            self.stats['processed'] += 1
            self.stats['successful'] += 1
            self.stats['total_time'] += processing_time
            self.stats['avg_time'] = self.stats['total_time'] / self.stats['processed']
            
            logger.debug(f"Processed {url} in {processing_time:.3f}s")
            return result
            
        except Exception as e:
            processing_time = time.perf_counter() - start_time
            self.stats['processed'] += 1
            self.stats['failed'] += 1
            self.stats['total_time'] += processing_time
            
            logger.error(f"Error processing {raw_doc.get('url', 'unknown')}: {e}")
            return None
    
    def _process_documents_parallel(self, doc_batch: List[Dict[str, Any]]) -> List[Optional[Dict[str, Any]]]:
        """Process a batch of documents using parallel workers with graceful shutdown."""
        if not doc_batch:
            return []
        
        # Check for shutdown signal before starting
        if shutdown_requested:
            logger.warning("🛑 Shutdown requested, skipping batch processing...")
            return []
        
        logger.info(f"⚡ Starting parallel processing of {len(doc_batch)} documents with {self.max_workers} workers")
        
        # Use ProcessPoolExecutor for true parallelism (bypasses GIL)
        executor = None
        try:
            executor = ProcessPoolExecutor(max_workers=self.max_workers)
            # Submit all documents for parallel processing
            future_to_doc = {executor.submit(process_document_worker, doc): doc for doc in doc_batch}
            
            logger.info(f"🚀 {len(future_to_doc)} tasks submitted to worker pool")
            
            results = []
            completed_count = 0
            for future in as_completed(future_to_doc):
                # Check for shutdown signal during processing
                if shutdown_requested:
                    logger.warning("🛑 Shutdown requested, cancelling remaining tasks...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                    
                try:
                    result = future.result()
                    results.append(result)
                    completed_count += 1
                    
                    # Log progress every 20% or every 25 documents
                    if completed_count % max(1, len(doc_batch) // 5) == 0 or completed_count % 25 == 0:
                        logger.info(f"   Progress: {completed_count}/{len(doc_batch)} documents completed")
                        
                except Exception as e:
                    doc = future_to_doc[future]
                    logger.error(f"Parallel processing error for {doc.get('url', 'unknown')}: {e}")
                    results.append(None)
            
            successful = len([r for r in results if r is not None])
            logger.info(f"✅ Parallel batch completed: {successful}/{len(doc_batch)} successful")
            
            return results
            
        finally:
            if executor:
                executor.shutdown(wait=True)
    
    def _handle_parallel_results(self, results: List[Optional[Dict[str, Any]]], 
                                all_documents: List[Dict], all_chunks: List[Dict]):
        """Handle results from parallel processing."""
        successful_results = [r for r in results if r is not None]
        
        # Collect documents and chunks for file output
        for result in successful_results:
            all_documents.extend(result['documents'])
            all_chunks.extend(result['chunks'])
        
        # Update stats
        self.stats['processed'] += len(results)
        self.stats['successful'] += len(successful_results)
        self.stats['failed'] += len(results) - len(successful_results)

    def process_batch_from_files(self, input_files: List[str], 
                                batch_name: str = None, 
                                batch_size: int = 100,
                                max_items_per_file: int = 1000) -> Dict[str, Any]:
        """Process documents from input files using parallel processing and write to toIndex."""
        batch_start = time.perf_counter()
        batch_name = batch_name or f"batch_{int(time.time())}"
        
        logger.info(f"📊 Processing batch '{batch_name}' from {len(input_files)} files")
        logger.info(f"🚀 Using {self.max_workers} parallel workers")
        logger.info(f"⚙️  Batch size: {batch_size} documents per batch")
        logger.info(f"� Max items per output file: {max_items_per_file}")
        logger.info(f"�📤 Output: toIndex folder")
        
        all_documents = []
        all_chunks = []
        total_docs = 0
        output_file_count = 0
        
        def write_output_file():
            """Write current batch to a separate output file."""
            nonlocal output_file_count, all_documents, all_chunks
            
            if not all_documents and not all_chunks:
                return
                
            output_file_count += 1
            output_filename = f"{batch_name}_part_{output_file_count:03d}.jsonl"
            to_index_file = self.to_index_dir / output_filename
            
            try:
                with open(to_index_file, 'w', encoding='utf-8') as f:
                    # Write documents and chunks as individual JSON lines
                    for doc in all_documents:
                        doc_with_type = {'type': 'document', **doc}
                        f.write(json.dumps(doc_with_type, ensure_ascii=False, default=str) + '\n')
                    
                    for chunk in all_chunks:
                        chunk_with_type = {'type': 'chunk', **chunk}
                        f.write(json.dumps(chunk_with_type, ensure_ascii=False, default=str) + '\n')

                total_items = len(all_documents) + len(all_chunks)
                logger.info(f"📤 Written output file {output_file_count}: {output_filename} ({total_items} items)")
                
                # Clear the lists for next file
                all_documents.clear()
                all_chunks.clear()
                
            except IOError as e:
                logger.error(f"Error writing to {to_index_file}: {e}")
        
        for file_idx, input_file in enumerate(input_files):
            if shutdown_requested:
                logger.info("⚠️ Shutdown requested - stopping file processing")
                break
                
            file_start_time = time.perf_counter()
            logger.info(f"📂 Processing file {file_idx + 1}/{len(input_files)}: {Path(input_file).name}")
            
            try:
                # Collect documents in batches for parallel processing
                doc_batch = []
                file_doc_count = 0
                
                for raw_doc in self.file_reader.read_json_file(Path(input_file)):
                    if shutdown_requested:
                        logger.info("⚠️ Shutdown requested - stopping document processing")
                        break
                        
                    doc_batch.append(raw_doc)
                    file_doc_count += 1
                    total_docs += 1
                    
                    # Process in batches to manage memory and provide progress updates
                    if len(doc_batch) >= batch_size:
                        if shutdown_requested:
                            logger.info("⚠️ Shutdown requested - stopping batch processing")
                            break
                            
                        batch_start_time = time.perf_counter()
                        logger.info(f"⚡ Processing batch of {len(doc_batch)} documents (File {file_idx + 1}/{len(input_files)})")
                        
                        # Process batch in parallel
                        results = self._process_documents_parallel(doc_batch)
                        self._handle_parallel_results(results, all_documents, all_chunks)
                        
                        batch_time = time.perf_counter() - batch_start_time
                        logger.info(f"✅ Batch completed in {batch_time:.2f}s")
                        
                        # Check if we should write output file
                        total_items = len(all_documents) + len(all_chunks)
                        if total_items >= max_items_per_file:
                            write_output_file()
                        
                        doc_batch = []  # Clear for next batch
                
                # Process remaining documents
                if doc_batch and not shutdown_requested:
                    batch_start_time = time.perf_counter()
                    logger.info(f"⚡ Processing final batch of {len(doc_batch)} documents")
                    
                    results = self._process_documents_parallel(doc_batch)
                    self._handle_parallel_results(results, all_documents, all_chunks)
                    
                    batch_time = time.perf_counter() - batch_start_time
                    logger.info(f"✅ Final batch completed in {batch_time:.2f}s")
                
                file_time = time.perf_counter() - file_start_time
                logger.info(f"📄 File {file_idx + 1}/{len(input_files)} completed: {file_doc_count} docs in {file_time:.1f}s")
                
                # Check if we should write output file after processing each input file
                total_items = len(all_documents) + len(all_chunks)
                if total_items >= max_items_per_file:
                    write_output_file()
                
            except Exception as e:
                logger.error(f"❌ Error processing file {input_file}: {e}")
                continue
        
        # Write any remaining items to final output file
        if all_documents or all_chunks:
            write_output_file()
        
        batch_time = time.perf_counter() - batch_start
        total_documents = sum(1 for f in self.to_index_dir.glob(f"{batch_name}_part_*.jsonl"))
        
        logger.info(f"✅ Batch '{batch_name}' completed:")
        logger.info(f"   📄 Total processing time: {batch_time:.1f}s")
        logger.info(f"   📊 Total documents processed: {total_docs}")
        logger.info(f"   📁 Output files created: {output_file_count}")
        logger.info(f"   ⚡ Processing rate: {total_docs / batch_time:.1f} docs/sec")
        
        return {
            'batch_name': batch_name,
            'total_documents': total_docs,
            'output_files': output_file_count,
            'processing_time': batch_time
        }
        logger.info(f"   ⏱️  Time: {batch_time:.2f}s")
        logger.info(f"   🚀 Speed: {total_docs/batch_time:.1f} docs/sec")
        
        # The return value might need adjustment depending on what the caller expects.
        # For now, returning a summary metadata object.
        return {
            'metadata': {
                'batch_name': batch_name,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_documents': total_docs,
                'total_chunks': len(all_chunks),
                'processing_time': batch_time,
                'documents_per_second': total_docs / batch_time if batch_time > 0 else 0
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = {
            **self.stats,
            'success_rate': (self.stats['successful'] / max(self.stats['processed'], 1)) * 100,
            'docs_per_second': 1 / max(self.stats['avg_time'], 0.001)
        }
        return stats


def main():
    """Main entry point for production pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Production Data Pipeline - Processing Only')
    parser.add_argument('--input-files', nargs='*', 
                       help='Specific input JSON files to process (optional - auto-discovers from RawHTMLdata if not specified)')
    parser.add_argument('--input-dir', default='/home/gyashu/projects/A_Search_Engine/RawHTMLdata',
                       help='Directory containing input JSON files')
    parser.add_argument('--batch-name', help='Name for this batch')
    parser.add_argument('--batch-size', type=int, default=100, help='Documents per batch')
    parser.add_argument('--max-workers', type=int, help='Maximum worker processes')
    parser.add_argument('--to-index-dir', help='Directory to write processed files for indexing')
    
    args = parser.parse_args()
    
    # Auto-discover input files if not specified
    if args.input_files:
        input_files = args.input_files
        logger.info(f"📁 Using specified input files: {len(input_files)} files")
    else:
        # Auto-discover JSON files from RawHTMLdata directory
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            # Try alternative paths
            alt_paths = [
                Path("../RawHTMLdata"),
                Path("RawHTMLdata"),
                Path("/home/gyashu/projects/A_Search_Engine/RawHTMLdata")
            ]
            
            for alt_path in alt_paths:
                if alt_path.exists():
                    input_dir = alt_path
                    break
            else:
                logger.error("RawHTMLdata directory not found. Please ensure it exists.")
                print("Error: RawHTMLdata directory not found!")
                print("Expected locations:")
                print("  - /home/gyashu/projects/A_Search_Engine/RawHTMLdata")
                print("  - ../RawHTMLdata (relative to data_pipeline/)")
                print("  - RawHTMLdata (in current directory)")
                print("\nAlternatively, use --input-files to specify files manually.")
                return 1
        
        # Discover all JSON files
        json_files = list(input_dir.glob("*.json"))
        if not json_files:
            logger.error(f"No JSON files found in {input_dir}")
            print(f"Error: No JSON files found in {input_dir}")
            print("Use --input-files to specify files manually.")
            return 1
        
        input_files = [str(f) for f in sorted(json_files)]
        logger.info(f"📁 Auto-discovered {len(input_files)} JSON files in {input_dir}")
    
    # Initialize pipeline
    logger.info("🏗️ Initializing Processing Pipeline...")
    pipeline = ProductionPipeline(
        max_workers=args.max_workers,
        to_index_dir=args.to_index_dir
    )
    logger.info("✅ Pipeline initialization completed")
    
    # Process all input files
    total_start = time.perf_counter()
    
    logger.info(f"🚀 Starting batch processing with {len(input_files)} files...")
    logger.info(f"📋 Batch processing parameters:")
    logger.info(f"   📄 Files: {[Path(f).name for f in input_files][:3]}{'...' if len(input_files) > 3 else ''}")
    logger.info(f"   📤 toIndex directory: {pipeline.to_index_dir}")
    logger.info(f"   ⚙️  Batch size: {args.batch_size}")
    logger.info(f"   🔄 Max workers: {pipeline.max_workers}")
    
    # Process files
    try:
        batch_name = args.batch_name or f"production_batch_{int(time.time())}"
        result = pipeline.process_batch_from_files(
            input_files,
            batch_name=batch_name,
            batch_size=args.batch_size,
            max_items_per_file=1000  # Limit each output file to 1000 items
        )
        
        total_time = time.perf_counter() - total_start
        
        # Final statistics
        stats = pipeline.get_stats()
        logger.info(f"🏁 Pipeline completed:")
        logger.info(f"   Total processed: {stats['processed']}")
        logger.info(f"   Success rate: {stats['success_rate']:.1f}%")
        logger.info(f"   Average speed: {stats['docs_per_second']:.1f} docs/sec")
        logger.info(f"   Total time: {total_time:.2f}s")
        
        logger.info("🎉 Processing completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Pipeline interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"💥 Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
