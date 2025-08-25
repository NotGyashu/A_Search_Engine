"""
Standalone Indexer Configuration
Configuration settings for the standalone OpenSearch indexer.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenSearch Connection Settings
OPENSEARCH_HOST = os.getenv('OPENSEARCH_HOST', 'https://localhost:9200')
OPENSEARCH_USER = os.getenv('OPENSEARCH_USER', 'admin')
OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', 'admin')
OPENSEARCH_VERIFY_CERTS = os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true'
OPENSEARCH_TIMEOUT = int(os.getenv('OPENSEARCH_TIMEOUT', '120'))

# Auto-detect AWS OpenSearch based on host URL
def _is_aws_opensearch():
    host = OPENSEARCH_HOST
    return '.es.amazonaws.com' in host or '.aoss.amazonaws.com' in host

# Allow override for testing
FORCE_BASIC_AUTH = os.getenv('FORCE_BASIC_AUTH', 'false').lower() == 'true'

if FORCE_BASIC_AUTH:
    OPENSEARCH_AUTH_TYPE = 'basic'
else:
    OPENSEARCH_AUTH_TYPE = 'aws' if _is_aws_opensearch() else os.getenv('OPENSEARCH_AUTH_TYPE', 'basic')

# AWS Settings (automatically used for AWS OpenSearch)
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', os.getenv('AWS_REGION', 'us-east-1'))
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Directories
TO_INDEX_DIR = "/home/gyashu/projects/A_Search_Engine/toIndex"
FRESH_DIR = "/home/gyashu/projects/A_Search_Engine/toIndex/fresh"
BACKLOG_DIR = "/home/gyashu/projects/A_Search_Engine/toIndex/backlog"
PROCESSED_DIR = "/home/gyashu/projects/A_Search_Engine/toIndex/processed"
FAILED_DIR = "/home/gyashu/projects/A_Search_Engine/toIndex/failed"
LOG_FILE = "/home/gyashu/projects/A_Search_Engine/indexer/indexer.log"

# Indexing Settings
POLL_INTERVAL = 5.0  # seconds between checking for new files
BULK_CHUNK_SIZE = 500  # documents per bulk operation (reduced for free tier)
MAX_RETRIES = 5  # retry attempts for failed operations
MAX_WORKERS = 1  # CRITICAL: Set to 1 to avoid rate-limiting on free tier

# Queue Settings
HIGH_PRIORITY_QUEUE_SIZE = 2000  # High priority queue max size
STANDARD_PRIORITY_QUEUE_SIZE = 1000  # Standard priority queue max size
BACKLOG_BATCH_SIZE = 5  # Number of backlog files to process per batch

# Index Settings
DOCUMENTS_INDEX_BASE = "search_documents"
CHUNKS_INDEX_BASE = "search_chunks"
NUMBER_OF_SHARDS = 1
NUMBER_OF_REPLICAS = 0

# Performance Settings
REFRESH_INTERVAL = "30s"  # how often to refresh indices
TRANSLOG_DURABILITY = "async"  # async for better performance

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
STATS_INTERVAL = 60  # seconds between stats logging

# File Processing Settings
MOVE_PROCESSED_FILES = True
KEEP_FAILED_FILES = True

# Health Check Settings
HEALTH_CHECK_INTERVAL = 300  # seconds between health checks
MAX_QUEUE_SIZE = 1000  # alert if more than this many files in queue
