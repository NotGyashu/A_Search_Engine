"""
🚀 Enhanced Search Service with Domain Ranking
Extends the base SearchService with educational domain prioritization
"""

import time
import math
import hashlib
from typing import Dict, List
from collections import defaultdict
import logging

from .search_service import SearchService
from .domain_ranker import DomainRanker
from common.utils import TextProcessor
from common.config import MAX_SEARCH_LIMIT  # already likely imported


logger = logging.getLogger(__name__)

class EnhancedSearchService(SearchService):
    """
    Enhanced BM25 search with domain-based ranking, content type detection, and caching
    """
    
    def __init__(self, db_service):
        super().__init__(db_service)
        self.domain_ranker = DomainRanker()
        self.logger = logging.getLogger(__name__)
        print("Initializing Enhanced Search Service with Domain Ranking...")
        # Enhanced scoring parameters
        self.DOMAIN_BOOST_WEIGHT = 0.3  # 30% weight to domain ranking
        self.CONTENT_BOOST_WEIGHT = 0.2  # 20% weight to content type
        self.BM25_WEIGHT = 0.5  # 50% weight to BM25 score
        self.MAX_SEARCH_LIMIT = MAX_SEARCH_LIMIT
        
        # Search result caching for performance
        self.search_cache = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.max_cache_size = 1000
        
        self.logger.info("Enhanced search service initialized with domain ranking and caching")
    
    def _get_cache_key(self, query: str, limit: int) -> str:
        """Generate cache key for search query"""
        content = f"{query.lower().strip()}:{limit}"
        print(f"Generating cache key for query")
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Dict:
        """Get search results from cache if available and not expired"""
        print(f"Checking cache for key:...")
        if cache_key in self.search_cache:
            cached_item = self.search_cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                self.logger.info(f"Cache hit for search query: {cache_key[:8]}...")
                cached_result = cached_item['result'].copy()
                cached_result['from_cache'] = True
                return cached_result
            else:
                # Remove expired cache entry
                del self.search_cache[cache_key]
        return None
    
    def _store_in_cache(self, cache_key: str, result: Dict):
        """Store search result in cache"""
        print(f"Storing result in cache for key:...")
        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self.search_cache) >= self.max_cache_size:
            oldest_key = min(self.search_cache.keys(), 
                           key=lambda k: self.search_cache[k]['timestamp'])
            del self.search_cache[oldest_key]
        
        # Store result without the from_cache flag
        result_to_cache = result.copy()
        result_to_cache.pop('from_cache', None)
        
        self.search_cache[cache_key] = {
            'result': result_to_cache,
            'timestamp': time.time()
        }
    
    def _calculate_enhanced_bm25_score(self, query_terms: List[str], doc_id: int) -> float:
        """Calculate enhanced BM25 score with domain and content boosts"""
        print(f"Calculating enhanced BM25 score for doc_id with query terms:")
        # Get base BM25 score
        base_score = self._calculate_bm25_score(query_terms, doc_id)
        
        if base_score == 0:
            return 0.0
        
        doc = self.documents[doc_id]
        
        # Calculate domain boost
        domain_boost = self.domain_ranker.calculate_domain_boost(
            doc['url'], 
            doc.get('title', ''),
            doc.get('content', '')[:1000],  # First 1000 chars for performance
            query_terms
        )
        
        # Enhanced scoring formula
        enhanced_score = (
            base_score * self.BM25_WEIGHT +
            base_score * domain_boost * self.DOMAIN_BOOST_WEIGHT +
            base_score * self._calculate_content_quality_boost(doc) * self.CONTENT_BOOST_WEIGHT
        )
        
        return enhanced_score
    
    def _calculate_content_quality_boost(self, doc: Dict) -> float:
        """Calculate content quality boost based on document characteristics"""
        boost = 1.0
        print(f"Calculating content quality boost for document:")
        
        title = doc.get('title', '').lower()
        content = doc.get('content', '')
        word_count = doc.get('word_count', 0)
        
        # Title quality boost
        if len(title) > 10 and len(title) < 100:  # Reasonable title length
            boost *= 1.1
        
        # Content length boost (sweet spot: 500-5000 words)
        if 500 <= word_count <= 5000:
            boost *= 1.2
        elif 100 <= word_count < 500:
            boost *= 1.1
        elif word_count > 5000:
            boost *= 1.05
        
        # Educational content indicators
        educational_indicators = [
            'tutorial', 'guide', 'documentation', 'reference',
            'example', 'explanation', 'definition', 'introduction',
            'overview', 'course', 'lesson', 'learn'
        ]
        
        title_lower = title.lower()
        content_lower = content[:500].lower()
        
        educational_score = 0
        for indicator in educational_indicators:
            if indicator in title_lower:
                educational_score += 2  # Higher weight for title
            if indicator in content_lower:
                educational_score += 1
        
        if educational_score > 0:
            boost *= (1.0 + min(educational_score * 0.05, 0.3))  # Cap at 30% boost
        
        return boost
    
    def search(self, query: str, limit: int = None) -> Dict:
        """Enhanced search with domain ranking, content type detection, and caching"""
        start_time = time.time()
        print(f"Starting enhanced search for query: '' with limit")
        # Validate inputs
        if not query or not query.strip():
            return {
                'query': query,
                'results': [],
                'total_found': 0,
                'search_time_ms': 0,
                'search_method': 'Enhanced BM25',
                'error': 'Empty query',
                'from_cache': False
            }
        
        # Set default limit
        if limit is None:
            limit = self.DEFAULT_SEARCH_LIMIT
        elif limit > self.MAX_SEARCH_LIMIT:
            limit = self.MAX_SEARCH_LIMIT
        
        # Check cache first
        cache_key = self._get_cache_key(query, limit)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Check if index is built
        if not self.documents:
            self.logger.warning("Search index not built, attempting to rebuild...")
            self._build_index()
            
            if not self.documents:
                return {
                    'query': query,
                    'results': [],
                    'total_found': 0,
                    'search_time_ms': 0,
                    'search_method': 'Enhanced BM25',
                    'error': 'No documents in index',
                    'from_cache': False
                }
                    
        
        # Tokenize query
        query_terms = self._tokenize(query.lower())
        
        if not query_terms:
            return {
                'query': query,
                'results': [],
                'total_found': 0,
                'search_time_ms': 0,
                'search_method': 'Enhanced BM25',
                'error': 'No valid search terms'
            }
        
        # Find candidate documents
        candidate_docs = set()
        for term in query_terms:
            if term in self.term_freq:
                candidate_docs.update(self.term_freq[term].keys())
        
        if not candidate_docs:
            # Fallback to simple text search
            self.logger.info("No BM25 matches, falling back to enhanced text search")
            fallback_results = self._enhanced_text_search_fallback(query, limit)
            
            fallback_result = {
                'query': query,
                'results': fallback_results,
                'total_found': len(fallback_results),
                'search_time_ms': round((time.time() - start_time) * 1000, 2),
                'search_method': 'Enhanced Text Search (fallback)',
                'error': None,
                'from_cache': False
            }
            
            # Cache fallback results too
            self._store_in_cache(cache_key, fallback_result)
            
            return fallback_result
        
        # Calculate enhanced BM25 scores
        doc_scores = []
        for doc_id in candidate_docs:
            score = self._calculate_enhanced_bm25_score(query_terms, doc_id)
            if score > 0:
                doc_scores.append((doc_id, score))
        
        # Sort by enhanced relevance
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        doc_scores = doc_scores[:limit]
        
        # Format results with enhanced metadata
        results = []
        for doc_id, score in doc_scores:
            doc = self.documents[doc_id]
            
            # Calculate individual boost components for transparency
            domain_boost = self.domain_ranker.get_domain_score(doc['url'])
            content_boost = self._calculate_content_quality_boost(doc)
            
            results.append({
                'id': doc_id,
                'url': doc['url'],
                'title': doc['title'],
                'content_preview': self._create_preview(doc['content'], query),
                'domain': doc['domain'],
                'word_count': doc['word_count'],
                'relevance_score': round(score, 3),
                'domain_boost': round(domain_boost, 2),
                'content_boost': round(content_boost, 2),
                'is_educational': self.domain_ranker.is_educational_domain(doc['url'])
            })
        
        search_time = round((time.time() - start_time) * 1000, 2)
        
        # Prepare result
        result = {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_time_ms': search_time,
            'search_method': 'Enhanced BM25',
            'error': None,
            'from_cache': False
        }
        
        # Store in cache for future requests
        self._store_in_cache(cache_key, result)
        
        self.logger.info(f"Enhanced search completed: '{query}' -> {len(results)} results in {search_time}ms")
        
        return result
    
    def _enhanced_text_search_fallback(self, query: str, limit: int) -> List[Dict]:
        """Enhanced fallback search with domain ranking"""
        fallback_results = self.db_service.search_documents_by_text(query, limit * 2)  # Get more for ranking
        print(f"Performing enhanced text search fallback for query: '' with limit ")
        # Apply domain ranking to fallback results
        enhanced_results = []
        for doc in fallback_results:
            domain_boost = self.domain_ranker.get_domain_score(doc['url'])
            content_boost = self._calculate_content_quality_boost(doc)
            
            # Calculate fallback score
            fallback_score = 0.1 * domain_boost * content_boost
            
            enhanced_results.append({
                'id': doc['id'],
                'url': doc['url'],
                'title': doc['title'],
                'content_preview': self._create_preview(doc['content'], query),
                'domain': doc['domain'],
                'word_count': doc['word_count'],
                'relevance_score': round(fallback_score, 3),
                'domain_boost': round(domain_boost, 2),
                'content_boost': round(content_boost, 2),
                'is_educational': self.domain_ranker.is_educational_domain(doc['url'])
            })
        
        # Sort by enhanced fallback score
        enhanced_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return enhanced_results[:limit]
    
    def get_search_stats(self) -> Dict:
        """Get enhanced search service statistics"""
        base_stats = super().get_search_stats() if hasattr(super(), 'get_search_stats') else {}
        print("Gathering enhanced search service statistics...")
        enhanced_stats = {
            'domain_ranking_enabled': True,
            'content_boost_enabled': True,
            'bm25_weight': self.BM25_WEIGHT,
            'domain_boost_weight': self.DOMAIN_BOOST_WEIGHT,
            'content_boost_weight': self.CONTENT_BOOST_WEIGHT,
            'domain_stats': self.domain_ranker.get_domain_stats()
        }
        
        return {**base_stats, **enhanced_stats}
    
    def _create_enhanced_preview(self, content: str, query: str) -> str:
        """Create enhanced preview with better snippet extraction"""
        print(f"Creating enhanced preview for content with query:")
        # Use base preview method but could be enhanced further
        return self._create_preview(content, query)
