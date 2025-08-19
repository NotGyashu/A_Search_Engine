"""
Enhanced Inspection Pipeline Runner - Process data and save to file for analysis.

This script runs the complete data pipeline but skips the final indexing step.
Instead, it writes the processed documents and chunks to a local JSON file,
allowing for detailed quality analysis and debugging.

Enhanced with support for:
- Original metadata preservation (meta descriptions, keywords, icons)
- Enhanced metadata analysis and reporting  
- Comprehensive field inspection and validation
"""

import logging
import multiprocessing
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import os
from collections import Counter, defaultdict
from dotenv import load_dotenv

from file_reader import FileReader
from processor import DocumentProcessor

# Load environment variables
load_dotenv()

# --- Configuration ---
# Use the same data directory as the main pipeline
CRAWLER_DATA_DIR = Path(__file__).parent.parent / "RawHTMLdata"
# Define a separate output directory for inspection files
INSPECTION_OUTPUT_DIR = Path("processed_inspection_output")

MAX_WORKERS = int(os.getenv("MAX_WORKERS", str(multiprocessing.cpu_count())))
MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "150"))
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "2000"))

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("inspection_pipeline.log")
    ]
)
logger = logging.getLogger(__name__)

# --- Worker Initialization (Identical to run_pipeline.py) ---
# This ensures the processing logic is exactly the same.
_worker_processor = None

