"""
🚀 Enhanced Search Service with Domain Ranking
Extends the base SearchService with educational domain prioritization
"""

import time
import math
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
    Enhanced BM25 search with domain-based ranking and content type detection
    """
    
    def __init__(self, db_service):
        super().__init__(db_service)
        self.domain_ranker = DomainRanker()
        self.logger = logging.getLogger(__name__)
        
        # Enhanced scoring parameters
        self.DOMAIN_BOOST_WEIGHT = 0.3  # 30% weight to domain ranking
        self.CONTENT_BOOST_WEIGHT = 0.2  # 20% weight to content type
        self.BM25_WEIGHT = 0.5  # 50% weight to BM25 score
        self.MAX_SEARCH_LIMIT = MAX_SEARCH_LIMIT

        
        self.logger.info("Enhanced search service initialized with domain ranking")
    
    def _calculate_enhanced_bm25_score(self, query_terms: List[str], doc_id: int) -> float:
        """Calculate enhanced BM25 score with domain and content boosts"""
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
        """Enhanced search with domain ranking and content type detection"""
        start_time = time.time()
        
        # Validate inputs
        if not query or not query.strip():
            return {
                'query': query,
                'results': [],
                'total_found': 0,
                'search_time_ms': 0,
                'search_method': 'Enhanced BM25',
                'error': 'Empty query'
            }
        
        # Set default limit
        if limit is None:
            limit = self.DEFAULT_SEARCH_LIMIT
        elif limit > self.MAX_SEARCH_LIMIT:
            limit = self.MAX_SEARCH_LIMIT
        
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
                    'error': 'No documents indexed'
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
            
            return {
                'query': query,
                'results': fallback_results,
                'total_found': len(fallback_results),
                'search_time_ms': round((time.time() - start_time) * 1000, 2),
                'search_method': 'Enhanced Text Search (fallback)',
                'error': None
            }
        
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
        
        self.logger.info(f"Enhanced search completed: '{query}' -> {len(results)} results in {search_time}ms")
        
        return {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_time_ms': search_time,
            'search_method': 'Enhanced BM25',
            'error': None
        }
    
    def _enhanced_text_search_fallback(self, query: str, limit: int) -> List[Dict]:
        """Enhanced fallback search with domain ranking"""
        fallback_results = self.db_service.search_documents_by_text(query, limit * 2)  # Get more for ranking
        
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
        # Use base preview method but could be enhanced further
        return self._create_preview(content, query)
