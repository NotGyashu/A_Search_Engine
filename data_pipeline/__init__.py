"""
AI Search Data Pipeline - Modular Document Processing System

This package provides a comprehensive, modular system for processing raw HTML data
and preparing it for indexing. The indexing functionality has been moved to a 
standalone indexer for better architectural separation.

Components:
- extractor: Raw HTML parsing and content extraction
- cleaner: Text cleaning, metadata extraction, and chunking
- scorer: Domain and content quality scoring
- processor: Main processing orchestrator
- file_reader: File handling and data ingestion
- run_pipeline: Main execution script

Note: Indexing functionality is now handled by the standalone indexer in the 
indexer/ folder, which reads from the toIndex/ queue folder.
"""

__version__ = "2.0.0"
__author__ = "AI Search Team"

from .extractor import ContentExtractor
from .cleaner import ContentCleaner
from .processor import DocumentProcessor
from .file_reader import FileReader

__all__ = [
    "ContentExtractor",
    "ContentCleaner",
    "DocumentProcessor",
    "FileReader"
]
