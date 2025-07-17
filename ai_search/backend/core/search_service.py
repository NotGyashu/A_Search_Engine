""" # Search Service - Core search functionality using BM25 algorithm
Clean, modular implementation with proper separation of concerns
"""

import time
import math
import re
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import sys

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger, PerformanceMonitor, TextProcessor
from common.config import (
    BM25_K1, BM25_B, BM25_MIN_TERM_LENGTH, 
    DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT,
    CONTENT_PREVIEW_LENGTH, TITLE_WEIGHT_MULTIPLIER
)
from .database_service import DatabaseService


class SearchService:
    """Main search service using BM25 algorithm"""
    
    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.logger = Logger.setup_logger("backend.search")
        
        # BM25 parameters
        self.k1 = BM25_K1
        self.b = BM25_B
        
        # Search index
        self.documents = {}              # doc_id -> document data
        self.term_freq = defaultdict(dict)  # term -> {doc_id: frequency}
        self.doc_freq = defaultdict(int)    # term -> document frequency
        self.doc_lengths = {}            # doc_id -> document length
        self.avg_doc_length = 0
        self.total_docs = 0
        
        # Build index on initialization
        self._build_index()
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for search indexing"""
        if not text:
            return []
        
        # Use the common text processor
        processor = TextProcessor()
        tokens = processor.tokenize(text)
        
        # Filter by minimum length
        return [token for token in tokens if len(token) >= BM25_MIN_TERM_LENGTH]
    
    def _build_index(self):
        """Build BM25 search index from database"""
        with PerformanceMonitor("Search Index Build") as monitor:
            self.logger.info("Building search index...")
            
            # Get all documents from database
            documents = self.db_service.get_all_documents()
            
            if not documents:
                self.logger.warning("No documents found in database")
                return
            
            # Reset index
            self.documents = {}
            self.term_freq = defaultdict(dict)
            self.doc_freq = defaultdict(int)
            self.doc_lengths = {}
            
            total_length = 0
            
            for doc in documents:
                doc_id = doc['id']
                
                # Store document
                self.documents[doc_id] = doc
                
                # Create searchable text (title gets extra weight)
                title = doc.get('title', '') or ''
                content = doc.get('content', '') or ''
                
                # Weight title by appearing multiple times
                searchable_text = ' '.join([title] * TITLE_WEIGHT_MULTIPLIER + [content])
                
                # Tokenize and count terms
                tokens = self._tokenize(searchable_text)
                doc_length = len(tokens)
                
                if doc_length == 0:
                    continue
                
                self.doc_lengths[doc_id] = doc_length
                total_length += doc_length
                
                # Count term frequencies
                term_counts = Counter(tokens)
                
                for term, freq in term_counts.items():
                    self.term_freq[term][doc_id] = freq
                    if doc_id not in [d for d in self.term_freq[term].keys()]:
                        self.doc_freq[term] += 1
                
                # Fix doc_freq calculation
                for term in set(tokens):
                    if term not in self.doc_freq:
                        self.doc_freq[term] = 0
                    # Count unique documents containing this term
                    self.doc_freq[term] = len(self.term_freq[term])
            
            self.total_docs = len(self.documents)
            self.avg_doc_length = total_length / self.total_docs if self.total_docs > 0 else 0
            
            self.logger.info(f"Index built: {self.total_docs} documents, "
                        f"{len(self.term_freq)} unique terms, "
                        f"avg length: {self.avg_doc_length:.1f}")
    
    def _calculate_bm25_score(self, query_terms: List[str], doc_id: int) -> float:
        """Calculate BM25 score for a document"""
        if doc_id not in self.documents:
            return 0.0
        
        doc_length = self.doc_lengths.get(doc_id, 0)
        if doc_length == 0:
            return 0.0
        
        score = 0.0
        
        for term in query_terms:
            if term not in self.term_freq or doc_id not in self.term_freq[term]:
                continue
            
            # Term frequency in document
            tf = self.term_freq[term][doc_id]
            
            # Document frequency
            df = self.doc_freq[term]
            if df == 0:
                continue
            
            # IDF calculation
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5))
            
            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
            
            score += idf * (numerator / denominator)
        
        return score
    
    def search(self, query: str, limit: int = None) -> Dict:
        """Perform search and return results"""
        start_time = time.time()
        
        # Validate inputs
        if not query or not query.strip():
            return {
                'query': query,
                'results': [],
                'total_found': 0,
                'search_time_ms': 0,
                'search_method': 'BM25',
                'error': 'Empty query'
            }
        
        # Set default limit
        if limit is None:
            limit = DEFAULT_SEARCH_LIMIT
        elif limit > MAX_SEARCH_LIMIT:
            limit = MAX_SEARCH_LIMIT
        
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
                    'search_method': 'BM25',
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
                'search_method': 'BM25',
                'error': 'No valid search terms'
            }
        
        # Find candidate documents
        candidate_docs = set()
        for term in query_terms:
            if term in self.term_freq:
                candidate_docs.update(self.term_freq[term].keys())
        
        if not candidate_docs:
            # Fallback to simple text search
            self.logger.info("No BM25 matches, falling back to text search")
            fallback_results = self.db_service.search_documents_by_text(query, limit)
            
            results = []
            for doc in fallback_results:
                results.append({
                    'id': doc['id'],
                    'url': doc['url'],
                    'title': doc['title'],
                    'content_preview': self._create_preview(doc['content'], query),
                    'domain': doc['domain'],
                    'word_count': doc['word_count'],
                    'relevance_score': 0.1  # Low score for fallback
                })
            
            return {
                'query': query,
                'results': results,
                'total_found': len(results),
                'search_time_ms': round((time.time() - start_time) * 1000, 2),
                'search_method': 'Text Search (fallback)',
                'error': None
            }
        
        # Calculate BM25 scores
        doc_scores = []
        for doc_id in candidate_docs:
            score = self._calculate_bm25_score(query_terms, doc_id)
            if score > 0:
                doc_scores.append((doc_id, score))
        
        # Sort by relevance
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        doc_scores = doc_scores[:limit]
        
        # Format results
        results = []
        for doc_id, score in doc_scores:
            doc = self.documents[doc_id]
            
            results.append({
                'id': doc_id,
                'url': doc['url'],
                'title': doc['title'],
                'content_preview': self._create_preview(doc['content'], query),
                'domain': doc['domain'],
                'word_count': doc['word_count'],
                'relevance_score': round(score, 3)
            })
        
        search_time = round((time.time() - start_time) * 1000, 2)
        
        self.logger.info(f"Search completed: '{query}' -> {len(results)} results in {search_time}ms")
        
        return {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_time_ms': search_time,
            'search_method': 'BM25',
            'error': None
        }
    
    def _create_preview(self, content: str, query: str) -> str:
        """Create content preview highlighting search terms"""
        if not content:
            return ""
        
        # Find the best excerpt around search terms
        query_terms = self._tokenize(query.lower())
        content_lower = content.lower()
        
        # Find first occurrence of any search term
        best_start = 0
        for term in query_terms:
            pos = content_lower.find(term.lower())
            if pos != -1:
                # Start preview a bit before the term
                best_start = max(0, pos - 100)
                break
        
        # Extract preview
        preview = content[best_start:best_start + CONTENT_PREVIEW_LENGTH]
        
        # Clean up preview
        if best_start > 0:
            preview = "..." + preview
        
        if len(content) > best_start + CONTENT_PREVIEW_LENGTH:
            preview = preview + "..."
        
        return preview.strip()
    
    def get_stats(self) -> Dict:
        """Get search engine statistics"""
        return {
            'total_documents': self.total_docs,
            'total_terms': len(self.term_freq),
            'average_document_length': round(self.avg_doc_length, 1),
            'bm25_parameters': {
                'k1': self.k1,
                'b': self.b,
                'min_term_length': BM25_MIN_TERM_LENGTH
            },
            'index_status': 'ready' if self.documents else 'not_built'
        }
    
    def health_check(self) -> Dict:
        """Check search service health"""
        try:
            # Check if index is built
            if not self.documents:
                return {
                    'status': 'unhealthy',
                    'error': 'Search index not built',
                    'document_count': 0
                }
            
            # Test search functionality
            test_result = self.search("test", limit=1)
            
            return {
                'status': 'healthy',
                'document_count': self.total_docs,
                'terms_indexed': len(self.term_freq),
                'test_search_working': test_result.get('error') is None
            }
            
        except Exception as e:
            self.logger.error(f"Search health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'document_count': 0
            }
    
    def rebuild_index(self):
        """Rebuild the search index"""
        self.logger.info("Rebuilding search index...")
        self._build_index()
        return self.get_stats()