# core/enhanced_search_service.py
import time
import logging
import hashlib
from typing import Dict, List, Optional

from .opensearch_service import OpenSearchService

class EnhancedSearchService:
    """
    The primary search service for the application.
    Orchestrates search calls to the OpenSearchService and formats results.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.es_service = self._initialize_es_service()

    def _initialize_es_service(self) -> Optional[OpenSearchService]:
        """Safely initializes the OpenSearchService."""
        try:
            service = OpenSearchService()
            self.logger.info("Connection to OpenSearch successful.")
            return service
        except ConnectionError as e:
            self.logger.critical(f"Search will be unavailable. Could not connect to OpenSearch. Error: {e}")
            return None

    def search(self, query: str, limit: int = 10) -> Dict:
        """Enhanced search with improved content processing and domain diversity."""
        start_time = time.time()
        self.current_query = query  # Store for smart preview generation
        
        cache_key = self._generate_cache_key(query, limit)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        if not self.es_service:
            return self._build_error_response(query, "Search service is currently unavailable.", 0)

        try:
            # Use enhanced OpenSearch with domain diversity
            es_results = self.es_service.search(query, limit)
            
            if not es_results:
                # Try fallback search
                es_results = self.es_service.fallback_search(query, limit)

        except Exception as e:
            self.logger.error(f"Search failed for '{query}': {e}")
            search_time_ms = round((time.time() - start_time) * 1000, 2)
            return self._build_error_response(query, str(e), search_time_ms)

        # Format the final results for the API with enhanced previews
        formatted_results = self._format_es_results(es_results)
        
        search_time_ms = round((time.time() - start_time) * 1000, 2)
        final_result = {
            'query': query,
            'results': formatted_results,
            'total_found': len(formatted_results),
            'search_time_ms': search_time_ms,
            'search_method': 'Enhanced OpenSearch (Modular Pipeline)',
            'error': None,
            'from_cache': False,
            'domain_diversity_applied': True
        }

        self._store_in_cache(cache_key, final_result)
        return final_result
        
    def _format_es_results(self, es_hits: List[Dict]) -> List[Dict]:
        """Formats raw Elasticsearch hits into the application's standard structure."""
        formatted = []
        for hit in es_hits:
            source = hit.get('_source', {})
            
            # Create intelligent content preview
            content_preview = self._create_smart_preview(
                source.get('text_chunk', ''), 
                self.current_query if hasattr(self, 'current_query') else ''
            )
            
            formatted.append({
                'id': hit.get('_id'),
                'url': source.get('url'),
                'title': source.get('title'),
                'content_preview': content_preview,
                'domain': source.get('domain'),
                'relevance_score': hit.get('_score'),
                'domain_score': source.get('domain_score'),
                'quality_score': source.get('quality_score'),
                'content_categories': source.get('content_categories', []),
                'keywords': source.get('keywords', [])
            })
        return formatted
    
    def _create_smart_preview(self, content: str, query: str, max_length: int = 300) -> str:
        """Create an intelligent content preview highlighting query relevance."""
        if not content:
            return ""
        
        if not query:
            return content[:max_length] + ("..." if len(content) > max_length else "")
        
        # Find query-relevant excerpts
        query_terms = query.lower().split()
        sentences = content.split('.')
        
        # Score sentences by query relevance
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:
                continue
            
            sentence_lower = sentence.lower()
            score = sum(1 for term in query_terms if term in sentence_lower)
            
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        # Use best sentence or fallback to beginning
        if best_sentence and len(best_sentence) <= max_length:
            return best_sentence + "."
        elif best_sentence:
            # Truncate at word boundary
            words = best_sentence.split()
            truncated = []
            length = 0
            
            for word in words:
                if length + len(word) + 1 > max_length - 3:
                    break
                truncated.append(word)
                length += len(word) + 1
            
            return " ".join(truncated) + "..."
        
        # Fallback to beginning of content
        return content[:max_length] + ("..." if len(content) > max_length else "")

    def _build_error_response(self, query: str, error_message: str, search_time_ms: float) -> Dict:
        """Helper to build a standardized error response."""
        return {
            'query': query, 'results': [], 'total_found': 0, 
            'search_time_ms': search_time_ms, 'search_method': 'OpenSearch Two-Index',
            'error': error_message
        }

    def health_check(self) -> Dict:
        """Checks the health of the underlying Elasticsearch service."""
        if not self.es_service:
            return {"status": "unhealthy", "reason": "Elasticsearch client not initialized."}
        return self.es_service.health_check()

    def _generate_cache_key(self, query: str, limit: int) -> str:
        """Generate a cache key for the search query."""
        return f"search:{query.lower().strip()}:{limit}"

    def _get_from_cache(self, cache_key: str) -> Dict:
        """Get cached search results if available."""
        # Simple in-memory cache (can be replaced with Redis)
        if not hasattr(self, '_cache'):
            self._cache = {}
        
        return self._cache.get(cache_key)

    def _store_in_cache(self, cache_key: str, result: Dict):
        """Store search results in cache."""
        if not hasattr(self, '_cache'):
            self._cache = {}
        
        # Simple cache with max 1000 entries
        if len(self._cache) >= 1000:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        result_copy = result.copy()
        result_copy['from_cache'] = True
        self._cache[cache_key] = result_copy