"""
Backend Utils - Helper functions and utilities
"""

import re
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger


class ResponseFormatter:
    """Format API responses consistently"""
    
    @staticmethod
    def success_response(data: Any, message: str = "Success") -> Dict:
        """Format successful response"""
        return {
            'status': 'success',
            'message': message,
            'data': data
        }
    
    @staticmethod
    def error_response(error: str, code: str = "ERROR", details: Dict = None) -> Dict:
        """Format error response"""
        response = {
            'status': 'error',
            'message': error,
            'error_code': code
        }
        
        if details:
            response['details'] = details
        
        return response


class QueryProcessor:
    """Process and validate search queries"""
    
    @staticmethod
    def clean_query(query: str) -> str:
        """Clean and normalize search query"""
        if not query:
            return ""
        
        # Remove excessive whitespace
        query = ' '.join(query.split())
        
        # Remove special characters but keep basic punctuation
        query = re.sub(r'[^\w\s\-\.\?\!]', '', query)
        
        return query.strip()
    
    @staticmethod
    def validate_query(query: str) -> tuple[bool, str]:
        """Validate search query"""
        if not query:
            return False, "Query cannot be empty"
        
        if len(query) > 500:
            return False, "Query too long (maximum 500 characters)"
        
        # Check for only special characters
        if not re.search(r'[a-zA-Z0-9]', query):
            return False, "Query must contain at least one alphanumeric character"
        
        return True, ""


class ResultProcessor:
    """Process search results for better presentation"""
    
    @staticmethod
    def highlight_terms(text: str, terms: List[str], max_length: int = 300) -> str:
        """Highlight search terms in text"""
        if not text or not terms:
            return text[:max_length]
        
        # Find first occurrence of any term
        text_lower = text.lower()
        first_pos = len(text)
        
        for term in terms:
            pos = text_lower.find(term.lower())
            if pos != -1:
                first_pos = min(first_pos, pos)
        
        # Extract around the first term
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
        """Extract domain from URL"""
        if not url:
            return ""
        
        # Remove protocol
        if url.startswith(('http://', 'https://')):
            url = url.split('://', 1)[1]
        
        # Remove path
        domain = url.split('/')[0]
        
        # Remove www
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain


class PerformanceTracker:
    """Track API performance metrics"""
    
    def __init__(self):
        self.logger = Logger.setup_logger("backend.performance")
        self.metrics = {
            'total_requests': 0,
            'search_requests': 0,
            'avg_response_time': 0,
            'error_count': 0
        }
    
    def track_request(self, endpoint: str, response_time: float, error: bool = False):
        """Track request metrics"""
        self.metrics['total_requests'] += 1
        
        if endpoint.startswith('/api/search'):
            self.metrics['search_requests'] += 1
        
        if error:
            self.metrics['error_count'] += 1
        
        # Update average response time
        current_avg = self.metrics['avg_response_time']
        total_requests = self.metrics['total_requests']
        
        self.metrics['avg_response_time'] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.metrics.copy()


# Global performance tracker
performance_tracker = PerformanceTracker()
