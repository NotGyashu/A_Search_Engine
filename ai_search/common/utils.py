"""
AI Search Engine - Common Utilities
Shared utilities and helper functions across all components
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

# Add the ai_search directory to Python path for imports
AI_SEARCH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(AI_SEARCH_ROOT))

from common.config import *

class Logger:
    """Centralized logging utility"""
    
    @staticmethod
    def setup_logger(name: str, level: str = LOG_LEVEL) -> logging.Logger:
        """Setup logger with consistent formatting"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level))
        
        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (create logs directory if needed)
        log_dir = AI_SEARCH_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "ai_search.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

class PathManager:
    """Centralized path management"""
    
    @staticmethod
    def get_ai_search_root() -> Path:
        """Get the ai_search root directory"""
        return AI_SEARCH_ROOT
    
    @staticmethod
    def get_database_path() -> Path:
        """Get the processed database path"""
        return AI_SEARCH_ROOT / DATABASE_PATH
    
    @staticmethod
    def get_raw_data_path() -> Path:
        """Get the raw HTML data path"""
        return AI_SEARCH_ROOT / RAW_DATA_PATH
    
    @staticmethod
    def get_backend_path() -> Path:
        """Get the backend directory path"""
        return AI_SEARCH_ROOT / "backend"
    
    @staticmethod
    def get_frontend_path() -> Path:
        """Get the frontend directory path"""
        return AI_SEARCH_ROOT / "frontend"
    
    @staticmethod
    def get_data_pipeline_path() -> Path:
        """Get the data pipeline directory path"""
        return AI_SEARCH_ROOT / "data_pipeline"
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists"""
        path.mkdir(parents=True, exist_ok=True)

class ConfigManager:
    """Configuration management utility"""
    
    @staticmethod
    def get_config(section: str = None) -> Dict[str, Any]:
        """Get configuration values"""
        config = {}
        
        # Import all config variables
        import common.config as cfg
        
        for attr_name in dir(cfg):
            if not attr_name.startswith('_'):
                attr_value = getattr(cfg, attr_name)
                if not callable(attr_value):
                    config[attr_name] = attr_value
        
        if section:
            # Filter by section prefix
            section_config = {}
            prefix = section.upper() + "_"
            for key, value in config.items():
                if key.startswith(prefix):
                    section_key = key[len(prefix):]
                    section_config[section_key] = value
            return section_config
        
        return config
    
    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """Get database configuration"""
        return ConfigManager.get_config("DATABASE")
    
    @staticmethod
    def get_search_config() -> Dict[str, Any]:
        """Get search engine configuration"""
        return {
            "BM25_K1": BM25_K1,
            "BM25_B": BM25_B,
            "BM25_MIN_TERM_LENGTH": BM25_MIN_TERM_LENGTH,
            "DEFAULT_SEARCH_LIMIT": DEFAULT_SEARCH_LIMIT,
            "MAX_SEARCH_LIMIT": MAX_SEARCH_LIMIT,
            "CONTENT_PREVIEW_LENGTH": CONTENT_PREVIEW_LENGTH,
            "TITLE_WEIGHT_MULTIPLIER": TITLE_WEIGHT_MULTIPLIER
        }
    
    @staticmethod
    def get_ai_config() -> Dict[str, Any]:
        """Get AI configuration"""
        return {
            "AI_MODEL_PREFERENCE": AI_MODEL_PREFERENCE,
            "OPENAI_MODEL": OPENAI_MODEL,
            "OPENAI_MAX_TOKENS": OPENAI_MAX_TOKENS,
            "OPENAI_TEMPERATURE": OPENAI_TEMPERATURE,
            "LOCAL_SUMMARIZATION_MODEL": LOCAL_SUMMARIZATION_MODEL,
            "OLLAMA_MODEL": OLLAMA_MODEL,
            "TOPIC_KEYWORDS": TOPIC_KEYWORDS
        }

class PerformanceMonitor:
    """Performance monitoring utility"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = Logger.setup_logger(f"performance.{operation_name}")
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.logger.info(f"Completed {self.operation_name} in {duration:.3f}s")
    
    def checkpoint(self, message: str):
        """Log a checkpoint during the operation"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.logger.info(f"{self.operation_name} - {message} ({elapsed:.3f}s elapsed)")

class APIResponse:
    """Standardized API response utility"""
    
    @staticmethod
    def success(data: Any, message: str = "Success", meta: Dict = None) -> Dict:
        """Create a success response"""
        response = {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": time.time()
        }
        if meta:
            response["meta"] = meta
        return response
    
    @staticmethod
    def error(message: str, code: str = "GENERIC_ERROR", details: Any = None) -> Dict:
        """Create an error response"""
        response = {
            "status": "error",
            "message": message,
            "error_code": code,
            "timestamp": time.time()
        }
        if details:
            response["details"] = details
        return response
    
    @staticmethod
    def search_response(query: str, results: List, total_found: int, 
                       search_time_ms: float, ai_summary: str = "", 
                       method: str = "BM25") -> Dict:
        """Create a standardized search response"""
        return {
            "query": query,
            "ai_summary": ai_summary,
            "results": results,
            "total_found": total_found,
            "search_time_ms": search_time_ms,
            "search_method": method,
            "timestamp": time.time()
        }

class TextProcessor:
    """Common text processing utilities"""
    
    @staticmethod
    def tokenize(text: str, min_length: int = BM25_MIN_TERM_LENGTH) -> List[str]:
        """Tokenize text for search indexing"""
        if not text:
            return []
        
        import re
        # Convert to lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b[a-z0-9]+\b', text)
        return [token for token in tokens if len(token) >= min_length]
    
    @staticmethod
    def clean_content(content: str) -> str:
        """Clean and normalize content"""
        if not content:
            return ""
        
        import re
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove HTML entities
        content = re.sub(r'&[a-zA-Z0-9#]+;', ' ', content)
        # Remove special characters except basic punctuation
        content = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)]', ' ', content)
        
        return content.strip()
    
    @staticmethod
    def extract_preview(content: str, length: int = CONTENT_PREVIEW_LENGTH) -> str:
        """Extract content preview"""
        if not content:
            return ""
        
        cleaned = TextProcessor.clean_content(content)
        if len(cleaned) <= length:
            return cleaned
        
        # Try to break at sentence boundary
        preview = cleaned[:length]
        last_period = preview.rfind('.')
        if last_period > length * 0.7:  # If period is reasonably close to end
            return preview[:last_period + 1]
        
        return preview + "..."

class HealthChecker:
    """System health checking utility"""
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity and status"""
        try:
            import sqlite3
            db_path = PathManager.get_database_path()
            
            if not db_path.exists():
                return {
                    "status": "error",
                    "message": "Database file not found",
                    "path": str(db_path)
                }
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            conn.close()
            
            return {
                "status": "healthy",
                "document_count": doc_count,
                "path": str(db_path),
                "size_mb": round(db_path.stat().st_size / (1024*1024), 2)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    @staticmethod
    def check_ai_models() -> Dict[str, Any]:
        """Check AI model availability"""
        available_models = []
        
        # Check OpenAI
        try:
            import openai
            available_models.append("openai")
        except ImportError:
            pass
        
        # Check Transformers
        try:
            from transformers import pipeline
            available_models.append("transformers")
        except ImportError:
            pass
        
        # Check Ollama
        try:
            import requests
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
            if response.status_code == 200:
                available_models.append("ollama")
        except:
            pass
        
        return {
            "status": "healthy" if available_models else "limited",
            "available_models": available_models,
            "fallback": "smart_template" not in available_models
        }
    
    @staticmethod
    def system_health() -> Dict[str, Any]:
        """Get overall system health"""
        return {
            "database": HealthChecker.check_database(),
            "ai_models": HealthChecker.check_ai_models(),
            "config": {
                "ai_search_root": str(PathManager.get_ai_search_root()),
                "backend_port": BACKEND_PORT,
                "frontend_port": FRONTEND_PORT
            }
        }

# Export commonly used functions
__all__ = [
    'Logger', 'PathManager', 'ConfigManager', 'PerformanceMonitor',
    'APIResponse', 'TextProcessor', 'HealthChecker',
    'AI_SEARCH_ROOT'
]
