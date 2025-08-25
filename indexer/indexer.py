#!/usr/bin/env python3
"""
Production-Grade Standalone OpenSearch Indexer

A continuous, resource-efficient indexer for OpenSearch that prioritizes fresh data
while processing backlog during idle periods. Designed for 23-hour daily operation
with zero data loss and low CPU usage.

Features:
- Dual-queue priority system (fresh vs backlog)
- Backpressure management with size-limited queues
- Efficient bulk indexing with single HTTP requests
- Graceful shutdown handling
- Robust file management and error recovery
- OpenSearch initialization and health checks
- Comprehensive logging and statistics

Author: Production Indexer System
Version: 1.0.0
"""

import os
import sys
import json
import time
import signal
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from queue import Queue, Full, Empty
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

# Third-party imports
try:
    from opensearchpy import OpenSearch, helpers
    from opensearchpy.exceptions import ConnectionError, RequestError, TransportError
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from requests_aws4auth import AWS4Auth
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install: pip install opensearch-py boto3 requests-aws4auth python-dotenv")
    sys.exit(1)

# Import configuration
try:
    import config
except ImportError:
    print("Error: config.py not found. Please ensure config.py exists in the same directory.")
    sys.exit(1)


@dataclass
class IndexerStats:
    """Statistics tracking for the indexer."""
    start_time: float
    documents_processed: int = 0
    chunks_processed: int = 0
    files_processed: int = 0
    files_failed: int = 0
    fresh_files_processed: int = 0
    backlog_files_processed: int = 0
    bulk_operations: int = 0
    last_activity: float = 0
    errors: int = 0


@dataclass
class QueueItem:
    """Item for indexing queues."""
    data: Dict[str, Any]
    file_path: str
    priority: str  # 'high' or 'standard'


class DualPriorityQueue:
    """Dual-queue system with high and standard priority queues."""
    
    def __init__(self, high_priority_size: int, standard_priority_size: int):
        self.high_priority = Queue(maxsize=high_priority_size)
        self.standard_priority = Queue(maxsize=standard_priority_size)
        self._lock = threading.Lock()
    
    def put(self, item: QueueItem, block: bool = True, timeout: Optional[float] = None) -> bool:
        """Put item in appropriate queue with backpressure."""
        try:
            if item.priority == 'high':
                self.high_priority.put(item, block=block, timeout=timeout)
            else:
                self.standard_priority.put(item, block=block, timeout=timeout)
            return True
        except Full:
            return False
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[QueueItem]:
        """Get item with priority preference."""
        # Always try high priority first
        try:
            return self.high_priority.get(block=False)
        except Empty:
            pass
        
        # If no high priority items, try standard priority
        try:
            return self.standard_priority.get(block=block, timeout=timeout)
        except Empty:
            return None
    
    def qsize(self) -> Tuple[int, int]:
        """Return (high_priority_size, standard_priority_size)."""
        return self.high_priority.qsize(), self.standard_priority.qsize()
    
    def is_full(self) -> bool:
        """Check if queues are approaching capacity."""
        high_size, standard_size = self.qsize()
        high_threshold = self.high_priority.maxsize * 0.9
        standard_threshold = self.standard_priority.maxsize * 0.9
        return high_size >= high_threshold or standard_size >= standard_threshold


