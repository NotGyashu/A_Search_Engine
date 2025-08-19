# core/enhanced_search_service.py
import time
import logging
from typing import Dict, List, Optional
from collections import Counter
from datetime import datetime

from .opensearch_service import OpenSearchService

class ContentPreviewGenerator:
    """Handles intelligent content preview generation."""
    
    @staticmethod
    def create_preview(source: Dict, query: str = "", max_length: int = 300) -> str:
        """Create enhanced content preview with priority-based selection."""
        # Priority 1: Enhanced description from metadata
        description = source.get('description', '').strip()
        if description and len(description) > 30:
            return ContentPreviewGenerator._truncate_at_sentence(description, max_length)
        
        # Priority 2: Structured data description
        structured_data = source.get('structured_data', {})
        if structured_data and 'description' in structured_data:
            struct_desc = structured_data['description'].strip()
            if struct_desc and len(struct_desc) > 50:
                return ContentPreviewGenerator._truncate_smartly(struct_desc, max_length)
        
        # Priority 3: Query-relevant content from text chunk
        text_chunk = source.get('text_chunk', '')
        return ContentPreviewGenerator._create_query_relevant_preview(text_chunk, query, max_length)
    
    @staticmethod
    def _truncate_at_sentence(text: str, max_length: int) -> str:
        """Truncate text at sentence boundary."""
        if len(text) <= max_length:
            return text
        
        sentences = text.split('.')
        preview = ""
        for sentence in sentences:
            if len(preview + sentence) < max_length - 10:
                preview += sentence + "."
            else:
                break
        return preview + ("..." if len(text) > len(preview) else "")
    
    @staticmethod
    def _truncate_smartly(text: str, max_length: int) -> str:
        """Truncate text smartly at word boundary."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def _create_query_relevant_preview(content: str, query: str, max_length: int) -> str:
        """Create query-relevant content preview."""
        if not content:
            return ""
        
        if not query:
            return ContentPreviewGenerator._truncate_smartly(content, max_length)
        
        # Find most relevant sentence
        query_terms = query.lower().split()
        sentences = content.split('.')
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            score = sum(1 for term in query_terms if term in sentence.lower())
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        if best_sentence:
            return ContentPreviewGenerator._truncate_smartly(best_sentence + ".", max_length)
        
        return ContentPreviewGenerator._truncate_smartly(content, max_length)

class MetadataExtractor:
    """Handles extraction and processing of enhanced metadata."""
    
    @staticmethod
    def extract_author_info(source: Dict) -> tuple[Optional[str], Dict]:
        """Extract author name and full author info."""
        author_info = source.get('author_info', {})
        if not author_info:
            return None, {}
        
        author_name = (
            author_info.get('name') or 
            author_info.get('author') or 
            author_info.get('display_name')
        )
        return author_name, author_info
    
    @staticmethod
    def extract_dates(source: Dict) -> tuple[Optional[str], Optional[str]]:
        """Extract publication and modification dates."""
        return source.get('published_date'), source.get('modified_date')
    
    @staticmethod
    def extract_article_type(structured_data: Dict) -> Optional[str]:
        """Extract article type from structured data."""
        if not structured_data:
            return None
        
        article_type = structured_data.get('@type', '')
        if article_type:
            if ':' in article_type:
                article_type = article_type.split(':')[-1]
            return article_type.lower()
        
        for type_field in ['type', 'articleType', 'contentType']:
            if type_field in structured_data:
                return str(structured_data[type_field]).lower()
        
        return None
    
    @staticmethod
    def format_table_of_contents(toc_data: List[Dict], max_items: int = 5) -> List[str]:
        """Format table of contents for display."""
        if not toc_data:
            return []
        
        formatted_items = []
        for item in toc_data[:max_items]:
            if isinstance(item, dict):
                text = item.get('text', '').strip()
                level = item.get('level', 1)
                if text:
                    indent = "  " * (level - 1) if level > 1 else ""
                    formatted_items.append(f"{indent}{text}")
            elif isinstance(item, str) and item.strip():
                formatted_items.append(item.strip())
        
        return formatted_items

class SearchInsightsAnalyzer:
    """Analyzes search results to generate insights and analytics."""
    
    @staticmethod
    def analyze_results(results: List[Dict], query: str) -> Dict:
        """Generate comprehensive search insights."""
        if not results:
            return SearchInsightsAnalyzer._empty_insights()
        
        # Analyze domains and content types
        domains = [r.get('domain', '') for r in results if r.get('domain')]
        content_types = [r.get('content_type', 'unknown') for r in results if r.get('content_type')]
        article_types = [r.get('article_type', '') for r in results if r.get('article_type')]
        
        # Analyze dates and metadata presence
        published_dates = [r.get('published_date') for r in results if r.get('published_date')]
        authors_count = sum(1 for r in results if r.get('author'))
        toc_count = sum(1 for r in results if r.get('table_of_contents'))
        
        # Calculate scores
        quality_scores = [r.get('quality_score', 0) for r in results if r.get('quality_score')]
        relevance_scores = [r.get('relevance_score', 0) for r in results if r.get('relevance_score')]
        
        # Analyze categories
        all_categories = []
        for r in results:
            categories = r.get('content_categories', [])
            if categories:
                all_categories.extend(categories)
        
        return {
            'total_results': len(results),
            'domains_found': len(set(domains)),
            'top_domains': dict(Counter(domains).most_common(5)),
            'content_types': dict(Counter(content_types)),
            'article_types': dict(Counter(article_types)),
            'top_categories': dict(Counter(all_categories).most_common(5)),
            'date_range': SearchInsightsAnalyzer._analyze_date_range(published_dates),
            'results_with_authors': authors_count,
            'results_with_toc': toc_count,
            'average_quality_score': round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.0,
            'average_relevance_score': round(sum(relevance_scores) / len(relevance_scores), 2) if relevance_scores else 0.0,
            'has_recent_content': SearchInsightsAnalyzer._has_recent_content(published_dates),
            'content_diversity_score': SearchInsightsAnalyzer._calculate_diversity_score(results)
        }
    
    @staticmethod
    def _empty_insights() -> Dict:
        """Return empty insights structure."""
        return {
            'total_results': 0,
            'domains_found': 0,
            'content_types': {},
            'date_range': None,
            'has_authors': False,
            'has_toc': False,
            'average_quality': 0.0
        }
    
    @staticmethod
    def _analyze_date_range(dates: List[str]) -> Optional[Dict]:
        """Analyze date range of results."""
        if not dates:
            return None
        
        try:
            parsed_dates = []
            for date_str in dates:
                if not date_str:
                    continue
                try:
                    if 'T' in date_str:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    parsed_dates.append(dt)
                except:
                    continue
            
            if not parsed_dates:
                return None
            
            earliest = min(parsed_dates)
            latest = max(parsed_dates)
            
            return {
                'earliest': earliest.strftime('%Y-%m-%d'),
                'latest': latest.strftime('%Y-%m-%d'),
                'span_days': (latest - earliest).days,
                'total_dated_results': len(parsed_dates)
            }
        except:
            return None
    
    @staticmethod
    def _has_recent_content(dates: List[str], days_threshold: int = 365) -> bool:
        """Check if results contain recent content."""
        if not dates:
            return False
        
        try:
            current_date = datetime.now()
            for date_str in dates:
                if not date_str:
                    continue
                try:
                    if 'T' in date_str:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    
                    if (current_date - dt).days <= days_threshold:
                        return True
                except:
                    continue
            return False
        except:
            return False
    
    @staticmethod
    def _calculate_diversity_score(results: List[Dict]) -> float:
        """Calculate content diversity score."""
        if not results:
            return 0.0
        
        domains = set(r.get('domain', '') for r in results if r.get('domain'))
        content_types = set(r.get('content_type', '') for r in results if r.get('content_type'))
        
        all_categories = set()
        for r in results:
            categories = r.get('content_categories', [])
            if categories:
                all_categories.update(categories)
        
        max_possible_diversity = len(results)
        actual_diversity = len(domains) + len(content_types) + len(all_categories)
        
        return min(1.0, actual_diversity / max(max_possible_diversity, 1))

class ResultFormatter:
    """Formats search results with enhanced metadata."""
    
    @staticmethod
    def format_search_results(raw_results: List[Dict], query: str = "") -> List[Dict]:
        """Format raw OpenSearch results into enhanced application format."""
        formatted_results = []
        
        for hit in raw_results:
            source = hit.get('_source', {})
            formatted_result = ResultFormatter._format_single_result(hit, source, query)
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    @staticmethod
    def _format_single_result(hit: Dict, source: Dict, query: str) -> Dict:
        """Format a single search result."""
        # Extract enhanced metadata
        author_name, author_info = MetadataExtractor.extract_author_info(source)
        published_date, modified_date = MetadataExtractor.extract_dates(source)
        
        structured_data = source.get('structured_data', {})
        article_type = MetadataExtractor.extract_article_type(structured_data)
        
        table_of_contents = source.get('table_of_contents', [])
        toc_preview = MetadataExtractor.format_table_of_contents(table_of_contents) if table_of_contents else None
        
        # Generate content preview
        content_preview = ContentPreviewGenerator.create_preview(source, query)
        
        # Build enhanced result
        return {
            'id': hit.get('_id'),
            'url': source.get('url'),
            'canonical_url': source.get('canonical_url'),
            'title': source.get('title'),
            'content_preview': content_preview,
            'description': source.get('description', ''),
            'domain': source.get('domain'),
            'relevance_score': hit.get('_score'),
            'domain_score': source.get('domain_score'),
            'quality_score': source.get('quality_score'),
            'content_categories': source.get('content_categories', []),
            'categories': source.get('categories', source.get('content_categories', [])),
            'keywords': source.get('keywords', []),
            'icons': source.get('icons', {}),
            
            # Enhanced metadata
            'published_date': published_date,
            'modified_date': modified_date,
            'author': author_name,
            'author_info': author_info,
            'article_type': article_type,
            'table_of_contents': toc_preview,
            'semantic_info': source.get('semantic_info', {}),
            'structured_data_type': structured_data.get('@type') if structured_data else None,
            
            # Content metrics
            'chunk_count': source.get('chunk_count'),
            'word_count': source.get('word_count'),
            'content_type': source.get('content_type'),
            
            # Media information
            'images': source.get('images', []),
            'has_images': bool(source.get('images')),
            'image_count': len(source.get('images', [])),
        }

class SimpleCache:
    """Simple in-memory cache for search results."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache = {}
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached result."""
        return self._cache.get(key)
    
    def set(self, key: str, value: Dict) -> None:
        """Store result in cache."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        cached_value = value.copy()
        cached_value['from_cache'] = True
        self._cache[key] = cached_value
    
    def generate_key(self, query: str, limit: int) -> str:
        """Generate cache key."""
        return f"search:{query.lower().strip()}:{limit}"