def _init_worker():
    """Initialize worker process with a persistent DocumentProcessor instance."""
    global _worker_processor
    _worker_processor = DocumentProcessor(
        min_content_length=MIN_CONTENT_LENGTH,
        max_chunk_size=MAX_CHUNK_SIZE
    )
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def _file_processor_worker(file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Worker function that processes a single file and returns its data."""
    global _worker_processor
    try:
        all_documents = []
        all_chunks = []
        file_reader = FileReader()
        for doc in file_reader.read_json_file(file_path):
            result = _worker_processor.process_document(doc)
            if result:
                all_documents.extend(result["documents"])
                all_chunks.extend(result["chunks"])
        return {
            "documents": all_documents,
            "chunks": all_chunks,
        }
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return {"documents": [], "chunks": []}


class EnhancedMetadataAnalyzer:
    """Analyzes enhanced metadata fields in processed documents."""
    
    def __init__(self):
        self.metadata_stats = {
            'total_documents': 0,
            'with_original_meta_description': 0,
            'with_original_keywords': 0,
            'with_icons': 0,
            'with_canonical_url': 0,
            'keyword_combination_stats': {
                'only_original': 0,
                'only_generated': 0,
                'combined': 0,
                'mixed': 0,
                'none': 0
            },
            'icon_types': Counter(),
            'meta_description_usage': {
                'preserved_in_snippet': 0,
                'different_from_snippet': 0
            }
        }
    
    def analyze_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single document for enhanced metadata."""
        analysis = {
            'has_original_meta_description': bool(doc.get('original_meta_description')),
            'has_original_keywords': bool(doc.get('original_keywords')),
            'has_icons': bool(doc.get('icons')),
            'has_canonical_url': bool(doc.get('canonical_url')),
            'icon_count': len(doc.get('icons', {})) if doc.get('icons') else 0,
            'original_keyword_count': len(doc.get('original_keywords', [])) if doc.get('original_keywords') else 0,
            'total_keyword_count': len(doc.get('keywords', [])) if doc.get('keywords') else 0,
            'meta_description_preserved': False
        }
        
        # Check if meta description is preserved in snippet
        orig_desc = doc.get('original_meta_description')
        snippet = doc.get('text_snippet', '')
        if orig_desc and snippet:
            # Check if original description is used in snippet
            analysis['meta_description_preserved'] = orig_desc.strip().lower() in snippet.lower()
        
        # Analyze keyword combination
        orig_kw = set(doc.get('original_keywords', []) or [])
        all_kw = set(doc.get('keywords', []) or [])
        
        if orig_kw and all_kw:
            if orig_kw.issubset(all_kw):
                analysis['keyword_combination_type'] = 'combined'
            else:
                analysis['keyword_combination_type'] = 'mixed'
        elif orig_kw:
            analysis['keyword_combination_type'] = 'only_original'
        elif all_kw:
            analysis['keyword_combination_type'] = 'only_generated'
        else:
            analysis['keyword_combination_type'] = 'none'
        
        return analysis
    
    def update_stats(self, doc: Dict[str, Any], analysis: Dict[str, Any]):
        """Update overall statistics based on document analysis."""
        self.metadata_stats['total_documents'] += 1
        
        if analysis['has_original_meta_description']:
            self.metadata_stats['with_original_meta_description'] += 1
            
        if analysis['has_original_keywords']:
            self.metadata_stats['with_original_keywords'] += 1
            
        if analysis['has_icons']:
            self.metadata_stats['with_icons'] += 1
            # Count icon types
            icons = doc.get('icons', {})
            for icon_type in icons.keys():
                self.metadata_stats['icon_types'][icon_type] += 1
                
        if analysis['has_canonical_url']:
            self.metadata_stats['with_canonical_url'] += 1
        
        # Update keyword combination stats
        combo_type = analysis['keyword_combination_type']
        self.metadata_stats['keyword_combination_stats'][combo_type] += 1
        
        # Update meta description usage stats
        if analysis['has_original_meta_description']:
            if analysis['meta_description_preserved']:
                self.metadata_stats['meta_description_usage']['preserved_in_snippet'] += 1
            else:
                self.metadata_stats['meta_description_usage']['different_from_snippet'] += 1
    
    def generate_report(self) -> str:
        """Generate a comprehensive metadata analysis report."""
        stats = self.metadata_stats
        total = stats['total_documents']
        
        if total == 0:
            return "No documents to analyze."
        
        report = []
        report.append("🔍 ENHANCED METADATA ANALYSIS REPORT")
        report.append("=" * 50)
        report.append(f"Total Documents Analyzed: {total:,}")
        report.append("")
        
        # Original metadata preservation
        report.append("📋 ORIGINAL METADATA PRESERVATION:")
        report.append(f"  Original Meta Descriptions: {stats['with_original_meta_description']:,} ({(stats['with_original_meta_description']/total)*100:.1f}%)")
        report.append(f"  Original Keywords: {stats['with_original_keywords']:,} ({(stats['with_original_keywords']/total)*100:.1f}%)")
        report.append(f"  Icons Extracted: {stats['with_icons']:,} ({(stats['with_icons']/total)*100:.1f}%)")
        report.append(f"  Canonical URLs: {stats['with_canonical_url']:,} ({(stats['with_canonical_url']/total)*100:.1f}%)")
        report.append("")
        
        # Meta description usage analysis
        if stats['with_original_meta_description'] > 0:
            report.append("📄 META DESCRIPTION USAGE:")
            usage = stats['meta_description_usage']
            preserved = usage['preserved_in_snippet']
            different = usage['different_from_snippet']
            total_with_desc = preserved + different
            
            if total_with_desc > 0:
                report.append(f"  Preserved in Snippet: {preserved} ({(preserved/total_with_desc)*100:.1f}%)")
                report.append(f"  Different from Snippet: {different} ({(different/total_with_desc)*100:.1f}%)")
            report.append("")
        
        # Keyword combination analysis
        report.append("🏷️  KEYWORD COMBINATION ANALYSIS:")
        kw_stats = stats['keyword_combination_stats']
        for combo_type, count in kw_stats.items():
            if count > 0:
                report.append(f"  {combo_type.replace('_', ' ').title()}: {count} ({(count/total)*100:.1f}%)")
        report.append("")
        
        # Icon types analysis
        if stats['icon_types']:
            report.append("🎨 ICON TYPES FOUND:")
            for icon_type, count in stats['icon_types'].most_common(10):
                report.append(f"  {icon_type}: {count}")
            report.append("")
        
        # Quality assessment
        report.append("🎯 QUALITY ASSESSMENT:")
        enhancement_score = (
            (stats['with_original_meta_description'] / total) * 0.3 +
            (stats['with_original_keywords'] / total) * 0.3 +
            (stats['with_icons'] / total) * 0.2 +
            (stats['with_canonical_url'] / total) * 0.2
        ) * 100
        
        report.append(f"  Enhancement Score: {enhancement_score:.1f}%")
        
        if enhancement_score >= 80:
            report.append("  Status: ✅ Excellent metadata enhancement")
        elif enhancement_score >= 60:
            report.append("  Status: ✅ Good metadata enhancement")
        elif enhancement_score >= 40:
            report.append("  Status: ⚠️  Moderate metadata enhancement")
        else:
            report.append("  Status: ❌ Limited metadata enhancement")
        
        return "\n".join(report)


class InspectionPipeline:
    """Orchestrates processing and saves the output for inspection with enhanced metadata analysis."""

    def __init__(self, data_dir: str = None, config_path: str = None):
        self.data_dir = Path(data_dir) if data_dir else CRAWLER_DATA_DIR
        self.output_dir = Path.cwd() / "processed_inspection_output"
        
        self.file_reader = FileReader()
        # Initialize processor with enhanced metadata support
        self.processor = DocumentProcessor(
            min_content_length=MIN_CONTENT_LENGTH,
            max_chunk_size=MAX_CHUNK_SIZE
        )
        self.metadata_analyzer = EnhancedMetadataAnalyzer()
        self.processed_files = set()
        
        # Store config path for potential future use
        self.config_path = config_path
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized InspectionPipeline with data_dir: {self.data_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
        
        # Enhanced metadata tracking
        self.enhanced_metadata_report_path = self.output_dir / "enhanced_metadata_report.txt"

    def run(self):
        """Scan for files, process them, and write the output with enhanced metadata analysis."""
        logger.info("🚀 Starting Enhanced Inspection Pipeline...")
        
        if not self.data_dir.exists():
            logger.error(f"Data directory not found: {self.data_dir}")
            return

        # 1. Scan for all files (you might want to process only a subset for testing)
        all_files = self.file_reader.scan_directory(self.data_dir, recursive=True)
        if not all_files:
            logger.info("😴 No files found to process.")
            return

        logger.info(f"📁 Found {len(all_files)} files to process for inspection.")
        
        all_processed_documents = []
        all_processed_chunks = []
        
        # FIXED: Collect and aggregate stats from all workers
        aggregated_stats = {
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'total_processing_time': 0,
            'language_filtered': 0,
            'content_too_short': 0,
            'extraction_failed': 0
        }

        # 2. Process files in parallel
        try:
            with multiprocessing.Pool(
                processes=MAX_WORKERS,
                initializer=_init_worker
            ) as pool:
                logger.info(f"🚀 Starting parallel processing with {MAX_WORKERS} workers...")
                
                # Use imap_unordered to get results as they are completed
                results_iterator = pool.imap_unordered(_file_processor_worker, all_files)
                
                for i, file_result in enumerate(results_iterator):
                    all_processed_documents.extend(file_result["documents"])
                    all_processed_chunks.extend(file_result["chunks"])
                    
                    # FIXED: Aggregate stats from worker
                    worker_stats = file_result.get("stats", {})
                    for key in aggregated_stats:
                        aggregated_stats[key] += worker_stats.get(key, 0)
                    
                    logger.info(f"⏳ Progress: {i + 1}/{len(all_files)} files processed")

        except Exception as e:
            logger.error(f"❌ Critical error during parallel processing: {e}")
            return

        logger.info(f"✅ Processing complete. Found {len(all_processed_documents)} documents and {len(all_processed_chunks)} chunks.")

        # 3. Analyze enhanced metadata
        logger.info("🔍 Analyzing enhanced metadata...")
        for doc in all_processed_documents:
            analysis = self.metadata_analyzer.analyze_document(doc)
            self.metadata_analyzer.update_stats(doc, analysis)
        
        # Generate and save enhanced metadata report
        metadata_report = self.metadata_analyzer.generate_report()
        with open(self.enhanced_metadata_report_path, 'w', encoding='utf-8') as f:
            f.write(metadata_report)
        
        logger.info(f"📊 Enhanced metadata report saved to: {self.enhanced_metadata_report_path}")
        print("\n" + metadata_report)

        # 4. Write the collected data to files for inspection
        if all_processed_documents or all_processed_chunks:
            logger.info(f"✍️ Writing processed data to '{self.output_dir}' directory...")
            
            # FIXED: Pass aggregated stats to the processor for proper reporting
            self.processor.stats.update(aggregated_stats)
            
            self.processor.write_processed_documents(
                documents=all_processed_documents,
                chunks=all_processed_chunks,
                output_dir=str(self.output_dir),
                batch_name="inspection_run"
            )
        else:
            logger.warning("No documents or chunks were generated from the source files.")
            
        logger.info("✅ Enhanced inspection pipeline finished successfully.")
    
    def write_enhanced_metadata_sample(self, documents: list, sample_size: int = 10):
        """Write a sample of documents with enhanced metadata for detailed inspection."""
        if not documents:
            return
        
        sample_docs = documents[:sample_size]
        sample_file = self.output_dir / "enhanced_metadata_samples.json"
        
        sample_data = []
        for doc in sample_docs:
            enhanced_fields = {
                'url': doc.get('url', 'unknown'),
                'title': doc.get('title', ''),
                'original_meta_description': doc.get('original_meta_description'),
                'text_snippet': doc.get('text_snippet', '')[:200] + '...' if len(doc.get('text_snippet', '')) > 200 else doc.get('text_snippet', ''),
                'original_keywords': doc.get('original_keywords', []),
                'keywords': doc.get('keywords', []),
                'icons': doc.get('icons', {}),
                'canonical_url': doc.get('canonical_url'),
                'content_length': len(doc.get('content', '')),
                'chunk_count': doc.get('chunk_count', 0)
            }
            sample_data.append(enhanced_fields)
        
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📝 Enhanced metadata samples written to: {sample_file}")


def main():
    """Main entry point for the inspection script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run inspection pipeline with enhanced metadata analysis')
    parser.add_argument('--data-dir', type=str, help='Path to data directory (default: RawHTMLdata)')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--sample-size', type=int, default=10, help='Number of sample documents to write (default: 10)')
    
    args = parser.parse_args()
    
    pipeline = InspectionPipeline(data_dir=args.data_dir, config_path=args.config)
    try:
        pipeline.run()
        
        # Write enhanced metadata samples if documents were processed
        if hasattr(pipeline.metadata_analyzer, 'metadata_stats') and pipeline.metadata_analyzer.metadata_stats['total_documents'] > 0:
            # Get processed documents for sampling
            documents_file = pipeline.output_dir / "inspection_run_documents.json"
            if documents_file.exists():
                with open(documents_file, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                pipeline.write_enhanced_metadata_sample(documents, args.sample_size)
        
        return 0
    except Exception as e:
        logger.error(f"❌ Inspection pipeline execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

