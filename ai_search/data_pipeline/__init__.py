"""
AI Search Data Pipeline - Modular Document Processing System

This package provides a comprehensive, modular system for processing raw HTML data
and indexing it to OpenSearch for optimal search performance.

Components:
- extractor: Raw HTML parsing and content extraction
- cleaner: Text cleaning, metadata extraction, and chunking
- scorer: Domain and content quality scoring
- processor: Main processing orchestrator
- indexer: OpenSearch client and bulk indexing
- file_reader: File handling and data ingestion
- run_pipeline: Main execution script
"""

__version__ = "2.0.0"
__author__ = "AI Search Team"

from .extractor import ContentExtractor
from .cleaner import ContentCleaner
from .scorer import ContentScorer
from .processor import DocumentProcessor
from .indexer import OpenSearchIndexer
from .file_reader import FileReader

__all__ = [
    "ContentExtractor",
    "ContentCleaner", 
    "ContentScorer",
    "DocumentProcessor",
    "OpenSearchIndexer",
    "FileReader"
]
