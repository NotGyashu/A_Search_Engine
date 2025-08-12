"""
AI Search Engine - Backend Utilities
Merged for .env + Elasticsearch architecture
"""

import os
import sys
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend root to Python path
BACKEND_ROOT = Path(__file__).parent
sys.path.insert(0, str(BACKEND_ROOT))

# =========================
# Logging
# =========================
class Logger:
    """Centralized logging utility"""

    @staticmethod
    def setup_logger(name: str) -> logging.Logger:
        log_level = os.getenv("BACKEND_LOG_LEVEL", "INFO")
        log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        logger = logging.getLogger(name)
        if logger.hasHandlers():
            return logger

        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        formatter = logging.Formatter(log_format)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        try:
            log_dir = BACKEND_ROOT / "logs"
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_dir / "backend.log")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")

        return logger

# =========================
# Config Manager
# =========================
class ConfigManager:
    """Configuration management using .env"""

    @staticmethod
    def get_ai_config() -> Dict[str, Any]:
        return {
            "AI_MODEL_PREFERENCE": os.getenv("AI_MODEL_PREFERENCE", "google_gemini,smart_template").split(","),
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            "OPENAI_MAX_TOKENS": int(os.getenv("OPENAI_MAX_TOKENS", "150")),
            "OPENAI_TEMPERATURE": float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
        }

# =========================
# Performance Monitor
# =========================
class PerformanceMonitor:
    """Measure operation time"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = Logger.setup_logger(f"performance.{operation_name}")

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        self.logger.info(f"Completed: {self.operation_name} in {duration:.2f}ms")

# =========================
# API Responses
# =========================
class ResponseFormatter:
    """Standard API response formatting"""

    @staticmethod
    def success(data: Any, message: str = "Success", meta: Optional[Dict] = None) -> Dict:
        resp = {"status": "success", "message": message, "data": data, "timestamp": time.time()}
        if meta:
            resp["meta"] = meta
        return resp

    @staticmethod
    def error(message: str, code: str = "GENERIC_ERROR", details: Any = None) -> Dict:
        resp = {"status": "error", "message": message, "error_code": code, "timestamp": time.time()}
        if details:
            resp["details"] = details
        return resp

# =========================
# Query Processing
# =========================
class QueryProcessor:
    """Clean and validate search queries"""

    @staticmethod
    def clean_query(query: str) -> str:
        if not query:
            return ""
        query = " ".join(query.split())
        query = re.sub(r"[^\w\s\-\.\?\!]", "", query)
        return query.strip()

    @staticmethod
    def validate_query(query: str) -> tuple[bool, str]:
        if not query:
            return False, "Query cannot be empty"
        if len(query) > 500:
            return False, "Query too long (max 500 chars)"
        if not re.search(r"[a-zA-Z0-9]", query):
            return False, "Query must contain at least one alphanumeric character"
        return True, ""

# =========================
# Result Processing
# =========================
class ResultProcessor:
    """Process search results for display"""

    @staticmethod
    def highlight_terms(text: str, terms: List[str], max_length: int = 300) -> str:
        if not text or not terms:
            return text[:max_length]

        text_lower = text.lower()
        first_pos = len(text)

        for term in terms:
            pos = text_lower.find(term.lower())
            if pos != -1:
                first_pos = min(first_pos, pos)

        if first_pos < len(text):
            start = max(0, first_pos - 100)
            end = min(len(text), start + max_length)
            excerpt = text[start:end]
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(text):
                excerpt = excerpt + "..."
            return excerpt

        return text[:max_length]

    @staticmethod
    def extract_domain(url: str) -> str:
        if not url:
            return ""
        if url.startswith(("http://", "https://")):
            url = url.split("://", 1)[1]
        domain = url.split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

# =========================
# Text Processing
# =========================
class TextProcessor:
    """General text utilities"""

    @staticmethod
    def tokenize(text: str) -> List[str]:
        if not text:
            return []
        min_length = int(os.getenv("BM25_MIN_TERM_LENGTH", "3"))
        text = text.lower()
        tokens = re.findall(r"\b[a-z0-9]+\b", text)
        return [t for t in tokens if len(t) >= min_length]

    @staticmethod
    def clean_content(content: str) -> str:
        if not content:
            return ""
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r"&[a-zA-Z0-9#]+;", " ", content)
        return content.strip()

    @staticmethod
    def extract_preview(content: str) -> str:
        length = int(os.getenv("CONTENT_PREVIEW_LENGTH", "300"))
        if not content:
            return ""
        cleaned = TextProcessor.clean_content(content)
        return (cleaned[:length] + "...") if len(cleaned) > length else cleaned

# =========================
# Health Checker
# =========================
class HealthChecker:
    """Check health of external services"""

    @staticmethod
    def check_elasticsearch() -> Dict[str, Any]:
        try:
            from elasticsearch import Elasticsearch
            es_url = os.getenv("ELASTICSEARCH_URL")
            if not es_url:
                return {"status": "unhealthy", "error": "ELASTICSEARCH_URL not set."}

            es_client = Elasticsearch([es_url], request_timeout=5)
            if es_client.ping():
                info = es_client.info()
                return {"status": "healthy", "version": info.get("version", {}).get("number")}
            return {"status": "unhealthy", "error": "Failed to ping Elasticsearch."}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    def check_ai_runner() -> Dict[str, Any]:
        try:
            import requests
            ai_runner_url = os.getenv("AI_RUNNER_URL")
            if not ai_runner_url:
                return {"status": "unhealthy", "error": "AI_RUNNER_URL not set."}

            response = requests.get(f"{ai_runner_url}/health", timeout=5)
            return {"status": "healthy", "details": response.json()} if response.ok else {
                "status": "unhealthy",
                "error": f"AI Runner returned status {response.status_code}"
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    def system_health() -> Dict[str, Any]:
        return {
            "elasticsearch": HealthChecker.check_elasticsearch(),
            "ai_runner": HealthChecker.check_ai_runner()
        }

# =========================
# Performance Tracker
# =========================
class PerformanceTracker:
    """Track backend performance metrics"""

    def __init__(self):
        self.logger = Logger.setup_logger("backend.performance")
        self.metrics = {
            'total_requests': 0,
            'search_requests': 0,
            'avg_response_time': 0,
            'error_count': 0
        }

    def track_request(self, endpoint: str, response_time: float, error: bool = False):
        self.metrics['total_requests'] += 1
        if endpoint.startswith('/api/search'):
            self.metrics['search_requests'] += 1
        if error:
            self.metrics['error_count'] += 1

        current_avg = self.metrics['avg_response_time']
        total_requests = self.metrics['total_requests']
        self.metrics['avg_response_time'] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )

    def get_metrics(self) -> Dict:
        return self.metrics.copy()


# Global performance tracker instance
performance_tracker = PerformanceTracker()
