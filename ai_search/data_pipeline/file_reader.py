"""
File Reading and Data Ingestion

Handles reading various file formats and preprocessing raw crawl data
for the document processing pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Generator, Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class FileReader:
    """Advanced file reading with validation and preprocessing."""
    
    def __init__(self, supported_extensions: Optional[List[str]] = None):
        self.supported_extensions = supported_extensions or ['.json', '.jsonl']
        self.stats = {
            'files_processed': 0,
            'documents_read': 0,
            'errors_count': 0,
            'empty_files': 0
        }
    
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
        """Read JSONL file line by line."""
        documents_count = 0
        line_number = 0
        
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
                    logger.warning(f"Invalid JSON on line {line_number} in {file_path}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error on line {line_number} in {file_path}: {e}")
                    continue
        
        return documents_count
    
    def _read_json(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Read regular JSON file."""
        documents_count = 0
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for i, document in enumerate(data):
                    if self._validate_document(document, file_path, i):
                        documents_count += 1
                        yield document
            elif isinstance(data, dict):
                if self._validate_document(data, file_path, 0):
                    documents_count = 1
                    yield data
            else:
                logger.error(f"Unexpected JSON structure in {file_path}: expected list or dict")
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
        
        return documents_count
    
    def _validate_document(self, document: Dict[str, Any], file_path: Path, position: int) -> bool:
        """Validate document structure and required fields."""
        if not isinstance(document, dict):
            logger.warning(f"Invalid document structure at position {position} in {file_path}: not a dict")
            return False
        
        # Check required fields
        required_fields = ['url']
        for field in required_fields:
            if field not in document:
                logger.warning(f"Missing required field '{field}' at position {position} in {file_path}")
                return False
        
        # Validate URL
        url = document.get('url', '').strip()
        if not url or not self._is_valid_url(url):
            logger.warning(f"Invalid URL at position {position} in {file_path}: {url}")
            return False
        
        # Check for content
        if not document.get('content'):
            logger.debug(f"No content field at position {position} in {file_path}")
            return False
        
        return True
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        return url.startswith(('http://', 'https://')) and len(url) > 10
    
    def scan_directory(self, directory: Path, recursive: bool = True) -> List[Path]:
        """Scan directory for supported files."""
        files = []
        
        try:
            if not directory.exists():
                logger.error(f"Directory does not exist: {directory}")
                return files
            
            pattern = "**/*" if recursive else "*"
            for file_path in directory.glob(pattern):
                if file_path.is_file() and file_path.suffix in self.supported_extensions:
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
                # For JSON, we need to parse to count
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return len(data)
                    elif isinstance(data, dict):
                        return 1
                    else:
                        return 0
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
        return {
            **self.stats,
            'success_rate': (
                (self.stats['files_processed'] - self.stats['errors_count']) / 
                max(self.stats['files_processed'], 1) * 100
            ),
            'avg_documents_per_file': (
                self.stats['documents_read'] / 
                max(self.stats['files_processed'] - self.stats['empty_files'], 1)
            )
        }
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            'files_processed': 0,
            'documents_read': 0,
            'errors_count': 0,
            'empty_files': 0
        }
    
    def batch_read_files(self, file_paths: List[Path], batch_size: int = 10) -> Generator[List[Dict[str, Any]], None, None]:
        """Read multiple files in batches for memory efficiency."""
        current_batch = []
        
        for file_path in file_paths:
            try:
                documents = list(self.read_json_file(file_path))
                current_batch.extend(documents)
                
                # Yield batch when it reaches the desired size
                if len(current_batch) >= batch_size:
                    yield current_batch
                    current_batch = []
                    
            except Exception as e:
                logger.error(f"Error in batch reading {file_path}: {e}")
                continue
        
        # Yield remaining documents
        if current_batch:
            yield current_batch
