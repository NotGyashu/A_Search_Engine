"""
File Reading and Data Ingestion

Handles reading various file formats and preprocessing raw crawl data
for the document processing pipeline with memory-efficient streaming.
"""

import json
import logging
from pathlib import Path
from typing import Generator, Dict, Any, List, Optional

# Import ijson for memory-efficient JSON parsing (required dependency)
try:
    import ijson
except ImportError:
    raise ImportError(
        "ijson is required for memory-efficient processing. "
        "Install it with: pip install ijson"
    )

logger = logging.getLogger(__name__)


class FileReader:
    """Advanced file reading with validation and preprocessing."""
    
    def __init__(self, supported_extensions: Optional[List[str]] = None):
        self.supported_extensions = supported_extensions or ['.json', '.jsonl']
        self.stats = {
            'files_processed': 0,
            'documents_read': 0,
            'errors_count': 0,
            'empty_files': 0,
            'validation_errors': 0,
            'invalid_urls': 0,
            'missing_content': 0
        }
        # Validation error tracking (to avoid log flooding)
        self._validation_error_counts = {}
        self._log_validation_threshold = 100  # Log every N validation errors
    
    def read_json_file(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Read JSON or JSONL files with enhanced error handling and validation."""
        try:
            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return
            
            if file_path.suffix not in self.supported_extensions:
                logger.warning(f"Unsupported file extension: {file_path.suffix}")
                return
            
            documents_count = 0
            
            if file_path.suffix == ".jsonl":
                documents_count = yield from self._read_jsonl(file_path)
            else:
                documents_count = yield from self._read_json(file_path)
            
            if documents_count == 0:
                self.stats['empty_files'] += 1
                logger.warning(f"No valid documents found in {file_path}")
            else:
                self.stats['documents_read'] += documents_count
                logger.info(f"Successfully read {documents_count} documents from {file_path}")
            
            self.stats['files_processed'] += 1
            
        except Exception as e:
            self.stats['errors_count'] += 1
            logger.error(f"Error reading file {file_path}: {e}")
    
    def _read_jsonl(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Read JSONL file line by line with optimized error handling."""
        documents_count = 0
        line_number = 0
        json_errors = 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_number += 1
                line = line.strip()
                
                if not line:  # Skip empty lines
                    continue
                
                try:
                    document = json.loads(line)
                    if self._validate_document(document, file_path, line_number):
                        documents_count += 1
                        yield document
                except json.JSONDecodeError as e:
                    json_errors += 1
                    # Log only first few JSON errors to avoid flooding
                    if json_errors <= 5:
                        logger.warning(f"Invalid JSON on line {line_number} in {file_path}: {e}")
                    elif json_errors == 6:
                        logger.warning(f"More JSON decode errors in {file_path} (suppressing further warnings)")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error on line {line_number} in {file_path}: {e}")
                    continue
        
        if json_errors > 5:
            logger.warning(f"Total JSON decode errors in {file_path}: {json_errors}")
        
        return documents_count
    
    def _read_json(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Read regular JSON file with memory-efficient streaming."""
        logger.debug(f"Using streaming parser for: {file_path}")
        return self._read_json_streaming(file_path)
    
    def _read_json_streaming(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Memory-efficient streaming JSON parser using ijson."""
        documents_count = 0
        
        try:
            with open(file_path, 'rb') as f:
                # Parse JSON array items one by one
                parser = ijson.items(f, 'item')
                for i, document in enumerate(parser):
                    if self._validate_document(document, file_path, i):
                        documents_count += 1
                        yield document
                        
        except Exception as e:
            logger.error(f"Error streaming JSON file {file_path}: {e}")
            raise  # Don't fallback - fail fast for proper error handling
        
        return documents_count
    
    def _validate_document(self, document: Dict[str, Any], file_path: Path, position: int) -> bool:
        """Validate document structure and required fields with reduced logging."""
        if not isinstance(document, dict):
            self.stats['validation_errors'] += 1
            self._log_validation_error(f"Invalid document structure at position {position} in {file_path}: not a dict")
            return False
        
        # Check required fields
        required_fields = ['url']
        for field in required_fields:
            if field not in document:
                self.stats['validation_errors'] += 1
                self._log_validation_error(f"Missing required field '{field}' at position {position} in {file_path}")
                return False
        
        # Validate URL
        url = document.get('url', '').strip()
        if not url or not self._is_valid_url(url):
            self.stats['invalid_urls'] += 1
            self._log_validation_error(f"Invalid URL at position {position} in {file_path}: {url}")
            return False
        
        # Check for content
        if not document.get('content'):
            self.stats['missing_content'] += 1
            # Don't log missing content as it's often expected
            return False
        
        return True
    
    def _log_validation_error(self, message: str):
        """Log validation errors with throttling to prevent log flooding."""
        error_key = message.split(':')[0]  # Use error type as key
        
        self._validation_error_counts[error_key] = self._validation_error_counts.get(error_key, 0) + 1
        
        # Log only the first occurrence and every Nth occurrence
        count = self._validation_error_counts[error_key]
        if count == 1 or count % self._log_validation_threshold == 0:
            if count > 1:
                logger.warning(f"{message} (occurred {count} times)")
            else:
                logger.warning(message)
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        return url.startswith(('http://', 'https://')) and len(url) > 10
    
    def scan_directory(self, directory: Path, recursive: bool = True, min_mtime: float = 0) -> List[Path]:
        """Scan directory for supported files with optional modification time filtering."""
        files = []
        
        try:
            if not directory.exists():
                logger.error(f"Directory does not exist: {directory}")
                return files
            
            pattern = "**/*" if recursive else "*"
            for file_path in directory.glob(pattern):
                if (file_path.is_file() and 
                    file_path.suffix in self.supported_extensions and
                    file_path.stat().st_mtime > min_mtime):
                    files.append(file_path)
            
            logger.info(f"Found {len(files)} supported files in {directory}")
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
        
        return sorted(files)  # Sort for consistent processing order
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get metadata about a file."""
        try:
            stat = file_path.stat()
            return {
                'path': str(file_path),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_time': stat.st_mtime,
                'extension': file_path.suffix,
                'stem': file_path.stem
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {}
    
    def estimate_document_count(self, file_path: Path) -> int:
        """Estimate number of documents in a file without full parsing."""
        try:
            if file_path.suffix == ".jsonl":
                # Count lines for JSONL
                with open(file_path, 'r', encoding='utf-8') as f:
                    return sum(1 for line in f if line.strip())
            else:
                # For JSON, use streaming counter to avoid loading entire file
                count = 0
                with open(file_path, 'rb') as f:
                    parser = ijson.items(f, 'item')
                    for _ in parser:
                        count += 1
                return count
        except Exception as e:
            logger.warning(f"Could not estimate document count for {file_path}: {e}")
            return 0
    
    def filter_new_files(self, all_files: List[Path], processed_files: set) -> List[Path]:
        """Filter out already processed files."""
        new_files = [f for f in all_files if f not in processed_files]
        
        if new_files:
            logger.info(f"Found {len(new_files)} new files to process")
        else:
            logger.info("No new files found")
        
        return new_files
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get file processing statistics."""
        total_validation_errors = (self.stats['validation_errors'] + 
                                 self.stats['invalid_urls'] + 
                                 self.stats['missing_content'])
        
        return {
            **self.stats,
            'total_validation_errors': total_validation_errors,
            'success_rate': (
                (self.stats['files_processed'] - self.stats['errors_count']) / 
                max(self.stats['files_processed'], 1) * 100
            ),
            'avg_documents_per_file': (
                self.stats['documents_read'] / 
                max(self.stats['files_processed'] - self.stats['empty_files'], 1)
            ),
            'validation_error_types': dict(self._validation_error_counts)
        }
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            'files_processed': 0,
            'documents_read': 0,
            'errors_count': 0,
            'empty_files': 0,
            'validation_errors': 0,
            'invalid_urls': 0,
            'missing_content': 0
        }
        self._validation_error_counts = {}
    
    def batch_read_files(self, file_paths: List[Path]) -> Generator[List[Dict[str, Any]], None, None]:
        """Read files one at a time to reduce memory usage (file-based batching)."""
        for file_path in file_paths:
            try:
                # Process one file at a time and yield all its documents as a batch
                documents = list(self.read_json_file(file_path))
                if documents:  # Only yield non-empty batches
                    yield documents
                    
            except Exception as e:
                logger.error(f"Error in batch reading {file_path}: {e}")
                continue
