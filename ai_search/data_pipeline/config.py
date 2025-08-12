"""
Configuration settings for the modular data pipeline.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class PipelineConfig:
    """Configuration class for the data pipeline."""
    
    # OpenSearch settings
    OPENSEARCH_HOST = os.getenv('OPENSEARCH_HOST', 'localhost:9200')
    OPENSEARCH_USE_SSL = os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true'
    OPENSEARCH_VERIFY_CERTS = os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true'
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # Index names
    DOCUMENTS_INDEX = os.getenv('DOCUMENTS_INDEX', 'documents')
    CHUNKS_INDEX = os.getenv('CHUNKS_INDEX', 'chunks')
    
    # Processing settings
    BATCH_SIZE = int(os.getenv('PIPELINE_BATCH_SIZE', '100'))
    MAX_WORKERS = int(os.getenv('PIPELINE_MAX_WORKERS', '4'))
    CHUNK_SIZE = int(os.getenv('CONTENT_CHUNK_SIZE', '1000'))
    CHUNK_OVERLAP = int(os.getenv('CONTENT_CHUNK_OVERLAP', '100'))
    
    # Content filtering
    MIN_CONTENT_LENGTH = int(os.getenv('MIN_CONTENT_LENGTH', '100'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '1000000'))
    MIN_QUALITY_SCORE = float(os.getenv('MIN_QUALITY_SCORE', '0.3'))
    
    # File processing
    SUPPORTED_FORMATS = ['json', 'jsonl']
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Domain scoring configuration
    DOMAIN_SCORES = {
        # High authority domains
        'wikipedia.org': 0.9,
        'github.com': 0.85,
        'stackoverflow.com': 0.8,
        'arxiv.org': 0.85,
        'nature.com': 0.9,
        'science.org': 0.9,
        'pubmed.ncbi.nlm.nih.gov': 0.85,
        
        # Educational domains
        '.edu': 0.8,
        '.ac.uk': 0.8,
        
        # Government domains
        '.gov': 0.75,
        '.mil': 0.7,
        
        # News domains
        'reuters.com': 0.8,
        'bbc.com': 0.8,
        'cnn.com': 0.7,
        'npr.org': 0.75,
        
        # Tech domains
        'techcrunch.com': 0.7,
        'arstechnica.com': 0.75,
        'wired.com': 0.7,
        
        # Default scores by TLD
        '.org': 0.6,
        '.com': 0.5,
        '.net': 0.45,
        '.info': 0.4,
        '.biz': 0.35
    }
    
    # Content categories keywords
    CATEGORY_KEYWORDS = {
        'technology': [
            'software', 'hardware', 'computer', 'programming', 'algorithm',
            'artificial intelligence', 'machine learning', 'ai', 'ml',
            'python', 'javascript', 'java', 'react', 'node', 'database',
            'api', 'cloud', 'aws', 'docker', 'kubernetes'
        ],
        'science': [
            'research', 'study', 'experiment', 'hypothesis', 'theory',
            'physics', 'chemistry', 'biology', 'mathematics', 'scientific',
            'discovery', 'analysis', 'data', 'statistics'
        ],
        'business': [
            'company', 'startup', 'investment', 'funding', 'revenue',
            'market', 'economy', 'finance', 'management', 'strategy',
            'entrepreneur', 'business', 'corporate'
        ],
        'education': [
            'learning', 'course', 'tutorial', 'guide', 'education',
            'training', 'skill', 'knowledge', 'teach', 'student',
            'university', 'college', 'school'
        ],
        'news': [
            'breaking', 'update', 'report', 'announcement', 'news',
            'today', 'yesterday', 'latest', 'current', 'recent'
        ],
        'documentation': [
            'documentation', 'docs', 'manual', 'guide', 'reference',
            'api docs', 'readme', 'wiki', 'how-to', 'instructions'
        ]
    }
    
    # Text cleaning patterns
    CLEANING_PATTERNS = {
        'social_media': [
            r'follow us on \w+',
            r'like and subscribe',
            r'@\w+',
            r'#\w+',
            r'tweet this',
            r'share on facebook'
        ],
        'navigation': [
            r'home\s*>\s*',
            r'breadcrumb',
            r'navigation',
            r'skip to content',
            r'menu',
            r'sidebar'
        ],
        'boilerplate': [
            r'copyright \d{4}',
            r'all rights reserved',
            r'privacy policy',
            r'terms of service',
            r'cookie policy',
            r'powered by \w+',
            r'designed by \w+'
        ]
    }
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.OPENSEARCH_HOST:
            raise ValueError("OPENSEARCH_HOST is required")
        
        if cls.BATCH_SIZE <= 0:
            raise ValueError("BATCH_SIZE must be positive")
        
        if cls.MAX_WORKERS <= 0:
            raise ValueError("MAX_WORKERS must be positive")
        
        if cls.CHUNK_SIZE <= 0:
            raise ValueError("CHUNK_SIZE must be positive")
        
        return True
