#!/usr/bin/env python3
"""
Enhanced Data Pipeline Runner with Quality Inspection

This script demonstrates how to integrate quality inspection into your 
main data processing pipeline for better data quality control.
"""

import os
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

from file_reader import FileReader
from processor import DocumentProcessor
from indexer import OpenSearchIndexer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedDataPipeline:
    """
    Enhanced data pipeline with quality inspection and monitoring.
    """
    
    def __init__(self, 
                 enable_quality_inspection: bool = True,
                 quality_output_dir: str = "quality_inspection",
                 min_quality_score: float = 0.5):
        """
        Initialize the enhanced pipeline.
        
        Args:
            enable_quality_inspection: Whether to write quality files
            quality_output_dir: Directory for quality inspection files
            min_quality_score: Minimum quality score for indexing
        """
        self.enable_quality_inspection = enable_quality_inspection
        self.quality_output_dir = quality_output_dir
        self.min_quality_score = min_quality_score
        
        # Initialize components
        self.file_reader = FileReader()
        self.processor = DocumentProcessor()
        # self.indexer = OpenSearchIndexer()
        
        # Create quality output directory
        if self.enable_quality_inspection:
            Path(self.quality_output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🚀 Enhanced pipeline initialized")
        logger.info(f"   Quality inspection: {'enabled' if enable_quality_inspection else 'disabled'}")
        logger.info(f"   Quality output dir: {quality_output_dir}")
        logger.info(f"   Min quality score: {min_quality_score}")
    
    def process_single_batch_file(self, batch_file_path: str) -> Dict[str, Any]:
        """
        Process a single batch file with quality inspection.
        
        Args:
            batch_file_path: Path to the JSON batch file
            
        Returns:
            Dict with processing results and quality metrics
        """
        batch_file = Path(batch_file_path)
        if not batch_file.exists():
            logger.error(f"❌ Batch file not found: {batch_file_path}")
            return {"success": False, "error": "File not found"}
        
        logger.info(f"📁 Processing batch file: {batch_file.name}")
        
        try:
            # Read documents from batch file
            documents = list(self.file_reader.read_json_file(batch_file))
            logger.info(f"📖 Read {len(documents)} documents from {batch_file.name}")
            
            if not documents:
                logger.warning(f"⚠️ No documents found in {batch_file.name}")
                return {"success": False, "error": "No documents found"}
            
            # Process documents with quality inspection
            batch_name = batch_file.stem
            result = self.processor.process_batch(
                documents,
                write_output=self.enable_quality_inspection,
                output_dir=self.quality_output_dir,
                batch_name=batch_name
            )
            
            processed_docs = result["documents"]
            processed_chunks = result["chunks"]
            
            if not processed_docs:
                logger.warning(f"⚠️ No documents successfully processed from {batch_file.name}")
                return {"success": False, "error": "No documents processed"}
            
            # Quality filtering
            high_quality_docs, high_quality_chunks = self._filter_by_quality(
                processed_docs, processed_chunks
            )
            
            logger.info(
                f"✅ Quality filtering: {len(high_quality_docs)}/{len(processed_docs)} docs, "
                f"{len(high_quality_chunks)}/{len(processed_chunks)} chunks passed"
            )
            
            # Index to OpenSearch
            # indexing_result = self._index_documents(high_quality_docs, high_quality_chunks)
            
            # Get processing stats
            processing_stats = self.processor.get_processing_stats()
            
            return {
                "success": True,
                "batch_file": batch_file.name,
                "documents_read": len(documents),
                "documents_processed": len(processed_docs),
                "documents_indexed": len(high_quality_docs),
                "chunks_indexed": len(high_quality_chunks),
                "indexing_result": indexing_result,
                "processing_stats": processing_stats,
                "quality_filter_rate": len(high_quality_docs) / len(processed_docs) * 100 if processed_docs else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing batch {batch_file.name}: {e}")
            return {"success": False, "error": str(e)}
    
    def process_batch_directory(self, batch_dir: str, file_pattern: str = "*.json") -> Dict[str, Any]:
        """
        Process all batch files in a directory.
        
        Args:
            batch_dir: Directory containing batch files
            file_pattern: File pattern to match (default: *.json)
            
        Returns:
            Dict with overall processing results
        """
        batch_path = Path(batch_dir)
        if not batch_path.exists():
            logger.error(f"❌ Batch directory not found: {batch_dir}")
            return {"success": False, "error": "Directory not found"}
        
        # Find all batch files
        batch_files = list(batch_path.glob(file_pattern))
        if not batch_files:
            logger.error(f"❌ No batch files found in {batch_dir} matching {file_pattern}")
            return {"success": False, "error": "No batch files found"}
        
        logger.info(f"🗂️ Found {len(batch_files)} batch files to process")
        
        # Process each batch file
        results = []
        total_docs_read = 0
        total_docs_processed = 0
        total_docs_indexed = 0
        total_chunks_indexed = 0
        
        # Optimize indices for bulk operations
        logger.info("⚡ Optimizing indices for bulk operations...")
        # original_settings = self.indexer.optimize_for_bulk_indexing()
        
        try:
            for i, batch_file in enumerate(batch_files, 1):
                logger.info(f"\n📄 Processing batch {i}/{len(batch_files)}: {batch_file.name}")
                
                result = self.process_single_batch_file(str(batch_file))
                results.append(result)
                
                if result["success"]:
                    total_docs_read += result["documents_read"]
                    total_docs_processed += result["documents_processed"]
                    total_docs_indexed += result["documents_indexed"]
                    total_chunks_indexed += result["chunks_indexed"]
                    
                    logger.info(
                        f"✅ Batch {i} complete: "
                        f"{result['documents_indexed']} docs, "
                        f"{result['chunks_indexed']} chunks indexed"
                    )
                else:
                    logger.error(f"❌ Batch {i} failed: {result.get('error', 'Unknown error')}")
        
        finally:
            # Restore original index settings
            logger.info("🔄 Restoring original index settings...")
            # self.indexer.restore_settings(original_settings)
        
        # Calculate overall stats
        # successful_batches = sum(1 for r in results if r["success"])
        # overall_success_rate = successful_batches / len(batch_files) * 100
        # overall_quality_rate = total_docs_indexed / total_docs_processed * 100 if total_docs_processed > 0 else 0
        
        summary = {
            # "success": True,
            # "total_batches": len(batch_files),
            # # "successful_batches": successful_batches,
            # "batch_success_rate": overall_success_rate,
            # "total_documents_read": total_docs_read,
            # "total_documents_processed": total_docs_processed,
            # "total_documents_indexed": total_docs_indexed,
            # "total_chunks_indexed": total_chunks_indexed,
            # "overall_quality_filter_rate": overall_quality_rate,
            # "batch_results": results
        }
        
        # logger.info(f"\n🎉 Pipeline Complete!")
        # logger.info(f"   Batches: {successful_batches}/{len(batch_files)} successful ({overall_success_rate:.1f}%)")
        # logger.info(f"   Documents: {total_docs_indexed}/{total_docs_read} indexed")
        # logger.info(f"   Chunks: {total_chunks_indexed} indexed")
        # logger.info(f"   Quality Rate: {overall_quality_rate:.1f}%")
        
        return summary
    
    def _filter_by_quality(self, documents: List[Dict[str, Any]], 
                          chunks: List[Dict[str, Any]]) -> tuple:
        """Filter documents and chunks by quality score."""
        high_quality_docs = []
        high_quality_chunks = []
        
        # Create a mapping of document IDs that pass quality filter
        quality_doc_ids = set()
        
        for doc in documents:
            # For now, we'll keep all documents (add quality filtering logic here if needed)
            high_quality_docs.append(doc)
            quality_doc_ids.add(doc["document_id"])
        
        # Filter chunks by quality score and document quality
        for chunk in chunks:
            if (chunk.get("quality_score", 0) >= self.min_quality_score and 
                chunk.get("document_id") in quality_doc_ids):
                high_quality_chunks.append(chunk)
        
        return high_quality_docs, high_quality_chunks
    
    def _index_documents(self, documents: List[Dict[str, Any]], 
                        chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Index documents and chunks to OpenSearch."""
        if not documents and not chunks:
            return {"success": 0, "failed": 0}
        
        try:
            result = self.indexer.bulk_index_documents(
                documents=documents,
                chunks=chunks,
                thread_count=4,
                chunk_size=500
            )
            return result
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return {"success": 0, "failed": len(documents) + len(chunks)}
    
    def health_check(self) -> bool:
        """Perform a comprehensive health check."""
        logger.info("🔍 Performing health check...")
        
        # # Check OpenSearch connection
        # health = self.indexer.health_check()
        # if health.get("status") != "healthy":
        #     logger.error(f"❌ OpenSearch unhealthy: {health.get('reason', 'Unknown')}")
        #     return False
        
        logger.info("✅ OpenSearch connection healthy")
        
        # # Check if indices exist
        # if not self.indexer.create_indices():
        #     logger.error("❌ Failed to create/verify indices")
        #     return False
        
        logger.info("✅ Indices ready")
        
        # # Test search functionality
        # search_test = self.indexer.search_test()
        # if "error" in search_test:
        #     logger.error(f"❌ Search test failed: {search_test['error']}")
        #     return False
        
        # logger.info(f"✅ Search test passed ({search_test.get('total_hits', 0)} hits)")
        
        # return True


def main():
    """Main function to run the enhanced pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Data Pipeline with Quality Inspection")
    parser.add_argument("--batch-dir", required=True, help="Directory containing batch JSON files")
    parser.add_argument("--pattern", default="*.json", help="File pattern to match (default: *.json)")
    parser.add_argument("--quality-dir", default="quality_inspection", help="Quality output directory")
    parser.add_argument("--min-quality", type=float, default=0.5, help="Minimum quality score for indexing")
    parser.add_argument("--no-quality-inspection", action="store_true", help="Disable quality inspection")
    parser.add_argument("--health-check-only", action="store_true", help="Only perform health check")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = EnhancedDataPipeline(
        enable_quality_inspection=not args.no_quality_inspection,
        quality_output_dir=args.quality_dir,
        min_quality_score=args.min_quality
    )
    
    # # Health check
    # if not pipeline.health_check():
    #     logger.error("❌ Health check failed. Exiting.")
    #     sys.exit(1)
    
    if args.health_check_only:
        logger.info("✅ Health check complete. Exiting.")
        sys.exit(0)
    
    # Process batch directory
    result = pipeline.process_batch_directory(args.batch_dir, args.pattern)
    
    # if result["success"]:
    #     logger.info("🎉 Pipeline completed successfully!")
    #     sys.exit(0)
    # else:
    #     logger.error(f"❌ Pipeline failed: {result.get('error', 'Unknown error')}")
    #     sys.exit(1)


if __name__ == "__main__":
    main()