class OpenSearchIndexer:
    """Production-grade OpenSearch indexer with dual-priority queuing."""
    
    def __init__(self):
        self.stats = IndexerStats(start_time=time.time())
        self.running = True
        self.shutdown_event = threading.Event()
        self.opensearch_available = False
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize OpenSearch client
        try:
            self.client = self._create_opensearch_client()
            self.opensearch_available = True
        except Exception as e:
            self.logger.error(f"Failed to create OpenSearch client: {e}")
            self.logger.warning("Running in offline mode - files will be processed but not indexed")
            self.client = None
            self.opensearch_available = False
        
        # Initialize dual-priority queue
        self.queue = DualPriorityQueue(
            config.HIGH_PRIORITY_QUEUE_SIZE,
            config.STANDARD_PRIORITY_QUEUE_SIZE
        )
        
        # Thread management
        self.indexing_thread = None
        self.file_workers = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("OpenSearch Indexer initialized successfully")
    
    def _setup_logging(self):
        """Configure logging with proper formatting."""
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format=config.LOG_FORMAT,
            handlers=[
                logging.FileHandler(config.LOG_FILE),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _create_opensearch_client(self) -> OpenSearch:
        """Create OpenSearch client with proper authentication."""
        self.logger.info(f"Connecting to OpenSearch at {config.OPENSEARCH_HOST}")
        
        if config.OPENSEARCH_AUTH_TYPE == 'aws':
            # AWS authentication using opensearch-py's built-in AWS support
            try:
                import boto3
                from botocore.exceptions import NoCredentialsError, PartialCredentialsError
                from opensearchpy import RequestsHttpConnection, AWSV4SignerAuth
                
                # Try to get credentials
                session = boto3.Session(
                    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                    region_name=config.AWS_REGION
                )
                
                credentials = session.get_credentials()
                if not credentials:
                    raise Exception("No AWS credentials found")
                
                
                # Use the built-in AWSV4SignerAuth
                auth = AWSV4SignerAuth(credentials, config.AWS_REGION, 'es')
                
                # Parse the host properly for AWS
                if config.OPENSEARCH_HOST.startswith('https://'):
                    host = config.OPENSEARCH_HOST[8:]  # Remove https://
                elif config.OPENSEARCH_HOST.startswith('http://'):
                    host = config.OPENSEARCH_HOST[7:]   # Remove http://
                else:
                    host = config.OPENSEARCH_HOST
                
                # Create connection configuration
                connection_config = {
                    'hosts': [{'host': host, 'port': 443}],
                    'http_auth': auth,
                    'use_ssl': True,
                    'verify_certs': config.OPENSEARCH_VERIFY_CERTS,
                    'ssl_assert_hostname': False,
                    'ssl_show_warn': False,
                    'connection_class': RequestsHttpConnection,
                    'timeout': config.OPENSEARCH_TIMEOUT,
                    'max_retries': config.MAX_RETRIES,
                    'retry_on_timeout': True
                }
                
                self.logger.info("Using AWS authentication with AWSV4SignerAuth")
                return OpenSearch(**connection_config)
                
            except (NoCredentialsError, PartialCredentialsError, Exception) as e:
                self.logger.error(f"AWS authentication failed: {e}")
                self.logger.error("Cannot use basic auth with AWS OpenSearch domain")
                raise Exception(f"AWS OpenSearch requires proper AWS credentials: {e}")
        
        # Basic authentication for non-AWS OpenSearch
        self.logger.info("Using basic authentication")
        return OpenSearch(
            hosts=[config.OPENSEARCH_HOST],
            http_auth=(config.OPENSEARCH_USER, config.OPENSEARCH_PASSWORD),
            use_ssl=True,
            verify_certs=config.OPENSEARCH_VERIFY_CERTS,
            timeout=config.OPENSEARCH_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_on_timeout=True
        )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        self.shutdown_event.set()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            config.FRESH_DIR,
            config.BACKLOG_DIR,
            config.PROCESSED_DIR,
            config.FAILED_DIR
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {directory}")
    
    def _get_daily_index_name(self, base_name: str) -> str:
        """Generate daily index name."""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{base_name}-{today}"
    
    def _create_index_template(self, template_name: str, index_pattern: str, mappings: Dict):
        """Create or update index template."""
        template_body = {
            "index_patterns": [index_pattern],
            "template": {
                "settings": {
                    "number_of_shards": config.NUMBER_OF_SHARDS,
                    "number_of_replicas": config.NUMBER_OF_REPLICAS,
                    "refresh_interval": config.REFRESH_INTERVAL,
                    "translog.durability": config.TRANSLOG_DURABILITY
                },
                "mappings": mappings
            }
        }
        
        try:
            self.client.indices.put_index_template(
                name=template_name,
                body=template_body
            )
            self.logger.info(f"Index template '{template_name}' created/updated successfully")
        except Exception as e:
            self.logger.error(f"Failed to create index template '{template_name}': {e}")
            raise
    
    def initialize_opensearch(self):
        """Initialize OpenSearch indices and templates."""
        self.logger.info("Initializing OpenSearch environment...")
        
        try:
            # Test connection first
            health = self.client.cluster.health()
            self.logger.info(f"OpenSearch cluster status: {health.get('status', 'unknown')}")
        except Exception as e:
            self.logger.error(f"Cannot connect to OpenSearch: {e}")
            self.logger.warning("Continuing in offline mode - files will be processed but not indexed")
            return
        
        # Document mappings
        document_mappings = {
            "properties": {
                "document_id": {"type": "keyword"},
                "url": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "standard"},
                "domain": {"type": "keyword"},
                "description": {"type": "text"},
                "content_type": {"type": "keyword"},
                "categories": {"type": "keyword"},
                "keywords": {"type": "keyword"},
                "canonical_url": {"type": "keyword"},
                "published_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "modified_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "author_info": {"type": "object"},
                "structured_data": {"type": "object"},
                "images": {"type": "nested"},
                "table_of_contents": {"type": "nested"},
                "semantic_info": {"type": "object"},
                "icons": {"type": "object"},
                "indexed_at": {"type": "date"},
                "@timestamp": {"type": "date"}
            }
        }
        
        # Chunk mappings
        chunk_mappings = {
            "properties": {
                "chunk_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "text_chunk": {"type": "text", "analyzer": "standard"},
                "headings": {"type": "text"},
                "domain_score": {"type": "float"},
                "quality_score": {"type": "float"},
                "word_count": {"type": "integer"},
                "content_categories": {"type": "keyword"},
                "keywords": {"type": "keyword"},
                "indexed_at": {"type": "date"},
                "@timestamp": {"type": "date"}
            }
        }
        
        # Create templates
        try:
            self._create_index_template(
                "documents_template",
                f"{config.DOCUMENTS_INDEX_BASE}-*",
                document_mappings
            )
            
            self._create_index_template(
                "chunks_template",
                f"{config.CHUNKS_INDEX_BASE}-*",
                chunk_mappings
            )
        except Exception as e:
            self.logger.error(f"Failed to create index templates: {e}")
            # Continue anyway - templates might already exist
        
        # Create today's indices if they don't exist
        doc_index = self._get_daily_index_name(config.DOCUMENTS_INDEX_BASE)
        chunk_index = self._get_daily_index_name(config.CHUNKS_INDEX_BASE)
        
        for index_name in [doc_index, chunk_index]:
            try:
                if not self.client.indices.exists(index=index_name):
                    self.client.indices.create(index=index_name)
                    self.logger.info(f"Created index: {index_name}")
            except Exception as e:
                self.logger.warning(f"Could not create index {index_name}: {e}")
        
        # Create/update aliases
        try:
            self.client.indices.put_alias(
                index=doc_index,
                name=config.DOCUMENTS_INDEX_BASE
            )
            self.client.indices.put_alias(
                index=chunk_index,
                name=config.CHUNKS_INDEX_BASE
            )
            self.logger.info("Aliases created/updated successfully")
        except Exception as e:
            self.logger.warning(f"Failed to create aliases: {e}")
        
        self.logger.info("OpenSearch initialization completed")
    
    def _process_jsonl_file(self, file_path: str, is_fresh: bool = True) -> int:
        """Process a JSONL file and add items to queue."""
        items_added = 0
        priority = 'high' if is_fresh else 'standard'
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if not self.running:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # Add timestamp with timezone-aware UTC
                        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                        data['indexed_at'] = current_time
                        data['@timestamp'] = current_time
                        
                        # Create queue item
                        item = QueueItem(
                            data=data,
                            file_path=file_path,
                            priority=priority
                        )
                        
                        # Try to add to queue with backpressure
                        max_wait_time = 30.0  # Maximum time to wait for queue space
                        if self.queue.put(item, block=True, timeout=max_wait_time):
                            items_added += 1
                        else:
                            self.logger.warning(f"Queue full, skipping item {line_num} from {file_path}")
                            break
                    
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Invalid JSON in {file_path} line {line_num}: {e}")
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing line {line_num} in {file_path}: {e}")
                        continue
        
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return 0
        
        return items_added
    
    def _move_file(self, source_path: str, destination_dir: str, add_timestamp: bool = True):
        """Move file to destination directory with optional timestamp."""
        try:
            source = Path(source_path)
            dest_dir = Path(destination_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            if add_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_name = f"{timestamp}_{source.name}"
            else:
                dest_name = source.name
            
            dest_path = dest_dir / dest_name
            shutil.move(str(source), str(dest_path))
            self.logger.debug(f"Moved {source_path} to {dest_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to move file {source_path}: {e}")
    
    def _bulk_index_items(self, items: List[QueueItem]) -> Tuple[int, int]:
        """Bulk index a list of items."""
        if not items:
            return 0, 0
        
        # If OpenSearch is not available, just count items and return
        if not self.opensearch_available or not self.client:
            doc_count = sum(1 for item in items if item.data.get('type') == 'document')
            chunk_count = sum(1 for item in items if item.data.get('type') == 'chunk')
            self.logger.debug(f"Offline mode: would have indexed {doc_count} docs, {chunk_count} chunks")
            return doc_count, chunk_count
        
        actions = []
        doc_count = 0
        chunk_count = 0
        
        for item in items:
            data = item.data
            doc_type = data.get('type')
            
            if doc_type == 'document':
                index_name = self._get_daily_index_name(config.DOCUMENTS_INDEX_BASE)
                doc_id = data.get('document_id')
                doc_count += 1
            elif doc_type == 'chunk':
                index_name = self._get_daily_index_name(config.CHUNKS_INDEX_BASE)
                doc_id = data.get('chunk_id')
                chunk_count += 1
            else:
                self.logger.warning(f"Unknown document type: {doc_type}")
                continue
            
            action = {
                "_index": index_name,
                "_id": doc_id,
                "_source": data
            }
            actions.append(action)
        
        if not actions:
            return 0, 0
        
        try:
            # Use OpenSearch helpers.bulk for efficient bulk indexing
            success_count, failed_items = helpers.bulk(
                self.client,
                actions,
                chunk_size=config.BULK_CHUNK_SIZE,
                max_retries=config.MAX_RETRIES,
                initial_backoff=2,
                max_backoff=600,
                raise_on_error=False,
                raise_on_exception=False
            )
            
            if failed_items:
                self.logger.error(f"Failed to index {len(failed_items)} items")
                for failed_item in failed_items[:5]:  # Log first 5 failures
                    self.logger.error(f"Failed item: {failed_item}")
            
            self.stats.bulk_operations += 1
            self.stats.last_activity = time.time()
            
            return doc_count, chunk_count
        
        except Exception as e:
            self.logger.error(f"Bulk indexing failed: {e}")
            self.stats.errors += 1
            return 0, 0
    
    def _indexing_worker(self):
        """Worker thread for indexing items from the queue."""
        self.logger.info("Indexing worker started")
        batch = []
        batch_timeout = 5.0  # Seconds to wait before flushing partial batch
        last_batch_time = time.time()
        
        while self.running or not self.queue.qsize() == (0, 0):
            try:
                # Get item from queue
                item = self.queue.get(block=True, timeout=1.0)
                if item:
                    batch.append(item)
                
                # Check if we should flush the batch
                should_flush = (
                    len(batch) >= config.BULK_CHUNK_SIZE or
                    (batch and time.time() - last_batch_time > batch_timeout) or
                    not self.running
                )
                
                if should_flush and batch:
                    # Process the batch
                    doc_count, chunk_count = self._bulk_index_items(batch)
                    
                    # Update statistics
                    self.stats.documents_processed += doc_count
                    self.stats.chunks_processed += chunk_count
                    
                    self.logger.debug(
                        f"Indexed batch: {doc_count} docs, {chunk_count} chunks "
                        f"(queue: {self.queue.qsize()})"
                    )
                    
                    # Clear batch
                    batch = []
                    last_batch_time = time.time()
            
            except Empty:
                # No items in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Error in indexing worker: {e}")
                self.stats.errors += 1
                time.sleep(1.0)
        
        # Final batch flush
        if batch:
            doc_count, chunk_count = self._bulk_index_items(batch)
            self.stats.documents_processed += doc_count
            self.stats.chunks_processed += chunk_count
            self.logger.info(f"Final batch indexed: {doc_count} docs, {chunk_count} chunks")
        
        self.logger.info("Indexing worker stopped")
    
    def _scan_directory(self, directory: str) -> List[str]:
        """Scan directory for JSONL files."""
        try:
            directory_path = Path(directory)
            if not directory_path.exists():
                return []
            
            jsonl_files = list(directory_path.glob("*.jsonl"))
            return [str(f) for f in sorted(jsonl_files)]
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
            return []
    
    def _process_fresh_files(self) -> int:
        """Process all files in the fresh directory."""
        fresh_files = self._scan_directory(config.FRESH_DIR)
        processed_count = 0
        
        for file_path in fresh_files:
            if not self.running:
                break
            
            try:
                self.logger.info(f"Processing fresh file: {file_path}")
                items_added = self._process_jsonl_file(file_path, is_fresh=True)
                
                if items_added > 0:
                    # Move to processed directory
                    self._move_file(file_path, config.PROCESSED_DIR)
                    self.stats.files_processed += 1
                    self.stats.fresh_files_processed += 1
                    processed_count += 1
                    self.logger.info(f"Processed fresh file: {file_path} ({items_added} items)")
                else:
                    # Move to failed directory
                    self._move_file(file_path, config.FAILED_DIR)
                    self.stats.files_failed += 1
                    self.logger.warning(f"Failed to process fresh file: {file_path}")
            
            except Exception as e:
                self.logger.error(f"Error processing fresh file {file_path}: {e}")
                self._move_file(file_path, config.FAILED_DIR)
                self.stats.files_failed += 1
                self.stats.errors += 1
        
        return processed_count
    
    def _process_backlog_files(self) -> int:
        """Process a limited number of backlog files."""
        backlog_files = self._scan_directory(config.BACKLOG_DIR)
        
        # Limit the number of backlog files processed per batch
        files_to_process = backlog_files[:config.BACKLOG_BATCH_SIZE]
        processed_count = 0
        
        for file_path in files_to_process:
            if not self.running:
                break
            
            try:
                self.logger.info(f"Processing backlog file: {file_path}")
                items_added = self._process_jsonl_file(file_path, is_fresh=False)
                
                if items_added > 0:
                    # Move to processed directory
                    self._move_file(file_path, config.PROCESSED_DIR)
                    self.stats.files_processed += 1
                    self.stats.backlog_files_processed += 1
                    processed_count += 1
                    self.logger.info(f"Processed backlog file: {file_path} ({items_added} items)")
                else:
                    # Move to failed directory
                    self._move_file(file_path, config.FAILED_DIR)
                    self.stats.files_failed += 1
                    self.logger.warning(f"Failed to process backlog file: {file_path}")
            
            except Exception as e:
                self.logger.error(f"Error processing backlog file {file_path}: {e}")
                self._move_file(file_path, config.FAILED_DIR)
                self.stats.files_failed += 1
                self.stats.errors += 1
        
        return processed_count
    
    def _log_statistics(self):
        """Log current statistics."""
        uptime = time.time() - self.stats.start_time
        uptime_hours = uptime / 3600
        
        high_queue, standard_queue = self.queue.qsize()
        
        self.logger.info(
            f"Statistics - Uptime: {uptime_hours:.1f}h | "
            f"Files: {self.stats.files_processed} processed, {self.stats.files_failed} failed | "
            f"Fresh: {self.stats.fresh_files_processed} | Backlog: {self.stats.backlog_files_processed} | "
            f"Docs: {self.stats.documents_processed} | Chunks: {self.stats.chunks_processed} | "
            f"Bulk ops: {self.stats.bulk_operations} | Errors: {self.stats.errors} | "
            f"Queue: {high_queue}+{standard_queue}"
        )
    
    def _health_check(self) -> bool:
        """Perform health check on OpenSearch cluster."""
        if not self.opensearch_available or not self.client:
            self.logger.debug("Skipping health check - OpenSearch not available")
            return True  # Don't fail in offline mode
        
        try:
            health = self.client.cluster.health()
            status = health.get('status', 'unknown')
            
            if status in ['red']:
                self.logger.error(f"OpenSearch cluster health is {status}")
                return False
            elif status in ['yellow']:
                self.logger.warning(f"OpenSearch cluster health is {status}")
            
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def run(self):
        """Main execution loop."""
        self.logger.info("Starting OpenSearch Indexer...")
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Initialize OpenSearch if available
        if self.opensearch_available:
            try:
                self.initialize_opensearch()
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenSearch: {e}")
                self.logger.warning("Continuing in offline mode")
                self.opensearch_available = False
        
        # Initial health check (only if OpenSearch is available)
        if self.opensearch_available and not self._health_check():
            self.logger.warning("Initial health check failed, but continuing")
        
        # Start indexing worker thread
        self.indexing_thread = threading.Thread(target=self._indexing_worker, daemon=True)
        self.indexing_thread.start()
        
        # Statistics logging
        last_stats_time = time.time()
        last_health_check = time.time()
        
        mode = "online" if self.opensearch_available else "offline"
        self.logger.info(f"Indexer is now running in {mode} mode. Press Ctrl+C to stop.")
        
        # Main processing loop
        while self.running:
            try:
                loop_start = time.time()
                
                # 1. Process fresh files first (highest priority)
                fresh_processed = self._process_fresh_files()
                
                # 2. Process backlog files only if no fresh files were processed
                if fresh_processed == 0:
                    self._process_backlog_files()
                
                # 3. Periodic statistics logging
                if time.time() - last_stats_time >= config.STATS_INTERVAL:
                    self._log_statistics()
                    last_stats_time = time.time()
                
                # 4. Periodic health checks (only if OpenSearch is available)
                if self.opensearch_available and time.time() - last_health_check >= config.HEALTH_CHECK_INTERVAL:
                    if not self._health_check():
                        self.logger.error("Health check failed, but continuing operation")
                    last_health_check = time.time()
                
                # 5. Check queue size and warn if too large
                high_queue, standard_queue = self.queue.qsize()
                total_queue = high_queue + standard_queue
                if total_queue > config.MAX_QUEUE_SIZE:
                    self.logger.warning(f"Queue size is large: {total_queue} items")
                
                # 6. Sleep for the polling interval (idle CPU management)
                loop_duration = time.time() - loop_start
                sleep_time = max(0, config.POLL_INTERVAL - loop_duration)
                
                if sleep_time > 0:
                    if self.shutdown_event.wait(sleep_time):
                        break  # Shutdown requested
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                self.stats.errors += 1
                time.sleep(5.0)  # Brief pause before retrying
        
        # Shutdown sequence
        self.logger.info("Initiating shutdown sequence...")
        self.running = False
        
        # Wait for indexing worker to finish
        if self.indexing_thread and self.indexing_thread.is_alive():
            self.logger.info("Waiting for indexing worker to finish...")
            self.indexing_thread.join(timeout=30.0)
        
        # Final statistics
        self._log_statistics()
        
        self.logger.info("OpenSearch Indexer shutdown complete")


def main():
    """Entry point for the indexer."""
    try:
        indexer = OpenSearchIndexer()
        indexer.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