class EnhancedSearchService:
    """Enhanced search service with AI Intelligence Hub integration."""
    
    def __init__(self, opensearch_service: OpenSearchService, ai_client_service=None):
        self.opensearch_service = opensearch_service
        self.ai_client = ai_client_service
        self.logger = logging.getLogger(__name__)
        self.cache = SimpleCache()
        
        # AI integration status
        self.ai_enabled = ai_client_service is not None
        if self.ai_enabled:
            self.logger.info("🧠 Enhanced Search Service initialized with AI Intelligence Hub")
        else:
            self.logger.info("🔍 Enhanced Search Service initialized without AI integration")
    
    def search(self, query: str, limit: int = 10, enable_cache: bool = True, enable_ai_enhancement: bool = True) -> Dict:
        """
        Perform enhanced search with AI Intelligence Hub integration.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            enable_cache: Whether to use caching
            enable_ai_enhancement: Whether to use AI enhancements
            
        Returns:
            Enhanced search results with AI analytics and insights
        """
        start_time = time.time()
        ai_insights = {}
        enhanced_query = query
        
        try:
            # Phase 1: AI Query Intelligence (if enabled) - BATCH OPTIMIZED
            if enable_ai_enhancement and self.ai_enabled:
                try:
                    # Prepare batch operations for Phase 1
                    phase1_operations = [
                        {"type": "enhance_query", "data": {"query": query}},
                        {"type": "classify_intent", "data": {"query": query}},
                        {"type": "extract_entities", "data": {"query": query}}
                    ]
                    
                    # Execute batch Phase 1 operations
                    batch_result = self.ai_client.batch_ai_operations(phase1_operations)
                    
                    if batch_result and batch_result.get('results'):
                        results = batch_result['results']
                        
                        # Process query enhancement
                        if 'enhance_query' in results and not results['enhance_query'].get('error'):
                            enhanced_query = results['enhance_query'].get('enhanced_query', query)
                            ai_insights['query_enhancement'] = results['enhance_query']
                        
                        # Process intent classification
                        if 'classify_intent' in results and not results['classify_intent'].get('error'):
                            ai_insights['intent_classification'] = results['classify_intent']
                        
                        # Process entity extraction
                        if 'extract_entities' in results and not results['extract_entities'].get('error'):
                            ai_insights['entity_extraction'] = results['extract_entities']
                        
                        # Log batch processing stats
                        batch_time = batch_result.get('total_processing_time_ms', 0)
                        self.logger.info(f"🚀 AI Phase 1 batch completed in {batch_time}ms for: '{query}'")
                    
                except Exception as e:
                    self.logger.warning(f"AI Phase 1 batch failed: {e}")
            
            # Check cache first
            if enable_cache:
                cache_key = self.cache.generate_key(enhanced_query, limit)
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    self.logger.info(f"Cache hit for enhanced query: {enhanced_query[:50]}")
                    # Add AI insights to cached result
                    if ai_insights:
                        cached_result['ai_insights'] = ai_insights
                    return cached_result
            
            # Perform the search with enhanced query
            opensearch_results = self._perform_search(enhanced_query, limit)
            
            # Format and enhance results
            formatted_results = self._format_and_enhance_results(opensearch_results, query)
            
            # Phase 2: AI Content Analysis (if enabled and we have results) - BATCH OPTIMIZED
            if enable_ai_enhancement and self.ai_enabled and formatted_results:
                try:
                    # Prepare batch operations for Phase 2
                    phase2_operations = [
                        {"type": "analyze_content", "data": {"results": formatted_results}},
                        {"type": "rerank_results", "data": {"results": formatted_results, "query": query}},
                        {"type": "generate_insights", "data": {"query": query, "results": formatted_results}}
                    ]
                    
                    # Execute batch Phase 2 operations
                    batch_result = self.ai_client.batch_ai_operations(phase2_operations)
                    
                    if batch_result and batch_result.get('results'):
                        results = batch_result['results']
                        
                        # Process content analysis
                        if 'analyze_content' in results and not results['analyze_content'].get('error'):
                            ai_insights['content_analysis'] = results['analyze_content']
                        
                        # Process reranking
                        if 'rerank_results' in results and not results['rerank_results'].get('error'):
                            formatted_results = results['rerank_results'].get('reranked_results', formatted_results)
                            ai_insights['reranking'] = results['rerank_results']
                        
                        # Process comprehensive insights
                        if 'generate_insights' in results and not results['generate_insights'].get('error'):
                            ai_insights['comprehensive_insights'] = results['generate_insights']
                        
                        # Log batch processing stats
                        batch_time = batch_result.get('total_processing_time_ms', 0)
                        self.logger.info(f"🔍 AI Phase 2 batch completed in {batch_time}ms for {len(formatted_results)} results")
                    
                except Exception as e:
                    self.logger.warning(f"AI Phase 2 batch failed: {e}")
            
            # Generate analytics and insights
            search_insights = self._generate_search_analytics(formatted_results, query)
            
            # Build final response with AI insights
            response = self._build_search_response(
                formatted_results, search_insights, query, start_time, ai_insights
            )
            
            # Cache successful results
            if enable_cache and formatted_results:
                self.cache.set(cache_key, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Search failed for query '{query}': {str(e)}")
            return self._build_error_response(str(e), start_time)
    
    def _perform_search(self, query: str, limit: int) -> List[Dict]:
        """Perform the actual OpenSearch query."""
        return self.opensearch_service.search(query, limit)
    
    def _format_and_enhance_results(self, raw_results: List[Dict], query: str) -> List[Dict]:
        """Format raw results and enhance with metadata."""
        return ResultFormatter.format_search_results(raw_results, query)
    
    def _generate_search_analytics(self, results: List[Dict], query: str) -> Dict:
        """Generate search insights and analytics."""
        return SearchInsightsAnalyzer.analyze_results(results, query)
    
    def _build_search_response(self, results: List[Dict], insights: Dict, query: str, start_time: float, ai_insights: Dict = None) -> Dict:
        """Build the final search response with AI insights."""
        response_time = round((time.time() - start_time) * 1000, 2)
        
        response = {
            'query': query,
            'total_results': len(results),
            'results': results,
            'search_insights': insights,
            'response_time_ms': response_time,
            'timestamp': datetime.now().isoformat(),
            'from_cache': False
        }
        
        # Add AI insights if available
        if ai_insights:
            response['ai_insights'] = ai_insights
            response['ai_enhanced'] = True
        else:
            response['ai_enhanced'] = False
            
        return response
    
    def _build_error_response(self, error_message: str, start_time: float) -> Dict:
        """Build error response."""
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'error': error_message,
            'results': [],
            'total_results': 0,
            'search_insights': SearchInsightsAnalyzer._empty_insights(),
            'response_time_ms': response_time,
            'timestamp': datetime.now().isoformat(),
            'from_cache': False
        }
    
    def health_check(self) -> Dict:
        """Check service health."""
        try:
            opensearch_health = self.opensearch_service.health_check()
            cache_size = len(self.cache._cache)
            
            return {
                'status': 'healthy' if opensearch_health.get('status') == 'healthy' else 'unhealthy',
                'opensearch': opensearch_health,
                'cache_size': cache_size,
                'cache_max_size': self.cache.max_size,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }