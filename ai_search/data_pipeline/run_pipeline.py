"""
Main Pipeline Runner - Orchestrates the Complete Data Processing Pipeline

This script coordinates all components to process raw HTML data and index it
to OpenSearch with advanced features for better search results.
"""

import logging
import multiprocessing
import time
from pathlib import Path
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

from file_reader import FileReader
from processor import DocumentProcessor
from indexer import OpenSearchIndexer

# Load environment variables
load_dotenv()

# Configuration
CRAWLER_DATA_DIR = Path(__file__).parent.parent.parent / "RawHTMLdata"
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "600"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", str(multiprocessing.cpu_count())))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "150"))
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "2000"))

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data_pipeline.log")
    ]
)

logger = logging.getLogger(__name__)


class DataPipeline:
    """Main pipeline orchestrator with advanced monitoring and optimization."""
    
    def __init__(self):
        self.file_reader = FileReader()
        self.processor = DocumentProcessor(
            min_content_length=MIN_CONTENT_LENGTH,
            max_chunk_size=MAX_CHUNK_SIZE
        )
        self.indexer = OpenSearchIndexer()
        
        self.processed_files = set()
        self.pipeline_stats = {
            'total_files_processed': 0,
            'total_documents_created': 0,
            'total_chunks_created': 0,
            'total_processing_time': 0,
            'start_time': time.time()
        }
    
    def initialize(self) -> bool:
        """Initialize the pipeline and verify all components."""
        logger.info("🚀 Initializing AI Search Data Pipeline...")
        
        # Verify data directory
        if not CRAWLER_DATA_DIR.exists():
            logger.error(f"Crawler data directory not found: {CRAWLER_DATA_DIR}")
            return False
        
        # Create OpenSearch indices
        if not self.indexer.create_indices():
            logger.error("Failed to create OpenSearch indices")
            return False
        
        # Perform health checks
        health = self.indexer.health_check()
        if health.get("status") != "healthy":
            logger.error(f"OpenSearch health check failed: {health}")
            return False
        
        logger.info("✅ Pipeline initialization successful")
        logger.info(f"📁 Monitoring directory: {CRAWLER_DATA_DIR}")
        logger.info(f"👥 Worker processes: {MAX_WORKERS}")
        logger.info(f"📦 Batch size: {BATCH_SIZE}")
        
        return True
    
    def file_processor_worker(self, file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Worker function for processing individual files."""
        try:
            processor = DocumentProcessor(
                min_content_length=MIN_CONTENT_LENGTH,
                max_chunk_size=MAX_CHUNK_SIZE
            )
            
            all_documents = []
            all_chunks = []
            
            for raw_doc in self.file_reader.read_json_file(file_path):
                result = processor.process_document(raw_doc)
                if result:
                    all_documents.extend(result["documents"])
                    all_chunks.extend(result["chunks"])
            
            file_stats = processor.get_processing_stats()
            logger.info(
                f"📄 Completed {file_path.name}: "
                f"{len(all_documents)} documents, {len(all_chunks)} chunks "
                f"(Success rate: {file_stats['success_rate']:.1f}%)"
            )
            
            return {
                "documents": all_documents,
                "chunks": all_chunks
            }
            
        except Exception as e:
            logger.error(f"❌ Worker failed on {file_path}: {e}")
            return {"documents": [], "chunks": []}
    
    def process_files_batch(self, new_files: List[Path]) -> bool:
        """Process a batch of files with optimized indexing."""
        if not new_files:
            return True
        
        logger.info(f"🔄 Processing batch of {len(new_files)} files...")
        batch_start_time = time.time()
        
        # Estimate total documents for progress tracking
        total_estimated_docs = sum(
            self.file_reader.estimate_document_count(f) for f in new_files
        )
        logger.info(f"📊 Estimated documents to process: {total_estimated_docs:,}")
        
        # Optimize OpenSearch for bulk operations
        original_settings = self.indexer.optimize_for_bulk_indexing()
        
        try:
            # Process files in parallel
            with multiprocessing.Pool(processes=MAX_WORKERS) as pool:
                logger.info(f"🚀 Starting parallel processing with {MAX_WORKERS} workers...")
                
                results_iterator = pool.imap_unordered(
                    self.file_processor_worker, 
                    new_files
                )
                
                # Collect and batch index results
                batch_documents = []
                batch_chunks = []
                files_processed = 0
                
                for file_result in results_iterator:
                    files_processed += 1
                    batch_documents.extend(file_result["documents"])
                    batch_chunks.extend(file_result["chunks"])
                    
                    # Index in smaller batches to manage memory
                    if (len(batch_documents) + len(batch_chunks)) >= BATCH_SIZE:
                        self._index_batch(batch_documents, batch_chunks)
                        batch_documents.clear()
                        batch_chunks.clear()
                    
                    # Progress logging
                    if files_processed % 10 == 0:
                        logger.info(f"⏳ Progress: {files_processed}/{len(new_files)} files processed")
                
                # Index remaining documents
                if batch_documents or batch_chunks:
                    self._index_batch(batch_documents, batch_chunks)
                
                # Update pipeline statistics
                batch_time = time.time() - batch_start_time
                self.pipeline_stats['total_files_processed'] += len(new_files)
                self.pipeline_stats['total_processing_time'] += batch_time
                
                logger.info(
                    f"✅ Batch complete in {batch_time:.1f}s: "
                    f"{len(new_files)} files processed"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Critical error in batch processing: {e}")
            return False
        
        finally:
            # Always restore OpenSearch settings
            self.indexer.restore_settings(original_settings)
            self.processed_files.update(new_files)
    
    def _index_batch(self, documents: List[Dict[str, Any]], chunks: List[Dict[str, Any]]):
        """Index a batch of documents and chunks."""
        if not documents and not chunks:
            return
        
        try:
            results = self.indexer.bulk_index_documents(
                documents=documents,
                chunks=chunks,
                thread_count=min(MAX_WORKERS, 4),
                chunk_size=BATCH_SIZE
            )
            
            self.pipeline_stats['total_documents_created'] += len(documents)
            self.pipeline_stats['total_chunks_created'] += len(chunks)
            
            logger.info(
                f"📤 Indexed batch: {len(documents)} docs, {len(chunks)} chunks "
                f"(Success: {results['success']}, Failed: {results['failed']})"
            )
            
        except Exception as e:
            logger.error(f"❌ Indexing batch failed: {e}")
    
    def scan_for_new_files(self) -> List[Path]:
        """Scan for new files to process."""
        all_files = self.file_reader.scan_directory(CRAWLER_DATA_DIR, recursive=True)
        new_files = self.file_reader.filter_new_files(all_files, self.processed_files)
        
        if new_files:
            # Log file information
            total_size_mb = sum(
                self.file_reader.get_file_info(f).get('size_mb', 0) 
                for f in new_files
            )
            logger.info(f"📁 Found {len(new_files)} new files ({total_size_mb:.1f} MB total)")
        
        return new_files
    
    def run_continuous_monitoring(self):
        """Run the pipeline in continuous monitoring mode."""
        logger.info("🔄 Starting continuous monitoring mode...")
        logger.info(f"⏰ Check interval: {CHECK_INTERVAL_SECONDS} seconds")
        
        iteration_count = 0
        
        while True:
            try:
                iteration_count += 1
                logger.info(f"\n🔍 Monitoring iteration #{iteration_count}")
                
                # Scan for new files
                new_files = self.scan_for_new_files()
                
                if new_files:
                    # Process new files
                    success = self.process_files_batch(new_files)
                    
                    if success:
                        logger.info("✅ Batch processing completed successfully")
                    else:
                        logger.error("❌ Batch processing failed")
                    
                    # Log pipeline statistics
                    self._log_pipeline_stats()
                    
                else:
                    logger.info("😴 No new files found. Waiting...")
                
                # Health check every 10 iterations
                if iteration_count % 10 == 0:
                    health = self.indexer.health_check()
                    logger.info(f"🔧 System health: {health.get('status', 'unknown')}")
                
                # Wait before next check
                logger.info(f"⏸️  Waiting {CHECK_INTERVAL_SECONDS} seconds...")
                time.sleep(CHECK_INTERVAL_SECONDS)
                
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal. Shutting down gracefully...")
                break
            
            except Exception as e:
                logger.error(f"❌ Unexpected error in monitoring loop: {e}")
                logger.info(f"⏳ Waiting {CHECK_INTERVAL_SECONDS} seconds before retry...")
                time.sleep(CHECK_INTERVAL_SECONDS)
        
        self._shutdown()
    
    def run_single_batch(self):
        """Run a single batch processing cycle."""
        logger.info("🔄 Running single batch processing...")
        
        new_files = self.scan_for_new_files()
        
        if not new_files:
            logger.info("😴 No new files found to process")
            return
        
        success = self.process_files_batch(new_files)
        
        if success:
            logger.info("✅ Single batch processing completed successfully")
            self._log_pipeline_stats()
        else:
            logger.error("❌ Single batch processing failed")
        
        self._shutdown()
    
    def _log_pipeline_stats(self):
        """Log comprehensive pipeline statistics."""
        runtime = time.time() - self.pipeline_stats['start_time']
        
        # File reader stats
        reader_stats = self.file_reader.get_processing_stats()
        
        # Processor stats
        processor_stats = self.processor.get_processing_stats()
        
        # Indexer stats
        indexer_stats = self.indexer.get_indexing_stats()
        
        logger.info("\n📊 PIPELINE STATISTICS")
        logger.info("=" * 50)
        logger.info(f"⏰ Total runtime: {runtime:.1f} seconds")
        logger.info(f"📁 Files processed: {self.pipeline_stats['total_files_processed']}")
        logger.info(f"📄 Documents created: {self.pipeline_stats['total_documents_created']:,}")
        logger.info(f"🧩 Chunks created: {self.pipeline_stats['total_chunks_created']:,}")
        logger.info(f"📈 Processing rate: {self.pipeline_stats['total_documents_created'] / max(runtime, 1):.1f} docs/sec")
        logger.info(f"✅ File success rate: {reader_stats.get('success_rate', 0):.1f}%")
        logger.info(f"🎯 Document success rate: {processor_stats.get('success_rate', 0):.1f}%")
        logger.info(f"📤 Indexing success rate: {indexer_stats.get('success_rate', 0):.1f}%")
        logger.info("=" * 50)
    
    def _shutdown(self):
        """Graceful shutdown of the pipeline."""
        logger.info("🔧 Performing graceful shutdown...")
        
        try:
            # Final statistics
            self._log_pipeline_stats()
            
            # Close connections
            self.indexer.close()
            
            logger.info("✅ Pipeline shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")


def main():
    """Main entry point for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Search Data Pipeline")
    parser.add_argument(
        "--mode",
        choices=["continuous", "single"],
        default="continuous",
        help="Pipeline mode: continuous monitoring or single batch"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Initialize and run pipeline
    pipeline = DataPipeline()
    
    if not pipeline.initialize():
        logger.error("❌ Pipeline initialization failed")
        return 1
    
    try:
        if args.mode == "continuous":
            pipeline.run_continuous_monitoring()
        else:
            pipeline.run_single_batch()
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
